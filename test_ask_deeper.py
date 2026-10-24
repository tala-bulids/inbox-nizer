"""Contract, temporal SQL, grounded bundle and negative-evidence regressions."""
from datetime import datetime,timedelta,timezone
import pytest
from rag_time import scope
from rag_service import answer_email_question,prepare_rag_request
from test_relational_facts import indexed
from test_rag_hybrid import SpyLLM
from test_backend_isolation import two_users,owned

NOW=datetime(2026,10,12,12,tzinfo=timezone.utc)

@pytest.fixture(autouse=True)
def clock(monkeypatch):
    monkeypatch.setattr('rag_time.now',lambda:NOW)

@pytest.mark.parametrize('question,days', [('انقبلت بمعسكر؟',14),('جاني قبول قريب؟',14),('وش صار على طلباتي آخر أسبوعين؟',14),('What is the latest application update?',14)])
def test_default_and_explicit_recent_scope(question,days):
    window=scope(question)
    assert window['start']==NOW-timedelta(days=days) and window['end']==NOW

@pytest.mark.parametrize('question,start,end', [
 ('ماذا وصل أمس؟',datetime(2026,10,11,tzinfo=timezone.utc),datetime(2026,10,12,tzinfo=timezone.utc)),
 ('last week',datetime(2026,10,5,tzinfo=timezone.utc),datetime(2026,10,12,tzinfo=timezone.utc)),
 ('هذا الشهر',datetime(2026,10,1,tzinfo=timezone.utc),NOW),
])
def test_calendar_scope(question,start,end):
    assert scope(question)['start']==start and scope(question)['end']==end


def test_conversational_trip_bundle_same_record_only(test_database):
    body='Travel date: 20-Nov-2027\nDeparture time: 08:15\nArrival time: 10:25\nOrigin: Alder\nDestination: Birch\nBooking reference: REF-39\nDeparture airport: Alder International\nArrival airport: Birch Airport'
    email=indexed(test_database,body,subject='Trip to Birch')
    llm=SpyLLM()
    result=answer_email_question(test_database,'When is my trip to Birch?',llm,min_score=0)
    assert result['status']=='answered' and llm.calls==0
    for value in ('20 November 2027','08:15','10:25','REF-39','Alder International','Birch Airport'):
        assert value in result['answer']
    assert result['citations']==[{'email_id':email.id}]
    assert result['verification']=='source_supported'


def test_multiple_itineraries_do_not_mix(test_database):
    body='Travel date: 20-Nov-2027\nDestination: Birch\nDeparture time: 08:15\nTravel date: 21-Nov-2027\nDestination: Cedar\nDeparture time: 17:10'
    indexed(test_database,body,subject='Travel records')
    answer=answer_email_question(test_database,'When is my trip to Birch?',SpyLLM(),min_score=0)
    assert '17:10' not in answer['answer'] and '21-Nov' not in answer['answer']

@pytest.mark.parametrize('body', ['Bootcamp: Your application has been accepted.', 'تم قبولك في معسكر البرمجة.', 'Your application has been rejected by the bootcamp.'])
def test_recent_literal_status_keeps_polarity_and_scope(test_database,body):
    email=indexed(test_database,body,subject='Bootcamp معسكر')
    email.message_at=NOW-timedelta(days=2);test_database.flush()
    llm=SpyLLM();result=answer_email_question(test_database,'انقبلت بمعسكر؟',llm,min_score=0)
    assert result['status']=='answered' and llm.calls==0
    assert body in result['answer'] and '28 سبتمبر 2026' in result['answer']
    assert result['citations']==[{'email_id':email.id}]


def test_old_acceptance_not_retrieved_as_recent(test_database):
    email=indexed(test_database,'Your application has been accepted by the bootcamp.',subject='Bootcamp')
    email.message_at=NOW-timedelta(days=365);test_database.flush()
    prepared=prepare_rag_request(test_database,'انقبلت بمعسكر؟',min_score=0)
    assert prepared['retrieved_chunks']==[]
    answer=answer_email_question(test_database,'انقبلت بمعسكر؟',SpyLLM(),min_score=0)
    assert answer['status']=='insufficient_evidence' and not answer['citations']
    assert 'لا يثبت القبول أو الرفض' in answer['answer']


def test_recent_ambiguous_applications_clarify(test_database):
    for n in range(2):
        email=indexed(test_database,'Your application has been accepted by the bootcamp.',message_id=f'accept-{n}',subject=f'Bootcamp {n}')
        email.message_at=NOW-timedelta(days=n+1)
    test_database.flush()
    llm=SpyLLM();answer=answer_email_question(test_database,'جاني قبول؟',llm,min_score=0)
    assert answer['status']=='needs_clarification' and llm.calls==0


def test_conditional_acceptance_is_not_acceptance(test_database):
    email=indexed(test_database,'If your application has been accepted, please bring your ID to the bootcamp.',subject='Bootcamp')
    email.message_at=NOW-timedelta(days=1);test_database.flush()
    answer=answer_email_question(test_database,'انقبلت بمعسكر؟',SpyLLM(),min_score=0)
    assert answer['status']=='insufficient_evidence'


def test_recent_scope_does_not_leak_other_tenant(two_users,owned,test_database):
    from semantic_index import index_email
    from fact_store import refresh_facts
    a,b,_=two_users
    b.body='Your application has been accepted by the bootcamp.';b.subject='Bootcamp'
    b.message_at=NOW-timedelta(days=1)
    index_email(b,test_database);refresh_facts(b,test_database);test_database.commit()
    result=answer_email_question(owned,'انقبلت بمعسكر؟',SpyLLM(),min_score=0)
    assert result['status']=='insufficient_evidence' and not result['citations']


def test_unknown_timestamp_is_not_recent(test_database):
    indexed(test_database,'Your application has been accepted by the bootcamp.',subject='Bootcamp')
    result=prepare_rag_request(test_database,'انقبلت بمعسكر؟',min_score=0)
    assert result['retrieved_chunks']==[]


def test_recent_status_details_are_same_record(test_database):
    email=indexed(test_database,'Your application has been accepted.\nOrganization: Cedar Academy\nPosition: Research intern\nNext step: Submit signed agreement',subject='Application')
    email.message_at=NOW-timedelta(days=1);test_database.flush()
    result=answer_email_question(test_database,'What is the latest application update?',SpyLLM(),min_score=0)
    assert result['status']=='answered'
    assert 'Cedar Academy' in result['answer'] and 'Research intern' in result['answer']


def test_no_airport_invention(test_database):
    indexed(test_database,'Travel date: 20-Nov-2027\nDeparture time: 08:15',subject='Trip')
    result=answer_email_question(test_database,'When is my trip?',SpyLLM(),min_score=0)
    assert 'airport' not in result['answer'].lower()


def test_event_details_from_same_verified_record(test_database):
    indexed(test_database,'Our conference is scheduled for 20 November 2027.\nEvent time: 09:00\nLocation: Cedar Hall',subject='Conference')
    result=answer_email_question(test_database,'When is the conference?',SpyLLM(),min_score=0)
    assert result['status']=='answered' and 'Cedar Hall' in result['answer'] and '09:00' in result['answer']


def test_time_scope_does_not_confuse_message_and_trip_date():
    assert scope('When is my trip this week?') is None


def test_latest_status_uses_explicit_same_application_identity(test_database):
    for n,state in enumerate(['under review','accepted']):
        email=indexed(test_database,f'Application reference: APP-82\nOrganization: Cedar Institute\nYour application is {state}.',message_id=f'status-{n}',subject='Application update')
        email.message_at=NOW-timedelta(days=4-n)
    test_database.flush()
    result=answer_email_question(test_database,'What is the latest application update?',SpyLLM(),min_score=0)
    assert result['status']=='answered' and 'accepted' in result['answer']
    assert result['citations']==[{'email_id':email.id}]


def test_finance_bundle_uses_explicit_due_date_amount_company(test_database):
    indexed(test_database,'Due date: 20-Nov-2027\nAmount due: 135 SAR\nCompany: Cedar Services',subject='Invoice')
    result=answer_email_question(test_database,'When is my invoice due?',SpyLLM(),min_score=0)
    assert result['status']=='answered'
    assert '135 SAR' in result['answer'] and 'Cedar Services' in result['answer']


def test_gulf_departure_phrase_preserves_time_role(test_database):
    indexed(test_database,'Departure time: 08:15\nArrival time: 10:25',subject='Trip')
    result=answer_email_question(test_database,'متى بطلع؟',SpyLLM(),min_score=0)
    assert '08:15' in result['answer'] and '10:25' not in result['answer']

@pytest.mark.parametrize('second_reference',[False,True])
def test_parent_booking_reference_requires_document_uniqueness(test_database,second_reference):
    body='Your booking reference: REF-39\n\nTravel date: 20-Nov-2027\nDestination: Birch\nDeparture time: 08:15\n\n'
    if second_reference:body+='Booking reference: OTHER-82\n'
    body+='Travel date: 21-Nov-2027\nDestination: Cedar\nDeparture time: 17:10'
    indexed(test_database,body,subject='Itinerary')
    result=answer_email_question(test_database,'When is my trip to Birch?',SpyLLM(),min_score=0)
    assert result['status']=='answered'
    assert ('REF-39' in result['answer']) is (not second_reference)
    assert 'OTHER-82' not in result['answer'] and '17:10' not in result['answer']


def test_classifier_challenge_is_separate_and_balanced():
    from quality.deeper_cases import TRAIN,HOLDOUT,rows
    from quality.classification_cases import DEV,FINAL,examples
    from quality.dataset import LABELS
    training={r['text'].strip().casefold() for r in rows(TRAIN)+examples(DEV)+examples(FINAL)}
    holdout=rows(HOLDOUT)
    assert len(holdout)==40
    assert not training & {r['text'].strip().casefold() for r in holdout}
    assert set(HOLDOUT)==set(LABELS)
    assert all(len(items)==4 for items in HOLDOUT.values())
