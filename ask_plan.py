"""Small query plans; conversation supplies a topic, never answer evidence."""
from dataclasses import dataclass
import re
from fact_roles import words, intent, STOP
from rag_time import scope, now
from datetime import timedelta


@dataclass(frozen=True)
class QueryPlan:
    kind: str
    question: str
    window: dict | None = None
    entity: tuple = ()
    newsletter: bool = False
    selected: int | None = None


def effective_question(question, history=()):
    tokens=words(question)
    # Only a short explicit narrowing inherits the previous topic.
    if history and len(tokens)<=8 and set(tokens)&{'بس','فقط','only'}:
        qualifier=[t for t in tokens if t not in {'طيب','بس','فقط','only','just','and','what','about'}]
        if qualifier:
            previous=history[-1]
            if isinstance(previous,str) and 0<len(previous)<=2000:
                return previous+' '+ ' '.join(qualifier)
    return question


def plan(question, email_id=None, history=()):
    question=effective_question(question,history)
    tokens=words(question); values=set(tokens)
    window=scope(question)
    if email_id is not None:
        return QueryPlan('selected_email',question,window,selected=email_id)
    existence=bool(values&{'استلمت','وصلتني','وصلني','جاني','received','receive','get','got'}) and bool(values&{'هل','did','have','any','اي'})
    if existence:
        marker=next((i for i,t in enumerate(tokens) if t in {'from','من'}),None)
        entity=tuple(tokens[marker+1:]) if marker is not None else ()
        entity=tuple(t for t in entity if t not in {'recently','today','yesterday','اليوم','امس','مؤخرا',
            'last','week','weeks','two','2','past','this','month','اخر','اسبوع','اسبوعين','هذا','شهر','ماضي'})
        if entity:
            return QueryPlan('existence',question,scope(question,default_recent=False),entity,
                             bool(values&{'نشره','نشرات','newsletter','newsletters','digest'}))
    broad=bool(values&{'مستجدات','updates','changed','جاني','وصلني','اهم'})
    temporal=bool(values&{'اخر','recent','recently','latest','هالاسبوع','اسبوع','اسبوعين','اليوم','today','week','weeks','هذا'})
    domains=values&{'طلبي','طلباتي','application','applications','رحلتي','flight','معسكر','جامعه'}
    if broad and temporal and not domains:
        if window is None:
            current=now();start=current-timedelta(days=14)
            if 'هالاسبوع' in values:
                start=current.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=current.weekday())
            from answer_presentation import period_label
            window=dict(start=start,end=current,label=period_label(start,current,bool(re.search('[\u0600-\u06ff]',question))))
        return QueryPlan('recent_digest',question,window)
    from rag_status import request
    if request(question):
        return QueryPlan('recent_status',question,window)
    if values&{'تفاصيل','details','itinerary'} and values&{'رحلتي','رحله','trip','flight','travel'}:
        remaining=[t for t in tokens if t not in {'عطني','اعطني','تفاصيل','details','show','me','my','itinerary'}]
        canonical=('متى ' if re.search('[\u0600-\u06ff]',question) else 'when ')+ ' '.join(remaining)
        return QueryPlan('record_summary',canonical,window)
    return QueryPlan('fact_lookup' if intent(question) else 'open_synthesis',question,window)
