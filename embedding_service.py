"""Lazy, local E5 embeddings. Importing this module never loads a model."""
import os
from threading import Lock

import numpy as np

MODEL_NAME = 'intfloat/multilingual-e5-small'
DIMENSIONS = 384
MAX_TOKENS = 512
_encoder = None
_load_lock = Lock()
_encode_lock = Lock()


class EmbeddingInputError(ValueError):
    """Invalid caller input, safe to report as a validation error."""


def _load_encoder():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME, device=os.getenv('EMBEDDING_DEVICE', 'cpu'))
    model.max_seq_length = MAX_TOKENS
    return model


def _get_encoder():
    global _encoder
    if _encoder is None:
        with _load_lock:
            if _encoder is None:
                _encoder = _load_encoder()
    return _encoder


def get_tokenizer():
    return _get_encoder().tokenizer


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise EmbeddingInputError('Embedding text must be a non-empty string')
    return value.strip()


def _embed(texts, prefix):
    inputs = [prefix + _text(value) for value in texts]
    if not inputs:
        return []
    encoder = _get_encoder()
    for value in inputs:
        if len(encoder.tokenizer.encode(value, add_special_tokens=True)) > MAX_TOKENS:
            raise EmbeddingInputError('Embedding input exceeds 512 tokens; split it into chunks')
    with _encode_lock:
        values = np.asarray(encoder.encode(inputs, normalize_embeddings=True,
                                          convert_to_numpy=True, show_progress_bar=False,
                                          batch_size=32), dtype=np.float32)
    if values.shape != (len(inputs), DIMENSIONS) or not np.isfinite(values).all():
        raise RuntimeError('Encoder returned invalid embedding dimensions or values')
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or (norms <= 0).any():
        raise RuntimeError('Encoder returned a zero or invalid vector')
    return (values / norms).tolist()


def embed_query(text: str) -> list[float]:
    return _embed([text], 'query: ')[0]


def embed_passages(texts: list[str]) -> list[list[float]]:
    if not isinstance(texts, list):
        raise EmbeddingInputError('Passages must be a list of strings')
    return _embed(texts, 'passage: ')
