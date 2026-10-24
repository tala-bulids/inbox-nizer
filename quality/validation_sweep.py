"""Small offline candidate sweep; never evaluates public test or private holdout.

The public labels are noisy and author-labelled bilingual examples are consumed
development diagnostics. Selection here cannot authorize production activation.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pyarrow.ipc as ipc
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline

from quality.dataset import audit_split, LABELS
from quality.metrics import metrics
from quality.classification_cases import DEV, FINAL, examples
from quality.deeper_cases import TRAIN, HOLDOUT, rows as authored_rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output directory; never overwrite candidate evidence.')
    cached=sorted((Path.home()/'.cache/huggingface/datasets/imnim___multiclass-email-classification').rglob('*train.arrow'))
    if not cached:
        parser.error('No cached public dataset; this tool never downloads data.')
    with cached[0].open('rb') as stream:
        raw=ipc.open_stream(stream).read_all().to_pylist()
    partitioned,audit=audit_split(raw,42)
    training=[r for r in partitioned if r['split']=='train']+examples(DEV)+authored_rows(TRAIN)
    validation=[r for r in partitioned if r['split']=='validation']
    # These older authored challenges were consumed in the October 12 reports.
    # They are development examples now, never a new final holdout.
    bilingual=examples(FINAL)+authored_rows(HOLDOUT)
    y=np.array([[label in row['labels'] for label in LABELS] for row in training])
    runs=[];best=None;stale=0
    args.output.mkdir(parents=True)
    for c in (.3,1,3,10,30,100,300):
        started=time.perf_counter()
        candidate=Pipeline([
            ('features',TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),max_features=40000,sublinear_tf=True)),
            ('head',OneVsRestClassifier(LogisticRegression(C=c,class_weight='balanced',solver='liblinear',max_iter=500,random_state=42))),
        ])
        candidate.fit([r['text'] for r in training],y)
        public=metrics(candidate.predict_proba([r['text'] for r in validation]),[r['labels'] for r in validation])
        bilingual_metrics=metrics(candidate.predict_proba([r['text'] for r in bilingual]),[r['labels'] for r in bilingual])
        key=(public['top1_macro_f1']+bilingual_metrics['top1_macro_f1'])/2
        run={'C':c,'seconds':time.perf_counter()-started,'public_validation':public,
             'consumed_bilingual_development':bilingual_metrics,'selection_score':key}
        runs.append(run)
        if best is None or key>best[0]:
            best=(key,c)
            stale=0
            joblib.dump(candidate,args.output/'candidate.joblib')
        else:
            stale+=1
        print(json.dumps({'C':c,'public_macro_f1':public['top1_macro_f1'],
                          'bilingual_dev_macro_f1':bilingual_metrics['top1_macro_f1']}),flush=True)
        if stale>=2:
            break
    def digest(data):
        return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    report={'seed':42,'architecture':'character TF-IDF + balanced one-vs-rest logistic regression',
            'selection':'mean of public validation and consumed authored bilingual development macro F1',
            'best_C':best[1],'runs':runs,'data_audit':audit,
            'stop_reason':'two consecutive non-improving candidates' if stale>=2 else 'bounded seven-candidate budget exhausted',
            'split_manifest_sha256':digest([{k:v for k,v in r.items() if k!='text'} for r in partitioned]),
            'training_sha256':digest(training),'validation_sha256':digest(validation),'bilingual_development_sha256':digest(bilingual),
            'artifact_sha256':hashlib.sha256((args.output/'candidate.joblib').read_bytes()).hexdigest(),
            'public_test_evaluated':False,'private_holdout_opened':False,'production_adopted':False,
            'limitations':['Public labels have known noise and no representative Arabic mailbox sample.',
                          'Bilingual development examples are authored and previously consumed; no fresh test accuracy is claimed.',
                          'Probabilities are not calibrated. A representative human-labelled final evaluation is still required.']}
    (args.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
