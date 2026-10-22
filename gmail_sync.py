"""Bounded, resumable Gmail history sync; one request is one committed batch."""
from contextlib import nullcontext
from datetime import datetime, timezone
import logging
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
from email_pipeline import store_message, process_email

logger = logging.getLogger(__name__)
MESSAGE_LIMIT = 5
PAGE_LIMIT = 2
PAGE_SIZE = 50
TIME_BUDGET = 20  # Soft: checked between operations; render-free never runs models.


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
    state.pending = list(dict.fromkeys(ids))
    state.page_token = result.get('nextPageToken')
    state.listing_done = not state.page_token


def _mark_pending(db, email):
    state = db.scalar(select(ProcessingState).where(ProcessingState.email_id == email.id,
                                                   ProcessingState.stage == 'clean'))
    if state is None:
        state = ProcessingState(email_id=email.id, stage='clean', input_hash='', version='clean-v1', attempts=0)
        db.add(state)
    state.status = 'pending'


def _batch(db, account_id):
    deadline = monotonic() + TIME_BUDGET
    account = db.get(GmailAccount, account_id)
    if account is None:
        raise HTTPException(404, 'Gmail account not found')
    result = dict(count=0, success_count=0, failed_count=0, enrichment_failed=0,
                  deleted=0, emails=[], has_more=False)
    processed = set()
    try:
        service = get_gmail_service(db, account)
        db.commit()
        state = db.get(GmailSyncState, account_id)
        if state is None:
            state = GmailSyncState(account_id=account_id, generation=str(uuid4()),
                mode='history' if account.history_id else 'full', anchor=account.history_id,
                pending=[], listing_done=False)
            db.add(state)
        db.commit()
        if state.mode == 'full' and not state.anchor:
            state.anchor = state.target = str(execute(service.users().getProfile(userId='me'))['historyId'])
            db.commit()
        pages = 0
        while result['count'] < MESSAGE_LIMIT and monotonic() < deadline:
            if not state.pending:
                if state.listing_done or pages >= PAGE_LIMIT:
                    break
                db.commit()
                try:
                    _page(service, state)
                except HttpError as error:
                    if error.resp.status == 404 and state.mode == 'history':
                        state.mode, state.anchor, state.target = 'full', None, None
                        state.generation = str(uuid4())
                    elif error.resp.status == 400 and state.page_token:
                        if state.mode == 'full':
                            state.generation, state.anchor, state.target = str(uuid4()), None, None
                    else:
                        raise
                    state.page_token, state.pending, state.listing_done = None, [], False
                    db.commit()
                    result['has_more'] = True
                    return result
                pages += 1
                db.commit()  # Persist page IDs before fetching any bodies.
                if not state.pending:
                    continue
            if monotonic() >= deadline:
                break  # Listing may have consumed the remaining request budget.
            message_id = state.pending[0]
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
                state.pending = state.pending[1:]
                db.commit()  # Atomic acknowledgement; replay is idempotent.
            except HTTPException:
                db.commit()  # Persist a provider-triggered reconnect requirement.
                raise
            except Exception as error:
                db.rollback()
                logger.warning('Gmail source failed: error_type=%s', type(error).__name__)
                result['failed_count'] += 1
                break  # Failed ID remains pending, never silently skipped.

        if not state.pending and state.listing_done:
            missing = []
            if state.mode == 'full':
                missing = db.scalars(select(Email).where(Email.account_id == account_id,
                    or_(Email.sync_generation.is_(None), Email.sync_generation != state.generation))
                    .order_by(Email.id).limit(MESSAGE_LIMIT)).all()
                for email in missing:
                    db.delete(email)
                    result['deleted'] += 1
                db.commit()
            if not missing:
                account.history_id = state.target
                account.last_synced_at = datetime.now(timezone.utc)
                db.delete(state)
                db.commit()
                state = None
        pending = list(db.scalars(select(ProcessingState.email_id).join(Email, Email.id == ProcessingState.email_id)
            .where(Email.account_id == account_id, ProcessingState.status.in_(['failed', 'pending']),
                   ProcessingState.email_id.not_in(processed))
            .distinct().order_by(ProcessingState.email_id).limit(1)))
        for email_id in pending:
            if monotonic() >= deadline:
                break
            email = db.get(Email, email_id)
            failures = process_email(db, email, commit_stages=True, deadline=deadline)
            result['enrichment_failed'] += bool(failures)
        enrichment_pending = db.scalar(select(ProcessingState.id).join(Email, Email.id == ProcessingState.email_id)
            .where(Email.account_id == account_id, ProcessingState.status.in_(['failed', 'pending'])).limit(1)) is not None
        result['has_more'] = state is not None or enrichment_pending
        account.sync_error = 'partial_failure' if result['failed_count'] else None
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


def sync_account(db, account_id):
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
                return _batch(worker, account_id)
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
