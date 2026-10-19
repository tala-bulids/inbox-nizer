"""Durability, cursor fencing and bounded work against isolated PostgreSQL."""
from unittest.mock import Mock
from uuid import uuid4
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend_models import AppUser, GmailAccount, GmailSyncState, ProcessingState
from models import Email
from ownership import OwnedSession, OwnershipError
from test_backend_sync import sync_env, message, http_error
import gmail_sync
import email_pipeline


def test_many_messages_resume_without_relisting_or_duplicates(sync_env, monkeypatch):
    db, account, service = sync_env
    monkeypatch.setattr(gmail_sync, 'MESSAGE_LIMIT', 2)
    service.users().messages().list.return_value.execute.return_value = {'messages': [{'id': f'm{i}'} for i in range(5)]}
    assert gmail_sync.sync_account(db, account)['has_more']
    assert db.get(GmailAccount, account).history_id is None
    assert len(db.get(GmailSyncState, account).pending) == 3
    assert gmail_sync.sync_account(db, account)['has_more']
    assert not gmail_sync.sync_account(db, account)['has_more']
    assert db.query(Email).count() == 5
    assert db.get(GmailAccount, account).history_id == '100'
    service.users().messages().list.assert_called_once()


def test_interruption_after_source_commit_is_recoverable(sync_env, monkeypatch):
    db, account, _ = sync_env
    original = gmail_sync.process_email
    monkeypatch.setattr(gmail_sync, 'process_email', Mock(side_effect=KeyboardInterrupt))
    with pytest.raises(KeyboardInterrupt):
        gmail_sync.sync_account(db, account)
    assert db.query(Email).count() == 1
    assert db.get(GmailAccount, account).history_id is None
    assert db.get(GmailSyncState, account).pending == ['m1']
    monkeypatch.setattr(gmail_sync, 'process_email', original)
    assert not gmail_sync.sync_account(db, account)['has_more']
    assert db.query(Email).count() == 1
    assert all(s.status == 'complete' for s in db.scalars(select(ProcessingState)))


def test_history_cursor_waits_for_all_pages(sync_env, monkeypatch):
    db, account, service = sync_env
    gmail_sync.sync_account(db, account)
    monkeypatch.setattr(gmail_sync, 'PAGE_LIMIT', 1)
    history = service.users().history().list.return_value.execute
    history.side_effect = [
        {'historyId': '200', 'nextPageToken': 'page-two', 'history': [{'messages': [{'id': 'm2'}]}]},
        {'historyId': '250', 'history': [{'messages': [{'id': 'm3'}]}]},
    ]
    assert gmail_sync.sync_account(db, account)['has_more']
    assert db.get(GmailAccount, account).history_id == '100'
    assert not gmail_sync.sync_account(db, account)['has_more']
    assert db.get(GmailAccount, account).history_id == '250'
    assert service.users().history().list.call_args.kwargs['startHistoryId'] == '100'


def test_page_failure_and_expiration_keep_safe_cursor(sync_env, monkeypatch):
    db, account, service = sync_env
    gmail_sync.sync_account(db, account)
    monkeypatch.setattr(gmail_sync, 'PAGE_LIMIT', 1)
    history = service.users().history().list.return_value.execute
    history.side_effect = [{'historyId': '200', 'nextPageToken': 'expired'}, http_error(503), http_error(400), {'historyId': '300'}]
    assert gmail_sync.sync_account(db, account)['has_more']
    with pytest.raises(HTTPException):
        gmail_sync.sync_account(db, account)
    assert db.get(GmailSyncState, account).page_token == 'expired'
    assert db.get(GmailAccount, account).history_id == '100'
    assert gmail_sync.sync_account(db, account)['has_more']
    assert db.get(GmailSyncState, account).page_token is None
    assert not gmail_sync.sync_account(db, account)['has_more']
    assert db.get(GmailAccount, account).history_id == '300'


def test_expiry_after_partial_history_refetches_previously_seen_message(sync_env, monkeypatch):
    db, account, service = sync_env
    gmail_sync.sync_account(db, account)
    monkeypatch.setattr(gmail_sync, 'PAGE_LIMIT', 1)
    service.users().history().list.return_value.execute.side_effect = [
        {'historyId':'200','nextPageToken':'later','history':[{'messages':[{'id':'m1'}]}]},
        http_error(404)]
    gmail_sync.sync_account(db, account)
    generation=db.get(GmailSyncState, account).generation
    gmail_sync.sync_account(db, account)
    assert db.get(GmailSyncState, account).generation != generation
    service.users().messages().get.return_value.execute.return_value=message('Please upload the new document.')
    gmail_sync.sync_account(db, account)
    assert 'new document' in db.query(Email).one().body


def test_reconciliation_is_bounded_and_not_before_scan_end(sync_env, monkeypatch):
    db, account, service = sync_env
    for i in range(6):
        db.add(Email(account_id=account, message_id=f'old-{i}', body='Preserved until complete scan'))
    db.commit()
    monkeypatch.setattr(gmail_sync, 'MESSAGE_LIMIT', 2)
    service.users().messages().list.return_value.execute.return_value = {}
    for remaining in (4, 2, 0):
        result = gmail_sync.sync_account(db, account)
        assert result['deleted'] == 2 and result['has_more']
        assert db.query(Email).count() == remaining
        assert db.get(GmailAccount, account).history_id is None
    assert not gmail_sync.sync_account(db, account)['has_more']
    assert db.get(GmailAccount, account).history_id == '100'


def test_checkpoint_isolation_and_foreign_sync_rejection(sync_env, test_database, monkeypatch):
    db, account, service = sync_env
    monkeypatch.setattr(gmail_sync, 'MESSAGE_LIMIT', 1)
    service.users().messages().list.return_value.execute.return_value = {'messages': [{'id': 'm1'}, {'id': 'm2'}]}
    gmail_sync.sync_account(db, account)
    foreign = AppUser(name='other-batch-user', active=True)
    test_database.add(foreign); test_database.flush()
    with OwnedSession(bind=test_database.get_bind(), user_id=foreign.id, join_transaction_mode='create_savepoint') as other:
        assert other.get(GmailSyncState, account) is None
        with pytest.raises(HTTPException) as error:
            gmail_sync.sync_account(other, account)
        assert error.value.status_code == 404
        other.add(GmailSyncState(account_id=account, generation='foreign', mode='full', pending=[], listing_done=False))
        with pytest.raises(OwnershipError):
            other.flush()
        other.rollback()


def test_real_commits_release_transactions_during_provider_and_models(test_database, monkeypatch):
    # Separate committed test-only principal exercises the actual Engine path,
    # rather than the outer-transaction fixture's SAVEPOINT approximation.
    from conftest import test_engine
    assert test_engine.url.database.endswith('_test')
    with Session(test_engine) as admin:
        user = AppUser(name='batch-engine-' + str(uuid4()), active=True)
        admin.add(user); admin.flush()
        account = GmailAccount(user_id=user.id, status='connected')
        admin.add(account); admin.commit()
        user_id, account_id = user.id, account.id
    current = {}
    service = Mock()
    def outside(value):
        assert not current['db'].in_transaction()
        assert not current['db'].get_bind().in_transaction()
        return value
    def connect(db, account):
        current['db'] = db
        return service
    monkeypatch.setattr(gmail_sync, 'get_gmail_service', connect)
    monkeypatch.setattr(email_pipeline, 'classify_email', lambda *args: outside([{'category': 'Business', 'confidence': .9}]))
    monkeypatch.setattr(email_pipeline, 'summarize_email', lambda *args: outside('Synthetic summary'))
    import embedding_service
    original_embed = embedding_service.embed_passages
    monkeypatch.setattr(embedding_service, 'embed_passages', lambda values: original_embed(outside(values)))
    service.users().getProfile.return_value.execute.side_effect = lambda **k: outside({'historyId': '100'})
    service.users().messages().list.return_value.execute.side_effect = lambda **k: outside({'messages': [{'id': 'm1'}]})
    service.users().messages().get.return_value.execute.side_effect = lambda **k: outside(message())
    try:
        with OwnedSession(bind=test_engine, user_id=user_id) as db:
            result = gmail_sync.sync_account(db, account_id)
            assert result['success_count'] == 1 and not result['has_more']
        with test_engine.connect() as c:
            assert c.scalar(text('SELECT pg_try_advisory_xact_lock(724193, :a)'), {'a': account_id})
    finally:
        with Session(test_engine) as admin:
            admin.delete(admin.get(AppUser, user_id)); admin.commit()


def test_stage_budget_persists_retry_without_model_call(sync_env, monkeypatch):
    db, account, _ = sync_env
    from email_pipeline import store_message, process_email
    email = store_message(db, db.get(GmailAccount, account), 'budget', message())
    db.commit()
    classify = Mock()
    monkeypatch.setattr(email_pipeline, 'classify_email', classify)
    process_email(db, email, commit_stages=True, deadline=0)
    classify.assert_not_called()
    assert db.scalar(select(ProcessingState).where(ProcessingState.email_id==email.id)).status == 'pending'


def test_bounded_sync_migration_and_downgrade_guard():
    from pathlib import Path
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from conftest import test_engine
    config=Config();config.set_main_option('script_location',str(Path(__file__).parent/'alembic'))
    scripts=ScriptDirectory.from_config(config)
    with test_engine.connect() as c:
        tx=c.begin()
        try:
            c.execute(text('CREATE SCHEMA sync_migration_test'))
            c.execute(text('SET LOCAL search_path TO sync_migration_test, public'))
            with Operations.context(MigrationContext.configure(c)):
                for revision in reversed(list(scripts.walk_revisions(base='base',head='c4d9e6f135ab'))):
                    revision.module.upgrade()
                migration=scripts.get_revision('d5ea7f246bc0').module
                migration.upgrade()
                c.execute(text("INSERT INTO gmail_sync_states(account_id,generation,mode,pending,listing_done) SELECT id,'test','full','[]',false FROM gmail_accounts LIMIT 1"))
                with pytest.raises(RuntimeError,match='pending sync'):
                    migration.downgrade()
                c.execute(text('DELETE FROM gmail_sync_states'))
                migration.downgrade()
                migration.upgrade()
                assert c.scalar(text('SELECT count(*) FROM gmail_sync_states'))==0
        finally:
            tx.rollback()


def test_bounded_batch_measurement(sync_env, monkeypatch):
    import json,os,time
    from pathlib import Path
    output=os.getenv('SYNC_BENCHMARK_OUTPUT')
    if not output:
        pytest.skip('Explicit bounded synthetic benchmark only')
    db,account,service=sync_env
    service.users().messages().list.return_value.execute.return_value={'messages':[{'id':f'bench-{i}'} for i in range(12)]}
    samples=[]
    for _ in range(4):
        start=time.perf_counter();result=gmail_sync.sync_account(db,account)
        samples.append(dict(seconds=round(time.perf_counter()-start,4),count=result['count'],has_more=result['has_more']))
        assert result['count']<=gmail_sync.MESSAGE_LIMIT
        if not result['has_more']:break
    assert db.query(Email).count()==12 and not result['has_more']
    path=Path(output).resolve()
    assert path.is_relative_to(Path(__file__).parent.resolve())
    path.write_text(json.dumps(dict(samples=samples,provider='mocked',models='test doubles',
        database='isolated PostgreSQL',production_changed=False),indent=2),encoding='utf-8')
