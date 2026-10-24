import pytest

from email_utils import clean_email_text, extract_main_content
from summarizer import summarize_email, _words, _references


LINK = 'https://tracking.example/click?token=' + 'AbCd1234-review-request-' * 50
BODY = (f'Learning Community\n\n( {LINK} )\n\n**************\nWeekly Digest\n**************'
        f'\n\n( )\n\n( )\n\nRead More\n( {LINK} )\n\n'
        f"Don't want weekly digests for this group? Turn them off ( {LINK} )\n\n"
        f'Start your own community ( {LINK} )')


def test_digest_shell_excludes_tracking_and_footer_directly():
    main = extract_main_content('Weekly digest for Tuesday', BODY)
    assert 'Learning Community' in main and 'Weekly Digest' in main
    for noise in ['https://', 'Read More', 'Turn them off', 'Start your own', '***', '( )']:
        assert noise not in main
    assert LINK in clean_email_text(BODY)


def test_digest_summary_is_readable_not_tracking_tokens():
    assert summarize_email('Weekly digest for Tuesday', BODY) == 'Learning Community Weekly Digest'


def test_no_real_content_falls_back_to_subject_without_reviving_footer():
    body = BODY[BODY.index('( '):].replace('Weekly Digest', '')
    assert summarize_email('Weekly digest for Tuesday', body) == 'Weekly digest for Tuesday'


def test_real_news_survives_digest_navigation():
    main = 'Our next workshop starts on Friday. Please upload your project by Thursday.'
    body = BODY.replace('Weekly Digest', main)
    result = summarize_email('Workshop update', body)
    assert main in result and 'https://' not in result and 'Turn them off' not in result


@pytest.mark.parametrize('notice', [
    "Don't want these newsletters? Turn them off",
    'Do not want weekly notifications? Disable these notifications',
    'لا ترغب في تلقي النشرة؟ أوقف هذه الرسائل',
])
def test_notification_preferences(notice):
    body = f'Product A\nProduct B\n\n{notice} ( {LINK} )'
    result = extract_main_content('Updates', body)
    assert 'Product A' in result and notice not in result


def test_turn_off_is_not_a_footer_without_email_context():
    main = 'Please turn off the machine before Friday.'
    assert extract_main_content('Maintenance', main) == main
    assert summarize_email('Maintenance', main) == main


def test_useful_link_and_deadline_remain_in_main_content():
    body = f'Please upload your document by Friday:\n{LINK}'
    assert LINK in extract_main_content('Document request', body)
    assert 'Please upload your document by Friday:' in summarize_email('Document request', body)
    assert LINK not in summarize_email('Document request', body)


def test_link_text_cannot_inflate_scores_or_reference_matches():
    assert _words(LINK) == []
    assert _references(LINK) == set()
    body = f'Please pay invoice INV-123 by Friday ( {LINK} ).'
    result = summarize_email('Invoice INV-123', body)
    assert 'invoice INV-123 by Friday' in result and 'http' not in result


def test_promotion_phrase_is_preserved_outside_footer_context():
    body = 'Start your own garden with these instructions.'
    assert extract_main_content('Garden tips', body) == body


@pytest.mark.parametrize('wrapped', ['({})', '[{}]', '( {} )', '{}'])
def test_link_wrappers_cannot_leave_empty_summary_fragments(wrapped):
    body = 'Please upload your document by Friday.\n' + wrapped.format(LINK)
    assert summarize_email('Document request', body) == 'Please upload your document by Friday.'
