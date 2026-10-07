"""Conservative checks for literal labelled scalar values, not prose inference."""

import re
import unicodedata
from rag_evidence import _records


_QUESTION_WORDS = set("what when is are the my your in on at for of please tell me ما متى هو هي في من فضلك الخاص بي".split())


def _tokens(text):
    text = unicodedata.normalize('NFKC', text).casefold().replace('_', ' ')
    text = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', text)
    text = text.translate(str.maketrans('أإآى', 'اااي'))
    return set(re.findall(r'[^\W_]+', text))


def explicit_fields(content, *, include_unusable=False):
    """Read short literal fields, retaining offsets in the refined content."""
    lines = list(re.finditer(r'[^\r\n]+', content))
    fields = []
    observed = {}
    for index, line in enumerate(lines):
        label, separator, value = line[0].partition(':')
        end = line.end()
        # A clock colon is not a label/value separator.
        if separator and re.search(r'\d$', label) and re.match(r'\d{2}\b', value):
            continue
        if not separator:
            following = lines[index + 1] if index + 1 < len(lines) else None
            if following is None:
                continue
            value = following[0].strip()
            # Without a colon, accept only identifier-like values.
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9./-]{1,39}', value) or not any(c.isdigit() for c in value):
                continue
            end = following.end()
        label, value = label.strip(), value.strip()
        observed.setdefault(tuple(sorted(_role_tokens(label))), set()).add(value)
        unusable = (not 1 <= len(label) <= 60 or not 1 <= len(value) <= 80
                or len(_tokens(label)) > 6 or len(value.split()) > 6
                or not re.fullmatch(r'[^\W\d_][\w ()/\-]*', label)
                or not re.fullmatch(r'[\w\s.,/():+%$€£\-]+', value)
                or re.search(r':(?!\d{2}\b)', value)
                or len(value.split()) > 4 and not any(c.isdigit() for c in value))
        fields.append({'label': label, 'value': value, 'usable': not unusable,
                       'span': [line.start(), end],
                       'literal_evidence': content[line.start():end]})
    for field in fields:
        field['conflicting_values'] = len(observed[tuple(sorted(_role_tokens(field['label'])))]) > 1
    return fields if include_unusable else [f for f in fields if f['usable']]


_NON_LOOKUP = set('why how explain summarize compare difference better important should not except without or لماذا كيف اشرح لخص قارن افضل اهم ينبغي لا ليس غير عدا او'.split())


def _role_tokens(text):
    # Normalize Arabic definite articles and attached conjunctions consistently.
    words = _tokens(text)
    plurals = {'times': 'time', 'dates': 'date', 'amounts': 'amount', 'values': 'value'}
    words = {plurals.get(word, word) for word in words}
    return {w[2:] if w.startswith('ال') and len(w) > 3 else w
            for w in words} - _QUESTION_WORDS


def resolve_answer(question, evidence):
    """Resolve a direct field lookup; ambiguity or interpretation returns [].

    Single-field compatibility is exposed through answer_candidate below.
    Facts remain literal and carry provenance in the selected source chunk.
    """
    from fact_roles import intent, matching_fields
    request = intent(question)
    if request:
        matches = matching_fields(request, evidence)
        return matches if len(matches) == 1 else []
    normalized = unicodedata.normalize('NFKC', question).casefold().strip()
    if not re.match(r'^(what|when)\b|^(ما|متى)\s', normalized):
        return []
    coordinated = re.sub(r'\bوال(?=[\u0600-\u06ff])', 'و ال', question)
    if _tokens(coordinated) & _NON_LOOKUP:
        return []
    multiple = bool(_tokens(coordinated) & {'and', 'و'})
    requested = _role_tokens(coordinated) - {'and', 'و'}
    if not requested:
        return []
    matches = []
    for source in evidence:
        if not isinstance(source.get('email_id'), int) or source['email_id'] <= 0:
            continue
        fields = source.get('fields')
        if fields is None:
            fields = explicit_fields(source['content'], include_unusable=True)
        records = _records(source['content'])
        for field in fields:
            role = _role_tokens(field['label'])
            if not role or not role <= requested:
                continue
            if not multiple and requested - role - _role_tokens(source.get('qualifier_text', source['subject'])):
                continue
            if bool(re.search(r'[\u0600-\u06ff]', question)) != bool(re.search(r'[\u0600-\u06ff]', field['label'])):
                continue
            if field['conflicting_values'] or not field['usable']:
                return []
            matches.append(dict(field, role=sorted(role), source_label=field['label'],
                                email_id=source['email_id'], chunk_id=source.get('chunk_id'),
                                chunk_index=source.get('chunk_index'),
                                reason='unique_explicit_label', span_basis=field.get('span_basis', 'refined_content'),
                                record_index=field.get('record_index', next((i for i, (start, end) in enumerate(records)
                                                   if start <= field['span'][0] < end), -1)),
                                competing_values=[f['value'] for f in fields if f['value'] != field['value']]))
    # Same literal field repeated in overlapping chunks is not a new answer.
    unique = {}
    for fact in matches:
        key = (fact['email_id'], tuple(fact['role']), fact['value'])
        if key not in unique:
            unique[key] = fact
        else:
            unique[key]['competing_values'] = sorted(set(unique[key]['competing_values'] + fact['competing_values']))
    facts = list(unique.values())
    if not multiple:
        return facts if len(facts) == 1 else []
    if (len(facts) < 2 or len({f['email_id'] for f in facts}) != 1
            or len({tuple(f['role']) for f in facts}) != len(facts)
            or set().union(*(set(f['role']) for f in facts)) != requested):
        return []
    if any(set(a['role']) < set(b['role']) for a in facts for b in facts):
        return []
    # Do not combine separate, potentially unrelated records across chunks.
    if len({(f['chunk_id'], f['chunk_index'], f['record_index']) for f in facts}) != 1:
        return []
    return facts


def answer_candidate(question, evidence):
    """Compatibility helper for callers that require exactly one fact."""
    facts = resolve_answer(question, evidence)
    return facts[0] if len(facts) == 1 else None


def format_facts(facts):
    """Application-owned wording; no model may rewrite literal values."""
    return '\n'.join(f"{f.get('answer_label', f['source_label'])}: {f.get('display_value', f['value'])} [email_id={f['email_id']}]" for f in facts)


def has_role_conflict(answer, candidate):
    if not candidate:
        return False
    answer = re.sub(r'\[email_id=\d+\]', '', answer)

    def present(value):
        return re.search(r'(?<!\w)' + re.escape(value) + r'(?!\w)', answer) is not None
    # Reject a substituted competing value, not an answer mentioning both roles.
    return not present(candidate['value']) and any(present(v) for v in candidate['competing_values'])


def is_abstention(answer):
    # Discard clear refusal prose even when the model adds syntactically valid citations.
    return bool(re.search(r'\binsufficient[\s_]+evidence\b|'
                          r'\b(?:cannot|could not|can\'t) (?:find|verify|determine)\b|'
                          r'لا توجد معلومات كافية|لم أتمكن من (?:العثور|التحقق)', answer, re.I))
