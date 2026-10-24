"""Opt-in synthetic PostgreSQL/API benchmark, isolated by conftest's test DB guard.

INBOX_BENCHMARK_OUTPUT=results/.../runtime-performance.json python -m pytest
test_runtime_performance.py -q

Provider and model time is deliberately excluded. This is not a load test.
"""
import json
import math
import os
import platform
import statistics
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from authentication import current_user
from backend_models import AppUser, GmailAccount
from database import get_db
from main import app
from models import Email, EmailPrediction, EmailTask
from ownership import OwnedSession
import gmail_sync
import google_login


@pytest.mark.skipif(not os.getenv('INBOX_BENCHMARK_OUTPUT'), reason='Explicit synthetic benchmark only')
def test_synthetic_runtime_latency(test_database, monkeypatch):
    assert test_database.get_bind().engine.url.database.endswith('_test')
    monkeypatch.setenv('APP_ENV', 'production')
    origin = 'https://inbox.example.invalid'
    monkeypatch.setenv('BROWSER_ORIGIN', origin)
    monkeypatch.setenv('GOOGLE_LOGIN_REDIRECT_URI', origin + '/auth/google/login/callback')
    app.dependency_overrides.pop(current_user)

    def owned_db(principal=Depends(current_user)):
        with OwnedSession(bind=test_database.get_bind(), user_id=principal.id,
                          join_transaction_mode='create_savepoint', autoflush=False) as db:
            yield db
    app.dependency_overrides[get_db] = owned_db

    account = test_database.get(GmailAccount, test_database.info['account_id'])
    account.address = 'benchmark@gmail.com'
    account.history_id = '100'
    other = AppUser(name='benchmark-foreign-user', active=True)
    test_database.add(other)
    test_database.flush()
    foreign = GmailAccount(user_id=other.id, address='foreign@example.invalid', status='connected')
    test_database.add(foreign)
    test_database.flush()
    now = datetime(2026, 10, 15, tzinfo=timezone.utc)
    for tenant_account in (account, foreign):
        for index in range(1000):
            stamp = now - timedelta(hours=index)
            email = Email(account_id=tenant_account.id, message_id='synthetic-' + str(index),
                          subject='Synthetic report ' + str(index), sender='sender@example.invalid',
                          body='Synthetic benchmark text only.', summary='Synthetic summary.',
                          sent_at=stamp, message_at=stamp, created_at=stamp,
                          priority_level='high' if index % 2 else 'low', priority_score=0.6)
            email.predictions = [EmailPrediction(category='Business', confidence=0.9)]
            if index % 10 == 0:
                email.tasks = [EmailTask(task='Submit the requested report.', confidence=0.9,
                                        deadline_date=stamp.date())]
            test_database.add(email)
    test_database.commit()

    claims = dict(sub='benchmark-subject', email='benchmark@gmail.com', email_verified=True)
    serial = 0
    def login_flow(*args):
        nonlocal serial
        serial += 1
        flow = SimpleNamespace(code_verifier='synthetic-verifier', client_config={'client_id': 'synthetic'},
                               oauth2session=SimpleNamespace(token={'id_token': 'synthetic'}),
                               fetch_token=lambda **kwargs: None)
        def authorize(**kwargs):
            claims['nonce'] = kwargs['nonce']
            return 'https://accounts.google.com/o/oauth2/auth', 'state-' + str(serial)
        flow.authorization_url = authorize
        return flow
    monkeypatch.setattr(google_login, 'login_flow', login_flow)
    monkeypatch.setattr(google_login, 'verified_claims', lambda *args: claims)
    service = Mock()
    service.users.return_value.history.return_value.list.return_value.execute.return_value = {'historyId': '100'}
    monkeypatch.setattr(gmail_sync, 'get_gmail_service', lambda *args: service)

    measurements = {}
    def measure(name, operation, validate, samples=30):
        for _ in range(3):
            validate(operation())
        elapsed = []
        for _ in range(samples):
            started = time.perf_counter()
            response = operation()
            elapsed.append((time.perf_counter() - started) * 1000)
            validate(response)
        ordered = sorted(elapsed)
        measurements[name] = dict(n=samples, warmups=3, p50_ms=round(statistics.median(elapsed), 3),
                                  p95_ms=round(ordered[math.ceil(samples * .95) - 1], 3),
                                  max_ms=round(max(elapsed), 3))

    with TestClient(app, base_url=origin, follow_redirects=False) as client:
        def login():
            started = client.post('/auth/google/login/start', headers={'origin': origin})
            assert started.status_code == 200
            state = 'state-' + str(serial)
            return client.get('/auth/google/login/callback', params={'state': state, 'code': 'synthetic'})
        def logged_in(response):
            assert response.status_code == 303 and response.headers['location'] == origin + '/'
        measure('google_login_server_only_mocked_provider', login, logged_in, samples=20)
        def ok(response):
            assert response.status_code == 200
        measure('session_restore', lambda: client.get('/auth/session'), ok)
        def inbox(response):
            ok(response)
            assert response.json()['total'] == 1000 and response.json()['count'] == 20
        measure('inbox_first_page', lambda: client.get('/emails?limit=20'), inbox)
        measure('inbox_later_page', lambda: client.get('/emails?limit=20&offset=800'), inbox)
        def tasks(response):
            ok(response)
            assert response.json()['total'] == 100 and response.json()['count'] == 20
        measure('tasks_first_page', lambda: client.get('/tasks?limit=20'), tasks)
        csrf = client.get('/auth/session').json()['csrf_token']
        def synced(response):
            ok(response)
            assert response.json()['count'] == response.json()['failed_count'] == 0
        measure('gmail_incremental_no_changes_mocked_provider', lambda: client.post(
            f'/gmail/accounts/{account.id}/sync', headers={'origin': origin, 'x-csrf-token': csrf}), synced)

    result = dict(protocol='Single client, sequential TestClient requests and real isolated PostgreSQL; nearest-rank p95.',
                  limitations=['No TLS, nginx, socket network or Google latency.',
                               'Google exchange and verification are mocked; Gmail history is mocked with no changes.',
                               'No model loading, enrichment, Search, Ask, concurrency or capacity guarantee.',
                               'Test DB sessions use an outer rolled-back transaction; production pool contention is excluded.'],
                  seed_data=dict(owned_emails=1000, foreign_emails=1000, owned_tasks=100, foreign_tasks=100),
                  environment=dict(platform=platform.system(), python=platform.python_version()),
                  measurements=measurements, production_modified=False)
    output = Path(os.environ['INBOX_BENCHMARK_OUTPUT']).resolve()
    workspace = Path(__file__).parent.resolve()
    assert output.is_relative_to(workspace), 'Benchmark output must remain in the workspace'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
