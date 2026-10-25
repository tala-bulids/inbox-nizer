from datetime import date, datetime, timedelta, timezone

import pytest

from deadline_extractor import extract_deadline, parse_email_datetime
from task_extractor import extract_action_items, extract_tasks


REFERENCE = datetime(2026, 9, 21, 14, 0, tzinfo=timezone(timedelta(hours=3)))


@pytest.mark.parametrize('text, expected', [
    ('Please submit your application by 30 September 2026.', date(2026, 9, 30)),
    ('يرجى سداد الفاتورة قبل 30 سبتمبر 2026.', date(2026, 9, 30)),
    ('ادفع الفاتورة قبل ٣٠ سبتمبر ٢٠٢٦.', date(2026, 9, 30)),
    ('Submit it by Friday.', date(2026, 9, 25)),
    ('أرسل المستند قبل الجمعة.', date(2026, 9, 25)),
    ('أرسل المستند غدًا.', date(2026, 9, 22)),
    ('Pay your invoice due on October 4.', date(2026, 10, 4)),
    ('Pay your invoice due by October 4.', date(2026, 10, 4)),
    ('Submit the form no later than October 4.', date(2026, 10, 4)),
    ('Submit the form; deadline is October 4.', date(2026, 10, 4)),
    ('أرسل المستند، الموعد النهائي 30 سبتمبر.', date(2026, 9, 30)),
    ('الدفع مستحق في 30 سبتمبر.', date(2026, 9, 30)),
    ('سدد المبلغ المستحق قبل نهاية الشهر.', date(2026, 9, 30)),
    ('Pay your invoice by the end of the month.', date(2026, 9, 30)),
    ('Submit the document before 2026-10-16.', date(2026, 10, 16)),
    ('Submit the document by 16-Oct-2026.', date(2026, 10, 16)),
    ('Submit it before January 2.', date(2027, 1, 2)),
])
def test_calendar_dates(text, expected):
    result = extract_deadline(text, REFERENCE)
    assert result is not None
    assert result['deadline_date'] == expected
    assert result['deadline_at'] is None
    assert result['confidence'] == 0.9


@pytest.mark.parametrize('text', ['Reply tomorrow at 10 AM.', 'يرجى إرسال المستند غداً الساعة 10 صباحاً.'])
def test_real_time_preserves_timezone(text):
    result = extract_deadline(text, REFERENCE)
    assert result['deadline_at'] == REFERENCE.replace(day=22, hour=10)
    assert result['deadline_at'].utcoffset() == timedelta(hours=3)
    assert result['deadline_date'] is None


@pytest.mark.parametrize('text, hour', [
    ('Reply tomorrow at 12 AM.', 0), ('Reply tomorrow at 12 PM.', 12),
    ('Reply tomorrow at 10 PM.', 22), ('أرسل المستند غداً الساعة 10 مساءً.', 22),
    ('Reply tomorrow at 16:30.', 16),
])
def test_clock_formats(text, hour):
    assert extract_deadline(text, REFERENCE)['deadline_at'].hour == hour


@pytest.mark.parametrize('text, phrase', [
    ('Issue the boarding pass before arriving at the airport.', 'before arriving at the airport'),
    ('أصدر بطاقة الصعود قبل الوصول إلى المطار.', 'قبل الوصول إلى المطار'),
    ('Review the document before the meeting.', 'before the meeting'),
    ('أرسل المستند قبل الاجتماع.', 'قبل الاجتماع'),
])
def test_non_calendar_constraints(text, phrase):
    result = extract_deadline(text, REFERENCE)
    assert result['deadline_text'] == phrase
    assert result['deadline_date'] is result['deadline_at'] is None


@pytest.mark.parametrize('text', [
    'The company was founded in 2019.', 'Travel date: 16-Oct-2026.',
    'Sale ends October 4.', 'Our event happened last Friday.',
    'Please review the report. Travel date: 16-Oct-2026.',
    'Shop now before October 4.', 'رفع كفاءة الأداء المؤسسي قبل الجمعة.',
    "Review tomorrow's report.", 'Review today’s report.',
])
def test_unrelated_dates_are_not_deadlines(text):
    assert extract_deadline(text, REFERENCE) is None


@pytest.mark.parametrize('text', ['Reply tomorrow.', 'Submit it by Friday.', 'Pay your invoice before 30 September.'])
def test_missing_reference_does_not_use_system_clock(text):
    result = extract_deadline(text)
    assert result['deadline_text']
    assert result['deadline_date'] is result['deadline_at'] is None


def test_absolute_date_without_reference_and_explicit_timezone():
    assert extract_deadline('Submit the form by 30 September 2026.')['deadline_date'] == date(2026, 9, 30)
    result = extract_deadline('Submit the form by 30 September 2026 at 10 AM UTC.')
    assert result['deadline_at'] == datetime(2026, 9, 30, 10, tzinfo=timezone.utc)


@pytest.mark.parametrize('text', ['Reply tomorrow at 25:00.', 'Reply tomorrow at 13 PM.'])
def test_invalid_time_is_not_invented(text):
    result = extract_deadline(text, REFERENCE)
    assert result['deadline_at'] is None
    assert result['deadline_text']


def test_invalid_date_remains_text():
    result = extract_deadline('Submit the form by 31 February 2026.', REFERENCE)
    assert result['deadline_date'] is result['deadline_at'] is None


def test_naive_reference_does_not_assume_timezone():
    result = extract_deadline('Reply tomorrow at 10 AM.', REFERENCE.replace(tzinfo=None))
    assert result['deadline_at'] is None
    assert result['deadline_date'] == date(2026, 9, 22)


def test_header_parser():
    assert parse_email_datetime('Mon, 21 Sep 2026 14:00:00 +0300') == REFERENCE
    assert parse_email_datetime('bad date') is None
    assert parse_email_datetime(None) is None
    assert parse_email_datetime('Mon, 21 Sep 2026 14:00:00 -0000').tzinfo is None


def test_original_arabic_wording_and_wrapper_compatibility():
    text = 'يرجى إرسال المستند غدًا.'
    items = extract_action_items('', text, REFERENCE)
    assert items[0]['deadline_text'] == 'غدًا'
    assert extract_tasks('', text) == [{key: item[key] for key in ('task', 'confidence')} for item in items]


@pytest.mark.parametrize('text', [
    'Raise organizational efficiency.', 'Improve your health.',
    'Register now and unlock premium benefits.', 'رفع معدل الحرق', 'رفع كفاءة الأداء المؤسسي',
    'عروض حصرية.\nسجّل الآن',
    'Register now and unlock premium benefits before Friday.',
    'سجّل الآن قبل الجمعة',
])
def test_benefits_and_registration_ads(text):
    assert extract_action_items('', text, REFERENCE) == []


@pytest.mark.parametrize('text', [
    'Please upload the requested ID.', 'Submit your application before Friday.',
    'Pay your invoice.', 'يرجى إرسال المستند المطلوب.',
    'سدد المبلغ المستحق قبل نهاية الشهر.', 'أصدر بطاقة الصعود قبل الوصول إلى المطار.',
    'You must register now for mandatory training.', 'Registration is required. Register now.',
])
def test_real_obligations(text):
    assert len(extract_action_items('', text, REFERENCE)) == 1


@pytest.mark.parametrize('reverse', [False, True])
def test_semantic_dedup_prefers_deadline(reverse):
    candidates = ['يرجى إصدار بطاقة الصعود إلكترونياً قبل الوصول إلى المطار.', 'إصدار بطاقة صعود الطائرة.']
    if reverse:
        candidates.reverse()
    items = extract_action_items('', '\n'.join(candidates), REFERENCE)
    assert len(items) == 1
    assert items[0]['deadline_text'] == 'قبل الوصول إلى المطار'


@pytest.mark.parametrize('body', [
    'Upload the passport. Upload the application.',
    'Reply to the customer. Pay the invoice.',
    'Review document 1. Review document 2.',
    'Submit the form by Friday. Submit the form by Monday.',
    'Send the contract to Ali. Send the contract to Ahmed.',
])
def test_distinct_tasks_stay_distinct(body):
    assert len(extract_tasks('', body)) == 2


def test_mixed_marketing_keeps_one_obligation():
    body = 'Register now and unlock premium benefits.\nرفع معدل الحرق\nShop now.\nPlease upload your ID by Friday.'
    items = extract_action_items('', body, REFERENCE)
    assert len(items) == 1
    assert items[0]['deadline_date'] == date(2026, 9, 25)
