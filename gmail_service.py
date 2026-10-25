"""Only account-owned, encrypted credentials can create a Gmail client."""
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
from httplib2 import Http
from fastapi import HTTPException
from backend_config import decrypt, encrypt
from backend_models import OAuthCredential
from gmail_auth import SCOPES


def save_credentials(db, account, credentials):
    row = db.get(OAuthCredential, account.id)
    data = json.loads(credentials.to_json())
    if not data.get('refresh_token') and row:
        data['refresh_token'] = json.loads(decrypt(row.ciphertext)).get('refresh_token')
    if not data.get('refresh_token'):
        raise HTTPException(409, 'Reconnect Gmail with offline consent')
    if row is None:
        row = OAuthCredential(account_id=account.id)
        db.add(row)
    row.ciphertext = encrypt(json.dumps(data))
    db.flush()


def get_gmail_service(db, account):
    row = db.get(OAuthCredential, account.id)
    if row is None or account.status != 'connected':
        raise HTTPException(409, 'Connect or reconnect this Gmail account')
    credentials = Credentials.from_authorized_user_info(json.loads(decrypt(row.ciphertext)), SCOPES)
    refresh = credentials.refresh

    def refresh_and_persist(request):
        try:
            refresh(request)
        except RefreshError as error:
            if not getattr(error, 'retryable', False):
                account.status = 'reconnect_required'
                db.flush()
            raise HTTPException(503 if getattr(error, 'retryable', False) else 409,
                                'Gmail temporarily unavailable' if getattr(error, 'retryable', False) else 'Reconnect Gmail') from error
        save_credentials(db, account, credentials)
    # AuthorizedHttp can refresh again during a long sync. Persist that refresh too.
    credentials.refresh = refresh_and_persist
    if not credentials.valid:
        credentials.refresh(lambda *args, **kwargs: Request()(*args, **dict(kwargs, timeout=30)))
    return build('gmail', 'v1', http=AuthorizedHttp(credentials, http=Http(timeout=30)), cache_discovery=False)
