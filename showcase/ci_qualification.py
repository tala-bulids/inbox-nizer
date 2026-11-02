"""Secret-free CI orchestration and allowlisted public evidence.

No provider or credentials are invented. A missing private descriptor is BLOCKED.
Dependency/constraint smoke evidence is never called real-model qualification.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import sys

from showcase.acquire_artifacts import acquire, identities
from showcase.qualify_linux import run


def smoke():
    import onnxruntime
    import sklearn
    names = ('memory.max', 'memory.swap.max', 'memory.peak', 'memory.events', 'cpu.max', 'cpu.stat')
    values = {name: (Path('/sys/fs/cgroup') / name).read_text().strip() for name in names}
    quota, period = map(int, values['cpu.max'].split())
    events = dict(line.split() for line in values['memory.events'].splitlines())
    assert sys.platform == 'linux'
    assert int(values['memory.max']) == 512 * 2**20
    assert int(values['memory.swap.max']) == 0
    assert quota > 0 and period > 0 and abs(quota / period - .1) < .000001
    assert int(events['oom']) == int(events['oom_kill']) == 0
    assert not any(x in sys.modules for x in ('torch', 'transformers', 'sentence_transformers', 'database', 'gmail_sync'))
    return {'status': 'PASS', 'scope': 'constraints_and_dependencies_only',
            'real_model_inference': False, 'memory_limit_bytes': int(values['memory.max']),
            'swap_limit_bytes': 0, 'cpu_fraction': quota / period,
            'onnxruntime': onnxruntime.__version__, 'sklearn': sklearn.__version__}


def valid_smoke(data):
    return (data.get('status') == 'PASS' and data.get('scope') == 'constraints_and_dependencies_only'
            and data.get('real_model_inference') is False
            and data.get('memory_limit_bytes') == 512 * 2**20
            and data.get('swap_limit_bytes') == 0 and data.get('cpu_fraction') == .1)


def numeric_metrics(receipt):
    # Never copy raw outputs, URLs, errors, vectors or classifier vocabulary.
    result = {}
    for key in ('http_start_seconds', 'first_ask_ms', 'first_classifier_ms', 'elapsed_seconds'):
        value = receipt.get(key)
        if type(value) in (int, float) and math.isfinite(value): result[key] = value
    for key in ('warm_ask', 'warm_classifier', 'max_classifier', 'tasks', 'evidence', 'frontend'):
        result[key] = {field: value for field, value in receipt.get(key, {}).items()
                       if field in ('n', 'p50_ms', 'p95_ms') and type(value) in (int, float) and math.isfinite(value)}
    cg = receipt.get('observer_final', {}).get('cgroup_v2', {})
    for key in ('memory.peak', 'memory.max', 'memory.swap.max'):
        value = cg.get(key, '')
        if isinstance(value, str) and value.isdecimal(): result[key] = int(value)
    statuses = receipt.get('concurrent_four', {}).get('statuses', [])
    if isinstance(statuses, list) and all(type(v) is int and v in (200, 429) for v in statuses):
        result['concurrent_four_statuses'] = statuses
    return result


def collect(temp, sha):
    if not re.fullmatch(r'[0-9a-f]{40}', sha): raise ValueError('A full source SHA is required')
    report = {'source_sha': sha, 'status': 'FAIL', 'real_model_inference': False,
              'deployment_authorized': False, 'render_accepted': False}
    try:
        data = json.loads((temp / 'inbox-nizer-constraint-smoke.json').read_text())
        if not valid_smoke(data): raise ValueError('Constraint smoke incomplete')
        report['constraint_check'] = {'status': 'PASS', 'memory_limit_bytes': 512 * 2**20,
                                      'swap_limit_bytes': 0, 'cpu_fraction': .1,
                                      'real_model_inference': False}
    except (OSError, ValueError, TypeError, AttributeError):
        report['reason'] = 'Image build or constrained dependency check failed or is unavailable'
        return report
    descriptor = temp / 'inbox-nizer-approved-artifacts.json'
    if not descriptor.is_file():
        report.update(status='BLOCKED', reason='Approved private artifact descriptor unavailable')
        return report
    try:
        # Provider must place this file directly in runner temp, never in Git.
        # Signed HTTPS locations stay in the private file; not environment values.
        if descriptor.is_symlink(): raise ValueError('Descriptor must be a regular private file')
        os.chmod(descriptor, 0o600)
        sources = json.loads(descriptor.read_text(encoding='utf-8'))
        if set(sources) != set(identities()) or any(set(v) != {'url'} for v in sources.values()):
            raise ValueError('CI requires exactly three approved HTTPS locations')
        models = temp / 'inbox-nizer-private-models'
        models.mkdir(mode=0o700, exist_ok=False)
        acquire(descriptor, models)
        output = temp / 'inbox-nizer-private-receipts'
        qualification = run(models, output)
        report['real_model_test_attempted'] = qualification.get('capacity_test_executed') is True
        gate = qualification['verdict']['technical_gate']
        if gate not in ('PASS', 'FAIL'): raise ValueError('Invalid qualification status')
        report['status'] = gate
        if report['status'] != 'PASS':
            report['reason'] = 'Real-model constrained qualification failed; private receipts retained on runner only'
        path = output / 'linux-free.json'
        if path.is_file():
            receipt = json.loads(path.read_text(encoding='utf-8'))
            report['real_model_inference'] = (receipt.get('status') == 'completed'
                                               and receipt.get('real_inference') is True
                                               and not receipt.get('mocked_inference'))
            report['metrics'] = numeric_metrics(receipt)
        if report['status'] == 'PASS' and not report['real_model_inference']:
            report.update(status='FAIL', reason='Completed real inference not established')
    except Exception:
        report.update(status='FAIL', reason='Approved artifact acquisition or qualification failed; no private details logged')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--temp', type=Path)
    parser.add_argument('--sha')
    parser.add_argument('--enforce', type=Path)
    args = parser.parse_args()
    if args.smoke:
        print(json.dumps(smoke()))
        return
    if args.enforce:
        try:
            report = json.loads(args.enforce.read_text())
            passed = report.get('status') == 'PASS' and report.get('real_model_inference') is True
        except (OSError, ValueError): passed = False
        if not passed: raise SystemExit('Real-model Free qualification is BLOCKED or FAILED; deployment is not approved')
        return
    if not args.temp or not args.sha: parser.error('--temp and --sha required')
    report = collect(args.temp.resolve(), args.sha)
    (args.temp / 'inbox-nizer-qualification-public.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a', encoding='utf-8') as summary:
            summary.write(f"## Free qualification: {report['status']}\n\nSource: `{args.sha}`. "
                          f"Real-model inference executed: {report['real_model_inference']}. "
                          "Dependency smoke success is not model capacity evidence. No deployment.\n")


if __name__ == '__main__': main()
