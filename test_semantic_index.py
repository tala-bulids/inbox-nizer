from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select, delete, text
from sqlalchemy.exc import IntegrityError, StatementError, DBAPIError

import embedding_service
from models import Email, EmailEmbeddingChunk
from semantic_index import index_email, index_all_emails, content_hash


def saved_email(db, body='Your flight AB123 is confirmed.', **kwargs):
    email = Email(message_id=kwargs.pop('message_id', 'semantic-index'), body=body, **kwargs)
    db.add(email)
    db.flush()
    return email


def chunks(db):
    return db.scalars(select(EmailEmbeddingChunk).order_by(EmailEmbeddingChunk.chunk_index)).all()


def test_persist_skip_update_and_hash(test_database, fake_embedding_encoder):
    email = saved_email(test_database, subject='Flight')
    assert index_email(email, test_database)['created'] == 1
    row = chunks(test_database)[0]
    assert len(row.embedding) == 384 and row.content_hash == content_hash(row.chunk_text)
    assert index_email(email, test_database)['skipped'] == 1
    assert len(fake_embedding_encoder.calls) == 1
    email.body = 'Your flight AB456 is confirmed for Friday.'
    assert index_email(email, test_database)['updated'] == 1
    assert len(fake_embedding_encoder.calls) == 2
    assert 'AB456' in chunks(test_database)[0].chunk_text
    assert content_hash('same') == content_hash('same')
    assert content_hash('same', 'other-model') != content_hash('same')


def test_stale_chunks_empty_content_and_model_change(test_database, monkeypatch):
    email = saved_email(test_database, body=' '.join(f'word{i}' for i in range(900)))
    assert index_email(email, test_database)['created'] > 1
    email.body = 'A short useful message.'
    assert index_email(email, test_database)['deleted'] > 0
    assert len(chunks(test_database)) == 1
    monkeypatch.setattr(embedding_service, 'MODEL_NAME', 'replacement-model')
    counts = index_email(email, test_database)
    assert counts['created'] == counts['deleted'] == 1
    assert chunks(test_database)[0].embedding_model == 'replacement-model'
    email.body = ''
    assert index_email(email, test_database)['deleted'] == 1
    assert chunks(test_database) == []


def test_failure_preserves_existing_vectors(test_database, monkeypatch):
    email = saved_email(test_database)
    index_email(email, test_database)
    original = chunks(test_database)[0].content_hash
    email.body = 'Changed content'
    def fail(*args):
        raise RuntimeError('encoder unavailable')
    monkeypatch.setattr(embedding_service, 'embed_passages', fail)
    with pytest.raises(RuntimeError):
        index_email(email, test_database)
    assert chunks(test_database)[0].content_hash == original
    assert test_database.scalar(select(Email.id)) == email.id


def test_database_failure_rolls_back_chunk_changes_only(test_database, monkeypatch):
    email = saved_email(test_database)
    index_email(email, test_database)
    original = chunks(test_database)[0].content_hash
    email.body = 'Updated flight details'
    monkeypatch.setattr(embedding_service, 'embed_passages', lambda texts: [[float('nan')] + [0.0] * 383])
    with pytest.raises((DBAPIError, StatementError)):
        index_email(email, test_database)
    test_database.expire_all()
    assert chunks(test_database)[0].content_hash == original
    assert test_database.scalar(select(Email.body)) == 'Updated flight details'


def test_vector_dimension_unique_constraint_and_delete_cascade(test_database):
    email = saved_email(test_database)
    index_email(email, test_database)
    values = dict(email_id=email.id, chunk_index=0, chunk_text='copy', content_hash='a' * 64,
                  embedding_model=embedding_service.MODEL_NAME, embedding=[1.0] + [0.0] * 383)
    with pytest.raises(IntegrityError):
        with test_database.begin_nested():
            test_database.add(EmailEmbeddingChunk(**values))
            test_database.flush()
    with pytest.raises(StatementError):
        with test_database.begin_nested():
            test_database.add(EmailEmbeddingChunk(**{**values, 'chunk_index': 1, 'embedding': [1.0, 2.0]}))
            test_database.flush()
    assert test_database.scalar(text("SELECT format_type(atttypid, atttypmod) FROM pg_attribute WHERE attrelid = 'email_embedding_chunks'::regclass AND attname = 'embedding'")) == 'vector(384)'
    test_database.execute(delete(Email).where(Email.id == email.id))
    test_database.flush()
    assert chunks(test_database) == []


def test_all_emails_pagination_and_counts(test_database):
    for index in range(3):
        saved_email(test_database, message_id=f'index-{index}')
    counts = index_all_emails(test_database, batch_size=1)
    assert counts['processed'] == counts['created'] == 3
    assert index_all_emails(test_database, batch_size=2)['skipped'] == 3


def test_backfill_commits_closes_and_reports(test_database, capsys):
    import backfill_email_embeddings as backfill
    saved_email(test_database)
    session = MagicMock(wraps=test_database)
    session.close = MagicMock()
    with patch.object(backfill, 'SessionLocal', return_value=session):
        assert backfill.main()['created'] == 1
    session.commit.assert_called_once()
    session.close.assert_called_once()
    assert 'Created 1 chunks' in capsys.readouterr().out


def test_backfill_rolls_back_whole_job_on_failure(test_database):
    import backfill_email_embeddings as backfill
    for i in range(2):
        saved_email(test_database, message_id=f'failure-{i}')
    test_database.commit()
    session = MagicMock(wraps=test_database)
    session.close = MagicMock()
    with patch.object(backfill, 'SessionLocal', return_value=session), patch(
        'embedding_service.embed_passages', side_effect=[[[1.0] + [0.0] * 383], RuntimeError('failure')]
    ):
        with pytest.raises(RuntimeError):
            backfill.main()
    session.rollback.assert_called_once()
    session.close.assert_called_once()
    session.commit.assert_not_called()
    assert chunks(test_database) == []
