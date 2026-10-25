"""Revocable backend access tokens. Gmail consent is separate from app login."""
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

bearer = HTTPBearer(auto_error=False)


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class Principal:
    id: int


def issue_token(db, user, *, days=7):
    from backend_models import AccessToken
    if not user.active or not 1 <= days <= 30:
        raise ValueError('Active user and token lifetime of 1 to 30 days required')
    value = secrets.token_urlsafe(32)
    db.add(AccessToken(digest=digest(value), user_id=user.id,
                       expires_at=datetime.now(timezone.utc) + timedelta(days=days)))
    db.flush()
    return value


def auth_session():
    # Privileged, short-lived session, used only for credential authentication.
    from database import SessionLocal
    with SessionLocal() as db:
        yield db


def valid_access(db, value):
    from backend_models import AccessToken, AppUser
    return db.scalar(select(AccessToken).join(AppUser, AppUser.id == AccessToken.user_id).where(
        AppUser.active.is_(True), AccessToken.digest == digest(value),
        AccessToken.expires_at > datetime.now(timezone.utc)))


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(auth_session), request: Request = None):
    from browser_auth import cookie_name, check_csrf
    if credentials is not None:
        value = credentials.credentials
        row = None if value.startswith('web_') else valid_access(db, value)
    else:
        value = request.cookies.get(cookie_name(), '') if request is not None else ''
        row = valid_access(db, value) if value.startswith('web_') else None
        if row is not None and (request.method not in ('GET', 'HEAD', 'OPTIONS')
                                or request.url.path.endswith('/auth/google')):
            check_csrf(request, value)
    if row is not None:
        return Principal(row.user_id)
    raise HTTPException(401, 'Authentication required', headers={'WWW-Authenticate': 'Bearer'})
