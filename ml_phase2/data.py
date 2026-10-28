"""Pinned public-data preparation; raw examples and split manifests remain local."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from quality.dataset import canonical, content, prepare_rows, partition_rows

CONFIG = Path(__file__).with_name('config.json')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def normalize(subject, body):
    text = unicodedata.normalize('NFC', content(subject, body))
    text = re.sub(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b', ' EMAIL ', text)
    text = re.sub(r'https?://\S+|www\.\S+', ' URL ', text)
    # Conservative contact/identifier removal, not a claim of full anonymization.
    text = re.sub(r'(?<!\w)\+?\d[\d ().-]{6,}\d(?!\w)', ' NUMBER ', text)
    return re.sub(r'\s+', ' ', text).strip()


def language(text):
    ar = len(re.findall(r'[\u0621-\u064a]', text))
    en = len(re.findall(r'[A-Za-z]', text))
    if ar and en and min(ar, en) / (ar + en) > .1:
        return 'mixed'
    return 'ar' if ar > en else 'en' if en else 'und'


def prepare(raw, source_id, seed=42):
    provenance = defaultdict(list)
    normalized = []
    pii = Counter()
    for index, row in enumerate(raw):
        original = content(row.get('subject'), row.get('body'))
        text = normalize(row.get('subject'), row.get('body'))
        pii['rows_changed_by_contact_redaction'] += text != re.sub(r'\s+', ' ', unicodedata.normalize('NFC', original)).strip()
        provenance[canonical(text)].append({'source': source_id, 'row_index': index,
            'raw_sha256': hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()})
        normalized.append({'text': text, 'labels': row['labels'], 'sender_domains': row.get('sender_domains', [])})
    rows, audit = prepare_rows(normalized)
    rows, split = partition_rows(rows, seed)
    for row in rows:
        row['provenance'] = provenance[canonical(row['text'])]
        row['language'] = language(row['text'])
    audit.update(split)
    audit.update(pii_screen=dict(pii), language_counts=dict(Counter(r['language'] for r in rows)),
        class_counts=dict(Counter(l for r in rows for l in r['labels'])),
        language_method='Script heuristic, not human language annotation',
        sender_metadata_available=any(r.get('sender_domains') for r in rows),
        preprocessing='NFC + existing HTML/body cleaner; whitespace; contact/URL/long-number redaction',
        dedup='Exact normalized duplicates collapsed; conflicting exact labels quarantined; transitive near-template cosine >=0.9 and provided sender-domain groups',
        limitations=['Names and semantic personal information may remain. No raw text is approved for redistribution.',
                    'Source has no sender/thread metadata; template grouping cannot eliminate all leakage.',
                    'Public data was used in historical experiments; reserved test is not a new release holdout.'])
    return rows, audit


def load_development(directory):
    directory = Path(directory)
    manifest = read(directory / 'manifest.json')
    # Never open test.json. Verify only train and validation inputs here.
    parts = {}
    for split in ('train', 'validation'):
        path = directory / (split + '.json')
        if digest(path) != manifest['files'][path.name]:
            raise ValueError('Prepared data changed after split freeze')
        parts[split] = read(path)
    if {r['group'] for r in parts['train']} & {r['group'] for r in parts['validation']}:
        raise ValueError('Cross-split group leakage')
    return parts, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = read(CONFIG)
    expected = {'email_dataset.json': 'data_sha256', 'README.md': 'card_sha256', 'dataset_creation.py': 'generation_code_sha256'}
    for filename, key in expected.items():
        if digest(args.source_dir / filename) != config['source'][key]:
            raise ValueError('Unreviewed source revision; review rights and update the source manifest first')
    rows, audit = prepare(read(args.source_dir / 'email_dataset.json'),
                          config['source']['repository'] + '@' + config['source']['revision'], config['seed'])
    args.output.mkdir(parents=True, exist_ok=False)
    for split in ('train', 'validation', 'test'):
        write(args.output / (split + '.json'), [r for r in rows if r['split'] == split])
    write(args.output / 'dataset-card.json', {**audit, 'source': config['source'], 'seed': config['seed']})
    write(args.output / 'manifest.json', {'config_sha256': digest(CONFIG), 'files': {
        name: digest(args.output / name) for name in ('train.json', 'validation.json', 'test.json', 'dataset-card.json')},
        'test_predictions_executed': False, 'test_status': 'reserved, historically exposed corpus; not release gold'})
    print(json.dumps({'prepared': len(rows), 'splits': {s: sum(r['split']==s for r in rows) for s in ('train','validation','test')}}))


if __name__ == '__main__':
    main()
