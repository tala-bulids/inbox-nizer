import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from database import get_db, engine as production_engine
from main import app
from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.migration import MigrationContext
from alembic.operations import Operations
import embedding_service
from embedding_test_fakes import FakeEncoder


load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not configured"
    )

database_name = make_url(TEST_DATABASE_URL).database

production_database_name = make_url(os.environ["DATABASE_URL"]).database

if (not database_name or not database_name.endswith("_test")
        or database_name == production_database_name):
    raise RuntimeError(
        "Tests must use a test database"
    )


@event.listens_for(production_engine, "do_connect")
def block_production_connection(*args, **kwargs):
    raise RuntimeError("Production database connections are disabled in tests")


test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True
)


@pytest.fixture(scope='session')
def semantic_test_schema():
    # Only the validated _test database receives schema setup.
    config = Config()
    config.set_main_option('script_location', str(Path(__file__).parent / 'alembic'))
    scripts = ScriptDirectory.from_config(config)
    with test_engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            if not inspect(connection).has_table('emails'):
                for revision in reversed(list(scripts.walk_revisions())):
                    revision.module.upgrade()
                return
            scripts.get_revision('e8f3a2b491cd').module.upgrade()
            if not inspect(connection).has_table('email_embedding_chunks'):
                scripts.get_revision('f1a6b3c802de').module.upgrade()
            if not inspect(connection).has_table('email_facts'):
                scripts.get_revision('a2b7c4d913ef').module.upgrade()
            if not inspect(connection).has_table('app_users'):
                scripts.get_revision('b3c8d5e024fa').module.upgrade()
            if not inspect(connection).has_table('google_identities'):
                scripts.get_revision('c4d9e6f135ab').module.upgrade()
            if not inspect(connection).has_table('gmail_sync_states'):
                scripts.get_revision('d5ea7f246bc0').module.upgrade()


@pytest.fixture(autouse=True)
def fake_embedding_encoder(monkeypatch):
    fake = FakeEncoder()
    monkeypatch.setattr(embedding_service, '_encoder', None)
    monkeypatch.setattr(embedding_service, '_load_encoder', lambda: fake)
    return fake


@pytest.fixture(autouse=True)
def fake_rag_token_budget(monkeypatch):
    # Never load a real GGUF in tests.
    from types import SimpleNamespace
    from local_llm import _qwen_prompt
    fake = SimpleNamespace(context_size=2048, max_new_tokens=256,
        count_tokens=lambda messages: len(_qwen_prompt(messages).encode('utf-8')) // 3 + 1)
    monkeypatch.setattr('rag_budget.get_budget', lambda: fake)
    return fake


@pytest.fixture(autouse=True)
def test_database(semantic_test_schema, monkeypatch):
    connection = test_engine.connect()

    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    db = TestingSessionLocal()
    from backend_models import AppUser, GmailAccount
    from models import Email
    from authentication import current_user, auth_session, Principal
    from ownership import OwnedSession
    from cryptography.fernet import Fernet
    monkeypatch.setenv('OAUTH_TOKEN_KEYS', Fernet.generate_key().decode())
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/google/callback')
    user = AppUser(name='fixture-user', active=True)
    db.add(user)
    db.flush()
    account = GmailAccount(user_id=user.id, address='fixture@example.invalid', status='connected')
    db.add(account)
    db.commit()
    db.info.update(user_id=user.id, account_id=account.id)

    @event.listens_for(db, 'before_flush')
    def assign_fixture_account(session, context, instances):
        for obj in session.new:
            if isinstance(obj, Email) and obj.account_id is None:
                obj.account_id = account.id

    def override_get_db():
        with OwnedSession(bind=connection, user_id=user.id, autoflush=False,
                          join_transaction_mode='create_savepoint') as owned:
            yield owned

    app.dependency_overrides[current_user] = lambda: Principal(user.id)
    app.dependency_overrides[auth_session] = lambda: db

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield db

    finally:
        app.dependency_overrides.clear()

        db.close()

        transaction.rollback()

        connection.close()
