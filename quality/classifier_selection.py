"""Resource-bounded, local classifier selection using development data only.

The sparse candidate is an experiment, not a runtime replacement. No mailbox
data, previous final examples, or test-partition predictions are opened here.
"""
import argparse
import hashlib
import json
import platform
import re
import time
from pathlib import Path

from classifier_contract import LABELS


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-file', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--minimum-available-gib', type=float, default=.75)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output directory; existing evidence and models are immutable.')
    import psutil
    available = psutil.virtual_memory().available / 2**30
    if available < args.minimum_available_gib:
        parser.error(f'Insufficient available RAM: {available:.2f} GiB; wait for at least {args.minimum_available_gib} GiB.')
    cached = sorted((Path.home()/'.cache/huggingface/datasets/imnim___multiclass-email-classification').rglob('*train.arrow'))
    source = args.dataset_file or (cached[0] if cached else None)
    if source is None:
        parser.error('Provide a local Arrow --dataset-file. This script never downloads data.')
    import joblib
    import numpy as np
    import pyarrow as pa
    import sklearn
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.pipeline import FeatureUnion
    from threadpoolctl import threadpool_limits
    from .classification_cases import DEV, examples
    from .deeper_cases import TRAIN, rows as authored
    from .dataset import audit_split
    from .metrics import metrics

    started = time.perf_counter()
    with pa.memory_map(str(source), 'r') as memory:
        public = pa.ipc.open_stream(memory).read_all().to_pylist()
    supplement = examples(DEV) + authored(TRAIN)
    public_rows, public_audit = audit_split(public, seed=args.seed)
    rows, audit = audit_split(public + supplement, seed=args.seed)
    supplement_ids = {hashlib.sha256(re.sub(r'\s+', ' ', r['text']).strip().casefold().encode()).hexdigest() for r in supplement}
    for row in rows:
        row['label_source'] = 'authored_synthetic_development' if row['id'] in supplement_ids else 'public_annotations'
        row['language'] = 'ar' if re.search('[\u0600-\u06ff]', row['text']) else 'en'
    parts = {name: [row for row in rows if row['split'] == name] for name in ('train', 'validation', 'test')}
    # Test texts are never encoded or evaluated. Their hashes remain in the
    # reproducible split manifest so accidental reuse can be detected later.
    features = FeatureUnion([
        ('word', TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=8000, sublinear_tf=True, dtype=np.float32)),
        ('char', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2, max_features=16000, sublinear_tf=True, dtype=np.float32)),
    ])
    train_x = features.fit_transform([r['text'] for r in parts['train']])
    validation_x = features.transform([r['text'] for r in parts['validation']])
    train_y = np.array([[label in r['labels'] for label in LABELS] for r in parts['train']])
    if np.any(train_y.sum(axis=0) == 0):
        raise ValueError('Every category needs training coverage.')
    runs, best = [], None
    with threadpool_limits(limits=1):
        for weight in (None, 'balanced'):
            for regularization in (.3, 3., 30.):
                candidate = OneVsRestClassifier(LogisticRegression(C=regularization, class_weight=weight,
                    solver='liblinear', max_iter=1000, random_state=args.seed), n_jobs=1)
                begin = time.perf_counter()
                candidate.fit(train_x, train_y)
                scores = candidate.predict_proba(validation_x)
                measured = metrics(scores, [r['labels'] for r in parts['validation']])
                config = {'C': regularization, 'class_weight': weight, 'seed': args.seed}
                runs.append({'configuration': config, 'validation': measured, 'seconds': time.perf_counter()-begin})
                key = (measured['top1_macro_f1'], measured['top1_accuracy'], -measured['finance_false_positive_rate'])
                if best is None or key > best[0]:
                    best = (key, candidate, scores, config)
    _, selected, scores, configuration = best
    languages = {}
    for language in ('ar', 'en'):
        indexes = [i for i, r in enumerate(parts['validation']) if r['language'] == language]
        if indexes:
            languages[language] = metrics(scores[indexes], [parts['validation'][i]['labels'] for i in indexes])
    hard_negatives = [{'id': row['id'], 'reference': row['labels'], 'predicted': LABELS[int(np.argmax(score))],
                      'confidence': float(max(score)), 'label_source': row['label_source']}
                     for row, score in zip(parts['validation'], scores) if LABELS[int(np.argmax(score))] not in row['labels']]
    args.output.mkdir(parents=True)
    artifact = args.output/'candidate.joblib'
    joblib.dump({'features': features, 'classifier': selected, 'labels': LABELS, 'configuration': configuration}, artifact)
    manifest = [{key: value for key, value in row.items() if key != 'text'} for row in rows]
    (args.output/'split-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    artifact_hash = digest(artifact)
    report = {'selected_configuration': configuration, 'artifact_sha256': artifact_hash,
        'selection_rule': 'Validation top1 macro F1, then accuracy, then fewer Finance false positives; first candidate breaks ties.',
        'candidate_family': 'Word/character TF-IDF with one-vs-rest logistic regression; local sparse baseline experiment.',
        'source_sha256': digest(source), 'public_data_audit': public_audit, 'combined_data_audit': audit,
        'split_manifest_sha256': digest(args.output/'split-manifest.json'), 'seed': args.seed,
        'runs': runs, 'selected_validation': metrics(scores, [r['labels'] for r in parts['validation']]),
        'validation_by_language': languages, 'hard_negative_review_queue': hard_negatives,
        'environment': {'python': platform.python_version(), 'sklearn': sklearn.__version__, 'numpy': np.__version__},
        'resources': {'available_gib_before': available, 'process_rss_mib_after': psutil.Process().memory_info().rss/2**20,
                      'elapsed_seconds': time.perf_counter()-started, 'threads': 1},
        'public_test_evaluated': False, 'mailbox_holdout_opened': False, 'production_adopted': False,
        'confidence': 'Uncalibrated scores; diagnostics do not establish probabilities of correctness.',
        'limitations': ['Public annotations and authored synthetic examples are not representative human mailbox gold.',
            'Validation is consumed by model selection and cannot be reported as release accuracy.',
            'Arabic synthetic validation coverage is small and cannot establish bilingual parity.',
            'Hard negatives are review suggestions with existing weak reference labels, not newly created human gold.',
            'Earlier public/synthetic test partitions may have been evaluated in historical experiments; no final test is evaluated in this run.']}
    (args.output/'selection-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (args.output/'candidate-descriptor.json').write_text(json.dumps({'artifact_sha256': artifact_hash,
        'holdout_used_for_selection': False, 'selection_report_sha256': digest(args.output/'selection-report.json'),
        'production_adopted': False,
        'note': 'Not a final-evaluation freeze: bind a real review manifest and policy only after candidate selection ends.'}, indent=2), encoding='utf-8')
    print(json.dumps({'selected': configuration, 'validation': {key: report['selected_validation'][key]
        for key in ('n', 'top1_accuracy', 'top1_macro_f1', 'finance_false_positives', 'wrong_confident_rate')},
        'production_adopted': False, 'output': str(args.output)}))


if __name__ == '__main__':
    main()
