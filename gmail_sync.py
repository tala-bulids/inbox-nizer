"""Bounded, resumable Gmail history sync; one request is one committed batch."""
from contextlib import nullcontext
from datetime import datetime, timezone, timedelta
import os
import logging
import hashlib
import json
from time import monotonic
from uuid import uuid4
from fastapi import HTTPException
from googleapiclient.errors import HttpError
from sqlalchemy import select, text, or_
from sqlalchemy.engine import Engine
from models import Email
from backend_models import GmailAccount, GmailSyncState, ProcessingState
from ownership import OwnedSession
from gmail_service import get_gmail_service
from email_pipeline import store_message, process_email, retryable_stages

logger = logging.getLogger(__name__)
MESSAGE_LIMIT = 5
PAGE_LIMIT = 2
PAGE_SIZE = 50
TIME_BUDGET = 20  # Soft: checked between operations; Render uses bounded CPU inference.


def source_id(item):
    # Existing checkpoints contain strings. Failed entries additionally persist
    # attempt counts in the existing JSON column; no source ID is discarded.
    return item['id'] if isinstance(item, dict) else item


def source_attempts(item):
    return item.get('attempts', 0) if isinstance(item, dict) else 0


def source_has_more(state):
    return state is not None and (not state.listing_done or not state.pending or
                                 any(source_attempts(item) < 3 for item in state.pending))


def source_failure_count(state):
    return sum(source_attempts(item) > 0 for item in state.pending) if state else 0


def initial_query():
    days = int(os.getenv('GMAIL_INITIAL_SYNC_DAYS', '90'))
    if not 0 <= days <= 3650:
        raise ValueError('Invalid Gmail initial import window')
    if not days:
        return None  # Explicit operator opt-in to an unfiltered mirror.
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return 'after:' + str(int(cutoff.timestamp()))


def execute(request):
    return request.execute(num_retries=0)


def connection_guard(db, account_id):
    """Connection changes share the sync lock without changing OAuth."""
    if not db.scalar(text('SELECT pg_try_advisory_xact_lock(724193, :account)'), {'account': account_id}):
        raise HTTPException(409, 'Sync already in progress; retry connection change')


def _page(service, state):
    args = dict(userId='me', maxResults=PAGE_SIZE)
    if state.page_token:
        args['pageToken'] = state.page_token
    if state.mode == 'full':
        if state.import_query:
            args['q'] = state.import_query
        result = execute(service.users().messages().list(includeSpamTrash=True, **args))
        ids = [item['id'] for item in result.get('messages', [])]
    else:
        result = execute(service.users().history().list(startHistoryId=state.anchor, **args))
        ids = []
        for event in result.get('history', []):
            for kind in ('messagesAdded', 'messagesDeleted', 'labelsAdded', 'labelsRemoved'):
                ids.extend(item['message']['id'] for item in event.get(kind, []))
            ids.extend(item['id'] for item in event.get('messages', []))
        state.target = str(result['historyId'])
    next_page = result.get('nextPageToken')
    if next_page and next_page == state.page_token:
        raise RuntimeError('Gmail pagination did not advance')
    existing_ids = {source_id(item) for item in state.pending}
    state.pending = state.pending + [ident for ident in dict.fromkeys(ids) if ident not in existing_ids]
    state.page_token = next_page
    state.listing_done = not state.page_token


def _mark_pending(db, email):
    state = db.scalar(select(ProcessingState).where(ProcessingState.email_id == email.id,
                                                   ProcessingState.stage == 'clean'))
    if state is None:
        state = ProcessingState(email_id=email.id, stage='clean', input_hash='', version='clean-v1', attempts=0)
        db.add(state)
    state.status = 'pending'


def _progress_token(db, account_id, state):
    """Opaque checkpoint, not a continuation authority or a Gmail page token.

    A page spans several batches. Include its remaining IDs, reconciliation,
    and the first retryable stage so unchanged work can be detected by clients.
    Attempts are intentionally excluded: repeated failures are not progress.
    """
    retry = db.scalar(select(ProcessingState).join(Email, Email.id == ProcessingState.email_id)
        .where(Email.account_id == account_id, retryable_stages())
        .order_by(ProcessingState.id).limit(1))
    missing = None
    if state and state.mode == 'full' and not state.import_query and state.listing_done and not state.pending:
        missing = db.scalar(select(Email.id).where(Email.account_id == account_id,
            or_(Email.sync_generation.is_(None), Email.sync_generation != state.generation))
            .order_by(Email.id).limit(1))
    checkpoint = dict(
        source=[state.generation, state.mode, state.anchor, state.target, state.page_token,
                [[source_id(item), source_attempts(item) >= 3] for item in state.pending],
                state.listing_done] if state else None,
        retry=[retry.id, retry.status, retry.input_hash, retry.version] if retry else None,
        missing=missing)
    return hashlib.sha256(json.dumps(checkpoint, sort_keys=True).encode()).hexdigest()


def _batch(db, account_id, retry_failed=False):
    deadline = monotonic() + TIME_BUDGET
    account = db.get(GmailAccount, account_id)
    if account is None:
        raise HTTPException(404, 'Gmail account not found')
    result = dict(count=0, success_count=0, failed_count=0, enrichment_failed=0,
                  deleted=0, emails=[], has_more=False)
    processed = set()
    failed_ids = set()
    try:
        service = get_gmail_service(db, account)
        db.commit()
        state = db.get(GmailSyncState, account_id)
        if state is None:
            state = GmailSyncState(account_id=account_id, generation=str(uuid4()),
                mode='history' if account.history_id else 'full', anchor=account.history_id,
                pending=[], listing_done=False,
                import_query=None if account.history_id else initial_query())
            db.add(state)
        db.commit()
        if state.mode == 'full' and not state.anchor:
            state.anchor = state.target = str(execute(service.users().getProfile(userId='me'))['historyId'])
            db.commit()
        pages = 0
        while result['count'] < MESSAGE_LIMIT and monotonic() < deadline:
            # Listing later pages takes precedence over retrying failed bodies.
            # Persist failures alongside fresh IDs, keeping the original anchor.
            if not any(source_attempts(item) == 0 for item in state.pending) and not state.listing_done:
                if pages >= PAGE_LIMIT:
                    break
                db.commit()
                try:
                    _page(service, state)
                except HttpError as error:
                    if error.resp.status == 404 and state.mode == 'history':
                        state.mode, state.anchor, state.target = 'full', None, None
                        state.generation = str(uuid4())
                        state.import_query = initial_query()
                    elif error.resp.status == 400 and state.page_token:
                        if state.mode == 'full':
                            state.generation, state.anchor, state.target = str(uuid4()), None, None
                    else:
                        raise
                    state.page_token, state.listing_done = None, False
                    db.commit()
                    result['has_more'] = True
                    result['progress_token'] = _progress_token(db, account_id, state)
                    return result
                pages += 1
                db.commit()  # Persist page IDs before fetching any bodies.
                if not state.pending:
                    continue
            if monotonic() >= deadline:
                break  # Listing may have consumed the remaining request budget.
            candidate = next((item for item in sorted(state.pending, key=lambda item: source_attempts(item) > 0)
                              if source_id(item) not in failed_ids and
                              (source_attempts(item) < 3 or retry_failed)), None)
            if candidate is None:
                break  # Exhausted IDs remain durable for explicit recovery.
            message_id = source_id(candidate)
            result['count'] += 1
            try:
                existing = db.scalar(select(Email).where(Email.account_id == account_id, Email.message_id == message_id))
                already_seen = state.mode == 'full' and existing is not None and existing.sync_generation == state.generation
                db.commit()
                if not already_seen:
                    try:
                        message = execute(service.users().messages().get(userId='me', id=message_id, format='full'))
                    except HttpError as error:
                        if error.resp.status != 404:
                            raise
                        if existing:
                            db.delete(existing)
                            result['deleted'] += 1
                    else:
                        email = store_message(db, account, message_id, message)
                        email.sync_generation = state.generation
                        _mark_pending(db, email)
                        db.commit()  # Original source plus retry marker survive interruption.
                        failures = process_email(db, email, commit_stages=True, deadline=deadline)
                        processed.add(email.id)
                        result['success_count'] += 1
                        result['enrichment_failed'] += bool(failures)
                        result['emails'].append(dict(id=message_id, **{'from': email.sender}, date=email.email_date,
                            subject=email.subject, body=email.body,
                            predictions=[dict(category=p.category, confidence=p.confidence) for p in email.predictions]))
                state.pending = [item for item in state.pending if source_id(item) != message_id]
                db.commit()  # Atomic acknowledgement; replay is idempotent.
            except HTTPException:
                db.commit()  # Persist a provider-triggered reconnect requirement.
                raise
            except Exception as error:
                db.rollback()
                logger.warning('Gmail source failed: error_type=%s', type(error).__name__)
                result['failed_count'] += 1
                failed_ids.add(message_id)
                # Keep failures durable, but allow other IDs on this page to
                # succeed. The cursor cannot advance while any failed ID remains.
                attempts = source_attempts(candidate) + 1
                state.pending = [item for item in state.pending if source_id(item) != message_id] + [
                    {'id': message_id, 'attempts': attempts}]
                db.commit()

        if not state.pending and state.listing_done:
            missing = []
            if state.mode == 'full' and not state.import_query:
                missing = db.scalars(select(Email).where(Email.account_id == account_id,
                    or_(Email.sync_generation.is_(None), Email.sync_generation != state.generation))
                    .order_by(Email.id).limit(MESSAGE_LIMIT)).all()
                for email in missing:
                    db.delete(email)
                    result['deleted'] += 1
                db.commit()
            if not missing:
                account.history_id = state.target
                db.delete(state)
                db.commit()
                state = None
        pending = list(db.scalars(select(ProcessingState.email_id).join(Email, Email.id == ProcessingState.email_id)
            .where(Email.account_id == account_id, retryable_stages(),
                   ProcessingState.email_id.not_in(processed))
            .distinct().order_by(ProcessingState.email_id).limit(1)))
        for email_id in pending:
            if monotonic() >= deadline:
                break
            email = db.get(Email, email_id)
            failures = process_email(db, email, commit_stages=True, deadline=deadline)
            result['enrichment_failed'] += bool(failures)
        enrichment_pending = db.scalar(select(ProcessingState.id).join(Email, Email.id == ProcessingState.email_id)
            .where(Email.account_id == account_id, retryable_stages()).limit(1)) is not None
        result['source_failed_count'] = source_failure_count(state)
        result['recovery_required'] = bool(state and any(source_attempts(item) >= 3 for item in state.pending))
        result['has_more'] = source_has_more(state) or enrichment_pending
        account.sync_error = ('source_recovery_required' if result['recovery_required'] else
                              'partial_failure' if result['source_failed_count'] or enrichment_pending else None)
        # Last successful Gmail contact with committed source progress, not the
        # completion time of optional classification/backfill work.
        if result['success_count'] or result['deleted'] or (state is None and not result['failed_count']):
            account.last_synced_at = datetime.now(timezone.utc)
        result['progress_token'] = _progress_token(db, account_id, state)
        db.commit()
        return result
    except HTTPException:
        db.commit()
        raise
    except Exception as error:
        logger.warning('Gmail sync failed: error_type=%s', type(error).__name__)
        db.rollback()
        account = db.get(GmailAccount, account_id)
        account.sync_error = 'sync_unavailable'
        db.commit()
        raise HTTPException(503, 'Gmail sync temporarily unavailable; retry safely') from error


def sync_account(db, account_id, *, retry_failed=False):
    return _locked_account_work(db, account_id, lambda worker, ident: _batch(worker, ident, retry_failed))


def retry_enrichment(db, email_id):
    email = db.get(Email, email_id)
    if email is None:
        raise HTTPException(404, 'Email not found')
    def repair(worker, account_id):
        stored = worker.get(Email, email_id)
        if stored is None:
            raise HTTPException(404, 'Email not found')
        failures = process_email(worker, stored, commit_stages=True,
                                 deadline=monotonic() + TIME_BUDGET, retry_failed=True)
        return {'failed_stages': failures}
    return _locked_account_work(db, email.account_id, repair)


def _locked_account_work(db, account_id, operation):
    if db.scalar(select(GmailAccount.id).where(GmailAccount.id == account_id)) is None:
        raise HTTPException(404, 'Gmail account not found')
    user_id = db.user_id
    db.commit()
    bind = db.get_bind()
    dedicated = isinstance(bind, Engine)
    # Pin a connection: session locks must never return to the pool while held.
    with (bind.connect() if dedicated else nullcontext(bind)) as connection:
        locked = False
        try:
            try:
                locked = bool(connection.scalar(text('SELECT pg_try_advisory_lock(724193, :account)'), {'account': account_id}))
            except BaseException:
                # A lost/cancelled response can leave acquisition ambiguous.
                # Never pool a connection that might own this session lock.
                connection.invalidate()
                raise
            if dedicated:
                connection.commit()
            if not locked:
                raise HTTPException(409, 'Sync already in progress')
            with OwnedSession(bind=connection, user_id=user_id, expire_on_commit=False,
                              autoflush=False, join_transaction_mode='create_savepoint') as worker:
                return operation(worker, account_id)
        finally:
            if locked:
                try:
                    if dedicated and connection.in_transaction():
                        connection.rollback()
                    released = connection.scalar(text('SELECT pg_advisory_unlock(724193, :account)'), {'account': account_id})
                    if not released:
                        raise RuntimeError('Sync lock release was not confirmed')
                    if dedicated:
                        connection.commit()
                except BaseException as error:
                    connection.invalidate()
                    if not isinstance(error, Exception):
                        raise
            db.expire_all()
