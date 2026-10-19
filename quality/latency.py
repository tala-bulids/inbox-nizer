"""Small warm single-email latency check, identical inputs and CPU threads."""
import gc,time,json
import numpy as np
from .classification import OUT,save
from .classification_cases import FINAL,examples

def measure(fn,texts):
    for text in texts[:3]:fn(text)
    durations=[]
    for text in texts:
        start=time.perf_counter();fn(text);durations.append((time.perf_counter()-start)*1000)
    return dict(n=len(durations),mean_ms=float(np.mean(durations)),p50_ms=float(np.median(durations)),p95_ms=float(np.percentile(durations,95)))

def main():
    import torch
    torch.set_num_threads(2)
    from transformers import AutoTokenizer,AutoModelForSequenceClassification
    texts=[r['text'] for r in examples(FINAL)]
    tokenizer=AutoTokenizer.from_pretrained('results/checkpoint-3159',local_files_only=True)
    model=AutoModelForSequenceClassification.from_pretrained('results/checkpoint-3159',local_files_only=True).eval()
    def current(text):
        with torch.inference_mode():return model(**tokenizer(text,return_tensors='pt',truncation=True)).logits
    result={'settings':'20 identical short bilingual inputs; batch=1; CPU threads=2; 3 warmups. Does not measure long real inbox throughput.'}
    result['current']=measure(current,texts)
    del model;gc.collect()
    from sentence_transformers import SentenceTransformer
    import joblib
    encoder=SentenceTransformer('intfloat/multilingual-e5-small',local_files_only=True,device='cpu')
    model=joblib.load(OUT/'multilingual-probe.joblib')
    result['candidate']=measure(lambda text:model.predict_proba(encoder.encode(['query: '+text],normalize_embeddings=True,show_progress_bar=False)),texts)
    save('latency.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
