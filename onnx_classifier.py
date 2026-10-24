"""Lazy CPU inference of the existing exported classifier, one call at a time.

No training, downloads, Torch or Transformers imports occur in this runtime.
The artifact must be provisioned and parity checked before deployment.
"""
import json
import os
from pathlib import Path
from threading import Lock
from types import SimpleNamespace
import numpy as np
from classifier_contract import validate_classifier_config, inference_token_limit

_lock = Lock()
_runtime = None


def classify(text):
    global _runtime
    with _lock:
        if _runtime is None:
            import onnxruntime as ort
            from tokenizers import Tokenizer
            root = Path(os.getenv('CLASSIFIER_ONNX_PATH', 'local_models/render/classifier'))
            if not root.is_absolute():
                root = Path(__file__).resolve().parent / root
            config = SimpleNamespace(**json.loads((root / 'config.json').read_text(encoding='utf-8')))
            mapping = validate_classifier_config(config)
            tokenizer = Tokenizer.from_file(str(root / 'tokenizer.json'))
            tokenizer.enable_truncation(max_length=inference_token_limit(config, tokenizer))
            options = ort.SessionOptions()
            options.intra_op_num_threads = options.inter_op_num_threads = 1
            options.enable_cpu_mem_arena = options.enable_mem_pattern = False
            options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
            session = ort.InferenceSession(str(root / 'model.onnx'), options,
                                           providers=['CPUExecutionProvider'])
            _runtime = tokenizer, mapping, session
        tokenizer, mapping, session = _runtime
        ids = tokenizer.encode(text).ids
        if not 1 <= len(ids) <= 512:
            raise ValueError('Invalid classifier input size')
        scores = session.run(None, {'input_ids': np.asarray([ids], dtype=np.int64),
                                   'attention_mask': np.ones((1, len(ids)), dtype=np.int64)})[0][0]
        if scores.shape != (len(mapping),) or not np.isfinite(scores).all():
            raise ValueError('Invalid classifier output')
        index = int(scores.argmax())
        confidence = float(1 / (1 + np.exp(-np.clip(scores[index], -80, 80))))
        return [{'category': mapping[index], 'confidence': confidence}]
