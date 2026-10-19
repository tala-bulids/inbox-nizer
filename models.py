from datetime import date, datetime
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy import (
    String,
    Text,
    Float,
    DateTime,
    Date,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column,relationship

from database import Base
from pgvector.sqlalchemy import Vector


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint('account_id', 'message_id', name='uq_email_account_message'),
        Index('ix_email_account_created', 'account_id', 'created_at', 'id'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey('gmail_accounts.id', ondelete='CASCADE'), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    date_status: Mapped[str] = mapped_column(String(20), default='missing', server_default='missing')
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    gmail_labels: Mapped[list | None] = mapped_column(JSONB)
    sync_generation: Mapped[str | None] = mapped_column(String(36), deferred=True)

    message_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    sender: Mapped[str] = mapped_column(
        String(500),
        nullable=True
    )

    email_date: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )

    subject: Mapped[str] = mapped_column(
        String(500),
        nullable=True
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )    
    predictions: Mapped[list["EmailPrediction"]] = relationship(
    back_populates="email",
    cascade="all, delete-orphan"
    )
    tasks: Mapped[list["EmailTask"]] = relationship(
        back_populates="email", cascade="all, delete-orphan", order_by="EmailTask.id"
    )
    priority_score: Mapped[float | None] = mapped_column(
     Float,
     nullable=True,
     index=True
    )

    priority_level: Mapped[str | None] = mapped_column(
     String(20),
     nullable=True,
     index=True
    )    
    
class EmailPrediction(Base):
    __tablename__ = "email_predictions"
    __table_args__ = (
    UniqueConstraint(
        "email_id",
        "category",
        name="uq_email_prediction_email_category"
    ),
)

    id: Mapped[int] = mapped_column(primary_key=True)

    email_id: Mapped[int] = mapped_column(
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    email: Mapped["Email"] = relationship(
        back_populates="predictions"
    )    

class EmailTask(Base):
    __tablename__ = "email_tasks"
    __table_args__ = (
        UniqueConstraint("email_id", "task", name="uq_email_task_email_task"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email_id: Mapped[int] = mapped_column(
        ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    deadline_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    email: Mapped["Email"] = relationship(back_populates="tasks")


class EmailEmbeddingChunk(Base):
    __tablename__ = 'email_embedding_chunks'
    __table_args__ = (
        UniqueConstraint('email_id', 'chunk_index', 'embedding_model', name='uq_email_chunk_model'),
        CheckConstraint('chunk_index >= 0', name='ck_email_chunk_index'),
        Index('ix_email_chunks_embedding_cosine', 'embedding', postgresql_using='hnsw',
              postgresql_ops={'embedding': 'vector_cosine_ops'},
              postgresql_with={'m': 16, 'ef_construction': 64}),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email_id: Mapped[int] = mapped_column(ForeignKey('emails.id', ondelete='CASCADE'), index=True)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Facts reference the stored body, independently of embedding chunk lifetimes.


class EmailFactState(Base):
    __tablename__ = 'email_fact_states'
    email_id: Mapped[int] = mapped_column(ForeignKey('emails.id', ondelete='CASCADE'), primary_key=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


import backend_models  # Register ownership tables in Alembic metadata.


class EmailFact(Base):
    __tablename__ = 'email_facts'
    __table_args__ = (
        UniqueConstraint('email_id', 'fact_key', name='uq_email_fact_key'),
        CheckConstraint('source_start >= 0 AND source_end > source_start', name='ck_fact_span'),
        CheckConstraint('record_start >= 0 AND record_start <= source_start AND record_end >= source_end', name='ck_fact_record'),
        Index('ix_email_facts_email_role', 'email_id', 'role'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    email_id: Mapped[int] = mapped_column(ForeignKey('emails.id', ondelete='CASCADE'), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    source_label: Mapped[str] = mapped_column(Text, nullable=False)
    literal_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_start: Mapped[int] = mapped_column(nullable=False)
    source_end: Mapped[int] = mapped_column(nullable=False)
    record_start: Mapped[int] = mapped_column(nullable=False)
    record_end: Mapped[int] = mapped_column(nullable=False)
    extraction_reason: Mapped[str] = mapped_column(String(100), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
