"""Run manually to refresh stored bodies, summaries, and tasks in one transaction."""
from sqlalchemy import select

from database import SessionLocal
from email_utils import clean_email_text
from models import Email, EmailTask
from summarizer import summarize_email
from task_extractor import extract_action_items
from deadline_extractor import parse_email_datetime


def reprocess_email_content():
    db = SessionLocal()
    processed = cleaned = regenerated = 0
    try:
        emails = db.scalars(select(Email).order_by(Email.id).execution_options(yield_per=100))
        for email in emails:
            body = clean_email_text(email.body or '', subject=email.subject or '')
            # Whitespace alone does not require a body update.
            if ' '.join(body.split()) != ' '.join((email.body or '').split()):
                email.body = body
                cleaned += 1
            email.summary = summarize_email(email.subject or '', body)
            tasks = extract_action_items(email.subject or '', body, parse_email_datetime(email.email_date))
            email.tasks.clear()
            # Delete old tasks before inserting matching task text.
            db.flush()
            email.tasks.extend(EmailTask(**task) for task in tasks)
            regenerated += len(tasks)
            processed += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print(f'Processed {processed} emails')
    print(f'Cleaned {cleaned} bodies')
    print(f'Regenerated {regenerated} tasks')


if __name__ == '__main__':
    reprocess_email_content()
