"""Build bounded, source-labelled context for RAG generation."""

import json
from sqlalchemy import select
from sqlalchemy.orm import load_only

from models import Email


def build_rag_context(db, chunks, max_chars: int = 12000):
    if not 1000 <= max_chars <= 50000:
        raise ValueError("max_chars must be between 1000 and 50000")
    if not chunks:
        return {
            "context": "",
            "sources": [],
        }

    email_ids = list(dict.fromkeys(chunk["email_id"] for chunk in chunks))

    emails = db.scalars(
        select(Email)
        .options(
            load_only(
                Email.id,
                Email.sender,
                Email.email_date,
                Email.subject,
            )
        )
        .where(Email.id.in_(email_ids))
    ).all()

    emails_by_id = {email.id: email for email in emails}

    blocks = []
    evidence = []
    sources = []
    current_size = 0

    for chunk in chunks:
        email = emails_by_id.get(chunk["email_id"])

        if email is None:
            continue

        if not chunk['text'].strip():
            continue
        # JSON escaping prevents email text from forging source delimiters.
        data = json.dumps({'subject': (email.subject or '')[:500],
                           'from': (email.sender or '')[:300],
                           'email_message_timestamp': (email.email_date or '')[:100],
                           'content': chunk['text'].strip()}, ensure_ascii=False)
        for char in '[]<>':
            data = data.replace(char, '\\u%04x' % ord(char))
        block = f"[SOURCE email_id={email.id} chunk={chunk['chunk_index']}]\n{data}\n[END SOURCE]"

        added_size = len(block) + (2 if blocks else 0)

        if current_size + added_size > max_chars:
            continue

        evidence.append({'email_id': email.id, 'chunk_id': chunk['chunk_id'],
                         'chunk_index': chunk['chunk_index'], 'subject': (email.subject or '')[:500],
                         'content': chunk['text'].strip()})
        blocks.append(block)
        current_size += added_size

        sources.append(
            {
                "email_id": email.id,
                "chunk_id": chunk["chunk_id"],
                "chunk_index": chunk["chunk_index"],
                "score": chunk["score"],
                "subject": (email.subject or '')[:500],
                "from": (email.sender or '')[:300],
                "date": (email.email_date or '')[:100],
            }
        )

    return {
        "context": "\n\n".join(blocks),
        "evidence": evidence,
        "sources": sources,
    }
