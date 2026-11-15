"""Build-only retrieval from the approved private GitHub release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from showcase.acquire_artifacts import identities, valid

API = 'https://api.github.com/repos/tala-bulids/inbox-nizer-model-artifacts/releases'
TAG = 'showcase-research-v1'
TOKEN_ENV = 'SHOWCASE_GITHUB_TOKEN'
REDIRECT_HOSTS = {'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}


class NoFollow(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def api_request(url, token, accept):
    return Request(url, headers={'Authorization': 'Bearer ' + token,
                                 'Accept': accept, 'X-GitHub-Api-Version': '2022-11-28',
                                 'User-Agent': 'Inbox-nizer-build'})


def release_assets(opener, token, expected):
    with opener.open(api_request(API + '/tags/' + TAG, token, 'application/vnd.github+json'), timeout=30) as response:
        if response.status != 200:
            raise ValueError('Unexpected release status')
        payload = response.read(1048577)
    if len(payload) > 1048576:
        raise ValueError('Oversized release metadata')
    release = json.loads(payload)
    if release['tag_name'] != TAG or release['draft'] is not False:
        raise ValueError('Unexpected release identity')
    ids = {}
    for asset in release['assets']:
        name, asset_id = asset['name'], asset['id']
        if (name not in expected or name in ids or type(asset_id) is not int or asset_id <= 0
                or asset_id in ids.values() or asset['state'] != 'uploaded'
                or asset['size'] != expected[name]['bytes']):
            raise ValueError('Unexpected release asset')
        ids[name] = asset_id
    if set(ids) != set(expected):
        raise ValueError('Missing release asset')
    return ids


def redirect_request(location):
    parsed = urlsplit(location)
    if (parsed.scheme != 'https' or parsed.hostname not in REDIRECT_HOSTS
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443) or parsed.fragment or not parsed.path):
        raise ValueError('Unapproved asset redirect')
    # Never forward Authorization or other API headers to the signed URL.
    return Request(location, headers={'User-Agent': 'Inbox-nizer-build'})


def asset_stream(opener, token, asset_id):
    try:
        response = opener.open(api_request(API + '/assets/' + str(asset_id), token,
                                           'application/octet-stream'), timeout=60)
    except HTTPError as error:
        with error:
            if error.code != 302:
                raise
            request = redirect_request(error.headers.get('Location', ''))
        response = opener.open(request, timeout=60)
    if response.status != 200:
        response.close()
        raise ValueError('Unexpected asset status')
    return response


def save_asset(stream, destination, expected):
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.incoming-', dir=destination.parent)
    try:
        size, digest = 0, hashlib.sha256()
        with os.fdopen(fd, 'wb') as output:
            while block := stream.read(1024 * 1024):
                size += len(block)
                if size > expected['bytes']:
                    raise ValueError('Oversized artifact')
                digest.update(block)
                output.write(block)
        if size != expected['bytes'] or digest.hexdigest() != expected['sha256']:
            raise ValueError('Artifact identity mismatch')
        os.chmod(temporary, 0o600)
        os.link(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def acquire_github(output, token, *, opener=None):
    if not token or not token.strip() or '\n' in token or '\r' in token:
        raise ValueError('Missing build credential')
    output = Path(output)
    if output.is_symlink():
        raise ValueError('Artifact output must not be a symbolic link')
    expected = identities()
    opener = opener if opener is not None else build_opener(NoFollow)
    ids = release_assets(opener, token, expected)
    for name, spec in expected.items():
        destination = output / name
        if destination.is_symlink():
            raise ValueError('Artifact must not be a symbolic link')
        if destination.exists():
            if valid(destination, spec):
                continue
            raise ValueError('Existing artifact differs; refusing overwrite')
        with asset_stream(opener, token, ids[name]) as stream:
            save_asset(stream, destination, spec)
    return {name: spec['sha256'] for name, spec in expected.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = acquire_github(args.output, os.environ.pop(TOKEN_ENV, ''))
    except Exception:
        raise SystemExit('Private artifact acquisition failed; verify access and artifact identities. No source details logged.') from None
    print(json.dumps({'verified_sha256': result}))


if __name__ == '__main__':
    main()
