"""Recent import, existing checkpoint preservation and classification integration."""
from datetime import datetime, timezone
from unittest.mock import Mock
import pytest
from sqlalchemy import select
from backend_models import GmailAccount, GmailSyncState, ProcessingState
from models import Email
from test_backend_sync import sync_env, message, http_error
import gmail_sync
import email_pipeline


def test_bad_source_does_not_block_other_ids_but_cursor_stays_safe(sync_env):
    db, account, service = sync_env
    service.users().messages().list.return_value.execute.return_value = {'messages': [{'id':'bad'}, {'id':'good'}]}
    service.users().messages().get.return_value.execute.side_effect = [ValueError('malformed'), message()]
    result = gmail_sync.sync_account(db, account)
    assert result['success_count'] == 1 and result['failed_count'] == 1
    assert db.get(GmailSyncState, account).pending == ['bad']
    assert db.get(GmailAccount, account).history_id is None
    assert db.query(Email).one().message_id == 'good'
    service.users().messages().get.return_value.execute.side_effect = None
    service.users().messages().get.return_value.execute.return_value = message()
    assert not gmail_sync.sync_account(db, account)['has_more']
    assert db.query(Email).count() == 2


def test_recent_import_scope_is_persisted_and_never_reconciles_old_mail(sync_env, monkeypatch):
    db, account, service = sync_env
    monkeypatch.setenv('GMAIL_INITIAL_SYNC_DAYS', '90')
    monkeypatch.setattr(gmail_sync, 'MESSAGE_LIMIT', 1)
    old = Email(account_id=account, message_id='preserved-archive', body='Existing original')
    db.add(old); db.commit()
    service.users().messages().list.return_value.execute.return_value = {'messages': [{'id':'m1'}, {'id':'m2'}]}
    assert gmail_sync.sync_account(db, account)['has_more']
    state = db.get(GmailSyncState, account)
    query = state.import_query
    assert query.startswith('after:')
    age = datetime.now(timezone.utc).timestamp() - int(query.split(':')[1])
    assert 89 * 86400 < age < 91 * 86400
    assert service.users().messages().list.call_args.kwargs['q'] == query
    monkeypatch.setenv('GMAIL_INITIAL_SYNC_DAYS', '7')
    assert not gmail_sync.sync_account(db, account)['has_more']
    assert db.get(Email, old.id).body == 'Existing original'
    assert db.get(GmailAccount, account).history_id == '100'
    assert not gmail_sync.sync_account(db, account)['has_more']
    assert service.users().messages().list.call_count == 1
    assert service.users().history().list.call_args.kwargs['startHistoryId'] == '100'


def test_existing_legacy_checkpoint_continues_without_new_scope(sync_env, monkeypatch):
    db, account, service = sync_env
    monkeypatch.setattr(gmail_sync, 'MESSAGE_LIMIT', 1)
    service.users().messages().list.return_value.execute.return_value = {'messages': [{'id':'m1'}, {'id':'m2'}]}
    gmail_sync.sync_account(db, account)
    saved = db.get(GmailSyncState, account)
    generation = saved.generation
    assert saved.import_query is None
    monkeypatch.setenv('GMAIL_INITIAL_SYNC_DAYS', '90')
    assert not gmail_sync.sync_account(db, account)['has_more']
    assert db.query(Email).count() == 2
    assert all(e.sync_generation == generation for e in db.scalars(select(Email)))
    service.users().messages().list.assert_called_once()


def test_expired_history_recovers_recent_mail_without_deleting_archive(sync_env, monkeypatch):
    db, account, service = sync_env
    gmail_sync.sync_account(db, account)
    monkeypatch.setenv('GMAIL_INITIAL_SYNC_DAYS', '90')
    service.users().history().list.return_value.execute.side_effect = http_error(404)
    assert gmail_sync.sync_account(db, account)['has_more']
    assert db.get(GmailAccount, account).history_id == '100'
    assert db.get(GmailSyncState, account).import_query.startswith('after:')
    service.users().getProfile.return_value.execute.return_value = {'historyId':'200'}
    service.users().messages().list.return_value.execute.return_value = {'messages': [{'id':'new'}]}
    assert not gmail_sync.sync_account(db, account)['has_more']
    assert db.query(Email).count() == 2
    assert db.get(GmailAccount, account).history_id == '200'


def test_render_free_classifies_through_existing_entrypoint_without_torch(sync_env, monkeypatch):
    import predict
    import onnx_classifier
    import builtins
    db, account, _ = sync_env
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    monkeypatch.delenv('CLASSIFIER_RUNTIME', raising=False)
    monkeypatch.setattr(email_pipeline, 'classify_email', predict.classify_email)
    onnx = Mock(return_value=[{'category':'Business','confidence':.9}])
    monkeypatch.setattr(onnx_classifier, 'classify', onnx)
    original = builtins.__import__
    def guard(name, *args, **kwargs):
        assert name.split('.')[0] not in {'torch', 'transformers', 'sentence_transformers'}
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guard)
    result = gmail_sync.sync_account(db, account)
    assert result['success_count'] == 1 and not result['enrichment_failed']
    onnx.assert_called_once()
    assert db.query(Email).one().predictions[0].category == 'Business'


def test_classifier_failure_does_not_block_other_messages_or_cursor_and_retries_are_bounded(sync_env, monkeypatch):
    db, account, service = sync_env
    classify = Mock(side_effect=RuntimeError('private'))
    monkeypatch.setattr(email_pipeline, 'classify_email', classify)
    service.users().messages().list.return_value.execute.return_value = {'messages': [{'id':'m1'}, {'id':'m2'}]}
    result = gmail_sync.sync_account(db, account)
    assert result['success_count'] == 2 and result['enrichment_failed'] == 2
    assert db.query(Email).count() == 2
    assert db.get(GmailAccount, account).history_id == '100'
    for _ in range(5):
        result = gmail_sync.sync_account(db, account)
    assert not result['has_more']
    assert classify.call_count == 6
    assert all(row.status == 'failed' and row.attempts == 3 for row in db.scalars(
        select(ProcessingState).where(ProcessingState.stage == 'classify')))


def test_scoped_migration_preserves_existing_checkpoint_and_guards_downgrade():
    from pathlib import Path
    from sqlalchemy import text
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from conftest import test_engine
    config = Config(); config.set_main_option('script_location', str(Path(__file__).parent/'alembic'))
    scripts = ScriptDirectory.from_config(config)
    with test_engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text('CREATE SCHEMA recent_import_test'))
            connection.execute(text('SET LOCAL search_path TO recent_import_test, public'))
            with Operations.context(MigrationContext.configure(connection)):
                for revision in reversed(list(scripts.walk_revisions(base='base', head='d5ea7f246bc0'))):
                    revision.module.upgrade()
                connection.execute(text("INSERT INTO gmail_sync_states(account_id,generation,mode,pending,listing_done) SELECT id,'saved','full','[\"old-id\"]',false FROM gmail_accounts LIMIT 1"))
                migration = scripts.get_revision('e6fb80357cd1').module
                migration.upgrade()
                assert connection.scalar(text('SELECT import_query IS NULL FROM gmail_sync_states'))
                assert connection.scalar(text('SELECT generation FROM gmail_sync_states')) == 'saved'
                connection.execute(text("UPDATE gmail_sync_states SET import_query='after:1'"))
                with pytest.raises(RuntimeError): migration.downgrade()
                connection.execute(text('UPDATE gmail_sync_states SET import_query=NULL'))
                migration.downgrade()
        finally:
            transaction.rollback()
