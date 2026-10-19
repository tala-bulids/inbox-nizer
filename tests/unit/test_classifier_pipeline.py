"""Offline mechanics checks using real, tiny, randomly initialized DistilBERT.

These synthetic fixtures measure no email-classification quality.
Run with --confcutdir=tests/unit to avoid the PostgreSQL integration fixtures.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from classifier_config import PROJECT_ROOT, DEFAULT_MODEL_DIR, model_path
from classifier_contract import LABELS, inference_token_limit


def test_model_paths_do_not_depend_on_working_directory(monkeypatch, tmp_path):
    monkeypatch.delenv('EMAIL_MODEL_PATH', raising=False)
    monkeypatch.chdir(tmp_path)
    assert model_path() == DEFAULT_MODEL_DIR
    monkeypatch.setenv('EMAIL_MODEL_PATH', 'results/custom')
    assert model_path() == PROJECT_ROOT / 'results/custom'
    assert model_path(tmp_path) == tmp_path
    assert model_path('results/explicit') == PROJECT_ROOT / 'results/explicit'


def test_training_limit_survives_tokenizer_metadata_changes():
    config = SimpleNamespace(max_position_embeddings=512, inbox_nizer_max_length=32)
    assert inference_token_limit(config, SimpleNamespace(model_max_length=10**30)) == 32


@pytest.mark.parametrize('logits,targets', [([], []), ([[1]], [[1]]),
    (np.zeros((1, 10)), np.zeros((1, 10))),
    (np.zeros((1, 10)), np.full((1, 10), 2)),
    (np.full((1, 10), np.nan), np.ones((1, 10)))])
def test_metrics_reject_invalid_arrays(logits, targets):
    from app import score_predictions
    with pytest.raises(ValueError):
        score_predictions(logits, targets)


def test_missing_artifact_is_actionable(tmp_path):
    from predict import load_classifier
    with pytest.raises(FileNotFoundError, match='EMAIL_MODEL_PATH'):
        load_classifier(tmp_path / 'missing')


def test_train_save_reload_predict_and_evaluate(tmp_path, monkeypatch):
    import torch
    from tokenizers import Tokenizer, models, pre_tokenizers, processors
    from transformers import DistilBertConfig, DistilBertForSequenceClassification, PreTrainedTokenizerFast
    from evaluate import evaluate_emails
    import predict

    torch.set_num_threads(2)
    monkeypatch.setenv('HF_HUB_OFFLINE', '1')
    monkeypatch.setenv('HF_DATASETS_OFFLINE', '1')
    words = ('apple zebra volcano telescope signature ocean password university ticket calendar '
             'penguin bicycle journal lantern violet cloud forest amber quartz window '
             'harbor dragon mango velvet rocket copper orchid winter summer emerald').split()
    special = ['[PAD]', '[UNK]', '[CLS]', '[SEP]', '[MASK]']
    vocab = {word: i for i, word in enumerate(special + words)}
    backend = Tokenizer(models.WordPiece(vocab, unk_token='[UNK]'))
    backend.pre_tokenizer = pre_tokenizers.Whitespace()
    backend.post_processor = processors.TemplateProcessing(
        single='[CLS] $A [SEP]', special_tokens=[('[CLS]', 2), ('[SEP]', 3)])
    tokenizer = PreTrainedTokenizerFast(tokenizer_object=backend, pad_token='[PAD]',
        unk_token='[UNK]', cls_token='[CLS]', sep_token='[SEP]', mask_token='[MASK]',
        model_max_length=32, model_input_names=['input_ids', 'attention_mask'])
    config = DistilBertConfig(vocab_size=len(vocab), n_layers=1, n_heads=2,
        dim=16, hidden_dim=32, max_position_embeddings=32,
        num_labels=len(LABELS), problem_type='multi_label_classification',
        id2label=dict(enumerate(LABELS)), label2id={label: i for i, label in enumerate(LABELS)})
    base, output = tmp_path / 'base', tmp_path / 'trained'
    DistilBertForSequenceClassification(config).save_pretrained(base)
    tokenizer.save_pretrained(base)
    data = tmp_path / 'emails.json'
    # Every class is present in every partition; labels are purely synthetic.
    data.write_text(json.dumps([{'subject': word, 'body': '', 'labels': LABELS}
                                for word in words]), encoding='utf-8')
    command = [sys.executable, str(PROJECT_ROOT / 'app.py'), '--base-model', str(base),
        '--dataset-file', str(data), '--output-dir', str(output), '--epochs', '1',
        '--batch-size', '8', '--max-length', '32', '--train-layers', '1', '--evaluate-test']
    run = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, run.stdout + run.stderr
    report = json.loads((output / 'training_report.json').read_text(encoding='utf-8'))
    assert report['best_epoch'] == 1 and report['test_consumed'] is True
    assert report['max_length'] == 32
    manifest = json.loads((output / 'split_manifest.json').read_text(encoding='utf-8'))
    groups = {part: {r['group'] for r in manifest if r['split'] == part}
              for part in ('train', 'validation', 'test')}
    assert not groups['train'] & (groups['validation'] | groups['test'])
    assert not groups['validation'] & groups['test']
    monkeypatch.setattr(predict, 'MODEL_PATH', output)
    monkeypatch.setattr(predict, 'model', None)
    monkeypatch.setattr(predict, 'tokenizer', None)
    subject, body = ' apple ', '<p>zebra</p> ' * 80
    result = predict.classify_email(subject, body)
    evaluated = evaluate_emails(output, [{'subject': subject, 'body': body}])
    assert evaluated['emails'][0]['predictions'] == result
    assert result[0]['category'] in LABELS and 0 <= result[0]['confidence'] <= 1
    assert evaluated['top1_accuracy'] is None
    before = hashlib.sha256((output / 'model.safetensors').read_bytes()).hexdigest()
    retry = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert retry.returncode == 2 and 'empty output directory' in retry.stderr
    assert hashlib.sha256((output / 'model.safetensors').read_bytes()).hexdigest() == before
