"""Retryable stages. Store the source before attempting optional enrichment."""
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from sqlalchemy import select, and_, or_
from models import Email, EmailPrediction, EmailTask
from backend_models import ProcessingState
from email_utils import extract_email_body
from predict import classify_email
from priority import calculate_priority
from summarizer import summarize_email
from task_extractor import extract_action_items, _same_task
from deadline_extractor import parse_email_datetime
from fact_store import refresh_facts
from semantic_index import index_email
import email_facts
import embedding_service
from semantic_content import CONTENT_VERSION

logger = logging.getLogger(__name__)


def disabled_sync_stages():
    """The default/local profile retains every enrichment stage."""
    if os.getenv('INBOX_RUNTIME_PROFILE', 'full').strip().lower() == 'render-free':
        return frozenset({'embedding'})
    return frozenset()


def retryable_stages():
    # Bounded retries per input/version; a failing classifier never blocks Gmail
    # cursor publication. Previously disabled classification is adopted gradually.
    return or_(ProcessingState.status == 'pending',
               and_(ProcessingState.status == 'failed', ProcessingState.attempts < 3),
               and_(ProcessingState.status == 'skipped', ProcessingState.stage == 'classify'))


def parse_header_date(raw):
    if not raw:
        return None, 'missing'
    try:
        value = parsedate_to_datetime(raw)
        return (value.astimezone(timezone.utc), 'parsed') if value.tzinfo else (None, 'naive')
    except (TypeError, ValueError, OverflowError):
        return None, 'invalid'


def store_message(db, account, message_id, message):
    headers = {h['name'].lower(): h.get('value', '') for h in message.get('payload', {}).get('headers', [])}
    email = db.scalar(select(Email).where(Email.account_id == account.id, Email.message_id == message_id))
    if email is None:
        email = Email(account_id=account.id, message_id=message_id)
        db.add(email)
    email.raw_payload = message.get('payload', {})
    email.subject = headers.get('subject', '')[:500]
    email.sender = headers.get('from', '')[:500]
    email.email_date = headers.get('date', '')[:255]
    email.sent_at, email.date_status = parse_header_date(email.email_date)
    try:
        email.message_at = datetime.fromtimestamp(int(message['internalDate']) / 1000, timezone.utc)
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        email.message_at = None
    email.gmail_labels = message.get('labelIds', [])
    db.flush()
    return email


def _classify(email, db):
    # Adopt legacy results once; later changed inputs replace derived results.
    if not email.predictions:
        predictions = classify_email(email.subject or '', email.body or '')
        email.predictions = [EmailPrediction(**item) for item in predictions]
        if email.priority_score is None:
            priority = calculate_priority(predictions)
            email.priority_score, email.priority_level = priority['priority_score'], priority['priority_level']


def _summary(email, db):
    if not email.summary:
        email.summary = summarize_email(email.subject or '', email.body or '')


def _tasks(email, db):
    if not email.tasks:
        email.tasks = [EmailTask(**item) for item in extract_action_items(
            email.subject or '', email.body or '', parse_email_datetime(email.email_date))]
    elif any(t.deadline_confidence is None for t in email.tasks):
        items = extract_action_items(email.subject or '', email.body or '', parse_email_datetime(email.email_date))
        for task in email.tasks:
            matches = [item for item in items if _same_task(task.task, item['task'])]
            fields = ('deadline_text', 'deadline_date', 'deadline_at', 'deadline_confidence')
            if len(matches) == 1 and not any(getattr(task, f) is not None and matches[0].get(f) is not None
                                           and getattr(task, f) != matches[0][f] for f in fields):
                for field in fields:
                    if getattr(task, field) is None:
                        setattr(task, field, matches[0].get(field))


def process_email(db, email, *, commit_stages=False, deadline=None):
    from time import monotonic
    from types import SimpleNamespace
    stages = [('clean', 'clean-v1', lambda e, s: setattr(e, 'body', extract_email_body(e.raw_payload or {}))),
              ('classify', 'classify-v1', _classify), ('summary', 'summary-v1', _summary),
              ('tasks', 'tasks-v1', _tasks), ('facts', email_facts.EXTRACTOR_VERSION, lambda e, s: refresh_facts(e, s)),
              ('embedding', embedding_service.MODEL_NAME + ':' + str(CONTENT_VERSION), lambda e, s: index_email(e, s))]
    failures = []
    disabled = disabled_sync_stages()
    # Persist terminal markers before any deadline/clean-stage early return.
    # Previously interrupted or failed heavy stages must not keep sync pending.
    for stage, version, _ in stages:
        if stage not in disabled:
            continue
        state = db.scalar(select(ProcessingState).where(
            ProcessingState.email_id == email.id, ProcessingState.stage == stage))
        if state is None:
            state = ProcessingState(email_id=email.id, stage=stage, attempts=0,
                                    input_hash='', version=version)
            db.add(state)
        state.status, state.error_code = 'skipped', 'runtime_disabled'
    if disabled:
        db.flush()
        if commit_stages:
            db.commit()
    for stage, version, operation in stages:
        if stage in disabled:
            continue  # Do not prepare inputs, load models, or erase derived data.
        data = email.raw_payload if stage == 'clean' else [email.subject, email.body, email.email_date,
                                                          email.summary if stage == 'embedding' else None]
        digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        state = db.scalar(select(ProcessingState).where(ProcessingState.email_id == email.id, ProcessingState.stage == stage))
        if state and state.status == 'complete' and state.input_hash == digest and state.version == version:
            continue
        changed = state is not None and (state.input_hash != digest or state.version != version
                                         or state.status != 'complete')
        if state is None:
            state = ProcessingState(email_id=email.id, stage=stage, attempts=0)
            db.add(state)
        elif state.input_hash != digest or state.version != version:
            state.attempts = 0
        state.input_hash, state.version, state.status = digest, version, 'pending'
        state.attempts += 1
        db.flush()
        if commit_stages:
            # The sync worker uses expire_on_commit=False and owns an account
            # session lock. Source/state commits survive interruption. Long local
            # model calls run with no database transaction or row lock held.
            if stage == 'classify':
                snapshot = SimpleNamespace(subject=email.subject, body=email.body,
                    predictions=[] if changed else list(email.predictions),
                    priority_score=None if changed else email.priority_score,
                    priority_level=None if changed else email.priority_level)
            elif stage == 'summary':
                snapshot = SimpleNamespace(subject=email.subject, body=email.body,
                                           summary=None if changed else email.summary)
            db.commit()
            if deadline is not None and monotonic() >= deadline:
                break  # Persisted pending stage is picked up by a later batch.
        try:
            prepared = None
            if commit_stages and stage in ('classify', 'summary'):
                (_classify if stage == 'classify' else _summary)(snapshot, None)
            elif commit_stages and stage == 'embedding':
                from semantic_index import prepare_index
                prepared = prepare_index(email)
            with db.begin_nested():
                if changed:
                    if stage == 'classify':
                        email.predictions.clear()
                        email.priority_score = email.priority_level = None
                    elif stage == 'summary':
                        email.summary = None
                    elif stage == 'tasks':
                        email.tasks.clear()
                    db.flush()
                if commit_stages and stage == 'classify':
                    email.predictions = snapshot.predictions
                    email.priority_score, email.priority_level = snapshot.priority_score, snapshot.priority_level
                elif commit_stages and stage == 'summary':
                    email.summary = snapshot.summary
                elif commit_stages and stage == 'embedding':
                    index_email(email, db, prepared=prepared)
                else:
                    operation(email, db)
                db.flush()
            state.status, state.error_code = 'complete', None
        except Exception as error:
            state.status, state.error_code = 'failed', 'stage_unavailable'
            failures.append(stage)
            logger.warning('Email enrichment failed: stage=%s error_type=%s',
                           stage, type(error).__name__)
        db.flush()
        if commit_stages:
            db.commit()
        if stage == 'clean' and failures:
            break
    return failures
