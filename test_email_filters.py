from fastapi.testclient import TestClient

from main import app
from models import Email


client = TestClient(app)


def test_filter_emails_by_priority(test_database):
    high_email = Email(
        message_id="priority-high-test",
        sender="high@example.com",
        subject="High priority email",
        body="Important email",
        priority_score=0.9,
        priority_level="high"
    )

    low_email = Email(
        message_id="priority-low-test",
        sender="low@example.com",
        subject="Low priority email",
        body="Newsletter",
        priority_score=0.2,
        priority_level="low"
    )

    test_database.add_all([
        high_email,
        low_email
    ])
    test_database.commit()

    response = client.get(
        "/emails?priority_level=high"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1
    assert data["emails"][0]["message_id"] == "priority-high-test"
    assert data["emails"][0]["priority_level"] == "high"