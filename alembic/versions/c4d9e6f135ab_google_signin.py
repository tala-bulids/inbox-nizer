"""Separate Google application identity from Gmail mailbox consent."""
from alembic import op
import sqlalchemy as sa
revision = 'c4d9e6f135ab'
down_revision = 'b3c8d5e024fa'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('google_identities',
        sa.Column('subject', sa.String(255), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('app_users.id', ondelete='CASCADE'), nullable=False, unique=True))
    op.create_table('google_login_attempts',
        sa.Column('state_hash', sa.String(64), primary_key=True),
        sa.Column('browser_hash', sa.String(64), nullable=False),
        sa.Column('nonce_hash', sa.String(64), nullable=False),
        sa.Column('verifier', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table('google_login_attempts')
    op.drop_table('google_identities')
