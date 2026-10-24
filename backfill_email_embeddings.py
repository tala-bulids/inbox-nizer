"""Manual embedding backfill. Nothing runs when this module is imported."""
from database import SessionLocal
from semantic_index import index_all_emails


def main():
    db = SessionLocal()
    try:
        counts = index_all_emails(db, progress=lambda email_id, totals:
                                  print(f"Processed {totals['processed']} emails (latest id {email_id})"))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print(f"Processed {counts['processed']} emails")
    print(f"Created {counts['created']} chunks")
    print(f"Updated {counts['updated']} chunks")
    print(f"Skipped {counts['skipped']} unchanged chunks")
    print(f"Deleted {counts['deleted']} stale chunks")
    return counts


if __name__ == '__main__':
    main()
