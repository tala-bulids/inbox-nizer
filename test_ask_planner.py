from datetime import timedelta
import pytest
from ask_plan import plan
from rag_service import answer_email_question
from test_ask_deeper import NOW,clock
from test_relational_facts import indexed
from test_rag_hybrid import SpyLLM
from test_backend_isolation import two_users,owned

@pytest.mark.parametrize('q', ['وش آخر المستجدات؟','وش جاني هالأسبوع؟','What changed recently?','latest updates'])
def test_digest_plan(q):
    assert plan(q).kind=='recent_digest' and plan(q).window

@pytest.mark.parametrize('q',['هل استلمت نشرة من سالم؟','Have I received a newsletter from Salim?'])
def test_existence_plan(q):
    assert plan(q).kind=='existence'


def test_digest_complete_condition_and_noise(test_database):
    good=indexed(test_database,'Your payment due date is tomorrow unless the invoice was already paid.',subject='Invoice')
    good.message_at=NOW-timedelta(days=1)
    bad=indexed(test_database,'Shop now and book your trip with a discount.',subject='Sale',message_id='ad')
    bad.message_at=NOW;test_database.flush()
    llm=SpyLLM();result=answer_email_question(test_database,'What changed recently?',llm)
    assert result['status']=='answered' and llm.calls==0
    assert 'unless the invoice was already paid' in result['answer']
    assert result['citations']==[{'email_id':good.id}]
    assert '28 September 2026' in result['answer']


def test_sender_existence_without_embeddings(test_database):
    from models import Email
    email=Email(account_id=test_database.info['account_id'],message_id='newsletter',sender='Salim <salim@example.invalid>',subject='Weekly newsletter',body='A useful weekly digest.')
    test_database.add(email);test_database.flush()
    answer=answer_email_question(test_database,'Have I received a newsletter from Salim?',SpyLLM())
    assert answer['status']=='answered' and answer['citations']==[{'email_id':email.id}]


def test_body_mention_not_sender(test_database):
    email=indexed(test_database,'Newsletter mentions Salim.',subject='Weekly newsletter')
    email.sender='Other <other@example.invalid>';test_database.flush()
    assert answer_email_question(test_database,'Have I received a newsletter from Salim?',SpyLLM())['status']=='insufficient_evidence'


def test_existence_tenant_isolation(two_users,owned):
    assert answer_email_question(owned,'Have I received a newsletter from Private?',SpyLLM())['status']=='insufficient_evidence'


@pytest.mark.parametrize('q',['when am I travelling to Birch?','متى flight حقي؟','When is my flight?'])
def test_paraphrase_bundle(test_database,q):
    indexed(test_database,'Travel date: 20-Nov-2027\nDestination: Birch\nDeparture time: 08:15\nArrival time: 10:25\nFlight number: AB123',subject='Trip')
    result=answer_email_question(test_database,q,SpyLLM(),min_score=0)
    assert result['status']=='answered' and '08:15' in result['answer'] and 'AB123' in result['answer']


def test_followup_only_inherits_question_not_answer():
    assert 'K A' in plan('طيب K&A بس؟',history=['وش آخر تحديث على طلبي؟']).question.upper()
    assert plan('when is my flight?',history=['bad prior topic']).question=='when is my flight?'

def test_clarification_api_roundtrip(test_database):
    from fastapi.testclient import TestClient
    from main import app
    emails=[]
    for index,date in enumerate(('20-Nov-2027','21-Nov-2027')):
        emails.append(indexed(test_database,f'Travel date: {date}\nDestination: Birch',subject=f'Trip {index}',message_id=f'clarify-{index}'))
    test_database.commit()
    with TestClient(app) as client:
        first=client.post('/ask',json={'question':'When is my flight?','min_score':0}).json()
        assert first['status']=='needs_clarification'
        selected=first['clarification_options'][0]['email_id']
        second=client.post('/ask',json={'question':'When is my flight?','email_id':selected,'min_score':0})
        assert second.status_code==200 and second.json()['status']=='answered'
        assert second.json()['citations']==[{'email_id':selected}]


def test_bounded_history_api(test_database):
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as client:
        assert client.post('/ask',json={'question':'hello','history':['hello']*5}).status_code==422
        assert client.post('/ask',json={'question':'hello','history':['x'*2001]}).status_code==422

def test_plural_status_composes_distinct_supported_messages(test_database):
    for i in range(2):
        e=indexed(test_database,'Your application has been accepted.',subject=f'Application {i}',message_id=f'plural-{i}')
        e.message_at=NOW-timedelta(days=i+1)
    test_database.flush()
    answer=answer_email_question(test_database,'وش آخر تحديث على طلباتي؟',SpyLLM(),min_score=0)
    assert answer['status']=='answered' and len(answer['citations'])==2


def test_named_fact_mismatch_does_not_generate(test_database):
    indexed(test_database,'Travel date: 20-Nov-2027\nDestination: Birch',subject='Trip')
    llm=SpyLLM()
    answer=answer_email_question(test_database,'When is my trip to Cedar?',llm,min_score=0)
    assert answer['status']=='insufficient_evidence' and llm.calls==0

def test_explicit_not_selected_is_not_positive(test_database):
    email=indexed(test_database,'Unfortunately, you were not selected for the bootcamp.',subject='Bootcamp')
    email.message_at=NOW-timedelta(days=1);test_database.flush()
    answer=answer_email_question(test_database,'انقبلت بمعسكر؟',SpyLLM(),min_score=0)
    assert answer['status']=='answered' and 'not selected' in answer['answer']
    assert answer['citations']==[{'email_id':email.id}]
