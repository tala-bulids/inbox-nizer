import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from models import Email, EmailTask


def test_deadline_migration_is_nullable_and_preserves_rows(test_database):
    path = Path(__file__).parent / 'alembic/versions/d7e9f2a310bc_add_task_deadlines.py'
    spec = importlib.util.spec_from_file_location('deadline_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    email = Email(message_id='migration-regression')
    email.tasks = [EmailTask(task='Keep this task', confidence=0.8)]
    test_database.add(email)
    test_database.flush()
    task_id = email.tasks[0].id
    connection = test_database.connection()
    assert connection.engine.url.database.endswith('_test')
    columns = {'deadline_text', 'deadline_date', 'deadline_at', 'deadline_confidence'}
    with Operations.context(MigrationContext.configure(connection)):
        migration.downgrade()
        assert not columns & {c['name'] for c in inspect(connection).get_columns('email_tasks')}
        assert connection.scalar(text('SELECT task FROM email_tasks WHERE id=:id'), {'id': task_id}) == 'Keep this task'
        migration.upgrade()
    metadata = {c['name']: c for c in inspect(connection).get_columns('email_tasks')}
    assert all(metadata[name]['nullable'] for name in columns)
    test_database.expire_all()
    assert email.tasks[0].task == 'Keep this task'
    assert all(getattr(email.tasks[0], name) is None for name in columns)
