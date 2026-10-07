"""Generated prose is never promoted to a verified extraction, even when cited."""
import pytest
from fastapi.testclient import TestClient
from main import app
from rag_service import answer_email_question
from test_rag import FakeLLM
from test_rag_hybrid import setup_evidence, SpyLLM
from test_backend_isolation import two_users, owned


@pytest.mark.parametrize('body,prose', [
    ('Our team is currently reviewing your application. Should your profile align with our current needs, we will contact you directly to discuss the next steps.',
     'The team is reviewing your application and will contact you directly to discuss the next steps.'),
    ('If approved, we will contact you.', 'We will contact you.'),
    ('We will not contact you.', 'We will contact you.'),
    ('We will contact everyone except unsuccessful applicants.', 'We will contact everyone.'),
    ('We will contact you unless the vacancy closes.', 'We will contact you.'),
    ('We will contact you only if your application is approved.', 'We will contact you.'),
    ('سنواصلك إذا تمت الموافقة على طلبك.', 'سنواصلك.'),
    ('لن نتواصل معك إلا إذا تمت الموافقة.', 'سنتواصل معك.'),
    ('We will contact you if approved.', 'We will contact you if approved.'),
])
def test_conditions_cannot_be_promoted_to_verified(test_database, monkeypatch, body, prose):
    email, _ = setup_evidence(test_database, monkeypatch, body)
    raw = f'{prose} [email_id={email.id}]'
    result = answer_email_question(test_database, 'Summarize the next steps.', FakeLLM(raw))
    assert result['status'] == 'answered'
    assert result['answer_mode'] == 'generated_synthesis'
    assert result['verification'] == 'not_semantically_verified'
    warning, answer = result['answer'].split('\n\n', 1)
    assert 'conditions, negation or exceptions' in warning
    assert 'check the original email' in warning
    assert answer == raw and result['citations'] == [{'email_id': email.id}]


def test_arabic_notice_and_no_model_control_of_verification(test_database, monkeypatch):
    email, _ = setup_evidence(test_database, monkeypatch, 'سنواصلك إذا تمت الموافقة.')
    raw = f'verification: source_supported [email_id={email.id}]'
    result = answer_email_question(test_database, 'لخص الرسالة', FakeLLM(raw))
    assert result['answer'].startswith('ملخص مولّد، وليس استخراجًا متحققًا من معناه.')
    assert result['verification'] == 'not_semantically_verified'
    assert result['answer_mode'] == 'generated_synthesis'


@pytest.mark.parametrize('body,question,mode,literal', [
    ('Booking reference: REF-72', 'What is the booking reference?', 'deterministic_fact', 'REF-72'),
    ('Our team is currently reviewing your application.', 'What is my application status?', 'extractive',
     'Our team is currently reviewing your application.'),
])
def test_verified_answers_keep_original_text(test_database, monkeypatch, body, question, mode, literal):
    email, _ = setup_evidence(test_database, monkeypatch, body)
    fake = SpyLLM()
    result = answer_email_question(test_database, question, fake)
    assert result['answer_mode'] == mode and result['verification'] == 'source_supported'
    assert literal in result['answer'] and result['answer'].endswith(f'[email_id={email.id}]')
    assert 'Generated synthesis' not in result['answer'] and fake.calls == 0
    if mode == 'extractive':
        assert result['answer'] == f'{literal} [email_id={email.id}]'


@pytest.mark.parametrize('raw', ['Uncited prose', 'Wrong [email_id=999999]', 'Wrong [email_id=abc]', ''])
def test_notice_does_not_launder_invalid_citations(test_database, monkeypatch, raw):
    setup_evidence(test_database, monkeypatch, 'If approved, we will contact you.')
    result = answer_email_question(test_database, 'Summarize the next steps.', FakeLLM(raw))
    assert result['status'] == 'insufficient_evidence' and result['citations'] == []
    assert 'verification' not in result and 'answer_mode' not in result
    assert 'Generated synthesis' not in result['answer']


def test_api_additive_contract_and_failure(test_database, monkeypatch):
    email, _ = setup_evidence(test_database, monkeypatch, 'If approved, we will contact you.')
    fake = FakeLLM(f'We will contact you. [email_id={email.id}]')
    monkeypatch.setattr('rag_api.get_llm_provider', lambda: fake)
    with TestClient(app) as client:
        response = client.post('/ask', json={'question': 'Summarize the next steps.'})
        assert response.status_code == 200
        data = response.json()
        assert {'answer','status','sources','citations'} <= data.keys()
        assert data['verification'] == 'not_semantically_verified'
        assert data['answer_mode'] == 'generated_synthesis'
        assert 'Generated synthesis' in data['answer']
        fake.answer = RuntimeError('PRIVATE_PROVIDER_DETAIL')
        failure = client.post('/ask', json={'question': 'Summarize the next steps.'})
        assert failure.status_code == 503 and 'PRIVATE_PROVIDER_DETAIL' not in failure.text


def test_cross_user_sources_and_citations_still_rejected(two_users, owned, monkeypatch):
    a, b, _ = two_users
    chunks = [dict(email_id=e.id, chunk_id=e.id, chunk_index=0, score=.9, text=e.body) for e in (a,b)]
    monkeypatch.setattr('rag_service.retrieve_rag_chunks', lambda *args, **kwargs: chunks)
    fake = FakeLLM(f'Foreign claim [email_id={b.id}]')
    rejected = answer_email_question(owned, 'Summarize the emails.', fake)
    assert rejected['status'] == 'insufficient_evidence' and rejected['sources'] == []
    assert b.body not in fake.messages[1]['content']
    result = answer_email_question(owned, 'Summarize the emails.', FakeLLM(f'Own claim [email_id={a.id}]'))
    assert result['verification'] == 'not_semantically_verified'
    assert {s['email_id'] for s in result['sources']} == {a.id}


def test_clarification_and_abstention_contracts_unchanged(test_database, monkeypatch):
    from test_semantic_index import saved_email
    _, chunks = setup_evidence(test_database, monkeypatch, 'Your application is accepted.')
    other = saved_email(test_database, message_id='other-freeze', body='Your application is rejected.')
    chunks.append(dict(chunks[0], email_id=other.id, chunk_id=902, text=other.body))
    fake = SpyLLM()
    result = answer_email_question(test_database, 'What happened with my application?', fake)
    assert result['status'] == 'needs_clarification' and fake.calls == 0
    assert 'verification' not in result and len(result['clarification_options']) == 2
    chunks.clear()
    result = answer_email_question(test_database, 'Summarize the emails.', fake)
    assert set(result) == {'answer','sources','citations','status'}
    assert result['status'] == 'insufficient_evidence' and fake.calls == 0
