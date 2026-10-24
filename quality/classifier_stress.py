"""Post-selection sender stress and tokenizer audit; never tunes a checkpoint."""
import hashlib,json,time,gc
from pathlib import Path
import numpy as np
from .classification_cases import FINAL,examples
from .dataset import LABELS,content
from .classification import OUT,save

def main():
    import torch
    torch.set_num_threads(2)
    from transformers import AutoTokenizer,AutoModelForSequenceClassification
    from datasets import Dataset
    raw=list(Dataset.from_file(str(next((Path.home()/'.cache/huggingface/datasets/imnim___multiclass-email-classification').rglob('*train.arrow')))))
    tokenizer=AutoTokenizer.from_pretrained('results/checkpoint-3159',local_files_only=True)
    lengths=[len(tokenizer(content(r['subject'],r['body']),truncation=False)['input_ids']) for r in raw]
    tests=examples(FINAL);variants=[r['text']+f'\nSent by {sender}' for r in tests for sender in ('accounts@billing.example','community@network.example')]
    report={'tokenizer':{'public_over_256':sum(n>256 for n in lengths),'public_over_512':sum(n>512 for n in lengths),'max_tokens':max(lengths),'arabic_unknown':[]},'artifacts':{},'sender_stress':{}}
    for r in tests:
        if r['language']=='ar':
            ids=tokenizer(r['text'])['input_ids'];report['tokenizer']['arabic_unknown'].append(dict(id=r['id'],unk=sum(i==tokenizer.unk_token_id for i in ids),tokens=len(ids)))
    for name in ('checkpoint-3159','email-candidate-v2'):
        path=Path('results')/name
        manifest={}
        for f in path.iterdir():
            if f.name in ('config.json','model.safetensors','tokenizer.json','training_report.json'):
                h=hashlib.sha256()
                with f.open('rb') as stream:
                    for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
                manifest[f.name]=h.hexdigest()
        report['artifacts'][name]=manifest
    model=AutoModelForSequenceClassification.from_pretrained('results/checkpoint-3159',local_files_only=True).eval()
    with torch.inference_mode():
        pred=[]
        for i in range(0,len(variants),4):
            b=tokenizer(variants[i:i+4],padding=True,truncation=True,return_tensors='pt')
            pred.extend(model(**b).logits.argmax(-1).tolist())
    report['sender_stress']['checkpoint-3159']={'pairs':len(tests),'changed_category':sum(pred[i]!=pred[i+1] for i in range(0,len(pred),2))}
    del model;gc.collect()
    from sentence_transformers import SentenceTransformer
    import joblib
    model=SentenceTransformer('intfloat/multilingual-e5-small',local_files_only=True,device='cpu')
    vectors=model.encode(['query: '+t for t in variants],batch_size=4,normalize_embeddings=True,show_progress_bar=False)
    probe=joblib.load(OUT/'multilingual-probe.joblib');pred=probe.predict_proba(vectors).argmax(-1)
    report['sender_stress']['multilingual-probe']={'pairs':len(tests),'changed_category':sum(bool(pred[i]!=pred[i+1]) for i in range(0,len(pred),2))}
    save('artifact-tokenizer-stress.json',report)
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
