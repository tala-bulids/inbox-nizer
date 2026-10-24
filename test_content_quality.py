from datetime import date, datetime, timezone

import pytest

from email_utils import clean_email_text
from summarizer import summarize_email
from task_extractor import extract_action_items


EN_NOTICE = ('This e-mail and any attachments may contain confidential and privileged information. '
             'It is intended only for the named recipient. '
             'Unauthorized disclosure or distribution is prohibited. '
             'If you are not the intended recipient, delete this message.')
AR_NOTICE = ('الرسالة ومرفقاتها قد تحتوي على معلومات سرية. '
             'هذه المعلومات مخصصة للمستلم المقصود. '
             'يحظر إفشاء المعلومات أو توزيعها. '
             'إذا لم تكن المستلم المقصود، احذف الرسالة.')


@pytest.mark.parametrize('main', [
    'Your request CRN-123 has been created successfully.',
    'Your application is under review.',
    'Your booking AB123 is confirmed for 30 September 2026.',
    'Please pay invoice INV-123 by 30 September 2026.',
])
def test_short_main_message_beats_huge_disclaimer(main):
    source = main + '\n\n' + '\n'.join([EN_NOTICE] * 20)
    assert clean_email_text(source) == main
    assert summarize_email('Update', source) == main
    assert summarize_email('Update', clean_email_text(source)) == main


@pytest.mark.parametrize('main', ['تم إنشاء الطلب CRN-123 بنجاح. 😊', 'طلبك قيد المراجعة.', 'يرجى إرسال المستند قبل 30 سبتمبر 2026.'])
def test_arabic_legal_sections(main):
    source = main + '\n\nإخلاء المسؤولية\n' + '\n'.join([AR_NOTICE] * 10)
    assert clean_email_text(source) == main
    assert summarize_email('تحديث الطلب', source) == main


def test_promotion_with_terms_footer():
    main = 'Our autumn collection is available now. Save 20% on selected items this week.'
    footer = ('Terms & Conditions\nOffers are provided without warranty. '
              'The provider accepts no liability. Unauthorized distribution is prohibited.\n'
              'Manage preferences | Unsubscribe\nCopyright 2026')
    assert clean_email_text(main + '\n\n' + footer) == main
    assert summarize_email('Autumn collection', main + '\n\n' + footer) == main


@pytest.mark.parametrize('text', [
    'Privacy policy changes take effect on 30 September. Please review the updated retention period.',
    'Terms and Conditions\nWe updated clause 4 to clarify your refund rights. Please review the changes before Friday.',
    'Confidential\nPlease review the attached business contract.',
    'Privacy\nWe need your feedback on the new data retention policy.',
    'الشروط\nيرجى مراجعة البند الرابع قبل التوقيع.',
    'سياسة الخصوصية الجديدة تحمي بيانات المستخدمين. يرجى مراجعتها قبل الخميس.',
    'Your support request is resolved. If the issue persists, reply to support@example.com.',
    'This email confirms your booking AB123 for 30 September 2026.',
    'The revised clause prohibits unauthorized distribution and accepts no liability. Please review clause 4.',
])
def test_legitimate_legal_and_support_content_survives(text):
    assert clean_email_text(text) == text
    summary = summarize_email('Update', text)
    assert summary == ' '.join(text.split())


@pytest.mark.parametrize('signature', [
    'Kind regards,\nA Person\nperson@example.com',
    'مع التحية،\nفريق الدعم\nهاتف: +966 555 123 456',
    'Regards,\nA Person\nDirect: person@example.com',
])
def test_short_useful_contact_signatures(signature):
    body = 'Your support request is resolved.\n\n' + signature
    assert clean_email_text(body) == body


def test_useful_contact_before_disclaimer():
    main = 'Please submit your application at https://example.com/apply. Contact support@example.com for help.'
    assert clean_email_text(main + '\n\n' + EN_NOTICE) == main
    signed = main + '\n\nRegards,\nA Person\nDirect: person@example.com'
    assert clean_email_text(signed + '\n\n' + EN_NOTICE) == signed


def test_tasks_and_deadlines_survive_cleaning():
    main = 'Please pay your invoice by 30 September 2026.\nيرجى إرسال المستند غداً.'
    reference = datetime(2026, 9, 21, 10, tzinfo=timezone.utc)
    expected = extract_action_items('', main, reference)
    cleaned = clean_email_text(main + '\n\n' + EN_NOTICE + '\n' + AR_NOTICE)
    assert cleaned == main
    assert extract_action_items('', cleaned, reference) == expected
    assert [item['deadline_date'] for item in expected] == [date(2026, 9, 30), date(2026, 9, 22)]


def test_inline_footer_does_not_dominate_raw_summary():
    main = 'Your application is under review.'
    assert summarize_email('Application status', main + ' ' + EN_NOTICE * 8) == main


def test_summary_ignores_unframed_legal_repetition():
    main = 'Your request CRN-123 has been created successfully.'
    remainder = 'Unauthorized disclosure or distribution is prohibited and no liability is accepted.'
    assert summarize_email('Request status', main + '\n' + '\n'.join([remainder] * 20)) == main


def test_summary_selects_later_relevant_action_not_just_first_sentences():
    sentences = [
        'The office has recently introduced new chairs.',
        'The kitchen has a selection of new cups.',
        'The garden is now open to all visitors.',
        'Your booking AB123 is confirmed for 30 September 2026.',
        'Please upload your passport before 25 September 2026.',
        'We look forward to welcoming you soon.',
    ]
    summary = summarize_email('Booking and passport', ' '.join(sentences))
    assert sentences[3] in summary and sentences[4] in summary
    assert sentences[2] not in summary
    assert all(part + '.' in sentences for part in summary[:-1].split('. '))


def test_uncertain_corporate_text_is_preserved():
    text = 'We maintain strict confidentiality. Our legal team will review the changes next week.'
    assert clean_email_text(text) == text
    assert summarize_email('Legal review', text) == text


def test_arabic_emoji_and_cleaning_twice():
    main = 'تم تأكيد الحجز رقم AB123. سعداء بزيارتك 👩\u200d💻 ✈️'
    cleaned = clean_email_text(main + '\n' + AR_NOTICE)
    assert cleaned == main
    assert clean_email_text(cleaned) == cleaned
    assert summarize_email('الحجز', cleaned) == main


def test_requested_legal_draft_is_not_mistaken_for_footer():
    source = 'Please review this draft confidentiality notice.\n\n' + EN_NOTICE
    assert clean_email_text(source) == source
    summary = summarize_email('Review draft notice', source)
    assert 'Please review this draft confidentiality notice.' in summary
    assert 'confidential' in summary


def test_terms_update_with_navigation_keeps_actual_terms():
    main = ('Hello.\nTerms and Conditions\nThe revised clause prohibits unauthorized distribution '
            'and accepts no liability. Please review clause 4.')
    source = main + '\nUnsubscribe\nCopyright 2026'
    assert clean_email_text(source) == main
    assert 'revised clause' in summarize_email('Terms update', source)


def test_footer_only_summary_falls_back_to_subject():
    assert summarize_email('Request update', 'Unauthorized disclosure is prohibited and no liability is accepted.') == 'Request update'
