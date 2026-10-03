"""Conservative checks for literal labelled scalar values, not prose inference."""

import re
import unicodedata


_QUESTION_WORDS = set("what when is are the my your in on at for of please tell me ما متى هو هي في من فضلك الخاص بي".split())


def _tokens(text):
    text = unicodedata.normalize('NFKC', text).casefold().replace('_', ' ')
    text = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', text)
    text = text.translate(str.maketrans('أإآى', 'اااي'))
    return set(re.findall(r'[^\W_]+', text))


def explicit_fields(content):
    """Keep literal labels/values; never infer roles from ordering or prose."""
    lines = content.splitlines()
    fields = []
    for index, line in enumerate(lines):
        label, separator, value = line.partition(':')
        if not separator:
            label = line.strip()
            following = next((s.strip() for s in lines[index + 1:] if s.strip()), '')
            # Vertical fields need an identifier-like value, not another heading.
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9./-]{1,39}', following) or not any(c.isdigit() for c in following):
                continue
            value = following
        label, value = label.strip(), value.strip()
        if (not 1 <= len(label) <= 60 or not 1 <= len(value) <= 80
                or len(_tokens(label)) > 6 or len(value.split()) > 6
                or not any(c.isalpha() for c in label)
                or any(c in label + value for c in '[]<>|')
                or not any(c.isdigit() for c in value)):
            continue
        fields.append({'label': label, 'value': value})
    return fields


def answer_candidate(question, evidence):
    """Match a single explicit field, with all question qualifiers supported.

    This deliberately does not translate labels, resolve aliases, or parse dates
    out of prose. Ambiguity disables deterministic answering.
    """
    requested = _tokens(question) - _QUESTION_WORDS
    if not requested:
        return None
    candidates = []
    for source in evidence:
        fields = explicit_fields(source['content'])
        for field in fields:
            label = _tokens(field['label']) - _QUESTION_WORDS
            if not label or not label <= requested:
                continue
            if requested - label - _tokens(source['subject']):
                continue
            # A literal quote should not silently change the answer language.
            if bool(re.search(r'[\u0600-\u06ff]', question)) != bool(re.search(r'[\u0600-\u06ff]', field['label'])):
                continue
            candidates.append(dict(field, email_id=source['email_id'],
                                   competing_values=[f['value'] for f in fields if f['value'] != field['value']]))
    distinct = {(c['email_id'], c['label'], c['value']) for c in candidates}
    if len(distinct) != 1:
        return None
    result = candidates[0]
    result['competing_values'] = sorted({v for c in candidates for v in c['competing_values']})
    return result


def has_role_conflict(answer, candidate):
    if not candidate:
        return False
    answer = re.sub(r'\[email_id=\d+\]', '', answer)

    def present(value):
        return re.search(r'(?<!\w)' + re.escape(value) + r'(?!\w)', answer) is not None
    # Reject a substituted competing value, not an answer mentioning both roles.
    return not present(candidate['value']) and any(present(v) for v in candidate['competing_values'])


def is_abstention(answer):
    # The service validates any citations before discarding refusal prose.
    return re.search(r'\bINSUFFICIENT_EVIDENCE\b', answer) is not None
