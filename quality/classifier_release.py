"""Local classifier evidence gate. Never trains, activates, or changes a mailbox.

Status mode does not open holdout.csv. Final mode requires frozen model identity,
human review attestations and an exclusive consumption receipt. No email content
or reviewer identity is copied into reports.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from classifier_contract import LABELS
from quality.metrics import metrics


POLICY = {
    'version': 'classifier-release-v1',
    'note': 'Conservative engineering acceptance criteria; diagnostic sets cannot establish public readiness.',
    'minimum_examples': 300,
    'minimum_per_class': 20,
    'minimum_per_language': 50,
    'minimum_accuracy': .9,
    'minimum_macro_f1': .85,
    'minimum_class_precision': .8,
    'minimum_class_recall': .7,
    'minimum_finance_precision': .95,
    'maximum_finance_false_positive_rate': .02,
    'maximum_wrong_confident_rate': .02,
    'maximum_ece': .1,
    'maximum_language_accuracy_gap': .05,
    'maximum_ambiguous_fraction': .05,
}


def valid_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def number(value, minimum=0, maximum=1, integer=False):
    return (type(value) in (int, float) and math.isfinite(value)
            and minimum <= value <= maximum and (not integer or int(value) == value))


def text_field(row, key):
    return str(row.get(key) or '').strip()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def review_metadata(rows):
    """Validate reviewer attestation, without returning labels or private content."""
    counts = Counter(total=0, human_reviewed=0, ambiguous=0, weak=0, pending=0, invalid=0)
    seen = set()
    for row in rows:
        counts['total'] += 1
        identity = text_field(row, 'email_id')
        if not identity or identity in seen:
            counts['invalid'] += 1
            continue
        seen.add(identity)
        label = text_field(row, 'gold_label')
        source = text_field(row, 'label_source')
        ambiguous = text_field(row, 'ambiguous').lower()
        if source == 'weak':
            counts['weak'] += 1
            continue
        if not label and ambiguous not in {'yes', 'true', '1'}:
            counts['pending'] += 1
            continue
        try:
            reviewed_date = date.fromisoformat(text_field(row, 'reviewed_at'))
            valid_date = reviewed_date <= datetime.now(timezone.utc).date()
        except ValueError:
            valid_date = False
        if (source != 'human_reviewed' or not text_field(row, 'reviewer') or not valid_date
                or ambiguous not in {'', 'no', 'false', '0', 'yes', 'true', '1'}):
            counts['invalid'] += 1
        elif ambiguous in {'yes', 'true', '1'}:
            counts['ambiguous'] += 1
        elif label not in LABELS:
            counts['invalid'] += 1
        else:
            counts['human_reviewed'] += 1
    return dict(counts)


def review_status(directory):
    if directory is None or not Path(directory).is_dir():
        return {'available': False, 'human_reviewed': None, 'holdout_opened': False,
                'reason': 'No local review directory was supplied/found; missing evidence is not zero labels.'}
    directory = Path(directory)
    development = directory / 'development.csv'
    status = {'available': True, 'holdout_opened': False, 'holdout_present': (directory/'holdout.csv').is_file()}
    if development.is_file():
        with development.open(encoding='utf-8-sig', newline='') as stream:
            status['development'] = review_metadata(csv.DictReader(stream))
    return status


def assess_release(evaluation, artifact_sha256=None):
    failures = []
    if not evaluation:
        failures.append('Representative human-reviewed final holdout evaluation is missing.')
    elif not isinstance(evaluation, dict):
        failures.append('Evaluation must be a structured evidence report.')
    else:
        provenance = evaluation.get('provenance', {})
        if not isinstance(provenance, dict):
            provenance = {}
        for key, expected in [('label_source', 'human_reviewed_mailbox'), ('partition', 'holdout'),
                              ('used_for_selection', False), ('representative', True),
                              ('all_rows_reviewed', True), ('one_time_evaluation', True)]:
            if (type(provenance.get(key)) is not type(expected) or provenance.get(key) != expected):
                failures.append('Required evidence provenance is missing or invalid: ' + key)
        for key in ('artifact_sha256', 'review_manifest_sha256', 'review_labels_sha256', 'review_policy_sha256', 'predictions_sha256'):
            value = provenance.get(key, '')
            if not valid_hash(value):
                failures.append('Missing immutable evidence hash: ' + key)
        if artifact_sha256 and provenance.get('artifact_sha256') != artifact_sha256:
            failures.append('Evaluated artifact does not match the artifact being assessed.')
        measured = evaluation.get('metrics', {})
        if not isinstance(measured, dict):
            measured = {}

        def minimum(key, threshold, count=False):
            value = measured.get(key)
            if not number(value, threshold, math.inf if count else 1, integer=count):
                failures.append(f'{key} must be at least {threshold}.')

        def maximum(key, threshold):
            value = measured.get(key)
            if not number(value, 0, threshold):
                failures.append(f'{key} must be at most {threshold}.')

        minimum('n', POLICY['minimum_examples'], count=True)
        minimum('top1_accuracy', POLICY['minimum_accuracy'])
        minimum('top1_macro_f1', POLICY['minimum_macro_f1'])
        maximum('finance_false_positive_rate', POLICY['maximum_finance_false_positive_rate'])
        maximum('top1_ece', POLICY['maximum_ece'])
        maximum('wrong_confident_rate', POLICY['maximum_wrong_confident_rate'])
        per_class = measured.get('per_class', {})
        if not isinstance(per_class, dict):
            per_class = {}
        for label in LABELS:
            entry = per_class.get(label, {})
            if not isinstance(entry, dict):
                entry = {}
            for key, bound in [('support', POLICY['minimum_per_class']),
                               ('precision', POLICY['minimum_class_precision']), ('recall', POLICY['minimum_class_recall'])]:
                value = entry.get(key)
                if not number(value, bound, measured.get('n', 0) if key == 'support' and number(measured.get('n'), 0, math.inf) else 1, integer=key == 'support'):
                    failures.append(f'{label}: insufficient {key} (requires {bound}).')
        finance = per_class.get('Finance & Bills', {})
        finance_precision = finance.get('precision') if isinstance(finance, dict) else None
        if not number(finance_precision, POLICY['minimum_finance_precision'], 1):
            failures.append('Finance precision must be at least .95.')
        language = evaluation.get('by_language', {})
        if not isinstance(language, dict):
            language = {}
        valid_languages = {}
        for name in ('ar', 'en'):
            entry = language.get(name, {})
            if not isinstance(entry, dict):
                entry = {}
            if (not number(entry.get('n'), POLICY['minimum_per_language'], measured.get('n', 0) if number(measured.get('n'), 0, math.inf) else 0, integer=True)
                    or not number(entry.get('top1_accuracy'), POLICY['minimum_accuracy'], 1)):
                failures.append(name + ': insufficient representative coverage or accuracy.')
            else:
                valid_languages[name] = entry
        if len(valid_languages) == 2:
            if abs(valid_languages['ar']['top1_accuracy']-valid_languages['en']['top1_accuracy']) > POLICY['maximum_language_accuracy_gap']:
                failures.append('Arabic/English accuracy gap exceeds .05.')
            if sum(entry['n'] for entry in valid_languages.values()) > measured['n']:
                failures.append('Language partitions cannot exceed the evaluated sample size.')
        counts = evaluation.get('review_counts', {})
        if not isinstance(counts, dict):
            counts = {}
        total, ambiguous, reviewed = (counts.get(key) for key in ('total', 'ambiguous', 'human_reviewed'))
        if (not number(total, 1, math.inf, integer=True) or not number(ambiguous, 0, total if number(total, 0, math.inf) else 0, integer=True)
                or reviewed != measured.get('n') or type(reviewed) is not int
                or total != reviewed + ambiguous
                or any(counts.get(key) != 0 for key in ('invalid', 'pending', 'weak'))):
            failures.append('Review counts must reconcile to the complete final sample without unreviewed or weak labels.')
        elif ambiguous / total > POLICY['maximum_ambiguous_fraction']:
            failures.append('Too many ambiguous examples were excluded from final accuracy.')
    return {'passed': not failures, 'rating': 'A' if not failures else 'C',
            'blockers': failures, 'policy': POLICY, 'production_activation_authorized': False}


def final_evaluation(directory, predictions, frozen, receipt=None):
    """Evaluate supplied frozen-candidate scores once; predictions contain no gold.

    A frozen descriptor is written during selection with artifact_sha256 and
    used_for_selection=False. The review-policy describes the sampling design.
    This function cannot prove a human attestation truthful; it refuses weak or
    unlabeled rows and preserves that provenance limitation explicitly.
    """
    directory = Path(directory)
    canonical_receipt = directory/'FINAL_EVALUATION_CONSUMED.json'
    if receipt is not None and Path(receipt).resolve() != canonical_receipt.resolve():
        raise ValueError('The consumption receipt must remain in the reviewed dataset directory.')
    receipt = canonical_receipt
    if not isinstance(frozen, dict) or not isinstance(predictions, dict):
        raise ValueError('Candidate and predictions must be structured descriptors.')
    artifact_hash = frozen.get('artifact_sha256', '')
    if (not valid_hash(artifact_hash)
            or frozen.get('holdout_used_for_selection') is not False
            or predictions.get('artifact_sha256') != artifact_hash):
        raise ValueError('A frozen candidate hash and matching predictions are required before final evaluation.')
    if predictions.get('label_order') != LABELS:
        raise ValueError('Predictions must declare the exact category score order.')
    policy_path = directory/'review-policy.json'
    policy = json.loads(policy_path.read_text(encoding='utf-8'))
    if policy.get('holdout_used_for_selection') is not False:
        raise ValueError('Consumed development data cannot become a release holdout.')
    manifest_path = directory/'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if (frozen.get('review_manifest_sha256') != sha256_file(manifest_path)
            or frozen.get('review_policy_sha256') != sha256_file(policy_path)):
        raise ValueError('Freeze the exact review manifest and sampling policy before final evaluation.')
    groups = {}
    all_ids = set()
    for row in manifest:
        identity = text_field(row, 'email_id')
        if (not identity or identity in all_ids or not text_field(row, 'group')
                or row.get('split') not in {'development', 'holdout'}
                or row.get('language') not in {'ar', 'en', 'mixed', 'other'}):
            raise ValueError('Review manifest identities, groups, partitions and languages must be valid.')
        all_ids.add(identity)
        groups.setdefault(row['group'], set()).add(row['split'])
    if any(len(splits) != 1 for splits in groups.values()):
        raise ValueError('Review groups cross development and holdout partitions.')
    expected = {text_field(row, 'email_id'): row for row in manifest if row['split'] == 'holdout'}
    if len(expected) != sum(row['split'] == 'holdout' for row in manifest) or not expected:
        raise ValueError('Holdout manifest must contain unique identities.')
    scores = predictions.get('rows', [])
    by_id = {text_field(row, 'email_id'): row['scores'] for row in scores}
    if len(by_id) != len(scores) or set(by_id) != set(expected):
        raise ValueError('Predictions must cover the frozen holdout exactly once.')
    # Validate the complete score matrix before consuming any labels, including
    # examples that a reviewer may ultimately consider ambiguous.
    metrics(list(by_id.values()), [[LABELS[0]]] * len(by_id))
    predictions_hash = hashlib.sha256(json.dumps(predictions, sort_keys=True, allow_nan=False).encode()).hexdigest()
    # The exclusive marker survives errors: failed final evaluation never opens
    # a quiet path to tuning and retrying on the same labels.
    with receipt.open('x', encoding='utf-8') as stream:
        json.dump({'artifact_sha256': artifact_hash, 'started_at': datetime.now(timezone.utc).isoformat(),
                   'status': 'consumed', 'review_manifest_sha256': sha256_file(manifest_path),
                   'predictions_sha256': predictions_hash}, stream, indent=2)
    with (directory/'holdout.csv').open(encoding='utf-8-sig', newline='') as stream:
        reviewed = list(csv.DictReader(stream))
    metadata = review_metadata(reviewed)
    if metadata['invalid'] or metadata['pending'] or metadata['weak']:
        raise ValueError('Every holdout row needs a genuine human-review attestation; weak/unreviewed labels cannot be evaluated as gold.')
    if {text_field(row, 'email_id') for row in reviewed} != set(expected):
        raise ValueError('Reviewed identities differ from the frozen holdout manifest.')
    usable = [row for row in reviewed if text_field(row, 'ambiguous').lower() not in {'yes', 'true', '1'}]
    if not usable:
        raise ValueError('All reviewed examples are ambiguous; no final accuracy can be measured.')
    selected_scores = [by_id[text_field(row, 'email_id')] for row in usable]
    labels = [[text_field(row, 'gold_label')] for row in usable]
    measured = metrics(selected_scores, labels)
    measured['wrong_confident_rate'] = measured['wrong_confident_ge_080']/measured['n']
    languages = {}
    for language in ('ar', 'en'):
        indexes = [i for i, row in enumerate(usable) if expected[text_field(row, 'email_id')].get('language') == language]
        if indexes:
            languages[language] = metrics([selected_scores[i] for i in indexes], [labels[i] for i in indexes])
    report = {'metrics': measured, 'by_language': languages, 'review_counts': metadata,
        'provenance': {'label_source': 'human_reviewed_mailbox', 'partition': 'holdout',
            'used_for_selection': False, 'representative': policy.get('representative') is True,
            'sampling': policy.get('sampling'), 'all_rows_reviewed': True, 'one_time_evaluation': True,
            'artifact_sha256': artifact_hash, 'review_manifest_sha256': sha256_file(manifest_path),
            'review_policy_sha256': sha256_file(policy_path), 'predictions_sha256': predictions_hash,
            'review_labels_sha256': sha256_file(directory/'holdout.csv'),
            'limitation': 'Reviewer attestations are validated structurally; the tool cannot independently verify who entered labels.'}}
    report['release_gate'] = assess_release(report, artifact_hash)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-dir', type=Path)
    parser.add_argument('--artifact', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--final-predictions', type=Path)
    parser.add_argument('--frozen-candidate', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; evidence reports are immutable.')
    if bool(args.final_predictions) != bool(args.frozen_candidate):
        parser.error('Final evaluation requires both predictions and a frozen candidate descriptor.')
    if args.final_predictions:
        if not args.review_dir:
            parser.error('Final evaluation requires --review-dir.')
        result = final_evaluation(args.review_dir,
            json.loads(args.final_predictions.read_text(encoding='utf-8')),
            json.loads(args.frozen_candidate.read_text(encoding='utf-8')),
            args.review_dir/'FINAL_EVALUATION_CONSUMED.json')
    else:
        result = {'review_status': review_status(args.review_dir), 'release_gate': assess_release(None)}
    if args.artifact:
        result['current_artifact_sha256'] = sha256_file(args.artifact)
        if 'metrics' in result:
            result['release_gate'] = assess_release(result, result['current_artifact_sha256'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'passed': result['release_gate']['passed'], 'output': str(args.output)}))


if __name__ == '__main__':
    main()
