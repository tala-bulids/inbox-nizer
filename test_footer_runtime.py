import pytest

from email_utils import extract_main_content, _segment_blocks


LEGAL = (
    'This Website is owned and operated by Example Company, with its registered office at the address listed on our website.\n'
    'For the purposes of these Terms & Conditions, references to the seller mean the registered company operating this website.\n'
    'When you purchase Products from our Website, you are entering into a contract with the seller under these conditions.'
)
SUBSCRIPTION = (
    'You have received this email because you subscribed to our newsletter.\n'
    'if you want to stop receiving them, please click here'
)
BODY = 'Product A\n\nProduct B\n\n' + LEGAL + '\n\n' + SUBSCRIPTION


def test_exact_runtime_structure_direct_selection():
    assert extract_main_content('Explore the latest collection', BODY).splitlines() == ['Product A', '', 'Product B']


def test_runtime_roles():
    blocks = [block for block in _segment_blocks(BODY, 'Latest collection', main_content=True) if block['text']]
    assert [block['role'] for block in blocks] == (
        ['main_content'] * 2 + ['legal/footer'] * 3 + ['unsubscribe/preferences'] * 2
    )


def test_runtime_merged_paragraphs():
    body = 'Product A\n\nProduct B\n\n' + LEGAL.replace('\n', ' ') + '\n\n' + SUBSCRIPTION.replace('\n', ' ')
    assert extract_main_content('Latest collection', body) == 'Product A\n\nProduct B'


@pytest.mark.parametrize('reason', [
    'You received this email because you signed up for our newsletters.',
    'You are receiving these emails because you opted in on our website.',
    'You have received this email because you subscribed to our newsletter.',
])
def test_subscription_reason_and_contextual_stop_request(reason):
    body = 'Product A\nProduct B\n\n' + LEGAL + '\n\n' + reason + '\nIf you wish to stop receiving them, click here.'
    assert extract_main_content('New collection', body) == 'Product A\nProduct B'


def test_useful_action_after_subscription_notice_stops_tail():
    body = 'Product A\n\n' + LEGAL + '\n\n' + SUBSCRIPTION + '\n\nPlease upload your document by Friday.'
    result = extract_main_content('Your documents', body)
    assert LEGAL in result and 'Please upload your document by Friday.' in result


def test_arabic_subscription_reason_and_stop_request():
    body = ('منتج جديد\nمجموعة الصيف\n\n' + LEGAL + '\n\n'
            'لقد تلقيت هذه الرسالة لأنك اشتركت في النشرة.\n'
            'إذا كنت ترغب في التوقف عن تلقي هذه الرسائل، اضغط هنا.')
    assert extract_main_content('مجموعة جديدة', body) == 'منتج جديد\nمجموعة الصيف'


@pytest.mark.parametrize('subject', ['Updated Terms', 'Privacy Policy Update', 'Changes to our Terms'])
def test_real_legal_message_preserves_runtime_legal_block(subject):
    result = extract_main_content(subject, BODY)
    assert LEGAL in result and SUBSCRIPTION not in result
    assert 'stop receiving' not in result


def test_uncertain_content_stops_tail_walk():
    body = BODY.replace('\n\n' + SUBSCRIPTION, '\n\nPlease send your feedback by Friday.\n\n' + SUBSCRIPTION)
    result = extract_main_content('Latest collection', body)
    assert LEGAL in result and 'Please send your feedback by Friday.' in result
    assert 'stop receiving' not in result


def test_stop_receiving_without_subscription_context_is_preserved():
    body = 'Please investigate the delivery issue.\n\nIf you want to stop receiving them, please click here'
    assert extract_main_content('Support investigation', body) == body
