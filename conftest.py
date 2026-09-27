import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from database import get_db, engine as production_engine
from main import app


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


@pytest.fixture(autouse=True)
def test_database():
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

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield db

    finally:
        app.dependency_overrides.clear()

        db.close()

        transaction.rollback()

        connection.close()