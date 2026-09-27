"""Local extractive summaries. No model downloads or external services."""

import math
import re
from collections import Counter


STOP_WORDS = set('''
a an the and or but if to of in on at for from with by as is are was were be been
it its this that these those i you your we our they their he she his her us them
will would can could should have has had do does did not please dear hello regards
من إلى الى في على عن مع هذا هذه ذلك تلك هو هي هم نحن انت أنت أن ان إن ثم أو او
و لا ما لم لن قد لقد كان كانت يكون تكون تم يتم التي الذي كل بعض عند بعد قبل
يرجى شكرا شكراً لكم لكمُ تحية مرحبا
'''.split())

BOILERPLATE = re.compile(
    r'^(?:unsubscribe\b|click here to unsubscribe\b|'
    r'if you (?:no longer wish|would like to unsubscribe)\b|'
    r'you are receiving this (?:email|message)\b|'
    r'privacy policy\b|terms (?:and|&) conditions\b|'
    r'all rights reserved\b|copyright\b|©|view (?:this email )?in (?:a |your )?browser\b|'
    r'إلغاء الاشتراك|الغاء الاشتراك|لإلغاء الاشتراك|لالغاء الاشتراك|'
    r'سياسة الخصوصية|جميع الحقوق محفوظة|عرض الرسالة في المتصفح)', re.IGNORECASE
)
ABBREVIATION = re.compile(
    r'(?:\b(?:mr|mrs|ms|dr|prof|sr|jr|vs|etc)|\b[A-Z]|(?:\b[A-Za-z]\.)+[A-Za-z])\.$',
    re.IGNORECASE
)


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def _words(text: str) -> list[str]:
    # Normalize only for scoring, not for the returned text.
    text = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', text.casefold())
    text = text.translate(str.maketrans('أإآى', 'اااي'))
    return [word for word in re.findall(r'[^\W\d_]+', text)
            if len(word) > 1 and word not in STOP_WORDS]


def _sentences(body: str) -> list[str]:
    sentences = []
    for line in (body or '').splitlines():
        line = _clean(line)
        if not line or BOILERPLATE.match(line):
            continue
        parts = re.split(r'(?<=[.!?؟؛;])\s+', line)
        joined = []
        for part in parts:
            if joined and ABBREVIATION.search(joined[-1]):
                joined[-1] += ' ' + part
            else:
                joined.append(part)
        sentences.extend(part for part in joined if not BOILERPLATE.match(part))
    return sentences


class ExtractiveSummarizer:
    """Rank sentences by frequency and subject overlap; keep their original order."""

    def summarize(self, subject: str, body: str) -> str:
        sentences = _sentences(body)
        if not sentences:
            return _clean(subject)

        text = ' '.join(sentences)
        if len(text.split()) <= 60 and len(sentences) <= 3:
            return text

        # Skip tiny lines and repeated sentences.
        candidates = []
        seen = set()
        for index, sentence in enumerate(sentences):
            key = sentence.casefold()
            if len(sentence.split()) < 3 or len(sentence) < 12 or key in seen:
                continue
            seen.add(key)
            candidates.append((index, sentence, _words(sentence)))
        if not candidates:
            return _clean(subject)

        frequency = Counter(word for _, _, words in candidates for word in words)
        subject_words = set(_words(subject))

        def score(candidate):
            words = candidate[2]
            if not words:
                return 0.0
            unique = set(words)
            common = sum(min(frequency[word], 3) for word in unique)
            subject_bonus = 4 * len(unique & subject_words)
            return (common + subject_bonus) / math.sqrt(len(words))

        ranked = sorted(candidates, key=lambda item: (-score(item), item[0]))
        selected = []
        word_count = 0
        for candidate in ranked:
            length = len(candidate[1].split())
            if selected and word_count + length > 90:
                continue
            selected.append(candidate)
            word_count += length
            if len(selected) == 3:
                break
        return ' '.join(item[1] for item in sorted(selected, key=lambda item: item[0]))


_summarizer = ExtractiveSummarizer()


def summarize_email(subject: str, body: str) -> str:
    """Return 1–3 original sentences, or the subject when the body has no content.

    Whitespace is normalized. Replace the backend object to change the algorithm
    without changing callers or database storage.
    """
    return _summarizer.summarize(subject, body)
