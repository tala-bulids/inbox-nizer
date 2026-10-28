"""Offline HF/PyTorch DistilBERT fine-tuning recipe, separate from public serving.

The final test partition is never opened. Existing models cannot be overwritten.
Real training requires separately provisioned weights and sufficient free memory.
"""
import argparse
import os
from pathlib import Path
import random

import numpy as np
from classifier_contract import LABELS, inference_token_limit, validate_classifier_config
from .data import CONFIG, digest, load_development, read, write
from .evaluation import environment, evaluate
from .run import target


def seed_everything(seed):
    import torch
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.set_num_threads(2)


def fit(model, tokenizer, training, validation, config, output):
    """Testable training core; output directory must be new."""
    import torch
    from torch.utils.data import DataLoader
    from transformers import DataCollatorWithPadding
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    seed_everything(config['seed'])
    hp = config['finetune']
    if not hasattr(model, 'distilbert'):
        raise ValueError('This bounded recipe supports DistilBERT architectures only')
    validate_classifier_config(model.config)
    if hp['max_length'] > inference_token_limit(model.config, tokenizer):
        raise ValueError('Token limit exceeds model capacity')
    if not 1 <= hp['train_last_layers'] <= len(model.distilbert.transformer.layer):
        raise ValueError('Invalid last-layer count')
    model.config.inbox_nizer_max_length = hp['max_length']
    tokenizer.model_max_length = hp['max_length']
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    for parameter in model.distilbert.parameters():
        parameter.requires_grad = False
    for layer in model.distilbert.transformer.layer[-hp['train_last_layers']:]:
        for parameter in layer.parameters():
            parameter.requires_grad = True
    positives = target(training).sum(0)
    if (positives==0).any() or (positives==len(training)).any():
        raise ValueError('Missing positive/negative training coverage')
    weights = torch.tensor(np.clip((len(training)-positives)/positives, 1, hp['positive_weight_cap']), dtype=torch.float32, device=device)
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=weights)
    collator = DataCollatorWithPadding(tokenizer)

    def encode(rows):
        encoded = tokenizer([r['text'] for r in rows], truncation=True, max_length=hp['max_length'])
        return [{**{k:v[i] for k,v in encoded.items()}, 'labels': target([row])[0].astype(float).tolist()} for i,row in enumerate(rows)]

    generator = torch.Generator().manual_seed(config['seed'])
    loader = DataLoader(encode(training), batch_size=hp['batch_size'], shuffle=True, generator=generator, num_workers=0, collate_fn=collator)
    validation_loader = DataLoader(encode(validation), batch_size=hp['batch_size'], shuffle=False, num_workers=0, collate_fn=collator)
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=hp['learning_rate'], weight_decay=hp['weight_decay'])
    history = {'training_executed': True, 'test_evaluated': False, 'device': str(device), 'seed': config['seed'],
               'hyperparameters': hp, 'epochs': [], 'loss': 'Positive-weighted binary cross entropy; weights fit on training only'}
    best, stale = (-1., -1.), 0
    for epoch in range(hp['epochs']):
        model.train(); total = 0.; count = 0
        for batch in loader:
            labels = batch.pop('labels').to(device)
            optimizer.zero_grad()
            logits = model(**{k:v.to(device) for k,v in batch.items()}).logits
            loss = criterion(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total += float(loss.detach()) * len(labels); count += len(labels)
        model.eval(); scores = []; val_loss = 0.
        with torch.inference_mode():
            for batch in validation_loader:
                labels = batch.pop('labels').to(device)
                logits = model(**{k:v.to(device) for k,v in batch.items()}).logits
                val_loss += float(criterion(logits, labels)) * len(labels)
                scores.extend(torch.sigmoid(logits).cpu().numpy().tolist())
        measured = evaluate(scores, validation)
        history['epochs'].append({'epoch':epoch+1, 'train_loss':total/count,
            'validation_loss':val_loss/len(validation), 'validation_macro_f1':measured['top1_macro_f1'],
            'validation_accuracy':measured['top1_accuracy']})
        key = (measured['top1_macro_f1'], measured['top1_accuracy'])
        if key > best:
            best, stale = key, 0
            history['best_epoch'] = epoch+1
            checkpoint = output/f'epoch-{epoch+1}'
            model.save_pretrained(checkpoint); tokenizer.save_pretrained(checkpoint)
            write(checkpoint/'metrics.json', measured)
        else:
            stale += 1
        write(output/f'history-epoch-{epoch+1}.json', history)
        if stale >= hp['patience']:
            history['early_stopped'] = True
            break
    write(output/'training-history.json', history)
    return history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--base-model', type=Path, required=True, help='Locally provisioned DistilBERT snapshot; no network downloads')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import psutil
    if psutil.virtual_memory().available < 3*2**30:
        parser.error('Need at least 3 GiB available RAM before fine-tuning; use an authorized training environment')
    if args.output.exists():
        parser.error('Existing output is protected')
    config = read(CONFIG)
    parts, manifest = load_development(args.data)
    if manifest['config_sha256'] != digest(CONFIG):
        parser.error('Config changed after dataset freeze')
    seed_everything(config['seed'])
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(args.base_model, local_files_only=True,
        num_labels=len(LABELS), problem_type='multi_label_classification',
        id2label=dict(enumerate(LABELS)), label2id={v:k for k,v in enumerate(LABELS)})
    fit(model, tokenizer, parts['train'], parts['validation'], config, args.output)
    write(args.output/'run.json', {'environment':environment(), 'config_sha256':digest(CONFIG),
        'data_manifest_sha256':digest(args.data/'manifest.json'),
        'base_files':{p.name:digest(p) for p in args.base_model.iterdir() if p.is_file()},
        'artifacts':{str(p.relative_to(args.output)):digest(p) for p in args.output.rglob('*') if p.is_file()},
        'production_approved':False, 'test_evaluated':False})


if __name__ == '__main__':
    main()
