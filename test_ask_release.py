"""Release behavior checks with isolated synthetic mailbox evidence."""
from datetime import timedelta
import pytest
from ask_plan import plan
from rag_service import answer_email_question
from test_ask_deeper import NOW, clock
from test_rag_hybrid import SpyLLM
from test_relational_facts import indexed
from test_backend_isolation import two_users, owned


def test_selected_ambiguous_email_requests_refinement_instead_of_repeating_choice(test_database):
    from test_relational_facts import route
    email = indexed(test_database, 'date: 2028-03-12\n' + route() + '\n\ndate: 2028-03-18\n' +
                    route('Birch', 'Alder', '16:20', '18:30'), subject='Round trip')
    llm = SpyLLM()
    result = answer_email_question(test_database, 'What is the arrival time?', llm, email_id=email.id)
    assert result['status'] == 'needs_clarification'
    assert result['clarification_options'] == []
    assert 'Add a destination' in result['answer']
    refined = answer_email_question(test_database, 'What is the arrival time to Alder?', llm, email_id=email.id)
    assert refined['status'] == 'answered' and '18:30' in refined['answer']
    assert llm.calls == 0


@pytest.mark.parametrize('question', ['Did I get an email from Cedar?', 'هل وصلني شيء من الجامعة؟',
                                     'Have I received a newsletter from Cedar last week?'])
def test_metadata_existence_routing(question):
    assert plan(question).kind=='existence'


def test_existence_does_not_invent_recent_window():
    assert plan('هل وصلني شيء من الجامعة؟').window is None
    assert plan('Did I get an email from Cedar last week?').entity==('cedar',)
    assert plan('Did I get an email from Cedar last week?').window is not None


def message(db,body,number=0,subject='Update',sender='Cedar <cedar@example.invalid>',days=1):
    from models import Email
    email=Email(account_id=db.info['account_id'],message_id=f'release-{number}',body=body,
                sender=sender,subject=subject,message_at=NOW-timedelta(days=days))
    db.add(email);db.flush();return email


def test_existence_is_natural_and_count_is_not_capped_silently(test_database):
    for number in range(7):
        message(test_database,'Weekly newsletter.',number,subject=f'Weekly newsletter {number}')
    result=answer_email_question(test_database,'Did I get a newsletter from Cedar?',SpyLLM())
    assert result['status']=='answered'
    assert 'at least 5' in result['answer']
    assert 'T00:' not in result['answer'] and len(result['sources'])==5
    assert result['answer'].count('Cedar')==1


def test_digest_security_precedes_newer_low_value_item(test_database):
    message(test_database,'Your booking is confirmed for the trip.',subject='Trip',days=1)
    security=message(test_database,'Security alert: a new sign-in was detected on your account.',1,subject='Security',days=3)
    answer=answer_email_question(test_database,'What changed recently?',SpyLLM())
    assert answer['sources'][0]['email_id']==security.id
    assert 'new sign-in' in answer['answer']


def test_digest_deduplicates_explicit_threads_and_keeps_latest(test_database):
    first=message(test_database,'Your application has been accepted.',subject='Application',days=3)
    last=message(test_database,'Your application has been rejected.',1,subject='Application',days=1)
    first.raw_payload={'headers':[{'name':'Message-ID','value':'<root@example.invalid>'}]}
    last.raw_payload={'headers':[{'name':'References','value':'<root@example.invalid>'}]}
    test_database.flush()
    answer=answer_email_question(test_database,'What changed recently?',SpyLLM())
    assert answer['citations']==[{'email_id':last.id}]
    assert 'rejected' in answer['answer'] and 'accepted' not in answer['answer']


def test_digest_does_not_merge_unrelated_identical_subjects(test_database):
    first=message(test_database,'Your payment due date is tomorrow unless already paid.',subject='Invoice')
    second=message(test_database,'Your amount due is 150 SAR by next week.',1,subject='Invoice')
    answer=answer_email_question(test_database,'What changed recently?',SpyLLM())
    assert {s['email_id'] for s in answer['sources']}=={first.id,second.id}
    assert 'unless already paid' in answer['answer']


def test_old_email_does_not_enter_digest(test_database):
    message(test_database,'Security alert: a new sign-in was detected on your account.',days=700)
    answer=answer_email_question(test_database,'What changed recently?',SpyLLM())
    assert answer['status']=='insufficient_evidence'


def test_digest_and_alias_lanes_are_owned(two_users,owned):
    assert answer_email_question(owned,'What changed recently?',SpyLLM())['sources']==[]
    assert answer_email_question(owned,'Did I get an email from Private?',SpyLLM())['sources']==[]


def test_application_followup_rechecks_organization(test_database):
    for i,name in enumerate(('Cedar','Birch')):
        email=indexed(test_database,'Your application has been accepted.',subject=f'{name} application',message_id=f'followup-{i}')
        email.message_at=NOW-timedelta(days=1)
    test_database.flush()
    answer=answer_email_question(test_database,'طيب Birch بس؟',SpyLLM(),history=['وش صار على طلباتي؟'],min_score=0)
    assert answer['status']=='answered' and answer['citations']==[{'email_id':email.id}]


def test_absence_never_states_rejection(test_database):
    answer=answer_email_question(test_database,'انقبلت بمعسكر؟',SpyLLM())
    assert answer['status']=='insufficient_evidence' and 'لا يثبت القبول أو الرفض' in answer['answer']
