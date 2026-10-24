"""Finite offline diagnostic, NOT representative release quality or host acceptance.

Run in a fresh process with CLASSIFIER_ONNX_PATH pointing to a frozen export.
Never trains, opens a mailbox/holdout, or prints input text or predictions.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import time

from quality.classification_cases import FINAL, examples

# Freeze before running. The 512 MiB host needs headroom for API/DB/Gmail work.
LIMITS = {'cold_seconds': 10, 'warm_p95_seconds': 1,
          'long_p95_seconds': 2, 'classifier_process_peak_mib': 384}


def p95(values):
    return sorted(values)[math.ceil(.95 * len(values)) - 1]


def qualify():
    root = Path(os.environ['CLASSIFIER_ONNX_PATH']).resolve()
    hashes = {}
    for name in ('model.onnx', 'weights.bin', 'config.json', 'tokenizer.json'):
        with (root / name).open('rb') as source:
            hashes[name] = hashlib.file_digest(source, 'sha256').hexdigest()
    from onnx_classifier import classify
    start = time.perf_counter()
    classify('Synthetic receipt: your payment was received.')
    cold = time.perf_counter() - start
    timings, long_timings = [], []
    by_language = {language: {'n': 0, 'correct': 0} for language in ('en', 'ar')}
    for case in examples(FINAL):
        start = time.perf_counter()
        result = classify(case['text'])[0]
        timings.append(time.perf_counter() - start)
        counts = by_language[case['language']]
        counts['n'] += 1
        counts['correct'] += result['category'] in case['labels']
    for _ in range(10):
        start = time.perf_counter()
        classify('Synthetic report ' * 1000)
        long_timings.append(time.perf_counter() - start)
    peak = None
    if sys.platform == 'linux':
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    for counts in by_language.values():
        counts['accuracy'] = counts['correct'] / counts['n']
    measured = {'cold_seconds': cold, 'warm_p95_seconds': p95(timings),
                'warm_median_seconds': statistics.median(timings),
                'long_p95_seconds': p95(long_timings), 'classifier_process_peak_mib': peak}
    return {'platform': platform.system(), 'python': platform.python_version(),
            'artifact_sha256': hashes, 'limits': LIMITS, 'measurements': measured,
            'performance_gate': all(measured[k] is not None and measured[k] <= v for k, v in LIMITS.items()),
            'by_language': by_language, 'examples': 20, 'long_calls': 10,
            'representative_quality': False, 'release_approved': False,
            'limitations': 'Public synthetic examples; no human-reviewed holdout, Google network, DB, concurrent inbox workload or full server memory. Linux results qualify only the machine that ran this command.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Do not overwrite evidence')
    result = qualify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as target:
        json.dump(result, target, indent=2)
    print(json.dumps(result))
