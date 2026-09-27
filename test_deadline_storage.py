import base64
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import rebuild_tasks_and_deadlines as rebuild
import routes
from main import app
from models import Email, EmailPrediction, EmailTask


def _gmail(monkeypatch, body, sent='Mon, 21 Sep 2026 14:00:00 +0300'):
    service = Mock()
    messages = service.users.return_value.messages.return_value
    messages.list.return_value.execute.return_value = {'messages': [{'id': 'deadline-message'}]}
    messages.get.return_value.execute.return_value = {'payload': {
        'mimeType': 'text/plain',
        'headers': [{'name': 'Subject', 'value': 'Application'}, {'name': 'Date', 'value': sent}],
        'body': {'data': base64.urlsafe_b64encode(body.encode()).decode()},
    }}
    monkeypatch.setattr(routes, 'get_gmail_service', lambda: service)
    monkeypatch.setattr(routes, 'classify_email', Mock(return_value=[{'category': 'Business', 'confidence': 0.8}]))


def test_gmail_stores_deadlines_and_does_not_duplicate(monkeypatch, test_database):
    _gmail(monkeypatch, 'Please submit your application by Friday.\nReply tomorrow at 10 AM.')
    with TestClient(app) as client:
        for _ in range(2):
            assert client.get('/gmail/messages').json()['success_count'] == 1
        saved = client.get('/emails', params={'has_deadline': 'true'}).json()
    assert saved['count'] == 1
    tasks = saved['emails'][0]['tasks']
    assert tasks[0]['deadline_text'] == 'by Friday'
    assert tasks[0]['deadline_date'] == '2026-09-25'
    assert tasks[0]['deadline_at'] is None
    assert tasks[0]['deadline_confidence'] == 0.9
    moment = datetime.fromisoformat(tasks[1]['deadline_at'].replace('Z', '+00:00'))
    assert moment == datetime(2026, 9, 22, 10, tzinfo=timezone(timedelta(hours=3)))
    assert tasks[1]['deadline_date'] is None
    assert test_database.query(Email).count() == 1
    assert test_database.query(EmailTask).count() == 2
    assert test_database.query(EmailPrediction).count() == 1


def test_existing_task_is_enriched_without_replacing_it(monkeypatch, test_database):
    email = Email(message_id='deadline-message', body='Submit your application', summary='Keep summary',
                  priority_score=0.4, priority_level='medium')
    email.tasks = [EmailTask(task='Submit your application', confidence=0.8)]
    email.predictions = [EmailPrediction(category='Personal', confidence=0.6)]
    test_database.add(email)
    test_database.commit()
    task_id = email.tasks[0].id
    _gmail(monkeypatch, 'Please submit your application by Friday.')
    with TestClient(app) as client:
        for _ in range(2):
            assert client.get('/gmail/messages').json()['success_count'] == 1
    test_database.expire_all()
    assert len(email.tasks) == 1
    assert email.tasks[0].id == task_id
    assert email.tasks[0].task == 'Submit your application'
    assert email.tasks[0].deadline_date == date(2026, 9, 25)
    assert email.summary == 'Keep summary'
    assert email.priority_score == 0.4
    assert email.predictions[0].category == 'Personal'


@pytest.mark.parametrize('body, expected', [
    ('Submit your application by Friday.', None),
    ('Submit your application by 30 September 2026.', date(2026, 9, 30)),
])
def test_bad_header_keeps_absolute_and_text_deadlines(monkeypatch, test_database, body, expected):
    _gmail(monkeypatch, body, 'bad header')
    with TestClient(app) as client:
        assert client.get('/gmail/messages').json()['success_count'] == 1
    task = test_database.scalar(select(EmailTask))
    assert task.deadline_text
    assert task.deadline_date == expected
    assert task.deadline_at is None


def test_deadline_filters_combine_with_existing_filters(test_database):
    examples = [
        ('calendar', 'high', 'Business', {'deadline_date': date(2026, 9, 30)}),
        ('event', 'low', 'Personal', {'deadline_text': 'before arrival'}),
        ('timed', 'high', 'Business', {'deadline_at': datetime(2026, 9, 30, 10, tzinfo=timezone.utc)}),
        ('plain', 'high', 'Business', {}),
        ('empty-text', 'low', 'Personal', {'deadline_text': ''}),
        ('no-tasks', 'low', 'Personal', None),
    ]
    for message_id, level, category, deadline in examples:
        email = Email(message_id=message_id, summary='Keep summary', priority_level=level, priority_score=0.5)
        email.predictions = [EmailPrediction(category=category, confidence=0.8)]
        if deadline is not None:
            email.tasks = [EmailTask(task='Review document', confidence=0.8, **deadline)]
        test_database.add(email)
    test_database.commit()
    with TestClient(app) as client:
        assert client.get('/emails').json()['count'] == 6
        for value, expected in [('true', {'calendar', 'event', 'timed'}), ('false', {'plain', 'no-tasks', 'empty-text'})]:
            result = client.get('/emails', params={'has_deadline': value}).json()
            assert {e['message_id'] for e in result['emails']} == expected
        result = client.get('/emails', params={'has_deadline': True, 'has_tasks': True, 'category': 'Business', 'priority_level': 'high'}).json()
        assert {e['message_id'] for e in result['emails']} == {'calendar', 'timed'}
        assert all(e['summary'] == 'Keep summary' and e['predictions'] and e['priority_score'] == 0.5 for e in result['emails'])
        assert client.get('/emails', params={'has_deadline': True, 'has_tasks': False}).json()['count'] == 0
        assert client.get('/emails', params={'has_deadline': 'invalid'}).status_code == 422


def test_gmail_semantic_dedup_is_persisted(monkeypatch, test_database):
    _gmail(monkeypatch, 'يرجى إصدار بطاقة الصعود إلكترونياً قبل الوصول إلى المطار.\nإصدار بطاقة صعود الطائرة.')
    with TestClient(app) as client:
        assert client.get('/gmail/messages').json()['success_count'] == 1
    task = test_database.scalars(select(EmailTask)).one()
    assert task.deadline_text == 'قبل الوصول إلى المطار'
    assert task.deadline_date is task.deadline_at is None


def _rebuild_session(monkeypatch, db):
    session = MagicMock(wraps=db)
    session.close = Mock()
    monkeypatch.setattr(rebuild, 'SessionLocal', lambda: session)
    return session


def _snapshot(email):
    return (email.id, email.message_id, email.sender, email.email_date, email.subject,
            email.body, email.summary, email.created_at, email.priority_level, email.priority_score,
            [(p.id, p.category, p.confidence) for p in email.predictions])


def test_rebuild_preserves_email_data_and_removes_stale_tasks(monkeypatch, test_database, capsys):
    for message_id, body in [('real', 'Submit your application by Friday.'), ('promo', 'Register now and unlock benefits.')]:
        email = Email(message_id=message_id, body=body, email_date='Mon, 21 Sep 2026 14:00:00 +0300',
                      sender='sender@example.com', summary='Keep summary', priority_score=0.6, priority_level='high')
        email.predictions = [EmailPrediction(category='Business', confidence=0.8)]
        email.tasks = [EmailTask(task='Old task', confidence=0.8)]
        test_database.add(email)
    test_database.commit()
    emails = test_database.scalars(select(Email).order_by(Email.id)).all()
    before = [_snapshot(e) for e in emails]
    session = _rebuild_session(monkeypatch, test_database)
    for _ in range(2):
        rebuild.rebuild_tasks_and_deadlines()
        assert capsys.readouterr().out == 'Processed 2 emails\nAdded 1 tasks\nTasks with deadlines 1\n'
    test_database.expire_all()
    assert [_snapshot(e) for e in emails] == before
    assert emails[0].tasks[0].deadline_date == date(2026, 9, 25)
    assert emails[1].tasks == []
    assert session.close.call_count == 2


@pytest.mark.parametrize('failure', ['extract', 'commit'])
def test_rebuild_rolls_back_all_changes(monkeypatch, test_database, failure):
    for number in range(2):
        email = Email(message_id=f'rollback-{number}', body='Submit your application by Friday.')
        email.tasks = [EmailTask(task='Original task', confidence=0.7)]
        test_database.add(email)
    test_database.commit()
    before = [(t.id, t.task) for t in test_database.scalars(select(EmailTask).order_by(EmailTask.id))]
    session = _rebuild_session(monkeypatch, test_database)
    if failure == 'commit':
        session.commit.side_effect = RuntimeError('test failure')
    else:
        monkeypatch.setattr(rebuild, 'extract_action_items', Mock(side_effect=[[], RuntimeError('test failure')]))
    with pytest.raises(RuntimeError, match='test failure'):
        rebuild.rebuild_tasks_and_deadlines()
    session.rollback.assert_called_once()
    session.close.assert_called_once()
    assert [(t.id, t.task) for t in test_database.scalars(select(EmailTask).order_by(EmailTask.id))] == before
