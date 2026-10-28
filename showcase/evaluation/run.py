"""One-shot real-E5 evaluation of the frozen authored suite, without Gmail/DB."""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import time

import numpy as np
import psutil
from showcase.engine import Engine, collection, tasks
from showcase.intelligence import index_version, metadata

ROOT=Path(__file__).resolve().parents[2]


def digest(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def retrieval_metrics(ranked, expected):
    if not expected: return None
    truth=set(expected)
    result={f'recall@{k}':len(set(ranked[:k])&truth)/len(truth) for k in (1,3,5,10)}
    result['mrr']=next((1/(i+1) for i,e in enumerate(ranked) if e in truth),0.)
    dcg=sum(1/math.log2(i+2) for i,e in enumerate(ranked[:5]) if e in truth)
    ideal=sum(1/math.log2(i+2) for i in range(min(len(truth),5)))
    result['ndcg@5']=dcg/ideal
    return result


def literal_grounding(answer, emails):
    """Mechanical source containment/date derivation, not semantic entailment."""
    by_id={e['id']:e for e in emails}
    checks=[]
    for block in answer.split('\n\n'):
        ids=[int(x) for x in re.findall(r'\[email_id=(\d+)\]',block)]
        if not ids: continue
        for eid in ids:
            if eid not in by_id:
                checks.append(False);continue
            email=by_id[eid]
            allowed_dates={str(t['deadline_date']) for t in tasks(email) if t['deadline_date']}
            body=' '.join(email['body'].split())
            for line in block.splitlines():
                line=re.sub(r'\[email_id=\d+\]','',line).strip()
                if not line or line.startswith(('Conflicting evidence','أدلة متعارضة','Past stated deadlines')): continue
                if ' — ' in line:
                    checks.append(line==f"{email['subject']} — {email['sender']} — {email['date'][:10]}")
                elif line.startswith(('Resolved date:','الموعد المحسوب:')):
                    checks.append(line.split(':',1)[1].strip() in allowed_dates)
                else:
                    checks.append(' '.join(line.split()) in body)
    return all(checks) if checks else None


def task_metrics(gold, emails):
    by_id={str(e['id']):e for e in emails}; results=[]
    for eid,expected in gold.items():
        email=by_id[eid];predicted=tasks(email)
        remaining=Counter(g['span'] for g in expected)
        tp=fp=deadlines=owners=sources=0
        for task in predicted:
            ev=task['evidence'];source=ev['text']
            sources+=task['email_id']==email['id'] and email['body'][ev['start']:ev['end']]==source
            if remaining[source]:
                tp+=1;remaining[source]-=1
                truth=next(g for g in expected if g['span']==source)
                actual=task['deadline_date'] or (task['deadline_at'].date() if task['deadline_at'] else None)
                deadlines+=(str(actual) if actual else None)==truth['deadline']
                owners+=task['responsible']==truth['responsible']
            else:fp+=1
        results.append({'email_id':int(eid),'language':email['language'],'tp':tp,'fp':fp,'fn':sum(remaining.values()),
            'deadline_correct_matched':deadlines,'responsible_correct_matched':owners,
            'source_correct':sources,'predicted':len(predicted),'negative':not expected})
    def aggregate(rows):
        tp=sum(r['tp'] for r in rows);fp=sum(r['fp'] for r in rows);fn=sum(r['fn'] for r in rows)
        return {'messages':len(rows),'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else None,
            'recall':tp/(tp+fn) if tp+fn else None,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
            'deadline_accuracy_matched':sum(r['deadline_correct_matched'] for r in rows)/tp if tp else None,
            'deadline_end_to_end_recall':sum(r['deadline_correct_matched'] for r in rows)/(tp+fn) if tp+fn else None,
            'responsible_accuracy_matched':sum(r['responsible_correct_matched'] for r in rows)/tp if tp else None,
            'source_reference_accuracy':sum(r['source_correct'] for r in rows)/sum(r['predicted'] for r in rows) if sum(r['predicted'] for r in rows) else None,
            'negative_message_false_task_rate':sum(r['negative'] and r['predicted']>0 for r in rows)/sum(r['negative'] for r in rows) if sum(r['negative'] for r in rows) else None}
    return {'overall':aggregate(results),'by_language':{l:aggregate([r for r in results if r['language']==l]) for l in ('en','ar')},'cases':results}


def aggregate_qa(cases):
    ranked=[c['retrieval'] for c in cases if c['retrieval']]
    citations=sum(c['citation_count'] for c in cases)
    grounded=[c['literal_grounding'] for c in cases if c['literal_grounding'] is not None]
    missing=[c for c in cases if c['expected_status']=='insufficient_evidence']
    return {'n':len(cases),'retrieval':{k:float(np.mean([r[k] for r in ranked])) for k in ranked[0]} if ranked else None,
        'status_accuracy':sum(c['status_correct'] for c in cases)/len(cases),
        'evidence_set_accuracy':sum(c['evidence_set_correct'] for c in cases)/len(cases),
        'citation_precision_against_expected':sum(c['correct_citations'] for c in cases)/citations if citations else None,
        'literal_grounding_check_rate':sum(grounded)/len(grounded) if grounded else None,
        'literal_grounding_note':'Automated source containment/derived-date check; not independent semantic correctness',
        'missing_evidence_abstention_rate':sum(c['status']=='insufficient_evidence' for c in missing)/len(missing) if missing else None,
        'latency_p50_ms':float(np.percentile([c['latency_ms'] for c in cases],50)),
        'latency_p95_ms':float(np.percentile([c['latency_ms'] for c in cases],95))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): parser.error('Never overwrite an evaluation receipt')
    freeze=read(Path(__file__).with_name('freeze.json'))
    for name,sha in freeze.items():
        if digest(ROOT/name)!=sha: raise ValueError('Frozen corpus/evaluation changed: '+name)
    suite=read(Path(__file__).with_name('heldout-v1.json'))
    import torch
    torch.set_num_threads(2)
    engine=Engine();start=time.perf_counter();engine.retrieve('Browse the curated mail collection')
    cold_seconds=time.perf_counter()-start
    emails=collection();cases=[]
    for case in suite['questions']:
        ranked=engine.retrieve(case['question'])
        start=time.perf_counter();result=engine.ask(case['question']);elapsed=(time.perf_counter()-start)*1000
        cited=[int(x) for x in re.findall(r'\[email_id=(\d+)\]',result['answer'])]
        cases.append({**case,'expected_status':case['status'],'status':result['status'],
            'status_correct':result['status']==case['status'],'retrieval':retrieval_metrics([r['email_id'] for r in ranked],case['evidence']),
            'ranked_top10':[r['email_id'] for r in ranked[:10]],'cited':cited,
            'citation_count':len(cited),'correct_citations':sum(i in case['evidence'] for i in cited),
            'evidence_set_correct':set(cited)==set(case['evidence']),
            'literal_grounding':literal_grounding(result['answer'],emails), 'latency_ms':elapsed,
            'answer':result['answer']})
    memory=psutil.Process().memory_info()
    report={'evaluation':'Frozen authored suite; same AI author, not independently human-reviewed or representative',
        'real_embeddings':True,'mocked_inference':False,'generator_used':False,'collection_version':index_version(emails),
        'frozen_files':freeze,'reference_datetime':metadata()['reference_datetime'],
        'code_sha256':{p.relative_to(ROOT).as_posix():digest(p) for p in [ROOT/'showcase/engine.py',ROOT/'showcase/intelligence.py',Path(__file__)]},
        'runtime':{p:importlib.metadata.version(p) for p in ('torch','transformers','sentence-transformers','numpy','tokenizers','fastapi','psutil')},
        'cold_index_seconds':cold_seconds,'rss_mib_after':memory.rss/2**20,
        'process_peak_wset_mib':getattr(memory,'peak_wset',0)/2**20 or None,
        'qa':aggregate_qa(cases),'by_language':{l:aggregate_qa([c for c in cases if c['language']==l]) for l in ('en','ar')},
        'tasks':task_metrics(suite['task_gold'],emails),'cases':cases,
        'no_post_evaluation_tuning':True,'production_approved':False,'render_capacity_verified':False}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False,default=str)
    print(json.dumps({k:report[k] for k in ('qa','by_language','cold_index_seconds','rss_mib_after','process_peak_wset_mib')},ensure_ascii=True))
    print(json.dumps(report['tasks']['overall']))


if __name__=='__main__':main()
