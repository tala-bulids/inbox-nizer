"""Application-composed dates and scope labels; source text remains literal."""
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime

_MONTHS = {
    'en': 'January February March April May June July August September October November December'.split(),
    'ar': 'يناير فبراير مارس أبريل مايو يونيو يوليو أغسطس سبتمبر أكتوبر نوفمبر ديسمبر'.split(),
}


def human_date(value, arabic=False):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            try:
                value = parsedate_to_datetime(value)
            except (ValueError, TypeError, OverflowError):
                try:
                    value = datetime.strptime(value, '%d-%b-%Y').date()
                except ValueError:
                    return value
    if not isinstance(value, (date, datetime)):
        return 'تاريخ غير متاح' if arabic else 'date unavailable'
    if isinstance(value, datetime) and value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return f"{value.day} {_MONTHS['ar' if arabic else 'en'][value.month - 1]} {value.year}"


def period_label(start, end, arabic=False):
    zone = 'بالتوقيت العالمي' if arabic else 'UTC'
    return f'{human_date(start, arabic)} – {human_date(end, arabic)} ({zone})'
