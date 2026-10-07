"""Chunk-level semantic retrieval for RAG."""

import math
from time import perf_counter
from collections import defaultdict

from sqlalchemy import select, text

import embedding_service
from models import EmailEmbeddingChunk


class RagQueryError(ValueError):
    """Invalid RAG retrieval parameters."""


def retrieve_rag_chunks(
    db,
    query: str,
    limit: int = 8,
    min_score: float | None = None,
    max_chunks_per_email: int = 2,
):
    if not isinstance(query, str) or not query.strip():
        raise RagQueryError("Query must not be empty")

    if not 1 <= limit <= 20:
        raise RagQueryError("Limit must be between 1 and 20")

    if min_score is not None and (
        not math.isfinite(min_score) or not -1 <= min_score <= 1
    ):
        raise RagQueryError("min_score must be between -1 and 1")

    if not 1 <= max_chunks_per_email <= 5:
        raise RagQueryError("max_chunks_per_email must be between 1 and 5")

    query = query.strip()
    model = embedding_service.MODEL_NAME

    has_embeddings = db.scalar(
        select(EmailEmbeddingChunk.id)
        .where(EmailEmbeddingChunk.embedding_model == model)
        .limit(1)
    )

    if has_embeddings is None:
        return []

    vector = embedding_service.embed_query(query)
    distance = EmailEmbeddingChunk.embedding.cosine_distance(vector)

    db.execute(
        text(
            "SELECT set_config("
            "'hnsw.iterative_scan', "
            "'strict_order', "
            "true"
            ")"
        )
    )

    pool = max(50, limit * 10)

    while True:
        pool = min(pool, 1000)

        db.execute(
            text("SELECT set_config('hnsw.ef_search', :size, true)"),
            {"size": str(pool)},
        )

        statement = (
            select(
                EmailEmbeddingChunk.id.label("chunk_id"),
                EmailEmbeddingChunk.email_id,
                EmailEmbeddingChunk.chunk_index,
                EmailEmbeddingChunk.chunk_text,
                distance.label("distance"),
            )
            .where(EmailEmbeddingChunk.embedding_model == model)
            .order_by(distance)
            .limit(pool)
        )

        if min_score is not None:
            statement = statement.where(distance <= 1.0 - min_score)

        started = perf_counter()
        rows = db.execute(statement).all()
        vector_seconds = perf_counter() - started

        from rag_candidates import as_chunks, merge_candidates
        candidates = merge_candidates(db, query, as_chunks(rows), distance, model, min_score)
        for candidate in candidates:
            candidate['retrieval']['vector_seconds'] = vector_seconds

        results = []
        chunks_per_email = defaultdict(int)

        for candidate in candidates:
            email_id = candidate['email_id']
            if chunks_per_email[email_id] >= max_chunks_per_email:
                continue
            results.append(candidate)
            chunks_per_email[email_id] += 1

            if len(results) >= limit:
                return results

        if len(rows) < pool or pool >= 1000:
            return results

        pool *= 2
