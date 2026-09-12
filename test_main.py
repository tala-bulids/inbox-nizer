from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "message": "AI Smart Inbox API is running"
    }
def test_empty_email():
    response = client.post(
        "/classify-email",
        json={
            "subject": "",
            "body": ""
        }
    )

    assert response.status_code == 422    
def test_classify_valid_email():
    response = client.post(
        "/classify-email",
        json={
            "subject": "Interview Invitation",
            "body": "We would like to invite you for an interview next Monday."
        }
    )

    assert response.status_code == 200
    assert "predictions" in response.json()    