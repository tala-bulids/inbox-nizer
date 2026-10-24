"""Regression checks for quality changes, separate from model training."""
import pytest
from quality.cases import TASKS, ASK, ASK_SOURCE, REFERENCE
from task_extractor import extract_action_items, extract_tasks
from rag_grounding import resolve_answer
from test_relational_facts import indexed
from test_rag_hybrid import SpyLLM
from rag_service import answer_email_question

@pytest.mark.parametrize('name,body,fragment,deadline',TASKS,ids=[r[0] for r in TASKS])
def test_task_scope_and_due_role(name,body,fragment,deadline):
    result=extract_action_items('',body,REFERENCE)
    if fragment is None:
        assert result==[]
    else:
        assert len(result)==1
        assert fragment.casefold() in result[0]['task'].casefold()
        assert result[0]['deadline_text']==deadline

@pytest.mark.parametrize('question,expected', ASK)
def test_bilingual_query_roles(question,expected):
    facts=resolve_answer(question,[ASK_SOURCE])
    assert (facts[0]['value'] if facts else None)==expected

@pytest.mark.parametrize('question', ['وش آخر موعد؟','متى آخر يوم؟','What is the deadline?','متى deadline؟'])
def test_bilingual_deadline_lookup(question):
    source=dict(ASK_SOURCE,content='Deadline: 2027-11-05')
    assert resolve_answer(question,[source])[0]['value']=='2027-11-05'

@pytest.mark.parametrize('question,expected', [(q,e) for q,e in ASK if e])
def test_searchable_owned_source_resolves_without_llm(test_database,question,expected):
    from semantic_search import semantic_search
    email=indexed(test_database,ASK_SOURCE['content'],subject=ASK_SOURCE['subject'])
    # The fake embedding is deterministic; this exercises the actual PostgreSQL
    # candidate/evidence/fact/service pipeline, not an invented model answer.
    assert semantic_search(test_database,question,min_score=0)[0]['email'].id==email.id
    llm=SpyLLM()
    result=answer_email_question(test_database,question,llm,min_score=0)
    assert result['status']=='answered'
    from answer_presentation import human_date
    from rag_bundle import wanted
    import re
    displayed = human_date(expected,bool(re.search('[\u0600-\u06ff]',question))) if wanted(question) else expected
    assert displayed in result['answer']
    assert result['citations']==[{'email_id':email.id}]
    assert result['verification']=='source_supported'
    assert llm.calls==0

@pytest.mark.parametrize('question',['متى رحلتي؟','كم وقت الوصول؟'])
def test_ambiguous_flights_still_clarify(test_database,question):
    indexed(test_database,ASK_SOURCE['content'],message_id='first')
    indexed(test_database,ASK_SOURCE['content'].replace('18-Nov-2027','20-Nov-2027'),message_id='second')
    llm=SpyLLM()
    result=answer_email_question(test_database,question,llm,min_score=0)
    assert result['status']=='needs_clarification' and llm.calls==0

@pytest.mark.parametrize('text', ['يرجى الحضور غداً الساعة 10 صباحاً.', 'Please attend the conference tomorrow.'])
def test_attendance_date_is_not_a_deadline(text):
    item=extract_action_items('',text,REFERENCE)[0]
    assert item['deadline_text'] is None


def test_conditions_are_not_deduplicated_away():
    result=extract_tasks('', 'If your ID expired, please upload a new copy.\nIf your address changed, please upload a new copy.')
    assert len(result)==2

@pytest.mark.parametrize('text,deadline', [
 ('If your ID expires before Friday, please upload a replacement by Monday.', 'by Monday'),
 ('إذا انتهت صلاحية هويتك قبل الخميس، يرجى إرسال نسخة جديدة قبل الأحد.', 'قبل الأحد'),
 ('Please review the report for the event on Friday, then send your comments before Monday.', None),
])
def test_conditions_and_event_dates_do_not_supply_other_actions_deadlines(text,deadline):
    items=extract_action_items('',text,REFERENCE)
    assert items[0]['deadline_text']==deadline
    if len(items)>1:
        assert items[1]['deadline_text']=='before Monday'


def test_registration_context_does_not_leak_to_distant_promotional_cta():
    text='Registration is mandatory.\nPlease upload your ID.\nOur offers\nRegister now.'
    tasks=extract_tasks('',text)
    assert len(tasks)==1 and tasks[0]['task']=='Upload your ID'

@pytest.mark.parametrize('subject,body', [
 ('Pay your invoice','Your invoice has been paid.'),
 ('إكمال التسجيل','تم إكمال التسجيل بنجاح.'),
 ('Upload the document','The document was uploaded successfully.'),
])
def test_completed_subject_is_not_a_new_task(subject,body):
    assert extract_tasks(subject,body)==[]


def test_completed_status_keeps_a_new_body_request():
    result=extract_tasks('Upload the document','The document was uploaded successfully. Please confirm your address.')
    assert [r['task'] for r in result]==['Confirm your address']


def test_completed_status_for_other_object_does_not_cancel_subject():
    assert extract_tasks('Pay the invoice','The document was uploaded successfully.')[0]['task']=='Pay the invoice'


def test_completed_different_action_does_not_cancel_subject_request():
    result=extract_tasks('Review the document','The document was uploaded successfully.')
    assert result[0]['task']=='Review the document'

@pytest.mark.parametrize('body', ['التسجيل ينتهي يوم الجمعة.', 'التسجيل متاح الآن.', 'التسجيل في الدورة قبل الخميس.'])
def test_arabic_registration_information_needs_request_context(body):
    assert extract_tasks('',body)==[]


def test_completed_same_action_different_object_keeps_subject():
    result=extract_tasks('إكمال التسجيل','تم إكمال الدفع بنجاح.')
    assert result[0]['task']=='إكمال التسجيل'
