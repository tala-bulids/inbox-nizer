"""Reproducible data audit and leakage-resistant classifier splits."""
import hashlib
import re
from collections import Counter, defaultdict
from email.utils import parseaddr

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import GroupShuffleSplit

from email_utils import clean_email_body
from classifier_contract import LABELS


def content(subject, body):
    return ((subject or '').strip() + ' ' + clean_email_body(body or '')).strip()


def canonical(text):
    return re.sub(r'\s+', ' ', text).strip().casefold()


def prepare_rows(raw):
    """Quarantine conflicting annotations; never turn contradictions into gold."""
    buckets = defaultdict(list)
    count = 0
    for source in raw:
        count += 1
        text = source.get('text') or content(source.get('subject'), source.get('body'))
        labels = sorted(set(source['labels']))
        if not labels or set(labels) - set(LABELS):
            raise ValueError('Every row needs nonempty labels from the category contract.')
        if not canonical(text):
            raise ValueError('Empty classifier text is not a training example.')
        address = parseaddr(source.get('sender') or source.get('from') or '')[1].casefold()
        domains = set(source.get('sender_domains', []))
        if '@' in address:
            domains.add(address.rsplit('@', 1)[1])
        buckets[canonical(text)].append(dict(text=text, labels=labels, sender_domains=domains))
    conflicts = [items for items in buckets.values() if len({tuple(r['labels']) for r in items}) > 1]
    rows = []
    for key, items in sorted(buckets.items()):
        if len({tuple(r['labels']) for r in items}) != 1:
            continue
        rows.append(dict(text=items[0]['text'], labels=items[0]['labels'],
                         id=hashlib.sha256(key.encode()).hexdigest(),
                         sender_domains=sorted(set().union(*(r['sender_domains'] for r in items)))))
    return rows, dict(raw_rows=count, usable_rows=len(rows), exact_duplicate_excess=count-len(buckets),
                      contradictory_exact_groups=len(conflicts), quarantined_rows=sum(map(len, conflicts)))


def partition_rows(rows, seed=42):
    """Connected content/template AND sender-domain groups stay in one split.

    Domain grouping is conservative when metadata exists. A source dominated by
    one domain can be unsplittable; silently leaking it is worse.
    """
    rows = [dict(row) for row in rows]
    if len(rows) < 3:
        raise ValueError('At least three independent groups are needed for train/validation/test.')
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(j)] = find(i)

    templates = [re.sub(r'\b\d+\b|\b[\w.+-]+@[\w.-]+\b', ' ID ', canonical(r['text'])) for r in rows]
    by_template, by_domain = {}, {}
    for i, row in enumerate(rows):
        if templates[i] in by_template:
            union(i, by_template[templates[i]])
        by_template[templates[i]] = i
        for domain in row.get('sender_domains', []):
            if domain in by_domain:
                union(i, by_domain[domain])
            by_domain[domain] = i
    near = []
    try:
        vectors = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2).fit_transform(templates)
    except ValueError as exc:
        if 'vocabulary' not in str(exc) and 'terms remain' not in str(exc):
            raise
    else:
        # Bound working memory rather than materializing an N x N matrix.
        for start in range(0, len(rows), 256):
            similarity = (vectors[start:start+256] @ vectors.T).tocoo()
            for local_i, j, score in zip(similarity.row, similarity.col, similarity.data):
                i = start + int(local_i)
                if i < j and score >= .9:
                    union(i, int(j))
                    near.append((i, int(j)))
    groups = np.array([find(i) for i in range(len(rows))])
    group_count = len(set(groups))
    if group_count < 3:
        raise ValueError('At least three independent groups are needed; sender/template groups cannot be split.')
    holdout_groups = min(group_count-1, max(2, int(np.ceil(group_count * .2))))
    train, hold = next(GroupShuffleSplit(n_splits=1, test_size=holdout_groups, random_state=seed).split(rows, groups=groups))
    a, b = next(GroupShuffleSplit(n_splits=1, test_size=.5, random_state=seed).split(hold, groups=groups[hold]))
    partitions = {'train': train, 'validation': hold[a], 'test': hold[b]}
    assignment = {int(i): part for part, indices in partitions.items() for i in indices}
    for i, row in enumerate(rows):
        row.setdefault('id', hashlib.sha256(canonical(row['text']).encode()).hexdigest())
        group_id = hashlib.sha256(canonical(rows[groups[i]]['text']).encode()).hexdigest()
        row.update(split=assignment[i], group=group_id)
    return rows, dict(near_duplicate_pairs=len(near), groups=group_count,
        near_pairs_different_labels=sum(set(rows[i]['labels']) != set(rows[j]['labels']) for i, j in near),
        sender_domains=len(by_domain), sender_thread_metadata_available=bool(by_domain),
        splits={part: {'rows': len(indices), 'classes': dict(Counter(label for i in indices for label in rows[i]['labels']))}
                for part, indices in partitions.items()})


def audit_split(raw, seed=42):
    rows, report = prepare_rows(raw)
    rows, grouping = partition_rows(rows, seed)
    report.update(grouping)
    report.update(arabic_rows=sum(bool(re.search('[\u0600-\u06ff]', r['text'])) for r in rows),
        placeholder_rows=sum(bool(re.search(r'\[(?:your|company|name)', r['text'], re.I)) for r in rows),
        class_counts=dict(Counter(label for r in rows for label in r['labels'])),
        seed=seed, cluster_cosine_threshold=.9,
        policy='Contradictory exact labels quarantined. Transitive near-template and available sender-domain groups cannot cross splits.')
    return rows, report
