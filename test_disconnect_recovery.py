import json
from unittest.mock import Mock
from backend_models import GmailAccount, GmailSyncState, OAuthCredential
from models import Email
from backend_config import encrypt, decrypt
from test_browser_auth import browser, login, headers, oauth_start
from test_backend_sync import message
import account_routes
import gmail_service


def test_disconnect_reconnect_keeps_checkpoint_source_and_account(browser, test_database, monkeypatch):
    db = test_database
    account = db.get(GmailAccount, db.info['account_id'])
    original = {'mimeType': 'text/plain', 'body': {'data': 'c2F2ZWQ='}}
    email = Email(account_id=account.id, message_id='saved', raw_payload=original, body='saved')
    db.add(email)
    db.add(GmailSyncState(account_id=account.id, generation='resume-same-account', mode='full',
                         anchor='100', target='100', pending=['saved'], listing_done=True))
    db.add(OAuthCredential(account_id=account.id, ciphertext=encrypt('{"refresh_token":"old"}')))
    db.commit()
    client, _ = browser
    session = login(browser)
    assert client.delete(f'/gmail/accounts/{account.id}/connection', headers=headers(session)).status_code == 200
    db.expire_all()
    assert db.get(OAuthCredential, account.id) is None
    assert db.get(Email, email.id).raw_payload == original
    assert db.get(GmailSyncState, account.id).pending == ['saved']
    provider = Mock(side_effect=AssertionError('Disconnected Gmail must not build a client'))
    monkeypatch.setattr(gmail_service, 'build', provider)
    assert client.post(f'/gmail/accounts/{account.id}/sync', headers=headers(session)).status_code == 409
    provider.assert_not_called()
    flow = oauth_start(browser, monkeypatch)
    flow.credentials.to_json.return_value = json.dumps({
        'token': 'new-token', 'refresh_token': 'new-refresh', 'client_id': 'fake',
        'client_secret': 'fake', 'token_uri': 'https://oauth2.googleapis.com/token'})
    service = Mock()
    service.users().getProfile.return_value.execute.return_value = {'emailAddress': account.address}
    monkeypatch.setattr(account_routes, 'build', lambda *a, **k: service)
    response = client.get('/auth/google/callback', params={'state': 'fake-state', 'code': 'fake-code'},
                          headers={'accept': 'text/html'}, follow_redirects=False)
    assert response.status_code == 303 and response.headers['location'].endswith('result=success')
    db.expire_all()
    assert db.query(GmailAccount).filter(GmailAccount.user_id == db.info['user_id']).count() == 1
    assert db.get(GmailAccount, account.id).status == 'connected'
    assert db.get(GmailSyncState, account.id).pending == ['saved']
    assert db.get(Email, email.id).raw_payload == original
    assert json.loads(decrypt(db.get(OAuthCredential, account.id).ciphertext))['refresh_token'] == 'new-refresh'

    # Resume via the real credential loader with a fake network boundary.
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    credentials = Mock(valid=True)
    monkeypatch.setattr(gmail_service.Credentials, 'from_authorized_user_info', lambda *args: credentials)
    service.users().messages().get.return_value.execute.return_value = message()
    monkeypatch.setattr(gmail_service, 'build', lambda *a, **k: service)
    monkeypatch.setattr('email_pipeline.classify_email', lambda *a: [{'category': 'Business', 'confidence': .9}])
    response = client.post(f'/gmail/accounts/{account.id}/sync', headers=headers(client.get('/auth/session')))
    assert response.status_code == 200 and response.json()['success_count'] == 1
    db.expire_all()
    assert db.query(Email).count() == 1
    assert db.get(GmailSyncState, account.id) is None
    assert db.get(GmailAccount, account.id).history_id == '100'
