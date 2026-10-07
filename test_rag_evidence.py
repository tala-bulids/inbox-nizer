import copy
import json
import re

import pytest

from rag_evidence import select_evidence


def chunk(value, index=0):
    return {'email_id': 73, 'chunk_id': index + 10, 'chunk_index': index, 'score': 0.8, 'text': value}


SCHEDULE = ('Reference: REF-27\n\nRecord: morning\nFrom: Lakeview\nTo: Hilltown\n'
            'Date: 07-May-2028\nStart: 09:20\nEnd: 10:40\n\n'
            'Record: evening\nFrom: Hilltown\nTo: Lakeview\n'
            'Date: 09-May-2028\nStart: 16:10\nEnd: 17:30')


@pytest.mark.parametrize('question,keep,drop', [
    ('When is the event to Hilltown?', '07-May-2028', '09-May-2028'),
    ('When is the event from Hilltown?', '09-May-2028', '07-May-2028'),
    ('What is the morning start time?', '09:20', '16:10'),
])
def test_qualifier_selects_complete_record_without_mixing(question, keep, drop):
    chunks = [chunk(SCHEDULE)]
    original = copy.deepcopy(chunks)
    evidence, audit = select_evidence(question, chunks)
    assert keep in evidence[0]['text'] and drop not in evidence[0]['text']
    assert 'REF-27' in evidence[0]['text']
    assert chunks == original
    start, end = audit[0]['selected_spans'][0]
    assert SCHEDULE[start:end].strip() in evidence[0]['text']
    assert evidence[0]['email_id'] == 73 and evidence[0]['chunk_index'] == 0


@pytest.mark.parametrize('question', ['List both records and dates', 'Compare morning and evening',
                                     'When are all events?', 'When is the event to Unknown?',
                                     'When are events to Hilltown and Lakeview?',
                                     'When is the event not to Hilltown?'])
def test_ambiguous_multi_item_or_unmatched_question_keeps_all(question):
    chunks = [chunk(SCHEDULE)]
    evidence, audit = select_evidence(question, chunks)
    assert evidence == chunks and audit == []


def test_arabic_direction_normalization():
    value = ('سجل: الأول\nالمكان: الواحة إلى الروضة\nالتاريخ: 07-May-2028\nالبدء: 09:20\n\n'
             'سجل: الثاني\nالمكان: الروضة إلى الواحة\nالتاريخ: 09-May-2028\nالبدء: 16:10')
    result, audit = select_evidence('متى الموعد للروضة؟', [chunk(value)])
    assert '07-May-2028' in result[0]['text'] and '09-May-2028' not in result[0]['text']
    assert audit[0]['reason'] == 'explicit_relation'


@pytest.mark.parametrize('question,label,first,second', [
    ('What is the amount for Alice?', 'Invoice', 'For: Alice\nAmount: 120', 'For: Bob\nAmount: 240'),
    ('What is the new deadline?', 'Version', 'old\nDeadline: 07-May-2028', 'new\nDeadline: 09-May-2028'),
    ('When is the review appointment?', 'Appointment', 'intake\nTime: 09:20', 'review\nTime: 16:10'),
])
def test_generic_nontravel_records(question, label, first, second):
    value = f'{label}: {first}\n\n{label}: {second}'
    result, audit = select_evidence(question, [chunk(value)])
    assert audit
    assert (('120' in result[0]['text'] and '240' not in result[0]['text']) if label == 'Invoice'
            else second in result[0]['text'] and first not in result[0]['text'])


def test_adjacent_chunk_and_nonstructured_evidence_are_preserved():
    following = chunk('Bring reference REF-27 and your identification.', 1)
    chunks = [chunk(SCHEDULE), following]
    result, _ = select_evidence('When is the event to Hilltown?', chunks)
    assert result[1] == following
    prose = [chunk('The earlier value was 100 and the new value is 120.')]
    assert select_evidence('What is the new value?', prose) == (prose, [])


def test_repeated_boilerplate_is_not_a_record_boundary():
    value = 'Notice: Shared details\nEvent A\nNotice: Shared details\nEvent B'
    chunks = [chunk(value)]
    assert select_evidence('Event A', chunks) == (chunks, [])


def test_compound_summary_does_not_merge_distinct_records():
    summary = 'Record: morning | From: Lakeview | To: Hilltown | Start: 09:20\n\n'
    result, audit = select_evidence('When is the event to Hilltown?', [chunk(summary + SCHEDULE)])
    assert len(audit[0]['selected_spans']) == 1
    assert '07-May-2028' in result[0]['text'] and '09-May-2028' not in result[0]['text']


def test_selection_is_not_based_on_record_order():
    prefix, first, second = SCHEDULE.split('\n\n')
    reversed_records = prefix + '\n\n' + second + '\n\n' + first
    result, audit = select_evidence('When is the event to Hilltown?', [chunk(reversed_records)])
    assert '07-May-2028' in result[0]['text'] and '09-May-2028' not in result[0]['text']
    assert audit[0]['selected_spans'][0][0] > reversed_records.index('09-May-2028')


def test_service_delivers_scoped_evidence_and_keeps_citation_checks(test_database, monkeypatch):
    from test_semantic_index import saved_email
    from rag_service import answer_email_question, InvalidGeneration
    email = saved_email(test_database, subject='Schedule', body=SCHEDULE)
    retrieved = [dict(chunk(SCHEDULE), email_id=email.id)]
    monkeypatch.setattr('rag_service.retrieve_rag_chunks', lambda *a, **k: retrieved)
    class EvidenceReader:
        def generate(self, messages):
            match = re.search(r'\[SOURCE email_id=(\d+) chunk=\d+\]\n(.*?)\n\[END SOURCE\]', messages[1]['content'], re.S)
            content = json.loads(match[2])['content']
            assert '07-May-2028' in content and '09-May-2028' not in content
            date = re.search(r'Date: ([^\n]+)', content)[1]
            return f'{date} [email_id={match[1]}]'
    result = answer_email_question(test_database, 'When is the event to Hilltown?', EvidenceReader())
    assert result['answer'] == f'07-May-2028 [email_id={email.id}]'
    class InvalidReader:
        def generate(self, messages):
            return '07-May-2028 [email_id=999999]'
    rejected = answer_email_question(test_database, 'When is the event to Hilltown?', InvalidReader())
    assert rejected['status'] == 'insufficient_evidence'
    assert rejected['citations'] == []
    assert '999999' not in rejected['answer']
