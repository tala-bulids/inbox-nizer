import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from database import get_db
from main import app


load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not configured"
    )

database_name = make_url(TEST_DATABASE_URL).database

if not database_name.endswith("_test"):
    raise RuntimeError(
        "Tests must use a test database"
    )


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