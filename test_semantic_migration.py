from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text


def test_semantic_migration_roundtrip_and_hnsw(test_database):
    config = Config()
    config.set_main_option('script_location', str(Path(__file__).parent / 'alembic'))
    scripts = ScriptDirectory.from_config(config)
    migration = scripts.get_revision('f1a6b3c802de')
    assert scripts.get_heads() == ['a2b7c4d913ef']
    assert migration.down_revision == 'e8f3a2b491cd'
    conn = test_database.connection()
    assert conn.engine.url.database.endswith('_test')
    with Operations.context(MigrationContext.configure(conn)):
        migration.module.downgrade()
        assert not inspect(conn).has_table('email_embedding_chunks')
        assert conn.scalar(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")) == 'vector'
        migration.module.upgrade()
    index = conn.scalar(text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_email_chunks_embedding_cosine'"))
    assert 'USING hnsw' in index and 'vector_cosine_ops' in index
    assert 'embedding' not in {column['name'] for column in inspect(conn).get_columns('emails')}
