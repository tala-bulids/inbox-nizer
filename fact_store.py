"""Fact persistence and scoped reads. Callers own transaction commits."""
import logging
from sqlalchemy import select, text, func
import email_facts
from models import Email, EmailFact, EmailFactState
from rag_grounding import explicit_fields
from relational_facts import supported
from fact_roles import label_role

logger = logging.getLogger(__name__)


def schema_available(db):
    return bool(db.scalar(text("SELECT to_regclass('email_facts') IS NOT NULL AND to_regclass('email_fact_states') IS NOT NULL")))


def refresh_facts(email, db, *, force=False):
    counts = dict(created=0, updated=0, skipped=0, deleted=0, unchanged_emails=0)
    with db.begin_nested():
        saved = db.scalar(select(Email).where(Email.id == email.id).with_for_update()
                          .execution_options(populate_existing=True))
        if saved is None:
            raise ValueError('Email must be stored before extracting facts')
        digest = email_facts.input_hash(saved)
        state = db.get(EmailFactState, saved.id, populate_existing=True)
        rows = db.scalars(select(EmailFact).where(EmailFact.email_id == saved.id)).all()
        if not force and state and state.input_hash == digest and state.extractor_version == email_facts.EXTRACTOR_VERSION:
            counts.update(skipped=len(rows), unchanged_emails=1)
            return counts
        # Finish extraction before deleting or replacing previously valid facts.
        facts = email_facts.extract_facts(saved)
        current = {r.fact_key: r for r in rows}
        for fact in facts:
            row = current.pop(fact['fact_key'], None)
            if row is None:
                row = EmailFact(email_id=saved.id, **fact)
                db.add(row)
                counts['created'] += 1
            elif any(getattr(row, key) != value for key, value in fact.items()):
                for key, value in fact.items():
                    setattr(row, key, value)
                counts['updated'] += 1
            else:
                counts['skipped'] += 1
        for row in current.values():
            db.delete(row)
            counts['deleted'] += 1
        if state is None:
            state = EmailFactState(email_id=saved.id)
            db.add(state)
        state.input_hash, state.extractor_version = digest, email_facts.EXTRACTOR_VERSION
        state.updated_at = func.now()
        db.flush()
    return counts


def _compact(value):
    return ' '.join(value.split())


def fact_evidence(db, evidence, *, preview=False):
    """Only current facts supported by already-selected SOURCE text are eligible.

    No global type-only search: authorization must scope retrieval first. Preview
    uses the identical extractor in memory and performs no schema or data writes.
    """
    if not evidence:
        return evidence, {'mode': 'preview' if preview else 'stored', 'facts': []}
    if not preview and not schema_available(db):
        return evidence, {'mode': 'schema_missing', 'facts': []}
    ids = {item['email_id'] for item in evidence}
    emails = {e.id: e for e in db.scalars(select(Email).where(Email.id.in_(ids))).all()}
    states = {} if preview else {s.email_id: s for s in db.scalars(select(EmailFactState).where(EmailFactState.email_id.in_(ids))).all()}
    grouped = {}
    if preview:
        for email in emails.values():
            grouped[email.id] = email_facts.extract_facts(email)
    else:
        for row in db.scalars(select(EmailFact).where(EmailFact.email_id.in_(ids))).all():
            grouped.setdefault(row.email_id, []).append({c.name: getattr(row, c.name) for c in EmailFact.__table__.columns})
    output, audit = [], []
    for source in evidence:
        email = emails.get(source['email_id'])
        state = states.get(source['email_id'])
        fresh = email is not None and (preview or state and state.input_hash == email_facts.input_hash(email)
                                       and state.extractor_version == email_facts.EXTRACTOR_VERSION)
        fields = []
        if fresh:
            body = email.body or ''
            for fact in grouped.get(email.id, []):
                start, end = fact['source_start'], fact['source_end']
                if (fact['extractor_version'] != email_facts.EXTRACTOR_VERSION
                        or body[start:end] != fact['source_text']
                        or fact['literal_value'] not in fact['source_text']
                        or not supported(fact, source['content'])):
                    continue
                normalized = fact['normalized_value']
                display = fact['literal_value']
                if normalized and normalized['kind'] == 'date' and normalized['value'] != display:
                    display += ' (' + normalized['value'] + ')'
                field = dict(label=fact['source_label'], value=fact['literal_value'], display_value=display,
                             usable=True, conflicting_values=False, span=[start, end],
                             literal_evidence=fact['source_text'], span_basis='stored_body',
                             record_index=f"{fact['record_start']}:{fact['record_end']}",
                             normalization=normalized, extraction_reason=fact['extraction_reason'],
                             extractor_version=fact['extractor_version'],
                             canonical_role=label_role(fact['source_label']),
                             relation=(normalized or {}).get('relation'))
                fields.append(field)
                audit.append(dict(email_id=email.id, chunk_id=source['chunk_id'], **field))
        if fields:
            # Preserve unparseable/conflicting raw fields as ambiguity blockers.
            fields.extend(explicit_fields(source['content'], include_unusable=True))
            output.append(dict(source, fields=fields,
                               qualifier_text=(email.subject or '') + ' ' + (email.sender or '')))
        else:
            output.append(source)
    return output, {'mode': 'preview' if preview else 'stored', 'facts': audit}


def backfill_facts(db, *, batch_size=100, force=False, apply=False, progress=None):
    if not 1 <= batch_size <= 500:
        raise ValueError('batch_size must be between 1 and 500')
    if apply and not schema_available(db):
        raise RuntimeError('Apply the facts Alembic migration first')
    totals = dict(processed=0, created=0, updated=0, skipped=0, deleted=0,
                  unchanged_emails=0, failed=0, discovered=0)
    last_id = 0
    while True:
        ids = list(db.scalars(select(Email.id).where(Email.id > last_id).order_by(Email.id).limit(batch_size)))
        if not ids:
            break
        for email_id in ids:
            try:
                email = db.get(Email, email_id)
                if apply:
                    counts = refresh_facts(email, db, force=force)
                    db.commit()
                    for key, value in counts.items():
                        totals[key] += value
                else:
                    totals['discovered'] += len(email_facts.extract_facts(email))
            except Exception as error:
                if apply:
                    db.rollback()
                totals['failed'] += 1
                logger.warning('Fact extraction failed for email %s (%s)', email_id, type(error).__name__)
            totals['processed'] += 1
            last_id = email_id
            if progress:
                progress(email_id, totals.copy())
    return totals
