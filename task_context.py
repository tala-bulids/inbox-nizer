"""Grammatical scope checks for local task clauses; no sender rules."""
import re
CONDITION = re.compile(r'^(?:if|unless|only if|provided that|اذا|ان كنت|في حال|فقط اذا)\b', re.I)
OTHER_ACTOR = re.compile(r'^(?:(?:we|i|they|he|she|our (?:team|staff)|the (?:team|company))\b|(?:سيقوم|سوف يقوم|سنقوم|سوف نقوم|قام|قامت)\b)', re.I)
NEGATED = re.compile(r'^(?:do not|don.t|never|no need to|not required to|لا\b|ليس\b|لن\b)', re.I)
STATUS = re.compile(r'\b(?:has been|have been|was|were|is being|are being|is optional|already (?:paid|submitted|sent))\b|(?:\bتم\b|\bقيد\b|اختياري|مغلق|اصبح|اصبحت)', re.I)
FOOTER_CONTEXT = re.compile(r'\b(?:unsubscribe|opt out|stop receiving)\b|الغاء الاشتراك', re.I)

def unsafe_scope(context, clause, polite):
    # An explicit new request can change actor; a bare coordinated verb cannot.
    if FOOTER_CONTEXT.search(context):
        return True
    if NEGATED.match(context):
        return True
    if clause != context and not polite:
        if OTHER_ACTOR.match(context) or ':' in context.split(clause, 1)[0]:
            return True
    return bool(STATUS.search(clause) and not polite)

COMPLETION = re.compile(r'\b(?:has been|have been|was|were)\s+(?:paid|submitted|sent|completed|confirmed|uploaded|received)\b|\b(?:already|successfully)\s+(?:paid|submitted|sent|completed|confirmed|uploaded)\b|(?:^|\s)تم\s+(?:دفع|سداد|ارسال|اكمال|تاكيد|رفع|التسجيل)', re.I)

_COMPLETED_ACTIONS = {
    'pay': r'paid|دفع|سداد', 'submit': r'submitted|تقديم',
    'send': r'sent|ارسال', 'complete': r'completed|اكمال',
    'confirm': r'confirmed|تاكيد', 'upload': r'uploaded|رفع',
    'register': r'registered|التسجيل',
}

def completed_subject(subject, body, action):
    """A completed object in the opening status cannot create a subject-only task."""
    opening = re.split(r'[.!?؟\n]', body, maxsplit=1)[0]
    forms = _COMPLETED_ACTIONS.get(action)
    if not forms or not COMPLETION.search(opening) or not re.search(r'\b(?:' + forms + r')\b', opening):
        return False
    ignored = set('the a an your my our please kindly it you has have been was were already تم بنجاح يرجى'.split())
    def objects(text):
        return {w[2:] if w.startswith('ال') and len(w)>3 else w
                for w in re.findall(r'\w+',text)
                if w not in ignored and w != action and not re.fullmatch(forms, w)}
    return bool(objects(subject) & objects(opening))
