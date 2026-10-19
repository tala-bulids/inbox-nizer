import gmail_sync
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

import routes
from main import app
from models import Email, EmailPrediction, EmailTask


@pytest.fixture
def inbox(test_database):
    rows = []
    for number in range(25):
        email = Email(message_id=f'inbox-{number}', subject=f'Subject {number}',
                      body=f'Full body {number}', summary=f'Summary {number}',
                      created_at=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=(number * 7) % 25),
                      priority_score=None if number == 24 else (number % 5) / 4,
                      priority_level='high' if number % 2 == 0 else 'low')
        test_database.add(email)
        rows.append(email)
    test_database.commit()
    return rows


def _get(params=None):
    with TestClient(app) as client:
        return client.get('/emails', params=params)


def test_default_pagination(inbox):
    data = _get().json()
    assert (data['count'], data['total'], data['limit'], data['offset']) == (20, 25, 20, 0)
    expected = sorted(inbox, key=lambda e: (e.created_at, e.id), reverse=True)[:20]
    assert [e['id'] for e in data['emails']] == [e.id for e in expected]
    assert all('body' not in email and 'summary' in email for email in data['emails'])


@pytest.mark.parametrize('limit, offset, count', [(5, 3, 5), (10, 20, 5), (100, 0, 25), (5, 99, 0)])
def test_custom_pages(inbox, limit, offset, count):
    data = _get({'limit': limit, 'offset': offset, 'sort_by': 'id', 'sort_order': 'asc'}).json()
    assert (data['count'], data['total'], data['limit'], data['offset']) == (count, 25, limit, offset)
    assert [e['id'] for e in data['emails']] == [e.id for e in inbox[offset:offset + limit]]


@pytest.mark.parametrize('params', [
    {'limit': 0}, {'limit': -1}, {'limit': 101}, {'limit': 'bad'}, {'limit': 1.5},
    {'offset': -1}, {'offset': 'bad'}, {'offset': 1.5},
    {'sort_by': 'body'}, {'sort_by': 'id; DROP TABLE emails'}, {'sort_order': 'sideways'},
])
def test_invalid_parameters(params):
    assert _get(params).status_code == 422


@pytest.mark.parametrize('field', ['created_at', 'id', 'priority_score'])
@pytest.mark.parametrize('order', ['asc', 'desc'])
def test_sorting(inbox, field, order):
    known = [e for e in inbox if getattr(e, field) is not None]
    missing = [e for e in inbox if getattr(e, field) is None]
    expected = sorted(known, key=lambda e: (getattr(e, field), e.id), reverse=order == 'desc') + missing
    data = _get({'sort_by': field, 'sort_order': order, 'limit': 100}).json()
    assert [e['id'] for e in data['emails']] == [e.id for e in expected]


def test_equal_timestamps_have_stable_pages(inbox, test_database):
    for email in inbox:
        email.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    test_database.commit()
    first = _get({'limit': 10}).json()['emails']
    second = _get({'limit': 10, 'offset': 10}).json()['emails']
    assert [e['id'] for e in first + second] == [e.id for e in reversed(inbox)][0:20]


def test_combined_filters_before_count_sort_and_pagination(test_database):
    matches = []
    configurations = [
        ('Job Application', 'high', True, True),
        ('Job Application', 'high', True, True),
        ('Job Application', 'high', True, True),
        ('Personal', 'high', True, True),
        ('Job Application', 'low', True, True),
        ('Job Application', 'high', False, False),
        ('Job Application', 'high', True, False),
    ]
    for number, (category, priority, has_tasks, deadline) in enumerate(configurations):
        email = Email(message_id=f'filter-{number}', priority_level=priority, priority_score=number / 10)
        email.predictions = [EmailPrediction(category=category, confidence=0.8),
                             EmailPrediction(category='Other', confidence=0.7)]
        if has_tasks:
            email.tasks = [EmailTask(task='Submit application', confidence=0.9,
                                    deadline_text='before arrival' if deadline else None)]
        test_database.add(email)
        if number < 3:
            matches.append(email)
    test_database.commit()
    params = {'category': 'Job Application', 'priority_level': 'high', 'has_tasks': True,
              'has_deadline': True, 'limit': 1, 'offset': 1, 'sort_by': 'priority_score', 'sort_order': 'asc'}
    result = _get(params).json()
    assert (result['total'], result['count']) == (3, 1)
    assert result['emails'][0]['id'] == matches[1].id
    params.update(sort_order='desc', offset=0)
    assert _get(params).json()['emails'][0]['id'] == matches[2].id
    params.update(has_deadline=False, offset=0)
    assert _get(params).json()['total'] == 1
    params.update(has_tasks=False)
    assert _get(params).json()['total'] == 1


def test_empty_inbox():
    assert _get().json() == {'count': 0, 'total': 0, 'limit': 20, 'offset': 0, 'emails': []}


def test_detail_returns_complete_stored_email(monkeypatch, test_database):
    email = Email(message_id='detail-message', sender='sender@example.com', email_date='Mon, 21 Sep 2026 10:00:00 +0300',
                  subject='Application', body='Full stored body', summary='Stored summary',
                  priority_score=0.8, priority_level='high')
    email.predictions = [EmailPrediction(category='Business', confidence=0.9),
                         EmailPrediction(category='Job Application', confidence=0.8)]
    email.tasks = [EmailTask(task='Submit application', confidence=0.9, deadline_text='by 30 September 2026',
                            deadline_date=date(2026, 9, 30), deadline_confidence=0.9),
                   EmailTask(task='Reply tomorrow', confidence=0.9, deadline_text='tomorrow at 10 AM',
                             deadline_at=datetime(2026, 9, 22, 7, tzinfo=timezone.utc), deadline_confidence=0.9)]
    test_database.add(email)
    test_database.commit()
    gmail = Mock(side_effect=AssertionError('Detail must not call Gmail'))
    monkeypatch.setattr(gmail_sync, 'get_gmail_service', gmail)
    with TestClient(app) as client:
        listing = client.get('/emails').json()['emails'][0]
        response = client.get(f'/emails/{email.id}')
    assert response.status_code == 200
    detail = response.json()
    assert detail == {**listing, 'body': 'Full stored body', 'processing': []}
    assert detail['message_id'] == 'detail-message'
    assert detail['from'] == 'sender@example.com'
    assert detail['date'] == email.email_date
    assert detail['summary'] == 'Stored summary'
    assert detail['priority_score'] == 0.8
    assert detail['priority_level'] == 'high'
    assert detail['created_at']
    assert {p['category'] for p in detail['predictions']} == {'Business', 'Job Application'}
    assert detail['tasks'][0] == {'task': 'Submit application', 'confidence': 0.9,
                                 'deadline_text': 'by 30 September 2026', 'deadline_date': '2026-09-30',
                                 'deadline_at': None, 'deadline_confidence': 0.9}
    assert datetime.fromisoformat(detail['tasks'][1]['deadline_at'].replace('Z', '+00:00')) == email.tasks[1].deadline_at
    gmail.assert_not_called()


def test_detail_empty_relationships_and_null_body(test_database):
    email = Email(message_id='detail-empty')
    test_database.add(email)
    test_database.commit()
    with TestClient(app) as client:
        data = client.get(f'/emails/{email.id}').json()
    assert data['body'] is None
    assert data['tasks'] == data['predictions'] == []


def test_missing_email_returns_404():
    with TestClient(app) as client:
        response = client.get('/emails/2147483647')
    assert response.status_code == 404
    assert response.json() == {'detail': 'Email not found'}


def test_inbox_uses_sql_pagination_without_body_or_per_email_queries(inbox, test_database):
    test_database.expunge_all()
    statements = []
    connection = test_database.connection()
    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            statements.append(statement.lower())
    event.listen(connection, 'before_cursor_execute', capture)
    try:
        response = _get({'limit': 10, 'offset': 5})
    finally:
        event.remove(connection, 'before_cursor_execute', capture)
    assert response.status_code == 200
    assert len(statements) == 4  # count, page, predictions, tasks
    page = next(sql for sql in statements if 'limit' in sql)
    assert 'offset' in page
    assert 'emails.body' not in page
    assert all('emails.body' not in sql for sql in statements)


def test_test_database_starts_clean(test_database):
    assert test_database.get_bind().engine.url.database.endswith('_test')
    assert test_database.query(Email).count() == 0
    assert test_database.query(EmailPrediction).count() == 0
    assert test_database.query(EmailTask).count() == 0
