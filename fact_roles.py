"""Small bilingual vocabulary for explicit roles, not general intent inference."""
import re
import unicodedata


def words(text):
    text = unicodedata.normalize('NFKC', text).casefold().replace('_', ' ')
    text = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', text)
    text = text.translate(str.maketrans('أإآىة', 'ااايه'))
    return [w[2:] if w.startswith('ال') and len(w) > 3 else w
            for w in re.findall(r'[^\W_]+', text)]


SIDES = {
    'departure': {'departure', 'depart', 'leave', 'takeoff', 'مغادره', 'اقلاع'},
    'arrival': {'arrival', 'arrive', 'وصول'},
    'start': {'start', 'بدايه', 'بدء'},
    'end': {'end', 'نهايه'},
}
KINDS = {'time': {'time', 'times', 'وقت', 'ساعه'}, 'date': {'date', 'dates', 'تاريخ'}}
TRAVEL = {'travel', 'trip', 'flight', 'سفر', 'سفري', 'سفرتي', 'رحله', 'رحلتي'}
LOCATIONS = {'origin': {'origin', 'مبدا'}, 'destination': {'destination', 'وجهه'}}
STOP = set('what when where is are do does my your the a an in on at for of please tell me ما متي اين وش هو هي في من فضلك بي خاص'.split())
UNSAFE = set('why how explain summarize compare difference should not except without or all both لماذا كيف اشرح لخص قارن ينبغي لا ليس غير عدا او جميع كل'.split())


def label_role(label):
    tokens = set(words(label))
    if tokens & TRAVEL and tokens & KINDS['date'] and tokens <= TRAVEL | KINDS['date']:
        return 'travel_date'
    if tokens in ({'from'}, {'من'}):
        return 'origin'
    if tokens in ({'to'}, {'الي'}):
        return 'destination'
    for role, aliases in LOCATIONS.items():
        if tokens and tokens <= aliases | {'location', 'مكان'} and tokens & aliases:
            return role
    for side, aliases in SIDES.items():
        for kind, names in KINDS.items():
            if tokens & aliases and tokens & names and tokens <= aliases | names:
                return side + '_' + kind
    return None


def intent(question):
    """One clear role plus literal qualifiers; coordination stays with old resolver."""
    tokens = words(question)
    if not tokens or tokens[0] not in {'what', 'when', 'where', 'ما', 'متي', 'اين', 'وش'}:
        return None
    if set(tokens) & (UNSAFE | {'and', 'و'}) or any(t.startswith('وال') for t in tokens):
        return None
    sides = [side for side, aliases in SIDES.items() if set(tokens) & aliases]
    locations = [role for role, aliases in LOCATIONS.items() if set(tokens) & aliases]
    kinds = [kind for kind, aliases in KINDS.items() if set(tokens) & aliases]
    if not sides and not locations and set(tokens) & TRAVEL and (
            set(tokens) & KINDS['date'] or tokens[0] in {'when', 'متي'}):
        role = 'travel_date'
        consumed = TRAVEL | KINDS['date']
    elif len(sides) == 1 and not locations:
        if not kinds and tokens[0] in {'when', 'متي'}:
            kinds = ['time']
        if len(kinds) != 1:
            return None
        role = sides[0] + '_' + kinds[0]
        consumed = SIDES[sides[0]] | KINDS[kinds[0]] | TRAVEL
    elif len(locations) == 1 and not sides and not kinds:
        role = locations[0]
        consumed = LOCATIONS[role] | {'location', 'مكان'}
    else:
        return None
    # Expand the attached Arabic to/for prefix only on remaining qualifiers.
    expanded = []
    for token in tokens:
        if token not in consumed | STOP and token.startswith('ل') and len(token) > 2:
            expanded.extend(['to', token[1:]])
        else:
            expanded.append(token)
    qualifiers, relations = [], []
    index = 0
    while index < len(expanded):
        token = expanded[index]
        if token in {'to', 'الي', 'from', 'من'}:
            target = 'origin' if token in {'from', 'من'} else 'destination'
            end = index + 1
            while end < len(expanded) and expanded[end] not in STOP | {'to', 'الي', 'from', 'من'}:
                end += 1
            value = expanded[index + 1:end]
            if not value:
                return None
            relations.append((target, value))
            index = end
            continue
        if token not in consumed | STOP:
            qualifiers.append(token)
        index += 1
    return dict(role=role, qualifiers=qualifiers, relations=relations,
                language='ar' if re.search(r'[\u0600-\u06ff]', question) else 'en')


def qualified(request, field, source, siblings):
    relation = field.get('relation') or {}
    locations = {key: relation.get(key, '') for key in LOCATIONS}
    if not relation:
        for name in LOCATIONS:
            values = {s['value'] for s in siblings if (s.get('canonical_role') or label_role(s['label'])) == name}
            if len(values) == 1:
                locations[name] = next(iter(values))
    for role, wanted in request['relations']:
        if not set(wanted) <= set(words(locations[role])):
            return False
    context = source.get('qualifier_text', source.get('subject', ''))
    context += ' ' + ' '.join(s['value'] for s in siblings if s.get('usable', True))
    context += ' ' + ' '.join(locations.values())
    return set(request['qualifiers']) <= set(words(context))


def matching_fields(request, evidence):
    """Return all matches; callers must reject ambiguity across emails/records."""
    from rag_grounding import explicit_fields
    from rag_evidence import _records
    matches = {}
    invalid = False
    for source in evidence:
        if not isinstance(source.get('email_id'), int) or source['email_id'] <= 0:
            continue
        spans = _records(source['content'])
        fields = []
        originals = source.get('fields')
        if originals is None:
            originals = explicit_fields(source['content'], include_unusable=True)
        for original in originals:
            field = dict(original)
            field.setdefault('record_index', next((i for i, (a,b) in enumerate(spans) if a <= field['span'][0] < b), -1))
            fields.append(field)
        for field in fields:
            role = field.get('canonical_role') or label_role(field['label'])
            if role != request['role']:
                continue
            siblings = [f for f in fields if f['record_index'] == field['record_index']]
            if not qualified(request, field, source, siblings):
                continue
            if not field.get('usable', True):
                invalid = True
                continue
            if field.get('span_basis') != 'stored_body' and any(
                    f.get('span_basis') == 'stored_body' and f['value'] == field['value']
                    and (f.get('canonical_role') or label_role(f['label'])) == role for f in fields):
                continue
            key = (source['email_id'], role, field['value'], field['record_index'])
            matches.setdefault(key, dict(field, role=role, source_label=field['label'],
                email_id=source['email_id'], chunk_id=source.get('chunk_id'), chunk_index=source.get('chunk_index'),
                reason='unique_explicit_relation', span_basis=field.get('span_basis','refined_content'),
                competing_values=[f['value'] for f in siblings if f['value'] != field['value']],
                answer_label=display_role(role, request['language'])))
    return [] if invalid else list(matches.values())


def display_role(role, language):
    if language == 'en':
        return role.replace('_', ' ')
    if role in LOCATIONS:
        return {'origin': 'مكان المغادرة', 'destination': 'الوجهة'}[role]
    if role == 'travel_date':
        return 'تاريخ السفر'
    side, kind = role.split('_')
    return {'time': 'وقت', 'date': 'تاريخ'}[kind] + ' ' + {
        'departure': 'المغادرة', 'arrival': 'الوصول', 'start': 'البداية', 'end': 'النهاية'}[side]
