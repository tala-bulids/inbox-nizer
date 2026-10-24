from datetime import datetime, timezone

import pytest

from email_utils import clean_email_text, extract_main_content
from summarizer import summarize_email
from task_extractor import extract_action_items


def test_display_body_keeps_contacts_and_uncertain_legal_text():
    body = ('Your application REF-55 is under review.\n'
            'Regional conditions may apply.\n\nRegards,\nA Person\nperson@example.com')
    assert clean_email_text(body) == body
    main = extract_main_content('Application REF-55', body)
    assert main == body.split('\n\n')[0]
    assert 'person@example.com' not in summarize_email('Application REF-55', body)


@pytest.mark.parametrize('main', [
    'Women Men Furniture\nProduct A\nProduct B',
    'ملابس نسائية ورجالية\nمنتج جديد\nاثاث منزلي',
])
def test_short_newsletter_blocks_survive(main):
    body = main + '\nTerms & Conditions\n' + 'Offers depend on availability. ' * 30 + '\nUnsubscribe'
    assert extract_main_content('Latest collection', body) == main
    assert summarize_email('Latest collection', body) == ' '.join(main.split())


def test_longer_catalog_is_not_replaced_by_subject():
    body = 'Product Alpha\nProduct Beta\nProduct Gamma\nProduct Delta\nUnsubscribe'
    result = summarize_email('New collection', body)
    assert 'Product' in result and 'Unsubscribe' not in result


@pytest.mark.parametrize('subject,status,review,thanks', [
    ('Application REF-847', 'We received your application REF-847.',
     'We will review your application shortly.', 'Thank you for your interest in our team.'),
    ('الطلب REF-847', 'تم استلام طلبك REF-847.',
     'سيتم مراجعة طلبك قريبا.', 'شكرا لاهتمامك بخدماتنا.'),
])
def test_transaction_status_and_reference_win(subject, status, review, thanks):
    body = ('Better Days Together\n' + thanks + '\nGood luck with your future plans.\n'
            'We appreciate your interest in our services.\n' + status + '\n' + review
            + '\nRegards,\nA Person\nperson@example.com\nAll Rights Reserved')
    result = summarize_email(subject, body)
    assert status in result and review in result
    assert 'Better Days' not in result and 'person@example.com' not in result


def test_shared_reference_beats_other_transactions():
    body = ('Request OLD-100 was received.\nRequest OLD-200 was approved.\n'
            'Request OLD-300 was shipped.\nRequest TARGET-847 was rejected.')
    assert 'Request TARGET-847 was rejected.' in summarize_email('Update TARGET-847', body)


@pytest.mark.parametrize('subject,body', [
    ('Terms update', 'Terms & Conditions\nThe refund period is now 30 days.'),
    ('Privacy update', 'Privacy policy\nThe retention period is now 30 days.'),
    ('تحديث الشروط', 'الشروط والاحكام\nتم تعديل مدة الاسترجاع إلى 30 يوما.'),
    ('تحديث الخصوصية', 'سياسة الخصوصية\nتم تعديل مدة الاحتفاظ بالبيانات إلى 30 يوما.'),
])
def test_actual_policy_content_remains(subject, body):
    assert extract_main_content(subject, body + '\nUnsubscribe') == body
    assert body.splitlines()[-1] in summarize_email(subject, body)


@pytest.mark.parametrize('main', [
    'Please pay invoice INV-50 by Friday.\nPlease upload the document tomorrow.',
    'يرجى دفع الفاتورة قبل الخميس.\nيرجى إرسال المستند غداً.',
])
def test_tasks_and_deadlines_survive(main):
    body = 'Better Days Together\n' + main + '\nPowered by Example\nUnsubscribe'
    selected = extract_main_content('', body)
    assert selected == main
    reference = datetime(2026, 9, 21, tzinfo=timezone.utc)
    assert extract_action_items('', selected, reference) == extract_action_items('', main, reference)


def test_summary_uses_public_selector(monkeypatch):
    monkeypatch.setattr('summarizer.extract_main_content', lambda subject, body: 'Selected product')
    assert summarize_email('Catalog', 'Other body text.') == 'Selected product'


def test_empty_selection_fallback_still_excludes_footer(monkeypatch):
    monkeypatch.setattr('summarizer.extract_main_content', lambda subject, body: '')
    body = 'Your request REF-847 was received.\nUnsubscribe\nAll Rights Reserved'
    assert summarize_email('Request', body) == 'Your request REF-847 was received.'
    assert summarize_email('Request', 'Unsubscribe\nAll Rights Reserved') == 'Request'


@pytest.mark.parametrize('text', ['A Brighter Future', 'Approved.', 'تم القبول.'])
def test_uncertain_or_short_useful_content_remains(text):
    assert extract_main_content('', text) == text
    assert summarize_email('', text) == text
