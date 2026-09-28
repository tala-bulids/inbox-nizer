import base64
from datetime import datetime, timezone

import pytest

from email_utils import clean_email_text, extract_email_body, _segment_blocks
from summarizer import summarize_email
from task_extractor import extract_action_items


def test_newsletter_terms_tail_without_confidentiality_language():
    main = 'Explore our new workshops this month. Registration opens on Monday.'
    tail = ('Terms & Conditions\n' + 'Availability varies by location. Discounts cannot be combined. ' * 20
            + '\nManage preferences\nUnsubscribe\nOffice address')
    assert clean_email_text(main + '\n\n' + tail) == main
    assert summarize_email('New workshops', main + '\n\n' + tail) == main


@pytest.mark.parametrize('branding', ['Creating Email Magic', 'Better Days Together', 'Building New Possibilities'])
def test_transactional_summary_ignores_short_decorative_blocks(branding):
    main = 'Your request CASE-847 has been created successfully. Our team will review it shortly.'
    body = f'{branding}\n\n{main}\n\n{branding}\nPowered by Example\nContact us\n© 2023 All Rights Reserved'
    assert summarize_email('Request created CASE-847', body) == main
    # Weak decorative evidence affects selection, not deletion of the body.
    assert branding in clean_email_text(body)


@pytest.mark.parametrize('subject, heading', [('Terms update', 'Terms & Conditions'), ('Privacy notice', 'Privacy policy')])
def test_subject_preserves_real_legal_purpose(subject, heading):
    main = 'Hello.\n' + heading + '\nAvailability varies by location. Discounts cannot be combined.'
    body = main + '\nUnsubscribe\nOffice address'
    assert clean_email_text(body, subject=subject) == main
    assert 'Availability varies by location.' in summarize_email(subject, body)


def test_gmail_subject_reaches_nested_mime_cleaning():
    body = 'Hello.\nTerms & Conditions\nAvailability varies by location.\nUnsubscribe'
    payload = {'mimeType': 'multipart/alternative', 'headers': [{'name': 'Subject', 'value': 'Terms update'}],
               'parts': [{'mimeType': 'text/plain', 'body': {'data': base64.urlsafe_b64encode(body.encode()).decode()}}]}
    assert 'Availability varies by location.' in extract_email_body(payload)


def test_contacts_kept_in_body_but_not_used_as_summary_filler():
    main = 'Your application REF-55 is under review.'
    body = main + '\n\nRegards,\nA Person\nperson@example.com'
    assert clean_email_text(body) == body
    assert summarize_email('Application REF-55', body) == main


def test_obvious_parallel_status_sections_are_concise():
    arabic = 'تم استلام طلبك CASE-847 وسيقوم الفريق بمراجعته قريبا.'
    english = 'Your request CASE-847 was received and our team will review it shortly.'
    body = arabic + '\n\n' + english
    assert clean_email_text(body) == body
    assert summarize_email('Request received CASE-847', body) == english
    assert summarize_email('تم استلام الطلب CASE-847', body) == arabic


@pytest.mark.parametrize('english', [
    'Your request CASE-848 was received and our team will review it shortly.',
    'Your request CASE-847 was received and will be reviewed in 5 days.',
    'Your request CASE-847 was created successfully.',
    'Your request CASE-847 was not received.',
    'Your request CASE-847 was received and our team will review it shortly but documents are missing.',
])
def test_uncertain_bilingual_content_is_kept(english):
    arabic = 'تم استلام طلبك CASE-847 وسيقوم الفريق بمراجعته قريبا.'
    result = summarize_email('Request update', arabic + '\n' + english)
    assert arabic in result and english in result


def test_roles_distinguish_removal_from_summary_exclusion():
    blocks = _segment_blocks('Better Days Together\nYour request REF-55 was received.\nRegards,\nA Person\na@example.com\nPowered by Example\nManage preferences')
    assert blocks[0]['role'] == 'decorative/header' and not blocks[0]['remove']
    assert blocks[1]['role'] == 'main_content'
    assert blocks[2]['role'] == 'signature/contact'
    assert blocks[-1]['role'] == 'unsubscribe/preferences'


def test_tasks_and_timing_are_not_decorative():
    main = 'Please pay invoice INV-50 by Friday.\nيرجى إرسال المستند غداً.'
    body = 'A Brighter Future\n' + main + '\nPowered by Example\nAll Rights Reserved'
    reference = datetime(2026, 9, 21, tzinfo=timezone.utc)
    cleaned = clean_email_text(body)
    assert main in cleaned
    assert extract_action_items('', cleaned, reference) == extract_action_items('', main, reference)


def test_short_uncertain_content_is_preserved():
    assert clean_email_text('A Brighter Future') == 'A Brighter Future'
    assert summarize_email('', 'A Brighter Future') == 'A Brighter Future'
