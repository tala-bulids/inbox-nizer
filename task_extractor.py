"""Local action extraction. Confidence values are rule strengths, not probabilities."""
import re
from datetime import datetime

from deadline_extractor import _deadline_for_task, _normalized
from task_context import CONDITION, unsafe_scope, completed_subject


EN_ACTION = r'(?:pay|reply|respond|attend|complete|issue|submit|confirm|reset|upload|review|sign|send|provide|approve|register|renew|schedule|prepare)'
AR_ACTION = r'(?:ادفع|سدد|قم بدفع|قم بسداد|رد|قم بالرد|احضر|اكمل|اتمم|اصدر|قدم|اكد|قم بتاكيد|اعد تعيين|ارفع|حمل|راجع|وقع|ارسل|زودنا|وافق|سجل|جدد|جهز|دفع|سداد|الرد|حضور|الحضور|اكمال|اصدار|تقديم|تاكيد|اعادة تعيين|رفع|تحميل|مراجعة|ارسال|التسجيل)'
AR_ACTION = AR_ACTION.replace('ا', '[اأإآ]')
ACTION = rf'(?:{EN_ACTION}\b|{AR_ACTION}(?=\s))'
POLITE = re.compile(
    r'^(?:(?:please|kindly)\s+|(?:can|could|would|will) you\s+(?:please\s+)?|'
    r'(?:you (?:need to|must|should|are required to)|must|should|needs? to|required to)\s+|we (?:need|ask) you to\s+|(?:action required|reminder):\s*|'
    r'(?:يرجى|يرجي|الرجاء|من فضلك|من فضلكم|(?:نرجو|نامل)(?: منك| منكم)?|يجب عليك|يجب|مطلوب|عليك ان|عليك)\s+)', re.I
)
START = re.compile(rf'^(?P<action>{ACTION})\s+\S+', re.I)
# Match whole CTA phrases, not words inside useful instructions.
APP_CTA = r'(?:(?:download|install)\s+(?:(?:our|the|this|your|an)\s+)?app(?:lication)?|(?:حمل|تحميل|نزل|تنزيل)\s+(?:تطبيق(?:نا|كم)?|التطبيق))'
OTHER_CTA = r'(?:(?:shop|buy|browse)(?: now)?|learn more|click here|follow us|explore|view more|تسوق(?: الان)?|اشتر(?:ي)?(?: الان)?|تصفح|اعرف المزيد|تعرف عل[ىي] المزيد|اضغط هنا|انقر هنا|تابعنا|استكشف|عرض المزيد|شاهد المزيد)'
APP_CTA = APP_CTA.replace('ا', '[اأإآ]')
OTHER_CTA = OTHER_CTA.replace('ا', '[اأإآ]')
CTA_START = rf'(?:{APP_CTA}|{OTHER_CTA})(?=\s|$|[,.!?؟؛;،])'
GENERIC_CTA = re.compile(rf'^{CTA_START}', re.I)
APP_REQUIRED = re.compile(r'\b(?:to (?:complete|verify|attend|access)|required for)\b|(?:لاكمال|لاتمام|للتحقق|للدخول|لحضور)\b', re.I)
_POLITE_SPLIT = POLITE.pattern.removeprefix('^').replace('ا', '[اأإآ]')
SPLIT_ACTION = re.compile(rf'(?:[,،]\s*|\s+(?:and(?: then)?|then|و|ثم)\s+|\s+و)(?=(?:{_POLITE_SPLIT})?(?:{ACTION}|{CTA_START}))', re.I)
DANGLING_END = re.compile(r'(?:^|\s)(?:من|[اإ]لى|في|على|مع|عن|و|[اأ]و|ثم|for|from|to|with|and|or)[\W_]*$', re.I)

FOOTER = re.compile(r'\b(?:unsubscribe|privacy policy|all rights reserved|view in browser)\b|(?:الغاء الاشتراك|سياسه الخصوصيه|سياسة الخصوصية|جميع الحقوق محفوظة)', re.I)
PROMO = re.compile(r'\b(?:shop now|latest deals|special offers|exclusive discounts|win a|limited.time offer)\b|(?:عروض حصريه|عروض حصرية|تسوق الان|اربح جائزه|اربح جائزة)', re.I)
NEGATIVE = re.compile(r'\b(?:do not|don.t|no need to|not required to|never|already|completed|cancelled|canceled)\b|(?:لا داعي|لا تقم|لا ترسل|لا تدفع|تم بالفعل|تم الغاء)', re.I)


def _normalize(text):
    text = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', text.casefold())
    return text.translate(str.maketrans('أإآى', 'اااي'))


# These signals describe wording, not the sender or brand.
_SHOPPING = re.compile(
    r"\b(?:shop|shopping|buy|browse|purchase|cart|collection|discounts?|offers?|sale|promo|products?|shipping|installments?)\b|"
    r"(?:تسوق|اشتر|شراء|تشكيلتنا|خصومات|عروض|تخفيضات|منتجات|شحن|اقساط)", re.I
)
_PAY_LATER = re.compile(
    r"^(?:pay\s+(?:later|in installments)|(?:ادفع|دفع|سدد)\s+(?:بعدين|لاحقا|بالتقسيط))(?=\W|$)", re.I
)
_FINANCIAL = re.compile(
    r"\b(?:invoices?|bills?|outstanding balance|amount due|overdue|debt)\b|"
    r"(?:فاتور|فواتير|المبلغ المستحق|الرصيد المستحق|متاخرات)|\b(?:دين|الدين)\b", re.I
)
_DUE = re.compile(r"^(?:payment|your payment|the payment) is (?:due|overdue)\b|^(?:الدفع|السداد) مستحق(?=\s|$)", re.I)
_STRONG = re.compile(
    r"\b(?:by|before|deadline|required|requested|must|should|due)\b|"
    r"(?:قبل|بحلول|موعد نهائي|المطلوب|مطلوب|المستحق|يجب)", re.I
)
_WORK_OBJECT = re.compile(
    r"\b(?:document|id|passport|application|registration|meeting|customer|boarding pass|password|contract|booking)\b|"
    r"(?:مستند|التسجيل|اجتماع|رسالة|بطاقة|الحجز|العقد|العميل)", re.I
)
_BENEFIT = re.compile(r'^(?:رفع|زيادة|تحسين|تعزيز)\s+(?:معدل|كفاءة|مستوي|قدرة|انتاجية)\b')
_REGISTER_CTA = re.compile(r'^(?:register|sign up|سجل|التسجيل)\s+(?:now|الان)\b', re.I)
_REQUIRED = re.compile(r'\b(?:must|required|mandatory|need to|needs to)\b|(?:يجب|مطلوب|الزامي|عليك)', re.I)
_REGISTER_CONTEXT = re.compile(r'(?:registration|registering|التسجيل).{0,30}(?:required|mandatory|مطلوب|الزامي)', re.I)
_OPEN_INVITATION = re.compile(r'\b(?:free|public|optional|open to everyone)\b|مجاني|اختياري|للجميع',re.I)
_JOIN_ACTION = re.compile(r'^(?:register|attend|sign up|سجل|التسجيل|احضر|حضور|الحضور)\b',re.I)


def _split_action_clauses(text):
    # Match normalized Arabic while keeping the original task wording.
    normalized, offsets = _normalized(text)
    start = 0
    for match in SPLIT_ACTION.finditer(normalized):
        yield text[start:offsets[match.start()]]
        start = offsets[match.end()]
    yield text[start:]


def _clauses(text):
    # Keep punctuation inside addresses and URLs.
    sentences = []
    for sentence in re.split(r'\n+|(?<=[.!?؟؛;])\s+', text or ''):
        if (sentences and re.match(r'^(?:تنويه\s*[:،]?\s*)?(?:deadline\b|due (?:on|by)\b|الموعد النهائي|اخر (?:يوم|موعد)|الموعد الاخير)', _normalize(sentence))
                and sum(_candidate(part) is not None for part in _split_action_clauses(sentences[-1])) == 1
                and _deadline_for_task(sentence)):
            sentences[-1] = sentences[-1].rstrip(' .!?؟؛;') + '; ' + sentence
        else:
            sentences.append(sentence)
    for sentence_index, sentence in enumerate(sentences):
        sentence = re.sub(r'\s+', ' ', sentence).strip(' \t-*•')
        context = _normalize(sentence)
        previous = sentences[sentence_index - 1] if sentence_index else ''
        if _REGISTER_CONTEXT.search(_normalize(previous)):
            context += ' registration required'
        # A conditional request stays one source sentence, including its condition.
        if CONDITION.match(context):
            yield sentence, context
        else:
            for clause in _split_action_clauses(sentence):
                yield clause, context


def _candidate(clause):
    original = clause.strip(' \t,.!?؟؛;،')
    request = _normalize(original)
    condition = CONDITION.match(request)
    if condition:
        parts = re.split(r'[,،]\s*', original, maxsplit=1)
        if len(parts) != 2 or _candidate(parts[1]) is None:
            return None
        _, action, polite = _candidate(parts[1])
        return original, action, polite
    polite = POLITE.match(request)
    if polite:
        original = ' '.join(original.split()[len(polite.group().split()):])
        request = _normalize(original)
    if not (START.match(request) or _DUE.match(request)):
        return None
    return original, request, bool(polite)


def _incomplete(original):
    # Keep the difference between the name علي and the preposition على.
    ending = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', original.casefold())
    return len(original) > 500 or bool(DANGLING_END.search(ending))


def _intent(request, context):
    if FOOTER.search(request) or re.match(r'^(?:do not|don.t|no need to|never|already)\b|^(?:لا داعي|لا تقم|لا ترسل|لا تدفع|تم بالفعل|تم الغاء)', request, re.I):
        return 'boilerplate'
    if GENERIC_CTA.match(request):
        if not (re.match(APP_CTA, request, re.I) and APP_REQUIRED.search(request)):
            return 'navigation'
    if _BENEFIT.match(request):
        return 'benefit'
    if (_JOIN_ACTION.match(request) and _OPEN_INVITATION.search(context)
            and not _REQUIRED.search(context)):
        return 'invitation'
    if _REGISTER_CTA.match(request) and not (_REQUIRED.search(context) or
                                           (_WORK_OBJECT.search(request) and _STRONG.search(request))):
        return 'marketing'
    # An invoice remains an obligation even beside an offer.
    if _FINANCIAL.search(request) or _DUE.match(request):
        return 'obligation'
    if _PAY_LATER.match(request) or PROMO.search(request):
        return 'marketing'
    if _SHOPPING.search(context) and not _WORK_OBJECT.search(request):
        return 'marketing'
    return 'obligation'


def _confidence(request, polite):
    # Rule strength only; this is not an ML probability.
    return 0.9 if polite or _STRONG.search(request) or _DUE.match(request) else 0.8


_ACTION_GROUPS = [
    'pay ادفع سدد دفع سداد', 'reply respond رد الرد', 'issue اصدر اصدار',
    'upload ارفع رفع حمل تحميل', 'send ارسل ارسال', 'attend احضر حضور الحضور',
    'complete اكمل اتمم اكمال', 'submit قدم تقديم', 'confirm اكد تاكيد',
    'review راجع مراجعة', 'register سجل التسجيل',
]
_ACTION_KEYS = {word: group.split()[0] for group in _ACTION_GROUPS for word in group.split()}
_WEAK_WORDS = set('the a an your our please kindly requested required electronically الكترونيا المطلوب المطلوبة'.split())


def _task_identity(text):
    normalized = _normalize(text)
    deadline = _deadline_for_task(text)
    if deadline:
        normalized = normalized.split(_normalize(deadline['deadline_text']), 1)[0]
    words = re.findall(r'\w+', normalized)
    if not words:
        return '', set(), ''
    action = _ACTION_KEYS.get(words[0], words[0])
    tokens = {word[2:] if word.startswith('ال') and len(word) > 3 else word
              for word in words[1:] if word not in _WEAK_WORDS}
    timing = _normalize(deadline['deadline_text']) if deadline else ''
    return action, tokens, timing


def _same_task(first, second):
    # Different conditions describe different obligations.
    if CONDITION.match(_normalize(first)) or CONDITION.match(_normalize(second)):
        return _normalize(first) == _normalize(second)
    action_a, words_a, timing_a = _task_identity(first)
    action_b, words_b, timing_b = _task_identity(second)
    if action_a != action_b or not words_a or not words_b:
        return _normalize(first) == _normalize(second)
    # Different dates or identifiers can describe separate obligations.
    if timing_a and timing_b and timing_a != timing_b:
        return False
    if {word for word in words_a if any(c.isdigit() for c in word)} != {word for word in words_b if any(c.isdigit() for c in word)}:
        return False
    shared = words_a & words_b
    return (words_a == words_b or
            (len(shared) >= 2 and (words_a <= words_b or words_b <= words_a)))


def _specificity(task):
    return (bool(_deadline_for_task(task['task'])), task['confidence'], len(task['task'].split()))


def _select(candidates):
    unique = []
    for task in candidates:
        duplicate = next((i for i, saved in enumerate(unique) if _same_task(task['task'], saved['task'])), None)
        if duplicate is None:
            unique.append(task)
        elif _specificity(task) > _specificity(unique[duplicate]):
            unique[duplicate] = task
    # Prefer strong requests, then keep their original reading order.
    selected = sorted(range(len(unique)), key=lambda i: -unique[i]['confidence'])[:5]
    return [unique[i] for i in sorted(selected)]


class RuleTaskExtractor:
    """Extract local requests while retaining their original wording."""

    def extract(self, subject, body):
        candidates = []
        # Body first so details survive subject duplicates.
        heading = _candidate(subject)
        action = _task_identity(heading[0])[0] if heading else ''
        texts = (body,) if completed_subject(_normalize(subject), _normalize(body), action) else (body, subject)
        for text in texts:
            for clause, context in _clauses(text):
                candidate = _candidate(clause)
                if candidate is None:
                    continue
                original, request, polite = candidate
                # A registration heading or closing notice is not a request.
                if (request.startswith('التسجيل ') and not polite
                        and not _REQUIRED.search(context)):
                    continue
                if (unsafe_scope(context, request, polite) or _incomplete(original)
                        or _intent(request, context) != 'obligation'):
                    continue
                candidates.append({
                    'task': original[0].upper() + original[1:],
                    'confidence': _confidence(request, polite),
                })
        return _select(candidates)


_extractor = RuleTaskExtractor()


def extract_tasks(subject: str, body: str) -> list[dict]:
    """Return up to five tasks without external services."""
    return _extractor.extract(subject or '', body or '')


def extract_action_items(subject: str, body: str, reference_datetime: datetime | None = None) -> list[dict]:
    """Use the same tasks, enriched with calendar or event constraints."""
    items = []
    for task in extract_tasks(subject, body):
        deadline = _deadline_for_task(task['task'], reference_datetime)
        items.append({**task,
                      'deadline_text': deadline['deadline_text'] if deadline else None,
                      'deadline_date': deadline['deadline_date'] if deadline else None,
                      'deadline_at': deadline['deadline_at'] if deadline else None,
                      'deadline_confidence': deadline['confidence'] if deadline else None})
    return items
