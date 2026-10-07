"""Bounded, scoped semantic and persisted-role candidate union."""
from time import perf_counter

from sqlalchemy import select

from email_facts import EXTRACTOR_VERSION
from fact_roles import intent, SIDES, KINDS, LOCATIONS, TRAVEL, UNSAFE, words
from models import EmailFact, EmailEmbeddingChunk

FACT_LIMIT = 64


def stored_roles(question):
    """Map a small role vocabulary to existing persisted label keys."""
    from rag_grounding import _role_tokens
    request = intent(question)
    if request:
        role = request['role']
        if role in LOCATIONS:
            labels = LOCATIONS[role] | ({'from', 'من'} if role == 'origin' else {'to', 'إلى'})
        else:
            side, kind = role.split('_')
            aliases = TRAVEL if side == 'travel' else SIDES[side]
            labels = {f'{a} {b}' for a in aliases for b in KINDS[kind]}
        return {role} | {'_'.join(sorted(_role_tokens(label))) for label in labels}
    tokens = set(words(question))
    if not words(question) or words(question)[0] not in {'what','when','ما','متي','وش'} or tokens & UNSAFE:
        return set()
    # These paths only nominate candidates. Existing resolution checks all qualifiers.
    if tokens & {'booking', 'pnr', 'حجز'}:
        return {'booking_pnr', 'booking_reference', 'booking_number', 'حجز_رقم'}
    if tokens & {'deadline'} or {'اخر', 'يوم'} <= tokens or {'اخر', 'موعد'} <= tokens:
        return {'deadline', 'deadline_registration', 'اخر_يوم', 'اخر_موعد', 'نهائي_موعد'}
    return set()


def chunk_statement(distance, model):
    return select(
        EmailEmbeddingChunk.id.label('chunk_id'), EmailEmbeddingChunk.email_id,
        EmailEmbeddingChunk.chunk_index, EmailEmbeddingChunk.chunk_text,
        distance.label('distance'),
    ).where(EmailEmbeddingChunk.embedding_model == model)


def as_chunks(rows):
    return [dict(chunk_id=r.chunk_id, email_id=r.email_id, chunk_index=r.chunk_index,
                 score=max(-1.0, min(1.0, 1.0-float(r.distance))), text=r.chunk_text)
            for r in rows]


def fact_candidates(db, question, distance, model, min_score):
    roles = stored_roles(question)
    if not roles:
        return [], False
    # Correlated email/role lookup uses the existing (email_id, role) index.
    # OwnedSession also scopes the subquery, before either sort or limit.
    matching = select(EmailFact.id).where(
        EmailFact.email_id == EmailEmbeddingChunk.email_id,
        EmailFact.role.in_(roles), EmailFact.extractor_version == EXTRACTOR_VERSION,
    ).exists()
    statement = chunk_statement(distance, model).where(matching)
    if min_score is not None:
        statement = statement.where(distance <= 1.0-min_score)
    rows = db.execute(statement.order_by(distance, EmailEmbeddingChunk.id).limit(FACT_LIMIT+1)).all()
    return as_chunks(rows[:FACT_LIMIT]), len(rows) > FACT_LIMIT


def fuse(vector, facts):
    """Rank fusion, never add raw cosine to a binary role signal."""
    merged = {}
    for name, candidates in [('vector', vector), ('fact', facts)]:
        for rank, candidate in enumerate(candidates, 1):
            row = merged.setdefault(candidate['chunk_id'], dict(candidate, candidate_ranks={}, fusion_score=0.0))
            row['candidate_ranks'][name] = rank
            row['fusion_score'] += 1.0 / (60 + rank)
    ordered = sorted(merged.values(), key=lambda c: (-c['fusion_score'], -c['score'], c['chunk_id']))
    return [dict(row, merged_rank=i) for i, row in enumerate(ordered, 1)]


def merge_candidates(db, question, vector, distance, model, min_score):
    started = perf_counter()
    facts, saturated = fact_candidates(db, question, distance, model, min_score)
    fact_seconds = perf_counter()-started
    started = perf_counter()
    merged = fuse(vector, facts)
    from rag_ranking import rank_candidates
    ranked = rank_candidates(db, question, merged)
    audit = dict(vector_count=len(vector), fact_count=len(facts), merged_count=len(merged),
                 fact_saturated=saturated, fact_seconds=fact_seconds,
                 fusion_rerank_seconds=perf_counter()-started)
    # A capped fact search cannot prove a unique answer. Do not hide alternatives.
    for rank, row in enumerate(ranked, 1):
        row['retrieval'] = dict(audit, final_rank=rank)
        if saturated:
            row.setdefault('ranking', {})['ambiguous'] = True
    return ranked
