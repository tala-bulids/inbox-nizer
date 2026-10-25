"""Google application sign-in; never requests or stores Gmail credentials."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from sqlalchemy import delete, func
from authentication import auth_session, digest
from backend_config import ConfigurationError, browser_origin, encrypt, decrypt
from backend_models import AppUser, GmailAccount, GoogleIdentity, GoogleLoginAttempt
from browser_auth import check_origin, create_browser_session

router = APIRouter()
SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email']


def callback_uri():
    value = os.getenv('GOOGLE_LOGIN_REDIRECT_URI', 'http://localhost:8000/auth/google/login/callback')
    parsed = urlsplit(value)
    if (not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ('/auth/google/login/callback', '/api/auth/google/login/callback')
            or parsed.scheme not in ('https', 'http')
            or parsed.scheme == 'http' and (os.getenv('APP_ENV', 'development') != 'development'
                or parsed.hostname not in ('localhost', '127.0.0.1', '::1'))):
        raise ConfigurationError('Configure GOOGLE_LOGIN_REDIRECT_URI as a secure login callback')
    return value


def login_flow(state=None, verifier=None):
    return Flow.from_client_secrets_file(os.getenv('GOOGLE_CLIENT_FILE', 'credentials.json'),
        scopes=SCOPES, state=state, code_verifier=verifier, redirect_uri=callback_uri())


def cookie_options():
    return dict(path=urlsplit(callback_uri()).path, httponly=True, samesite='lax',
                secure=os.getenv('APP_ENV', 'development') != 'development')


@router.post('/auth/google/login/start')
def start_login(request: Request, db=Depends(auth_session)):
    check_origin(request)
    flow = login_flow()
    browser = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    url, state = flow.authorization_url(nonce=nonce, prompt='select_account', access_type='online')
    now = datetime.now(timezone.utc)
    db.execute(delete(GoogleLoginAttempt).where(GoogleLoginAttempt.expires_at < now))
    db.add(GoogleLoginAttempt(state_hash=digest(state), browser_hash=digest(browser),
        nonce_hash=digest(nonce), verifier=encrypt(flow.code_verifier), expires_at=now + timedelta(minutes=10)))
    db.commit()
    from fastapi.responses import JSONResponse
    response = JSONResponse({'authorization_url': url})
    response.set_cookie('inbox_google_login', browser, max_age=600, **cookie_options())
    return response


def verified_claims(token, audience):
    # Google's verifier checks signature, expiry, issuer and audience.
    transport = GoogleRequest()
    def bounded_request(*args, **kwargs):
        return transport(*args, **dict(kwargs, timeout=30))
    return id_token.verify_oauth2_token(token, bounded_request, audience=audience)


def identity_user(db, claims):
    subject = claims.get('sub')
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        return None
    existing = db.get(GoogleIdentity, subject)
    if existing:
        user = db.get(AppUser, existing.user_id)
        return user if user and user.active else None
    email = claims.get('email', '').casefold()
    # Do not auto-link third-party email addresses that Google does not own.
    authoritative = email.endswith('@gmail.com') or bool(claims.get('hd'))
    if claims.get('email_verified') is not True or not authoritative:
        return None
    account = db.query(GmailAccount).filter(func.lower(GmailAccount.address) == email).one_or_none()
    user = db.get(AppUser, account.user_id) if account else None
    if user is None:
        allowed = {item.strip().casefold() for item in os.getenv('GOOGLE_LOGIN_ALLOWED_EMAILS', '').split(',') if item.strip()}
        if email not in allowed:
            return None
        user = AppUser(name='google:' + digest(subject), active=True)
        db.add(user)
        db.flush()
    if not user.active or db.query(GoogleIdentity).filter_by(user_id=user.id).first():
        return None
    db.add(GoogleIdentity(subject=subject, user_id=user.id))
    db.flush()
    return user


@router.get('/auth/google/login/callback')
def finish_login(request: Request, state: str = '', code: str = '', error: str = '', db=Depends(auth_session)):
    def failure(result):
        response = RedirectResponse(browser_origin() + '/?login=' + result, status_code=303)
        response.delete_cookie('inbox_google_login', **cookie_options())
        return response
    attempt = db.get(GoogleLoginAttempt, digest(state)) if state else None
    browser = request.cookies.get('inbox_google_login', '')
    if (not attempt or not browser or attempt.expires_at <= datetime.now(timezone.utc)
            or not secrets.compare_digest(attempt.browser_hash, digest(browser))):
        return failure('expired')
    # Atomic consumption prevents parallel callback replay.
    consumed = db.execute(delete(GoogleLoginAttempt).where(GoogleLoginAttempt.state_hash == attempt.state_hash)
                          .returning(GoogleLoginAttempt.verifier, GoogleLoginAttempt.nonce_hash)).first()
    db.commit()
    if consumed is None:
        return failure('expired')
    if error:
        return failure('denied' if error == 'access_denied' else 'failed')
    if not code:
        return failure('failed')
    try:
        flow = login_flow(state, decrypt(consumed.verifier))
        flow.fetch_token(code=code, timeout=30)
        claims = verified_claims(flow.oauth2session.token['id_token'], flow.client_config['client_id'])
        nonce = claims.get('nonce', '')
        if not isinstance(nonce, str) or not secrets.compare_digest(digest(nonce), consumed.nonce_hash):
            return failure('failed')
        user = identity_user(db, claims)
        if user is None:
            db.rollback()
            return failure('not_allowed')
        connected = db.query(GmailAccount).filter_by(user_id=user.id, status='connected').first() is not None
        response = RedirectResponse(browser_origin() + ('/' if connected else '/settings'), status_code=303)
        create_browser_session(request, response, db, user.id)
        response.delete_cookie('inbox_google_login', **cookie_options())
        return response
    except Exception:
        db.rollback()
        return failure('failed')
