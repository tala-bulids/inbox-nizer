from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from models import Email, EmailPrediction
from priority import calculate_priority
from summarizer import summarize_email
from test_gmail import gmail_mocks, set_messages


def test_gmail_saves_summary_and_all_predictions(gmail_mocks, test_database):
    messages, _, classify = gmail_mocks
    set_messages(messages, 2)
    predictions = [
        {'category': 'Business', 'confidence': 0.8},
        {'category': 'Reminders', 'confidence': 0.7},
    ]
    classify.return_value = predictions
    with TestClient(app) as client:
        response = client.post('/gmail/messages')
    assert response.json()['success_count'] == 2
    emails = test_database.scalars(select(Email).order_by(Email.message_id)).all()
    assert len(emails) == 2
    for index, email in enumerate(emails, 1):
        assert email.summary == f'Clean body {index}'
        assert {p.category for p in email.predictions} == {'Business', 'Reminders'}
        assert email.priority_score == calculate_priority(predictions)['priority_score']


@pytest.mark.parametrize('summary', [None, '', 'Keep this summary'])
@pytest.mark.parametrize('has_predictions', [True, False])
def test_existing_email_summary_and_predictions(gmail_mocks, test_database, summary, has_predictions):
    email = Email(message_id='1', subject='Subject 1', body='Clean body 1', summary=summary,
                  priority_score=0.4, priority_level='medium')
    if has_predictions:
        email.predictions = [EmailPrediction(category='Personal', confidence=0.8)]
    test_database.add(email)
    test_database.commit()
    messages, _, _ = gmail_mocks
    for _ in range(2):
        set_messages(messages, 1)
        with TestClient(app) as client:
            result = client.post('/gmail/messages').json()
        assert result['success_count'] == 1
    test_database.expire_all()
    saved = test_database.scalar(select(Email).where(Email.message_id == '1'))
    assert saved.summary == (summary or 'Clean body 1')
    assert len(test_database.scalars(select(Email)).all()) == 1
    assert len(test_database.scalars(select(EmailPrediction)).all()) == 1
    assert saved.priority_score == 0.4
    assert saved.priority_level == 'medium'


def test_summary_failure_keeps_other_messages(gmail_mocks, test_database):
    messages, _, _ = gmail_mocks
    set_messages(messages, 2)
    with patch('email_pipeline.summarize_email', side_effect=[RuntimeError('private test detail'), 'Saved summary']):
        with TestClient(app) as client:
            response = client.post('/gmail/messages')
    assert response.status_code == 200
    assert response.json()['failed_count'] == 0
    assert response.json()['success_count'] == 2
    assert response.json()['enrichment_failed'] == 1
    emails = test_database.scalars(select(Email)).all()
    assert sorted((email.message_id, email.summary) for email in emails) == [('1', None), ('2', 'Saved summary')]
    assert len(test_database.scalars(select(EmailPrediction)).all()) == 2


def test_summary_and_combined_filters(test_database):
    high = Email(message_id='summary-high', summary='Important meeting tomorrow.',
                 priority_score=0.9, priority_level='high')
    high.predictions = [EmailPrediction(category='Business', confidence=0.9),
                        EmailPrediction(category='Reminders', confidence=0.8)]
    low = Email(message_id='summary-low', summary=None, priority_score=0.1, priority_level='low')
    low.predictions = [EmailPrediction(category='Business', confidence=0.7)]
    test_database.add_all([high, low])
    test_database.commit()
    with TestClient(app) as client:
        all_emails = client.get('/emails').json()['emails']
        assert {e['message_id']: e['summary'] for e in all_emails} == {
            'summary-high': 'Important meeting tomorrow.', 'summary-low': None
        }
        category = client.get('/emails', params={'category': 'Business'}).json()
        assert category['count'] == 2
        combined = client.get('/emails', params={'category': 'Business', 'priority_level': 'high'}).json()
        assert combined['count'] == 1
        assert combined['emails'][0]['summary'] == 'Important meeting tomorrow.'
        assert combined['emails'][0]['priority_score'] == 0.9
        assert len(combined['emails'][0]['predictions']) == 2
        assert client.get('/emails', params={'priority_level': 'invalid'}).status_code == 422


def test_backfill_updates_only_missing_summaries(test_database, capsys):
    import backfill_summaries
    test_database.add_all([
        Email(message_id='fill-null', subject='Report', body='Please send the report today.', summary=None),
        Email(message_id='fill-empty', subject='Meeting', body='The meeting starts at ten.', summary=''),
        Email(message_id='fill-existing', summary='Keep this text'),
    ])
    test_database.commit()
    session = MagicMock(wraps=test_database)
    session.close = MagicMock()
    with patch('backfill_summaries.SessionLocal', return_value=session):
        backfill_summaries.backfill_summaries()
    assert 'Updated 2 emails' in capsys.readouterr().out
    session.commit.assert_called_once()
    session.close.assert_called_once()
    assert test_database.scalar(select(Email).where(Email.message_id == 'fill-null')).summary == 'Please send the report today.'
    assert test_database.scalar(select(Email).where(Email.message_id == 'fill-empty')).summary == 'The meeting starts at ten.'
    assert test_database.scalar(select(Email).where(Email.message_id == 'fill-existing')).summary == 'Keep this text'


def test_backfill_failure_rolls_back(test_database):
    import backfill_summaries
    test_database.add_all([Email(message_id='rollback-1'), Email(message_id='rollback-2')])
    test_database.commit()
    session = MagicMock(wraps=test_database)
    session.close = MagicMock()
    with patch('backfill_summaries.SessionLocal', return_value=session), patch(
        'backfill_summaries.summarize_email', side_effect=['Pending summary', RuntimeError('test failure')]
    ):
        with pytest.raises(RuntimeError, match='test failure'):
            backfill_summaries.backfill_summaries()
    session.commit.assert_not_called()
    session.rollback.assert_called_once()
    session.close.assert_called_once()
    test_database.expire_all()
    assert all(email.summary is None for email in test_database.scalars(select(Email)))


def test_database_is_isolated(test_database):
    from database import engine
    assert test_database.get_bind().engine.url.database.endswith('_test')
    assert test_database.get_bind().engine.url.database != engine.url.database
    with pytest.raises(RuntimeError, match='Production database connections are disabled'):
        engine.connect()
