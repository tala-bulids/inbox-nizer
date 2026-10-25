"""Small same-record bundles; each optional value keeps the resolver's proof."""
import re
from fact_roles import intent, matching_fields, label_role, words
from rag_grounding import format_facts

_EXTRA = {
 'flight_number': {'flight number','flight no','رقم الرحلة'},
 'booking_reference': {'booking reference','booking number','booking pnr','pnr','رقم الحجز','مرجع الحجز','رقم الحجز الخاص بك','your booking reference'},
 'departure_airport': {'departure airport','origin airport','مطار المغادرة'},
 'arrival_airport': {'arrival airport','destination airport','مطار الوصول'},
 'terminal': {'terminal','صالة'}, 'gate': {'gate','بوابة'},
}
_AR={'flight_number':'رقم الرحلة','travel_date':'موعد رحلتك','departure_time':'وقت المغادرة','arrival_time':'وقت الوصول',
     'origin':'المغادرة من','destination':'الوجهة','booking_reference':'رقم الحجز',
     'departure_airport':'مطار المغادرة','arrival_airport':'مطار الوصول','terminal':'الصالة','gate':'البوابة'}


def profile(question):
    request=intent(question)
    if not request:
        return None
    tokens=set(words(question))
    if request['role']=='deadline_date' and tokens&{'invoice','bill','فاتوره','فاتورتي'}:
        return 'finance'
    if request['role']!='travel_date':
        return None
    # Explicit scalar lookups stay scalar; conversational trip questions get context.
    tokens=set(words(question))
    return 'travel' if tokens&{'when','متي','وش'} and not tokens&{'date','تاريخ','only','فقط'} else None


def wanted(question):
    return profile(question) is not None


def bundle(question, anchors, evidence, db=None):
    if len(anchors)!=1 or not wanted(question):
        return anchors
    anchor=anchors[0]; request=intent(question)
    same=[s for s in evidence if s['email_id']==anchor['email_id'] and s.get('chunk_id')==anchor.get('chunk_id')]
    result=[anchor]
    related = ('departure_time','arrival_time','origin','destination') if profile(question)=='travel' else ()
    for role in related:
        matches=matching_fields(dict(request,role=role),same)
        matches=[f for f in matches if f['record_index']==anchor['record_index'] and f['span_basis']==anchor['span_basis']]
        if len(matches)==1:
            result.extend(matches)
    # Optional labelled identifiers/locations must be persisted, same-record facts.
    if anchor['span_basis']=='stored_body':
        extra = _EXTRA if profile(question)=='travel' else _DETAIL_LABELS['finance']
        for role,aliases in extra.items():
            if role=='booking_reference' and db is not None and not unique_booking_reference(db,anchor,aliases):
                continue
            if role=='due_date':
                continue
            fields=[]
            for source in same:
                for field in source.get('fields',[]):
                    same_record=field.get('record_index')==anchor['record_index']
                    if role=='booking_reference' and not same_record and db is not None:
                        same_record=shared_booking_header(db,field,anchor,aliases)
                    if (field.get('span_basis')=='stored_body' and same_record
                        and ' '.join(words(field['label'])) in {' '.join(words(a)) for a in aliases}
                        and field.get('usable',True) and not re.search(r'\b(?:if|unless|not|اذا|ليس|لم)\b',' '.join(words(field['value'])))):
                        fields.append(dict(field,role=role,email_id=anchor['email_id'],chunk_id=anchor['chunk_id'],chunk_index=anchor['chunk_index']))
            unique={f['value']:f for f in fields}
            if len(unique)==1:
                result.append(next(iter(unique.values())))
    return result


def format_bundle(question, facts):
    if len(facts)<2 or not wanted(question):
        return format_facts(facts)
    arabic=bool(re.search('[\u0600-\u06ff]',question))
    if profile(question)=='travel':
        from answer_presentation import human_date
        fields={fact['role']:fact for fact in facts}
        date=fields.get('travel_date')
        if date:
            normalized=date.get('normalization') or {}
            day=human_date(normalized.get('value') if normalized.get('kind')=='date' else date['value'],arabic)
            destination=fields.get('destination',{}).get('value')
            answer=('رحلتك' if arabic else 'Your trip')
            if destination:
                answer+=(' إلى ' if arabic else ' to ')+destination
            answer+=(' يوم ' if arabic else ' is on ')+day+'. '
            remaining=[fact for fact in facts if fact['role'] not in {'travel_date','destination'}]
            pieces=[]
            for fact in remaining:
                label=_AR.get(fact['role'],fact['label']) if arabic else fact['role'].replace('_',' ')
                pieces.append(f"{label}: {fact['value']}")
            answer+=('؛ ' if arabic else '; ').join(pieces)
            return answer.rstrip(' .')+f". [email_id={facts[0]['email_id']}]"
    pieces=[]
    for fact in facts:
        label={**_AR, **_DETAIL_AR, 'deadline_date':'موعد الاستحقاق'}.get(fact['role'],fact['label']) if arabic else fact['role'].replace('_',' ')
        pieces.append(f"{label}: {fact.get('display_value',fact['value'])}")
    return ('؛ ' if arabic else '; ').join(pieces)+f". [email_id={facts[0]['email_id']}]"

# Optional details are chosen by intent, never inferred from the sender.
_DETAIL_LABELS={
 'application': {'organization':{'organization','company','المؤسسة','الجهة'},'application_role':{'position','job title','role','الوظيفة'},'next_step':{'next step','الخطوة التالية'}},
 'event': {'event_name':{'event name','اسم الفعالية'},'event_time':{'event time','وقت الفعالية'},'location':{'location','venue','المكان'},'registration_deadline':{'registration deadline','آخر موعد للتسجيل'}},
 'finance': {'amount_due':{'amount due','invoice amount','المبلغ المستحق'},'company':{'company','الجهة'},'due_date':{'due date','payment deadline','تاريخ الاستحقاق'}},
}
_DETAIL_AR={'organization':'الجهة','application_role':'الوظيفة','next_step':'الخطوة التالية','event_name':'الفعالية','event_time':'الوقت','location':'المكان','registration_deadline':'آخر موعد للتسجيل','amount_due':'المبلغ المستحق','company':'الجهة','due_date':'تاريخ الاستحقاق'}


def details(question, proof, evidence):
    """Attach only persisted facts whose record contains the verified answer span."""
    from rag_status import request as status_request
    tokens=set(words(question))
    kind=('application' if status_request(question) else
          'event' if tokens&{'event','conference','meeting','مؤتمر','فعاليه','اجتماع'} else
          'finance' if tokens&{'invoice','bill','فاتوره','فاتورتي','سداد'} else None)
    if kind is None:
        return []
    candidates={}
    for source in evidence:
        if source['email_id']!=proof['email_id'] or source['chunk_id']!=proof['chunk_id']:
            continue
        for field in source.get('fields',[]):
            if field.get('span_basis')!='stored_body' or not field.get('usable',True):
                continue
            bounds=field.get('record_index','').split(':')
            if len(bounds)!=2 or not all(b.isdigit() for b in bounds):
                continue
            if not int(bounds[0])<=proof['span'][0]<proof['span'][1]<=int(bounds[1]):
                continue
            if re.search(r'\b(?:if|unless|not|اذا|ليس|لم)\b',' '.join(words(field['value']))):
                continue
            for role,aliases in _DETAIL_LABELS[kind].items():
                if ' '.join(words(field['label'])) in {' '.join(words(a)) for a in aliases}:
                    candidates.setdefault(role,{})[field['value']]=dict(field,role=role,email_id=proof['email_id'])
    return [next(iter(items.values())) for items in candidates.values() if len(items)==1]


def append_details(answer, question, fields):
    arabic=bool(re.search('[\u0600-\u06ff]',question))
    if not fields:
        return answer
    text=('؛ ' if arabic else '; ').join(
        f"{_DETAIL_AR[f['role']] if arabic else f['role'].replace('_',' ')}: {f.get('display_value',f['value'])}" for f in fields)
    return answer+'\n'+text+f" [email_id={fields[0]['email_id']}]"


def shared_booking_header(db, field, anchor, aliases):
    """A unique persisted header may describe both legs of its child itinerary."""
    if field.get('span_basis')!='stored_body':
        return False
    label=' '.join(words(field['label']))
    accepted={' '.join(words(a)) for a in aliases}
    if label not in accepted:
        return False
    parent=field.get('record_index','').split(':')
    child=str(anchor['record_index']).split(':')
    if len(parent)!=2 or len(child)!=2 or not all(v.isdigit() for v in parent+child):
        return False
    a,b=map(int,parent);x,y=map(int,child)
    if not a<=field['span'][0]<field['span'][1]<=x<y<=b:
        return False
    from sqlalchemy import select
    from models import EmailFact
    # A second booking anywhere in this owned document blocks header inheritance.
    facts=db.scalars(select(EmailFact).where(EmailFact.email_id==anchor['email_id'])).all()
    values={f.literal_value for f in facts if ' '.join(words(f.source_label)) in accepted}
    return values=={field['value']}


def unique_booking_reference(db, anchor, aliases):
    from sqlalchemy import select
    from models import EmailFact
    accepted={' '.join(words(a)) for a in aliases}
    facts=db.scalars(select(EmailFact).where(EmailFact.email_id==anchor['email_id'])).all()
    return len({f.literal_value for f in facts if ' '.join(words(f.source_label)) in accepted})==1
