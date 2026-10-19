"""Pure release-gate regression tests; no models, mailbox or database required."""
import copy
import csv
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from classifier_contract import LABELS, inference_token_limit, validate_classifier_config
from quality.classifier_release import assess_release, final_evaluation, review_metadata, review_status, sha256_file
from quality.metrics import metrics


def perfect_evidence():
    labels = [[label] for label in LABELS for _ in range(30)]
    scores = [[.99 if label == row[0] else .01 for label in LABELS] for row in labels]
    return {'metrics': metrics(scores, labels), 'by_language': {
        'ar': {'n': 150, 'top1_accuracy': 1.0}, 'en': {'n': 150, 'top1_accuracy': 1.0}},
        'review_counts': {'total': 300, 'human_reviewed': 300, 'ambiguous': 0, 'weak': 0, 'pending': 0, 'invalid': 0},
        'provenance': {'label_source': 'human_reviewed_mailbox', 'partition': 'holdout',
            'used_for_selection': False, 'representative': True, 'all_rows_reviewed': True,
            'one_time_evaluation': True, **{key: 'a' * 64 for key in (
                'artifact_sha256', 'review_manifest_sha256', 'review_labels_sha256',
                'review_policy_sha256', 'predictions_sha256')}}}


def test_release_gate_requires_complete_real_evidence():
    assert not assess_release(None)['passed']
    assert assess_release(perfect_evidence())['passed']
    assert not assess_release(perfect_evidence(), 'b' * 64)['passed']
    for field, value in [('representative', False), ('label_source', 'synthetic'),
                         ('used_for_selection', True), ('all_rows_reviewed', 1)]:
        evidence = perfect_evidence()
        evidence['provenance'][field] = value
        assert not assess_release(evidence)['passed']


@pytest.mark.parametrize('value', [True, float('nan'), float('inf'), -1, 1.1, '1', None])
def test_invalid_numbers_cannot_pass_release(value):
    for container, field in [('metrics', 'top1_accuracy'), ('language', 'top1_accuracy'), ('class', 'precision')]:
        evidence = perfect_evidence()
        target = evidence['metrics'] if container == 'metrics' else (
            evidence['by_language']['ar'] if container == 'language' else evidence['metrics']['per_class']['Business'])
        target[field] = value
        assert not assess_release(evidence)['passed']


def test_excluding_ambiguous_cases_cannot_hide_large_failure_slice():
    evidence = perfect_evidence()
    evidence['review_counts'].update(total=400, ambiguous=100)
    assert not assess_release(evidence)['passed']
    evidence['review_counts'].update(total=300, ambiguous=0, weak=1)
    assert not assess_release(evidence)['passed']


def test_review_metadata_never_promotes_weak_or_unattested_labels():
    base = dict(email_id='1', gold_label=LABELS[0], label_source='human_reviewed',
                reviewer='Test human', reviewed_at='2026-01-01', ambiguous='')
    assert review_metadata([base])['human_reviewed'] == 1
    for change in ({'label_source': 'weak'}, {'label_source': ''}, {'reviewer': ''},
                   {'reviewed_at': '2999-01-01'}, {'reviewed_at': None}, {'gold_label': 'Unknown'}):
        assert review_metadata([{**base, **change}])['human_reviewed'] == 0
    assert review_metadata([base, base])['invalid'] == 1


def test_status_does_not_read_holdout(tmp_path, monkeypatch):
    (tmp_path / 'holdout.csv').touch()
    original = Path.open

    def guarded(path, *args, **kwargs):
        assert path.name != 'holdout.csv', 'Status must never inspect holdout labels'
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', guarded)
    assert review_status(tmp_path)['holdout_opened'] is False
    assert review_status(tmp_path)['holdout_present'] is True
    assert review_status(None)['human_reviewed'] is None


def final_fixture(tmp_path, source='human_reviewed'):
    # Artificial unit-test fixtures only; never used as real release evidence.
    manifest = [{'email_id': '1', 'group': 'g1', 'split': 'holdout', 'language': 'en'}]
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    (tmp_path / 'review-policy.json').write_text(json.dumps({
        'holdout_used_for_selection': False, 'representative': False, 'sampling': 'unit test'}), encoding='utf-8')
    row = dict(email_id='1', gold_label=LABELS[0], ambiguous='', label_source=source,
               reviewer='Test human', reviewed_at='2026-01-01')
    with (tmp_path / 'holdout.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    frozen = {'artifact_sha256': 'a' * 64, 'holdout_used_for_selection': False,
              'review_manifest_sha256': sha256_file(tmp_path / 'manifest.json'),
              'review_policy_sha256': sha256_file(tmp_path / 'review-policy.json')}
    predictions = {'artifact_sha256': 'a' * 64, 'label_order': LABELS,
                   'rows': [{'email_id': '1', 'scores': [.99] + [.01] * 9}]}
    return frozen, predictions


def test_final_evaluation_consumes_once_and_records_bindings(tmp_path):
    frozen, predictions = final_fixture(tmp_path)
    report = final_evaluation(tmp_path, predictions, frozen)
    assert report['metrics']['n'] == 1
    assert report['release_gate']['passed'] is False
    assert report['provenance']['review_policy_sha256'] == frozen['review_policy_sha256']
    with pytest.raises(FileExistsError):
        final_evaluation(tmp_path, predictions, frozen)
    with pytest.raises(ValueError, match='receipt'):
        final_evaluation(tmp_path, predictions, frozen, tmp_path / 'retry.json')


def test_weak_final_labels_are_rejected_and_consumption_survives(tmp_path):
    frozen, predictions = final_fixture(tmp_path, 'weak')
    with pytest.raises(ValueError, match='human-review'):
        final_evaluation(tmp_path, predictions, frozen)
    assert (tmp_path / 'FINAL_EVALUATION_CONSUMED.json').is_file()


@pytest.mark.parametrize('fault', ['order', 'scores', 'duplicate', 'manifest'])
def test_bad_predictions_or_manifest_rejected_before_opening_holdout(tmp_path, fault, monkeypatch):
    frozen, predictions = final_fixture(tmp_path)
    if fault == 'order':
        predictions['label_order'] = list(reversed(LABELS))
    elif fault == 'scores':
        predictions['rows'][0]['scores'][0] = float('nan')
    elif fault == 'duplicate':
        predictions['rows'].append(copy.deepcopy(predictions['rows'][0]))
    else:
        frozen['review_manifest_sha256'] = 'b' * 64
    original = Path.open

    def guarded(path, *args, **kwargs):
        assert path.name != 'holdout.csv'
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', guarded)
    with pytest.raises(ValueError):
        final_evaluation(tmp_path, predictions, frozen)
    assert not (tmp_path / 'FINAL_EVALUATION_CONSUMED.json').exists()


def test_artifact_contract_and_truncation_are_explicit():
    config = SimpleNamespace(id2label=dict(enumerate(LABELS)), label2id={l: i for i, l in enumerate(LABELS)},
        problem_type='multi_label_classification', max_position_embeddings=512)
    assert validate_classifier_config(config)[3] == 'Finance & Bills'
    assert inference_token_limit(config, SimpleNamespace(model_max_length=256)) == 256
    assert inference_token_limit(config, SimpleNamespace(model_max_length=10**30)) == 512
    config.label2id[LABELS[0]] = 9
    with pytest.raises(ValueError, match='mapping'):
        validate_classifier_config(config)


def test_predict_import_is_lazy():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, '-c',
        "import sys,predict; assert predict.model is None and predict.tokenizer is None; "
        "assert 'transformers' not in sys.modules; assert 'torch' not in sys.modules"],
        capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
