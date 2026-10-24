"""Persist the recent-import scope without changing existing checkpoints/mail."""
from alembic import op
import sqlalchemy as sa

revision = 'e6fb80357cd1'
down_revision = 'd5ea7f246bc0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('gmail_sync_states', sa.Column('import_query', sa.String(100), nullable=True))


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT count(*) FROM gmail_sync_states WHERE import_query IS NOT NULL')):
        raise RuntimeError('Finish scoped Gmail imports before downgrade')
    op.drop_column('gmail_sync_states', 'import_query')
