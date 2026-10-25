"""Literal status evidence for conversational questions; absence is not rejection."""
import re
from fact_roles import words, STOP

_GRAMMAR=set('وش ما ماذا هل صار علي على في من عن ب لي جاني جاء وصلني وصلني شي شيء جديد انقبلت قبلوني قبول طلبي طلباتي طلب طلبات تقديم حاله اخر تحديث اسبوع اسبوعين ماضي هذا شهر اليوم امس قريب مؤخرا متي what is has happened to my applications application status latest recent recently last week weeks two 2 past this month today yesterday did i get accepted acceptance any new update updates from'.split())
_STATUS=re.compile(
 r'\b(?:your application(?: for .{1,80}?)? (?:is|was|has been) (?:under review|being reviewed|accepted|approved|rejected|unsuccessful)|'
 r'you (?:have been|were|have) (?:not (?:been )?)?(?:accepted|admitted|selected)|we (?:have )?(?:received|rejected|accepted) your application)\b|'
 r'(?:تم (?:قبول|رفض|استلام|ترشيح)\s*(?:طلبك|طلبكم|ترشيحك)|تم قبولك|تم ترشيحك|تم رفضك|لم يتم قبول طلبك|طلبك (?:قيد مراجعه|مقبول|مرفوض))',re.I)
_CONDITIONAL=re.compile(r'\b(?:if|unless|might|would|example|old|previous|اذا|لو|ربما|مثال|سابق|قديم)\b',re.I)
_DOMAINS={'معسكر':{'معسكر','بمعسكر','معسكرات','bootcamp'},'جامعه':{'جامعه','university'}}


def request(question):
    tokens=words(question)
    tokens = ['تحديث' if t == 'تحديثات' else t for t in tokens]
    if not tokens or not set(tokens)&{'صار','جاني','انقبلت','قبلوني','وصلني','تحديث','recent','recently','latest','accepted','acceptance'}:
        return None
    if set(tokens)&{'why','how','لماذا','كيف','except','عدا','not','لا'}:
        return None
    domains=[key for key,values in _DOMAINS.items() if set(tokens)&values]
    used=_GRAMMAR | STOP | set().union(*_DOMAINS.values())
    qualifiers=set(tokens)-used
    return dict(kind='status',qualifiers=qualifiers,domains=domains)


def proofs(query,email,chunk):
    from rag_extractive import _units, _STATUS as established_status
    context=set(words((email.subject or '')+' '+chunk['text']))
    if not query['qualifiers']<=context:
        return []
    if any(not context&_DOMAINS[d] for d in query['domains']):
        return []
    found=[]
    for offset,unit in _units(chunk['text']):
        normalized=' '.join(words(unit))
        if not (_STATUS.search(normalized) or established_status.search(unit)) or _CONDITIONAL.search(normalized):
            continue
        start=(email.body or '').find(unit)
        if start<0 or (email.body or '').find(unit,start+1)>=0:
            continue
        found.append(dict(email_id=email.id,chunk_id=chunk['chunk_id'],chunk_index=chunk['chunk_index'],kind='status',
            value=unit,span=[start,start+len(unit)],evidence=unit,evidence_span=[start,start+len(unit)],
            chunk_span=[offset,offset+len(unit)],span_basis='stored_body',subject=email.subject or '',date=email.email_date or ''))
    return found


def latest_same_application(proofs, emails, question):
    """Recency breaks ties only for the same explicitly identified application."""
    from rag_time import scope
    from rag_grounding import explicit_fields
    from rag_evidence import _records
    if len(proofs)<2 or scope(question) is None:
        return proofs
    identities=[];dated=[]
    for proof in proofs:
        email=emails[proof['email_id']]
        timestamp=email.message_at or email.sent_at
        if timestamp is None:
            return proofs
        spans=_records(email.body or '') or [(0,len(email.body or ''))]
        bounds=next(((a,b) for a,b in spans if a<=proof['span'][0]<proof['span'][1]<=b),None)
        if bounds is None:
            return proofs
        fields=explicit_fields(email.body[bounds[0]:bounds[1]])
        def values(labels):
            return {f['value'].casefold() for f in fields if ' '.join(words(f['label'])) in labels and f['usable']}
        ids=values({'application id','application reference','رقم طلب','مرجع طلب'})
        organizations=values({'organization','company','جهه','مؤسسه'})
        if len(ids)!=1 or len(organizations)!=1:
            return proofs
        identities.append((next(iter(ids)),next(iter(organizations))))
        dated.append((timestamp,proof))
    if len(set(identities))!=1:
        return proofs
    latest=max(t for t,_ in dated)
    winners=[p for t,p in dated if t==latest]
    return winners if len(winners)==1 else proofs
