import json
import os
from pathlib import Path
import numpy as np
import pytest


@pytest.mark.skipif(not os.getenv('CLASSIFIER_ONNX_TEST_ROOT'), reason='Explicit existing-artifact parity check')
def test_existing_classifier_parity_and_session_reuse(monkeypatch):
    import onnx_classifier
    root = Path(os.environ['CLASSIFIER_ONNX_TEST_ROOT'])
    monkeypatch.setenv('CLASSIFIER_ONNX_PATH', str(root))
    monkeypatch.setattr(onnx_classifier, '_runtime', None)
    texts = json.loads((root / 'probe_texts.json').read_text(encoding='utf-8'))
    reference = np.load(root / 'reference.npy')
    mapping = json.loads((root / 'config.json').read_text(encoding='utf-8'))['id2label']
    session = None
    for text, logits in zip(texts, reference):
        actual = onnx_classifier.classify(text)[0]
        index = int(logits.argmax())
        assert actual['category'] == mapping[str(index)]
        assert abs(actual['confidence'] - float(1 / (1 + np.exp(-logits[index])))) <= .0001
        if session is not None:
            assert onnx_classifier._runtime[2] is session
        session = onnx_classifier._runtime[2]
    assert onnx_classifier.classify('report ' * 1000)[0]['category'] in mapping.values()
