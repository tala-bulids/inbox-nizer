import socket
import pytest
from task_extractor import extract_tasks


def texts(subject, body):
    return [item['task'] for item in extract_tasks(subject, body)]


def test_empty():
    assert extract_tasks('', '') == []
    assert extract_tasks('  ', '\n') == []


def test_english_action():
    assert texts('Invoice', 'Please pay the invoice before Friday.') == ['Pay the invoice before Friday']
    assert texts('', 'Could you reply to the customer by Monday?') == ['Reply to the customer by Monday']


def test_arabic_action():
    assert texts('فاتورة', 'يرجى سداد الفاتورة قبل الخميس.') == ['سداد الفاتورة قبل الخميس']
    assert texts('', 'الرجاء تأكيد الحجز اليوم.') == ['تأكيد الحجز اليوم']


def test_multiple_actions():
    assert texts('', 'Please review the document and upload the signed copy. Confirm your booking.') == [
        'Review the document', 'Upload the signed copy', 'Confirm your booking'
    ]
    assert texts('', 'يرجى دفع الفاتورة ومراجعة العقد.') == ['دفع الفاتورة', 'مراجعة العقد']


def test_duplicate_suppression():
    assert texts('Pay the invoice', 'Please pay the invoice. PAY THE INVOICE!') == ['Pay the invoice']
    assert texts('Upload the document', 'Please upload the document before Friday.') == ['Upload the document before Friday']


@pytest.mark.parametrize('body', [
    'Discover our latest products and shop now!',
    'Review our latest deals and special offers.',
    'Your payment has been received. Thank you for your purchase.',
    'We will review your application next week.',
    'Please do not submit the application.',
    'لا تقم بإرسال المستند الآن.',
])
def test_no_action(body):
    assert extract_tasks('', body) == []


def test_footer():
    assert texts('', 'Please submit the application today.\nReset your unsubscribe preferences.\nReview our privacy policy.') == ['Submit the application today']
    assert extract_tasks('', 'يرجى مراجعة سياسة الخصوصية.') == []


def test_maximum_five():
    result = extract_tasks('', '\n'.join(f'Please review document number {i}.' for i in range(10)))
    assert len(result) == 5
    assert all(0 <= task['confidence'] <= 1 for task in result)


@pytest.mark.parametrize('action', [
    'Issue boarding pass', 'Attend the meeting', 'Complete registration',
    'Submit your application', 'Reset your password', 'Respond before Friday',
])
def test_supported_actions(action):
    assert texts('', action + '.') == [action]


def test_network_not_needed(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Task extraction must not use the network')
    monkeypatch.setattr(socket, 'socket', blocked)
    assert texts('', 'Upload your document.') == ['Upload your document']


def test_long_passage_does_not_become_a_task():
    body = 'Please review ' + 'document ' * 100 + '.\nUpload your passport.'
    assert texts('', body) == ['Upload your passport']


@pytest.mark.parametrize('ending', ['من', 'إلى', 'في', 'على', 'مع', 'for', 'from', 'to', 'with', 'and', 'ثم'])
@pytest.mark.parametrize('punctuation', ['', '.', '…'])
def test_incomplete_task_endings(ending, punctuation):
    assert extract_tasks('', f'Please send the document {ending}{punctuation}') == []


@pytest.mark.parametrize('cta', [
    'Download our app', 'Shop now', 'Learn more', 'Click here', 'Follow us', 'Explore', 'View more',
    'حمل تطبيقنا الآن', 'تحميل التطبيق', 'حمل تطبيق طيران ناس', 'تسوق الآن', 'اعرف المزيد',
    'اضغط هنا', 'تابعنا', 'استكشف', 'عرض المزيد',
])
def test_generic_ctas_are_not_tasks(cta):
    assert extract_tasks(cta, cta + '.') == []


@pytest.mark.parametrize('task', [
    'إصدار بطاقة صعود الطائرة', 'دفع فاتورة', 'الرد على رسالة', 'حضور اجتماع', 'رفع مستند', 'إكمال التسجيل',
    'Send the document to the customer', 'Review the contract with the lawyer',
    'Pay the invoice for 2026', 'حمل المستند من البريد', 'إرسال الملف إلى العميل',
])
def test_complete_tasks_are_preserved(task):
    assert texts('', task + '.') == [task]


@pytest.mark.parametrize('separator', ['\n', '. ', ' و'])
def test_flynas_regression(separator):
    body = 'إصدار بطاقة صعود الطائرة' + separator + 'حمل تطبيق طيران ناس من'
    assert texts('إصدار بطاقة صعود الطائرة', body) == ['إصدار بطاقة صعود الطائرة']


def test_cta_does_not_remove_neighboring_action():
    assert texts('', 'Please pay the invoice and shop now.') == ['Pay the invoice']
    assert texts('', 'Please upload your document and download our app.') == ['Upload your document']
    assert texts('', 'إصدار بطاقة صعود الطائرة وحمل تطبيقنا الآن.') == ['إصدار بطاقة صعود الطائرة']


def test_app_instruction_with_concrete_purpose():
    assert texts('', 'يرجى حمل التطبيق لإكمال التسجيل.') == ['حمل التطبيق لإكمال التسجيل']


def test_complete_word_not_substring():
    assert texts('', 'Please send the document to Alison.') == ['Send the document to Alison']
    assert texts('', 'Please review the document with Form 24.') == ['Review the document with Form 24']


@pytest.mark.parametrize('cta', ['تسوق الآن', 'تعرف على المزيد', 'اضغط هنا', 'تابعنا'])
def test_arabic_cta_beside_real_action(cta):
    assert texts('', 'إصدار بطاقة صعود الطائرة و' + cta + '.') == ['إصدار بطاقة صعود الطائرة']


def test_arabic_name_not_confused_with_preposition():
    assert texts('', 'أرسل المستند إلى علي.') == ['أرسل المستند إلى علي']
    assert extract_tasks('', 'يرجى الرد علىٰ.') == []


@pytest.mark.parametrize('body, expected', [
    ('Please pay your invoice by Friday.', 'Pay your invoice by Friday'),
    ('Submit your application before 30 September.', 'Submit your application before 30 September'),
    ('Upload the requested document.', 'Upload the requested document'),
    ('يرجى إصدار بطاقة الصعود قبل الوصول إلى المطار.', 'إصدار بطاقة الصعود قبل الوصول إلى المطار'),
    ('سدد المبلغ المستحق قبل نهاية الشهر.', 'سدد المبلغ المستحق قبل نهاية الشهر'),
    ('أرسل المستند المطلوب.', 'أرسل المستند المطلوب'),
    ('Pay the outstanding balance.', 'Pay the outstanding balance'),
    ('Payment is due by Friday.', 'Payment is due by Friday'),
    ('ادفع فاتورتك قبل 30 سبتمبر.', 'ادفع فاتورتك قبل 30 سبتمبر'),
    ('يجب إرسال المستند.', 'إرسال المستند'),
    ('You must complete registration.', 'Complete registration'),
])
def test_obligations(body, expected):
    assert texts('', body) == [expected]


@pytest.mark.parametrize('body', [
    'Shop now and pay later.', 'Buy now.', 'Buy now, pay later.',
    'Buy now and pay later.', 'Pay later.', 'Pay in installments.',
    'تسوق الآن وادفع لاحقًا.', 'تسوق الآن وادفع بعدين', 'ادفع بعدين',
    'اشتر الآن', 'حمل التطبيق.', 'اضغط هنا لمعرفة المزيد.',
    'Please review our products.', 'Confirm your discount.',
    'عرض خاص وادفع بالتقسيط.', 'Please review our sale.',
    'Review shipping offers.', 'راجع عروض التخفيضات.',
])
def test_marketing_and_navigation(body):
    assert extract_tasks(body, body) == []


@pytest.mark.parametrize('body, expected', [
    ('Shop now and pay your invoice by Friday.', 'Pay your invoice by Friday'),
    ('تسوق الآن وادفع فاتورتك قبل الخميس.', 'ادفع فاتورتك قبل الخميس'),
    ('Special offers and pay in four installments.', None),
    ('عروض جديدة وادفع على أقساط.', None),
    ('Buy now, pay later. Upload the requested document.', 'Upload the requested document'),
    ('تسوق الآن وادفع بعدين. إصدار بطاقة صعود الطائرة.', 'إصدار بطاقة صعود الطائرة'),
    ('Review the shipping document.', 'Review the shipping document'),
    ('Shop now and complete registration.', 'Complete registration'),
])
def test_local_context(body, expected):
    assert texts('', body) == ([expected] if expected else [])


@pytest.mark.parametrize('body', [
    'Our newsletter contains product updates.', 'Your receipt is attached.',
    'The meeting has moved to Monday.', 'خصومات جديدة على المنتجات.',
    'تم سداد الفاتورة بنجاح.', 'Your payment was received.',
])
def test_generic_information(body):
    assert extract_tasks('', body) == []


def test_confidence_is_deterministic_rule_strength():
    weak = extract_tasks('', 'Review the document.')
    strong = extract_tasks('', 'Please review the document before Friday.')
    assert weak[0]['confidence'] == 0.8
    assert strong[0]['confidence'] == 0.9
    assert strong == extract_tasks('', 'Please review the document before Friday.')


def test_strong_request_selected_before_five_weak_requests():
    body = '\n'.join(f'Review document {i}.' for i in range(5))
    result = texts('', body + '\nPay your invoice by Friday.')
    assert len(result) == 5
    assert 'Pay your invoice by Friday' in result
