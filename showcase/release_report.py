"""Reduce real release probes to publishable aggregate evidence; never ship vectors/weights."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def parity(reference, candidate):
    """Report changes, not a new approval threshold or quality gate."""
    left, right = reference['evaluation'], candidate['evaluation']
    if [c['id'] for c in left['cases']] != [c['id'] for c in right['cases']]:
        raise ValueError('Cannot compare different question suites')
    if left['collection_version'] != right['collection_version']:
        raise ValueError('Cannot compare different collection versions')
    result = {'query_tokens_identical': left['query_token_ids'] == right['query_token_ids']}
    for key in ('query_vectors', 'document_vectors'):
        a, b = np.asarray(left[key]), np.asarray(right[key])
        if a.shape != b.shape or a.ndim != 2 or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError('Invalid paired vectors')
        denominator = np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1)
        if (denominator == 0).any():
            raise ValueError('Zero vector')
        cosine = (a*b).sum(axis=1) / denominator
        result[key] = {'n': len(a), 'cosine_min': float(cosine.min()),
                       'cosine_mean': float(cosine.mean()), 'max_absolute_difference': float(abs(a-b).max())}
    paired = list(zip(left['cases'], right['cases']))
    result['changed_top10_order'] = [a['id'] for a,b in paired if a['ranked_top10'] != b['ranked_top10']]
    result['changed_citation_sets'] = [a['id'] for a,b in paired if set(a['cited']) != set(b['cited'])]
    result['changed_status'] = [a['id'] for a,b in paired if a['status'] != b['status']]
    result['retrieval_metric_deltas'] = {k: right['qa']['retrieval'][k]-v for k,v in left['qa']['retrieval'].items()}
    return result


def summarize(paths):
    runs = []
    raw = []
    for path in paths:
        data = Path(path).read_bytes()
        report = json.loads(data)
        if report['status'] != 'completed' or not report['real_inference'] or report['mocked_inference']:
            raise ValueError('Only completed actual-inference runs can be compared')
        raw.append(report)
        reduced = {k:v for k,v in report.items() if k != 'evaluation'}
        reduced['receipt_sha256'] = hashlib.sha256(data).hexdigest()
        reduced['evaluation'] = {k:report['evaluation'][k] for k in ('qa','by_language','tasks','collection_version')}
        reduced['evaluation']['cases'] = [{k:c[k] for k in ('id','language','status','status_correct','cited','evidence_set_correct','ranked_top10')}
                                           for c in report['evaluation']['cases']]
        runs.append(reduced)
    return {'runs': runs, 'parity_against_first': {r['encoder']: parity(raw[0], r) for r in raw[1:]},
            'target_host_verified': False, 'production_approved': False,
            'note': 'Repeated frozen development suite, not a fresh independent holdout. No quality gate was changed.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipts', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = summarize(args.receipts)
    with args.output.open('x', encoding='utf-8') as output:
        output.write(json.dumps(result, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
