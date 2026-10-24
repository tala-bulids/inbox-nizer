"""Presentation order after semantic relevance selection."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def message_timestamp(email):
    value = email.sent_at or email.message_at
    if value is None and email.email_date:
        try:
            value = parsedate_to_datetime(email.email_date)
        except (TypeError, ValueError, OverflowError):
            return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    return value.astimezone(timezone.utc)


def newest_first(matches):
    floor = datetime.min.replace(tzinfo=timezone.utc)
    return sorted(matches, key=lambda item: message_timestamp(item['email']) or floor, reverse=True)
