"""Bounded local release qualification; never launch this diagnostic server publicly.

Fresh process per encoder, actual loopback HTTP, authored input only. No production
DB/Google settings are retained. Does not mutate or publish any model artifacts.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def memory():
    import psutil
    m=psutil.Process().memory_info()
    if sys.platform == 'linux':
        import resource
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    else:
        peak=getattr(m,'peak_wset',m.rss)/2**20
    result={'rss_mib':m.rss/2**20,'process_peak_mib':peak,'peak_wset_mib':peak}
    if sys.platform=='linux':
        result['cgroup_v2']={name:Path('/sys/fs/cgroup',name).read_text().strip()
                            for name in ('memory.current','memory.peak','memory.max','memory.swap.max','memory.events','cpu.max','cpu.stat')
                            if Path('/sys/fs/cgroup',name).is_file()}
    return result


def worker(args):
    for key in list(os.environ):
        if any(word in key for word in ('DATABASE','GOOGLE','OAUTH')):
            os.environ.pop(key)
    import numpy as np
    import embedding_service
    if args.encoder not in ('torch','free-candidate'):
        from showcase.onnx_probe_encoder import ProbeEncoder
        name='model.onnx' if args.encoder=='onnx-fp32' else 'model_int8.onnx'
        embedding_service._load_encoder=lambda:ProbeEncoder(args.artifacts,name)
    from showcase.api import create_api
    from showcase.engine import Engine, collection
    from showcase.portfolio import SelectedClassifier
    from showcase.intelligence import index_version, chunks
    outer=None
    if args.encoder=='free-candidate':
        from showcase.free_app import application
        from starlette.routing import Mount
        outer=application()
        api=next(route.app for route in outer.routes if isinstance(route, Mount) and route.path=='/api')
        engine,predictor,encoder=api.state.engine,api.state.predictor,api.state.encoder
    else:
        engine=Engine();predictor=SelectedClassifier()
        api=create_api(engine,predictor)

    @api.get('/__probe/stats')
    def stats():
        return {**memory(),'index_chunks':len(engine._chunks),
                'index_float32_bytes':np.asarray(engine._vectors,dtype=np.float32).nbytes if engine._vectors else 0,
                'heavy_imports':{name:name in sys.modules for name in ('torch','transformers','sentence_transformers','onnxruntime','sklearn')},
                'database_imported':'database' in sys.modules,'gmail_imported':'gmail_sync' in sys.modules}

    @api.get('/__probe/evaluate')
    def evaluate():
        import re
        from showcase.evaluation.run import retrieval_metrics, aggregate_qa, task_metrics, literal_grounding
        suite=json.loads((ROOT/'showcase/evaluation/heldout-v1.json').read_text(encoding='utf-8'))
        records=[];vectors=[]
        for case in suite['questions']:
            ranked=engine.retrieve(case['question'])
            started=time.perf_counter();answer=engine.ask(case['question'])
            elapsed=(time.perf_counter()-started)*1000
            ids=[int(v) for v in re.findall(r'\[email_id=(\d+)\]',answer['answer'])]
            records.append({**case,'expected_status':case['status'],'status':answer['status'],
                'status_correct':answer['status']==case['status'],
                'retrieval':retrieval_metrics([r['email_id'] for r in ranked],case['evidence']),
                'cited':ids,'citation_count':len(ids),'correct_citations':sum(i in case['evidence'] for i in ids),
                'evidence_set_correct':set(ids)==set(case['evidence']),
                'literal_grounding':literal_grounding(answer['answer'],collection()),'latency_ms':elapsed,
                'ranked_top10':[r['email_id'] for r in ranked[:10]]})
            vectors.append(encoder.query(case['question']) if args.encoder=='free-candidate' else embedding_service.embed_query(case['question']))
        tokenizer=encoder.tokenizer if args.encoder=='free-candidate' else embedding_service.get_tokenizer()
        tokens=[tokenizer.encode('query: '+case['question'],add_special_tokens=True) for case in suite['questions']]
        return {'qa':aggregate_qa(records),'by_language':{lang:aggregate_qa([c for c in records if c['language']==lang]) for lang in ('en','ar')},
                'tasks':task_metrics(suite['task_gold'],collection()),'cases':records,
                'query_vectors':vectors,'query_token_ids':tokens,'document_vectors':engine._vectors,
                'collection_version':index_version(collection()),'memory':memory()}

    @api.get('/__probe/max-tokens')
    def maximum():
        # Exercise the encoder's full reviewed 512-token boundary independently
        # of the smaller public 1000-character question limit.
        encoder=api.state.encoder if args.encoder=='free-candidate' else embedding_service._get_encoder()
        text='query: '+('meeting '*600)
        ids=encoder.tokenizer.encode(text,add_special_tokens=True)[:512]
        start=time.perf_counter()
        if args.encoder=='torch':
            import torch
            model=encoder[0].auto_model
            with torch.inference_mode():
                outputs=model(input_ids=torch.tensor([ids]),attention_mask=torch.ones((1,len(ids)),dtype=torch.int64))
                assert outputs.last_hidden_state.shape[-1]==384
        else:
            result=encoder.session.run(None,{'input_ids':np.asarray([ids],dtype=np.int64),'attention_mask':np.ones((1,len(ids)),dtype=np.int64)})[0]
            assert result.shape==(1,384) and np.isfinite(result).all()
        return {'tokens':len(ids),'latency_ms':(time.perf_counter()-start)*1000,**memory()}

    from deploy.render_app import create_app
    import uvicorn
    uvicorn.run(outer or create_app(api,ROOT/'frontend/dist'),host='127.0.0.1',port=args.port,access_log=False,log_level='error')


def parent(args):
    import httpx
    import numpy as np
    if args.output.exists():
        raise ValueError('Never overwrite a qualification receipt')
    environment=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
    command=[sys.executable,'-m','showcase.release_probe','--worker','--encoder',args.encoder,'--port',str(args.port)]
    if args.artifacts:command+=['--artifacts',str(args.artifacts)]
    started=time.perf_counter()
    process=subprocess.Popen(command,cwd=ROOT,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    base=f'http://127.0.0.1:{args.port}'
    report={'encoder':args.encoder,'platform':sys.platform,'fresh_process':True,'os_cache_controlled':False,
            'cpu_throttling':('See recorded cgroup CPU/memory limits; do not assume constrained' if sys.platform=='linux' else 'Not emulated; Windows timings are not 0.1-CPU Render timings'),
            'render_capacity_verified':False,'production_approved':False,'real_inference':True,'mocked_inference':False,'snapshots':{}}
    def call(client,path,body=None):
        start=time.perf_counter()
        response=client.get(base+path) if body is None else client.post(base+path,json=body)
        return response,(time.perf_counter()-start)*1000
    def sample(client,name,path,body=None,n=5):
        rows=[]
        for _ in range(n):
            response,elapsed=call(client,path,body)
            if response.status_code!=200:raise RuntimeError(f'{name}: HTTP {response.status_code}')
            rows.append(elapsed)
        report[name]={'n':n,'p50_ms':float(np.percentile(rows,50)),'p95_ms':float(np.percentile(rows,95)),'samples_ms':rows}
    try:
        with httpx.Client(timeout=240,trust_env=False) as client:
            deadline=time.monotonic()+60
            while True:
                if process.poll() is not None:raise RuntimeError('Local probe process failed before readiness')
                try:
                    if client.get(base+'/api/health/live',timeout=1).status_code==200:break
                except httpx.HTTPError:pass
                if time.monotonic()>deadline:raise TimeoutError('Local HTTP startup exceeded 60 seconds')
                time.sleep(.2)
            report['http_start_seconds']=time.perf_counter()-started
            report['snapshots']['http_ready']=client.get(base+'/api/__probe/stats').json()
            sample(client,'frontend','/',n=3)
            sample(client,'tasks','/api/showcase/tasks',n=3)
            sample(client,'evidence','/api/showcase/portfolio',n=3)
            question={'question':'What is the Atlas workshop date?','mode':'grounded'}
            response,elapsed=call(client,'/api/showcase/ask',question)
            response.raise_for_status()
            assert response.json()['status']=='answered' and '2026-11-05' in response.json()['answer']
            report['first_ask_ms']=elapsed
            report['snapshots']['retrieval_loaded']=client.get(base+'/api/__probe/stats').json()
            prediction={'subject':'Fictional interview','body':'Thank you for applying. We would like to invite you to an interview next Tuesday.'}
            response,elapsed=call(client,'/api/showcase/predict',prediction)
            response.raise_for_status();assert response.json()['model_version']=='phase2-A'
            report['first_classifier_ms']=elapsed
            report['snapshots']['combined_loaded']=client.get(base+'/api/__probe/stats').json()
            sample(client,'warm_ask','/api/showcase/ask',question)
            sample(client,'warm_classifier','/api/showcase/predict',prediction)
            if args.encoder=='free-candidate':
                ready=client.get(base+'/api/health/ready');ready.raise_for_status()
                assert ready.json()['id']=='e5-int8-fp32-corpus-v1'
                report['readiness']=ready.json()
                assert client.post(base+'/api/showcase/analyze',json=prediction).status_code==404
                # Long requests must stay bounded, including bilingual input and
                # token overflow that passes the character limit.
                for question_text in ['meeting '*125, 'هل عندي مهام متأخرة؟', 'x '*500]:
                    r,ms=call(client,'/api/showcase/ask',{'question':question_text,'mode':'grounded'})
                    assert r.status_code in (200,422)
                    report.setdefault('long_or_arabic_queries',[]).append({'characters':len(question_text),'status':r.status_code,'latency_ms':ms})
                assert client.post(base+'/api/showcase/ask',json={'question':'x'*1001}).status_code==422
                assert client.post(base+'/api/showcase/predict',content=b'x'*24001).status_code==413
            sample(client,'max_classifier','/api/showcase/predict',{'subject':'x'*300,'body':('Meeting invoice interview. '*300)[:6000]},n=2)
            report['max_encoder']=client.get(base+'/api/__probe/max-tokens').json()
            with ThreadPoolExecutor(max_workers=4) as pool:
                outcomes=list(pool.map(lambda _:call(client,'/api/showcase/ask',question),range(4)))
            report['concurrent_four']={'statuses':[r.status_code for r,_ in outcomes],'latencies_ms':[ms for _,ms in outcomes]}
            assert any(r.status_code==200 for r,_ in outcomes)
            assert all(r.status_code in (200,429) for r,_ in outcomes)
            response=client.get(base+'/api/__probe/evaluate');response.raise_for_status()
            report['evaluation']=response.json()
            report['snapshots']['final']=client.get(base+'/api/__probe/stats').json()
            assert not report['snapshots']['final']['database_imported'] and not report['snapshots']['final']['gmail_imported']
            report['elapsed_seconds']=time.perf_counter()-started
            report['status']='completed'
    except Exception as error:
        report['status']='failed';report['error_type']=type(error).__name__
        report['error']=str(error)[:300]
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        # The client shares the container cgroup with the worker. Preserve its
        # lifetime peak/OOM counters even if inference failed before readiness.
        # If the entire container dies, the external runner records Docker state.
        report['observer_final']=memory()
        report['worker_exit_code']=process.returncode
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='evaluation'},indent=2))
    if report['status']!='completed':raise SystemExit(1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',action='store_true')
    parser.add_argument('--encoder',choices=['torch','onnx-fp32','onnx-int8','free-candidate'],required=True)
    parser.add_argument('--artifacts',type=Path)
    parser.add_argument('--port',type=int,default=4182)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if not args.worker and args.output is None:parser.error('--output required')
    if args.encoder in ('onnx-fp32','onnx-int8') and args.artifacts is None:parser.error('--artifacts required for ONNX')
    worker(args) if args.worker else parent(args)

if __name__=='__main__':main()
