from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch

client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "message": "inbox-nizer API is running"
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
@patch('routes.classify_email', return_value=[{'category': 'Job Application', 'confidence': 0.8}])
def test_classify_valid_email(classifier):
    response = client.post(
        "/classify-email",
        json={
            "subject": "Interview Invitation",
            "body": "We would like to invite you for an interview next Monday."
        }
    )

    assert response.status_code == 200
    assert "predictions" in response.json()
    assert len(response.json()["predictions"]) == 1
def test_classification_error():
    with patch("routes.classify_email", side_effect=Exception("test error")):
        response = client.post(
            "/classify-email",
            json={
                "subject": "Test",
                "body": "Test email"
            }
        )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Email classification failed"
    }
