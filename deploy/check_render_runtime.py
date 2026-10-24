"""Build-only offline artifact smoke; never opens a mailbox or trains a model."""
import importlib.util
import sys

HEAVY = ('torch', 'transformers', 'sentence_transformers', 'llama_cpp')


def check():
    if any(importlib.util.find_spec(name) is not None for name in HEAVY):
        raise RuntimeError('Hosted environment contains full-runtime dependencies')
    from onnx_classifier import classify
    result = classify('Synthetic receipt: your payment was received.')
    assert len(result) == 1 and 0 <= result[0]['confidence'] <= 1
    assert not any(name in sys.modules for name in HEAVY)


if __name__ == '__main__':
    try:
        check()
    except Exception:
        raise SystemExit('Hosted runtime check failed; verify dependencies and approved artifact.') from None
    print('Offline hosted classifier smoke passed; not a quality approval.')
