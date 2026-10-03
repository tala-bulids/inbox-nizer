"""Conservative, query-scoped evidence from repeated labelled records.

No generated facts or domain dictionaries: every excerpt is an original span.
If structure or the qualifier is ambiguous, preserve the retrieved chunks.
"""

import re
import unicodedata
from collections import defaultdict

_STOP = set('what when where which who how is are was were my the a an of in on at does do please tell me all both list and or متي اين ما ماذا هل هو هي في يوم تاريخ موعد كل جميع و او'.split())
_RELATIONS = {'to': 'to', 'for': 'to', 'الي': 'to', 'ل': 'to',
              'from': 'from', 'من': 'from'}


def _words(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    text = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', text)
    text = text.translate(str.maketrans('أإآىة', 'ااايه'))
    return re.findall(r'[^\W_]+', text, re.UNICODE)


def _entity(word):
    return word[2:] if word.startswith('ال') and len(word) > 3 else word


def _query_features(question):
    words = _words(question)
    expanded = []
    for word in words:
        # Arabic attaches the general to/for preposition to its argument.
        if word.startswith('لل') and len(word) >= 5:
            expanded.extend(['ل', 'ال' + word[2:]])
        elif word.startswith('ل') and len(word) >= 4:
            expanded.extend(['ل', word[1:]])
        else:
            expanded.append(word)
    relations = [(_RELATIONS[word], _entity(expanded[i + 1]))
                 for i, word in enumerate(expanded[:-1]) if word in _RELATIONS]
    terms = {_entity(w) for w in expanded if w not in _STOP and w not in _RELATIONS and len(w) > 1}
    return relations, terms


def _has_relation(words, relation, target):
    for i, word in enumerate(words[:-1]):
        if _RELATIONS.get(word) == relation and _entity(words[i + 1]) == target:
            return True
    return False


def _records(text):
    labels = defaultdict(list)
    for match in re.finditer(r'(?m)^([^\n:|]{2,50}):[ \t]*([^\n]+)', text):
        if len(match[2]) <= 120 and '|' not in match[2]:
            labels[' '.join(_words(match[1]))].append(match)
    candidates = [matches for matches in labels.values()
                  if len(matches) >= 2 and len({m[2].strip() for m in matches}) > 1]
    if not candidates:
        return []
    # One recurring field starts each record; other fields stay attached to it.
    starts = min(candidates, key=lambda matches: matches[0].start())
    return [(m.start(), starts[i + 1].start() if i + 1 < len(starts) else len(text))
            for i, m in enumerate(starts)]


def select_evidence(question, chunks):
    """Return copied chunks and an audit trail, without changing stored content.

    Narrow only within a chunk with explicit repeated structure. Other retrieved
    chunks remain available, including continuations needed by multi-part answers.
    """
    question_words = _words(question)
    # Do not narrow comparisons/lists or potentially coordinated targets.
    if (set(question_words) & {'all', 'both', 'compare', 'list', 'and', 'or', 'versus', 'not', 'except', 'without',
                              'كل', 'جميع', 'قارن', 'او', 'و', 'لا', 'ليس', 'غير', 'عدا'}
            or any(word.startswith('وال') and len(word) > 4 for word in question_words)):
        return [dict(chunk) for chunk in chunks], []
    relations, terms = _query_features(question)
    output, audit = [], []
    for chunk in chunks:
        original = chunk['text']
        spans = _records(original)
        chosen = []
        if spans:
            tokens = [_words(original[start:end]) for start, end in spans]
            if relations:
                chosen = [i for i, words in enumerate(tokens)
                          if all(_has_relation(words, role, target) for role, target in relations)]
                reason = 'explicit_relation'
            else:
                # Only query terms that actually distinguish these records count.
                sets = [{_entity(w) for w in words} & terms for words in tokens]
                shared = set.intersection(*sets)
                distinguishing = [s - shared for s in sets]
                chosen = [i for i, s in enumerate(distinguishing) if s]
                reason = 'explicit_qualifier'
        if chosen and len(chosen) < len(spans):
            # Keep shared introductory context (IDs, instructions, common details).
            parts = [original[:spans[0][0]].strip()]
            parts.extend(original[spans[i][0]:spans[i][1]].strip() for i in chosen)
            refined = dict(chunk, text='\n\n'.join(part for part in parts if part))
            output.append(refined)
            audit.append({'email_id': chunk['email_id'], 'chunk_index': chunk['chunk_index'],
                          'reason': reason, 'selected_spans': [spans[i] for i in chosen],
                          'record_count': len(spans)})
        else:
            output.append(dict(chunk))
    return output, audit
