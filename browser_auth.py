"""Short-lived browser sessions in the existing revocable access-token table."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from authentication import auth_session, valid_access, digest
from backend_config import browser_origin

router = APIRouter()


def cookie_name():
    return '__Host-inbox_session' if os.getenv('APP_ENV', 'development') != 'development' else 'inbox_session'


def csrf_token(secret):
    return digest('inbox-csrf:' + secret)


def check_origin(request):
    if request.headers.get('origin') != browser_origin():
        raise HTTPException(403, 'Browser origin rejected')


def check_csrf(request, secret):
    check_origin(request)
    if not secrets.compare_digest(request.headers.get('x-csrf-token', ''), csrf_token(secret)):
        raise HTTPException(403, 'Browser request rejected')


class BrowserSession(BaseModel):
    csrf_token: str


def development_token_login_enabled():
    return os.getenv('APP_ENV', 'development') == 'development'


@router.post('/auth/session', response_model=BrowserSession)
def login(request: Request, response: Response, db=Depends(auth_session)):
    # Hiding the development form is not an authentication boundary.
    if not development_token_login_enabled():
        raise HTTPException(404, 'Not found')
    check_origin(request)
    header = request.headers.get('authorization', '')
    value = header[7:] if header.startswith('Bearer ') else ''
    row = valid_access(db, value) if value and not value.startswith('web_') else None
    if row is None:
        raise HTTPException(401, 'Authentication required')
    return create_browser_session(request, response, db, row.user_id, row.expires_at)


def create_browser_session(request, response, db, user_id, expires_at=None):
    from backend_models import AccessToken
    expires_at = expires_at or datetime.now(timezone.utc) + timedelta(hours=8)
    # Rotate this browser's old session, without revoking its provisioning credential.
    previous = request.cookies.get(cookie_name(), '')
    old = db.get(AccessToken, digest(previous)) if previous.startswith('web_') else None
    if old is not None:
        db.delete(old)
    secret = 'web_' + secrets.token_urlsafe(32)
    expires = min(expires_at, datetime.now(timezone.utc) + timedelta(hours=8))
    db.add(AccessToken(digest=digest(secret), user_id=user_id, expires_at=expires))
    db.commit()
    response.set_cookie(cookie_name(), secret, max_age=max(1,int((expires-datetime.now(timezone.utc)).total_seconds())),
                        secure=cookie_name().startswith('__Host-'), httponly=True, samesite='lax', path='/')
    return BrowserSession(csrf_token=csrf_token(secret))


@router.get('/auth/session', response_model=BrowserSession)
def session(request: Request, db=Depends(auth_session)):
    secret = request.cookies.get(cookie_name(), '')
    if not secret.startswith('web_') or valid_access(db, secret) is None:
        raise HTTPException(401, 'Authentication required')
    return BrowserSession(csrf_token=csrf_token(secret))


@router.delete('/auth/session', status_code=204)
def logout(request: Request, db=Depends(auth_session)):
    from backend_models import AccessToken
    secret = request.cookies.get(cookie_name(), '')
    check_origin(request)
    if secret:
        check_csrf(request, secret)
        row = db.get(AccessToken, digest(secret)) if secret.startswith('web_') else None
        if row is not None:
            db.delete(row)
            db.commit()
    response = Response(status_code=204)
    response.delete_cookie(cookie_name(), path='/', secure=cookie_name().startswith('__Host-'), httponly=True, samesite='lax')
    return response
