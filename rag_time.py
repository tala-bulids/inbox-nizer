"""Bounded message-time intent, independent of event dates and Search."""
import re
from datetime import datetime, timedelta, timezone
from fact_roles import words


def now():
    return datetime.now(timezone.utc)


def scope(question, reference=None, *, default_recent=True):
    from fact_roles import intent
    role=intent(question)
    if role and role['role'] in {'travel_date','departure_time','arrival_time'}:
        return None  # Trip timing refers to the event, not the email timestamp.
    tokens=words(question)
    value=' '.join(tokens)
    current=reference or now()
    day=current.replace(hour=0,minute=0,second=0,microsecond=0)
    start=end=None
    if re.search(r'\b(?:اليوم|today)\b',value):
        start,end=day,day+timedelta(days=1)
    elif re.search(r'\b(?:امس|yesterday)\b',value):
        start,end=day-timedelta(days=1),day
    elif re.search(r'اخر اسبوعين|last (?:two|2) weeks|past (?:two|2) weeks',value):
        start,end=current-timedelta(days=14),current
    elif re.search(r'اسبوع ماضي|last week',value):
        end=day-timedelta(days=day.weekday());start=end-timedelta(days=7)
    elif re.search(r'هذا اسبوع|هالاسبوع|this week',value):
        start,end=day-timedelta(days=day.weekday()),current
    elif re.search(r'هذا شهر|this month',value):
        start,end=day.replace(day=1),current
    elif (set(tokens)&{'recent','recently','latest','new','مؤخرا','قريب','جديد','اخر','انقبلت','قبول'}
          and (status_intent(question) or set(tokens)&{'recent','recently','latest','مؤخرا','جديد'})):
        start,end=current-timedelta(days=14),current
    if start is None and default_recent:
        from rag_status import request
        if request(question):
            start,end=current-timedelta(days=14),current
        else:
            return None
    if start is None:
        return None
    from answer_presentation import period_label
    return {'start':start,'end':end,'label':period_label(start,end,bool(re.search('[\u0600-\u06ff]',question)))}


def status_intent(question):
    tokens=set(words(question))
    return bool(tokens&{'application','applications','accepted','acceptance','status','طلبي','طلباتي','طلب','معسكر','بمعسكر','قبول','انقبلت','جامعه','تحديث'}
                or {'جاني','جديد'}<=tokens)


def constrain(statement, question):
    window=scope(question)
    if window is None:
        return statement
    from sqlalchemy import select,func
    from models import Email,EmailEmbeddingChunk
    timestamp=func.coalesce(Email.message_at,Email.sent_at)
    owned=select(Email.id).where(timestamp>=window['start'],timestamp<window['end'])
    return statement.where(EmailEmbeddingChunk.email_id.in_(owned))


def no_evidence(question, window):
    arabic=bool(re.search('[\u0600-\u06ff]',question))
    message = (f"لم أجد رسالة تجيب عن سؤالك خلال {window['label']}."
               if arabic else f"I found no supporting email for {window['label']}.")
    if status_intent(question):
        message += ' هذا لا يثبت القبول أو الرفض.' if arabic else ' This does not establish acceptance or rejection.'
    return message
