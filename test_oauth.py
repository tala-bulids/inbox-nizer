"""Exercise the real OAuth library with synthetic credentials and a fake token server."""
import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from google_auth_oauthlib.flow import Flow
from requests import Response, Request
from unittest.mock import mock_open
import account_routes
from backend_models import OAuthAttempt, OAuthCredential, GmailAccount
from backend_config import decrypt
from authentication import digest
from sqlalchemy import select
from unittest.mock import Mock
from requests_oauthlib import OAuth2Session

from main import app
from gmail_auth import REDIRECT_URI


@pytest.fixture
def oauth_client(monkeypatch):
    # Keep the real token file safe.
    service = Mock()
    service.users.return_value.getProfile.return_value.execute.return_value = {"emailAddress": "oauth@example.invalid"}
    monkeypatch.setattr(account_routes, "build", lambda *a, **k: service)
    config = {"web": {
        "client_id": "test-client",
        "client_secret": "test-secret",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [REDIRECT_URI],
    }}

    def fake_config_file(filename, scopes, **kwargs):
        return Flow.from_client_config(config, scopes=scopes, **kwargs)

    monkeypatch.setattr(Flow, "from_client_secrets_file", fake_config_file)
    with TestClient(app, base_url="http://localhost:8000") as client:
        yield client


def begin_login(client):
    response = client.get("/auth/google", follow_redirects=False)
    assert response.status_code == 307
    return response, parse_qs(urlparse(response.headers["location"]).query)


def test_oauth_pkce_survives_callback(oauth_client, monkeypatch, test_database):
    response, query = begin_login(oauth_client)
    attempt = test_database.get(OAuthAttempt, digest(query["state"][0]))
    verifier = decrypt(attempt.verifier)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    assert query["code_challenge"] == [challenge]
    assert query["code_challenge_method"] == ["S256"]
    assert query["redirect_uri"] == [REDIRECT_URI]
    cookie = next(c for c in response.headers.get_list("set-cookie")
                  if c.startswith("oauth_nonce="))
    assert "HttpOnly" in cookie
    assert "Max-Age=600" in cookie
    assert "SameSite=lax" in cookie
    exchanges = []

    def token_request(session, method, url, **kwargs):
        # Intercept only the network boundary: Flow.fetch_token and the actual
        # OAuth request serialization still run.
        assert method == "POST"
        assert url == "https://oauth2.googleapis.com/token"
        data = kwargs["data"]
        assert data["code_verifier"] == verifier
        assert data["code"] == "fresh-test-code"
        assert data["redirect_uri"] == REDIRECT_URI
        exchanges.append(True)
        result = Response()
        result.request = Request(method, url, data=data).prepare()
        result.status_code = 200
        result._content = b'{"access_token":"test-token","token_type":"Bearer","expires_in":3600,"refresh_token":"synthetic-refresh"}'
        return result

    monkeypatch.setattr(OAuth2Session, "request", token_request)
    response = oauth_client.get("/auth/google/callback", params={
        "code": "fresh-test-code", "state": query["state"][0]
    })
    assert response.status_code == 200
    assert response.json()["message"] == "Google account connected successfully"
    account = test_database.get(GmailAccount, response.json()["account_id"])
    assert account.user_id == test_database.info["user_id"]
    row = test_database.get(OAuthCredential, account.id)
    assert "synthetic-refresh" not in row.ciphertext
    assert "synthetic-refresh" in decrypt(row.ciphertext)
    assert exchanges == [True]
    assert oauth_client.cookies.get("oauth_state") is None
    assert oauth_client.cookies.get("oauth_code_verifier") is None
    # Replaying the callback after successful login must be rejected.
    assert oauth_client.get("/auth/google/callback", params={
        "code": "fresh-test-code", "state": query["state"][0]
    }).status_code == 400


@pytest.mark.parametrize("failure", ["missing_state", "wrong_state", "missing_verifier"])
def test_oauth_rejects_invalid_session(oauth_client, monkeypatch, failure):
    _, query = begin_login(oauth_client)
    state = query["state"][0]
    if failure == "missing_state":
        oauth_client.cookies.clear()
    elif failure == "wrong_state":
        state = "wrong-state"
    else:
        oauth_client.cookies.delete("oauth_nonce")

    def unexpected_exchange(*args, **kwargs):
        pytest.fail("Invalid session must not contact the token endpoint")

    monkeypatch.setattr(OAuth2Session, "request", unexpected_exchange)
    response = oauth_client.get("/auth/google/callback", params={
        "code": "test-code", "state": state
    })
    assert response.status_code == 400


def test_oauth_expired_state_rejected(oauth_client, test_database, monkeypatch):
    from datetime import datetime, timedelta, timezone
    _, query = begin_login(oauth_client)
    state = query['state'][0]
    attempt = test_database.get(OAuthAttempt, digest(state))
    attempt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    test_database.flush()
    unexpected = Mock(side_effect=AssertionError('Must not contact Google'))
    monkeypatch.setattr(Flow, 'fetch_token', unexpected)
    assert oauth_client.get('/auth/google/callback', params={'code': 'x', 'state': state}).status_code == 400
    unexpected.assert_not_called()


def test_oauth_cannot_overwrite_another_users_account(oauth_client, test_database, monkeypatch):
    from backend_models import AppUser
    from backend_config import encrypt
    user = AppUser(name='other-oauth-user', active=True)
    test_database.add(user)
    test_database.flush()
    account = GmailAccount(user_id=user.id, address='oauth@example.invalid', status='connected')
    test_database.add(account)
    test_database.flush()
    credential = OAuthCredential(account_id=account.id, ciphertext=encrypt('other-secret'))
    test_database.add(credential)
    test_database.commit()
    before = credential.ciphertext
    _, query = begin_login(oauth_client)
    monkeypatch.setattr(Flow, 'fetch_token', lambda *a, **k: None)
    # Supply synthetic credentials without the real Google token exchange.
    monkeypatch.setattr(Flow, 'credentials', property(lambda self: Mock()))
    result = oauth_client.get('/auth/google/callback', params={'code': 'x', 'state': query['state'][0]})
    assert result.status_code == 409
    test_database.expire_all()
    assert credential.ciphertext == before


def test_oauth_provider_error_is_safe_and_state_consumed(oauth_client, test_database, monkeypatch):
    _, query = begin_login(oauth_client)
    monkeypatch.setattr(Flow, 'fetch_token', Mock(side_effect=RuntimeError('private token')))
    params = {'code': 'x', 'state': query['state'][0]}
    result = oauth_client.get('/auth/google/callback', params=params)
    assert result.status_code == 503 and 'private token' not in result.text
    assert oauth_client.get('/auth/google/callback', params=params).status_code == 400
