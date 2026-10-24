"""Quarantine legacy rows; add identity, encrypted credentials and sync state."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from email.utils import parsedate_to_datetime
from datetime import timezone

revision = 'b3c8d5e024fa'
down_revision = 'a2b7c4d913ef'
branch_labels = depends_on = None


def upgrade():
    op.create_table('app_users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), unique=True, nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table('app_access_tokens',
        sa.Column('digest', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('app_users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_app_access_tokens_user_id', 'app_access_tokens', ['user_id'])
    op.create_table('gmail_accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('app_users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('address', sa.String(320), unique=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('history_id', sa.String(100)),
        sa.Column('last_synced_at', sa.DateTime(timezone=True)),
        sa.Column('sync_error', sa.String(40)))
    op.create_index('ix_gmail_accounts_user_id', 'gmail_accounts', ['user_id'])
    op.create_table('oauth_credentials',
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('gmail_accounts.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('ciphertext', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table('oauth_attempts',
        sa.Column('state_hash', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('app_users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('nonce_hash', sa.String(64), nullable=False),
        sa.Column('verifier', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_oauth_attempts_user_id', 'oauth_attempts', ['user_id'])
    op.add_column('emails', sa.Column('account_id', sa.Integer(), sa.ForeignKey('gmail_accounts.id', name='fk_email_account', ondelete='CASCADE')))
    op.add_column('emails', sa.Column('sent_at', sa.DateTime(timezone=True)))
    op.add_column('emails', sa.Column('message_at', sa.DateTime(timezone=True)))
    op.add_column('emails', sa.Column('date_status', sa.String(20), nullable=False, server_default='missing'))
    op.add_column('emails', sa.Column('raw_payload', JSONB()))
    op.add_column('emails', sa.Column('gmail_labels', JSONB()))
    connection = op.get_bind()
    user = connection.scalar(sa.text("INSERT INTO app_users(name,active) VALUES ('legacy-quarantine',false) RETURNING id"))
    account = connection.scalar(sa.text("INSERT INTO gmail_accounts(user_id,status) VALUES (:u,'quarantine') RETURNING id"), {'u': user})
    connection.execute(sa.text('UPDATE emails SET account_id=:a'), {'a': account})
    # Keep raw headers intact. Never assign a timezone to a naive/invalid date.
    for row in connection.execute(sa.text('SELECT id,email_date FROM emails')):
        parsed, status = None, 'missing'
        if row.email_date:
            try:
                parsed = parsedate_to_datetime(row.email_date)
                if parsed.tzinfo is None:
                    parsed, status = None, 'naive'
                else:
                    parsed, status = parsed.astimezone(timezone.utc), 'parsed'
            except (ValueError, TypeError, OverflowError):
                status = 'invalid'
        connection.execute(sa.text('UPDATE emails SET sent_at=:d,date_status=:s WHERE id=:i'), {'d': parsed, 's': status, 'i': row.id})
    op.alter_column('emails', 'account_id', nullable=False)
    op.drop_index('ix_emails_message_id', table_name='emails')
    op.create_unique_constraint('uq_email_account_message', 'emails', ['account_id', 'message_id'])
    op.create_index('ix_email_account_created', 'emails', ['account_id', 'created_at', 'id'])
    op.create_table('email_processing_states',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email_id', sa.Integer(), sa.ForeignKey('emails.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stage', sa.String(40), nullable=False),
        sa.Column('input_hash', sa.String(64), nullable=False),
        sa.Column('version', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_code', sa.String(40)),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('email_id', 'stage', name='uq_email_processing_stage'))
    op.create_index('ix_email_processing_states_email_id', 'email_processing_states', ['email_id'])


def downgrade():
    connection = op.get_bind()
    # Never silently collapse established multi-user data into an unowned inbox.
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM gmail_accounts WHERE status <> 'quarantine')")):
        raise RuntimeError('Disconnect/export accounts and explicitly resolve ownership before downgrade')
    op.drop_table('email_processing_states')
    op.drop_index('ix_email_account_created', table_name='emails')
    op.drop_constraint('uq_email_account_message', 'emails', type_='unique')
    op.create_index('ix_emails_message_id', 'emails', ['message_id'], unique=True)
    for column in ('gmail_labels', 'raw_payload', 'date_status', 'message_at', 'sent_at', 'account_id'):
        op.drop_column('emails', column)
    for table in ('oauth_attempts', 'oauth_credentials', 'gmail_accounts', 'app_access_tokens', 'app_users'):
        op.drop_table(table)
