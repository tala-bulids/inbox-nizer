"""Add provenance-preserving facts and extraction checkpoints."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'a2b7c4d913ef'
down_revision = 'f1a6b3c802de'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('email_fact_states',
        sa.Column('email_id', sa.Integer(), sa.ForeignKey('emails.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('input_hash', sa.String(64), nullable=False),
        sa.Column('extractor_version', sa.String(100), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table('email_facts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email_id', sa.Integer(), sa.ForeignKey('emails.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fact_key', sa.String(64), nullable=False),
        sa.Column('role', sa.String(255), nullable=False),
        sa.Column('source_label', sa.Text(), nullable=False),
        sa.Column('literal_value', sa.Text(), nullable=False),
        sa.Column('normalized_value', JSONB(), nullable=True),
        sa.Column('source_text', sa.Text(), nullable=False),
        sa.Column('source_start', sa.Integer(), nullable=False),
        sa.Column('source_end', sa.Integer(), nullable=False),
        sa.Column('record_start', sa.Integer(), nullable=False),
        sa.Column('record_end', sa.Integer(), nullable=False),
        sa.Column('extraction_reason', sa.String(100), nullable=False),
        sa.Column('extractor_version', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('email_id', 'fact_key', name='uq_email_fact_key'),
        sa.CheckConstraint('source_start >= 0 AND source_end > source_start', name='ck_fact_span'),
        sa.CheckConstraint('record_start >= 0 AND record_start <= source_start AND record_end >= source_end', name='ck_fact_record'))
    op.create_index('ix_email_facts_email_role', 'email_facts', ['email_id', 'role'])


def downgrade():
    op.drop_index('ix_email_facts_email_role', table_name='email_facts')
    op.drop_table('email_facts')
    op.drop_table('email_fact_states')
