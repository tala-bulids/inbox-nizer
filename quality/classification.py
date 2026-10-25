"""Offline classifier experiment. Final sets evaluated once after validation selection."""
import argparse, hashlib, json, time
from pathlib import Path
import numpy as np
from .dataset import audit_split, LABELS
from .metrics import metrics
from .classification_cases import DEV, FINAL, examples
OUT=Path('results/quality-20261012')
def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reuse-baselines',action='store_true',help='Reuse existing baseline measurements for the same fixed dataset.')
    args=parser.parse_args()
    import torch
    torch.set_num_threads(2)
    from datasets import Dataset
    raw=list(Dataset.from_file(str(next((Path.home()/'.cache/huggingface/datasets/imnim___multiclass-email-classification').rglob('*train.arrow')))))
    rows,audit=audit_split(raw);save('data-audit.json',audit)
    save('split-manifest.json',[{k:v for k,v in r.items() if k!='text'} for r in rows])
    parts={name:[r for r in rows if r['split']==name] for name in ('train','validation','test')}
    parts['train']+=examples(DEV)
    final=examples(FINAL)
    save('challenge-manifest.json',{'dev_sha256':hashlib.sha256(json.dumps(DEV).encode()).hexdigest(),'final_sha256':hashlib.sha256(json.dumps(FINAL).encode()).hexdigest(),'final_n':len(final),'selection':'public validation only; final bilingual set is not a selection criterion'})
    report={'audit':audit,'models':{},'limitations':['Public data may have been seen by legacy checkpoints; this public holdout is not an unbiased legacy test.','The bilingual challenge is tiny, author-labelled synthetic data; not a real-mailbox accuracy estimate.']}
    if args.reuse_baselines and (OUT/'classification.json').exists():
        report=json.loads((OUT/'classification.json').read_text(encoding='utf-8'))
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    for name in ('checkpoint-3159','email-candidate-v2'):
        if name in report['models']:
            continue
        path=Path('results')/name;start=time.perf_counter()
        tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True)
        model=AutoModelForSequenceClassification.from_pretrained(path,local_files_only=True).eval()
        order=[next(int(i) for i,label in model.config.id2label.items() if label==l) for l in LABELS]
        result={'load_seconds':time.perf_counter()-start,'mapping':model.config.id2label,'max_length':512,'sets':{}}
        for split,data in [('public_test',parts['test']),('bilingual_test',final)]:
            scores=[];start=time.perf_counter()
            with torch.inference_mode():
                for i in range(0,len(data),4):
                    batch=tokenizer([r['text'] for r in data[i:i+4]],return_tensors='pt',padding=True,truncation=True,max_length=512)
                    scores.extend(torch.sigmoid(model(**batch).logits).numpy()[:,order].tolist())
            result['sets'][split]=metrics(scores,[r['labels'] for r in data]);result['sets'][split]['ms_per_email']=(time.perf_counter()-start)*1000/len(data)
            if split=='bilingual_test':result['predictions']=[dict(id=r['id'],expected=r['labels'],predicted=LABELS[int(np.argmax(s))],confidence=max(s)) for r,s in zip(data,scores)]
        report['models'][name]=result;save('classification.json',report)
        del model,tokenizer
        import gc;gc.collect()
        print(name,'complete',flush=True)
    # Frozen multilingual features test the language mismatch without training a large encoder.
    from sentence_transformers import SentenceTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    import joblib
    model=SentenceTransformer('intfloat/multilingual-e5-small',local_files_only=True,device='cpu')
    model.max_seq_length=512
    vectors={};timings={}
    for name,data in {**parts,'bilingual_test':final}.items():
        start=time.perf_counter();vectors[name]=model.encode(['query: '+r['text'] for r in data],batch_size=4,normalize_embeddings=True,show_progress_bar=False)
        timings[name]=(time.perf_counter()-start)*1000/len(data)
    del model
    y=np.array([[label in r['labels'] for label in LABELS] for r in parts['train']])
    runs=[];best=None
    for c in (.1,1,10,100):
        model=OneVsRestClassifier(LogisticRegression(C=c,class_weight='balanced',solver='liblinear',max_iter=1000,random_state=42)).fit(vectors['train'],y)
        score=model.predict_proba(vectors['validation']);result=metrics(score,[r['labels'] for r in parts['validation']]);runs.append({'C':c,'validation':result})
        key=(result['top1_macro_f1'],result['top1_accuracy'])
        if best is None or key>best[0]:best=(key,model,c)
    model=best[1];joblib.dump(model,OUT/'multilingual-probe.joblib')
    result={'encoder':'intfloat/multilingual-e5-small','selection_metric':'top1_macro_f1 then top1_accuracy','C':best[2],'seed':42,'epochs':'not applicable: frozen encoder, convex linear head','learning_rate':'not applicable: liblinear','batch_size':4,'max_length':512,'validation_runs':runs,'sets':{}}
    for name,data in [('public_test',parts['test']),('bilingual_test',final)]:
        scores=model.predict_proba(vectors['test' if name=='public_test' else name]);result['sets'][name]=metrics(scores,[r['labels'] for r in data]);result['sets'][name]['ms_per_email']=timings['test' if name=='public_test' else name]
        if name=='bilingual_test':result['predictions']=[dict(id=r['id'],expected=r['labels'],predicted=LABELS[int(np.argmax(s))],confidence=float(max(s))) for r,s in zip(data,scores)]
    report['models']['multilingual-probe']=result;save('classification.json',report);print('probe complete',flush=True)
if __name__=='__main__':main()
