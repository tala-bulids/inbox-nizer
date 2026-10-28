"""Fetch only the reviewed pinned public source; never execute publisher code."""
import argparse
from pathlib import Path
import urllib.request
from .data import CONFIG, digest, read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = read(CONFIG)['source']
    args.output.mkdir(parents=True, exist_ok=False)
    for name, key in [('README.md','card_sha256'), ('dataset_creation.py','generation_code_sha256'), ('email_dataset.json','data_sha256')]:
        url = f"https://huggingface.co/datasets/{source['repository']}/resolve/{source['revision']}/{name}"
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = response.read(2_000_001)
        if len(payload) > 2_000_000:
            raise ValueError('Unexpected source size')
        path = args.output/name
        with path.open('xb') as stream:
            stream.write(payload)
        if digest(path) != source[key]:
            raise ValueError('Source hash mismatch; do not train')


if __name__ == '__main__':
    main()
