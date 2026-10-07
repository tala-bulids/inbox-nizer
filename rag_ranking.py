"""Re-rank a bounded vector candidate pool using current, evidenced fact roles."""
from fact_roles import intent, matching_fields


def rank_candidates(db, question, chunks):
    request = intent(question)
    if not chunks or (not request and not any('fact' in c.get('candidate_ranks', {}) for c in chunks)):
        return chunks
    from fact_store import fact_evidence
    from rag_evidence import select_evidence
    from models import Email
    from sqlalchemy import select
    narrowed, _ = select_evidence(question, chunks)
    subjects = dict(db.execute(select(Email.id,Email.subject).where(Email.id.in_({c['email_id'] for c in chunks}))).all())
    sources = [dict(c, content=c['text'], subject=subjects.get(c['email_id'],'')) for c in narrowed]
    enriched, _ = fact_evidence(db, sources)
    eligible, identities = {}, set()
    for source in enriched:
        # Only persisted, validated facts contribute ranking authority.
        stored = [f for f in source.get('fields',[]) if f.get('span_basis') == 'stored_body']
        if request:
            matches = matching_fields(request, [dict(source,fields=stored)])
        else:
            from rag_grounding import resolve_answer
            matches = resolve_answer(question, [dict(source,fields=stored)])
        eligible[source['chunk_id']] = bool(matches)
        identities.update((f['email_id'], tuple(f['role']) if isinstance(f['role'], list) else f['role'],
                           f['value'], f['record_index']) for f in matches)
    ambiguous = len(identities) > 1
    output = [dict(c, requested_role=request['role'] if request else None,
                   ranking=dict(persisted_role_match=eligible.get(c['chunk_id'],False),
                                ambiguous=ambiguous, candidate_count=len(chunks))) for c in chunks]
    return sorted(output, key=lambda c: (not c['ranking']['persisted_role_match'],
        -(c.get('fusion_score', c['score']) if c['ranking']['persisted_role_match'] else c['score']),
        -c['score'], c['chunk_id']))
