from database import SessionLocal
from models import Email
from priority import calculate_priority


def backfill_priorities():
    db = SessionLocal()

    try:
        emails = db.query(Email).all()

        updated = 0

        for email in emails:
            predictions = [
                {
                    "category": prediction.category,
                    "confidence": prediction.confidence
                }
                for prediction in email.predictions
            ]

            priority = calculate_priority(predictions)

            email.priority_score = priority["priority_score"]
            email.priority_level = priority["priority_level"]

            updated += 1

        db.commit()

        print(f"Updated {updated} emails")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    backfill_priorities()