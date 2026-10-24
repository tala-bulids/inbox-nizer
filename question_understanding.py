"""Question-only morphology. Literal source values are never rewritten."""
# Small verb paradigms compose with question roles and arbitrary place qualifiers.
TRAVEL_VERBS = {'اسافر', 'نسافر', 'سنسافر', 'ساسافر', 'بسافر', 'باسافر', 'بنسافر', 'حسافر', 'حنسافر', 'هسافر', 'هنسافر', 'بروح', 'اروح', 'بنروح', 'نروح'}
DEPARTURE_VERBS = {'بطلع', 'اطلع', 'بنطلع', 'نطلع'}
ARRIVAL_VERBS = {'اوصل', 'اصل', 'نوصل', 'نصل', 'بوصل', 'باوصل', 'بنوصل', 'ساوصل', 'ساصل'}

def normalize(tokens):
    verbs = TRAVEL_VERBS | ARRIVAL_VERBS | DEPARTURE_VERBS
    result = []
    for index, token in enumerate(tokens):
        if token in {'ب', 'راح', 'رح', 'سوف'} and index + 1 < len(tokens) and tokens[index+1] in verbs:
            continue
        if token in {'am', 'i', 'حقي'}:
            continue
        if token in {'travelling', 'traveling', 'flying'}:
            token = 'travel'
        if token in TRAVEL_VERBS:
            token = 'سفر'
        elif token in DEPARTURE_VERBS:
            token = 'مغادره'
        elif token in ARRIVAL_VERBS:
            token = 'وصول'
        elif token in {'امتي', 'امتا'}:
            token = 'متي'
        result.append(token)
    return result

DEADLINE_LABELS = {'deadline', 'registration deadline', 'payment deadline', 'due date', 'last date', 'آخر يوم', 'آخر موعد', 'الموعد النهائي', 'الموعد الأخير', 'آخر يوم للتسجيل', 'آخر موعد للتقديم'}

def deadline_tokens(tokens):
    values=set(tokens)
    return (bool(values & {'due'}) and bool(values & {'when','متي'}) and bool(values & {'invoice','bill','فاتوره','فاتورتي'}) or bool(values & {'deadline'}) or {'due','date'} <= values or
            bool(values & {'اخر','نهائي','اخير'}) and bool(values & {'موعد','يوم','تاريخ'}))
