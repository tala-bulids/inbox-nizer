"""Add nullable task deadlines.

Revision ID: d7e9f2a310bc
Revises: c4d8e1f206ab
"""
from alembic import op
import sqlalchemy as sa

revision = 'd7e9f2a310bc'
down_revision = 'c4d8e1f206ab'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('email_tasks', sa.Column('deadline_text', sa.Text(), nullable=True))
    op.add_column('email_tasks', sa.Column('deadline_date', sa.Date(), nullable=True))
    op.add_column('email_tasks', sa.Column('deadline_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('email_tasks', sa.Column('deadline_confidence', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('email_tasks', 'deadline_confidence')
    op.drop_column('email_tasks', 'deadline_at')
    op.drop_column('email_tasks', 'deadline_date')
    op.drop_column('email_tasks', 'deadline_text')
