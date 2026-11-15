import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError
from unittest.mock import patch

import pytest

from showcase import github_artifacts as ga

TOKEN = 'test-token-not-a-secret'
DATA = b'qualification fixture'
SPEC = {'candidate.joblib': {'bytes': len(DATA), 'sha256': hashlib.sha256(DATA).hexdigest()}}


class Response(io.BytesIO):
    status = 200


class Opener:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.requests = []

    def open(self, request, *, timeout):
        self.requests.append(request)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def metadata(**changes):
    row = dict(name='candidate.joblib', id=123, size=len(DATA), state='uploaded')
    row.update(changes)
    return Response(json.dumps(dict(tag_name=ga.TAG, draft=False, assets=[row])).encode())


def redirect(location):
    return HTTPError(ga.API + '/assets/123', 302, 'Found', {'Location': location}, io.BytesIO())


def test_direct_download(tmp_path):
    opener = Opener(metadata(), Response(DATA))
    with patch.object(ga, 'identities', return_value=SPEC):
        assert ga.acquire_github(tmp_path, TOKEN, opener=opener) == {'candidate.joblib': SPEC['candidate.joblib']['sha256']}
    assert (tmp_path / 'candidate.joblib').read_bytes() == DATA
    assert all(r.get_header('Authorization') == 'Bearer ' + TOKEN for r in opener.requests)


def test_redirect_drops_authorization(tmp_path):
    opener = Opener(metadata(), redirect('https://release-assets.githubusercontent.com/asset?signature=example'), Response(DATA))
    with patch.object(ga, 'identities', return_value=SPEC):
        ga.acquire_github(tmp_path, TOKEN, opener=opener)
    assert opener.requests[1].get_header('Accept') == 'application/octet-stream'
    assert opener.requests[2].get_header('Authorization') is None
    assert (tmp_path / 'candidate.joblib').read_bytes() == DATA


@pytest.mark.parametrize('location', ['http://release-assets.githubusercontent.com/a', 'https://evil.example/a', 'https://release-assets.githubusercontent.com.evil.example/a', 'https://user@release-assets.githubusercontent.com/a', 'https://release-assets.githubusercontent.com:444/a'])
def test_unsafe_redirect_rejected(tmp_path, location):
    opener = Opener(metadata(), redirect(location))
    with patch.object(ga, 'identities', return_value=SPEC), pytest.raises(ValueError):
        ga.acquire_github(tmp_path, TOKEN, opener=opener)
    assert len(opener.requests) == 2
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('data', [b'x' * len(DATA), DATA + b'x', DATA[:-1]])
def test_hash_and_size_fail_closed(tmp_path, data):
    opener = Opener(metadata(), Response(data))
    with patch.object(ga, 'identities', return_value=SPEC), pytest.raises(ValueError):
        ga.acquire_github(tmp_path, TOKEN, opener=opener)
    assert not list(tmp_path.iterdir())


def test_unexpected_asset_rejected(tmp_path):
    opener = Opener(metadata(name='other.bin'))
    with patch.object(ga, 'identities', return_value=SPEC), pytest.raises(ValueError):
        ga.acquire_github(tmp_path, TOKEN, opener=opener)
    assert len(opener.requests) == 1


def test_no_overwrite(tmp_path):
    path = tmp_path / 'candidate.joblib'
    path.write_bytes(b'wrong')
    opener = Opener(metadata())
    with patch.object(ga, 'identities', return_value=SPEC), pytest.raises(ValueError):
        ga.acquire_github(tmp_path, TOKEN, opener=opener)
    assert path.read_bytes() == b'wrong'


def test_no_follow_handler():
    assert ga.NoFollow().redirect_request(None, None, 302, '', {}, 'https://example.com') is None


@pytest.mark.parametrize('status', [301, 303, 307, 308, 401, 403, 404, 429, 500])
def test_unsupported_asset_status_does_not_follow(tmp_path, status):
    error = HTTPError(ga.API + '/assets/123', status, 'fixture', {}, io.BytesIO())
    opener = Opener(metadata(), error)
    with patch.object(ga, 'identities', return_value=SPEC), pytest.raises(HTTPError):
        ga.acquire_github(tmp_path, TOKEN, opener=opener)
    assert len(opener.requests) == 2 and not list(tmp_path.iterdir())


def test_second_redirect_rejected_without_forwarding_token(tmp_path):
    opener = Opener(metadata(), redirect('https://objects.githubusercontent.com/first'),
                    redirect('https://evil.example/second'))
    with patch.object(ga, 'identities', return_value=SPEC), pytest.raises(HTTPError):
        ga.acquire_github(tmp_path, TOKEN, opener=opener)
    assert len(opener.requests) == 3
    assert opener.requests[2].get_header('Authorization') is None
    assert opener.requests[2].get_header('Accept') is None
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('location', ['', '/relative', 'https://objects.githubusercontent.com/a#fragment',
                                      'https://user:password@objects.githubusercontent.com/a'])
def test_additional_unsafe_redirects(location):
    with pytest.raises(ValueError):
        ga.redirect_request(location)


@pytest.mark.parametrize('change', ['tag', 'draft', 'missing', 'duplicate', 'id', 'state', 'size', 'oversized', 'redirect'])
def test_bad_metadata_stops_before_download(tmp_path, change):
    if change == 'oversized':
        response = Response(b'x' * 1048577)
    elif change == 'redirect':
        response = redirect('https://objects.githubusercontent.com/metadata')
    else:
        payload = json.loads(metadata().getvalue())
        if change == 'tag': payload['tag_name'] = 'other'
        if change == 'draft': payload['draft'] = True
        if change == 'missing': payload['assets'] = []
        if change == 'duplicate': payload['assets'] *= 2
        if change == 'id': payload['assets'][0]['id'] = True
        if change == 'state': payload['assets'][0]['state'] = 'new'
        if change == 'size': payload['assets'][0]['size'] += 1
        response = Response(json.dumps(payload).encode())
    opener = Opener(response)
    with patch.object(ga, 'identities', return_value=SPEC), pytest.raises((ValueError, HTTPError)):
        ga.acquire_github(tmp_path, TOKEN, opener=opener)
    assert len(opener.requests) == 1 and not list(tmp_path.iterdir())


def test_valid_cache_is_rehashed_and_no_download_occurs(tmp_path):
    destination = tmp_path / 'candidate.joblib'
    destination.write_bytes(DATA)
    opener = Opener(metadata())
    with patch.object(ga, 'identities', return_value=SPEC):
        ga.acquire_github(tmp_path, TOKEN, opener=opener)
    assert len(opener.requests) == 1
    destination.write_bytes(b'x' * len(DATA))
    with patch.object(ga, 'identities', return_value=SPEC), pytest.raises(ValueError):
        ga.acquire_github(tmp_path, TOKEN, opener=Opener(metadata()))
    assert destination.read_bytes() == b'x' * len(DATA)


@pytest.mark.parametrize('link', ['directory', 'artifact'])
def test_link_detection_rejects_even_a_hash_matching_cache(tmp_path, monkeypatch, link):
    destination = tmp_path / 'candidate.joblib'
    destination.write_bytes(DATA)
    marked = tmp_path if link == 'directory' else destination
    monkeypatch.setattr(Path, 'is_symlink', lambda self: self == marked)
    with patch.object(ga, 'identities', return_value=SPEC), pytest.raises(ValueError, match='symbolic'):
        ga.acquire_github(tmp_path, TOKEN, opener=Opener(metadata()))
    assert destination.read_bytes() == DATA


def test_interrupted_stream_cleans_temporary_and_never_installs(tmp_path):
    class Broken(Response):
        def read(self, size):
            raise OSError('synthetic interruption')
    opener = Opener(metadata(), Broken(DATA))
    with patch.object(ga, 'identities', return_value=SPEC), pytest.raises(OSError):
        ga.acquire_github(tmp_path, TOKEN, opener=opener)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('token', ['', ' ', 'bad\nheader', 'bad\rheader'])
def test_invalid_token_never_opens_network(tmp_path, token):
    opener = Opener()
    with pytest.raises(ValueError):
        ga.acquire_github(tmp_path, token, opener=opener)
    assert not opener.requests


def test_cli_removes_token_and_sanitizes_exceptions(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(ga.TOKEN_ENV, TOKEN)
    monkeypatch.setattr(sys, 'argv', ['github_artifacts', '--output', str(tmp_path)])
    def fail(output, token):
        assert ga.TOKEN_ENV not in os.environ
        assert token == TOKEN
        raise ValueError(TOKEN + ' https://private.invalid/signed')
    monkeypatch.setattr(ga, 'acquire_github', fail)
    with pytest.raises(SystemExit) as caught:
        ga.main()
    assert TOKEN not in str(caught.value) and 'private.invalid' not in str(caught.value)
    assert caught.value.__suppress_context__
    assert capsys.readouterr().out == ''


def test_real_launcher_boundaries_and_fail_closed_build(tmp_path):
    root = Path(__file__).resolve().parents[2]
    shell = 'C:/Program Files/Git/bin/sh.exe' if sys.platform == 'win32' else '/bin/sh'
    binary = tmp_path / 'bin'
    binary.mkdir()
    calls = tmp_path / 'calls'
    python = '''#!/bin/sh
[ "${github_token+x}" != x ] || exit 90
if [ "$1 $2" = '-m showcase.github_artifacts' ]; then
  [ "${SHOWCASE_GITHUB_TOKEN:-}" = 'test-token-not-a-secret' ] || exit 91
  [ "${FAIL_DOWNLOAD:-}" != yes ] || exit 42
else
  [ "${SHOWCASE_GITHUB_TOKEN+x}" != x ] || exit 92
fi
printf 'python %s\\n' "$*" >> "$CALL_LOG"
'''
    npm = '''#!/bin/sh
[ "${SHOWCASE_GITHUB_TOKEN+x}" != x ] || exit 93
[ "${github_token+x}" != x ] || exit 94
printf 'npm %s\\n' "$*" >> "$CALL_LOG"
'''
    for name, content in [('python', python), ('npm', npm)]:
        file = binary / name
        file.write_text(content, encoding='utf-8', newline='\n')
        file.chmod(0o700)
    env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'],
               SHOWCASE_GITHUB_TOKEN=TOKEN, github_token='inherited-export', CALL_LOG=str(calls))
    env.pop('SHOWCASE_ARTIFACT_DESCRIPTOR', None)
    def launch(script, environment=env, syntax=False):
        return subprocess.run([shell, *(['-n'] if syntax else []), script], cwd=root,
                              env=environment, capture_output=True, text=True, timeout=30)
    build = 'deploy/build-showcase-free.sh'
    start = 'deploy/start-showcase-free.sh'
    for script in [build, start]:
        result = launch(script, syntax=True)
        assert result.returncode == 0, result.stderr
    result = launch(build)
    assert result.returncode == 0, result.stderr
    assert calls.read_text().splitlines() == [
        'python -m showcase.github_artifacts --output local_models/showcase-free',
        'python -m pip install -r deploy/requirements-showcase-free.txt',
        'python -m pip check', 'npm --prefix frontend ci', 'npm --prefix frontend run build:showcase']
    calls.write_text('')
    result = launch(build, dict(env, FAIL_DOWNLOAD='yes'))
    assert result.returncode == 42 and calls.read_text() == ''
    result = launch(build, dict(env, SHOWCASE_ARTIFACT_DESCRIPTOR='fixture.json'))
    assert result.returncode == 1 and calls.read_text() == ''
    no_token = dict(env)
    no_token.pop('SHOWCASE_GITHUB_TOKEN')
    result = launch(build, no_token)
    assert result.returncode == 1 and calls.read_text() == ''
    result = launch(build, dict(no_token, SHOWCASE_ARTIFACT_DESCRIPTOR='fixture.json'))
    assert result.returncode == 0, result.stderr
    assert calls.read_text().splitlines()[0] == 'python -m showcase.acquire_artifacts --descriptor fixture.json --output local_models/showcase-free'
    calls.write_text('')
    # Runtime only strips the approved SHOWCASE token; the build's local shell
    # variable is not part of Render's configuration.
    runtime_env = dict(env, PORT='12345')
    runtime_env.pop('github_token')
    result = launch(start, runtime_env)
    assert result.returncode == 0, result.stderr
    assert calls.read_text().strip() == ('python -m uvicorn showcase.free_app:application --factory '
        '--host 0.0.0.0 --port 12345 --workers 1 --no-access-log --timeout-keep-alive 5')
