import argparse
import json
import random
import hashlib
from pathlib import Path

import numpy as np
from quality.dataset import LABELS, audit_split, partition_rows, prepare_rows as audited_rows
from quality.metrics import metrics as top_one_metrics
from classifier_config import model_path
from classifier_contract import inference_token_limit, validate_classifier_config


def load_training_data(path):
    """Read an explicitly selected local Arrow, JSON or JSONL dataset."""
    path = Path(path)
    if path.suffix == '.arrow':
        from datasets import Dataset
        return Dataset.from_file(str(path))
    with path.open(encoding='utf-8') as stream:
        if path.suffix in ('.jsonl', '.ndjson'):
            return [json.loads(line) for line in stream if line.strip()]
        data = json.load(stream)
    if not isinstance(data, list):
        raise ValueError('Training JSON must contain a list of labeled email rows.')
    return data


def prepare_rows(dataset):
    return audited_rows(dataset)[0]


def split_rows(rows, seed=42):
    assigned, _ = partition_rows(rows, seed)
    return tuple([row for row in assigned if row['split'] == part]
                 for part in ('train', 'validation', 'test'))


def score_predictions(logits, targets):
    logits = np.asarray(logits, dtype=float)
    targets = np.asarray(targets)
    if (logits.ndim != 2 or logits.shape != targets.shape or not len(logits)
            or logits.shape[1] != len(LABELS) or not np.isin(targets, [0, 1]).all()
            or not targets.any(axis=1).all()):
        raise ValueError('Use nonempty N x category-count logits and binary targets with a label per row.')
    if not np.isfinite(logits).all():
        raise ValueError('Classifier logits must be finite.')
    predicted = logits >= 0
    actual = targets.astype(bool)
    tp = (predicted & actual).sum(axis=0)
    fp = (predicted & ~actual).sum(axis=0)
    fn = (~predicted & actual).sum(axis=0)
    f1 = 2 * tp / np.maximum(2 * tp + fp + fn, 1)
    result = {
        'top1_accuracy': float(actual[np.arange(len(actual)), logits.argmax(axis=1)].mean()),
        'macro_f1': float(f1.mean()),
        'micro_f1': float(2 * tp.sum() / max(2 * tp.sum() + fp.sum() + fn.sum(), 1)),
        'per_label_f1': dict(zip(LABELS, f1.tolist()))
    }
    probabilities = 1 / (1 + np.exp(-np.clip(logits, -50, 50)))
    result.update(top_one_metrics(probabilities, [[label for i, label in enumerate(LABELS) if row[i]] for row in actual]))
    return result


def main():
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding

    parser = argparse.ArgumentParser(description='Train the inbox-nizer DistilBERT classifier offline.')
    parser.add_argument('--dataset-file', required=True, help='Local labeled JSON, JSONL or Arrow file.')
    parser.add_argument('--base-model', default='distilbert-base-uncased')
    parser.add_argument('--output-dir', help='Local artifact directory; defaults to EMAIL_MODEL_PATH.')
    parser.add_argument('--epochs', type=int, default=3)
    parser.add_argument('--batch-size', type=int, default=16)
    parser.add_argument('--max-length', type=int, default=256)
    parser.add_argument('--train-layers', type=int, default=2)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--learning-rate', type=float, default=2e-5)
    parser.add_argument('--patience', type=int, default=2)
    parser.add_argument('--evaluate-test', action='store_true', help='Explicit final diagnostic only; never use the result to select another candidate.')
    args = parser.parse_args()
    if (args.epochs < 1 or not 1 <= args.train_layers <= 6 or args.batch_size < 1
            or not 16 <= args.max_length <= 512 or args.learning_rate <= 0 or args.patience < 1):
        parser.error('Use positive epochs, batch size, learning rate and patience; 1 to 6 layers; 16 to 512 tokens.')
    output = model_path(args.output_dir)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error('Choose an empty output directory to protect existing models.')
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.set_num_threads(4)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    dataset = load_training_data(args.dataset_file)
    rows, audit = audit_split(dataset, seed=args.seed)
    training, validation, testing = ([r for r in rows if r['split'] == part] for part in ('train', 'validation', 'test'))
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, local_files_only=True)
    tokenizer.model_max_length = args.max_length
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model, num_labels=len(LABELS), problem_type='multi_label_classification',
        id2label=dict(enumerate(LABELS)), label2id={label: i for i, label in enumerate(LABELS)}, local_files_only=True
    ).to(device)

    # Train the last layers and the classifier.
    if not hasattr(model, 'distilbert'):
        parser.error('Layer freezing in this command supports DistilBERT only; use a matching local base model.')
    if args.train_layers > len(model.distilbert.transformer.layer):
        parser.error('--train-layers exceeds the number of layers in the base model.')
    if args.max_length > inference_token_limit(model.config, tokenizer):
        parser.error('--max-length exceeds the base model position limit.')
    model.config.inbox_nizer_max_length = args.max_length
    validate_classifier_config(model.config)
    for parameter in model.distilbert.parameters():
        parameter.requires_grad = False
    for layer in model.distilbert.transformer.layer[-args.train_layers:]:
        for parameter in layer.parameters():
            parameter.requires_grad = True

    def encode(items):
        encoded = tokenizer([item['text'] for item in items], truncation=True, max_length=args.max_length)
        return [{**{key: values[i] for key, values in encoded.items()},
                 'labels': [float(label in item['labels']) for label in LABELS]}
                for i, item in enumerate(items)]

    collator = DataCollatorWithPadding(tokenizer)
    train_data, val_data = map(encode, (training, validation))
    train_loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True, collate_fn=collator)
    targets = np.array([item['labels'] for item in train_data])
    positive = targets.sum(axis=0)
    if np.any(positive == 0):
        raise ValueError('A label has no training examples.')
    output.mkdir(parents=True, exist_ok=True)
    # Give rare labels more weight.
    weights = torch.tensor(np.clip((len(targets) - positive) / positive, 1, 10), dtype=torch.float32, device=device)
    loss_function = torch.nn.BCEWithLogitsLoss(pos_weight=weights)
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.learning_rate, weight_decay=0.01)

    def evaluate(items):
        model.eval()
        predictions, labels = [], []
        with torch.inference_mode():
            for batch in DataLoader(items, batch_size=args.batch_size, collate_fn=collator):
                labels.append(batch.pop('labels').numpy())
                predictions.append(model(**{key: value.to(device) for key, value in batch.items()}).logits.cpu().numpy())
        return score_predictions(np.concatenate(predictions), np.concatenate(labels))

    report = {'raw_rows': len(dataset), 'unique_rows': len(rows),
              'splits': {'train': len(training), 'validation': len(validation), 'test': len(testing)},
              'seed': args.seed, 'base_model': args.base_model, 'max_length': args.max_length,
              'data_audit': audit, 'learning_rate': args.learning_rate, 'batch_size': args.batch_size,
              'patience': args.patience, 'selection_metric': 'validation top1_macro_f1 then top1_accuracy',
              'label_provenance': 'Public annotations; not human-reviewed representative mailbox gold.',
              'production_adopted': False, 'calibration': 'Raw sigmoid scores; uncalibrated.',
              'train_layers': args.train_layers, 'epochs': [],
              'note': 'Top-1 is correct when it matches any annotated label. Test data is not used for model selection.'}
    print(json.dumps({'device': str(device), 'splits': report['splits']}), flush=True)
    manifest = [{'id': r['id'], 'group': r['group'], 'split': r['split'], 'labels': r['labels']} for r in rows]
    serialized = json.dumps(manifest, sort_keys=True)
    report['split_manifest_sha256'] = hashlib.sha256(serialized.encode()).hexdigest()
    (output / 'split_manifest.json').write_text(serialized, encoding='utf-8')
    best, stale_epochs = (-1, -1), 0
    for epoch in range(args.epochs):
        model.train()
        total_loss = 0
        for step, batch in enumerate(train_loader, 1):
            labels = batch.pop('labels').to(device)
            inputs = {key: value.to(device) for key, value in batch.items()}
            optimizer.zero_grad()
            loss = loss_function(model(**inputs).logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
            if step % 20 == 0:
                print(f'Epoch {epoch + 1}: {step}/{len(train_loader)} batches', flush=True)
        metrics = evaluate(val_data)
        report['epochs'].append({'epoch': epoch + 1, 'loss': total_loss / len(train_loader), 'validation': metrics})
        print(json.dumps(report['epochs'][-1]), flush=True)
        key = (metrics['top1_macro_f1'], metrics['top1_accuracy'])
        if key > best:
            best, stale_epochs = key, 0
            report['best_epoch'] = epoch + 1
            model.save_pretrained(output)
            tokenizer.save_pretrained(output)
        else:
            stale_epochs += 1
        (output / 'training_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        if stale_epochs >= args.patience:
            report['early_stopped'] = True
            break

    if args.evaluate_test:
        model = AutoModelForSequenceClassification.from_pretrained(output, local_files_only=True).to(device)
        report['test'] = evaluate(encode(testing))
        report['test_consumed'] = True
    else:
        report['test_consumed'] = False
    (output / 'training_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'best_epoch': report['best_epoch'], 'test_consumed': report['test_consumed']}), flush=True)


if __name__ == '__main__':
    main()
