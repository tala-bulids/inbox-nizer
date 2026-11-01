"""Local Docker qualification only; never deploys, uploads artifacts or reads .env.

Builds a pinned Git archive, mounts only three verified model files read-only,
disables container network/swap, and keeps external OOM/exit evidence. Requires
an already installed, authorized Linux Docker engine. No installer is included.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

from showcase.acquire_artifacts import identities, valid
from showcase.resource_verdict import assess

ROOT = Path(__file__).resolve().parents[1]


def command(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def preflight(models):
    # No deserialization, network download or publication.
    for name, identity in identities().items():
        if not valid(models / name, identity):
            raise ValueError('Required local model bundle failed identity verification')
    if not shutil.which('docker'):
        raise RuntimeError('Docker unavailable; an authorized Linux engine is required')
    result = command(['docker', 'info', '--format', '{{.OSType}}'], capture_output=True, text=True)
    if result.stdout.strip() != 'linux':
        raise RuntimeError('Docker must use a Linux engine')
    return {'bundle_sha256': {name: v['sha256'] for name, v in identities().items()},
            'engine': 'linux', 'capacity_test_executed': False}


def create_command(name, image, models, output):
    args = ['docker', 'create', '--name', name, '--network=none',
            '--memory=512m', '--memory-swap=512m', '--cpus=0.1', '--pids-limit=128']
    for filename in identities():
        args += ['--mount', f'type=bind,src={models / filename},dst=/models/{filename},readonly']
    return args + ['--mount', f'type=bind,src={output},dst=/evidence', image]


def verdict(receipt, state, timed_out):
    result = assess(receipt)
    if timed_out:
        result['reasons'].append('Qualification exceeded the 600-second overall deadline')
    if state.get('OOMKilled') is not False:
        result['reasons'].append('External container OOM status is failed or unavailable')
    if state.get('ExitCode') != 0:
        result['reasons'].append('Container did not exit successfully')
    result['technical_gate'] = 'FAIL' if result['reasons'] else 'PASS'
    return result


def run(models, output):
    evidence = preflight(models)
    sha = command(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    if command(['git', 'status', '--porcelain', '--untracked-files=no'], capture_output=True, text=True).stdout.strip():
        raise RuntimeError('Commit reviewed tracked changes before building the pinned Git archive')
    output.mkdir(parents=True, exist_ok=False)
    name = 'inbox-nizer-qualification-' + uuid.uuid4().hex[:12]
    image = 'inbox-nizer-free-qualification:' + sha[:12]
    evidence.update(source_sha=sha, container_created=False, capacity_test_executed=False)
    state = {}; timed_out = False
    try:
        with tempfile.TemporaryFile() as archive, (output / 'build.log').open('wb') as log:
            command(['git', 'archive', '--format=tar', sha], stdout=archive)
            archive.seek(0)
            command(['docker', 'build', '-f', 'deploy/free-qualification.Dockerfile', '-t', image, '-'],
                    stdin=archive, stdout=log, stderr=subprocess.STDOUT, timeout=900)
        evidence['image_id'] = command(['docker', 'image', 'inspect', image, '--format', '{{.Id}}'],
                                       capture_output=True, text=True).stdout.strip()
        command(create_command(name, image, models, output), capture_output=True)
        evidence['container_created'] = True
        with (output / 'probe.log').open('wb') as log:
            evidence['capacity_test_executed'] = True
            try:
                subprocess.run(['docker', 'start', '--attach', name], cwd=ROOT,
                               stdout=log, stderr=subprocess.STDOUT, timeout=600, check=False)
            except subprocess.TimeoutExpired:
                timed_out = True
                command(['docker', 'stop', '--time=5', name], capture_output=True, timeout=30)
    except Exception as error:
        # Never publish host paths, command arguments or source URLs in a receipt.
        evidence['runner_error_type'] = type(error).__name__
    finally:
        if evidence['container_created']:
            try:
                state = json.loads(command(['docker', 'inspect', '--format', '{{json .State}}', name],
                                           capture_output=True, text=True).stdout)
                if state.get('Running'):
                    command(['docker', 'stop', '--time=5', name], capture_output=True, timeout=30)
                    state = json.loads(command(['docker', 'inspect', '--format', '{{json .State}}', name],
                                               capture_output=True, text=True).stdout)
                # Remove only this invocation's stopped container. Keep models,
                # logs, receipts and the local image; never prune or remove volumes.
                command(['docker', 'rm', name], capture_output=True)
            except Exception as error:
                evidence['cleanup_error_type'] = type(error).__name__
                evidence['container_for_manual_inspection'] = name
        evidence['container_state'] = {k: state.get(k) for k in ('Status', 'ExitCode', 'OOMKilled', 'StartedAt', 'FinishedAt')}
        receipt = {}
        path = output / 'linux-free.json'
        if path.is_file():
            try:
                receipt = json.loads(path.read_text(encoding='utf-8'))
            except (ValueError, OSError):
                evidence['receipt_error'] = 'Unreadable or incomplete inference receipt'
        evidence['verdict'] = verdict(receipt, state, timed_out)
        if 'runner_error_type' in evidence or 'cleanup_error_type' in evidence:
            evidence['verdict']['technical_gate'] = 'FAIL'
            evidence['verdict']['reasons'].append('Runner or cleanup failed; inspect local evidence')
        (output / 'qualification.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', action='store_true', help='Verify prerequisites only; never counts as capacity evidence')
    args = parser.parse_args()
    if not args.check and args.output is None:
        parser.error('--output must name a new private evidence directory')
    models = args.models.resolve()
    output = args.output.resolve() if args.output else None
    if any(',' in str(path) for path in (models, output) if path):
        parser.error('Docker bind paths must not contain commas')
    try:
        result = preflight(models) if args.check else run(models, output)
    except Exception as error:
        print(json.dumps({'status': 'BLOCKED', 'error_type': type(error).__name__,
                          'action': 'Verify exact local model bundle, installed Linux Docker engine and new output path',
                          'capacity_test_executed': False}))
        raise SystemExit(1) from None
    print(json.dumps(result, indent=2))
    if not args.check and result['verdict']['technical_gate'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
