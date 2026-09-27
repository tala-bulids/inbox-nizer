import base64

import pytest

from email_utils import clean_email_text, extract_email_body


LEGAL = ('This email communication is confidential and intended only for the named recipient. '
         'If you are not the intended recipient, delete this message and any copies. '
         'Unauthorized disclosure or distribution is prohibited.')
MAIN = 'Good day,\nPlease submit your application through our website.\nWe look forward to receiving your application.'


@pytest.mark.parametrize('footer', [
    'Regards,\nRecruitment Team\n\n' + LEGAL * 10,
    'Kind regards,\nA Person\ninfo@example.com',
    'Best regards\nA Person',
    'Sincerely,\nA Person',
    LEGAL * 10,
    'Confidentiality notice\n' + LEGAL,
    'If you are not the intended recipient, delete the message.\nSend email to info@example.com',
    'Privacy policy\nhttps://example.com/privacy\nUnsubscribe\nRegistered office address',
    'Follow us | Contact us\nPrivacy policy\nUnsubscribe',
    'All rights reserved.\nRegistered office address',
])
def test_english_footer_sections(footer):
    assert clean_email_text(MAIN + '\n\n' + footer) == MAIN


@pytest.mark.parametrize('footer', [
    'مع التحية،\nفريق العمل\ninfo@example.com',
    'تحياتي\nفريق العمل',
    'هذه الرسالة سرية ومخصصة للمستلم المقصود.\nإذا لم تكن المستلم المقصود، احذف الرسالة.',
    'سياسة الخصوصية\nالشروط والأحكام\nإلغاء الاشتراك',
    'جميع الحقوق محفوظة\nعنوان المكتب',
])
def test_arabic_footer_sections(footer):
    main = 'مرحبًا،\nيرجى إرسال المستند المطلوب قبل الخميس.'
    assert clean_email_text(main + '\n\n' + footer) == main


@pytest.mark.parametrize('text', [
    'Hi! Are we still meeting tomorrow?',
    'مرحبًا، أرجو مراجعة طلب التسجيل. شكرًا 😊',
    'Please review the privacy policy and terms and conditions before signing.',
    'In regards to the contract, please reply by Friday.',
    'Privacy policy\nPlease review the proposed changes to clause 4.',
    'Confidential\nPlease review this contract before Friday.',
    'This email is confidential. Please review the attached contract.',
    'Unsubscribe is not working. Please help.',
    'سياسة الخصوصية تحتاج إلى تعديل قبل توقيع العقد.',
    'Hi!\nيرجى تأكيد الحضور للاجتماع.\nSee you tomorrow 👩\u200d💻',
    'Complete registration at https://example.com/register?token=abc&step=2',
    'Send your application to info@example.com',
    'هل ستأتي غدًا؟؟؟ أرجو الرد.',
    'Please check the text ???? in the attached document.',
    'ظل الطفل تحت مظلة في الظهيرة. الطقس لطيف.',
    'Regards,\nPlease send the missing document tomorrow.',
])
def test_meaningful_content_preserved(text):
    assert clean_email_text(text) == text


@pytest.mark.parametrize('source, expected', [
    ('Send to info@example.com<mailto:info@example.com>', 'Send to info@example.com'),
    ('Send to <mailto:info@example.com>', 'Send to info@example.com'),
    ('Send to mailto:info@example.com', 'Send to info@example.com'),
    ('Visit <https://example.com/form>', 'Visit https://example.com/form'),
    ('Visit [https://example.com/form]', 'Visit [https://example.com/form]'),
    ('Visit <https://example.com/form?utm_source=email>', 'Visit https://example.com/form?utm_source=email'),
    ('Write to info@example.com&lt;mailto:info@example.com&gt;', 'Write to info@example.com'),
    ('<p>Apply <a href="https://example.com/apply">here</a>.</p>', 'Apply here (https://example.com/apply).'),
    ('<p>Write to <a href="mailto:info@example.com">info@example.com</a></p>', 'Write to info@example.com'),
])
def test_useful_links_and_mailto(source, expected):
    assert clean_email_text(source) == expected


@pytest.mark.parametrize('broken', [
    'ط§ظ„ط±ط³ط§ظ„ط© ظ‡ط°ظ‡ ط§ظ„ط±ط³ط§ظ„ط©',
    '???? ???? ????', '\ufffd\ufffd\ufffd\ufffd \ufffd\ufffd\ufffd\ufffd',
])
def test_corrupted_blocks(broken):
    main = 'يرجى إرسال المستند. 👩\u200d💻'
    assert clean_email_text(main + '\n' + broken + '\nSee you tomorrow.') == main + '\nSee you tomorrow.'


def test_footer_only_and_multilingual_footer():
    assert clean_email_text('Follow us\nPrivacy policy\nإلغاء الاشتراك') == ''
    assert clean_email_text(MAIN + '\n' + LEGAL + '\nهذه الرسالة سرية\n' + LEGAL) == MAIN


def test_html_and_mime_footer_cleaning():
    raw = '<p>Please submit your application.</p><p>Regards,</p><p>A Person</p><footer>' + LEGAL + '</footer>'
    payload = {'mimeType': 'text/html', 'body': {'data': base64.urlsafe_b64encode(raw.encode()).decode()}}
    assert extract_email_body(payload) == 'Please submit your application.'


def test_cleaning_is_idempotent():
    for source in [MAIN + '\n' + LEGAL, '<p>Visit <a href="https://example.com">here</a></p>',
                   'يرجى الرد.\n\nمع التحية\nفريق العمل']:
        cleaned = clean_email_text(source)
        assert clean_email_text(cleaned) == cleaned


def test_clean_message_drives_local_summary_and_tasks():
    from summarizer import summarize_email
    from task_extractor import extract_tasks
    cleaned = clean_email_text('Please submit your application.\n\n' + LEGAL + '\nSend email to info@example.com')
    assert summarize_email('Application', cleaned) == 'Please submit your application.'
    assert [item['task'] for item in extract_tasks('Application', cleaned)] == ['Submit your application']


def test_privacy_heading_does_not_hide_message_before_footer():
    body = 'Privacy policy\nPlease review clause 4.\n\nUnsubscribe\nOffice address'
    assert clean_email_text(body) == 'Privacy policy\nPlease review clause 4.'


def test_signature_does_not_hide_followup_request():
    body = 'Thanks!\nRegards,\nA Person\nPlease send the file to info@example.com'
    assert clean_email_text(body) == body


def test_navigation_with_contact_link():
    assert clean_email_text('Hello.\nFollow us\nContact us (info@example.com)\nPrivacy policy') == 'Hello.'


def test_corrupted_plain_part_falls_back_to_html():
    def part(mime, raw):
        return {'mimeType': mime, 'body': {'data': base64.urlsafe_b64encode(raw.encode()).decode()}}
    payload = {'mimeType': 'multipart/alternative', 'parts': [
        part('text/plain', '???? ???? ????'), part('text/html', '<p>Please reply.</p>')
    ]}
    assert extract_email_body(payload) == 'Please reply.'
