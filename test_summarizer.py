import socket

import pytest

from summarizer import summarize_email


def test_empty_email():
    assert summarize_email('', '') == ''
    assert summarize_email('  ', '\n\t') == ''


def test_short_email():
    assert summarize_email('Meeting', ' Please attend  the meeting at 10 AM. ') == 'Please attend the meeting at 10 AM.'
    assert summarize_email('  Subject only  ', '') == 'Subject only'


def test_english_email():
    body = 'Dr. Smith will attend the meeting at 10 AM. The budget is 3.5 million dollars. Please bring the final report.'
    assert summarize_email('Meeting', body) == body


def test_arabic_email():
    body = 'يرجى إرسال التقرير قبل يوم الخميس. سيعقد الاجتماع في الساعة العاشرة صباحًا. هل يمكنك تأكيد الحضور؟'
    assert summarize_email('التقرير والاجتماع', body) == body


def test_long_email_selects_relevant_sentences():
    sentences = [
        'The office kitchen has new coffee cups.',
        'The garden flowers need water every morning.',
        'The invoice payment deadline is Friday afternoon.',
        'The invoice must include the updated billing address.',
        'Please confirm the invoice payment before the deadline.',
        'The library has several novels on its shelves.',
    ]
    summary = summarize_email('Invoice payment deadline', ' '.join(sentences))
    assert sentences[2] in summary
    assert sentences[4] in summary
    assert sentences[0] not in summary
    assert sum(sentence in summary for sentence in sentences) <= 3
    assert all(part + '.' in sentences for part in summary[:-1].split('. '))
    assert summary.index(sentences[2]) < summary.index(sentences[4])


def test_subject_changes_selection():
    sentences = [
        'The garden flowers need fresh water daily.',
        'The office kitchen provides coffee every morning.',
        'The public library offers new novels weekly.',
        'The invoice payment requires approval before Friday.',
    ]
    body = ' '.join(sentences)
    assert sentences[3] in summarize_email('Invoice payment approval', body)
    assert sentences[3] not in summarize_email('Garden flowers water', body)


def test_footer_is_ignored():
    body = 'Please approve the invoice payment today.\nUnsubscribe from invoice payment offers.\nPrivacy Policy invoice payment.\nجميع الحقوق محفوظة.'
    assert summarize_email('Invoice', body) == 'Please approve the invoice payment today.'


def test_tiny_and_duplicate_sentences_are_ignored():
    body = 'Hi.\nThanks.\nPlease send the final report before Friday.\nPlease send the final report before Friday.\nThe review meeting starts on Monday morning.\nBring the supporting documents to the meeting.'
    result = summarize_email('Report meeting', body)
    assert 'Hi.' not in result
    assert 'Thanks.' not in result
    assert result.count('Please send the final report before Friday.') == 1


def test_arabic_subject_keywords():
    sentences = [
        'تتوفر القهوة في المطبخ كل صباح.',
        'تحتاج الحديقة إلى الري في الصباح.',
        'توجد كتب جديدة في المكتبة العامة.',
        'يرجى إرسال تقرير الميزانية قبل الخميس.',
    ]
    assert sentences[3] in summarize_email('تقرير الميزانية', ' '.join(sentences))


def test_no_network(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Summarization must not use the network')
    monkeypatch.setattr(socket, 'socket', blocked)
    assert summarize_email('Reminder', 'Please send the report today.') == 'Please send the report today.'
