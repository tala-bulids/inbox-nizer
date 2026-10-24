"""Explicit verified single-file download; never imported by the API."""

import argparse
import hashlib
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path
from local_llm import DEFAULT_MODEL_PATH

REPO = 'unsloth/Qwen3-0.6B-GGUF'
REVISION = '50968a4468ef4233ed78cd7c3de230dd1d61a56b'
FILENAME = 'Qwen3-0.6B-Q4_K_M.gguf'
SIZE = 396705472
SHA256 = 'ac2d97712095a558e31573f62f466a3f9d93990898b0ec79d7c974c1780d524a'
MARGIN = 512 * 1024**2
URL = f'https://huggingface.co/{REPO}/resolve/{REVISION}/{FILENAME}'


def _verify(path):
    if not path.is_file() or path.stat().st_size != SIZE:
        return False
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            digest.update(block)
    return digest.hexdigest() == SHA256


def download(destination):
    destination = Path(destination).expanduser().resolve()
    if destination.exists():
        if not _verify(destination):
            raise SystemExit('Existing destination does not match the selected GGUF. Choose another --destination; no file was overwritten.')
        print('Verified existing GGUF:', destination)
        return destination
    probe = destination.parent
    while not probe.exists():
        probe = probe.parent
    required = SIZE + MARGIN
    if shutil.disk_usage(probe).free < required:
        raise SystemExit(f'Insufficient disk space: need {required / 1024**2:.0f} MiB including a 512 MiB margin.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=FILENAME + '.', suffix='.part', delete=False) as output:
            temporary = Path(output.name)
            with urllib.request.urlopen(URL, timeout=60) as response:
                received = 0
                while block := response.read(1024**2):
                    received += len(block)
                    if received > SIZE:
                        raise ValueError('Download exceeds expected size')
                    output.write(block)
        if not _verify(temporary):
            raise ValueError('GGUF size or SHA-256 verification failed')
        # Publish without overwriting a concurrent download or an existing file.
        os.link(temporary, destination)
    except Exception:
        raise SystemExit('GGUF download failed or verification failed. Check network/disk and retry; existing files were preserved.') from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print('Verified GGUF:', destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=f'Download only {REPO}/{FILENAME} ({SIZE} bytes).')
    parser.add_argument('--destination', default=os.getenv('RAG_MODEL_PATH', str(DEFAULT_MODEL_PATH)))
    args = parser.parse_args()
    download(args.destination)


if __name__ == '__main__':
    main()
