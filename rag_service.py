"""Orchestration for retrieval-augmented email questions."""

import re
from llm_provider import LLMProvider
from rag_context import build_rag_context
from rag_prompt import build_rag_messages
from rag_retrieval import retrieve_rag_chunks
from rag_evidence import select_evidence
from rag_grounding import answer_candidate, has_role_conflict, is_abstention


class InvalidGeneration(RuntimeError):
    """Generation was empty or failed citation validation."""


def _validate_citations(answer, sources):
    pattern = r'\[email_id=(\d+)\]'
    cited = list(dict.fromkeys(int(value) for value in re.findall(pattern, answer)))
    allowed = {source['email_id'] for source in sources}
    if (not cited or not set(cited) <= allowed
            or any(not re.search(pattern, paragraph) for paragraph in answer.split('\n') if paragraph.strip())
            or '[email_id' in re.sub(pattern, '', answer)):
        raise InvalidGeneration('Generation failed source citation validation')

    return cited


def insufficient_answer(question):
    answer = ('لا توجد معلومات كافية في المصادر المسترجعة للإجابة عن هذا السؤال.'
              if re.search(r'[\u0600-\u06ff]', question)
              else 'The retrieved sources do not contain enough information to answer this question.')
    return {'answer': answer, 'sources': [], 'citations': [], 'status': 'insufficient_evidence'}


def prepare_rag_request(
    db,
    question: str,
    *,
    chunk_limit: int = 8,
    max_chunks_per_email: int = 2,
    min_score: float | None = None,
    max_context_chars: int = 12000,
):
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must not be empty")

    question = question.strip()

    chunks = retrieve_rag_chunks(
        db,
        query=question,
        limit=chunk_limit,
        min_score=min_score,
        max_chunks_per_email=max_chunks_per_email,
    )

    evidence, evidence_audit = select_evidence(question, chunks)
    context_result = build_rag_context(
        db,
        evidence,
        max_chars=max_context_chars,
    )

    messages = build_rag_messages(
        question,
        context_result["context"],
    )

    return {
        "messages": messages,
        "sources": context_result["sources"],
        "context": context_result["context"],
        "retrieved_chunks": chunks,
        "evidence_audit": evidence_audit,
        "answer_candidate": answer_candidate(question, context_result.get("evidence", [])),
    }


def answer_email_question(
    db,
    question: str,
    llm: LLMProvider,
    *,
    chunk_limit: int = 8,
    max_chunks_per_email: int = 2,
    min_score: float | None = None,
    max_context_chars: int = 12000,
):
    prepared = prepare_rag_request(
        db,
        question,
        chunk_limit=chunk_limit,
        max_chunks_per_email=max_chunks_per_email,
        min_score=min_score,
        max_context_chars=max_context_chars,
    )

    if not prepared['sources']:
        return insufficient_answer(question)
    answer = llm.generate(prepared["messages"])

    if not isinstance(answer, str) or not answer.strip():
        raise InvalidGeneration("Generation returned an empty answer")

    answer = answer.strip()
    candidate = prepared.get('answer_candidate')
    if is_abstention(answer):
        if '[email_id' in answer:
            _validate_citations(answer, prepared['sources'])
        if candidate is None:
            result = insufficient_answer(question)
            # A model refusal is not proof that the source lacks the answer.
            result['answer'] = ('لم أتمكن من استخراج إجابة موثوقة من المصادر المسترجعة.'
                                if re.search(r'[\u0600-\u06ff]', question)
                                else 'I could not verify an answer from the retrieved sources.')
            return result
        answer = f"{candidate['label']}: {candidate['value']} [email_id={candidate['email_id']}]"
    cited = _validate_citations(answer, prepared['sources'])

    if has_role_conflict(answer, candidate):
        raise InvalidGeneration('Generation contradicts the requested labelled field')

    return {
        "answer": answer.strip(),
        "sources": [source for source in prepared['sources'] if source['email_id'] in cited],
        "citations": [{'email_id': email_id} for email_id in cited],
        "status": "answered",
    }
