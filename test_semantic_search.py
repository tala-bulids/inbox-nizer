from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from models import Email, EmailEmbeddingChunk
from semantic_index import index_email
from semantic_search import semantic_search
from test_semantic_index import saved_email
from test_gmail import gmail_mocks, set_messages


def indexed_mail(db):
    travel = saved_email(db, subject='تم تأكيد حجز الرحلة', body='رحلة من الرياض إلى جدة يوم الجمعة AB123.', message_id='travel')
    invoice = saved_email(db, subject='Invoice', body='Please pay invoice INV-22.', message_id='invoice')
    index_email(travel, db)
    index_email(invoice, db)
    return travel, invoice


@pytest.mark.parametrize('query', ['متى سفرتي لجدة؟', 'When is my flight to Jeddah?', 'رحلة flight جدة'])
def test_retrieval_ranking_and_api_payload(test_database, query):
    travel, invoice = indexed_mail(test_database)
    matches = semantic_search(test_database, query)
    assert [item['email'].id for item in matches] == [travel.id, invoice.id]
    assert matches[0]['score'] > matches[1]['score']
    with TestClient(app) as client:
        response = client.get('/search/semantic', params={'q': query})
        assert response.status_code == 200
        result = response.json()
        assert result['query'] == query and result['count'] == 2
        assert result['results'][0]['email']['id'] == travel.id
        assert 'body' not in result['results'][0]['email']
        assert 'AB123' in result['results'][0]['matched_text']
        assert client.get(f'/emails/{travel.id}').json()['body'] == travel.body


def test_threshold_limit_and_no_duplicate_emails(test_database):
    travel, invoice = indexed_mail(test_database)
    original = test_database.scalar(select(EmailEmbeddingChunk).where(EmailEmbeddingChunk.email_id == travel.id))
    # More duplicate chunks than the initial candidate pool must not hide other emails.
    for i in range(1, 125):
        test_database.add(EmailEmbeddingChunk(email_id=travel.id, chunk_index=i, chunk_text=f'Flight chunk {i}',
                                            embedding=original.embedding, embedding_model=original.embedding_model,
                                            content_hash=str(i).zfill(64)))
    test_database.flush()
    results = semantic_search(test_database, 'flight', limit=2)
    assert len(results) == 2 and results[0]['email'].id == travel.id
    assert len(semantic_search(test_database, 'flight', limit=1)) == 1
    assert [item['email'].id for item in semantic_search(test_database, 'flight', min_score=0.8)] == [travel.id]
    assert len(semantic_search(test_database, 'flight', min_score=0)) == 2
    assert semantic_search(test_database, 'unrelated topic', min_score=0.8) == []


@pytest.mark.parametrize('params', [
    {}, {'q': ''}, {'q': '   '}, {'q': 'query', 'limit': 0}, {'q': 'query', 'limit': 51},
    {'q': 'query', 'min_score': 1.1}, {'q': 'query', 'min_score': -1.1}, {'q': 'query', 'min_score': 'nan'},
])
def test_search_validation(params):
    with TestClient(app) as client:
        assert client.get('/search/semantic', params=params).status_code == 422


def test_empty_index_does_not_load_model(fake_embedding_encoder):
    with TestClient(app) as client:
        assert client.get('/search/semantic', params={'q': 'hello'}).json()['results'] == []
    assert not fake_embedding_encoder.calls


@pytest.mark.parametrize('failure', [RuntimeError('private path or token'), ValueError('private model configuration')])
def test_search_model_failure_is_safe(test_database, failure):
    indexed_mail(test_database)
    with patch('embedding_service.embed_query', side_effect=failure):
        with TestClient(app) as client:
            response = client.get('/search/semantic', params={'q': 'flight'})
    assert response.status_code == 503 and 'private' not in response.text


def test_gmail_indexes_once_and_retries_missing_vectors(gmail_mocks, test_database, fake_embedding_encoder):
    messages, _, _ = gmail_mocks
    for _ in range(2):
        set_messages(messages, 1)
        with TestClient(app) as client:
            assert client.get('/gmail/messages').json()['success_count'] == 1
    assert test_database.query(EmailEmbeddingChunk).count() == 1
    assert len(fake_embedding_encoder.calls) == 1


def test_gmail_embedding_failure_does_not_lose_email(gmail_mocks, test_database):
    messages, _, _ = gmail_mocks
    set_messages(messages, 1)
    with patch('embedding_service.embed_passages', side_effect=RuntimeError('private')):
        with TestClient(app) as client:
            result = client.get('/gmail/messages').json()
    assert result['success_count'] == 1
    assert test_database.query(Email).count() == 1
    assert test_database.query(EmailEmbeddingChunk).count() == 0
    set_messages(messages, 1)
    with TestClient(app) as client:
        assert client.get('/gmail/messages').json()['success_count'] == 1
    assert test_database.query(EmailEmbeddingChunk).count() == 1


def test_gmail_reindexes_finalized_missing_summary(gmail_mocks, test_database):
    email = saved_email(test_database, subject='Subject 1', body='Old useful text', summary=None, message_id='1')
    index_email(email, test_database)
    old = test_database.scalar(select(EmailEmbeddingChunk.content_hash))
    messages, _, _ = gmail_mocks
    set_messages(messages, 1)
    with TestClient(app) as client:
        assert client.get('/gmail/messages').json()['success_count'] == 1
    assert test_database.scalar(select(EmailEmbeddingChunk.content_hash)) != old
