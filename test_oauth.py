"""Exercise the real OAuth library with synthetic credentials and a fake token server."""
import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from google_auth_oauthlib.flow import Flow
from requests import Response, Request
from requests_oauthlib import OAuth2Session

from main import app
from gmail_auth import REDIRECT_URI


@pytest.fixture
def oauth_client(monkeypatch):
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


def test_oauth_pkce_survives_callback(oauth_client, monkeypatch):
    response, query = begin_login(oauth_client)
    verifier = oauth_client.cookies.get("oauth_code_verifier")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    assert query["code_challenge"] == [challenge]
    assert query["code_challenge_method"] == ["S256"]
    assert query["redirect_uri"] == [REDIRECT_URI]
    cookie = next(c for c in response.headers.get_list("set-cookie")
                  if c.startswith("oauth_code_verifier="))
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
        result._content = b'{"access_token":"test-token","token_type":"Bearer","expires_in":3600}'
        return result

    monkeypatch.setattr(OAuth2Session, "request", token_request)
    response = oauth_client.get("/auth/google/callback", params={
        "code": "fresh-test-code", "state": query["state"][0]
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Google account connected successfully"}
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
        oauth_client.cookies.delete("oauth_code_verifier")

    def unexpected_exchange(*args, **kwargs):
        pytest.fail("Invalid session must not contact the token endpoint")

    monkeypatch.setattr(OAuth2Session, "request", unexpected_exchange)
    response = oauth_client.get("/auth/google/callback", params={
        "code": "test-code", "state": state
    })
    assert response.status_code == 400
