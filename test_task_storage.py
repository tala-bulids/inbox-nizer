from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from main import app
from models import Email, EmailPrediction, EmailTask
from test_gmail import gmail_mocks, set_messages


def test_gmail_saves_tasks(gmail_mocks, test_database):
    messages, extract_body, classify = gmail_mocks
    set_messages(messages, 2)
    extract_body.return_value = None
    extract_body.side_effect = lambda payload: 'Please review the document and upload the signed copy.'
    classify.return_value = [{'category': 'Business', 'confidence': 0.8}, {'category': 'Reminders', 'confidence': 0.7}]
    with TestClient(app) as client:
        result = client.post('/gmail/messages').json()
    assert result['success_count'] == 2
    emails = test_database.scalars(select(Email)).all()
    assert len(emails) == 2
    for email in emails:
        assert [task.task for task in email.tasks] == ['Review the document', 'Upload the signed copy']
        assert len(email.predictions) == 2
        assert email.summary
        assert email.priority_score is not None


@pytest.mark.parametrize('has_tasks', [False, True])
@pytest.mark.parametrize('has_predictions', [False, True])
def test_existing_email_is_not_duplicated(gmail_mocks, test_database, has_tasks, has_predictions):
    email = Email(message_id='1', subject='Invoice', body='Please pay the invoice.',
                  summary='Keep summary', priority_score=0.9, priority_level='high')
    if has_tasks:
        email.tasks.append(EmailTask(task='Keep saved task', confidence=0.7))
    if has_predictions:
        email.predictions.append(EmailPrediction(category='Personal', confidence=0.8))
    test_database.add(email)
    test_database.commit()
    messages, body, _ = gmail_mocks
    body.side_effect = lambda payload: 'Please pay the invoice.'
    for _ in range(2):
        set_messages(messages, 1)
        with TestClient(app) as client:
            assert client.post('/gmail/messages').json()['success_count'] == 1
    test_database.expire_all()
    assert test_database.query(Email).count() == 1
    assert test_database.query(EmailPrediction).count() == 1
    assert test_database.query(EmailTask).count() == 1
    assert email.tasks[0].task == ('Keep saved task' if has_tasks else 'Pay the invoice')
    assert email.summary == 'Keep summary'
    assert email.priority_score == 0.9


def test_task_failure_preserves_source(gmail_mocks, test_database):
    messages, _, _ = gmail_mocks
    set_messages(messages, 2)
    with patch('email_pipeline.extract_action_items', side_effect=[RuntimeError('private'), [{'task': 'Review document', 'confidence': 0.8}]]):
        with TestClient(app) as client:
            result = client.post('/gmail/messages').json()
    assert result['success_count'] == 2
    assert result['failed_count'] == 0
    assert result['enrichment_failed'] == 1
    assert test_database.query(Email).count() == 2
    assert test_database.query(EmailPrediction).count() == 2
    assert test_database.query(EmailTask).count() == 1
    assert {e.message_id for e in test_database.scalars(select(Email))} == {'1', '2'}


def test_tasks_and_combined_filters(test_database):
    for message_id, level, category, task_count in [
        ('high-tasks', 'high', 'Business', 2),
        ('high-empty', 'high', 'Business', 0),
        ('low-tasks', 'low', 'Personal', 1),
    ]:
        email = Email(message_id=message_id, priority_score=0.9 if level=='high' else 0.1,
                      priority_level=level, summary='Saved summary')
        email.predictions.append(EmailPrediction(category=category, confidence=0.8))
        email.tasks = [EmailTask(task=f'Review document {i}', confidence=0.8) for i in range(task_count)]
        test_database.add(email)
    test_database.commit()
    with TestClient(app) as client:
        assert client.get('/emails').json()['count'] == 3
        yes = client.get('/emails', params={'has_tasks': 'true'}).json()
        assert yes['count'] == 2
        assert all(email['tasks'] for email in yes['emails'])
        no = client.get('/emails', params={'has_tasks': 'false'}).json()
        assert no['count'] == 1
        assert no['emails'][0]['tasks'] == []
        for value, expected in [('true', 'high-tasks'), ('false', 'high-empty')]:
            combined = client.get('/emails', params={'category':'Business','priority_level':'high','has_tasks':value}).json()
            assert combined['count'] == 1
            email = combined['emails'][0]
            assert email['message_id'] == expected
            assert email['summary'] == 'Saved summary'
            assert email['priority_score'] == 0.9
            assert email['predictions'] == [{'category': 'Business', 'confidence': 0.8}]
            if value == 'true':
                assert email['tasks'] == [{'task':f'Review document {i}', 'confidence':0.8,
                                          'deadline_text': None, 'deadline_date': None,
                                          'deadline_at': None, 'deadline_confidence': None} for i in range(2)]
        assert client.get('/emails', params={'has_tasks':'invalid'}).status_code == 422


def test_task_constraints_and_cascade(test_database):
    email = Email(message_id='cascade-test')
    email.tasks.append(EmailTask(task='Review document', confidence=0.8))
    test_database.add(email)
    test_database.commit()
    with pytest.raises(IntegrityError):
        with test_database.begin_nested():
            test_database.add(EmailTask(email_id=email.id, task='Review document', confidence=0.9))
            test_database.flush()
    test_database.execute(delete(Email).where(Email.id==email.id))
    test_database.flush()
    assert test_database.query(EmailTask).count() == 0


def test_backfill_skips_existing_and_non_actions(test_database, capsys):
    import backfill_tasks
    actionable = Email(message_id='task-fill', body='Please attend the meeting.')
    no_action = Email(message_id='no-task', body='Thanks for your message.')
    existing = Email(message_id='keep-task', body='Please pay the invoice.')
    existing.tasks.append(EmailTask(task='Keep saved task', confidence=0.7))
    test_database.add_all([actionable, no_action, existing])
    test_database.commit()
    session = MagicMock(wraps=test_database)
    session.close = MagicMock()
    with patch('backfill_tasks.SessionLocal', return_value=session):
        backfill_tasks.backfill_tasks()
        assert 'Processed 2 emails\nAdded 1 tasks' in capsys.readouterr().out
        backfill_tasks.backfill_tasks()
        assert 'Added 0 tasks' in capsys.readouterr().out
    assert session.close.call_count == 2
    assert test_database.query(EmailTask).count() == 2
    assert actionable.tasks[0].task == 'Attend the meeting'
    assert existing.tasks[0].task == 'Keep saved task'


def test_backfill_failure_rolls_back(test_database):
    import backfill_tasks
    test_database.add_all([Email(message_id='rollback-a'), Email(message_id='rollback-b')])
    test_database.commit()
    session = MagicMock(wraps=test_database)
    session.close = MagicMock()
    with patch('backfill_tasks.SessionLocal', return_value=session), patch(
        'backfill_tasks.extract_action_items', side_effect=[[{'task':'Pay invoice','confidence':0.8}], RuntimeError('failed')]
    ):
        with pytest.raises(RuntimeError, match='failed'):
            backfill_tasks.backfill_tasks()
    session.rollback.assert_called_once()
    session.close.assert_called_once()
    session.commit.assert_not_called()
    assert test_database.query(EmailTask).count() == 0


def test_tasks_use_test_database(test_database):
    from database import engine
    assert test_database.get_bind().engine.url.database.endswith('_test')
    assert test_database.get_bind().engine.url.database != engine.url.database
    with pytest.raises(RuntimeError, match='Production database connections are disabled'):
        engine.connect()
