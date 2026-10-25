from unittest.mock import Mock

import numpy as np
import pytest

import embedding_service as service


def test_prefixes_normalization_and_single_lazy_load(fake_embedding_encoder, monkeypatch):
    loader = Mock(return_value=fake_embedding_encoder)
    monkeypatch.setattr(service, '_load_encoder', loader)
    query = service.embed_query('  متى سفرتي لجدة؟ ')
    passages = service.embed_passages(['رحلة إلى جدة', 'Invoice INV-12'])
    loader.assert_called_once()
    assert fake_embedding_encoder.calls[0][0] == ['query: متى سفرتي لجدة؟']
    assert fake_embedding_encoder.calls[1][0] == ['passage: رحلة إلى جدة', 'passage: Invoice INV-12']
    assert fake_embedding_encoder.calls[0][1]['normalize_embeddings'] is True
    for vector in [query, *passages]:
        assert len(vector) == 384 and all(isinstance(value, float) for value in vector)
        assert np.linalg.norm(vector) == pytest.approx(1)


@pytest.mark.parametrize('value', ['', '  ', None, 12])
def test_empty_or_invalid_query_does_not_load(value, fake_embedding_encoder):
    with pytest.raises(ValueError):
        service.embed_query(value)
    assert not fake_embedding_encoder.calls


def test_passage_validation_and_empty_batch(fake_embedding_encoder):
    assert service.embed_passages([]) == []
    for values in [['valid', ' '], 'not a list']:
        with pytest.raises(ValueError):
            service.embed_passages(values)
    assert not fake_embedding_encoder.calls


@pytest.mark.parametrize('output', [np.ones((1, 383)), np.ones((2, 384)), np.zeros((1, 384)),
                                    np.full((1, 384), np.nan), np.full((1, 384), np.inf)])
def test_invalid_encoder_output_is_rejected(output, fake_embedding_encoder, monkeypatch):
    monkeypatch.setattr(fake_embedding_encoder, 'encode', lambda *a, **k: output)
    with pytest.raises(RuntimeError):
        service.embed_query('query')


def test_normalizes_even_if_backend_does_not(fake_embedding_encoder, monkeypatch):
    monkeypatch.setattr(fake_embedding_encoder, 'encode', lambda *a, **k: np.ones((1, 384)))
    assert np.linalg.norm(service.embed_query('query')) == pytest.approx(1)


def test_overlong_input_rejected_instead_of_truncated(fake_embedding_encoder):
    with pytest.raises(ValueError, match='512 tokens'):
        service.embed_query('word ' * 512)
    assert not fake_embedding_encoder.calls
