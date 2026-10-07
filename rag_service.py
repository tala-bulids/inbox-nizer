"""Orchestration for retrieval-augmented email questions."""

import re
from llm_provider import LLMProvider, InvalidGeneration
from rag_context import build_rag_context
from fact_store import fact_evidence
from rag_prompt import build_rag_messages
from rag_retrieval import retrieve_rag_chunks
from rag_evidence import select_evidence
from rag_grounding import resolve_answer, format_facts, has_role_conflict, is_abstention
from rag_budget import pack_context
from local_llm import ContextTooLarge
from rag_extractive import audit_answers, decide, verify_proof, format_extractive
from rag_clarification import clarification


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


def unverified_answer(question):
    result = insufficient_answer(question)
    result['answer'] = ('لم أتمكن من استخراج إجابة موثوقة من المصادر المسترجعة.'
                        if re.search(r'[\u0600-\u06ff]', question)
                        else 'I could not verify an answer from the retrieved sources.')
    return result


def prepare_rag_request(
    db,
    question: str,
    *,
    chunk_limit: int = 8,
    max_chunks_per_email: int = 2,
    min_score: float | None = None,
    max_context_chars: int = 12000,
    preview_facts: bool = False,
    email_id: int | None = None,
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
        email_id=email_id,
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

    enriched, fact_audit = fact_evidence(db, context_result.get("evidence", []), preview=preview_facts)
    facts = resolve_answer(question, enriched)
    ambiguous = any(c.get('ranking', {}).get('ambiguous') for c in chunks)
    if ambiguous:
        facts = []
    answer_audit = chunks[0].get('answer_audit') if chunks else None
    if answer_audit is None:
        answer_audit = audit_answers(db, question, evidence)
    decision = decide(answer_audit)
    # Stored-fact ambiguity is already proved before the final chunk cap.
    ambiguous_ids = [email_id for c in chunks for email_id in c.get('ranking', {}).get('ambiguous_email_ids', [])]
    if ambiguous_ids:
        decision = 'needs_clarification'
    elif ambiguous:
        decision = 'insufficient_evidence'
    elif decision != 'needs_clarification' and facts:
        decision = 'deterministic_fact'
    return {
        "messages": messages,
        "sources": context_result["sources"],
        "context": context_result["context"],
        "retrieved_chunks": chunks,
        "evidence_audit": evidence_audit,
        "answer_candidate": facts[0] if len(facts) == 1 else None,
        "resolved_facts": facts,
        "structured_facts": fact_audit,
        "ambiguous_facts": ambiguous,
        "answer_mode": decision,
        "answer_audit": answer_audit,
        "ambiguity_email_ids": ambiguous_ids,
        "permitted_evidence": context_result.get('evidence', []),
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
    preview_facts: bool = False,
    email_id: int | None = None,
):
    prepared = prepare_rag_request(
        db,
        question,
        chunk_limit=chunk_limit,
        max_chunks_per_email=max_chunks_per_email,
        min_score=min_score,
        max_context_chars=max_context_chars,
        preview_facts=preview_facts,
        email_id=email_id,
    )

    mode = prepared['answer_mode']
    if mode == 'needs_clarification':
        ids = prepared['ambiguity_email_ids'] or [p['email_id'] for p in prepared['answer_audit']['proofs']]
        return clarification(db, question, ids)
    if not prepared['sources'] or mode == 'insufficient_evidence':
        return insufficient_answer(question)
    facts = prepared['resolved_facts']
    if mode == 'deterministic_fact':
        answer = format_facts(facts)
    elif mode == 'extractive':
        proof = next((p for p in prepared['answer_audit']['proofs']
                      if verify_proof(db,p,prepared['permitted_evidence'])), None)
        if proof is None:
            return unverified_answer(question)
        answer = format_extractive(proof, question)
    else:
        packed = pack_context(question, prepared['context'], prepared['sources'])
        if not packed['sources']:
            return insufficient_answer(question)
        prepared['sources'] = packed['sources']
        try:
            answer = llm.generate(packed['messages'])
        except (InvalidGeneration, ContextTooLarge):
            return unverified_answer(question)
        if not isinstance(answer, str) or not answer.strip():
            return unverified_answer(question)
        answer = answer.strip()
        if is_abstention(answer):
            # A model refusal is not proof that the source lacks the answer.
            return unverified_answer(question)
        # Short direct factual output requires a verified literal proof. A valid ID
        # alone cannot turn an inferred date/status into a supported assertion.
        if prepared['answer_audit'] and prepared['answer_audit']['kind'] in {'date','status'}:
            return unverified_answer(question)
    try:
        cited = _validate_citations(answer, prepared['sources'])
    except InvalidGeneration:
        return unverified_answer(question)

    if has_role_conflict(answer, prepared.get('answer_candidate')):
        return unverified_answer(question)

    generated = mode not in {'deterministic_fact', 'extractive'}
    if generated:
        # App-owned notice, added only after validating the model's citations.
        notice = (
            'ملخص مولّد، وليس استخراجًا متحققًا من معناه. قد يغيّر الشروط أو النفي أو الاستثناءات؛ راجع البريد الأصلي قبل الاعتماد عليه.'
            if re.search(r'[\u0600-\u06ff]', question) else
            'Generated synthesis, not a semantically verified extraction. It may change conditions, negation or exceptions; check the original email before relying on it.'
        )
        answer = notice + '\n\n' + answer

    return {
        "answer": answer.strip(),
        "sources": [source for source in prepared['sources'] if source['email_id'] in cited],
        "citations": [{'email_id': email_id} for email_id in cited],
        "status": "answered",
        "answer_mode": 'generated_synthesis' if generated else mode,
        "verification": 'not_semantically_verified' if generated else 'source_supported',
    }
