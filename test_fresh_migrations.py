"""Verify a new installation using an empty, transaction-isolated test schema."""
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import inspect


def test_complete_migration_chain_from_empty_schema(test_database):
    connection = test_database.connection()
    assert connection.engine.url.database.endswith('_test')
    schema = 'fresh_' + uuid4().hex
    connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}", public')
    config = Config()
    config.set_main_option('script_location', str(Path(__file__).parent / 'alembic'))
    scripts = ScriptDirectory.from_config(config)
    with Operations.context(MigrationContext.configure(connection)):
        for revision in reversed(list(scripts.walk_revisions())):
            revision.module.upgrade()
    tables = set(inspect(connection).get_table_names(schema=schema))
    assert {'emails', 'email_predictions', 'email_tasks', 'email_embedding_chunks',
            'email_facts', 'app_users', 'gmail_accounts', 'google_identities',
            'gmail_sync_states'} <= tables
    assert 'account_id' in {c['name'] for c in inspect(connection).get_columns('emails', schema=schema)}
    # The surrounding test transaction rolls back schema, rows and search_path.
