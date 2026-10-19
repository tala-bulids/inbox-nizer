"""Audit invariants; model-quality claims live in evaluation reports, not assertions."""
import numpy as np
from quality.dataset import LABELS, audit_split
from quality.classification_cases import DEV, FINAL, examples
from quality.metrics import metrics


def test_challenge_partitions_and_label_contract():
    assert len(LABELS)==len(set(LABELS))==10
    assert {r['text'] for r in examples(DEV)}.isdisjoint(r['text'] for r in examples(FINAL))
    assert {l for r in examples(FINAL) for l in r['labels']}==set(LABELS)
    assert {r['language'] for r in examples(FINAL)}=={'ar','en'}


def test_conflicting_labels_are_quarantined_and_groups_cannot_leak():
    raw=[dict(subject='',body=text,labels=[LABELS[i]]) for i,pair in enumerate(FINAL) for text in pair]
    raw += [dict(subject='Collision',body='same body',labels=[label]) for label in LABELS[:2]]
    raw += [dict(subject='',body=FINAL[0][0]+' ',labels=[LABELS[0]])]
    rows,report=audit_split(raw)
    assert report['contradictory_exact_groups']==1 and report['quarantined_rows']==2
    assert not any(r['text'].startswith('Collision') for r in rows)
    groups={}
    for row in rows:
        groups.setdefault(row['group'],set()).add(row['split'])
    assert all(len(partitions)==1 for partitions in groups.values())
    assert rows==audit_split(raw)[0]


def test_top_one_metrics_do_not_report_multilabel_recall_as_perfect():
    scores=np.zeros((2,10));scores[0,0]=.9;scores[1,3]=.95
    result=metrics(scores,[LABELS[:2],['Promotions']])
    assert result['top1_accuracy']==.5
    assert result['finance_false_positives']==1
    assert result['wrong_confident_ge_080']==1
    assert result['per_class']['Customer Support']['recall']==0
    assert result['confusion_matrix'][0][0]==.5
