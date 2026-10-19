"""Data-focused local candidates. The new forty-case holdout is evaluation-only."""
import json,hashlib,time,gc
from pathlib import Path
import numpy as np
from .dataset import audit_split,LABELS
from .classification_cases import DEV,FINAL,examples
from .deeper_cases import TRAIN,HOLDOUT,rows as authored
from .metrics import metrics
OUT=Path('results/quality-deeper-20261012')
def save(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def main():
    import torch
    torch.set_num_threads(2)
    from datasets import Dataset
    from sentence_transformers import SentenceTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    import joblib
    raw=list(Dataset.from_file(str(next((Path.home()/'.cache/huggingface/datasets/imnim___multiclass-email-classification').rglob('*train.arrow')))))
    data,audit=audit_split(raw)
    parts={s:[r for r in data if r['split']==s] for s in ('train','validation','test')}
    parts['supplement']=examples(DEV)+authored(TRAIN)
    parts['development']=examples(FINAL) # Former test is explicitly consumed development data.
    parts['holdout']=authored(HOLDOUT)
    save('manifest.json',{'seed':42,'audit':audit,'partitions':{s:[hashlib.sha256(r['text'].encode()).hexdigest() for r in rr] for s,rr in parts.items()},'note':'Prior twenty-case test is now development. New forty-case holdout is never used for selection.'})
    encoder=SentenceTransformer('intfloat/multilingual-e5-small',local_files_only=True,device='cpu')
    encoder.max_seq_length=512
    x={s:encoder.encode(['query: '+r['text'] for r in rr],batch_size=4,normalize_embeddings=True,show_progress_bar=False) for s,rr in parts.items()}
    del encoder;gc.collect()
    y={s:np.array([[label in r['labels'] for label in LABELS] for r in rr]) for s,rr in parts.items()}
    runs=[];best=None
    for weight in (1,3,6):
        xx=np.concatenate([x['train']]+[x['supplement']]*weight)
        yy=np.concatenate([y['train']]+[y['supplement']]*weight)
        for c in (1,10,100):
            model=OneVsRestClassifier(LogisticRegression(C=c,class_weight='balanced',solver='liblinear',max_iter=1000,random_state=42)).fit(xx,yy)
            public=metrics(model.predict_proba(x['validation']),[r['labels'] for r in parts['validation']])
            dev=metrics(model.predict_proba(x['development']),[r['labels'] for r in parts['development']])
            score=(public['top1_macro_f1']+dev['top1_macro_f1'])/2
            runs.append(dict(C=c,supplement_weight=weight,public_validation_f1=public['top1_macro_f1'],development_f1=dev['top1_macro_f1'],score=score))
            if best is None or score>best[0]:best=(score,model,c,weight)
    model=best[1];joblib.dump(model,OUT/'classifier-candidate.joblib')
    report={'selection':runs,'selected':{'C':best[2],'supplement_weight':best[3]},'models':{}}
    previous=joblib.load('results/quality-20261012/multilingual-probe.joblib')
    for name,head in [('previous-candidate',previous),('new-candidate',model)]:
        report['models'][name]={}
        for split in ('test','holdout'):
            scores=head.predict_proba(x[split]);m=metrics(scores,[r['labels'] for r in parts[split]])
            m['predictions']=[dict(id=r['id'],expected=r['labels'],predicted=LABELS[int(np.argmax(s))],confidence=float(max(s))) for r,s in zip(parts[split],scores)]
            report['models'][name][split]=m
    del previous,model;gc.collect()
    from transformers import AutoTokenizer,AutoModelForSequenceClassification
    tokenizer=AutoTokenizer.from_pretrained('results/checkpoint-3159',local_files_only=True)
    current=AutoModelForSequenceClassification.from_pretrained('results/checkpoint-3159',local_files_only=True).eval()
    order=[next(int(i) for i,l in current.config.id2label.items() if l==label) for label in LABELS]
    scores=[]
    with torch.inference_mode():
        for i in range(0,len(parts['holdout']),4):
            batch=tokenizer([r['text'] for r in parts['holdout'][i:i+4]],padding=True,truncation=True,return_tensors='pt')
            scores.extend(torch.sigmoid(current(**batch).logits).numpy()[:,order].tolist())
    m=metrics(scores,[r['labels'] for r in parts['holdout']]);m['predictions']=[dict(id=r['id'],expected=r['labels'],predicted=LABELS[int(np.argmax(s))],confidence=float(max(s))) for r,s in zip(parts['holdout'],scores)]
    report['models']['production']={'holdout':m}
    save('classification.json',report)
    print(json.dumps({name:{s:{k:v for k,v in m.items() if k in ('top1_accuracy','top1_macro_f1','finance_false_positives','wrong_confident_ge_080','top1_ece')} for s,m in sets.items()} for name,sets in report['models'].items()},indent=2))
if __name__=='__main__':main()
