from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text


def test_pgvector_migration_enables_type_and_is_idempotent(test_database):
    config = Config()
    config.set_main_option('script_location', str(Path(__file__).parent / 'alembic'))
    scripts = ScriptDirectory.from_config(config)
    revision = scripts.get_revision('e8f3a2b491cd')
    assert revision.revision in {item.revision for item in scripts.walk_revisions()}
    assert revision.down_revision == 'd7e9f2a310bc'

    connection = test_database.connection()
    assert connection.engine.url.database.endswith('_test')
    tables_before = inspect(connection).get_table_names()
    extension_before = connection.scalar(text("SELECT oid FROM pg_extension WHERE extname = 'vector'"))
    with Operations.context(MigrationContext.configure(connection)):
        revision.module.upgrade()
        extension_after = connection.scalar(text("SELECT oid FROM pg_extension WHERE extname = 'vector'"))
        assert extension_after is not None
        if extension_before is not None:
            assert extension_after == extension_before
        assert connection.scalar(text("SELECT vector_dims('[1,2,3]'::vector)")) == 3
        revision.module.upgrade()
        assert connection.scalar(text("SELECT oid FROM pg_extension WHERE extname = 'vector'")) == extension_after
        revision.module.downgrade()
        assert connection.scalar(text("SELECT vector_dims('[1,2,3]'::vector)")) == 3
    assert inspect(connection).get_table_names() == tables_before
    # The existing fixture rolls back extension creation with the test transaction.
