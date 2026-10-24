from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from fastapi import Depends
from database import get_db
from ownership import OwnedSession
from sqlalchemy import select
from main import app
from authentication import current_user, issue_token, digest
from backend_models import AppUser, AccessToken, OAuthAttempt
from browser_auth import cookie_name
import account_routes


@pytest.fixture
def browser(test_database, monkeypatch):
    monkeypatch.setenv('BROWSER_ORIGIN', 'https://inbox.example.invalid')
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('GOOGLE_REDIRECT_URI', 'https://inbox.example.invalid/api/auth/google/callback')
    # Session/CSRF tests provision synthetic credentials while retaining real
    # production cookie flags. Production refusal is independently tested in
    # test_google_login; real Google session creation is covered there too.
    monkeypatch.setattr('browser_auth.development_token_login_enabled', lambda: True)
    app.dependency_overrides.pop(current_user)
    def owned_db(principal=Depends(current_user)):
        with OwnedSession(bind=test_database.get_bind(), user_id=principal.id, autoflush=False,
                          join_transaction_mode="create_savepoint") as db:
            yield db
    app.dependency_overrides[get_db] = owned_db
    user = test_database.get(AppUser, test_database.info['user_id'])
    token = issue_token(test_database, user)
    test_database.commit()
    with TestClient(app, base_url='https://inbox.example.invalid') as client:
        yield client, token


def login(browser):
    client, token = browser
    response = client.post('/auth/session', headers={'origin':'https://inbox.example.invalid','authorization':'Bearer '+token})
    assert response.status_code == 200
    return response


def headers(response):
    return {'origin':'https://inbox.example.invalid','x-csrf-token':response.json()['csrf_token']}


def test_cookie_login_restore_logout_revocation(browser, test_database):
    client, provision = browser
    response = login(browser)
    cookie = response.headers['set-cookie']
    assert '__Host-inbox_session=' in cookie and 'Secure' in cookie and 'HttpOnly' in cookie
    assert 'SameSite=lax' in cookie and 'Path=/' in cookie and 'Domain=' not in cookie
    secret = client.cookies.get(cookie_name())
    assert secret not in response.text and provision not in response.text
    row = test_database.get(AccessToken, digest(secret))
    assert row.expires_at <= datetime.now(timezone.utc)+timedelta(hours=8)
    assert client.get('/auth/session').json() == response.json()
    assert client.get('/tasks').status_code == 200
    assert client.delete('/auth/session',headers=headers(response)).status_code == 204
    assert test_database.get(AccessToken,digest(secret)) is None
    assert client.get('/tasks').status_code == 401
    assert test_database.get(AccessToken,digest(provision)) is not None


@pytest.mark.parametrize('origin',[None,'https://evil.invalid','null','http://inbox.example.invalid'])
def test_login_rejects_wrong_origin(browser, origin):
    client,token=browser
    h={'authorization':'Bearer '+token}
    if origin:h['origin']=origin
    assert client.post('/auth/session',headers=h).status_code == 403


@pytest.mark.parametrize('extra',[{}, {'origin':'https://inbox.example.invalid'}, {'origin':'https://evil.invalid','x-csrf-token':'bad'}])
def test_cookie_mutations_require_origin_and_csrf(browser, extra):
    client,_=browser
    login(browser)
    assert client.post('/gmail/accounts/1/sync',headers=extra).status_code == 403
    assert client.delete('/gmail/accounts/1/connection',headers=extra).status_code == 403
    assert client.post('/emails/1/retry-enrichment',headers=extra).status_code == 403
    assert client.delete('/auth/session',headers=extra).status_code == 403
    assert client.get('/auth/google').status_code == 403


def test_cookie_expiration_inactive_and_bearer_replay(browser,test_database):
    client,_=browser
    response=login(browser)
    secret=client.cookies.get(cookie_name())
    assert client.get('/tasks',headers={'authorization':'Bearer '+secret}).status_code == 401
    assert client.post('/auth/session',headers={**headers(response),'authorization':'Bearer '+secret}).status_code == 401
    row=test_database.get(AccessToken,digest(secret))
    row.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    test_database.commit()
    assert client.get('/auth/session').status_code == 401
    login(browser)
    user=test_database.get(AppUser,test_database.info['user_id']);user.active=False;test_database.commit()
    assert client.get('/tasks').status_code == 401


def test_rotation_and_no_invalid_bearer_fallback(browser,test_database):
    client,_=browser
    login(browser);old=client.cookies.get(cookie_name());login(browser)
    assert old!=client.cookies.get(cookie_name())
    assert test_database.get(AccessToken,digest(old)) is None
    assert client.get('/tasks',headers={'authorization':'Bearer invalid'}).status_code == 401


def test_legacy_bearer_still_works_without_cookies(browser):
    client,token=browser
    assert client.get('/tasks',headers={'authorization':'Bearer '+token}).status_code == 200


def oauth_start(browser, monkeypatch):
    client,_=browser
    session=login(browser)
    flow=Mock(code_verifier='verifier',credentials=Mock())
    flow.authorization_url.return_value=('https://accounts.google.com/o/oauth2/auth?state=fake-state','fake-state')
    monkeypatch.setattr(account_routes,'create_google_flow',lambda **kw:flow)
    response=client.post('/auth/google/start?browser=true',headers=headers(session))
    assert response.status_code == 200
    assert 'Path=/api/auth/google/callback' in response.headers['set-cookie']
    # The proxy strips /api before FastAPI receives the callback.
    nonce=client.cookies.get('oauth_nonce')
    client.cookies.set('oauth_nonce',nonce,path='/auth/google/callback')
    return flow


@pytest.mark.parametrize('scenario,expected',[('denied','denied'),('expired','expired'),('provider','provider_error'),('provider_callback','provider_error'),('success','success')])
def test_browser_oauth_safe_completion(browser,monkeypatch,test_database,scenario,expected):
    client,_=browser
    flow=oauth_start(browser,monkeypatch)
    params={'state':'fake-state','code':'fake-code'}
    if scenario=='denied':params={'state':'fake-state','error':'access_denied'}
    if scenario=='provider_callback':params={'state':'fake-state','error':'temporarily_unavailable'}
    if scenario=='expired':
        row=test_database.get(OAuthAttempt,digest('fake-state'));row.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1);test_database.commit()
    if scenario=='provider':flow.fetch_token.side_effect=RuntimeError('SECRET_PROVIDER_DETAIL')
    if scenario=='success':
        service=Mock();service.users.return_value.getProfile.return_value.execute.return_value={'emailAddress':'browser@example.invalid'}
        monkeypatch.setattr(account_routes,'build',lambda *a,**k:service)
        monkeypatch.setattr(account_routes,'save_credentials',lambda *a:None)
    response=client.get('/auth/google/callback',params=params,headers={'accept':'text/html'},follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location']=='https://inbox.example.invalid/oauth/complete?result='+expected
    assert 'SECRET' not in response.text and 'code=' not in response.headers['location']
    if scenario in ('denied','expired','provider_callback'):flow.fetch_token.assert_not_called()
    if scenario!='expired':assert test_database.get(OAuthAttempt,digest('fake-state')) is None


def test_missing_nonce_browser_callback_returns_safe_expiry(browser):
    client,_=browser
    response=client.get('/auth/google/callback?code=private',headers={'accept':'text/html'},follow_redirects=False)
    assert response.status_code==303 and response.headers['location'].endswith('result=expired')


def test_production_origin_requires_https(monkeypatch):
    from backend_config import browser_origin, ConfigurationError
    monkeypatch.setenv('APP_ENV','production');monkeypatch.setenv('BROWSER_ORIGIN','http://localhost:5173')
    with pytest.raises(ConfigurationError):browser_origin()


def test_browser_cookie_preserves_user_isolation(browser, test_database):
    from backend_models import GmailAccount
    client, _ = browser
    other = AppUser(name='other-browser-user', active=True)
    test_database.add(other)
    test_database.flush()
    foreign = GmailAccount(user_id=other.id, address='other@example.invalid', status='connected')
    test_database.add(foreign)
    test_database.commit()
    response = login(browser)
    rows = client.get('/gmail/accounts').json()['accounts']
    assert rows and all(row['id'] != foreign.id for row in rows)
    assert client.delete(f'/gmail/accounts/{foreign.id}/connection', headers=headers(response)).status_code == 404
    own_id = test_database.info['account_id']
    assert client.delete(f'/gmail/accounts/{own_id}/connection', headers=headers(response)).status_code == 200
    assert test_database.get(GmailAccount, foreign.id).status == 'connected'


def test_session_rejects_invalid_code_and_caps_expiry(browser, test_database):
    client, token = browser
    assert client.post('/auth/session', headers={'origin':'https://inbox.example.invalid', 'authorization':'Bearer wrong'}).status_code == 401
    row = test_database.get(AccessToken, digest(token))
    expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    row.expires_at = expiry
    test_database.commit()
    response = login(browser)
    assert response.headers['cache-control'] == 'no-store'
    secret = client.cookies.get(cookie_name())
    assert test_database.get(AccessToken, digest(secret)).expires_at == expiry
