import pytest
from showcase.evaluation.run import retrieval_metrics, literal_grounding


def test_retrieval_metrics_use_all_expected_evidence_and_rank_discounts():
    result=retrieval_metrics([8,2,3,1],[1,2])
    assert result['recall@1']==0 and result['recall@3']==.5 and result['recall@5']==1
    assert result['mrr']==.5
    assert 0<result['ndcg@5']<1
    assert retrieval_metrics([1,2],[]) is None


def test_grounding_checker_rejects_missing_sources_and_fabricated_dates():
    rows=[dict(id=1,subject='Fixture',sender='fixture@example.invalid',date='2026-11-08T00:00:00+00:00',body='Meeting date: 2026-11-11')]
    assert literal_grounding('Meeting date: 2026-11-11 [email_id=1]',rows)
    assert not literal_grounding('Meeting date: 2038-01-01 [email_id=1]',rows)
    assert not literal_grounding('Meeting date: 2026-11-11 [email_id=99]',rows)
    assert literal_grounding('Insufficient evidence.',rows) is None
