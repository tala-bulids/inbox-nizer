import builtins
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from showcase.api import create_api
from showcase.release_app import application


@pytest.mark.parametrize('name', ['DATABASE_URL','GOOGLE_CLIENT_SECRET','GMAIL_TOKEN','PGPASSWORD','OAUTH_CONFIG'])
def test_private_configuration_rejected_before_any_model_import(monkeypatch, name):
    monkeypatch.setenv(name, 'private-marker')
    original = builtins.__import__
    def guard(module, *args, **kwargs):
        assert module not in ('showcase.engine','showcase.portfolio','torch','onnxruntime')
        return original(module, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guard)
    with pytest.raises(RuntimeError) as error:
        application()
    assert 'private-marker' not in str(error.value)


def test_hosted_historical_endpoint_rejected_without_model_or_budget_use():
    class Engine:
        def analyze(self,*args): raise AssertionError('Must not load the historical model')
    class Budget:
        def admit(self): raise AssertionError('Disabled route must not consume inference')
    with TestClient(create_api(Engine(),budget=Budget(),allow_historical=False)) as client:
        response=client.post('/showcase/analyze',json={'body':'short fictional mail'})
        assert response.status_code == 404
        assert response.json()['detail']['code'] == 'historical_model_not_served'


def test_local_historical_path_remains_available():
    class Engine:
        def analyze(self,*args): return {'historical':True}
    with TestClient(create_api(Engine())) as client:
        assert client.post('/showcase/analyze',json={'body':'text'}).json()=={'historical':True}


@pytest.mark.parametrize('revision', [None, 'pinned-revision'])
def test_revision_pin_is_optional_and_local_full_default_is_preserved(monkeypatch, revision):
    import embedding_service
    loader=Mock(return_value=SimpleNamespace())
    monkeypatch.setitem(sys.modules,'sentence_transformers',SimpleNamespace(SentenceTransformer=loader))
    monkeypatch.delenv('EMBEDDING_REVISION',raising=False)
    if revision:
        monkeypatch.setenv('EMBEDDING_REVISION',revision)
    embedding_service._load_encoder()
    assert loader.call_args.kwargs['local_files_only'] is True
    if revision:
        assert loader.call_args.kwargs['revision']==revision
    else:
        assert 'revision' not in loader.call_args.kwargs
