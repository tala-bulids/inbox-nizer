"""Optional isolated BGE benchmark; resource guard never deploys the model."""
import argparse,json,time
from pathlib import Path

def main():
    import psutil
    p=argparse.ArgumentParser();p.add_argument('--pairs',type=Path,required=True);p.add_argument('--model',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    free=psutil.virtual_memory().available/2**30
    if free<5:
        a.output.write_text(json.dumps({'status':'not_run_resource_guard','free_gib':free,'minimum_free_gib':5,'deployed':False},indent=2))
        return
    import torch
    torch.set_num_threads(2)
    from sentence_transformers import CrossEncoder
    start=time.perf_counter();model=CrossEncoder(a.model,device='cpu',local_files_only=True,max_length=512)
    load=time.perf_counter()-start;rows=[]
    for case in json.loads(a.pairs.read_text(encoding='utf-8')):
        candidates=case['candidates'][:32]
        start=time.perf_counter();scores=model.predict([(case['query'],c['text']) for c in candidates],batch_size=1)
        order=sorted(range(len(scores)),key=lambda i:-float(scores[i]))
        ranks=[r+1 for r,i in enumerate(order) if candidates[i]['relevant']]
        rows.append(dict(case=case['id'],seconds=time.perf_counter()-start,recall_at_5=sum(r<=5 for r in ranks)/max(1,sum(c['relevant'] for c in candidates)),mrr=1/min(ranks) if ranks else 0))
    a.output.write_text(json.dumps({'status':'measured','load_seconds':load,'rss_gib':psutil.Process().memory_info().rss/2**30,'cases':rows,'deployed':False},indent=2))
if __name__=='__main__':main()
