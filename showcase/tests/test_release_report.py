import copy
import json
from pathlib import Path

import pytest
from showcase.release_report import parity, summarize

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    return {'evaluation': {'collection_version': 'fixture', 'query_token_ids': [[1,2]],
        'query_vectors': [[1.,0.]], 'document_vectors': [[0.,1.]],
        'qa': {'retrieval': {'mrr': 1.}},
        'cases': [{'id':'q1','ranked_top10':[1,2],'cited':[1],'status':'answered'}]}}


def test_comparison_reports_quality_regressions_without_inventing_approval():
    baseline = fixture(); changed = copy.deepcopy(baseline)
    changed['evaluation']['qa']['retrieval']['mrr'] = .5
    changed['evaluation']['cases'][0].update(ranked_top10=[2,1], cited=[2])
    result = parity(baseline, changed)
    assert result['retrieval_metric_deltas']['mrr'] == -.5
    assert result['changed_top10_order'] == result['changed_citation_sets'] == ['q1']
    assert 'approved' not in result


@pytest.mark.parametrize('field,value', [('collection_version','different'), ('query_vectors', [[0.,0.]])])
def test_incompatible_comparison_rejected(field,value):
    original=fixture(); changed=copy.deepcopy(original)
    changed['evaluation'][field]=value
    with pytest.raises(ValueError): parity(original,changed)


def test_mocked_or_incomplete_receipt_cannot_become_measured_evidence(tmp_path):
    path=tmp_path/'receipt.json'
    path.write_text(json.dumps({'status':'failed','real_inference':True,'mocked_inference':False}))
    with pytest.raises(ValueError): summarize([path])


def test_committed_report_retains_regression_and_target_host_limitations():
    report=json.loads((ROOT/'docs/phase5/capacity-comparison.json').read_text(encoding='utf-8'))
    assert not report['target_host_verified'] and not report['production_approved']
    quant=report['parity_against_first']['onnx-int8']
    assert quant['retrieval_metric_deltas']['mrr'] < 0
    assert not quant['changed_citation_sets']
    assert all('query_vectors' not in r['evaluation'] for r in report['runs'])
