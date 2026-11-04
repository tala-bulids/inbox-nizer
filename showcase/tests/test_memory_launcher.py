"""Exercise the real shell/exec boundary, not mocked memory or inference."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def shell():
    value = shutil.which('sh')
    if not value and sys.platform == 'win32':
        candidate = Path('C:/Program Files/Git/bin/sh.exe')
        if candidate.is_file():
            value = str(candidate)
    if not value:
        pytest.skip('POSIX shell required; this check also runs on Ubuntu CI')
    return value


def test_allocator_policy_is_inherited_before_child_start_and_arguments_survive():
    keys = ('MALLOC_ARENA_MAX', 'MALLOC_MMAP_THRESHOLD_', 'MALLOC_TRIM_THRESHOLD_')
    code = ('import json,os,sys;print(json.dumps({'
            "'settings':{k:os.environ.get(k) for k in " + repr(keys) + "},"
            "'args':sys.argv[1:]}))")
    result = subprocess.run([shell(), 'deploy/with-showcase-memory.sh', sys.executable,
                             '-c', code, 'two words', 'literal;$value'], cwd=ROOT,
                            env=dict(os.environ, **{k: '999' for k in keys}),
                            capture_output=True, text=True, check=True, timeout=30)
    value = json.loads(result.stdout)
    assert value['settings'] == dict(zip(keys, ('2', '131072', '131072')))
    assert value['args'] == ['two words', 'literal;$value']


def test_launcher_propagates_application_failure():
    result = subprocess.run([shell(), 'deploy/with-showcase-memory.sh', sys.executable,
                             '-c', 'raise SystemExit(17)'], cwd=ROOT, timeout=30)
    assert result.returncode == 17
