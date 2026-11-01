import builtins
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from showcase.free_runtime import load_index, manifest, verify, ROOT
from showcase.engine import Engine, collection
from showcase.intelligence import index_version
from showcase.acquire_artifacts import transfer, acquire, NoRedirect


def test_committed_index_contains_only_current_authored_corpus_vectors():
    passages,vectors,version=load_index()
    assert len(passages)==len(vectors)==80
    assert version==index_version(collection())
    assert all(p['email_id'] in {e['id'] for e in collection()} for p in passages)


def test_prepared_index_never_falls_back_to_loading_original_encoder(monkeypatch):
    data=load_index()
    def forbidden(*args): raise AssertionError('Heavy fallback')
    monkeypatch.setattr('showcase.engine.embed_passages',forbidden)
    monkeypatch.setattr('showcase.engine.embed_query',forbidden)
    engine=Engine(query_encoder=lambda _: data[1][0],prepared_index=data)
    assert engine.retrieve('fixture query')
    monkeypatch.setattr('showcase.engine.index_version',lambda _: 'changed')
    with pytest.raises(ValueError,match='Prepared index'): engine.retrieve('fixture query')


def test_mismatched_artifact_rejected_before_native_loading(tmp_path,monkeypatch):
    from showcase.free_runtime import FreeEncoder
    (tmp_path/'model_int8.onnx').write_bytes(b'invalid')
    original=builtins.__import__
    def guard(name,*args,**kwargs):
        assert name!='onnxruntime'
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guard)
    with pytest.raises(ValueError,match='size'):FreeEncoder(tmp_path)


def test_free_runtime_requires_explicit_selection_before_loading(monkeypatch):
    from showcase.free_app import application
    for key in list(os.environ):
        if any(x in key for x in ('DATABASE','POSTGRES','PGPASSWORD','GOOGLE','GMAIL','OAUTH')):
            monkeypatch.delenv(key)
    monkeypatch.delenv('SHOWCASE_RUNTIME',raising=False)
    with pytest.raises(RuntimeError,match='Explicit'):application()


def test_runtime_identity_is_disclosed_without_replacing_historical_evidence():
    from showcase.api import create_api
    from showcase.free_runtime import runtime_info
    with TestClient(create_api(runtime=runtime_info(),allow_historical=False)) as client:
        value=client.get('/showcase/portfolio').json()
        assert value['serving_runtime']['id']==manifest()['runtime_id']
        assert value['historical']['development']['top1_accuracy']==.32
        assert value['rag']['qa']['retrieval']['recall@5']==pytest.approx(.7619047619)
        assert client.post('/showcase/analyze',json={'body':'text'}).status_code==404


def identity(data):return {'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}


def test_acquisition_verifies_before_install_and_preserves_existing(tmp_path):
    source=tmp_path/'approved';source.write_bytes(b'approved')
    target=tmp_path/'dest'/'candidate.joblib'
    transfer({'path':str(source)},target,identity(b'approved'))
    transfer({'path':str(source)},target,identity(b'approved'))
    assert target.read_bytes()==b'approved'
    with pytest.raises(ValueError,match='overwrite'):
        transfer({'path':str(source)},target,identity(b'changed'))
    assert target.read_bytes()==b'approved'


@pytest.mark.parametrize('content',[b'bad',b'excessive content'])
def test_bad_or_oversized_artifact_is_not_installed(tmp_path,content):
    source=tmp_path/'source';source.write_bytes(content)
    target=tmp_path/'model'
    with pytest.raises(ValueError):transfer({'path':str(source)},target,identity(b'good'))
    assert not target.exists() and not list(tmp_path.glob('.incoming-*'))


@pytest.mark.parametrize('url',['http://example.invalid/file','https://user:secret@example.invalid/file','file:///private/model','https://example.invalid/file#token'])
def test_unsafe_artifact_urls_rejected_before_network(tmp_path,url):
    with pytest.raises(ValueError,match='HTTPS'):transfer({'url':url},tmp_path/'model',identity(b'data'))


def test_redirects_and_unknown_artifact_names_rejected(tmp_path):
    with pytest.raises(ValueError,match='redirects'):NoRedirect().redirect_request(None,None,None,None,None,None)
    descriptor=tmp_path/'descriptor.json';descriptor.write_text(json.dumps({'extra':{'path':'private'}}))
    with pytest.raises(ValueError,match='exactly'):acquire(descriptor,tmp_path/'output')


def test_cli_errors_do_not_reveal_descriptor_or_location(tmp_path):
    descriptor=tmp_path/'descriptor.json'
    descriptor.write_text(json.dumps({'extra':{'url':'https://example.invalid/private-marker'}}))
    result=subprocess.run([sys.executable,'-m','showcase.acquire_artifacts','--descriptor',str(descriptor),'--output',str(tmp_path/'output')],capture_output=True,text=True,timeout=30)
    assert result.returncode!=0 and 'private-marker' not in result.stdout+result.stderr


def test_free_import_does_not_import_torch_transformers_database_or_google():
    code="""
import builtins
original=builtins.__import__
def guard(name,globals=None,locals=None,fromlist=(),level=0):
    assert level or name.split('.')[0] not in {'torch','transformers','sentence_transformers','database','gmail_sync','google','llama_cpp','huggingface_hub'},name
    return original(name,globals,locals,fromlist,level)
builtins.__import__=guard
from showcase.free_app import application
from showcase.free_runtime import load_index
assert len(load_index()[0])==80
"""
    subprocess.run([sys.executable,'-c',code],check=True,timeout=30)

def test_windows_or_unconstrained_measurement_never_passes_resource_gate():
    from showcase.resource_verdict import assess
    assert assess({'platform':'win32','status':'completed','real_inference':True})['technical_gate']=='FAIL'
    assert assess({'platform':'linux','status':'completed','real_inference':True})['technical_gate']=='FAIL'


def test_container_gate_counts_peak_not_only_process_rss():
    from showcase.resource_verdict import assess
    data={'platform':'linux','status':'completed','real_inference':True,'snapshots':{'final':{'rss_mib':250,'cgroup_v2':{'cpu.max':'10000 100000','memory.max':str(512*2**20),'memory.swap.max':'0','memory.peak':str(450*2**20),'memory.events':'oom 0\noom_kill 0'}}}}
    assert assess(data)['technical_gate']=='FAIL'
    data['snapshots']['final']['cgroup_v2']['memory.peak']=str(390*2**20)
    assert assess(data)['technical_gate']=='PASS'
    assert assess(data)['render_accepted'] is False
