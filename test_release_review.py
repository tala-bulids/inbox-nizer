import csv
import json
import pytest
from quality.release_review import task_metrics, ask_metrics, evaluate, digest


def human(**kwargs):
    return dict(reviewer='test reviewer', label_source='human_reviewed', reviewed_at='2026-10-17', **kwargs)


def test_unreviewed_rows_never_become_accuracy():
    for score in (task_metrics, ask_metrics):
        result = score([{}])
        assert result['reviewed'] == 0 and result['pending'] == 1
    assert task_metrics([{}])['precision'] is None
    assert ask_metrics([{}])['answer_accuracy'] is None


def test_task_counts_include_missed_actions_and_wrong_associations():
    row = human(ambiguous='no', predicted_tasks=json.dumps([{'task':'A','deadline_text':'Friday'}, {'task':'B'}]),
        gold_task_count='2', correct_task_indices='[2]', gold_deadline_count='1', correct_deadline_indices='[]')
    result = task_metrics([row])
    assert (result['tp'],result['fp'],result['fn']) == (1,1,1)
    assert result['deadline_precision'] == result['deadline_recall'] == 0
    row['correct_deadline_indices']='[1]'
    with pytest.raises(ValueError): task_metrics([row])


def test_ask_counts_abstention_separately_from_wrong_answer():
    rows = [human(status='insufficient_evidence', answerable='yes', answer_correct='no', source_correct='no',
                  citation_correct='no', unsupported_factual_answer='no'),
            human(status='answered', answerable='yes', answer_correct='yes', source_correct='yes',
                  citation_correct='yes', unsupported_factual_answer='no')]
    result = ask_metrics(rows)
    assert result['false_abstention_rate'] == .5 and result['source_accuracy'] == 1
    assert result['answer_accuracy'] == .5


def test_final_requires_freeze_and_cannot_be_reused(tmp_path):
    path=tmp_path/'ask-holdout.csv'
    row=human(status='insufficient_evidence', answerable='no', answer_correct='yes', source_correct='no',
              citation_correct='no', unsupported_factual_answer='no')
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(row));writer.writeheader();writer.writerow(row)
    with pytest.raises(ValueError):evaluate(path,'ask')
    with pytest.raises(ValueError):evaluate(path,'ask',final=True)
    freeze=tmp_path/'freeze.json'
    freeze.write_text(json.dumps(dict(selection_complete=True,holdout_used_for_selection=False,
                                    review_sha256=digest(path),artifact_sha256='a'*64)))
    assert evaluate(path,'ask',final=True,freeze=freeze)['metrics']['reviewed']==1
    with pytest.raises(FileExistsError):evaluate(path,'ask',final=True,freeze=freeze)
