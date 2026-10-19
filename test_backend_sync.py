"""Gmail protocol boundaries are fake; persistence and locks use PostgreSQL."""
import base64
import json
from datetime import timezone
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from httplib2 import Response
from sqlalchemy import select, text
from cryptography.fernet import Fernet
from backend_config import encrypt, decrypt, ConfigurationError, redirect_uri
from backend_models import GmailAccount, OAuthCredential, ProcessingState
from models import Email, EmailEmbeddingChunk
from ownership import OwnedSession
from gmail_sync import sync_account
import gmail_sync
import email_pipeline
import gmail_service


def http_error(status):
    return HttpError(Response({'status': status}), b'{"error":{"message":"private"}}')


def message(body='Please send the report.', date='Wed, 16 Sep 2026 10:09:26 +0300'):
    return dict(internalDate='1789542566000', labelIds=['INBOX'], payload=dict(mimeType='text/plain',
        headers=[dict(name='Subject', value='Report'), dict(name='Date', value=date)],
        body={'data': base64.urlsafe_b64encode(body.encode()).decode()}))


@pytest.fixture
def sync_env(test_database, monkeypatch):
    service = Mock()
    service.users.return_value.getProfile.return_value.execute.return_value = {'historyId': '100'}
    service.users.return_value.messages.return_value.list.return_value.execute.return_value = {'messages': [{'id': 'm1'}]}
    service.users.return_value.messages.return_value.get.return_value.execute.return_value = message()
    service.users.return_value.history.return_value.list.return_value.execute.return_value = {'historyId': '101'}
    monkeypatch.setattr(gmail_sync, 'get_gmail_service', lambda *args: service)
    monkeypatch.setattr(email_pipeline, 'classify_email', lambda *args: [{'category': 'Business', 'confidence': .9}])
    with OwnedSession(bind=test_database.get_bind(), user_id=test_database.info['user_id'],
                      autoflush=False, join_transaction_mode='create_savepoint') as db:
        yield db, test_database.info['account_id'], service


def test_initial_then_incremental_new_message(sync_env):
    db, account, service = sync_env
    assert sync_account(db, account)['success_count'] == 1
    assert db.get(GmailAccount, account).history_id == '100'
    history = service.users().history().list.return_value.execute
    history.return_value = {'historyId': '200', 'history': [{'messagesAdded': [{'message': {'id': 'm2'}}]}]}
    assert sync_account(db, account)['success_count'] == 1
    assert db.query(Email).count() == 2
    assert db.get(GmailAccount, account).history_id == '200'
    service.users().messages().list.assert_called_once()


def test_history_pagination_and_duplicates(sync_env):
    db, account, service = sync_env
    sync_account(db, account)
    event = {'messagesAdded': [{'message': {'id': 'm2'}}], 'messages': [{'id': 'm2'}]}
    service.users().history().list.return_value.execute.side_effect = [
        {'historyId': '150', 'history': [event], 'nextPageToken': 'next'},
        {'historyId': '200', 'history': [event]}]
    assert sync_account(db, account)['success_count'] == 2
    assert db.query(Email).count() == 2
    assert db.get(GmailAccount, account).history_id == '200'
    assert service.users().history().list.call_args.kwargs['pageToken'] == 'next'


def test_full_pagination(sync_env):
    db, account, service = sync_env
    service.users().messages().list.return_value.execute.side_effect = [
        {'messages': [{'id': 'm1'}], 'nextPageToken': 'next'}, {'messages': [{'id': 'm2'}, {'id': 'm1'}]}]
    assert sync_account(db, account)['success_count'] == 2
    assert db.query(Email).count() == 2
    assert service.users().messages().list.call_args.kwargs['pageToken'] == 'next'


def test_expired_history_full_recovery(sync_env):
    db, account, service = sync_env
    sync_account(db, account)
    service.users().history().list.return_value.execute.side_effect = http_error(404)
    assert sync_account(db, account)['has_more'] is True
    assert sync_account(db, account)['success_count'] == 1
    assert db.query(Email).count() == 1
    assert service.users().messages().list.call_count == 2


def test_partial_failure_keeps_cursor_and_retry(sync_env):
    db, account, service = sync_env
    service.users().messages().list.return_value.execute.return_value = {'messages': [{'id': 'm1'}, {'id': 'm2'}]}
    fetch = service.users().messages().get.return_value.execute
    fetch.side_effect = [message(), http_error(503)]
    result = sync_account(db, account)
    assert result['success_count'] == result['failed_count'] == 1
    assert db.query(Email).count() == 1
    assert db.get(GmailAccount, account).history_id is None
    fetch.side_effect = None
    result = sync_account(db, account)
    assert result['success_count'] == 1 and db.query(Email).count() == 2
    assert db.get(GmailAccount, account).history_id == '100'


@pytest.mark.parametrize('status', [429, 500, 503])
def test_history_error_preserves_cursor(sync_env, status):
    db, account, service = sync_env
    sync_account(db, account)
    service.users().history().list.return_value.execute.side_effect = http_error(status)
    with pytest.raises(HTTPException) as error:
        sync_account(db, account)
    assert error.value.status_code == 503
    assert 'private' not in error.value.detail
    assert db.get(GmailAccount, account).history_id == '100'


def test_deleted_message_cascades(sync_env):
    db, account, service = sync_env
    sync_account(db, account)
    service.users().history().list.return_value.execute.return_value = {
        'historyId': '200', 'history': [{'messagesDeleted': [{'message': {'id': 'm1'}}]}]}
    service.users().messages().get.return_value.execute.side_effect = http_error(404)
    assert sync_account(db, account)['deleted'] == 1
    assert db.query(Email).count() == db.query(EmailEmbeddingChunk).count() == 0


def test_overlapping_sync_rejected(sync_env):
    from conftest import test_engine
    db, account, _ = sync_env
    with test_engine.connect() as other:
        other.execute(text('SELECT pg_advisory_xact_lock(724193, :account)'), {'account': account})
        with pytest.raises(HTTPException) as error:
            sync_account(db, account)
        assert error.value.status_code == 409


@pytest.mark.parametrize('stage', ['extract_email_body', 'classify_email', 'summarize_email', 'extract_action_items', 'refresh_facts', 'index_email'])
def test_enrichment_failure_source_survives_and_retry(sync_env, monkeypatch, stage):
    db, account, service = sync_env
    original = getattr(email_pipeline, stage)
    monkeypatch.setattr(email_pipeline, stage, Mock(side_effect=RuntimeError('private secret')))
    result = sync_account(db, account)
    assert result['success_count'] == 1 and result['enrichment_failed'] == 1
    assert db.query(Email).one().raw_payload == message()['payload']
    assert db.scalar(select(ProcessingState).where(ProcessingState.status == 'failed')) is not None
    monkeypatch.setattr(email_pipeline, stage, original)
    sync_account(db, account)  # No new history: still retries failed stages.
    assert db.scalar(select(ProcessingState).where(ProcessingState.status == 'failed')) is None
    assert db.query(Email).count() == 1


def test_idempotent_processing_and_timestamps(sync_env):
    db, account, _ = sync_env
    sync_account(db, account)
    email = db.query(Email).one()
    attempts = [s.attempts for s in db.scalars(select(ProcessingState))]
    email_pipeline.process_email(db, email)
    assert attempts == [s.attempts for s in db.scalars(select(ProcessingState))]
    assert email.sent_at.astimezone(timezone.utc).hour == 7 and email.sent_at.tzinfo is not None
    assert email.message_at.tzinfo is not None
    assert email.email_date == message()['payload']['headers'][1]['value']


@pytest.mark.parametrize('raw,status', [('', 'missing'), ('bad date', 'invalid'), ('20 Sep 2026 10:00:00', 'naive')])
def test_unknown_date_no_guess(raw, status):
    value, actual = email_pipeline.parse_header_date(raw)
    assert value is None and actual == status


def test_authenticated_encryption_and_rotation(monkeypatch):
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    monkeypatch.setenv('OAUTH_TOKEN_KEYS', old)
    encrypted = encrypt('synthetic-secret')
    assert 'synthetic-secret' not in encrypted
    assert decrypt(encrypted) == 'synthetic-secret'
    monkeypatch.setenv('OAUTH_TOKEN_KEYS', new + ',' + old)
    rotated = encrypt(decrypt(encrypted))
    monkeypatch.setenv('OAUTH_TOKEN_KEYS', new)
    assert decrypt(rotated) == 'synthetic-secret'
    with pytest.raises(ConfigurationError):
        decrypt(encrypted)


@pytest.mark.parametrize('value', ['plaintext', 'v1:invalid', 'v2:invalid'])
def test_invalid_ciphertext_safe(value):
    with pytest.raises(ConfigurationError):
        decrypt(value)


@pytest.mark.parametrize('uri', ['http://evil.invalid/auth/google/callback', 'https://example.org/redirect',
                              'https://user:secret@example.org/auth/google/callback', 'https://example.org/auth/google/callback?next=evil'])
def test_redirect_validation(monkeypatch, uri):
    monkeypatch.setenv('GOOGLE_REDIRECT_URI', uri)
    with pytest.raises(ConfigurationError):
        redirect_uri()


def test_refresh_persists_rotated_credentials(test_database, monkeypatch):
    account = test_database.get(GmailAccount, test_database.info['account_id'])
    initial = dict(token='old', refresh_token='refresh', token_uri='https://oauth2.googleapis.com/token', client_id='fake', client_secret='fake')
    row = OAuthCredential(account_id=account.id, ciphertext=encrypt(json.dumps(initial)))
    test_database.add(row)
    test_database.flush()
    credentials = Mock(valid=False)
    refresh = credentials.refresh
    credentials.to_json.return_value = json.dumps(dict(initial, token='new', refresh_token='rotated'))
    monkeypatch.setattr(gmail_service.Credentials, 'from_authorized_user_info', lambda *a: credentials)
    monkeypatch.setattr(gmail_service, 'build', Mock())
    gmail_service.get_gmail_service(test_database, account)
    assert json.loads(decrypt(row.ciphertext))['refresh_token'] == 'rotated'
    refresh.assert_called_once()


def test_revoked_credential_requires_reconnect(test_database, monkeypatch):
    account = test_database.get(GmailAccount, test_database.info['account_id'])
    test_database.add(OAuthCredential(account_id=account.id, ciphertext=encrypt('{}')))
    test_database.flush()
    credentials = Mock(valid=False)
    credentials.refresh.side_effect = RefreshError('private token invalid_grant')
    monkeypatch.setattr(gmail_service.Credentials, 'from_authorized_user_info', lambda *a: credentials)
    with pytest.raises(HTTPException) as error:
        gmail_service.get_gmail_service(test_database, account)
    assert error.value.status_code == 409
    assert account.status == 'reconnect_required'
    assert 'private' not in error.value.detail


def test_reconsent_preserves_existing_refresh_token(test_database):
    account = test_database.get(GmailAccount, test_database.info['account_id'])
    test_database.add(OAuthCredential(account_id=account.id, ciphertext=encrypt('{"refresh_token":"existing"}')))
    test_database.flush()
    credentials = Mock()
    credentials.to_json.return_value = '{"token":"new"}'
    gmail_service.save_credentials(test_database, account, credentials)
    saved = json.loads(decrypt(test_database.get(OAuthCredential, account.id).ciphertext))
    assert saved == {'token': 'new', 'refresh_token': 'existing'}


def test_first_consent_requires_refresh_token(test_database):
    account = test_database.get(GmailAccount, test_database.info['account_id'])
    credentials = Mock()
    credentials.to_json.return_value = '{"token":"new"}'
    with pytest.raises(HTTPException) as error:
        gmail_service.save_credentials(test_database, account, credentials)
    assert error.value.status_code == 409
    assert test_database.get(OAuthCredential, account.id) is None


def test_changed_content_reprocesses_without_duplicate_derivatives(sync_env):
    db, account, service = sync_env
    sync_account(db, account)
    old = db.query(EmailEmbeddingChunk).first().content_hash
    service.users().history().list.return_value.execute.return_value = {
        'historyId': '200', 'history': [{'labelsAdded': [{'message': {'id': 'm1'}}]}]}
    service.users().messages().get.return_value.execute.return_value = message('Please upload the document by Friday.')
    sync_account(db, account)
    email = db.query(Email).one()
    assert 'upload' in email.body
    assert len(email.predictions) == 1
    assert len(email.tasks) == 1 and 'Upload' in email.tasks[0].task
    assert db.query(EmailEmbeddingChunk).first().content_hash != old


def test_full_recovery_removes_missing_messages(sync_env):
    db, account, service = sync_env
    sync_account(db, account)
    service.users().history().list.return_value.execute.side_effect = http_error(404)
    service.users().messages().list.return_value.execute.return_value = {}
    assert sync_account(db, account)['has_more'] is True
    assert sync_account(db, account)['deleted'] == 1
    assert db.query(Email).count() == 0


def test_query_privacy_middleware_preserves_request_but_redacts_server_scope():
    import asyncio
    from privacy_middleware import PrivateQueryMiddleware
    scope = dict(type='http', query_string=b'code=synthetic-secret')
    output = []
    async def app(scope, receive, send):
        assert scope['query_string'] == b'code=synthetic-secret'
        await send(dict(type='http.response.start', status=200, headers=[]))
    async def send(message):
        output.append(message)
    asyncio.run(PrivateQueryMiddleware(app)(scope, None, send))
    assert scope['query_string'] == b''
    assert (b'cache-control', b'no-store') in output[0]['headers']


def test_sync_and_enrichment_errors_log_no_mailbox_identifiers(sync_env, monkeypatch, caplog):
    db, account, service = sync_env
    monkeypatch.setattr(email_pipeline, 'classify_email', Mock(side_effect=RuntimeError('PRIVATE_MESSAGE')))
    assert sync_account(db, account)['enrichment_failed'] == 1
    assert 'Email enrichment failed: stage=classify error_type=RuntimeError' in caplog.text
    service.users().history().list.return_value.execute.side_effect = RuntimeError('PRIVATE_PROVIDER_TOKEN')
    with pytest.raises(HTTPException):
        sync_account(db, account)
    assert 'Gmail sync failed: error_type=RuntimeError' in caplog.text
    assert 'PRIVATE_' not in caplog.text
    assert 'email=' not in caplog.text and 'account=' not in caplog.text


@pytest.mark.parametrize('stage', ['classify_email', 'summarize_email', 'extract_action_items'])
def test_changed_content_failure_retry_does_not_adopt_stale_results(sync_env, monkeypatch, stage):
    db, account, service = sync_env
    sync_account(db, account)
    original = getattr(email_pipeline, stage)
    service.users().history().list.return_value.execute.return_value = {
        'historyId': '200', 'history': [{'messages': [{'id': 'm1'}]}]}
    service.users().messages().get.return_value.execute.return_value = message('Please upload the signed document.')
    monkeypatch.setattr(email_pipeline, stage, Mock(side_effect=RuntimeError('temporary')))
    assert sync_account(db, account)['enrichment_failed'] == 1
    retry = Mock(wraps=original)
    monkeypatch.setattr(email_pipeline, stage, retry)
    service.users().history().list.return_value.execute.return_value = {'historyId': '201'}
    sync_account(db, account)
    retry.assert_called_once()
    assert db.scalar(select(ProcessingState).where(ProcessingState.status == 'failed')) is None
