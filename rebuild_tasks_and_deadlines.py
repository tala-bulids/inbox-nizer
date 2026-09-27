"""Manual rebuild of tasks and deadlines; other email data stays unchanged."""
from sqlalchemy import select

from database import SessionLocal
from deadline_extractor import parse_email_datetime
from models import Email, EmailTask
from task_extractor import extract_action_items


def rebuild_tasks_and_deadlines():
    db = SessionLocal()
    processed = added = deadlines = 0
    try:
        emails = db.scalars(select(Email).order_by(Email.id).execution_options(yield_per=100))
        for email in emails:
            items = extract_action_items(email.subject or '', email.body or '', parse_email_datetime(email.email_date))
            email.tasks.clear()
            db.flush()
            email.tasks.extend(EmailTask(**item) for item in items)
            processed += 1
            added += len(items)
            deadlines += sum(bool(item['deadline_text'] or item['deadline_date'] or item['deadline_at']) for item in items)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print(f'Processed {processed} emails')
    print(f'Added {added} tasks')
    print(f'Tasks with deadlines {deadlines}')


if __name__ == '__main__':
    rebuild_tasks_and_deadlines()
