"""Explicit INT8 deployment candidate. No downloads, training or heavy fallback."""
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from embedding_service import EmbeddingInputError
from showcase.onnx_probe_encoder import ProbeEncoder

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ID = 'e5-int8-fp32-corpus-v1'


def manifest():
    return json.loads((ROOT/'showcase/free-manifest.json').read_text(encoding='utf-8'))


def verify(path, expected):
    path = Path(path)
    if path.stat().st_size != expected['bytes']:
        raise ValueError('Artifact size mismatch')
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected['sha256']:
            raise ValueError('Artifact identity mismatch')
    return path


def load_index():
    from showcase.engine import collection
    from showcase.intelligence import chunks, index_version
    spec = manifest()['index']
    path = verify(ROOT/spec['path'], spec)
    index = json.loads(path.read_text(encoding='utf-8'))
    passages = chunks(collection())
    version = index_version(collection())
    if index['collection_version'] != version or index['chunk_ids'] != [c['chunk_id'] for c in passages]:
        raise ValueError('Prepared index provenance mismatch')
    vectors = np.asarray(index['vectors'], dtype=np.float32)
    if vectors.shape != (len(passages), 384) or not np.isfinite(vectors).all():
        raise ValueError('Invalid corpus vectors')
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5):
        raise ValueError('Corpus vectors must be normalized')
    return passages, vectors.tolist(), version


class FreeEncoder(ProbeEncoder):
    def __init__(self, directory):
        # Verify all native/serialized assets before constructing a session.
        for name, identity in manifest()['embedding_files'].items():
            verify(Path(directory)/name, identity)
        super().__init__(directory, 'model_int8.onnx')

    def query(self, text):
        text = text.strip()
        if not text or len(self.tokenizer.encode('query: '+text)) > 512:
            raise EmbeddingInputError('Query exceeds the reviewed token budget')
        result = self.encode(['query: '+text])[0]
        norm = np.linalg.norm(result)
        if not np.isfinite(norm) or norm <= 0:
            raise ValueError('Invalid query vector')
        return (result/norm).tolist()


def components():
    from showcase.engine import Engine
    from showcase.portfolio import SelectedClassifier
    directory = os.environ.get('SHOWCASE_EMBEDDING_DIR')
    if not directory:
        raise ValueError('Provision the reviewed embedding directory')
    encoder = FreeEncoder(directory)
    engine = Engine(query_encoder=encoder.query, prepared_index=load_index())
    return engine, SelectedClassifier(), encoder


def runtime_info():
    return {'id': RUNTIME_ID, 'query_encoder': 'multilingual-e5-small INT8 ONNX',
            'document_encoder': 'original FP32 E5, precomputed authored corpus',
            'classification': 'phase2-A', 'answering': 'extractive',
            'production_approved': False}
