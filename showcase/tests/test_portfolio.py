"""Portfolio contract/security tests. UI mocks are not quality evidence."""
import builtins
import json
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from showcase.api import InferenceBudget, create_api
from showcase.portfolio import SelectedClassifier, evidence, ROOT


def test_evidence_matches_frozen_outputs_and_does_not_claim_missing_metrics():
    value=evidence()
    source=json.loads((ROOT/'docs/phase2/evidence/experiment-comparison.json').read_text())
    assert value['selected']==source['selected_research_candidate']=='A'
    for displayed, saved in zip(value['models'], source['runs']):
        assert displayed['run']==saved['run']
        assert displayed['history']==saved['training_history']
        assert all(saved['metrics'][k]==v for k,v in displayed['metrics'].items())
    assert not any(value[k] for k in ('training_curves_available','test_evaluated','arabic_classifier_evaluated','production_approved'))
    assert value['historical']['development']['top1_accuracy']==.32


def test_tampered_model_rejected_before_deserialization(monkeypatch,tmp_path):
    artifact=tmp_path/'model.joblib'; artifact.write_bytes(b'unsafe serialized model')
    monkeypatch.setenv('SHOWCASE_CLASSIFIER_PATH',str(artifact))
    original=builtins.__import__
    def guard(name,*args,**kwargs):
        assert name!='joblib', 'Unverified artifact must not reach deserialization'
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guard)
    with pytest.raises(ValueError,match='identity mismatch'):
        SelectedClassifier().predict('subject','text')


def test_global_budget_expires_without_storing_input_or_identifiers():
    now=[10.0]; budget=InferenceBudget(limit=2,window=60,clock=lambda:now[0])
    class Predictor:
        def predict(self,subject,body): return {'safe':True}
    with TestClient(create_api(predictor=Predictor(),budget=budget)) as client:
        for _ in range(2): assert client.post('/showcase/predict',json={'body':'private-marker'}).status_code==200
        limited=client.post('/showcase/predict',json={'body':'private-marker'})
        assert limited.status_code==429 and limited.headers['retry-after']
        assert 'private-marker' not in limited.text
        assert list(budget.requests)==[10.,10.]
        now[0]=71
        assert client.post('/showcase/predict',json={'body':'text'}).status_code==200


def test_prediction_failures_and_limits_are_sanitized_and_recoverable():
    class Predictor:
        def predict(self,*args): raise RuntimeError('private-marker')
    with TestClient(create_api(predictor=Predictor())) as client:
        for _ in range(2):
            r=client.post('/showcase/predict',json={'body':'private-marker'})
            assert r.status_code==503 and 'private-marker' not in r.text
            assert r.headers['cache-control']=='no-store'
        for body in ({'body':'x'*6001},{'body':'x','subject':'x'*301},{'body':'x','secret':'private-marker'}):
            r=client.post('/showcase/predict',json=body)
            assert r.status_code==422 and 'private-marker' not in r.text
        assert client.post('/showcase/predict',content=b'x'*24001).status_code==413


def test_new_read_routes_never_import_models_database_or_oauth():
    code='''
import builtins
original=builtins.__import__
def guard(name,globals=None,locals=None,fromlist=(),level=0):
    assert level or name.split('.')[0] not in {'torch','transformers','sentence_transformers','llama_cpp','onnxruntime','joblib','database','main','gmail_sync','google_login'}, name
    return original(name,globals,locals,fromlist,level)
builtins.__import__=guard
from fastapi.testclient import TestClient
from showcase.api import create_api
with TestClient(create_api()) as c:
    assert c.get('/showcase/portfolio').status_code==200
    reproduction=c.get('/showcase/reproduction')
    assert reproduction.status_code==200 and 'python -m ml_phase2.run' in reproduction.text
    assert reproduction.headers['content-type'].startswith('text/plain')
    tasks=c.get('/showcase/tasks').json()['tasks']
    assert tasks and all(t['evidence']['text'] in t['evidence']['body'] for t in tasks)
'''
    subprocess.run([sys.executable,'-c',code],check=True,timeout=30)


def test_real_selected_artifact_inference_has_no_heavy_ai_imports():
    if not (ROOT/'results/phase2-A/candidate.joblib').is_file():
        pytest.skip('Provision the recorded local selected artifact for real integration')
    code='''
import builtins
original=builtins.__import__
def guard(name,globals=None,locals=None,fromlist=(),level=0):
    assert level or name.split('.')[0] not in {'torch','transformers','sentence_transformers','llama_cpp','onnxruntime','database','gmail_sync'}, name
    return original(name,globals,locals,fromlist,level)
builtins.__import__=guard
from showcase.portfolio import SelectedClassifier
from fastapi.testclient import TestClient
from showcase.api import create_api
model=SelectedClassifier()
with TestClient(create_api(predictor=model)) as client:
    first=client.post('/showcase/predict',json={'subject':'Job application','body':'Thank you for applying. We would like to invite you to an interview.'})
    assert first.status_code==200, first.text
    result=first.json()
    assert result['model_version']=='phase2-A' and result['processing_ms']>0
    assert result['cold_load_included'] is True
    assert 0<=result['predictions'][0]['confidence']<=1
    second=client.post('/showcase/predict',json={'subject':'Job application','body':'Thank you for applying. We would like to invite you to an interview.'}).json()
    assert second['predictions']==result['predictions'] and second['cold_load_included'] is False
'''
    subprocess.run([sys.executable,'-c',code],check=True,timeout=60)
