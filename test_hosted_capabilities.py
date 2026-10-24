"""Hosted routes must reject before retrieval, inference, or heavy imports."""
import builtins
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.mark.parametrize('method,path,body', [
    ('get', '/search/semantic?q=hello', None),
    ('post', '/ask', {'question': 'hello'}),
])
def test_render_rejects_before_models(monkeypatch, method, path, body):
    monkeypatch.setenv('INBOX_RUNTIME_PROFILE', 'render-free')
    search = Mock(side_effect=AssertionError('retrieval called'))
    ask = Mock(side_effect=AssertionError('answer called'))
    monkeypatch.setattr('routes.semantic_search', search)
    monkeypatch.setattr('rag_api.answer_email_question', ask)
    original = builtins.__import__
    imported = []
    def guard(name, *args, **kwargs):
        if name.split('.')[0] in {'torch', 'transformers', 'sentence_transformers', 'llama_cpp'}:
            imported.append(name)
            raise AssertionError(name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guard)
    with TestClient(app) as client:
        response = client.request(method, path, json=body)
        assert response.status_code == 403
        assert response.json()['detail']['code'] == 'runtime_disabled'
        assert client.get('/gmail/accounts').json()['runtime_profile'] == 'render-free'
    assert not imported
    search.assert_not_called()
    ask.assert_not_called()


@pytest.mark.parametrize('profile', [None, 'full'])
def test_full_search_preserved(monkeypatch, profile):
    if profile is None:
        monkeypatch.delenv('INBOX_RUNTIME_PROFILE', raising=False)
    else:
        monkeypatch.setenv('INBOX_RUNTIME_PROFILE', profile)
    search = Mock(return_value=[])
    monkeypatch.setattr('routes.semantic_search', search)
    with TestClient(app) as client:
        assert client.get('/search/semantic?q=hello').status_code == 200
        assert client.get('/gmail/accounts').json()['runtime_profile'] == 'full'
    search.assert_called_once()
