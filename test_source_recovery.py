from collections import Counter
from unittest.mock import Mock
from sqlalchemy import select
from fastapi.testclient import TestClient
from main import app
from backend_models import GmailAccount, GmailSyncState
from models import Email
from test_backend_sync import sync_env, message, http_error
import gmail_sync


def test_explicit_source_retry_is_bounded_and_keeps_every_failed_id(sync_env):
    db, account, service = sync_env
    pending = [{'id': f'bad-{i}', 'attempts': 3} for i in range(7)]
    db.add(GmailSyncState(account_id=account, generation='manual-recovery', mode='full',
                         anchor='100', target='100', pending=pending, listing_done=True))
    db.commit()
    service.users().messages().get.return_value.execute.side_effect = http_error(503)
    result = gmail_sync.sync_account(db, account, retry_failed=True)
    assert result['count'] == result['failed_count'] == 5
    assert result['recovery_required'] and not result['has_more']
    state = db.get(GmailSyncState, account)
    assert {item['id'] for item in state.pending} == {item['id'] for item in pending}
    assert db.get(GmailAccount, account).history_id is None


def test_expired_page_token_keeps_failed_ids(sync_env):
    db, account, service = sync_env
    pending = [{'id': 'bad', 'attempts': 3}]
    db.add(GmailSyncState(account_id=account, generation='expired-page', mode='full',
                         anchor='100', target='100', pending=pending, listing_done=False, page_token='expired'))
    db.commit()
    service.users().messages().list.return_value.execute.side_effect = http_error(400)
    assert gmail_sync.sync_account(db, account)['has_more']
    assert db.get(GmailSyncState, account).pending == pending
    assert db.get(GmailAccount, account).history_id is None


def test_poison_id_does_not_block_pages_and_survives_reopening(sync_env, monkeypatch):
    db, account, service = sync_env
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    monkeypatch.setattr(gmail_sync, 'MESSAGE_LIMIT', 2)
    service.users().messages().list.return_value.execute.side_effect = [
        {'messages': [{'id': 'bad'}, {'id': 'good1'}], 'nextPageToken': 'p2'},
        {'messages': [{'id': 'good2'}, {'id': 'bad'}]},
    ]
    calls = Counter()
    repaired = False
    def fetch(**kwargs):
        ident = kwargs['id']
        calls[ident] += 1
        return Mock(execute=Mock(side_effect=http_error(503) if ident == 'bad' and not repaired else None,
                                return_value=message()))
    service.users().messages().get.side_effect = fetch
    for _ in range(8):
        result = gmail_sync.sync_account(db, account)
        db.expire_all()  # Each request reopens persisted checkpoint state.
    assert set(db.scalars(select(Email.message_id))) == {'good1', 'good2'}
    assert calls == {'bad': 3, 'good1': 1, 'good2': 1}
    assert not result['has_more'] and result['recovery_required']
    assert db.get(GmailAccount, account).history_id is None
    state = db.get(GmailSyncState, account)
    assert state.pending == [{'id': 'bad', 'attempts': 3}]
    with TestClient(app) as client:
        data = client.get('/gmail/accounts').json()['accounts'][0]
        assert data['source_failed_count'] == 1 and not data['sync_pending']
        assert client.post(f'/gmail/accounts/{account}/sync?retry_failed=true').json()['recovery_required']
    assert calls['bad'] == 4
    assert db.get(GmailAccount, account).history_id is None
    repaired = True
    with TestClient(app) as client:
        result = client.post(f'/gmail/accounts/{account}/sync?retry_failed=true').json()
    assert not result['has_more'] and not result['recovery_required']
    db.expire_all()
    assert db.get(GmailSyncState, account) is None
    assert db.get(GmailAccount, account).history_id == '100'
    assert set(db.scalars(select(Email.message_id))) == {'bad', 'good1', 'good2'}


def test_history_failure_preserves_existing_source_and_cursor(sync_env, monkeypatch):
    db, account, service = sync_env
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    gmail_sync.sync_account(db, account)
    source = db.query(Email).one().raw_payload
    service.users().history().list.return_value.execute.return_value = {
        'historyId': '200', 'history': [{'messages': [{'id': 'm1'}, {'id': 'm2'}]}]}
    def fetch(**kwargs):
        return Mock(execute=Mock(side_effect=http_error(503) if kwargs['id'] == 'm1' else None, return_value=message()))
    service.users().messages().get.side_effect = fetch
    for _ in range(5):
        gmail_sync.sync_account(db, account)
    db.expire_all()
    assert db.get(GmailAccount, account).history_id == '100'
    assert db.scalar(select(Email).where(Email.message_id == 'm1')).raw_payload == source
    assert db.query(Email).count() == 2
    assert db.get(GmailSyncState, account).pending == [{'id': 'm1', 'attempts': 3}]
