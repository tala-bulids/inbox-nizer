import pytest

from email_utils import clean_email_text, extract_main_content


LEGAL = (
    'Purchases are subject to our Terms & Conditions and form a contract with the seller. '
    'This website is owned and operated by the registered company. Our registered office '
    'is listed on the website. Liability is limited under the applicable jurisdiction.'
)
UNSUBSCRIBE = 'You can unsubscribe from this newsletter or manage your email preferences using the links below.'


def test_direct_newsletter_selection_keeps_products_only():
    body = 'Women | Men\nProduct A\nProduct B\n\n' + LEGAL + '\n\n' + UNSUBSCRIBE
    assert extract_main_content('Explore the new collection', body) == 'Product A\nProduct B'
    # Selection does not require more destructive display cleaning.
    cleaned = clean_email_text(body)
    assert LEGAL in cleaned and UNSUBSCRIBE in cleaned


@pytest.mark.parametrize('subject', ['Updated Terms of Service', 'Changes to our Terms', 'Privacy Policy Update'])
def test_real_legal_subject_preserves_legal_paragraph(subject):
    body = 'Please read the updated policy.\n\n' + LEGAL + '\n\n' + UNSUBSCRIBE
    main = extract_main_content(subject, body)
    assert LEGAL in main and UNSUBSCRIBE not in main


def test_legal_introduction_protects_generic_subject():
    body = 'We updated our terms of service.\n\n' + LEGAL + '\n\n' + UNSUBSCRIBE
    assert LEGAL in extract_main_content('An important announcement', body)


def test_middle_legal_block_does_not_start_a_destructive_tail():
    main = 'Please review the attached document by Friday.'
    body = 'Product A\nProduct B\n\nTerms & Conditions\n' + LEGAL + '\n\n' + main + '\n' + UNSUBSCRIBE
    result = extract_main_content('New collection', body)
    assert 'Product A' in result and 'Product B' in result and main in result
    assert LEGAL in result and UNSUBSCRIBE not in result


def test_supported_footer_chain_with_contacts_and_copyright():
    body = ('Product A\nProduct B\n\nThis website is owned and operated by a registered company.\n'
            + LEGAL + '\nhelp@example.com\nCopyright 2026 Example\n' + UNSUBSCRIBE)
    assert extract_main_content('New arrivals', body) == 'Product A\nProduct B'


def test_uncertain_block_stops_backward_propagation():
    body = 'Product A\nContract design workshop\nProduct B\n' + LEGAL + '\n' + UNSUBSCRIBE
    result = extract_main_content('New collection', body)
    assert 'Contract design workshop' in result and 'Product B' in result


def test_single_legal_word_without_footer_is_not_enough():
    body = 'Product A\nOur contract design workshop explores new ideas for everyone.'
    assert extract_main_content('New workshops', body) == body


def test_short_contract_product_next_to_footer_is_preserved():
    body = 'Product A\nContract design workshop\n' + LEGAL + '\n' + UNSUBSCRIBE
    assert extract_main_content('New collection', body) == 'Product A\nContract design workshop'


@pytest.mark.parametrize('unsubscribe', [
    'If you no longer wish to receive our newsletter, unsubscribe using this link.',
    'To stop receiving these emails, update your preferences or unsubscribe here.',
    'This newsletter is sent to subscribers. You may unsubscribe at any time.',
])
def test_subscription_prose_variations(unsubscribe):
    body = 'Product A\nProduct B\n' + LEGAL + '\n' + unsubscribe
    assert extract_main_content('New arrivals', body) == 'Product A\nProduct B'


def test_subscription_discussion_in_main_content_survives():
    body = ('Please review the newsletter unsubscribe bug by Friday.\n'
            'If you no longer receive invoices, contact support today.')
    assert extract_main_content('Support investigation', body) == body


def test_long_terminal_legal_paragraph_without_unsubscribe():
    assert extract_main_content('New collection', 'Product A\nProduct B\n' + LEGAL) == 'Product A\nProduct B'


def test_arabic_newsletter_footer():
    legal = ('تخضع المشتريات للشروط والأحكام ويشكل الشراء عقدا مع البائع. '
             'الموقع مملوك للشركة ويوجد المقر المسجل في العنوان المذكور. '
             'تحدد المسؤولية حسب القانون المعمول به في بلد الشراء.')
    unsubscribe = 'يمكنك إلغاء الاشتراك في هذه النشرة وتغيير تفضيلات البريد في أي وقت.'
    body = 'منتج جديد\nمجموعة الصيف\n\n' + legal + '\n' + unsubscribe
    assert extract_main_content('اكتشف مجموعتنا الجديدة', body) == 'منتج جديد\nمجموعة الصيف'
    result = extract_main_content('تحديث الشروط والأحكام', body)
    assert legal in result and unsubscribe not in result
