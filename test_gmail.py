from unittest.mock import MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def gmail_mocks():
    with (
        patch("routes.get_gmail_service") as get_service,
        patch("routes.extract_email_body") as extract_body,
        patch("routes.classify_email") as classify,
    ):
        messages = get_service.return_value.users.return_value.messages.return_value
        extract_body.side_effect = lambda payload: payload["text"]
        classify.return_value = [{"category": "Personal", "confidence": 0.8}]
        yield messages, extract_body, classify


def fake_email(number):
    return {"payload": {
        "headers": [
            {"name": "Subject", "value": f"Subject {number}"},
            {"name": "fRoM", "value": f"sender{number}@example.com"},
            {"name": "Date", "value": "Sat, 19 Sep 2026 10:00:00 +0300"},
        ],
        "text": f"Clean body {number}",
    }}


def set_messages(messages, count):
    messages.list.return_value.execute.return_value = {
        "messages": [{"id": str(number)} for number in range(1, count + 1)]
    }
    requests = []
    for number in range(1, count + 1):
        request = MagicMock()
        request.execute.return_value = fake_email(number)
        requests.append(request)
    messages.get.side_effect = requests
    return requests


def test_gmail_success(gmail_mocks):
    messages, extract_body, classify = gmail_mocks
    requests = set_messages(messages, 2)

    with TestClient(app) as client:
        response = client.get("/gmail/messages")

    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 2
    assert result["success_count"] == 2
    assert result["failed_count"] == 0
    assert result["emails"] == [
        {
            "id": str(number),
            "from": f"sender{number}@example.com",
            "date": "Sat, 19 Sep 2026 10:00:00 +0300",
            "subject": f"Subject {number}",
            "body": f"Clean body {number}",
            "predictions": [{"category": "Personal", "confidence": 0.8}],
        }
        for number in (1, 2)
    ]
    messages.list.assert_called_once_with(userId="me", maxResults=5)
    assert messages.get.call_args_list == [
        call(userId="me", id=str(number), format="full") for number in (1, 2)
    ]
    for request in requests:
        request.execute.assert_called_once_with()
    assert extract_body.call_args_list == [call(fake_email(n)["payload"]) for n in (1, 2)]
    assert classify.call_args_list == [call(f"Subject {n}", f"Clean body {n}") for n in (1, 2)]


@pytest.mark.parametrize("failure_stage", ["fetch", "extract", "classify"])
def test_gmail_continues_after_message_failure(gmail_mocks, failure_stage):
    messages, extract_body, classify = gmail_mocks
    requests = set_messages(messages, 3)
    internal_error = RuntimeError("Private internal diagnostic: synthetic-test-value")
    prediction = [{"category": "Personal", "confidence": 0.8}]
    if failure_stage == "fetch":
        requests[1].execute.side_effect = internal_error
    elif failure_stage == "extract":
        extract_body.side_effect = ["Clean body 1", internal_error, "Clean body 3"]
    else:
        classify.side_effect = [prediction, internal_error, prediction]

    with TestClient(app) as client:
        response = client.get("/gmail/messages")

    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 3
    assert result["success_count"] == 2
    assert result["failed_count"] == 1
    assert [email["id"] for email in result["emails"]] == ["1", "2", "3"]
    assert result["emails"][0]["predictions"] == prediction
    assert result["emails"][1] == {"id": "2", "error": "Failed to process email"}
    assert result["emails"][2]["predictions"] == prediction
    assert "synthetic-test-value" not in response.text
    assert messages.get.call_count == 3


@pytest.mark.parametrize("listing", [{"messages": []}, {}])
def test_gmail_no_messages(gmail_mocks, listing):
    messages, extract_body, classify = gmail_mocks
    messages.list.return_value.execute.return_value = listing

    with TestClient(app) as client:
        response = client.get("/gmail/messages")

    assert response.status_code == 200
    assert response.json() == {"message": "No emails found"}
    messages.get.assert_not_called()
    extract_body.assert_not_called()
    classify.assert_not_called()
