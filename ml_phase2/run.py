"""One fixed experiment per process: A sparse, B historical, C frozen E5 + head."""
import argparse
import gc
import json
from pathlib import Path
import random
import time
import warnings

import joblib
import numpy as np
import psutil
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import FeatureUnion
from threadpoolctl import threadpool_limits

from classifier_contract import LABELS, validate_classifier_config, inference_token_limit
from .data import CONFIG, digest, load_development, read, write
from .evaluation import benchmark, environment, evaluate


def target(rows):
    return np.asarray([[label in r['labels'] for label in LABELS] for r in rows], dtype=int)


def binary_loss(scores, y):
    p = np.clip(scores, 1e-7, 1-1e-7)
    return float(-(y*np.log(p)+(1-y)*np.log(1-p)).mean())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', choices=['A','B','C'], required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model-path', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output directory; never overwrite evidence/models')
    if psutil.virtual_memory().available < 1.2*2**30:
        parser.error('At least 1.2 GiB available RAM required; do not train in production')
    config = read(CONFIG)
    parts, manifest = load_development(args.data)
    if manifest['config_sha256'] != digest(CONFIG):
        parser.error('Configuration changed since dataset freeze')
    train, val = parts['train'], parts['validation']
    y = target(train)
    if (y.sum(0) == 0).any() or (y.sum(0) == len(y)).any():
        parser.error('Every label requires positive and negative training examples')
    random.seed(config['seed']); np.random.seed(config['seed'])
    warnings.simplefilter('error', ConvergenceWarning)
    args.output.mkdir(parents=True)
    write(args.output/'configuration.json', config)
    start = time.perf_counter()
    artifact = None
    history = {'epochs': [], 'method': 'Not trained: historical checkpoint inference'}
    with threadpool_limits(limits=1):
        if args.candidate in ('A','C'):
            if args.candidate == 'A':
                settings = config['tfidf']
                encoder = FeatureUnion([
                    ('word', TfidfVectorizer(ngram_range=(1,2), min_df=settings['min_df'], max_features=settings['word_features'], sublinear_tf=True, dtype=np.float32)),
                    ('char', TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), min_df=settings['min_df'], max_features=settings['char_features'], sublinear_tf=True, dtype=np.float32))])
                train_x = encoder.fit_transform([r['text'] for r in train])
                encode = encoder.transform
                identity = {'architecture': 'word/character TF-IDF + balanced one-vs-rest logistic regression'}
            else:
                import torch
                from sentence_transformers import SentenceTransformer
                torch.set_num_threads(2)
                torch.manual_seed(config['seed'])
                spec = config['multilingual']
                # Snapshot is pinned; no inference-time or trainer-time downloads.
                encoder = SentenceTransformer(spec['model'], revision=spec['revision'], local_files_only=True, device='cpu')
                encoder.max_seq_length = spec['max_length']
                def encode(texts):
                    return encoder.encode([spec['prefix']+text for text in texts], batch_size=spec['batch_size'], normalize_embeddings=True, show_progress_bar=False)
                train_x = encode([r['text'] for r in train])
                identity = dict(spec)
            val_x = encode([r['text'] for r in val])
            model = OneVsRestClassifier(LogisticRegression(**config['linear'], random_state=config['seed']), n_jobs=1)
            model.fit(train_x, y)
            scores = model.predict_proba(val_x)
            history = {'method': 'One fixed convex liblinear fit; no epoch/early-stopping claims',
                'solver_iterations_per_label': [int(est.n_iter_[0]) for est in model.estimators_],
                'train_unweighted_binary_log_loss': binary_loss(model.predict_proba(train_x), y),
                'validation_unweighted_binary_log_loss': binary_loss(scores, target(val)),
                'epochs': []}
            artifact = args.output/'candidate.joblib'
            joblib.dump({'classifier': model, 'features': encoder if args.candidate=='A' else None,
                         'encoder_spec': identity, 'labels': LABELS, 'preprocessing': 'ml_phase2.data.normalize'}, artifact)
            def predict(texts):
                return model.predict_proba(encode(texts))
        else:
            if args.model_path is None:
                parser.error('B requires the existing checkpoint directory')
            expected = read(Path(__file__).resolve().parents[1]/'docs/release/v03-v10-20261024.json')['source_files_sha256']
            for name, sha in expected.items():
                if digest(args.model_path/name) != sha:
                    raise ValueError('Historical model identity mismatch: '+name)
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            torch.set_num_threads(2)
            tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(args.model_path, local_files_only=True).eval()
            mapping = validate_classifier_config(model.config)
            order = [next(i for i,l in mapping.items() if l == label) for label in LABELS]
            limit = min(config['legacy']['max_length'], inference_token_limit(model.config, tokenizer))
            def predict(texts):
                batches = []
                with torch.inference_mode():
                    for i in range(0, len(texts), config['legacy']['batch_size']):
                        encoded = tokenizer(texts[i:i+config['legacy']['batch_size']], padding=True, truncation=True, max_length=limit, return_tensors='pt')
                        batches.append(torch.sigmoid(model(**encoded).logits).numpy()[:,order])
                return np.concatenate(batches)
            scores = predict([r['text'] for r in val])
            identity = {'checkpoint': config['legacy']['checkpoint'], 'files_sha256': expected, 'max_length': limit,
                        'contamination': 'Unknown original split; public corpus may have been used to train this checkpoint'}
        elapsed = time.perf_counter()-start
        measured = evaluate(scores, val)
        resources = benchmark(predict, val)
    write(args.output/'training-history.json', history)
    write(args.output/'metrics.json', measured)
    write(args.output/'confusion-matrix.json', {'labels': LABELS, 'matrix': measured['confusion_matrix'], 'definition': measured['confusion_note']})
    write(args.output/'per-class.json', measured['per_class'])
    # Local review only. Do not copy row-level outputs or text to the portfolio.
    write(args.output/'validation-predictions-private.json', [dict(id=r['id'], reference=r['labels'], scores=s.tolist()) for r,s in zip(val,scores)])
    report = {'candidate': args.candidate, 'training_executed': args.candidate in ('A','C'),
        'encoder_finetuned': False, 'test_evaluated': False, 'production_approved': False,
        'eligible_research_selection': args.candidate != 'B', 'identity': identity,
        'artifact_sha256': digest(artifact) if artifact else None,
        'data_manifest_sha256': digest(args.data/'manifest.json'), 'config_sha256': digest(CONFIG),
        'environment': environment(), 'fit_or_load_and_validation_seconds': elapsed, 'benchmark': resources,
        'scores_are_calibrated': False, 'validation_used_for_selection': True}
    write(args.output/'run.json', report)
    print(json.dumps({'candidate': args.candidate, 'validation_n': measured['n'], 'accuracy': measured['top1_accuracy'],
                      'macro_f1': measured['top1_macro_f1'], 'weighted_f1': measured['top1_weighted_f1'], 'test_evaluated': False}))
    gc.collect()


if __name__ == '__main__':
    main()
