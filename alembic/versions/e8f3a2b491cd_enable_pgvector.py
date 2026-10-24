"""Enable pgvector.

Revision ID: e8f3a2b491cd
Revises: d7e9f2a310bc
"""
from alembic import op

revision = 'e8f3a2b491cd'
down_revision = 'd7e9f2a310bc'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')


def downgrade():
    # The extension may predate this migration or be used by other objects.
    pass
