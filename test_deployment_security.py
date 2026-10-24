"""Operational probes and privacy boundaries use synthetic inputs only."""
import asyncio
import json
from contextlib import contextmanager
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import deployment_health
from backend_config import ConfigurationError
from main import app
from privacy_middleware import PrivateQueryMiddleware


def test_validation_errors_do_not_echo_rejected_private_input():
    private = 'PRIVATE_MAILBOX_CONTENT'
    with TestClient(app) as client:
        response = client.post('/ask', json={'question': {'private': private}})
    assert response.status_code == 422
    assert response.json() == {'detail': 'Invalid request'}
    assert private not in response.text
    assert response.headers['cache-control'] == 'no-store'


def test_unexpected_errors_do_not_reach_response_or_server_logs(caplog):
    private = 'PRIVATE_PROVIDER_CREDENTIAL'
    async def failing(scope, receive, send):
        assert scope['query_string'] == b'q=PRIVATE_QUERY'
        raise RuntimeError(private)
    output = []
    async def send(message):
        output.append(message)
    scope = {'type': 'http', 'method': 'GET', 'path': '/test', 'query_string': b'q=PRIVATE_QUERY', 'headers': []}
    asyncio.run(PrivateQueryMiddleware(failing)(scope, None, send))
    assert scope['query_string'] == b''
    assert output[0]['status'] == 500
    assert (b'cache-control', b'no-store') in output[0]['headers']
    assert private not in str(output) + caplog.text
    assert 'PRIVATE_QUERY' not in caplog.text
    assert 'RuntimeError' in caplog.text


def test_probes_disclose_no_private_configuration(monkeypatch):
    monkeypatch.setattr(deployment_health, 'validate_production_configuration', lambda: None)
    monkeypatch.setattr(deployment_health, 'database_is_ready', lambda: True)
    with TestClient(app) as client:
        assert client.get('/health/live').json() == {'status': 'alive'}
        assert client.get('/health/ready').json() == {'status': 'ready'}
        monkeypatch.setattr(deployment_health, 'database_is_ready', Mock(side_effect=RuntimeError('SECRET_DATABASE_URL')))
        result = client.get('/health/ready')
        assert result.status_code == 503 and result.json() == {'status': 'unavailable'}
        assert 'SECRET' not in result.text
        assert client.get('/health/live').status_code == 200


@pytest.mark.parametrize('revision,role,expected', [
    ('head', (False,) * 10, True),
    ('old', (False,) * 10, False),
    *[('head', tuple(index == unsafe for index in range(10)), False) for unsafe in range(10)],
])
def test_readiness_requires_current_schema_and_limited_role(monkeypatch, revision, role, expected):
    connection = Mock()
    connection.scalar.return_value = revision
    connection.execute.return_value.one.return_value = role
    @contextmanager
    def connect():
        yield connection
    monkeypatch.setattr(deployment_health, 'engine', Mock(connect=connect))
    monkeypatch.setattr(deployment_health, 'expected_schema_revision', lambda: 'head')
    assert deployment_health.database_is_ready() is expected
    statements = [str(call.args[0]).lstrip() for call in connection.scalar.call_args_list + connection.execute.call_args_list]
    assert all(statement.startswith('SELECT') for statement in statements)
    role_query = statements[-1]
    assert "'USAGE'" not in role_query
    assert role_query.count("'MEMBER'") == 4
    assert 'admin_member' in role_query and 'owns_schema' in role_query


@pytest.mark.parametrize('issue', ['callback_origin', 'insecure_transport', 'client_file'])
def test_production_readiness_rejects_insecure_configuration(monkeypatch, tmp_path, issue):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('BROWSER_ORIGIN', 'https://inbox.example.invalid')
    monkeypatch.setenv('GOOGLE_REDIRECT_URI', 'https://inbox.example.invalid/api/auth/google/callback')
    monkeypatch.setenv('GOOGLE_LOGIN_REDIRECT_URI', 'https://inbox.example.invalid/api/auth/google/login/callback')
    monkeypatch.delenv('OAUTHLIB_INSECURE_TRANSPORT', raising=False)
    client_file = tmp_path / 'client.json'
    client_file.write_text(json.dumps({'web': dict(client_id='synthetic', client_secret='synthetic', auth_uri='https://accounts.google.com/o/oauth2/auth', token_uri='https://oauth2.googleapis.com/token')}))
    monkeypatch.setenv('GOOGLE_CLIENT_FILE', str(client_file))
    deployment_health.validate_production_configuration()
    if issue == 'callback_origin':
        monkeypatch.setenv('GOOGLE_LOGIN_REDIRECT_URI', 'https://other.example.invalid/api/auth/google/login/callback')
    elif issue == 'insecure_transport':
        monkeypatch.setenv('OAUTHLIB_INSECURE_TRANSPORT', '1')
    else:
        client_file.write_text('{}')
    with pytest.raises(ConfigurationError):
        deployment_health.validate_production_configuration()
