"""Add semantic email chunks and a cosine HNSW index.

Revision ID: f1a6b3c802de
Revises: e8f3a2b491cd
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = 'f1a6b3c802de'
down_revision = 'e8f3a2b491cd'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'email_embedding_chunks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email_id', sa.Integer(), sa.ForeignKey('emails.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(384), nullable=False),
        sa.Column('embedding_model', sa.String(255), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('email_id', 'chunk_index', 'embedding_model', name='uq_email_chunk_model'),
        sa.CheckConstraint('chunk_index >= 0', name='ck_email_chunk_index'),
    )
    op.create_index('ix_email_embedding_chunks_email_id', 'email_embedding_chunks', ['email_id'])
    op.create_index('ix_email_chunks_embedding_cosine', 'email_embedding_chunks', ['embedding'],
                    postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'},
                    postgresql_with={'m': 16, 'ef_construction': 64})


def downgrade():
    op.drop_index('ix_email_chunks_embedding_cosine', table_name='email_embedding_chunks')
    op.drop_index('ix_email_embedding_chunks_email_id', table_name='email_embedding_chunks')
    op.drop_table('email_embedding_chunks')
