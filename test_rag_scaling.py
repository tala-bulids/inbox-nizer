"""Candidate recall and budgets use PostgreSQL fixtures and fake generation."""
from types import SimpleNamespace
import pytest
from sqlalchemy import event, select

import embedding_service
from fact_roles import intent
from rag_candidates import fuse, FACT_LIMIT
from rag_retrieval import retrieve_rag_chunks
from rag_service import answer_email_question, _validate_citations, InvalidGeneration
from rag_budget import pack_context
from test_relational_facts import indexed, route
from test_rag_hybrid import SpyLLM
from test_backend_isolation import two_users, owned
from fact_store import refresh_facts
from models import EmailEmbeddingChunk


@pytest.fixture
def vector(monkeypatch):
    monkeypatch.setattr(embedding_service, 'embed_query', lambda q: [1.0]+[0.0]*383)


def test_fact_path_recovers_buried_candidate(test_database, vector):
    for i in range(65):
        indexed(test_database, 'Information about destinations.', message_id=f'distractor-{i}', similarity=.95)
    right = indexed(test_database, route(), similarity=.8)
    chunks = retrieve_rag_chunks(test_database, 'What is the arrival time to Birch?', limit=1)
    assert chunks[0]['email_id'] == right.id
    assert 'vector' not in chunks[0]['candidate_ranks']
    assert chunks[0]['candidate_ranks']['fact'] == 1
    assert chunks[0]['retrieval']['vector_count'] == 50
    assert chunks[0]['retrieval']['merged_count'] == 51
    fake = SpyLLM()
    answer = answer_email_question(test_database, 'What is the arrival time to Birch?', fake, chunk_limit=1)
    assert '12:15' in answer['answer'] and fake.calls == 0


def test_rank_fusion_deduplicates_without_changing_cosine():
    a = dict(chunk_id=1, score=.8)
    b = dict(chunk_id=2, score=.9)
    result = fuse([b, a], [a])
    assert len(result) == 2 and result[0]['chunk_id'] == 1
    assert result[0]['score'] == .8
    assert result[0]['candidate_ranks'] == {'vector': 2, 'fact': 1}


def test_stale_generic_fact_gets_no_ranking_authority(test_database, vector):
    right = indexed(test_database, 'Information about booking.', message_id='live', similarity=.95)
    stale = indexed(test_database, 'Booking reference: REF-77', message_id='stale', similarity=.8)
    stale.body = 'Booking details removed.'
    test_database.flush()
    chunks = retrieve_rag_chunks(test_database, 'What is the booking reference?', limit=1)
    assert chunks[0]['email_id'] == right.id


def test_generic_fact_ambiguity_before_limit(test_database, vector):
    indexed(test_database, 'Booking reference: REF-77', message_id='one', similarity=.9)
    indexed(test_database, 'Booking reference: REF-88', message_id='two', similarity=.8)
    fake = SpyLLM()
    result = answer_email_question(test_database, 'What is the booking reference?', fake, chunk_limit=1)
    assert result['status'] == 'needs_clarification' and fake.calls == 0


@pytest.mark.parametrize('text', ['Insufficient evidence is provided.', 'I cannot determine the answer.',
                               'لا توجد معلومات كافية للإجابة.'])
def test_cited_refusal_is_not_presented_as_factual_answer(test_database, text):
    from test_rag import FakeLLM
    email = indexed(test_database, 'A general informational message.')
    result = answer_email_question(test_database, 'Describe the requested event',
                                  FakeLLM(text + f' [email_id={email.id}]'))
    assert result['status'] == 'insufficient_evidence'
    assert result['citations'] == [] and result['answer'] != text


@pytest.mark.parametrize('question', ['متى رحلتي إلى مدينة الأمل؟', 'When is my travel date to Birch?',
                                     'ما وقت arrival إلى Birch؟'])
def test_compact_bilingual_intent(question):
    assert intent(question) is not None


def test_travel_date_preserves_provenance(test_database, vector):
    right = indexed(test_database, 'Travel date: 09-Nov-2028\n'+route())
    fake = SpyLLM()
    result = answer_email_question(test_database, 'When is my trip to Birch?', fake)
    assert '9 November 2028' in result['answer'] and fake.calls == 0
    assert result['citations'] == [{'email_id': right.id}]


def test_fact_candidates_scoped_before_limit(two_users, owned, test_database, vector):
    a, b, _ = two_users
    for email, similarity in [(a, .7), (b, .99)]:
        email.body = route()
        refresh_facts(email, test_database)
        chunk = test_database.scalar(select(EmailEmbeddingChunk).where(EmailEmbeddingChunk.email_id == email.id))
        chunk.chunk_text = email.body
        chunk.embedding = [similarity, (1-similarity**2)**.5]+[0.0]*382
    test_database.commit()
    sql = []
    def capture(conn, cursor, statement, parameters, context, many):
        sql.append(statement)
    bind = owned.get_bind()
    event.listen(bind, 'before_cursor_execute', capture)
    try:
        chunks = retrieve_rag_chunks(owned, 'What is the arrival time to Birch?', limit=1)
    finally:
        event.remove(bind, 'before_cursor_execute', capture)
    assert chunks[0]['email_id'] == a.id
    assert chunks[0]['candidate_ranks']['fact'] == 1
    fact_sql = next(s for s in sql if 'EXISTS' in s and 'email_facts' in s)
    assert 'gmail_accounts.user_id' in fact_sql
    assert fact_sql.index('gmail_accounts.user_id') < fact_sql.index('LIMIT')
    assert all(c['email_id'] != b.id for c in chunks)


def test_saturated_fact_pool_cannot_claim_uniqueness(test_database, vector):
    for i in range(FACT_LIMIT+2):
        indexed(test_database, route(), message_id=f'route-{i}')
    chunks = retrieve_rag_chunks(test_database, 'What is the arrival time?', limit=1)
    assert chunks[0]['retrieval']['fact_count'] == FACT_LIMIT
    assert chunks[0]['retrieval']['fact_saturated']
    fake = SpyLLM()
    assert answer_email_question(test_database, 'What is the arrival time?', fake)['status'] == 'needs_clarification'
    assert fake.calls == 0


def block(number, content):
    import json
    return f'[SOURCE email_id={number} chunk=0]\n'+json.dumps({'content': content})+'\n[END SOURCE]'


@pytest.mark.parametrize('lengths', [[100], [100]*4, [5000], [100, 5000, 100]])
def test_token_budget_packs_whole_sources(lengths):
    budget = SimpleNamespace(context_size=1500, max_new_tokens=256,
                             count_tokens=lambda m: sum(len(x['content']) for x in m))
    sources = [dict(email_id=i+1, chunk_index=0) for i in range(len(lengths))]
    context = '\n\n'.join(block(i+1, 'x'*n) for i,n in enumerate(lengths))
    result = pack_context('Question?', context, sources, budget)
    audit = result['audit']
    assert audit['prompt_tokens'] + audit['output_tokens'] + audit['safety_tokens'] <= 1500
    assert result['messages'][1]['content'].count('[SOURCE') == len(result['sources'])
    if lengths[0] == 100:
        assert result['sources'][0]['email_id'] == 1


def test_question_too_large_abstains_without_generation():
    budget = SimpleNamespace(context_size=512, max_new_tokens=256, count_tokens=lambda m: 700)
    assert pack_context('large', block(1, 'fact'), [dict(email_id=1,chunk_index=0)], budget)['sources'] == []


@pytest.mark.parametrize('raw', ['private secret', '', None, 'I cannot find that information.',
                                'INSUFFICIENT EVIDENCE', 'unsafe [email_id=999999]'])
def test_bad_generation_is_safe(test_database, monkeypatch, raw):
    from test_rag import FakeLLM
    indexed(test_database, 'General news, no requested value.')
    result = answer_email_question(test_database, 'Explain the news', FakeLLM(raw))
    assert result['status'] == 'insufficient_evidence'
    assert result['citations'] == [] and result['answer'] != raw


@pytest.mark.parametrize('raw', ['uncited', 'foreign [email_id=2]', 'valid [email_id=1]\nuncited'])
def test_citation_validator_itself_remains_strict(raw):
    with pytest.raises(InvalidGeneration):
        _validate_citations(raw, [dict(email_id=1)])


def test_default_api_oversized_evidence_does_not_422(test_database, monkeypatch, fake_rag_token_budget):
    from fastapi.testclient import TestClient
    from main import app
    from test_rag import FakeLLM
    email = indexed(test_database, 'Long narrative. '*250)
    monkeypatch.setattr('rag_api.get_llm_provider', lambda: FakeLLM('INSUFFICIENT_EVIDENCE'))
    fake_rag_token_budget.count_tokens = lambda messages: 3000
    with TestClient(app) as client:
        result = client.post('/ask', json={'question': 'Explain the narrative'})
    assert result.status_code == 200 and result.json()['status'] == 'insufficient_evidence'


def test_gguf_budget_loads_only_vocabulary(monkeypatch, tmp_path):
    import local_llm
    model = tmp_path/'test.gguf'
    model.write_bytes(b'fake')
    monkeypatch.setenv('RAG_MODEL_PATH', str(model))
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(tokenize=lambda data, **kw: list(data))
    monkeypatch.setattr(local_llm, '_create_backend', create)
    provider = local_llm.LocalLLM()
    assert provider.count_tokens([dict(role='user',content='Arabic عربي')]) > 0
    provider.count_tokens([])
    assert len(calls) == 1 and calls[0]['vocab_only'] is True
    assert provider._model is None
