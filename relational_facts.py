"""Relationships proved by labels or a directed route and named clock rows."""
import re
from fact_roles import words, SIDES

CLOCK = r'(?:[01]?\d|2[0-3]):[0-5]\d'
PLACE = r'[^\W\d_][\w .\-]{0,55}'
ROUTE = re.compile(rf'(?:(?:from|من)\s+)?(?P<origin>{PLACE})\s+(?:to|إلى|الى|الي|→|->)\s+(?P<destination>{PLACE})', re.I)
ROW = re.compile(rf'(?P<place>{PLACE})\s+(?P<clock>{CLOCK})')
UNSAFE = {'not', 'if', 'unless', 'cancelled', 'canceled', 'لا', 'ليس', 'اذا', 'ملغي'}


def _lines(text):
    return list(re.finditer(r'[^\r\n]+', text))


def _same(a, b):
    return words(a) == words(b)


def candidates(text):
    """Offsets refer to this input. Never infer roles from two bare clocks."""
    lines = _lines(text)
    routes = []
    for number, line in enumerate(lines):
        previous = lines[number-1][0] if number else ''
        if set(words(previous)) & UNSAFE:
            continue
        # Route must occupy its whole line or a whole pipe-delimited cell.
        for cell in re.finditer(r'[^|]+', line[0]):
            match = ROUTE.fullmatch(cell[0].strip())
            if match and not set(words(match[0])) & UNSAFE:
                origin, destination = match['origin'].strip(), match['destination'].strip()
                if _same(origin, destination) or len(words(origin)) > 4 or len(words(destination)) > 4:
                    continue
                start = line.start() + cell.start() + len(cell[0]) - len(cell[0].lstrip())
                routes.append(dict(start=start, end=start+len(match[0]), origin=origin,
                                   destination=destination, anchor=match[0]))
        if number + 1 < len(lines):
            first = re.fullmatch(rf'\s*(?:from|من)\s*:\s*({PLACE})\s*', line[0], re.I)
            following = lines[number+1]
            second = re.fullmatch(rf'\s*(?:to|إلى|الى)\s*:\s*({PLACE})\s*', following[0], re.I)
            if first and second and not _same(first[1],second[1]):
                routes.append(dict(start=line.start(),end=following.end(),origin=first[1].strip(),
                    destination=second[1].strip(),anchor=text[line.start():following.end()]))
    output, contradicted = [], []
    for index, route in enumerate(routes):
        stop = routes[index+1]['start'] if index+1 < len(routes) else len(text)
        # Bound a group; a distant coincidental clock is not evidence.
        group = [l for l in lines if route['end'] <= l.start() < min(stop, route['end']+1000)][:20]
        located = {'origin': [], 'destination': []}
        conflict = False
        anchors = [route['anchor']]
        for n, line in enumerate(group):
            row = ROW.fullmatch(line[0].strip())
            if row:
                place, clock, end = row['place'].strip(), row['clock'], line.end()
                anchor = line[0]
            elif n+1 < len(group) and re.fullmatch(CLOCK, group[n+1][0].strip()):
                place, clock, end = line[0].strip(), group[n+1][0].strip(), group[n+1].end()
                anchor = text[line.start():end]
            else:
                continue
            for role in located:
                if _same(place, route[role]):
                    located[role].append((clock, end, anchor))
                    heading = set(words(group[n-1][0])) if n else set()
                    expected = 'departure' if role == 'origin' else 'arrival'
                    for side, aliases in SIDES.items():
                        if heading and heading <= aliases | {'time','وقت'} and heading & aliases and side != expected:
                            conflict = True
        if conflict:
            contradicted.append((route['start'],stop))
            continue
        # A directional route followed by a directional clock pair is explicit too.
        pairs = [l for l in group if re.fullmatch(rf'\s*({CLOCK})\s*(?:→|->)\s*({CLOCK})\s*', l[0])]
        if not any(located.values()) and len(pairs) == 1:
            pair = pairs[0]
            match = re.fullmatch(rf'\s*({CLOCK})\s*(?:→|->)\s*({CLOCK})\s*', pair[0])
            located = {'origin': [(match[1],pair.end(),pair[0])], 'destination': [(match[2],pair.end(),pair[0])]}
        if any(len(v) != 1 for v in located.values()):
            continue
        end = max(v[0][1] for v in located.values())
        section = text[route['start']:end]
        if set(words(section)) & UNSAFE:
            continue
        anchors += list(dict.fromkeys(v[2] for v in sorted((v[0] for v in located.values()), key=lambda item: item[1])))
        relation = dict(origin=route['origin'], destination=route['destination'], anchors=anchors)
        for role, value in [('origin', route['origin']), ('destination', route['destination']),
                            ('departure_time', located['origin'][0][0]), ('arrival_time', located['destination'][0][0])]:
            output.append(dict(role=role, value=value, start=route['start'], end=end,
                               relation=relation, reason='directed_route_named_clocks'))
    # Standalone vertical labels with a clock (optionally next to a location).
    for index, line in enumerate(lines[:-1]):
        if any(a <= line.start() < b for a,b in contradicted):
            continue
        tokens = set(words(line[0].strip().rstrip(':')))
        sides = [side for side, aliases in SIDES.items() if tokens and tokens <= aliases | {'time','وقت'} and tokens & aliases]
        if len(sides) != 1:
            continue
        next_line = lines[index+1]
        value = next_line[0].strip()
        row = ROW.fullmatch(value)
        clock = row['clock'] if row else value
        if not re.fullmatch(CLOCK, clock):
            continue
        # Route-backed facts carry stronger source qualifiers; avoid duplicates.
        if any(f['start'] <= line.start() < f['end'] for f in output):
            continue
        output.append(dict(role=sides[0]+'_time', value=clock, start=line.start(), end=next_line.end(),
                           relation=None, reason='vertical_role_clock'))
    return output


def supported(fact, content):
    """All proof anchors must survive selection, in order, within the same record."""
    compact = lambda value: ' '.join(value.split())
    relation = (fact.get('normalized_value') or {}).get('relation')
    if not relation:
        return compact(fact['source_text']) in compact(content)
    from rag_evidence import _records
    records = _records(content) or [(0,len(content))]
    for a,b in records:
        remaining = compact(content[a:b])
        for anchor in relation['anchors']:
            if anchor not in fact['source_text']:
                break
            at = remaining.find(compact(anchor))
            if at < 0:
                break
            remaining = remaining[at+len(compact(anchor)):]
        else:
            return True
    return False
