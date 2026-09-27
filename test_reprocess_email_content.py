from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy import select

import reprocess_email_content as maintenance
from models import Email, EmailPrediction, EmailTask


def _session(monkeypatch, db):
    session = MagicMock(wraps=db)
    session.close = Mock()
    monkeypatch.setattr(maintenance, 'SessionLocal', lambda: session)
    return session


def _email(message_id, body):
    email = Email(message_id=message_id, sender='sender@example.com', subject='Application',
                  email_date='Fri, 25 Sep 2026 10:00:00 +0300', body=body, summary='Old footer summary',
                  priority_score=0.73, priority_level='high')
    email.predictions = [EmailPrediction(category='Business', confidence=0.83)]
    email.tasks = [EmailTask(task='Send email to info@example.com', confidence=0.8)]
    return email


def _identity(email):
    return (email.id, email.message_id, email.subject, email.sender, email.email_date,
            email.created_at, email.priority_score, email.priority_level,
            [(p.id, p.category, p.confidence) for p in email.predictions])


def test_reprocess_updates_content_and_preserves_metadata(monkeypatch, test_database, capsys):
    main = 'Please submit your application.'
    email = _email('reprocess-main', main + '\n\nRegards,\nA Person\ninfo@example.com')
    test_database.add(email)
    test_database.commit()
    before = _identity(email)
    session = _session(monkeypatch, test_database)
    summary = Mock(wraps=maintenance.summarize_email)
    monkeypatch.setattr(maintenance, 'summarize_email', summary)
    maintenance.reprocess_email_content()
    test_database.expire_all()
    assert _identity(email) == before
    assert email.body == email.summary == main
    assert [t.task for t in email.tasks] == ['Submit your application']
    summary.assert_called_once_with('Application', main)
    assert capsys.readouterr().out == 'Processed 1 emails\nCleaned 1 bodies\nRegenerated 1 tasks\n'
    # A second run may regenerate the same task without a uniqueness conflict.
    maintenance.reprocess_email_content()
    assert 'Cleaned 0 bodies' in capsys.readouterr().out
    assert test_database.query(EmailTask).count() == 1
    assert test_database.query(EmailPrediction).count() == 1
    assert session.close.call_count == 2


def test_reprocess_whitespace_and_empty_bodies(monkeypatch, test_database, capsys):
    whitespace = _email('space', 'Please  submit your application.  ')
    empty = _email('empty', None)
    test_database.add_all([whitespace, empty])
    test_database.commit()
    _session(monkeypatch, test_database)
    maintenance.reprocess_email_content()
    test_database.expire_all()
    assert whitespace.body == 'Please  submit your application.  '
    assert empty.body is None
    assert empty.summary == 'Application'
    assert empty.tasks == []
    assert len(whitespace.tasks) == 1
    assert test_database.query(EmailPrediction).count() == 2
    assert capsys.readouterr().out == 'Processed 2 emails\nCleaned 0 bodies\nRegenerated 1 tasks\n'


@pytest.mark.parametrize('stage', ['clean_email_text', 'summarize_email', 'extract_action_items', 'commit'])
def test_reprocess_failure_is_atomic(monkeypatch, test_database, capsys, stage):
    for number in range(2):
        test_database.add(_email(f'rollback-{number}', 'Please submit your application.\nRegards,\nA Person'))
    test_database.commit()
    emails = test_database.scalars(select(Email).order_by(Email.id)).all()
    before = [(e.body, e.summary, _identity(e), [(t.id, t.task) for t in e.tasks]) for e in emails]
    session = _session(monkeypatch, test_database)
    if stage == 'commit':
        session.commit.side_effect = RuntimeError('test failure')
    else:
        original = getattr(maintenance, stage)
        calls = 0
        def fail_second(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError('test failure')
            return original(*args)
        monkeypatch.setattr(maintenance, stage, fail_second)
    with pytest.raises(RuntimeError, match='test failure'):
        maintenance.reprocess_email_content()
    session.rollback.assert_called_once()
    session.close.assert_called_once()
    test_database.expire_all()
    after = [(e.body, e.summary, _identity(e), [(t.id, t.task) for t in e.tasks]) for e in emails]
    assert after == before
    assert capsys.readouterr().out == ''
