from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from main import app
from models import Email, EmailTask
from backend_models import AppUser, GmailAccount
from authentication import current_user, Principal


def get(params=None):
    with TestClient(app) as client:
        return client.get('/tasks', params=params)


def add(db, name, account_id=None, **deadline):
    email = Email(message_id=name, account_id=account_id, subject='Source '+name,
                  sender='sender@example.invalid', email_date='raw date',
                  sent_at=datetime(2026, 10, 1, tzinfo=timezone.utc))
    task = EmailTask(task=name, confidence=.9, **deadline)
    email.tasks = [task]
    db.add(email)
    db.commit()
    return task


def test_owned_listing_metadata_deadlines_and_stable_pages(test_database):
    tasks = [add(test_database, str(i), deadline_date=date(2026, 10, 12) if i%2 else None)
             for i in range(5)]
    response = get({'limit': 2, 'offset': 1, 'sort_order': 'asc'})
    assert response.status_code == 200
    data = response.json()
    assert (data['count'], data['total'], data['limit'], data['offset']) == (2, 5, 2, 1)
    assert [t['id'] for t in data['tasks']] == [tasks[1].id, tasks[2].id]
    row = data['tasks'][0]
    assert row['deadline_date'] == '2026-10-12'
    assert row['email']['subject'] == 'Source 1'
    assert row['email']['sender'] == 'sender@example.invalid'
    assert row['email']['sent_at'].startswith('2026-10-01')
    assert 'body' not in row['email'] and 'confidence' not in row
    assert [t['id'] for t in get().json()['tasks']] == [t.id for t in reversed(tasks)]
    assert get({'offset':99}).json()['count'] == 0


def test_filters_before_limit_with_normalized_and_text_deadlines(test_database):
    add(test_database, 'no deadline')
    add(test_database, 'date', deadline_date=date(2026, 10, 12))
    add(test_database, 'time', deadline_at=datetime(2026, 10, 12, 9, tzinfo=timezone.utc))
    add(test_database, 'text', deadline_text='before arrival')
    assert get({'has_deadline':True,'limit':1}).json()['total'] == 3
    result = get({'has_deadline':False}).json()
    assert result['total'] == 1 and result['tasks'][0]['task'] == 'no deadline'


def test_two_user_scope_foreign_rows_never_consume_limit(test_database):
    own = add(test_database, 'own')
    other = AppUser(name='other', active=True)
    test_database.add(other)
    test_database.flush()
    account = GmailAccount(user_id=other.id, address='other@example.invalid',status='connected')
    test_database.add(account)
    test_database.flush()
    for i in range(4):
        add(test_database, 'foreign'+str(i), account_id=account.id)
    data = get({'limit':1}).json()
    assert data['total'] == 1 and data['tasks'][0]['id'] == own.id
    # Explicit principal restriction also fails closed if an injected session differs.
    app.dependency_overrides[current_user] = lambda: Principal(other.id)
    assert get().json()['total'] == 0


def test_other_user_owned_session(test_database):
    from database import get_db
    from ownership import OwnedSession
    own = add(test_database, 'first')
    user = AppUser(name='second',active=True)
    test_database.add(user)
    test_database.flush()
    account = GmailAccount(user_id=user.id,address='second@example.invalid',status='connected')
    test_database.add(account)
    test_database.flush()
    foreign = add(test_database,'second task',account_id=account.id)
    def session():
        with OwnedSession(bind=test_database.connection(),user_id=user.id,join_transaction_mode='create_savepoint') as db:
            yield db
    app.dependency_overrides[get_db] = session
    app.dependency_overrides[current_user] = lambda: Principal(user.id)
    data = get().json()
    assert [t['id'] for t in data['tasks']] == [foreign.id]
    assert own.id not in [t['id'] for t in data['tasks']]


@pytest.mark.parametrize('params', [{'limit':0},{'limit':101},{'limit':'bad'},{'offset':-1},{'offset':1.5},{'sort_order':'bad'},{'has_deadline':'bad'}])
def test_invalid_query(params):
    assert get(params).status_code == 422


def test_empty_and_optional_fields(test_database):
    assert get().json() == dict(count=0,total=0,limit=20,offset=0,tasks=[])
    email = Email(message_id='optional')
    email.tasks = [EmailTask(task='Reply',confidence=.7)]
    test_database.add(email)
    test_database.commit()
    row = get().json()['tasks'][0]
    assert row['deadline_at'] is None and row['deadline_date'] is None
    assert row['email']['sent_at'] is None


def test_requires_authentication():
    app.dependency_overrides.pop(current_user)
    assert get().status_code == 401


def test_openapi_response_is_typed():
    schema = app.openapi()
    response = schema['paths']['/tasks']['get']['responses']['200']['content']['application/json']['schema']
    assert response['$ref'].endswith('/TaskPage')
