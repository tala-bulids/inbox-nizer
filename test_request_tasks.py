from datetime import date, datetime, timezone

import pytest

from task_extractor import extract_tasks, extract_action_items


REFERENCE = datetime(2026, 9, 16, 10, 9, tzinfo=timezone.utc)
REQUEST = ('لاستكمال ترشيحك، نأمل التسجيل عبر الرابط أدناه في أقرب وقت، '
           'تنويه اخر يوم للتسجيل يوم الثلاثاء الموافق ٢٢ سبتمبر: رابط التسجيل (https://example.org/register)')
BODY = ('فرصتك تبدأ أبكر!\n\nنظرًا لتسجيلك مسبقًا في دفعة شهر ديسمبر، '
        'تم ترشيحك للدفعة الجديدة خلال شهر أكتوبر.\n\n' + REQUEST + '\n\nنتطلع لانضمامك معنا.')


def test_nomination_registration_request_and_explicit_deadline():
    items = extract_action_items('إشعار هام - دفعة جديدة', BODY, REFERENCE)
    assert len(items) == 1
    assert items[0]['task'].startswith('التسجيل عبر الرابط')
    assert items[0]['deadline_date'] == date(2026, 9, 22)
    assert '٢٢ سبتمبر' in items[0]['deadline_text']


@pytest.mark.parametrize('text,action', [
    ('نأمل إرسال المستند قبل الخميس.', 'إرسال المستند'),
    ('نرجو تأكيد الحضور قبل الخميس.', 'تأكيد الحضور'),
    ('نرجو منكم رفع المستند قبل الخميس.', 'رفع المستند'),
    ('نأمل منك إكمال التسجيل قبل الخميس.', 'إكمال التسجيل'),
    ('لاستكمال طلبك، يرجى دفع الفاتورة قبل الخميس.', 'دفع الفاتورة'),
    ('لإتمام الحجز، نرجو تأكيد الحضور قبل الخميس.', 'تأكيد الحضور'),
    ('To complete your application, please upload your document by Friday.', 'Upload your document'),
    ('We ask you to submit your application by Friday.', 'Submit your application'),
])
def test_polite_requests_and_purpose_prefixes(text, action):
    items = extract_tasks('', text)
    assert len(items) == 1 and items[0]['task'].startswith(action)


@pytest.mark.parametrize('text', [
    'نأمل أن تكون بخير.', 'نرجو لك التوفيق.', 'تم التسجيل بنجاح.',
    'لا نأمل التسجيل في هذه الدورة.', 'نأمل عدم إرسال المستند.',
    'نأمل التسجيل الآن للحصول على عروض حصرية.',
    'لاستكمال العرض، تسوق الآن وادفع بعدين.',
    'We hope you enjoy our newsletter.', 'We ask you to shop now.',
    'To complete your application, do not upload the document.',
])
def test_wishes_negation_status_and_marketing_are_not_tasks(text):
    assert extract_tasks('', text) == []


@pytest.mark.parametrize('tail', [
    'اخر يوم للتسجيل يوم الثلاثاء الموافق ٢٢ سبتمبر',
    'آخر موعد للتقديم 22 سبتمبر',
    'الموعد الأخير للرد يوم الثلاثاء الموافق 22 سبتمبر',
])
def test_deadline_notices_on_next_line_attach_to_single_request(tail):
    items = extract_action_items('', 'نأمل إرسال المستند.\n' + tail, REFERENCE)
    assert len(items) == 1 and items[0]['deadline_date'] == date(2026, 9, 22)


def test_explicit_calendar_date_takes_precedence_over_weekday():
    items = extract_action_items('', 'نأمل التسجيل عبر الرابط، آخر يوم للتسجيل يوم الثلاثاء الموافق ٢٩ سبتمبر', REFERENCE)
    assert items[0]['deadline_date'] == date(2026, 9, 29)


def test_new_request_forms_keep_duplicates_and_limit():
    body = '\n'.join(f'نأمل إرسال المستند رقم {i} قبل الخميس.' for i in range(7))
    assert len(extract_tasks('', body + '\n' + body)) == 5


def test_diacritics_and_separate_deadline_after_context():
    body = 'لاستكمال طلبك، نَأْمَل إرسال المستند.\nتنويه آخر يوم للتقديم يوم الثلاثاء الموافق ٢٢ سبتمبر.'
    items = extract_action_items('', body, REFERENCE)
    assert len(items) == 1 and items[0]['task'].startswith('إرسال المستند')
    assert items[0]['deadline_date'] == date(2026, 9, 22)


def test_deadline_is_not_attached_to_two_ambiguous_tasks():
    items = extract_action_items('', 'نأمل إرسال المستند، ونرجو تأكيد الحضور.\nآخر يوم للتقديم ٢٢ سبتمبر.', REFERENCE)
    assert len(items) == 2
    assert all(item['deadline_date'] is None for item in items)
