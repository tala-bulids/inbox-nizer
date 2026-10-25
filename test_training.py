import numpy as np
from app import prepare_rows, split_rows, score_predictions


def test_conflicting_duplicates_are_quarantined_and_groups_cannot_cross_splits():
    rows = prepare_rows([
        {'subject': 'Hello', 'body': '<p>World</p>', 'labels': ['Business']},
        {'subject': 'hello', 'body': 'World', 'labels': ['Personal']},
    ])
    assert rows == []
    import pytest
    with pytest.raises(ValueError,match='independent groups'):
        split_rows([{'text': str(i), 'labels': {'Business'}} for i in range(30)])
    rows = [{'text': word, 'labels': {'Business'}} for word in
            ('invoice','holiday','penguin','university','calendar','ticket','signature','password','volcano','telescope')]
    train, validation, test = split_rows(rows)
    groups = [set(row['text'] for row in split) for split in (train, validation, test)]
    assert not groups[0] & groups[1]
    assert not groups[0] & groups[2]
    assert not groups[1] & groups[2]
    assert split_rows(rows) == (train, validation, test)


def test_top1_accepts_any_correct_label():
    targets = np.zeros((2, 10))
    targets[0, [0, 1]] = 1
    targets[1, 2] = 1
    logits = np.full((2, 10), -3.0)
    logits[0, 1] = 2
    logits[1, 3] = 2
    metrics = score_predictions(logits, targets)
    assert metrics['top1_accuracy'] == 0.5
    assert metrics['per_label_f1']['Customer Support'] == 1.0
