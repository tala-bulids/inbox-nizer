"""Build artifacts are verified before any runtime files are installed."""
import hashlib
import io
import sys
import zipfile
from urllib.request import Request

import pytest
from deploy import install_classifier as installer


def bundle(extra=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        for name in installer.FILES:
            archive.writestr(name, b'synthetic artifact')
        if extra:
            archive.writestr(extra, b'unexpected')
    return output.getvalue()


def configure(monkeypatch, tmp_path, payload, digest=None):
    monkeypatch.setenv('CLASSIFIER_BUNDLE_URL', 'https://artifacts.example.invalid/model.zip')
    monkeypatch.setenv('CLASSIFIER_BUNDLE_SHA256', digest or hashlib.sha256(payload).hexdigest())
    target = tmp_path / 'classifier'
    monkeypatch.setattr(sys, 'argv', ['install_classifier.py', '--target', str(target)])
    class Opener:
        def open(self, url, timeout):
            assert timeout == 120
            return io.BytesIO(payload)
    monkeypatch.setattr(installer, 'build_opener', lambda *_: Opener())
    return target


def test_verified_bundle_installs_exact_runtime_files(monkeypatch, tmp_path):
    target = configure(monkeypatch, tmp_path, bundle())
    installer.main()
    assert {p.name for p in target.iterdir()} == installer.FILES
    assert all(p.read_bytes() == b'synthetic artifact' for p in target.iterdir())


def test_checksum_failure_does_not_touch_existing_artifact(monkeypatch, tmp_path):
    target = configure(monkeypatch, tmp_path, bundle(), '0' * 64)
    target.mkdir()
    (target / 'model.onnx').write_bytes(b'previous')
    with pytest.raises(ValueError, match='checksum mismatch'):
        installer.main()
    assert (target / 'model.onnx').read_bytes() == b'previous'


@pytest.mark.parametrize('extra', ['../outside', 'unapproved.bin'])
def test_unexpected_archive_paths_rejected_before_extraction(monkeypatch, tmp_path, extra):
    target = configure(monkeypatch, tmp_path, bundle(extra))
    with pytest.raises(ValueError, match='Unexpected artifact contents'):
        installer.main()
    assert not target.exists()


@pytest.mark.parametrize('url', ['http://example.invalid/x', 'https://user:secret@example.invalid/x'])
def test_insecure_redirect_rejected_before_following(url):
    with pytest.raises(ValueError, match='HTTPS artifact required'):
        installer.SecureRedirect().redirect_request(
            Request('https://example.invalid/original'), None, 302, '', {}, url)
