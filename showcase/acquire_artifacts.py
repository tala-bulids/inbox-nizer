"""Acquire exact approved artifacts at build time; no runtime downloader or deserializer.

Descriptor is an operator-provided local JSON file mapping artifact names to
{"path": "/approved/source/file"} OR {"url": "https://approved/signed/location"}.
No host, token or URL is inferred. Never print descriptor content or URL errors.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener, Request

ROOT = Path(__file__).resolve().parents[1]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Artifact redirects are not permitted')


def identities():
    spec=json.loads((ROOT/'showcase/free-manifest.json').read_text(encoding='utf-8'))
    return {**spec['embedding_files'], 'candidate.joblib':spec['classifier']}


def valid(path, expected):
    if not path.is_file() or path.stat().st_size != expected['bytes']:
        return False
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()==expected['sha256']


def transfer(source, destination, expected):
    destination=Path(destination)
    if destination.exists():
        if valid(destination,expected):return
        raise ValueError('Existing artifact differs; refusing overwrite')
    if set(source)=={'path'}:
        stream=Path(source['path']).open('rb')
    elif set(source)=={'url'}:
        parsed=urlsplit(source['url'])
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError('A direct approved HTTPS URL is required')
        stream=build_opener(NoRedirect).open(Request(source['url']),timeout=30)
    else:
        raise ValueError('Provide one approved path or HTTPS URL per artifact')
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.incoming-',dir=destination.parent)
    try:
        size=0;sha=hashlib.sha256()
        with stream,os.fdopen(fd,'wb') as output:
            while block:=stream.read(1024*1024):
                size+=len(block)
                if size>expected['bytes']:raise ValueError('Oversized artifact')
                sha.update(block);output.write(block)
        if size!=expected['bytes'] or sha.hexdigest()!=expected['sha256']:
            raise ValueError('Artifact identity mismatch')
        # Exclusive create never replaces an existing file, even if another
        # acquisition process raced us. Destination contains verified bytes only.
        os.chmod(temp,0o600)
        os.link(temp,destination)
    finally:
        Path(temp).unlink(missing_ok=True)


def acquire(descriptor, output):
    sources=json.loads(Path(descriptor).read_text(encoding='utf-8'))
    expected=identities()
    if set(sources)!=set(expected):raise ValueError('Descriptor must name exactly the three approved artifacts')
    for name,spec in expected.items():transfer(sources[name],Path(output)/name,spec)
    return {name:spec['sha256'] for name,spec in expected.items()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--descriptor',required=True,type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'local_models/showcase-free')
    args=parser.parse_args()
    try: result=acquire(args.descriptor,args.output)
    except Exception:
        raise SystemExit('Artifact acquisition failed; check approved locations, access and identities. No source details logged.') from None
    print(json.dumps({'verified_sha256':result}))


if __name__=='__main__':main()
