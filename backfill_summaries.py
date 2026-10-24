from sqlalchemy import or_, select

from database import SessionLocal
from models import Email
from summarizer import summarize_email


def backfill_summaries():
    db = SessionLocal()
    try:
        emails = db.scalars(select(Email).where(
            or_(Email.summary.is_(None), Email.summary == '')
        ))
        updated = 0
        for email in emails:
            email.summary = summarize_email(email.subject or '', email.body or '')
            updated += 1
        db.commit()
        print(f'Updated {updated} emails')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    backfill_summaries()
