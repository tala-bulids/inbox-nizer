"""Add optional email summary.

Revision ID: b9c7d2e4a610
Revises: 83258085a489
"""
from alembic import op
import sqlalchemy as sa

revision = 'b9c7d2e4a610'
down_revision = '83258085a489'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('emails', sa.Column('summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('emails', 'summary')
