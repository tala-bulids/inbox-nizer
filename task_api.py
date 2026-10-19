"""Read-only tasks from owned emails; no extraction or new persistence."""
from datetime import date, datetime
from typing import Literal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, cast, DateTime
from sqlalchemy.orm import Session
from authentication import current_user, Principal
from backend_models import GmailAccount
from database import get_db
from models import Email, EmailTask

router = APIRouter()


class TaskEmail(BaseModel):
    id: int
    subject: str | None
    sender: str | None
    date: str | None
    sent_at: datetime | None
    message_at: datetime | None


class TaskItem(BaseModel):
    id: int
    task: str
    deadline_text: str | None
    deadline_date: date | None
    deadline_at: datetime | None
    created_at: datetime
    email: TaskEmail


class TaskPage(BaseModel):
    count: int
    total: int
    limit: int
    offset: int
    tasks: list[TaskItem]


@router.get('/tasks', response_model=TaskPage)
def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    has_deadline: bool | None = None,
    sort_order: Literal['asc', 'desc'] = 'desc',
    principal: Principal = Depends(current_user),
    db: Session = Depends(get_db),
):
    # Scope both page and total before ordering or pagination.
    query = (db.query(EmailTask, Email.id, Email.subject, Email.sender,
                      Email.email_date, Email.sent_at, Email.message_at)
             .join(Email, Email.id == EmailTask.email_id)
             .join(GmailAccount, GmailAccount.id == Email.account_id)
             .filter(GmailAccount.user_id == principal.id))
    deadline = or_(EmailTask.deadline_date.is_not(None), EmailTask.deadline_at.is_not(None),
                   func.coalesce(EmailTask.deadline_text, '') != '')
    if has_deadline is not None:
        query = query.filter(deadline if has_deadline else ~deadline)
    total = query.with_entities(func.count(EmailTask.id)).scalar()
    order = EmailTask.id.asc() if sort_order == 'asc' else EmailTask.id.desc()
    task_date = func.coalesce(EmailTask.deadline_at, func.timezone('UTC', cast(EmailTask.deadline_date, DateTime())))
    date_order = task_date.asc() if sort_order == 'asc' else task_date.desc()
    rows = query.order_by(date_order.nulls_last(), order).limit(limit).offset(offset).all()
    items = [TaskItem(id=task.id, task=task.task, deadline_text=task.deadline_text,
                     deadline_date=task.deadline_date, deadline_at=task.deadline_at,
                     created_at=task.created_at,
                     email=TaskEmail(id=email_id, subject=subject, sender=sender, date=raw_date,
                                     sent_at=sent_at, message_at=message_at))
             for task, email_id, subject, sender, raw_date, sent_at, message_at in rows]
    return TaskPage(count=len(items), total=total, limit=limit, offset=offset, tasks=items)
