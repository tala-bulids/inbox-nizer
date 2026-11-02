"""Evidence/provisioning guards; these tests are not real Linux model benchmarks."""
import json
import subprocess
import sys

import pytest

from showcase import ci_qualification as ci

SHA = 'a' * 40


def write_smoke(temp, **overrides):
    data = {'status': 'PASS', 'scope': 'constraints_and_dependencies_only',
            'real_model_inference': False, 'memory_limit_bytes': 512 * 2**20,
            'swap_limit_bytes': 0, 'cpu_fraction': .1}
    data.update(overrides)
    (temp / 'inbox-nizer-constraint-smoke.json').write_text(json.dumps(data))


def test_missing_private_descriptor_is_blocked_without_network_or_inference(tmp_path, monkeypatch):
    write_smoke(tmp_path)
    monkeypatch.setattr(ci, 'acquire', lambda *_: pytest.fail('No approved source'))
    monkeypatch.setattr(ci, 'run', lambda *_: pytest.fail('No real models'))
    report = ci.collect(tmp_path, SHA)
    assert report['status'] == 'BLOCKED'
    assert report['real_model_inference'] is False
    assert report['deployment_authorized'] is False


@pytest.mark.parametrize('overrides', [{'cpu_fraction': 1}, {'memory_limit_bytes': 1024 * 2**20},
                                     {'real_model_inference': True}, {'swap_limit_bytes': 1}])
def test_wrong_or_mislabelled_constraints_cannot_pass(tmp_path, overrides):
    write_smoke(tmp_path, **overrides)
    assert ci.collect(tmp_path, SHA)['status'] == 'FAIL'


def test_private_acquisition_errors_are_not_published(tmp_path, monkeypatch):
    write_smoke(tmp_path)
    sources = {key: {'url': 'https://private.invalid/sensitive-signed-marker'} for key in ci.identities()}
    (tmp_path / 'inbox-nizer-approved-artifacts.json').write_text(json.dumps(sources))
    def denied(*_): raise RuntimeError('sensitive-signed-marker: authorization denied')
    monkeypatch.setattr(ci, 'acquire', denied)
    report = ci.collect(tmp_path, SHA)
    assert report['status'] == 'FAIL'
    assert 'sensitive-signed-marker' not in json.dumps(report)
    assert 'private.invalid' not in json.dumps(report)


def test_local_path_sources_not_accepted_as_ci_provider(tmp_path, monkeypatch):
    write_smoke(tmp_path)
    sources = {key: {'path': '/private-marker'} for key in ci.identities()}
    (tmp_path / 'inbox-nizer-approved-artifacts.json').write_text(json.dumps(sources))
    monkeypatch.setattr(ci, 'acquire', lambda *_: pytest.fail('Provider not approved'))
    report = ci.collect(tmp_path, SHA)
    assert report['status'] == 'FAIL' and 'private-marker' not in json.dumps(report)


def test_only_allowlisted_numeric_metrics_can_be_published():
    report = ci.numeric_metrics({'http_start_seconds': 2.0, 'error': 'secret-marker',
                                 'warm_ask': {'n': 5, 'p95_ms': 20.0, 'url': 'secret-marker'},
                                 'first_classifier_ms': float('nan'),
                                 'evaluation': {'document_vectors': ['private-marker']},
                                 'concurrent_four': {'statuses': [200, 429, 429, 429]}})
    assert report['http_start_seconds'] == 2.0
    assert report['warm_ask'] == {'n': 5, 'p95_ms': 20.0}
    assert 'first_classifier_ms' not in report
    assert 'marker' not in json.dumps(report)


def test_blocked_gate_exits_nonzero_and_smoke_success_never_passes(tmp_path):
    output = tmp_path / 'public.json'
    for status, real, expected in [('BLOCKED', False, 1), ('PASS', False, 1), ('PASS', True, 0)]:
        output.write_text(json.dumps({'status': status, 'real_model_inference': real}))
        result = subprocess.run([sys.executable, '-m', 'showcase.ci_qualification', '--enforce', str(output)],
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == expected
