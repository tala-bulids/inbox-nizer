"""Authenticated account operations and one-use, user-bound OAuth callbacks."""
import secrets
import os
from urllib.parse import urlsplit
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError
from authentication import current_user, auth_session, digest
from backend_config import encrypt, decrypt, redirect_uri, ConfigurationError, browser_origin
from backend_models import AppUser, GmailAccount, OAuthAttempt, OAuthCredential, GmailSyncState, ProcessingState
from models import Email
from database import get_db
from gmail_auth import create_google_flow
from gmail_service import save_credentials
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
from httplib2 import Http
from gmail_sync import sync_account, connection_guard, source_has_more, source_failure_count
from email_pipeline import retryable_stages
from runtime_capabilities import runtime_profile

router = APIRouter()


@router.get('/gmail/accounts')
def accounts(db=Depends(get_db)):
    return {'runtime_profile': runtime_profile(), 'accounts': [dict(id=a.id, address=a.address, status=a.status,
                              last_synced_at=a.last_synced_at, sync_error=a.sync_error,
                              initial_sync_pending=a.history_id is None,
                              message_count=db.scalar(select(func.count(Email.id)).where(Email.account_id == a.id)),
                              enrichment_failed_count=db.scalar(select(func.count(func.distinct(ProcessingState.email_id)))
                                  .join(Email, Email.id == ProcessingState.email_id)
                                  .where(Email.account_id == a.id, ProcessingState.status == 'failed')),
                              source_failed_count=source_failure_count(db.get(GmailSyncState, a.id)),
                              sync_pending=(source_has_more(db.get(GmailSyncState, a.id)) or
                                  db.scalar(select(ProcessingState.id).join(Email, Email.id == ProcessingState.email_id)
                                    .where(Email.account_id == a.id,
                                           retryable_stages()).limit(1)) is not None))
                         for a in db.scalars(select(GmailAccount).order_by(GmailAccount.id))],
            'sync_interval_seconds': max(60, min(3600, int(os.getenv('GMAIL_SYNC_INTERVAL_SECONDS', '300'))))}


@router.post('/gmail/accounts/{account_id}/sync')
def sync(account_id: int, retry_failed: bool = False, db=Depends(get_db)):
    return sync_account(db, account_id, retry_failed=retry_failed)


@router.post('/gmail/messages')
def sync_single(db=Depends(get_db)):
    ids = list(db.scalars(select(GmailAccount.id)))
    if len(ids) != 1:
        raise HTTPException(409, 'Choose a connected Gmail account using /gmail/accounts/{id}/sync')
    return sync_account(db, ids[0])


@router.delete('/gmail/accounts/{account_id}/connection')
def disconnect(account_id: int, db=Depends(get_db)):
    account = db.scalar(select(GmailAccount).where(GmailAccount.id == account_id).with_for_update())
    if account is None:
        raise HTTPException(404, 'Gmail account not found')
    connection_guard(db, account_id)
    credential = db.get(OAuthCredential, account.id)
    if credential:
        db.delete(credential)
    account.status = 'disconnected'
    db.commit()
    return {'status': 'disconnected'}


@router.get('/auth/google')
@router.post('/auth/google/start')
def start_google(request: Request, browser: bool = False, principal=Depends(current_user), db=Depends(auth_session)):
    try:
        flow = create_google_flow()
        url, state = flow.authorization_url(access_type='offline', prompt='consent')
        nonce = ('browser.' if browser else '') + secrets.token_urlsafe(32)
        # Prune expired handshakes without retaining secrets indefinitely.
        db.execute(delete(OAuthAttempt).where(OAuthAttempt.expires_at < datetime.now(timezone.utc)))
        db.add(OAuthAttempt(state_hash=digest(state), user_id=principal.id, nonce_hash=digest(nonce),
            verifier=encrypt(flow.code_verifier), expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)))
        db.commit()
        response = RedirectResponse(url) if request.method == 'GET' else JSONResponse({'authorization_url': url})
        response.set_cookie('oauth_nonce', nonce, httponly=True, secure=redirect_uri().startswith('https:'),
                            samesite='lax', max_age=600, path=urlsplit(redirect_uri()).path)
        response.headers['Cache-Control'] = 'no-store'
        return response
    except Exception as error:
        db.rollback()
        raise HTTPException(503, 'Google connection configuration unavailable') from error


@router.get('/auth/google/callback')
def finish_google(request: Request, state: str = '', code: str | None = None, error: str | None = None, db=Depends(auth_session)):
    attempt = db.scalar(select(OAuthAttempt).where(OAuthAttempt.state_hash == digest(state)).with_for_update())
    nonce = request.cookies.get('oauth_nonce', '')
    if (not attempt or attempt.expires_at <= datetime.now(timezone.utc) or not nonce
            or not secrets.compare_digest(attempt.nonce_hash, digest(nonce))):
        return oauth_result(request, 'expired', 400, 'Invalid or expired OAuth session')
    user_id, encrypted_verifier = attempt.user_id, attempt.verifier
    user = db.get(AppUser, user_id)
    active = user is not None and user.active
    db.delete(attempt)
    db.commit()  # Consume before contacting Google; failures require a fresh login.
    if not active or error or not code:
        result = ('denied' if error == 'access_denied' else 'provider_error') if active and error else 'expired'
        return oauth_result(request, result, 400, 'Restart Google connection')
    try:
        flow = create_google_flow(state=state, code_verifier=decrypt(encrypted_verifier))
        flow.fetch_token(code=code, timeout=30)
        service = build('gmail', 'v1', http=AuthorizedHttp(flow.credentials, http=Http(timeout=30)), cache_discovery=False)
        profile = service.users().getProfile(userId='me').execute(num_retries=3)
        address = profile['emailAddress'].strip().lower()
        if not address or '@' not in address:
            raise ValueError('Invalid account identity')
        account = db.scalar(select(GmailAccount).where(GmailAccount.address == address).with_for_update())
        if account is not None and account.user_id != user_id:
            raise HTTPException(409, 'This Gmail account cannot be connected')
        if account is None:
            account = GmailAccount(user_id=user_id, address=address)
            db.add(account)
            db.flush()
        connection_guard(db, account.id)
        save_credentials(db, account, flow.credentials)
        account.status = 'connected'
        db.commit()
    except HTTPException as error:
        db.rollback()
        return oauth_result(request, 'provider_error', error.status_code, 'Google connection failed; restart login')
    except IntegrityError as error:
        db.rollback()
        return oauth_result(request, 'provider_error', 409, 'This Gmail account cannot be connected; restart login')
    except Exception as error:
        db.rollback()
        return oauth_result(request, 'provider_error', 503, 'Google connection failed; restart login')
    if is_browser_callback(request):
        return oauth_result(request, 'success', 200, '')
    response = JSONResponse({'message': 'Google account connected successfully', 'account_id': account.id})
    response.delete_cookie('oauth_nonce', path=urlsplit(redirect_uri()).path)
    response.headers['Cache-Control'] = 'no-store'
    return response


def is_browser_callback(request):
    return ('text/html' in request.headers.get('accept', '')
            or request.cookies.get('oauth_nonce', '').startswith('browser.'))


def oauth_result(request, result, status, detail):
    if not is_browser_callback(request):
        raise HTTPException(status, detail)
    response = RedirectResponse(browser_origin() + '/oauth/complete?result=' + result, status_code=303)
    response.delete_cookie('oauth_nonce', path=urlsplit(redirect_uri()).path)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response
