from datetime import datetime, date, timezone
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from main import app
from models import EmailPrediction
from email_display_order import newest_first
from test_task_api import add, get
from test_inbox_api import inbox
from test_relational_facts import indexed
from test_rag_hybrid import SpyLLM
from rag_service import answer_email_question
from fact_roles import intent
import embedding_service


def test_category_union_before_pagination(inbox, test_database):
    for row, category in zip(inbox[:3], ['Personal', 'Business', 'Promotions']):
        test_database.add(EmailPrediction(email_id=row.id, category=category, confidence=.9))
    test_database.flush()
    with TestClient(app) as client:
        response = client.get('/emails', params=[('categories','Personal'),('categories','Business'),('limit',1)])
        assert response.status_code == 200
        assert response.json()['total'] == 2
        assert response.json()['count'] == 1
        options = client.get('/email-categories').json()
        assert 'Personal' in options and 'Travel & Bookings' in options


def test_search_orders_only_selected_set_with_real_dates():
    def item(id, sent=None, raw=None):
        return {'email':SimpleNamespace(id=id,sent_at=sent,message_at=None,email_date=raw), 'score':1/id}
    rows = [item(1,raw='unknown'),item(2,raw='Tue, 10 Mar 2026 10:00:00 +0300'),
            item(3,datetime(2026,3,11,tzinfo=timezone.utc)),item(4,datetime(2026,3,9,tzinfo=timezone.utc))]
    assert [r['email'].id for r in newest_first(rows)] == [3,2,4,1]
    assert rows[0]['email'].id == 1


def test_task_dates_not_insertion_order_undated_last(test_database):
    recent = add(test_database,'recent',deadline_date=date(2028,5,2))
    old = add(test_database,'old',deadline_at=datetime(2028,4,1,9,tzinfo=timezone.utc))
    text = add(test_database,'unknown',deadline_text='soon')
    assert [r['id'] for r in get().json()['tasks']] == [recent.id,old.id,text.id]
    assert [r['id'] for r in get({'sort_order':'asc'}).json()['tasks']] == [old.id,recent.id,text.id]


@pytest.mark.parametrize('question', ['متى ب اسافر لمدينة الأمل؟','متى بسافر لمدينة الأمل؟',
    'متى راح أسافر إلى مدينة الأمل؟','امتى باسافر لمدينة الأمل؟','متى سوف نسافر إلى مدينة الأمل؟'])
def test_arabic_travel_paraphrases_persisted_facts(test_database, monkeypatch, question):
    monkeypatch.setattr(embedding_service,'embed_query',lambda q:[1.0]+[0.0]*383)
    email = indexed(test_database,'travel_date: 2028-03-12\norigin: مدينة النور\ndestination: مدينة الأمل')
    llm = SpyLLM()
    result = answer_email_question(test_database,question,llm,chunk_limit=1)
    from rag_bundle import wanted
    assert ('12 مارس 2028' if wanted(question) else '2028-03-12') in result['answer']
    assert result['citations'] == [{'email_id':email.id}]
    assert llm.calls == 0


@pytest.mark.parametrize('question', ['متى لا اسافر إلى مدينة الأمل؟','متى اسافر أو نسافر؟'])
def test_travel_normalization_keeps_unsafe_guards(question):
    assert intent(question) is None
