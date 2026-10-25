"""Persist bounded Gmail sync continuation. Run only with the migration owner."""
from alembic import op
import sqlalchemy as sa

revision = 'd5ea7f246bc0'
down_revision = 'c4d9e6f135ab'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('emails', sa.Column('sync_generation', sa.String(36), nullable=True))
    op.create_table('gmail_sync_states',
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('gmail_accounts.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('generation', sa.String(36), nullable=False),
        sa.Column('mode', sa.String(20), nullable=False),
        sa.Column('anchor', sa.String(100)), sa.Column('target', sa.String(100)),
        sa.Column('page_token', sa.Text()), sa.Column('pending', sa.JSON(), nullable=False),
        sa.Column('listing_done', sa.Boolean(), nullable=False))


def downgrade():
    # Dropping a partial scan would lose its continuation. Finish or explicitly
    # abandon jobs before an operator downgrade; original email columns survive.
    if op.get_bind().scalar(sa.text('SELECT count(*) FROM gmail_sync_states')):
        raise RuntimeError('Finish or abandon pending sync jobs before downgrade')
    op.drop_table('gmail_sync_states')
    op.drop_column('emails', 'sync_generation')
