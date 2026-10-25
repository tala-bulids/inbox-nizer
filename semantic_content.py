"""Reusable search documents and tokenizer-bounded chunks."""
import re

import embedding_service
from email_utils import extract_main_content, _without_urls

CONTENT_VERSION = 'main-content-v1:tokens300:overlap40'


def _key(text):
    return ' '.join(text.casefold().split()).strip(' .!?؟')


def build_semantic_text(email) -> str:
    subject = _without_urls(email.subject or '').strip()
    main = _without_urls(extract_main_content(subject, email.body or ''))
    summary = _without_urls(extract_main_content(subject, email.summary or ''))
    pieces = [subject] if subject else []
    # Prefer the full useful passage when the summary repeats its sentences.
    main_key = _key(main)
    raw_key = _key(_without_urls(email.body or ''))
    if main and len(summary) < len(email.summary or '') / 4:
        # Old summaries dominated by tracking URLs add no reliable context.
        summary = ''
    for sentence in re.split(r'\n+|(?<=[.!?؟])\s+', summary):
        key = _key(sentence)
        excluded_from_body = key in raw_key and key not in main_key
        if key and not excluded_from_body and key not in main_key and not any(key in _key(part) for part in pieces):
            pieces.append(sentence.strip())
    for line in main.splitlines():
        key = _key(line)
        if key and not any(key == _key(part) for part in pieces):
            pieces.append(line.strip())
    return '\n\n'.join(pieces)


def chunk_semantic_text(text: str, *, tokenizer=None, target_tokens=300, overlap_tokens=40) -> list[str]:
    if not 1 <= target_tokens <= 350 or not 0 <= overlap_tokens < target_tokens:
        raise ValueError('Invalid chunk size or overlap')
    if not text or not text.strip():
        return []
    tokenizer = tokenizer if tokenizer is not None else embedding_service.get_tokenizer()
    offsets = tokenizer(text, add_special_tokens=False, truncation=False,
                        return_offsets_mapping=True)['offset_mapping']
    if not offsets:
        return []
    chunks, start = [], 0
    while start < len(offsets):
        end = min(start + target_tokens, len(offsets))
        if end < len(offsets):
            # Prefer sentence/paragraph boundaries near the target size.
            floor = max(start + overlap_tokens + 1, end - 50)
            for candidate in range(end, floor - 1, -1):
                tail = text[offsets[candidate - 1][1]:offsets[candidate][0]]
                preceding = text[:offsets[candidate - 1][1]]
                if '\n' in tail or re.search(r'[.!?؟؛]$', preceding):
                    end = candidate
                    break
        chunk = text[offsets[start][0]:offsets[end - 1][1]].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(offsets):
            break
        next_start = max(start + 1, end - overlap_tokens)
        # Avoid beginning overlap halfway through a word if possible.
        while next_start < end and offsets[next_start][0] > 0 and not text[offsets[next_start][0] - 1].isspace():
            next_start += 1
        start = next_start
    return chunks
