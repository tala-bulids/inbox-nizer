"""Render sync uses real PostgreSQL state/locks and synthetic Gmail messages."""
import builtins
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from backend_models import AppUser, GmailAccount, GmailSyncState, ProcessingState
from models import Email, EmailEmbeddingChunk
from ownership import OwnedSession
from test_backend_sync import sync_env, message, http_error
import email_pipeline
import embedding_service
import gmail_sync
import semantic_index


@pytest.fixture(autouse=True)
def full_by_default(monkeypatch):
    monkeypatch.delenv('INBOX_RUNTIME_PROFILE', raising=False)


def states(db, email_id):
    return {row.stage: row for row in db.scalars(select(ProcessingState).where(
        ProcessingState.email_id == email_id))}


def block_models(monkeypatch):
    calls = []
    for module, name in ((email_pipeline, 'index_email'),
                         (semantic_index, 'prepare_index'),
                         (embedding_service, '_load_encoder')):
        spy = Mock(side_effect=AssertionError('Sync must not load a model'))
        monkeypatch.setattr(module, name, spy)
        calls.append(spy)
    return calls


def test_render_free_keeps_light_stages_without_model_imports(sync_env, monkeypatch):
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    spies = block_models(monkeypatch)
    imported = []
    original_import = builtins.__import__

    def guard(name, *args, **kwargs):
        if name.split('.')[0] in {'torch', 'transformers', 'sentence_transformers', 'llama_cpp'}:
            imported.append(name)
            raise AssertionError('Heavy import during Render sync')
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', guard)
    db, account, _ = sync_env
    result = gmail_sync.sync_account(db, account)
    assert result['success_count'] == 1
    assert result['enrichment_failed'] == 0 and not result['has_more']
    email = db.query(Email).one()
    assert email.raw_payload == message()['payload']
    assert email.body and email.summary and email.tasks
    rows = states(db, email.id)
    assert {name for name, row in rows.items() if row.status == 'complete'} == {
        'clean', 'classify', 'summary', 'tasks', 'facts'}
    for name in ('embedding',):
        assert rows[name].status == 'skipped'
        assert rows[name].error_code == 'runtime_disabled'
        assert rows[name].attempts == 0
    assert not imported
    for spy in spies:
        spy.assert_not_called()
    # Repeated incremental sync must not retry the disabled stages forever.
    assert not gmail_sync.sync_account(db, account)['has_more']


@pytest.mark.parametrize('old_status', ['pending', 'failed'])
def test_old_heavy_work_becomes_terminal_without_new_mail(sync_env, monkeypatch, old_status):
    db, account, _ = sync_env
    gmail_sync.sync_account(db, account)
    email = db.query(Email).one()
    source = email.raw_payload
    predictions = [(p.category, p.confidence) for p in email.predictions]
    chunk_ids = list(db.scalars(select(EmailEmbeddingChunk.id)))
    rows = states(db, email.id)
    attempts = {name: rows[name].attempts for name in ('embedding',)}
    for name in attempts:
        rows[name].status = old_status
        rows[name].error_code = 'stage_unavailable'
    db.commit()
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    spies = block_models(monkeypatch)
    assert not gmail_sync.sync_account(db, account)['has_more']
    db.refresh(email)
    assert email.raw_payload == source
    assert [(p.category, p.confidence) for p in email.predictions] == predictions
    assert list(db.scalars(select(EmailEmbeddingChunk.id))) == chunk_ids
    for name, attempts_before in attempts.items():
        row = states(db, email.id)[name]
        assert row.status == 'skipped' and row.attempts == attempts_before
    for spy in spies:
        spy.assert_not_called()


def test_disabled_stages_terminal_even_when_budget_expired(sync_env, monkeypatch):
    db, account, _ = sync_env
    email = email_pipeline.store_message(db, db.get(GmailAccount, account), 'budget', message())
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    spies = block_models(monkeypatch)
    email_pipeline.process_email(db, email, commit_stages=True, deadline=0)
    rows = states(db, email.id)
    assert rows['clean'].status == 'pending'  # Genuine work can resume.
    assert all(rows[name].status == 'skipped' for name in ('embedding',))
    assert email.raw_payload == message()['payload']
    email_pipeline.process_email(db, email, commit_stages=True)
    assert not any(row.status in {'failed', 'pending'} for row in states(db, email.id).values())
    for spy in spies:
        spy.assert_not_called()


@pytest.mark.parametrize('profile', [None, 'full'])
def test_full_and_default_still_classify_and_embed(sync_env, monkeypatch, profile):
    if profile is not None:
        monkeypatch.setenv('INBOX_RUNTIME_PROFILE', profile)
    classify = Mock(wraps=email_pipeline.classify_email)
    prepare = Mock(wraps=semantic_index.prepare_index)
    monkeypatch.setattr(email_pipeline, 'classify_email', classify)
    monkeypatch.setattr(semantic_index, 'prepare_index', prepare)
    db, account, _ = sync_env
    assert not gmail_sync.sync_account(db, account)['has_more']
    classify.assert_called_once()
    prepare.assert_called_once()
    assert all(row.status == 'complete' for row in states(db, db.query(Email).one().id).values())


def test_switching_back_to_full_processes_skipped_stages(sync_env, monkeypatch):
    db, account, _ = sync_env
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    gmail_sync.sync_account(db, account)
    email = db.query(Email).one()
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'full')
    classify = Mock(wraps=email_pipeline.classify_email)
    prepare = Mock(wraps=semantic_index.prepare_index)
    monkeypatch.setattr(email_pipeline, 'classify_email', classify)
    monkeypatch.setattr(semantic_index, 'prepare_index', prepare)
    assert email_pipeline.process_email(db, email, commit_stages=True) == []
    classify.assert_not_called()
    prepare.assert_called_once()
    assert all(row.status == 'complete' for row in states(db, email.id).values())


def test_render_batch_stays_bounded_and_resumes(sync_env, monkeypatch):
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    db, account, service = sync_env
    size = gmail_sync.MESSAGE_LIMIT + 1
    service.users().messages().list.return_value.execute.return_value = {
        'messages': [{'id': f'm{i}'} for i in range(size)]}
    result = gmail_sync.sync_account(db, account)
    assert result['count'] == gmail_sync.MESSAGE_LIMIT and result['has_more']
    assert len(db.get(GmailSyncState, account).pending) == 1
    assert not gmail_sync.sync_account(db, account)['has_more']
    assert db.query(Email).count() == size


def test_expired_budget_after_listing_does_not_fetch_body(sync_env, monkeypatch):
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    db, account, service = sync_env
    now = [0]
    monkeypatch.setattr(gmail_sync, 'monotonic', lambda: now[0])

    def page(**kwargs):
        now[0] = gmail_sync.TIME_BUDGET + 1
        return {'messages': [{'id': 'm1'}]}

    service.users().messages().list.return_value.execute.side_effect = page
    result = gmail_sync.sync_account(db, account)
    assert result['count'] == 0 and result['has_more']
    assert db.get(GmailSyncState, account).pending == ['m1']
    service.users().messages().get.assert_not_called()


@pytest.mark.parametrize('outcome', ['success', 'provider_exception', 'timeout', 'interrupt', 'sql_error'])
def test_real_engine_releases_lock_and_connection(test_database, monkeypatch, outcome):
    from conftest import test_engine
    assert test_engine.url.database.endswith('_test')
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    service = Mock()
    service.users().getProfile.return_value.execute.return_value = {'historyId': '100'}
    service.users().messages().list.return_value.execute.return_value = {'messages': [{'id': 'm1'}]}
    service.users().messages().get.return_value.execute.return_value = message()
    monkeypatch.setattr(gmail_sync, 'get_gmail_service', lambda *args: service)
    monkeypatch.setattr(email_pipeline, 'classify_email', lambda *args: [{'category': 'Business', 'confidence': .9}])
    with Session(test_engine) as admin:
        user = AppUser(name='render-lock-' + str(uuid4()), active=True)
        admin.add(user)
        admin.flush()
        account = GmailAccount(user_id=user.id, status='connected')
        admin.add(account)
        admin.commit()
        user_id, account_id = user.id, account.id
    baseline = test_engine.pool.checkedout()
    try:
        if outcome == 'provider_exception':
            service.users().getProfile.return_value.execute.side_effect = http_error(503)
        elif outcome == 'timeout':
            service.users().messages().get.return_value.execute.side_effect = TimeoutError()
        elif outcome == 'interrupt':
            monkeypatch.setattr(gmail_sync, 'process_email', Mock(side_effect=KeyboardInterrupt))
        elif outcome == 'sql_error':
            def aborted_transaction(worker, account_id, retry_failed=False):
                worker.get_bind().execute(text('SELECT 1 / 0'))
            monkeypatch.setattr(gmail_sync, '_batch', aborted_transaction)
        with OwnedSession(bind=test_engine, user_id=user_id) as db:
            if outcome in {'provider_exception', 'interrupt', 'sql_error'}:
                error = {'provider_exception': HTTPException, 'interrupt': KeyboardInterrupt,
                         'sql_error': DBAPIError}[outcome]
                with pytest.raises(error):
                    gmail_sync.sync_account(db, account_id)
            else:
                result = gmail_sync.sync_account(db, account_id)
                assert result['failed_count'] == (1 if outcome == 'timeout' else 0)
                assert result['has_more'] == (outcome == 'timeout')
        assert test_engine.pool.checkedout() == baseline
        with test_engine.connect() as connection:
            # Checking pg_locks also catches a lock returned to the pool on the
            # same backend (where reentrant pg_try_advisory_lock would succeed).
            assert connection.scalar(text("""SELECT count(*) FROM pg_locks
                WHERE locktype = 'advisory' AND classid = 724193 AND objid = :account
                AND objsubid = 2 AND database = (SELECT oid FROM pg_database
                    WHERE datname = current_database())"""), {'account': account_id}) == 0
            assert connection.scalar(text('SELECT pg_try_advisory_xact_lock(724193, :account)'),
                                     {'account': account_id})
    finally:
        with Session(test_engine) as admin:
            admin.delete(admin.get(AppUser, user_id))
            admin.commit()


@pytest.mark.parametrize('phase', ['acquire', 'unlock', 'unlock_cancel', 'unlock_false'])
def test_uncertain_lock_connections_are_invalidated(monkeypatch, phase):
    db = Mock(user_id=1)
    db.scalar.return_value = 1
    engine = Mock(spec=Engine)
    connection = Mock()
    engine.connect.return_value.__enter__ = Mock(return_value=connection)
    engine.connect.return_value.__exit__ = Mock(return_value=False)
    db.get_bind.return_value = engine
    error = KeyboardInterrupt() if phase == 'unlock_cancel' else TimeoutError()
    connection.scalar.side_effect = [error] if phase == 'acquire' else [True, False if phase == 'unlock_false' else error]
    worker = Mock()
    worker.__enter__ = Mock(return_value=worker)
    worker.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(gmail_sync, 'OwnedSession', Mock(return_value=worker))
    monkeypatch.setattr(gmail_sync, '_batch', Mock(return_value={'has_more': False}))
    if phase in {'acquire', 'unlock_cancel'}:
        with pytest.raises(type(error)):
            gmail_sync.sync_account(db, 1)
    else:
        assert gmail_sync.sync_account(db, 1) == {'has_more': False}
    connection.invalidate.assert_called_once()
