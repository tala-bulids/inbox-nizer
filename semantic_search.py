"""Nearest-chunk retrieval, deduplicated by email."""
import math

from sqlalchemy import select, text
from sqlalchemy.orm import defer

import embedding_service
from models import Email, EmailEmbeddingChunk


class SemanticQueryError(ValueError):
    """Invalid search parameters."""


def semantic_search(db, query: str, limit: int = 10, min_score: float | None = None):
    if not isinstance(query, str) or not query.strip():
        raise SemanticQueryError('Query must not be empty')
    if not 1 <= limit <= 50:
        raise SemanticQueryError('Limit must be between 1 and 50')
    if min_score is not None and (not math.isfinite(min_score) or not -1 <= min_score <= 1):
        raise SemanticQueryError('min_score must be between -1 and 1')
    query = query.strip()
    model = embedding_service.MODEL_NAME
    if db.scalar(select(EmailEmbeddingChunk.id).where(EmailEmbeddingChunk.embedding_model == model).limit(1)) is None:
        return []
    vector = embedding_service.embed_query(query)
    distance = EmailEmbeddingChunk.embedding.cosine_distance(vector)
    pool = max(100, limit * 10)
    # pgvector 0.8+ can continue scanning when filters remove ANN candidates.
    db.execute(text("SELECT set_config('hnsw.iterative_scan', 'strict_order', true)"))
    matches = {}
    while True:
        db.execute(text("SELECT set_config('hnsw.ef_search', :size, true)"), {'size': str(min(pool, 1000))})
        statement = (select(EmailEmbeddingChunk.email_id, EmailEmbeddingChunk.chunk_text, distance.label('distance'))
                     .where(EmailEmbeddingChunk.embedding_model == model).order_by(distance).limit(pool))
        if min_score is not None:
            statement = statement.where(distance <= 1.0 - min_score)
        rows = db.execute(statement).all()
        for row in rows:
            score = max(-1.0, min(1.0, 1.0 - float(row.distance)))
            if row.email_id not in matches or score > matches[row.email_id]['score']:
                matches[row.email_id] = dict(score=score, matched_text=row.chunk_text[:2000])
        if len(matches) >= limit or len(rows) < pool:
            break
        pool *= 2
    ranked = sorted(matches, key=lambda email_id: (-matches[email_id]['score'], email_id))[:limit]
    if not ranked:
        return []
    emails = {email.id: email for email in db.scalars(select(Email).options(defer(Email.body), defer(Email.raw_payload)).where(Email.id.in_(ranked)))}
    return [dict(email=emails[email_id], **matches[email_id]) for email_id in ranked if email_id in emails]
