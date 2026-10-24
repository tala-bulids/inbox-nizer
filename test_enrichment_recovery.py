from unittest.mock import Mock
from fastapi.testclient import TestClient
from sqlalchemy import select
from main import app
from backend_models import ProcessingState
from models import Email
from test_backend_sync import sync_env
from test_backend_isolation import two_users, owned
import email_pipeline
import gmail_sync


def test_failed_classifier_manual_recovery_persists_without_source_change(sync_env, monkeypatch):
    db, account, service = sync_env
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    classifier = Mock(side_effect=RuntimeError('unavailable'))
    monkeypatch.setattr(email_pipeline, 'classify_email', classifier)
    for _ in range(5):
        gmail_sync.sync_account(db, account)
    assert classifier.call_count == 3
    email = db.query(Email).one()
    source = email.raw_payload
    with TestClient(app) as client:
        assert client.get('/gmail/accounts').json()['accounts'][0]['enrichment_failed_count'] == 1
        response = client.post(f'/emails/{email.id}/retry-enrichment')
        assert response.status_code == 200
        assert response.json()['failed_stages'] == ['classify']
        assert classifier.call_count == 4  # Exactly one explicit retry, no reset.
        gmail_sync.sync_account(db, account)
        assert classifier.call_count == 4
        classifier.side_effect = None
        classifier.return_value = [{'category': 'Business', 'confidence': .9}]
        assert client.post(f'/emails/{email.id}/retry-enrichment').json()['failed_stages'] == []
        data = client.get(f'/emails/{email.id}').json()
        assert data['predictions'][0]['category'] == 'Business'
        assert all(s['status'] in ('complete', 'skipped') for s in data['processing'])
        assert client.get('/gmail/accounts').json()['accounts'][0]['enrichment_failed_count'] == 0
        assert client.post(f'/emails/{email.id}/retry-enrichment').status_code == 200
        assert classifier.call_count == 5  # Completed stages are not rerun.
    db.expire_all()
    assert db.get(Email, email.id).raw_payload == source


def test_retry_cannot_access_other_owner(two_users):
    _, other, _ = two_users
    with TestClient(app) as client:
        assert client.post(f'/emails/{other.id}/retry-enrichment').status_code == 404


def test_other_pending_stage_does_not_restart_exhausted_classifier(sync_env, monkeypatch):
    db, account, _ = sync_env
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    classifier = Mock(side_effect=RuntimeError)
    monkeypatch.setattr(email_pipeline, 'classify_email', classifier)
    for _ in range(3):
        gmail_sync.sync_account(db, account)
    summary = db.scalar(select(ProcessingState).where(ProcessingState.stage == 'summary'))
    summary.status = 'pending'
    db.commit()
    gmail_sync.sync_account(db, account)
    assert classifier.call_count == 3
    db.refresh(summary)
    assert summary.status == 'complete'
