from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from main import app
from backend_models import AppUser, GmailAccount, GoogleLoginAttempt, GoogleIdentity, AccessToken
from authentication import current_user, digest
from browser_auth import cookie_name
import google_login


@pytest.fixture
def google(test_database, monkeypatch):
    monkeypatch.setenv('BROWSER_ORIGIN','https://inbox.example.invalid')
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.setenv('GOOGLE_LOGIN_REDIRECT_URI','https://inbox.example.invalid/auth/google/login/callback')
    app.dependency_overrides.pop(current_user)
    account = test_database.get(GmailAccount,test_database.info['account_id'])
    account.address='owner@gmail.com'
    test_database.flush()
    claims = dict(sub='google-owner',email='owner@gmail.com',email_verified=True,nonce='nonce')
    flow = SimpleNamespace(code_verifier='pkce-verifier', client_config={'client_id':'client'},
        oauth2session=SimpleNamespace(token={'id_token':'signed-id-token'}),fetch_token=lambda **kw: None)
    def authorize(**kw):
        claims['nonce']=kw['nonce']
        assert kw['access_type']=='online'
        return 'https://accounts.google.com/o/oauth2/auth?state=state', 'state'
    flow.authorization_url=authorize
    monkeypatch.setattr(google_login,'login_flow',lambda *a: flow)
    monkeypatch.setattr(google_login,'verified_claims',lambda token,audience: claims)
    with TestClient(app,base_url='https://inbox.example.invalid',follow_redirects=False) as client:
        yield client, claims, flow


def start(google):
    client,_,_=google
    return client.post('/auth/google/login/start',headers={'origin':'https://inbox.example.invalid'})


def finish(google, **params):
    return google[0].get('/auth/google/login/callback',params={'state':'state','code':'code',**params})


def test_google_session_separate_consent_and_replay(google,test_database):
    assert start(google).status_code==200
    attempt=test_database.get(GoogleLoginAttempt,digest('state'))
    assert attempt.verifier.startswith('v1:')
    result=finish(google)
    assert result.headers['location']=='https://inbox.example.invalid/'
    assert 'HttpOnly' in result.headers['set-cookie'] and 'Secure' in result.headers['set-cookie']
    assert google[0].get('/auth/session').status_code==200
    assert test_database.get(GoogleIdentity,'google-owner').user_id==test_database.info['user_id']
    assert finish(google).headers['location'].endswith('login=expired')
    assert all('gmail' not in scope for scope in google_login.SCOPES)
    assert google_login.SCOPES == ['openid', 'https://www.googleapis.com/auth/userinfo.email']


@pytest.mark.parametrize('kind', ['nonce','state','browser','expired','denied','provider','unverified','third_party','inactive'])
def test_google_failures_never_issue_session(google,test_database,monkeypatch,kind):
    assert start(google).status_code==200
    client,claims,flow=google
    params={}
    if kind=='nonce': claims['nonce']='wrong'
    if kind=='state': params['state']='wrong'
    if kind=='browser': client.cookies.clear()
    if kind=='expired':
        test_database.get(GoogleLoginAttempt,digest('state')).expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
        test_database.flush()
    if kind=='denied': params['error']='access_denied'
    if kind=='provider': monkeypatch.setattr(flow,'fetch_token',lambda **kw: (_ for _ in ()).throw(RuntimeError('secret')))
    if kind=='unverified': claims['email_verified']=False
    if kind=='third_party': claims['email']='owner@example.invalid'
    if kind=='inactive':
        test_database.get(AppUser,test_database.info['user_id']).active=False
        test_database.flush()
    result=finish(google,**params)
    assert '?login=' in result.headers['location']
    assert 'secret' not in result.text
    assert client.get('/auth/session').status_code==401


def test_start_rejects_other_origin(google):
    assert google[0].post('/auth/google/login/start',headers={'origin':'https://evil.invalid'}).status_code==403


def test_allowlisted_new_user_guided_to_gmail(google,test_database,monkeypatch):
    google[1].update(sub='new-sub',email='new@gmail.com')
    monkeypatch.setenv('GOOGLE_LOGIN_ALLOWED_EMAILS','new@gmail.com')
    start(google)
    assert finish(google).headers['location']=='https://inbox.example.invalid/settings'
    assert test_database.get(GoogleIdentity,'new-sub').user_id!=test_database.info['user_id']


def test_no_public_signup(google,test_database):
    google[1].update(sub='stranger',email='stranger@gmail.com')
    start(google)
    assert finish(google).headers['location'].endswith('login=not_allowed')
    assert test_database.get(GoogleIdentity,'stranger') is None


def test_existing_subject_cannot_switch_user_by_email(google,test_database):
    start(google)
    finish(google)
    google[1]['email']='someone-else@gmail.com'
    start(google)
    finish(google)
    assert test_database.get(GoogleIdentity,'google-owner').user_id==test_database.info['user_id']


def test_google_csrf_still_required(google):
    start(google)
    finish(google)
    assert google[0].delete('/auth/session').status_code==403

def test_pkce_and_nonce_present_in_actual_authorization_url(monkeypatch):
    from google_auth_oauthlib.flow import Flow
    from urllib.parse import urlsplit, parse_qs
    config={'web':{'client_id':'test-client','client_secret':'test-secret',
        'auth_uri':'https://accounts.google.com/o/oauth2/auth','token_uri':'https://oauth2.googleapis.com/token'}}
    monkeypatch.setattr(Flow,'from_client_secrets_file',lambda filename,**kwargs: Flow.from_client_config(config,**kwargs))
    flow=google_login.login_flow()
    url,state=flow.authorization_url(nonce='test-nonce',access_type='online')
    params=parse_qs(urlsplit(url).query)
    assert params['code_challenge_method']==['S256']
    assert params['nonce']==['test-nonce']
    assert len(flow.code_verifier)>=43 and params['state']==[state]
    assert 'gmail' not in params['scope'][0]


def test_google_verifier_receives_audience(monkeypatch):
    calls=[]
    monkeypatch.setattr(google_login.id_token,'verify_oauth2_token',lambda token,request,**kw: calls.append((token,kw)) or {'sub':'s'})
    assert google_login.verified_claims('signed','expected-client')=={'sub':'s'}
    assert calls==[('signed',{'audience':'expected-client'})]


def test_google_token_and_certificate_requests_are_bounded(google, monkeypatch):
    from unittest.mock import Mock
    client, _, flow = google
    exchange = Mock()
    monkeypatch.setattr(flow, 'fetch_token', exchange)
    start(google)
    finish(google)
    exchange.assert_called_once_with(code='code', timeout=30)

    transport = Mock(return_value='certificate-response')
    monkeypatch.setattr(google_login, 'GoogleRequest', lambda: transport)
    def verify(token, request, **kwargs):
        assert request('https://www.googleapis.com/oauth2/v1/certs', timeout=999) == 'certificate-response'
        return {'sub': 'verified'}
    monkeypatch.setattr(google_login.id_token, 'verify_oauth2_token', verify)
    # The fixture replaces this function; call the original through a saved
    # reference so the network transport itself remains exercised.
    assert _real_verified_claims('signed', 'client') == {'sub': 'verified'}
    transport.assert_called_once_with('https://www.googleapis.com/oauth2/v1/certs', timeout=30)


def test_production_rejects_admin_token_browser_login(google, test_database):
    from authentication import issue_token
    user = test_database.get(AppUser, test_database.info['user_id'])
    token = issue_token(test_database, user)
    test_database.commit()
    response = google[0].post('/auth/session', headers={
        'origin': 'https://inbox.example.invalid', 'authorization': 'Bearer ' + token,
    })
    assert response.status_code == 404
    assert 'set-cookie' not in response.headers
    assert google[0].get('/auth/session').status_code == 401


_real_verified_claims = google_login.verified_claims

def test_google_migration_roundtrip_preserves_users(test_database):
    from pathlib import Path
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    from sqlalchemy import inspect, text
    config=Config()
    config.set_main_option('script_location', str(Path(__file__).parent/'alembic'))
    scripts=ScriptDirectory.from_config(config)
    revision=scripts.get_revision('c4d9e6f135ab')
    assert revision.down_revision=='b3c8d5e024fa'
    connection=test_database.connection()
    assert connection.engine.url.database.endswith('_test')
    count=connection.scalar(text('select count(*) from app_users'))
    with Operations.context(MigrationContext.configure(connection)):
        revision.module.downgrade()
        assert not inspect(connection).has_table('google_identities')
        revision.module.upgrade()
        assert inspect(connection).has_table('google_login_attempts')
    assert connection.scalar(text('select count(*) from app_users'))==count
