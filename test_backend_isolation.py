"""Exercise real scoped sessions and PostgreSQL, including pre-ranking isolation."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from fastapi import Depends
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, func, update
from sqlalchemy.orm import aliased
from sqlalchemy.exc import IntegrityError
from main import app
from database import get_db
from authentication import current_user, auth_session, issue_token
from ownership import OwnedSession, OwnershipError
from backend_models import AppUser, AccessToken, GmailAccount, OAuthCredential, ProcessingState
from models import Email, EmailPrediction, EmailTask, EmailEmbeddingChunk, EmailFact, EmailFactState
from semantic_index import index_email
from fact_store import refresh_facts, fact_evidence
from semantic_search import semantic_search
from rag_retrieval import retrieve_rag_chunks
from rag_service import answer_email_question, _validate_citations, InvalidGeneration
from backend_config import encrypt, decrypt, ConfigurationError


@pytest.fixture
def two_users(test_database):
    db = test_database
    other = AppUser(name='other-user', active=True)
    db.add(other)
    db.flush()
    account = GmailAccount(user_id=other.id, address='other@example.invalid', status='connected')
    db.add(account)
    db.flush()
    a = Email(account_id=db.info['account_id'], message_id='same-id', subject='Alpha trip',
              body='Booking reference: ALPHA1\nTravel date: 16-Oct-2026', priority_level='high')
    b = Email(account_id=account.id, message_id='same-id', subject='Private other trip',
              body='Booking reference: PRIVATE2\nTravel date: 17-Nov-2026', priority_level='high')
    db.add_all([a, b])
    db.flush()
    for email in (a, b):
        email.predictions = [EmailPrediction(category='Travel & Bookings', confidence=.9)]
        email.tasks = [EmailTask(task='Confirm booking', confidence=.9)]
        index_email(email, db)
        refresh_facts(email, db)
    for ident in (a.account_id, b.account_id):
        db.add(OAuthCredential(account_id=ident, ciphertext=encrypt('secret-' + str(ident))))
    db.commit()
    return a, b, other


@pytest.fixture
def owned(test_database):
    with OwnedSession(bind=test_database.get_bind(), user_id=test_database.info['user_id'],
                      autoflush=False, join_transaction_mode='create_savepoint') as db:
        yield db


def test_same_message_id_across_accounts(two_users, test_database):
    a, b, _ = two_users
    assert a.message_id == b.message_id and a.account_id != b.account_id
    with pytest.raises(IntegrityError), test_database.begin_nested():
        test_database.add(Email(account_id=a.account_id, message_id=a.message_id))
        test_database.flush()


@pytest.mark.parametrize('model', [Email, EmailPrediction, EmailTask, EmailEmbeddingChunk, EmailFact, EmailFactState])
def test_all_email_models_are_scoped(two_users, owned, model):
    a, b, _ = two_users
    rows = owned.scalars(select(model)).all()
    assert rows
    assert all((row.id if model is Email else row.email_id) == a.id for row in rows)
    if model is Email:
        assert owned.get(Email, b.id) is None
        assert len(owned.get(Email, a.id).tasks) == 1


def test_aliases_counts_and_subquery_are_scoped(two_users, owned):
    alias = aliased(Email)
    assert len(owned.scalars(select(alias)).all()) == 1
    assert owned.query(Email).count() == 1
    assert owned.scalar(select(func.count()).select_from(select(Email).subquery())) == 1


def test_credentials_scoped(two_users, owned):
    a, b, _ = two_users
    assert owned.get(OAuthCredential, b.account_id) is None
    rows = owned.scalars(select(OAuthCredential)).all()
    assert len(rows) == 1 and rows[0].account_id == a.account_id


@pytest.mark.parametrize('statement', [text('SELECT * FROM emails'), select(Email.__table__), update(Email).values(body='bad'),
    select(Email.id, EmailTask.__table__.c.task), select(Email, EmailTask.__table__),
    select(Email.id, select(EmailTask.__table__.c.task).limit(1).scalar_subquery()),
    select(Email.id).where(text('1=1'))])
def test_unscoped_sql_rejected(owned, statement):
    with pytest.raises(OwnershipError):
        owned.execute(statement)


def test_parent_reassignment_denied(two_users, owned):
    a, b, _ = two_users
    email = owned.get(Email, a.id)
    email.account_id = b.account_id
    with pytest.raises(OwnershipError):
        owned.flush()


@pytest.mark.parametrize('model', [Email, EmailTask, OAuthCredential])
def test_cross_user_inserts_denied(two_users, owned, model):
    _, b, _ = two_users
    values = {Email: dict(account_id=b.account_id, message_id='bad'),
              EmailTask: dict(email_id=b.id, task='bad', confidence=.9),
              OAuthCredential: dict(account_id=b.account_id, ciphertext='bad')}
    owned.add(model(**values[model]))
    with pytest.raises(OwnershipError):
        owned.flush()


def test_api_list_detail_filters_and_no_secrets(two_users):
    a, b, _ = two_users
    with TestClient(app) as client:
        response = client.get('/emails?category=Travel%20%26%20Bookings&priority_level=high&has_tasks=true&limit=1')
        assert response.status_code == 200
        assert response.json()['total'] == 1
        assert response.json()['emails'][0]['id'] == a.id
        assert client.get(f'/emails/{b.id}').status_code == 404
        assert client.get(f'/emails/{b.id + 99999}').status_code == 404
        for url in ('/emails', f'/emails/{a.id}', '/gmail/accounts'):
            data = client.get(url).text
            assert all(word not in data for word in ('ciphertext', 'refresh_token', 'access_token', 'secret-', 'raw_payload'))
        assert client.post(f'/gmail/accounts/{b.account_id}/sync').status_code == 404
        assert client.delete(f'/gmail/accounts/{b.account_id}/connection').status_code == 404


def test_vectors_scoped_before_limit_and_reranking(two_users, owned, monkeypatch):
    a, b, _ = two_users
    import rag_retrieval
    import rag_ranking
    observed = []
    original = rag_ranking.rank_candidates
    def checked(db, query, candidates):
        observed.extend(c['email_id'] for c in candidates)
        assert all(c['email_id'] == a.id for c in candidates)
        return original(db, query, candidates)
    monkeypatch.setattr(rag_ranking, 'rank_candidates', checked)
    assert all(x['email'].id == a.id for x in semantic_search(owned, 'booking', 1))
    chunks = retrieve_rag_chunks(owned, 'booking', limit=1)
    assert chunks and observed == [a.id]
    assert all(c['email_id'] == a.id for c in chunks)


def test_facts_reject_other_user(two_users, owned):
    _, b, _ = two_users
    _, audit = fact_evidence(owned, [dict(email_id=b.id, chunk_id=1, content=b.body)])
    assert audit['facts'] == []


def test_ask_discards_injected_cross_user_source(two_users, owned, monkeypatch):
    _, b, _ = two_users
    import rag_service
    monkeypatch.setattr(rag_service, 'retrieve_rag_chunks', lambda *a, **k: [dict(email_id=b.id, chunk_id=1,
        chunk_index=0, score=.99, text=b.body)])
    llm = Mock()
    result = answer_email_question(owned, 'What is my booking reference?', llm)
    assert result['status'] == 'insufficient_evidence'
    assert result['sources'] == []
    llm.generate.assert_not_called()


def test_citations_cross_user_rejected(two_users):
    a, b, _ = two_users
    with pytest.raises(InvalidGeneration):
        _validate_citations(f'Private answer [email_id={b.id}]', [dict(email_id=a.id)])


@pytest.mark.parametrize('url', ['/emails', '/search/semantic?q=test', '/gmail/accounts', '/auth/google'])
def test_authentication_required(test_database, url):
    app.dependency_overrides.pop(current_user)
    app.dependency_overrides.pop(get_db)
    with TestClient(app) as client:
        assert client.get(url, headers={'X-User-ID': str(test_database.info['user_id'])}).status_code == 401
        assert client.get(url, headers={'Authorization': 'Bearer arbitrary-user-id'}).status_code == 401


def test_token_authentication_expiry_and_revocation(test_database):
    from authentication import current_user, bearer
    from fastapi.security import HTTPAuthorizationCredentials
    from fastapi import HTTPException
    user = test_database.get(AppUser, test_database.info['user_id'])
    value = issue_token(test_database, user)
    credential = HTTPAuthorizationCredentials(scheme='Bearer', credentials=value)
    assert current_user(credential, test_database).id == user.id
    row = test_database.scalar(select(AccessToken))
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    test_database.flush()
    with pytest.raises(HTTPException):
        current_user(credential, test_database)
    test_database.delete(row)
    test_database.flush()
    with pytest.raises(HTTPException):
        current_user(credential, test_database)


def test_disconnect_keeps_data_and_removes_secret(two_users, test_database):
    a, b, _ = two_users
    with TestClient(app) as client:
        assert client.delete(f'/gmail/accounts/{a.account_id}/connection').status_code == 200
    test_database.expire_all()
    assert test_database.get(OAuthCredential, a.account_id) is None
    assert test_database.get(OAuthCredential, b.account_id) is not None
    assert test_database.get(Email, a.id) is not None


def test_user_deletion_cascades(two_users, test_database):
    a, b, user = two_users
    a_id, b_id = a.id, b.id
    test_database.delete(user)
    test_database.commit()
    test_database.expire_all()
    assert test_database.scalar(select(Email.id).where(Email.id == b_id)) is None
    assert test_database.scalar(select(EmailEmbeddingChunk.id).where(EmailEmbeddingChunk.email_id == b_id)) is None
    assert test_database.scalar(select(EmailFact.id).where(EmailFact.email_id == b_id)) is None
    assert test_database.get(Email, a_id) is not None


def test_two_bearer_tokens_end_to_end(two_users, test_database, monkeypatch):
    a, b, other = two_users
    user = test_database.get(AppUser, test_database.info['user_id'])
    tokens = [(issue_token(test_database, user), a.id, b.id),
              (issue_token(test_database, other), b.id, a.id)]
    test_database.commit()
    app.dependency_overrides.pop(current_user)

    def authenticated_db(principal=Depends(current_user)):
        with OwnedSession(bind=test_database.get_bind(), user_id=principal.id, autoflush=False,
                          join_transaction_mode='create_savepoint') as db:
            yield db
    app.dependency_overrides[get_db] = authenticated_db
    import rag_api
    provider = Mock()
    monkeypatch.setattr(rag_api, 'get_llm_provider', lambda: provider)
    with TestClient(app) as client:
        for token, own_id, foreign_id in tokens:
            headers = {'Authorization': 'Bearer ' + token}
            assert client.get('/emails', headers=headers).json()['emails'][0]['id'] == own_id
            assert client.get(f'/emails/{foreign_id}', headers=headers).status_code == 404
            found = client.get('/search/semantic?q=booking', headers=headers).json()['results']
            assert found and all(r['email']['id'] == own_id for r in found)
            provider.generate.return_value = f'Supported trip [email_id={own_id}]'
            result = client.post('/ask', headers=headers, json={'question': 'Describe my trip'}).json()
            assert result['status'] == 'answered'
            assert all(s['email_id'] == own_id for s in result['sources'])
            if provider.generate.called:
                content = str(provider.generate.call_args)
                assert f'[SOURCE email_id={foreign_id} ' not in content
            provider.generate.return_value = f'Other trip [email_id={foreign_id}]'
            rejected = client.post('/ask', headers=headers, json={'question': 'Describe my trip'})
            assert rejected.status_code == 200
            assert rejected.json()['status'] == 'insufficient_evidence'
            assert rejected.json()['citations'] == []
            assert 'Other trip' not in rejected.json()['answer']


def test_vector_sql_contains_ownership_before_limit(two_users, owned):
    from sqlalchemy import event
    queries = []
    connection = owned.get_bind()
    def record(conn, cursor, statement, parameters, context, executemany):
        if '<=>' in statement:
            queries.append(statement)
    event.listen(connection, 'before_cursor_execute', record)
    try:
        retrieve_rag_chunks(owned, 'trip')
    finally:
        event.remove(connection, 'before_cursor_execute', record)
    assert queries
    for sql in queries:
        assert 'gmail_accounts.user_id' in sql
        assert sql.index('gmail_accounts.user_id') < sql.index('ORDER BY') < sql.index('LIMIT')
