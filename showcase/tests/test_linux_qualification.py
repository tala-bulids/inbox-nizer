"""Runner/receipt regressions only; mocks do not establish real model capacity."""
import json
from types import SimpleNamespace

import pytest

from showcase import qualify_linux as runner
from showcase.resource_verdict import assess


def receipt():
    return {'platform': 'linux', 'status': 'completed', 'real_inference': True,
            'snapshots': {'final': {'cgroup_v2': {
                'cpu.max': '10000 100000', 'memory.max': str(512 * 2**20),
                'memory.swap.max': '0', 'memory.peak': str(390 * 2**20),
                'memory.events': 'oom 0\noom_kill 0'}}}}


@pytest.mark.parametrize('key,value', [
    ('memory.events', ''), ('memory.events', 'oom 0'),
    ('memory.events', 'oom 1\noom_kill 0'),
    ('memory.max', '0'), ('memory.max', 'max'),
    ('memory.peak', '-1'), ('memory.peak', '0'),
    ('memory.swap.max', '1'), ('cpu.max', '100000 100000'),
    ('cpu.max', '-10000 -100000'),
])
def test_incomplete_or_invalid_cgroup_evidence_fails_closed(key, value):
    report = receipt()
    report['snapshots']['final']['cgroup_v2'][key] = value
    assert assess(report)['technical_gate'] == 'FAIL'


def test_external_observer_peak_includes_later_memory_and_failure():
    report = receipt()
    report['observer_final'] = {'cgroup_v2': dict(report['snapshots']['final']['cgroup_v2'])}
    report['observer_final']['cgroup_v2']['memory.peak'] = str(410 * 2**20)
    assert assess(report)['technical_gate'] == 'FAIL'
    report['status'] = 'failed'
    report['observer_final']['cgroup_v2']['memory.peak'] = str(390 * 2**20)
    assert assess(report)['technical_gate'] == 'FAIL'


@pytest.mark.parametrize('state,timed_out', [
    ({'ExitCode': 137, 'OOMKilled': True}, False),
    ({'ExitCode': 0}, False),
    ({'ExitCode': 0, 'OOMKilled': False}, True),
])
def test_container_failure_cannot_pass_even_with_completed_child_receipt(state, timed_out):
    assert runner.verdict(receipt(), state, timed_out)['technical_gate'] == 'FAIL'


def test_local_container_pass_never_authorizes_render():
    result = runner.verdict(receipt(), {'ExitCode': 0, 'OOMKilled': False}, False)
    assert result['technical_gate'] == 'PASS'
    assert result['render_accepted'] is False


def test_only_verified_model_files_are_mounted_with_strict_limits(tmp_path):
    args = runner.create_command('owned-test', 'local-image', tmp_path / 'private', tmp_path / 'output')
    assert {'--network=none', '--memory=512m', '--memory-swap=512m', '--cpus=0.1', '--pids-limit=128'} <= set(args)
    mounts = [args[i+1] for i, arg in enumerate(args) if arg == '--mount']
    assert len(mounts) == 4
    assert all(mount.endswith(',readonly') for mount in mounts[:3])
    assert all('/models/' + name in ' '.join(mounts) for name in runner.identities())
    assert '--publish' not in args and '--env-file' not in args and '--privileged' not in args


def test_bad_bundle_rejected_before_docker_or_native_loading(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.shutil, 'which', lambda _: pytest.fail('Docker must not run'))
    with pytest.raises(ValueError, match='identity'):
        runner.preflight(tmp_path)


def test_missing_linux_engine_is_blocked_not_emulated(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'valid', lambda *_: True)
    monkeypatch.setattr(runner.shutil, 'which', lambda _: None)
    with pytest.raises(RuntimeError, match='Docker unavailable'):
        runner.preflight(tmp_path)


def test_whole_container_oom_retains_external_receipt_and_preserves_models(tmp_path, monkeypatch):
    models = tmp_path / 'models'; models.mkdir()
    marker = models / 'private-marker'; marker.write_bytes(b'keep')
    output = tmp_path / 'evidence'
    monkeypatch.setattr(runner, 'preflight', lambda _: {'capacity_test_executed': False})
    calls = []
    def fake_command(args, **kwargs):
        calls.append(args)
        stdout = ''
        if args[:2] == ['git', 'rev-parse']: stdout = 'a' * 40
        if args[:2] == ['docker', 'inspect']:
            stdout = json.dumps({'Status': 'exited', 'ExitCode': 137, 'OOMKilled': True})
        return SimpleNamespace(stdout=stdout)
    monkeypatch.setattr(runner, 'command', fake_command)
    monkeypatch.setattr(runner.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=137))
    result = runner.run(models, output)
    assert result['verdict']['technical_gate'] == 'FAIL'
    assert result['container_state']['OOMKilled'] is True
    assert json.loads((output / 'qualification.json').read_text()) == result
    assert marker.read_bytes() == b'keep'
    assert not (output / 'linux-free.json').exists()
    removal = next(c for c in calls if c[:2] == ['docker', 'rm'])
    creation = next(c for c in calls if c[:2] == ['docker', 'create'])
    assert removal == ['docker', 'rm', creation[creation.index('--name')+1]]
    assert not any('push' in c or 'prune' in c for c in calls)
