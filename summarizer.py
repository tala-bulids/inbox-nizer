"""Local extractive summaries. No model downloads or external services."""

import math
import re
from collections import Counter

from email_utils import _footer_start, _legal_strength, _match_text, _navigation, _trim_sections, _LEGAL_REVIEW, _segment_blocks, _legal_purpose
from email_utils import clean_email_text, extract_main_content, _without_urls, _clean_text


STOP_WORDS = set('''
a an the and or but if to of in on at for from with by as is are was were be been
it its this that these those i you your we our they their he she his her us them
will would can could should have has had do does did not please dear hello regards
من إلى الى في على عن مع هذا هذه ذلك تلك هو هي هم نحن انت أنت أن ان إن ثم أو او
و لا ما لم لن قد لقد كان كانت يكون تكون تم يتم التي الذي كل بعض عند بعد قبل
يرجى شكرا شكراً لكم لكمُ تحية مرحبا
'''.split())

_ACTION = re.compile(r'\b(?:please|must|required|submit|pay|reply|respond|confirm|upload|deadline)\b|(?:يرجى|الرجاء|يجب|المطلوب|سدد|ادفع|ارسل|اكد|قبل|بحلول)', re.I)
_STATUS = re.compile(r'\b(?:booking|reservation|flight|invoice|payment|application|request|approved|confirmed|created|under review)\b|(?:الحجز|رحلة|الرحلة|فاتورة|الفاتورة|الدفع|الطلب|طلبك|تم انشاء|قيد المراجعة)', re.I)
_GREETING = re.compile(r'^(?:hi|hello|thanks|thank you|regards|best regards|kind regards|sincerely|مرحبا|شكرا|تحياتي|مع التحية)[,.!، ]*$', re.I)
_POLICY_CONTENT = re.compile(r'\b(?:clause|retention|refund|rights|updated|revised|draft)\b|(?:البند|حقوق|تعديل|مسودة)', re.I)
_STATE = re.compile(
    r'\b(?:received|created|under review|will review|approved|rejected|completed|shipped|confirmed)\b'
    r'|(?:تم\s+(?:استلام|انشاء|التاكيد|القبول|الرفض|الشحن)|تلقينا|سيتم\s+مراجعة|قيد المراجعة)', re.I)
_COURTESY = re.compile(
    r'^(?:dear\b|hello\b|hi\b|thank you\b|thanks\b|good luck\b|we appreciate your interest\b'
    r'|شكرا|عزيزي|عزيزتي|مرحبا|نتمنى لك التوفيق|نقدر اهتمامك)', re.I)


def _references(text):
    # Keep whole IDs; a shared digit alone is not a reference match.
    return {token for token in re.findall(r'\b[\w]+(?:[-/][\w]+)*\b', _match_text(_without_urls(text)))
            if any(char.isdigit() for char in token) and len(token) >= 3}
ABBREVIATION = re.compile(
    r'(?:\b(?:mr|mrs|ms|dr|prof|sr|jr|vs|etc)|\b[A-Z]|(?:\b[A-Za-z]\.)+[A-Za-z])\.$',
    re.IGNORECASE
)


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def _words(text: str) -> list[str]:
    # Normalize only for scoring, not for the returned text.
    text = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', _without_urls(text).casefold())
    text = text.translate(str.maketrans('أإآى', 'اااي'))
    return [word for word in re.findall(r'[^\W\d_]+', text)
            if len(word) > 1 and word not in STOP_WORDS]


def _sentences(body: str, subject: str = '', *, selected: bool = False) -> list[str]:
    sentences = []
    blocks = ([{'text': line, 'role': 'main_content'} for line in body.splitlines()]
              if selected else _segment_blocks(_clean_text(body or '', subject=subject, trim_sections=False), subject, main_content=True))
    for block in blocks:
        if block['role'] in {'decorative/header', 'signature/contact', 'legal/footer', 'unsubscribe/preferences', 'navigation/social'}:
            continue
        line = block['text']
        line = _clean(_without_urls(line))
        if not line or not re.search(r'\w', line):
            continue
        parts = re.split(r'(?<=[.!?؟؛;])\s+', line)
        joined = []
        for part in parts:
            if joined and ABBREVIATION.search(joined[-1]):
                joined[-1] += ' ' + part
            else:
                joined.append(part)
        for index, part in enumerate(joined):
            discussing_legal = _legal_purpose(body, subject) or _LEGAL_REVIEW.search(_match_text(' '.join(sentences[-4:])))
            if _footer_start(part, joined[index + 1:]) and not discussing_legal:
                break
            legal_heading = re.fullmatch(r'privacy policy|terms (?:and|&) conditions|سياسة الخصوصية|الشروط والاحكام', _match_text(part), re.I)
            if not _navigation(part.strip(' .')) or legal_heading:
                sentences.append(part)
    return sentences


def _parallel_key(sentence):
    normalized = _match_text(sentence)
    references = set(re.findall(r'\b[a-z]{2,}[-]?\d[\w-]*\b', normalized))
    if not references or _ACTION.search(normalized) or re.search(r'https?://|@', normalized):
        return None
    # Only collapse simple status templates; unexplained extra details stay.
    remaining = normalized
    for reference in references:
        remaining = remaining.replace(reference, '')
    words = set(re.findall(r'[^\W\d_]+', remaining))
    allowed = set(('your the our team request application was has been received and will be review reviewed it '
                   'shortly soon under created successfully تم استلام طلبك الطلب انشاء بنجاح وسيقوم '
                   'الفريق بمراجعته قريبا قيد المراجعة').split())
    if not words <= allowed:
        return None
    states = set()
    for state, pattern in (
        ('received', r'\breceived\b|تم استلام'),
        ('created', r'\bcreated\b|تم انشاء'),
        ('review', r'\b(?:under review|will (?:be )?review(?:ed)?)\b|(?:قيد المراجعة|سيقوم.{0,20}بمراجع|ستتم مراجع)'),
    ):
        if re.search(pattern, normalized):
            states.add(state)
    if not states or re.search(r'\b(?:not|cancelled|rejected|unless|if)\b|(?:لم |لن |الغاء|رفض|اذا )', normalized):
        return None
    numbers = set(re.findall(r'\d+', normalized))
    return references, states, numbers, 'application' if 'application' in words else 'request'


def _language(text):
    return 'ar' if len(re.findall(r'[\u0600-\u06ff]', text)) > len(re.findall(r'[a-zA-Z]', text)) else 'en'


def _reduce_parallel(sentences, subject):
    kept = []
    for sentence in sentences:
        key = _parallel_key(sentence)
        if (kept and key and key == _parallel_key(kept[-1])
                and _language(sentence) != _language(kept[-1])):
            if _language(sentence) == _language(subject):
                kept[-1] = sentence
        else:
            kept.append(sentence)
    return kept


class ExtractiveSummarizer:
    """Rank useful content while keeping the wording and reading order."""

    def summarize(self, subject: str, body: str) -> str:
        main_content = extract_main_content(subject, body)
        sentences = _sentences(main_content, subject, selected=True)
        # Short product names and status lines are useful too.
        if not any(_words(sentence) and not _GREETING.fullmatch(_match_text(sentence))
                   for sentence in sentences):
            sentences = _sentences(clean_email_text(body, subject=subject), subject)
        sentences = _reduce_parallel(sentences, subject)
        if not sentences:
            return _clean(subject)

        # Repetition must not make a footer look important.
        sentences = list(dict.fromkeys(sentences))
        useful = [sentence for sentence in sentences if not _GREETING.fullmatch(_match_text(sentence))]
        if useful:
            sentences = useful
        discussing_legal = _legal_purpose(body, subject)
        filtered = [sentence for sentence in sentences if _legal_strength(sentence) < 2
                    or discussing_legal or _POLICY_CONTENT.search(_match_text(sentence))]
        if not filtered:
            return _clean(subject)
        sentences = filtered

        text = ' '.join(sentences)
        if len(text.split()) <= 60 and len(sentences) <= 3:
            return text

        # Keep short product names, but skip repeated or empty lines.
        candidates = []
        seen = set()
        for index, sentence in enumerate(sentences):
            key = sentence.casefold()
            if not _words(sentence) or key in seen:
                continue
            seen.add(key)
            candidates.append((index, sentence, _words(sentence)))
        if not candidates:
            return _clean(subject)

        frequency = Counter(word for _, _, words in candidates for word in words)
        subject_words = set(_words(subject))
        subject_references = _references(subject)
        has_subject_match = any(set(words) & subject_words for _, _, words in candidates)

        def score(candidate):
            words = candidate[2]
            if not words:
                return 0.0
            unique = set(words)
            common = sum(min(frequency[word], 3) for word in unique)
            subject_bonus = 4 * len(unique & subject_words)
            references = _references(candidate[1])
            shared_reference = bool(references & subject_references)
            relevant = not has_subject_match or bool(unique & subject_words) or shared_reference
            normalized = _match_text(candidate[1])
            action = 1.2 if relevant and _ACTION.search(normalized) else 0
            status = (4 if _STATE.search(normalized) else 0.8) if relevant and (_STATUS.search(normalized) or _STATE.search(normalized)) else 0
            details = 2 if relevant and (action or status) and references else 0
            reference_bonus = 8 if shared_reference else 0
            courtesy_penalty = 4 if _COURTESY.search(normalized) and not (action or status) else 0
            early = 1.5 / (candidate[0] + 1)
            legal_penalty = 0 if discussing_legal or _POLICY_CONTENT.search(normalized) else 4 * _legal_strength(candidate[1])
            return ((common + subject_bonus) / math.sqrt(len(words)) + early + action + status
                    + details + reference_bonus - legal_penalty - courtesy_penalty)

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
