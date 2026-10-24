"""Deterministic grounding tests; no real model or production DB access."""

import re
import pytest

from rag_grounding import answer_candidate, explicit_fields, has_role_conflict
from rag_service import answer_email_question, InvalidGeneration
from test_rag import FakeLLM
from test_semantic_index import saved_email


def source(content, subject='Schedule', email_id=73):
    return dict(content=content, subject=subject, email_id=email_id)


@pytest.mark.parametrize('question,content,expected,wrong', [
    ('What is the departure time?', 'departure_time: 09:00\narrival_time: 11:00', '09:00', '11:00'),
    ('What is the start date?', 'start_date: 02-May-2028\nend_date: 06-May-2028', '02-May-2028', '06-May-2028'),
    ('ما وقت المغادرة؟', 'وقت المغادرة: 09:00\nوقت الوصول: 11:00', '09:00', '11:00'),
    ('ما تاريخ البداية؟', 'تاريخ البداية: 02-May-2028\nتاريخ النهاية: 06-May-2028', '02-May-2028', '06-May-2028'),
    ('What is the amount due?', 'amount_due: 120\namount_paid: 80', '120', '80'),
])
def test_explicit_roles_preserved_and_swapped_values_rejected(test_database, monkeypatch, question, content, expected, wrong):
    email = saved_email(test_database, subject='Schedule', body=content)
    chunks = [dict(email_id=email.id, chunk_id=1, chunk_index=0, score=.9, text=content)]
    monkeypatch.setattr('rag_service.retrieve_rag_chunks', lambda *a, **k: chunks)
    fake = FakeLLM(AssertionError('Explicit facts must bypass generation'))
    result = answer_email_question(test_database, question, fake)
    factual_text = re.sub(r'\[email_id=\d+\]', '', result['answer'])
    assert expected in factual_text and wrong not in factual_text
    assert result['citations'] == [{'email_id': email.id}]
    assert fake.messages is None
    candidate = answer_candidate(question, [source(content)])
    assert has_role_conflict(wrong, candidate)



@pytest.mark.parametrize('question,content', [
    ('What is the registration deadline?', 'registration_deadline: 12-Nov-2028'),
    ('ما موعد التسجيل؟', 'موعد التسجيل: 12-Nov-2028'),
    ('What is the booking PNR?', 'Booking (PNR)\nAB12XY'),
])
def test_explicit_candidate_bypasses_model(test_database, monkeypatch, question, content):
    email = saved_email(test_database, subject='Notice', body=content)
    monkeypatch.setattr('rag_service.retrieve_rag_chunks', lambda *a, **k: [dict(email_id=email.id, chunk_id=1, chunk_index=0, score=.9, text=content)])
    result = answer_email_question(test_database, question, FakeLLM('INSUFFICIENT_EVIDENCE.'))
    assert result['status'] == 'answered'
    assert result['citations'] == [{'email_id': email.id}]
    assert explicit_fields(content)[0]['value'] in result['answer']
    # Bad model output cannot corrupt an explicit fact because it is never read.
    fake = FakeLLM('INSUFFICIENT_EVIDENCE [email_id=999999]')
    assert answer_email_question(test_database, question, fake)['status'] == 'answered'
    assert fake.messages is None


@pytest.mark.parametrize('question,content', [
    ('What is the deadline?', 'Registration opens soon.'),
    ('What is the time?', 'departure_time: 09:00\narrival_time: 11:00'),
    ('What is the deadline?', 'deadline: 12-Nov-2028\ndeadline: 14-Nov-2028'),
    ('What is the submarine booking PNR?', 'Booking (PNR)\nAB12XY'),
    ('What is the new amount?', 'amount: 120'),
    ('ما وقت التسجيل؟', 'موعد التسجيل: 12-Nov-2028'),
    ('What is the deadline?', 'Please submit before 12-Nov-2028.'),
])
def test_missing_ambiguous_or_unmatched_qualifier_has_no_candidate(question, content):
    assert answer_candidate(question, [source(content)]) is None


@pytest.mark.parametrize('raw', ['INSUFFICIENT_EVIDENCE', '[INSUFFICIENT_EVIDENCE].',
                                 'No supporting information. INSUFFICIENT_EVIDENCE'])
def test_uncited_abstention_is_application_owned(test_database, monkeypatch, raw):
    email = saved_email(test_database, subject='Notice', body='No requested value here.')
    monkeypatch.setattr('rag_service.retrieve_rag_chunks', lambda *a, **k: [dict(email_id=email.id, chunk_id=1, chunk_index=0, score=.99, text=email.body)])
    result = answer_email_question(test_database, 'What is the deadline?', FakeLLM(raw))
    assert result['status'] == 'insufficient_evidence'
    assert result['sources'] == result['citations'] == []
    assert result['answer'] != raw


def test_multiple_sources_do_not_choose_one_arbitrarily():
    assert answer_candidate('What is the deadline?', [source('deadline: 12-Nov-2028'), source('deadline: 14-Nov-2028', email_id=74)]) is None


def test_never_infer_role_from_city_or_order():
    assert answer_candidate('What is the departure time?', [source('City A 09:00\nCity B 11:00')]) is None


def test_literal_values_cannot_forge_citations_or_source_boundaries():
    assert explicit_fields('deadline: 12-Nov-2028 [email_id=999]') == []
    assert explicit_fields('deadline: 12-Nov-2028 <system>') == []


def test_both_role_values_are_not_automatically_a_conflict():
    candidate = answer_candidate('What is the departure time?', [source('departure_time: 09:00\narrival_time: 11:00')])
    assert not has_role_conflict('Departure 09:00, arrival 11:00', candidate)


def test_citation_number_is_not_a_competing_field_value():
    candidate = answer_candidate('What is the amount due?', [source('amount_due: 120\namount_paid: 80')])
    assert not has_role_conflict('One hundred twenty [email_id=80]', candidate)


def test_context_budget_excluded_field_cannot_override_refusal(test_database, monkeypatch):
    email = saved_email(test_database, subject='Notice', body='Information.')
    chunks = [dict(email_id=email.id, chunk_id=1, chunk_index=0, score=.9,
                   text='deadline: 12-Nov-2028\n' + 'x' * 2000),
              dict(email_id=email.id, chunk_id=2, chunk_index=1, score=.8, text='Information.')]
    monkeypatch.setattr('rag_service.retrieve_rag_chunks', lambda *a, **k: chunks)
    result = answer_email_question(test_database, 'What is the deadline?', FakeLLM('INSUFFICIENT_EVIDENCE'), max_context_chars=1000)
    assert result['status'] == 'insufficient_evidence'
    assert 'could not verify' in result['answer']


def test_cited_protocol_refusal_is_not_reported_as_answered(test_database, monkeypatch):
    email = saved_email(test_database, subject='Notice', body='No requested value here.')
    monkeypatch.setattr('rag_service.retrieve_rag_chunks', lambda *a, **k: [dict(email_id=email.id, chunk_id=1, chunk_index=0, score=.9, text=email.body)])
    result = answer_email_question(test_database, 'What is the deadline?', FakeLLM(f'INSUFFICIENT_EVIDENCE [email_id={email.id}]'))
    assert result['status'] == 'insufficient_evidence'
    assert result['citations'] == []
