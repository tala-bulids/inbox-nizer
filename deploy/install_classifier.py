"""Build-time classifier bundle install with HTTPS, fixed contents and SHA-256.

Never downloads on a user request. URLs may be secret and are never logged.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener
import zipfile

FILES = {'model.onnx', 'weights.bin', 'config.json', 'tokenizer.json'}
MAX_BYTES = 400 * 1024 * 1024


def checksum(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def https(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('HTTPS artifact required')


class SecureRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        https(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pack', type=Path)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--target', type=Path, default=Path(os.getenv('CLASSIFIER_ONNX_PATH', 'local_models/render/classifier')))
    args = parser.parse_args()
    if args.pack:
        if not args.archive:
            parser.error('--pack requires an ignored --archive path')
        with zipfile.ZipFile(args.archive, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in sorted(FILES):
                bundle.write(args.pack / name, name)
        print('CLASSIFIER_BUNDLE_SHA256=' + checksum(args.archive))
        return
    url = os.environ.get('CLASSIFIER_BUNDLE_URL', '')
    expected = os.environ.get('CLASSIFIER_BUNDLE_SHA256', '').lower()
    https(url)
    if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
        raise ValueError('Artifact checksum required')
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / 'classifier.zip'
        with build_opener(SecureRedirect()).open(url, timeout=120) as response, archive.open('wb') as output:
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError('Artifact exceeds limit')
                output.write(chunk)
        if checksum(archive) != expected:
            raise ValueError('Artifact checksum mismatch')
        with zipfile.ZipFile(archive) as bundle:
            entries = bundle.infolist()
            if (len(entries) != len(FILES) or {e.filename for e in entries} != FILES
                    or sum(e.file_size for e in entries) > MAX_BYTES):
                raise ValueError('Unexpected artifact contents')
            args.target.mkdir(parents=True, exist_ok=True)
            for name in sorted(FILES):
                with bundle.open(name) as source, (args.target / name).open('wb') as destination:
                    shutil.copyfileobj(source, destination)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('Classifier artifact preparation failed; verify build configuration.') from None
