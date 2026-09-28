"""Local Gregorian deadlines. Scores are rule strengths, not probabilities."""
import calendar
import re
from datetime import date, datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime


_MONTHS = {}
for number, names in enumerate([
    'january jan يناير', 'february feb فبراير', 'march mar مارس', 'april apr ابريل أبريل',
    'may مايو', 'june jun يونيو', 'july jul يوليو', 'august aug اغسطس أغسطس',
    'september sep sept سبتمبر', 'october oct اكتوبر أكتوبر',
    'november nov نوفمبر', 'december dec ديسمبر',
], 1):
    for name in names.split():
        _MONTHS[name] = number
_DAYS = {}
for number, names in enumerate([
    'monday mon الاثنين الإثنين', 'tuesday tue الثلاثاء', 'wednesday wed الاربعاء الأربعاء',
    'thursday thu الخميس', 'friday fri الجمعة', 'saturday sat السبت', 'sunday sun الاحد الأحد',
]):
    for name in names.split():
        _DAYS[name] = number
_MONTH = '(?:' + '|'.join(sorted(_MONTHS, key=len, reverse=True)) + ')'
_WEEKDAY = '(?:' + '|'.join(sorted(_DAYS, key=len, reverse=True)) + ')'
_CALENDAR = (rf'(?:\d{{4}}-\d{{1,2}}-\d{{1,2}}|'
             rf'\d{{1,2}}(?:st|nd|rd|th)?[ -]+{_MONTH}(?:[ ,/-]+\d{{4}})?|'
             rf'{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:[ ,]+\d{{4}})?|'
             rf'(?:next\s+)?{_WEEKDAY}|tomorrow|today|غدا|اليوم|نهاية الشهر|(?:the )?end of (?:the )?month)')
_EVENT = r'(?:arriving at the airport|arrival at the airport|arrival|arriving|the meeting|الوصول الى المطار|الوصول|الاجتماع)'
_PREFIX = r'(?:no later than|deadline(?: is|:)?|due (?:on|by)|by|before|on|بحلول|قبل|الموعد النهائي(?: هو|:)?|مستحق في|(?:اخر (?:يوم|موعد)|الموعد الاخير)(?:\s+ل\w+)?(?:\s+هو)?)'
_CLOCK = r'(?:\s+(?:at|الساعة)\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|صباحا|مساء|مساءا)?(?:\s*(?:UTC|GMT|[+-]\d{2}:?\d{2}))?)'
_PHRASE = re.compile(
    rf'(?<!\w)(?:(?:{_PREFIX})\s+(?:يوم\s+)?(?:{_WEEKDAY}\s+الموافق\s+)?(?P<value>{_CALENDAR}|{_EVENT})|'
    rf'(?P<relative>tomorrow|today|غدا|اليوم)(?![\x27’]s\b))(?P<clock>{_CLOCK})?(?!\w)', re.I
)
_DATE_ORDER = re.compile(rf'^(?P<day>\d{{1,2}})(?:st|nd|rd|th)?[ -]+(?P<month>{_MONTH})(?:[ ,/-]+(?P<year>\d{{4}}))?$', re.I)
_MONTH_ORDER = re.compile(rf'^(?P<month>{_MONTH})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?(?:[ ,]+(?P<year>\d{{4}}))?$', re.I)
_TIME = re.compile(r'(?:at|الساعة)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm|صباحا|مساء|مساءا)?\s*(UTC|GMT|[+-]\d{2}:?\d{2})?$', re.I)


def parse_email_datetime(value: str | None) -> datetime | None:
    """Read an email Date header without choosing a local timezone."""
    try:
        return parsedate_to_datetime(value) if value else None
    except (TypeError, ValueError, OverflowError, IndexError):
        return None


def _normalized(text):
    # Remember offsets so deadline_text keeps accents and Arabic diacritics.
    letters, offsets = [], []
    for index, char in enumerate(text):
        if re.match(r'[\u064b-\u065f\u0670\u0640]', char):
            continue
        for letter in char.casefold().translate(str.maketrans('أإآ', 'ااا')):
            letters.append(letter)
            offsets.append(index)
    offsets.append(len(text))
    return ''.join(letters), offsets


def _resolve_date(value, reference):
    base = reference.date() if reference else None
    if value in {'tomorrow', 'غدا', 'today', 'اليوم'}:
        return base + timedelta(days=value in {'tomorrow', 'غدا'}) if base else None
    weekday = value.removeprefix('next ')
    if weekday in _DAYS:
        if base is None:
            return None
        distance = (_DAYS[weekday] - base.weekday()) % 7
        if value.startswith('next ') and distance == 0:
            distance = 7
        return base + timedelta(days=distance)
    if value in {'نهاية الشهر', 'end of month', 'end of the month', 'the end of the month'}:
        return date(base.year, base.month, calendar.monthrange(base.year, base.month)[1]) if base else None
    if re.fullmatch(r'\d{4}-\d{1,2}-\d{1,2}', value):
        return date(*(int(part) for part in value.split('-')))
    match = _DATE_ORDER.fullmatch(value) or _MONTH_ORDER.fullmatch(value)
    if not match:
        return None
    year = int(match['year']) if match['year'] else (base.year if base else None)
    if year is None:
        return None
    result = date(year, _MONTHS[match['month']], int(match['day']))
    # A missing year means the next occurrence relative to this message.
    if not match['year'] and result < base:
        result = result.replace(year=year + 1)
    return result


def _resolve_time(clock, day, reference):
    match = _TIME.fullmatch(clock.strip())
    if not match or day is None:
        return None
    hour, minute = int(match[1]), int(match[2] or 0)
    meridiem, zone = match[3], match[4]
    if meridiem:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if meridiem in {'pm', 'مساء', 'مساءا'} else 0)
    tz = reference.tzinfo if reference else None
    if zone:
        if zone.upper() in {'UTC', 'GMT'}:
            tz = timezone.utc
        else:
            digits = zone[1:].replace(':', '')
            hours, minutes = int(digits[:2]), int(digits[2:])
            if hours > 23 or minutes > 59:
                return None
            tz = timezone(timedelta(minutes=(hours * 60 + minutes) * (-1 if zone[0] == '-' else 1)))
    # Do not let PostgreSQL silently assign its timezone to an unknown wall time.
    if tz is None:
        return None
    return datetime.combine(day, time(hour, minute, tzinfo=tz))


def _deadline_for_task(text, reference_datetime=None):
    """Parse timing only after the shared task pipeline accepts the request."""
    normalized, offsets = _normalized(text)
    match = _PHRASE.search(normalized)
    if not match:
        return None
    original = text[offsets[match.start()]:offsets[match.end()]].strip()
    day = moment = None
    try:
        day = _resolve_date(match['value'] or match['relative'], reference_datetime)
        if match['clock']:
            moment = _resolve_time(match['clock'], day, reference_datetime)
    except (ValueError, OverflowError):
        # Keep the constraint even when it cannot safely become a calendar value.
        pass
    return {'deadline_text': original, 'deadline_date': None if moment else day,
            'deadline_at': moment, 'confidence': 0.9 if day else 0.7}


def extract_deadline(text: str, reference_datetime: datetime | None = None) -> dict | None:
    """Return the first task-linked constraint; unrelated dates are ignored.

    Relative dates require a supplied reference. Date-only constraints have no
    invented midnight. Unknown timezones remain unparsed in deadline_text.
    """
    from task_extractor import extract_tasks
    for task in extract_tasks('', text):
        deadline = _deadline_for_task(task['task'], reference_datetime)
        if deadline:
            return deadline
    return None
