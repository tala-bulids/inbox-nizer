"""Transactional indexing; callers own commit/rollback."""
import hashlib

from sqlalchemy import select

import embedding_service
from models import Email, EmailEmbeddingChunk
from semantic_content import build_semantic_text, chunk_semantic_text, CONTENT_VERSION


def content_hash(text, model=None):
    model = model or embedding_service.MODEL_NAME
    return hashlib.sha256(f'{model}\0{CONTENT_VERSION}\0{text}'.encode('utf-8')).hexdigest()


def prepare_index(email):
    """Compute model output without an open transaction; apply checks it again."""
    texts = chunk_semantic_text(build_semantic_text(email))
    return texts, embedding_service.embed_passages(texts) if texts else []


def index_email(email, db, *, prepared=None):
    counts = dict(created=0, updated=0, skipped=0, deleted=0)
    # Lock the parent so concurrent sync/backfill cannot create competing chunks.
    with db.begin_nested():
        saved = db.scalar(select(Email).where(Email.id == email.id).with_for_update()
                          .execution_options(populate_existing=True))
        if saved is None:
            raise ValueError('Email must be stored before indexing')
        model = embedding_service.MODEL_NAME
        texts = chunk_semantic_text(build_semantic_text(saved))
        rows = db.scalars(select(EmailEmbeddingChunk).where(EmailEmbeddingChunk.email_id == saved.id)).all()
        current = {row.chunk_index: row for row in rows if row.embedding_model == model}
        pending = []
        for index, chunk in enumerate(texts):
            digest = content_hash(chunk, model)
            row = current.get(index)
            if row is not None and row.content_hash == digest and row.chunk_text == chunk:
                counts['skipped'] += 1
            else:
                pending.append((index, chunk, digest, row))
        # Encode before replacing anything. A failure leaves existing chunks intact.
        if prepared is not None:
            prepared_texts, prepared_vectors = prepared
            if texts != prepared_texts or len(prepared_vectors) != len(texts):
                raise ValueError('Email changed during embedding preparation')
            vectors = [prepared_vectors[item[0]] for item in pending]
        else:
            vectors = embedding_service.embed_passages([item[1] for item in pending]) if pending else []
        if len(vectors) != len(pending):
            raise ValueError('Encoder returned the wrong number of embeddings')
        for (index, chunk, digest, row), vector in zip(pending, vectors):
            if row is None:
                row = EmailEmbeddingChunk(email_id=saved.id, chunk_index=index, embedding_model=model)
                db.add(row)
                counts['created'] += 1
            else:
                counts['updated'] += 1
            row.chunk_text, row.content_hash, row.embedding = chunk, digest, vector
        for row in rows:
            if row.embedding_model != model or row.chunk_index >= len(texts):
                db.delete(row)
                counts['deleted'] += 1
        db.flush()
    return counts


def index_all_emails(db, *, batch_size=100, progress=None):
    if batch_size < 1:
        raise ValueError('batch_size must be positive')
    totals = dict(processed=0, created=0, updated=0, skipped=0, deleted=0)
    last_id = 0
    while True:
        emails = db.scalars(select(Email).where(Email.id > last_id).order_by(Email.id).limit(batch_size)).all()
        if not emails:
            break
        for email in emails:
            counts = index_email(email, db)
            totals['processed'] += 1
            for field, value in counts.items():
                totals[field] += value
            last_id = email.id
            if progress:
                progress(last_id, totals.copy())
    return totals
