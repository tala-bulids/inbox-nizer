"""Conservative facts from the stored body; no model, network, or DB writes."""
import hashlib
import json
import re
from decimal import Decimal

from deadline_extractor import (_normalized, _PHRASE, _PREFIX, _DATE_ORDER,
                                _MONTH_ORDER, _DAYS, _resolve_date, parse_email_datetime)
from email_utils import extract_main_content
from rag_grounding import explicit_fields, _role_tokens
from rag_evidence import _records

EXTRACTOR_VERSION = 'facts-v1'
_STRONG_DEADLINE = re.compile(r'^(?:deadline|due (?:on|by)|no later than|اخر (?:يوم|موعد)|الموعد النهائي|الموعد الاخير|مستحق في)\b', re.I)
_UNCERTAIN = re.compile(r'\b(?:not|never|cancelled|canceled|old|previous|formerly|if|unless|لا|لم|لن|ليس|السابق|القديم|ملغي|اذا)\b', re.I)


def input_hash(email):
    data = [email.subject or '', email.body or '', email.email_date or '']
    return hashlib.sha256(json.dumps(data, ensure_ascii=False).encode()).hexdigest()


def normalize_value(label, value, reference=None, evidence=''):
    """No locale guessing, implicit timezone, midnight, or unqualified year."""
    roles = _role_tokens(label)
    normalized, _ = _normalized(value.strip().strip('.'))
    if roles & {'date', 'deadline', 'تاريخ', 'موعد', 'يوم'}:
        try:
            explicit = _resolve_date(normalized, None)
            if explicit:
                return dict(kind='date', value=explicit.isoformat(), basis='explicit_year')
            match = _DATE_ORDER.fullmatch(normalized) or _MONTH_ORDER.fullmatch(normalized)
            if match and not match['year'] and reference:
                # A nearby named day/month AND matching weekday anchor the year.
                candidate = _resolve_date(normalized + ' ' + str(reference.year), None)
                context, _ = _normalized(evidence)
                weekdays = {day for name, day in _DAYS.items() if re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', context)}
                if (candidate and weekdays == {candidate.weekday()}
                        and abs((candidate - reference.date()).days) <= 45):
                    return dict(kind='date', value=candidate.isoformat(),
                                basis='message_year_nearby_matching_weekday')
        except (ValueError, OverflowError):
            pass
        return None
    if roles & {'time', 'times', 'وقت', 'ساعة'}:
        match = re.fullmatch(r'(\d{1,2}):(\d{2})(?:\s+(UTC|GMT|[+-]\d{2}:\d{2}))?', normalized, re.I)
        if match and int(match[1]) < 24 and int(match[2]) < 60:
            zone = match[3].upper() if match[3] else None
            if zone and zone[0] in '+-' and (int(zone[1:3]) > 23 or int(zone[4:]) > 59):
                return None
            return dict(kind='time', value=f'{int(match[1]):02}:{int(match[2]):02}', timezone=zone)
    if roles & {'amount', 'مبلغ'}:
        match = re.fullmatch(r'(?:(?P<before>[A-Z]{3}|[$€£])\s*)?(?P<number>\d+(?:\.\d+)?)(?:\s*(?P<after>[A-Z]{3}|[$€£]))?', value)
        if match and not (match['before'] and match['after']):
            return dict(kind='amount', value=str(Decimal(match['number'])), currency_literal=match['before'] or match['after'])
    return None


def extract_facts(email):
    """Return only facts with exact offsets in Email.body, never in summaries."""
    body = email.body or ''
    main = extract_main_content(email.subject or '', body)
    reference = parse_email_datetime(email.email_date)
    fields = explicit_fields(main)
    candidates = [(f['label'], f['value'], f['literal_evidence'], 'labelled_field') for f in fields]
    normalized, offsets = _normalized(main)
    for match in _PHRASE.finditer(normalized):
        if not match['value'] or not _STRONG_DEADLINE.match(match[0]):
            continue
        prefix = re.match(_PREFIX, match[0], re.I)
        if not prefix:
            continue
        clause_start = max(normalized.rfind(c, 0, match.start()) for c in '\n.!?؛') + 1
        if _UNCERTAIN.search(normalized[clause_start:match.end()]):
            continue
        label = main[offsets[match.start()]:offsets[match.start() + prefix.end()]].strip(' :')
        value = main[offsets[match.start('value')]:offsets[match.end('value')]]
        # Clock-bearing prose is left to the existing task/deadline pipeline.
        if match['clock']:
            continue
        evidence = main[offsets[match.start()]:offsets[match.end()]]
        if not (_DATE_ORDER.fullmatch(match['value']) or _MONTH_ORDER.fullmatch(match['value'])
                or re.fullmatch(r'\d{4}-\d{1,2}-\d{1,2}', match['value'])):
            continue
        candidates.append((label, value, evidence, 'explicit_deadline_expression'))
    records = _records(body)
    facts = {}
    for label, value, evidence, reason in candidates:
        start = body.find(evidence)
        # Cleaning may transform text; do not manufacture offsets or attribution.
        if start < 0 or body.find(evidence, start + 1) >= 0 or value not in evidence:
            continue
        end = start + len(evidence)
        role = '_'.join(sorted(_role_tokens(label)))
        if not role or len(role) > 255:
            continue
        record = next(([a, b] for a, b in records if a <= start < b), [0, len(body)])
        if end > record[1]:
            continue
        normalized_value = normalize_value(label, value, reference, evidence)
        key = hashlib.sha256(json.dumps([role, value, start, end], ensure_ascii=False).encode()).hexdigest()
        facts[key] = dict(fact_key=key, role=role, source_label=label, literal_value=value,
                          normalized_value=normalized_value, source_text=evidence,
                          source_start=start, source_end=end, record_start=record[0], record_end=record[1],
                          extraction_reason=reason, extractor_version=EXTRACTOR_VERSION)
    return list(facts.values())
