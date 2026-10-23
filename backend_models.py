"""Application identity and account-owned operational state."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class AppUser(Base):
    __tablename__ = 'app_users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccessToken(Base):
    __tablename__ = 'app_access_tokens'
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('app_users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GmailAccount(Base):
    __tablename__ = 'gmail_accounts'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('app_users.id', ondelete='CASCADE'), index=True)
    address: Mapped[str | None] = mapped_column(String(320), unique=True)
    status: Mapped[str] = mapped_column(String(30), default='disconnected')
    history_id: Mapped[str | None] = mapped_column(String(100))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_error: Mapped[str | None] = mapped_column(String(40))


class OAuthCredential(Base):
    __tablename__ = 'oauth_credentials'
    account_id: Mapped[int] = mapped_column(ForeignKey('gmail_accounts.id', ondelete='CASCADE'), primary_key=True)
    ciphertext: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GmailSyncState(Base):
    __tablename__ = 'gmail_sync_states'
    account_id: Mapped[int] = mapped_column(ForeignKey('gmail_accounts.id', ondelete='CASCADE'), primary_key=True)
    generation: Mapped[str] = mapped_column(String(36))
    mode: Mapped[str] = mapped_column(String(20))
    anchor: Mapped[str | None] = mapped_column(String(100))
    target: Mapped[str | None] = mapped_column(String(100))
    page_token: Mapped[str | None] = mapped_column(Text)
    pending: Mapped[list] = mapped_column(JSON, default=list)
    listing_done: Mapped[bool] = mapped_column(Boolean, default=False)
    import_query: Mapped[str | None] = mapped_column(String(100))


class OAuthAttempt(Base):
    __tablename__ = 'oauth_attempts'
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('app_users.id', ondelete='CASCADE'), index=True)
    nonce_hash: Mapped[str] = mapped_column(String(64))
    verifier: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProcessingState(Base):
    __tablename__ = 'email_processing_states'
    __table_args__ = (UniqueConstraint('email_id', 'stage', name='uq_email_processing_stage'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    email_id: Mapped[int] = mapped_column(ForeignKey('emails.id', ondelete='CASCADE'), index=True)
    stage: Mapped[str] = mapped_column(String(40))
    input_hash: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20))
    error_code: Mapped[str | None] = mapped_column(String(40))
    attempts: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GoogleIdentity(Base):
    __tablename__ = 'google_identities'
    subject: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('app_users.id', ondelete='CASCADE'), unique=True)


class GoogleLoginAttempt(Base):
    __tablename__ = 'google_login_attempts'
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    browser_hash: Mapped[str] = mapped_column(String(64))
    nonce_hash: Mapped[str] = mapped_column(String(64))
    verifier: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
