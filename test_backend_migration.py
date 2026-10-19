"""Historical Alembic chain in an isolated, transaction-rolled-back test schema."""
from pathlib import Path
from datetime import timezone
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
import pytest
from conftest import test_engine


def test_legacy_upgrade_and_downgrade_preserves_source_and_children():
    config = Config()
    config.set_main_option('script_location', str(Path(__file__).parent / 'alembic'))
    scripts = ScriptDirectory.from_config(config)
    with test_engine.connect() as c:
        transaction = c.begin()
        try:
            c.execute(text('CREATE SCHEMA hardening_migration_test'))
            c.execute(text('SET LOCAL search_path TO hardening_migration_test, public'))
            with Operations.context(MigrationContext.configure(c)):
                for revision in reversed(list(scripts.walk_revisions(base='base', head='a2b7c4d913ef'))):
                    revision.module.upgrade()
                c.execute(text("INSERT INTO emails(id,message_id,email_date,body) VALUES (901,'legacy-valid','Wed, 16 Sep 2026 10:00:00 +0300','Original body'), (902,'legacy-invalid','unparseable','Keep body')"))
                c.execute(text("INSERT INTO email_tasks(email_id,task,confidence) VALUES (901,'Keep task',0.9)"))
                c.execute(text("INSERT INTO email_fact_states(email_id,input_hash,extractor_version) VALUES (901,'original-hash','facts-v2-relations')"))
                c.execute(text("INSERT INTO email_facts(email_id,fact_key,role,source_label,literal_value,source_text,source_start,source_end,record_start,record_end,extraction_reason,extractor_version) VALUES (901,'kept','status','Status','body','Original body',0,13,0,13,'literal','facts-v2-relations')"))
                c.execute(text("INSERT INTO email_embedding_chunks(email_id,chunk_index,chunk_text,embedding,embedding_model,content_hash) VALUES (901,0,'Original body',CAST(:v AS vector),'fixture','kept')"), {'v': str([0.0] * 384)})
                migration = scripts.get_revision('b3c8d5e024fa').module
                migration.upgrade()
                row = c.execute(text('SELECT e.id,e.body,e.email_date,e.sent_at,e.message_at,e.date_status,u.active,a.status FROM emails e JOIN gmail_accounts a ON a.id=e.account_id JOIN app_users u ON u.id=a.user_id WHERE e.id=901')).one()
                assert row.id == 901 and row.body == 'Original body'
                assert row.sent_at.astimezone(timezone.utc).hour == 7 and row.sent_at.tzinfo is not None
                assert row.email_date == 'Wed, 16 Sep 2026 10:00:00 +0300'
                assert row.message_at is None and row.date_status == 'parsed'
                assert row.active is False and row.status == 'quarantine'
                invalid = c.execute(text('SELECT email_date,sent_at,date_status FROM emails WHERE id=902')).one()
                assert tuple(invalid) == ('unparseable', None, 'invalid')
                assert c.scalar(text('SELECT count(*) FROM email_tasks')) == 1
                assert c.scalar(text('SELECT input_hash FROM email_fact_states')) == 'original-hash'
                assert c.scalar(text('SELECT count(*) FROM email_facts')) == 1
                assert c.scalar(text('SELECT count(*) FROM email_embedding_chunks')) == 1
                migration.downgrade()
                assert c.scalar(text('SELECT count(*) FROM emails')) == 2
                assert c.scalar(text('SELECT body FROM emails WHERE id=901')) == 'Original body'
                assert c.scalar(text('SELECT count(*) FROM email_tasks')) == 1
                assert c.scalar(text('SELECT count(*) FROM email_facts')) == 1
                assert c.scalar(text('SELECT count(*) FROM email_embedding_chunks')) == 1
                migration.upgrade()
                assert c.scalar(text('SELECT count(*) FROM emails')) == 2
                c.execute(text("UPDATE gmail_accounts SET status='connected'"))
                with pytest.raises(RuntimeError, match='resolve ownership'):
                    migration.downgrade()
        finally:
            transaction.rollback()


def test_legacy_claim_requires_verified_account(test_database):
    from backend_admin import claim_legacy
    from backend_models import GmailAccount
    account = test_database.get(GmailAccount, test_database.info['account_id'])
    account.status = 'disconnected'
    test_database.flush()
    with pytest.raises(ValueError, match='First connect'):
        claim_legacy(test_database, account.id)


def test_explicit_legacy_claim_preserves_ids_and_facts(test_database):
    from backend_admin import claim_legacy
    from backend_models import GmailAccount
    from models import Email, EmailFactState
    from sqlalchemy import select
    source = test_database.scalar(select(GmailAccount).where(GmailAccount.status == 'quarantine'))
    email = Email(account_id=source.id, message_id='legacy-claim', body='Preserved')
    test_database.add(email)
    test_database.flush()
    ident = email.id
    test_database.add(EmailFactState(email_id=ident, input_hash='same', extractor_version='same'))
    test_database.flush()
    assert claim_legacy(test_database, test_database.info['account_id']) == 1
    test_database.expire_all()
    assert test_database.get(Email, ident).body == 'Preserved'
    assert test_database.get(EmailFactState, ident).input_hash == 'same'
