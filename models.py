from datetime import date, datetime

from sqlalchemy import (
    String,
    Text,
    Float,
    DateTime,
    Date,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column,relationship

from database import Base


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True)

    message_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
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
