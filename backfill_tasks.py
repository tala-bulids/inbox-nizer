from sqlalchemy import select

from database import SessionLocal
from models import Email, EmailTask
from task_extractor import extract_action_items
from deadline_extractor import parse_email_datetime


def backfill_tasks():
    db = SessionLocal()
    try:
        emails = db.scalars(select(Email).where(~Email.tasks.any()))
        processed = added = 0
        for email in emails:
            processed += 1
            for task in extract_action_items(email.subject or '', email.body or '', parse_email_datetime(email.email_date)):
                email.tasks.append(EmailTask(**task))
                added += 1
        db.commit()
        print(f'Processed {processed} emails')
        print(f'Added {added} tasks')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    backfill_tasks()
