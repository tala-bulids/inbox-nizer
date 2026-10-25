"""Add normalized email tasks.

Revision ID: c4d8e1f206ab
Revises: b9c7d2e4a610
"""
from alembic import op
import sqlalchemy as sa

revision = 'c4d8e1f206ab'
down_revision = 'b9c7d2e4a610'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'email_tasks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email_id', sa.Integer(), sa.ForeignKey('emails.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('email_id', 'task', name='uq_email_task_email_task'),
    )
    op.create_index('ix_email_tasks_email_id', 'email_tasks', ['email_id'])


def downgrade():
    op.drop_index('ix_email_tasks_email_id', table_name='email_tasks')
    op.drop_table('email_tasks')
