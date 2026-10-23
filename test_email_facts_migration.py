from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from test_semantic_index import saved_email
from fact_store import refresh_facts


def test_facts_migration_upgrade_downgrade_preserves_parent(test_database):
    config = Config()
    config.set_main_option('script_location', str(Path(__file__).parent / 'alembic'))
    scripts = ScriptDirectory.from_config(config)
    migration = scripts.get_revision('a2b7c4d913ef')
    assert scripts.get_heads() == ['e6fb80357cd1']
    assert migration.down_revision == 'f1a6b3c802de'
    email = saved_email(test_database, body='status: Under review')
    refresh_facts(email, test_database)
    conn = test_database.connection()
    assert conn.engine.url.database.endswith('_test')
    with Operations.context(MigrationContext.configure(conn)):
        migration.module.downgrade()
        assert not inspect(conn).has_table('email_facts')
        assert not inspect(conn).has_table('email_fact_states')
        assert conn.scalar(text('SELECT body FROM emails WHERE id=:id'), {'id':email.id}) == 'status: Under review'
        assert inspect(conn).has_table('email_embedding_chunks')
        migration.module.upgrade()
    assert inspect(conn).has_table('email_facts')
    assert 'uq_email_fact_key' in {x['name'] for x in inspect(conn).get_unique_constraints('email_facts')}
    assert 'ix_email_facts_email_role' in {x['name'] for x in inspect(conn).get_indexes('email_facts')}
