"""Whole-action and deadline-association regressions; synthetic development data."""
import pytest
from quality.task_acceptance import CASES, REFERENCE
from task_extractor import extract_action_items


@pytest.mark.parametrize('name,body,expected',CASES,ids=[row[0] for row in CASES])
def test_task_and_deadline_association(name,body,expected):
    items=extract_action_items('',body,REFERENCE)
    assert len(items)==len(expected)
    remaining=list(items)
    for fragment,deadline in expected:
        item=next((item for item in remaining if fragment.casefold() in item['task'].casefold()),None)
        assert item is not None
        assert item['deadline_text']==deadline
        remaining.remove(item)
