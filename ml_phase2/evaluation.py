"""Metrics preserve multilabel truth; no invented primary gold class."""
from collections import Counter
import importlib.metadata
import platform
import time

import numpy as np
import psutil
from classifier_contract import LABELS
from quality.metrics import metrics


def evaluate(scores, rows):
    scores = np.asarray(scores)
    result = metrics(scores, [r['labels'] for r in rows])
    per_class = result['per_class']
    support = sum(v['support'] for v in per_class.values())
    result['top1_weighted_f1'] = sum(v['f1']*v['support'] for v in per_class.values()) / support
    result['metric_definition'] = 'Top-one accuracy accepts any annotated label; per-class F1 compares one prediction against all reference positives. Confusion rows fractional for multilabel gold.'
    result['by_language'] = {}
    for lang in ('en', 'ar', 'mixed', 'und'):
        indices = [i for i, r in enumerate(rows) if r['language'] == lang]
        result['by_language'][lang] = metrics(scores[indices], [rows[i]['labels'] for i in indices]) if indices else {'n': 0, 'status': 'unavailable'}
    errors = Counter()
    for row, score in zip(rows, scores):
        prediction = LABELS[int(np.argmax(score))]
        if prediction not in row['labels']:
            errors[' + '.join(row['labels']) + ' -> ' + prediction] += 1
    result['error_patterns'] = dict(errors.most_common(15))
    result['test_evaluated'] = False
    return result


def benchmark(predict, rows):
    # Warm serial single-message inference, including preprocessing. No test inputs.
    predict([rows[0]['text']])
    timings = []
    for row in rows[:min(30, len(rows))]:
        start = time.perf_counter()
        predict([row['text']])
        timings.append((time.perf_counter()-start)*1000)
    memory = psutil.Process().memory_info()
    return {'n': len(timings), 'p50_ms': float(np.percentile(timings, 50)),
        'p95_ms': float(np.percentile(timings, 95)), 'rss_mib_after': memory.rss/2**20,
        'process_peak_wset_mib': getattr(memory, 'peak_wset', 0)/2**20 or None,
        'scope': 'Warm single-message serial validation inference; process memory includes training/load; Windows peak working set when available. Not Render capacity.'}


def environment():
    return {'python': platform.python_version(), 'platform': platform.system(),
            'packages': {p: importlib.metadata.version(p) for p in ('torch','transformers','scikit-learn','numpy','sentence-transformers')}}
