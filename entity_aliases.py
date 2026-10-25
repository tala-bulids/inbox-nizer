"""Offline place-name equivalence from the versioned GeoNames city dataset.

Aliases nominate evidence; they never supply airport names or answer values.
Ambiguous aliases are not resolved using population or the mailbox's contents.
"""
from functools import lru_cache
import re
import unicodedata


def normalized(value):
    value = unicodedata.normalize('NFKC', value).casefold()
    value = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', value)
    value = value.translate(str.maketrans('أإآىة', 'ااايه'))
    return ' '.join(w[2:] if w.startswith('ال') and len(w) > 3 else w
                    for w in re.findall(r'[^\W_]+', value))


@lru_cache(maxsize=1)
def _index():
    import geonamescache
    names, records = {}, {}
    for city in geonamescache.GeonamesCache(min_city_population=15000).get_cities().values():
        identifier = city['geonameid']
        aliases = set()
        for raw in [city['name'], *city['alternatenames']]:
            # Airport codes and other shorthand do not prove city equivalence.
            if len(raw) < 3 or (raw.isupper() and len(raw) <= 4):
                continue
            if any(c.isalpha() and not ('LATIN' in unicodedata.name(c, '') or
                                       'ARABIC' in unicodedata.name(c, '')) for c in raw):
                continue
            key = normalized(raw)
            if key and len(key.split()) <= 5:
                names.setdefault(key, set()).add(identifier)
                aliases.add(key)
        records[identifier] = tuple(sorted(aliases))
    return {key: frozenset(ids) for key, ids in names.items()}, records


def identities(value):
    names, _ = _index()
    return names.get(normalized(value), frozenset())


def aliases(value):
    """Bounded query expansion, only for one unambiguous complete name."""
    key = normalized(value)
    names, records = _index()
    ids = names.get(key, ())
    if len(ids) != 1:
        return (key,) if key else ()
    choices = [name for name in records[next(iter(ids))] if names[name] == ids]
    choices.sort(key=lambda name: (not bool(re.search('[\u0600-\u06ff]', name)), len(name), name))
    return tuple(dict.fromkeys([key, *choices[:15]]))


def matches(wanted, actual):
    """Literal matching stays available for places absent from the gazetteer."""
    wanted = normalized(' '.join(wanted) if not isinstance(wanted, str) else wanted)
    actual = normalized(actual)
    if not wanted or not actual:
        return False
    if set(wanted.split()) <= set(actual.split()):
        return True
    expected = identities(wanted)
    if len(expected) != 1:
        return False
    # A location can carry a literal code in parentheses. Match a complete alias
    # span, and reject a second named city rather than merging itinerary legs.
    exact = identities(actual)
    if exact:
        return exact == expected
    actual_words = actual.split()
    found = set()
    start = 0
    while start < len(actual_words):
        for size in range(min(5, len(actual_words) - start), 0, -1):
            ids = identities(' '.join(actual_words[start:start + size]))
            if ids:
                found.update(ids)
                start += size
                break
        else:
            start += 1
    return found == set(expected)


def qualifier_matches(tokens, context):
    remaining = [token for token in tokens if token not in normalized(context).split()]
    if not remaining:
        return True
    # Only an entire remaining place qualifier may be translated. Arbitrary
    # organizations, people and unmatched words are never dropped.
    key = ' '.join(remaining)
    if len(identities(key)) != 1:
        return False
    return any(re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', normalized(context))
               for alias in aliases(key))


def lexical_groups(tokens):
    """Longest complete entity spans; every non-entity token still constrains SQL."""
    groups = []
    index = 0
    while index < len(tokens):
        for size in range(min(5, len(tokens) - index), 0, -1):
            value = ' '.join(tokens[index:index + size])
            if len(identities(value)) == 1:
                groups.append(aliases(value))
                index += size
                break
        else:
            groups.append((tokens[index],))
            index += 1
    return groups
