from types import SimpleNamespace

import pytest

from semantic_content import build_semantic_text, chunk_semantic_text
from embedding_test_fakes import FakeTokenizer


def test_semantic_text_preserves_entities_and_ignores_footer():
    main = 'Your booking AB123 is confirmed for 30 September.\nرحلة من الرياض إلى جدة يوم الجمعة.'
    email = SimpleNamespace(subject='Booking AB123', summary=main.replace('\n', ' '),
                            body=main + '\nUnsubscribe\nAll rights reserved')
    result = build_semantic_text(email)
    assert result.count('Your booking AB123') == 1
    assert '30 September' in result and 'الرياض' in result and 'جدة' in result
    assert 'Unsubscribe' not in result and 'rights reserved' not in result


def test_raw_body_is_not_primary_and_stale_summary_is_cleaned():
    email = SimpleNamespace(subject='Document', summary='Unsubscribe',
                            body='Please upload document REF-22 by Friday.\nRead More\n( https://track.example/click?t=123 )')
    result = build_semantic_text(email)
    assert 'REF-22' in result and 'Friday' in result
    assert 'http' not in result and 'Read More' not in result and 'Unsubscribe' not in result


def test_actual_privacy_update_survives():
    email = SimpleNamespace(subject='Privacy Policy Update', summary=None,
                            body='Privacy policy\nWe updated retention to 30 days.\nUnsubscribe')
    assert 'retention to 30 days' in build_semantic_text(email)


def test_old_summary_cannot_restore_a_footer_removed_from_body():
    footer = 'This website is owned and operated by a registered company under these Terms & Conditions.'
    email = SimpleNamespace(subject='New collection', summary=footer,
                            body='Product A\nProduct B\n' + footer + '\nUnsubscribe')
    assert footer not in build_semantic_text(email)
    assert 'Product A' in build_semantic_text(email)


def test_old_tracking_summary_does_not_pollute_document():
    tracking = 'https://track.example/click?t=' + 'abc123' * 200
    email = SimpleNamespace(subject='Weekly digest', summary=f'({tracking}) Turn them off ({tracking}) Start your own community',
                            body='Project updates\nPlease review document REF-12 by Friday.')
    result = build_semantic_text(email)
    assert 'REF-12' in result and 'Friday' in result
    assert 'Turn them off' not in result and 'Start your own' not in result


def test_empty_and_short_chunks():
    tokenizer = FakeTokenizer()
    assert chunk_semantic_text('', tokenizer=tokenizer) == []
    assert chunk_semantic_text('رحلة AB123 to Jeddah.', tokenizer=tokenizer) == ['رحلة AB123 to Jeddah.']


def test_long_chunks_order_overlap_and_token_budget():
    tokenizer = FakeTokenizer()
    text = '\n\n'.join(' '.join(f'item{i}' for i in range(start, start + 100)) + '.' for start in range(0, 1000, 100))
    chunks = chunk_semantic_text(text, tokenizer=tokenizer)
    assert chunks == chunk_semantic_text(text, tokenizer=tokenizer)
    assert len(chunks) > 1 and chunks[0].startswith('item0 ') and chunks[-1].endswith('item999.')
    assert all(len(tokenizer.encode('passage: ' + chunk)) <= 303 for chunk in chunks)
    assert all(set(first.split()) & set(second.split()) for first, second in zip(chunks, chunks[1:]))
    combined = set(' '.join(chunks).split())
    assert set(text.split()) <= combined


@pytest.mark.parametrize('size,overlap', [(0, 0), (351, 40), (30, 30), (50, -1)])
def test_bad_chunk_settings(size, overlap):
    with pytest.raises(ValueError):
        chunk_semantic_text('text', tokenizer=FakeTokenizer(), target_tokens=size, overlap_tokens=overlap)
