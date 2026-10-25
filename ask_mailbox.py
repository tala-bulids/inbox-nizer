"""Owned metadata/temporal lanes and an application-owned supported answer plan."""
from dataclasses import dataclass
from email.utils import parseaddr
import re
from sqlalchemy import select,func,or_
from models import Email,EmailEmbeddingChunk
from fact_roles import words

LIMIT=120


def normalized(column):
    return func.lower(func.translate(func.coalesce(column,''),'أإآىة','ااايه'))


def lexical_condition(entity, columns):
    return [or_(*(normalized(c).contains(token,autoescape=True) for c in columns)) for token in entity]


def candidates(db,plan):
    statement=select(Email)
    stamp=func.coalesce(Email.message_at,Email.sent_at)
    if plan.window:
        statement=statement.where(stamp>=plan.window['start'],stamp<plan.window['end'])
    if plan.entity:
        # Sender constraint cannot be satisfied by a forwarded name in the body.
        statement=statement.where(*lexical_condition(plan.entity,[Email.sender]))
    return db.scalars(statement.order_by(stamp.desc().nullslast(),Email.id.desc()).limit(LIMIT+1)).all()


@dataclass
class SupportedItem:
    email: object
    text: str
    basis: str
    span: tuple | None = None
    importance: int = 0


@dataclass
class AnswerPlan:
    intent: str
    period: str | None
    items: list
    truncated: bool = False
    negative_evidence_type: str = 'no_matching_evidence'
    more_matches: bool = False


def plain(text):
    return re.sub(r'[\x00-\x1f<>\[\]]',' ',text or '').strip()


def meaningful(email):
    """Complete literal sentences; no tasks or classifier labels used as truth."""
    from rag_extractive import _units
    signals = [
        (5, r'\b(?:security alert|unusual sign.in|new sign.in|suspicious activity|password (?:changed|reset))\b|تنبيه امني|تسجيل دخول|نشاط مشبوه'),
        (4, r'\b(?:accepted|rejected|under review|not selected)\b|تم قبول|تم رفض|لم يتم قبول|قيد مراجعه'),
        (3, r'\b(?:payment due|amount due|overdue|deadline|payment deadline)\b|مبلغ مستحق|موعد نهائي|اخر موعد|فاتوره مستحقه'),
        (2, r'\b(?:booking|flight.{0,30}(?:changed|cancelled|delayed)|reservation)\b|تاكيد حجز|تغيير رحله|الغاء رحله'),
        (1, r'\b(?:meeting.{0,30}(?:changed|rescheduled)|action required)\b|تغيير موعد|موعد اجتماع'),
    ]
    noise=r'\b(?:shop now|buy now|discount|sale|unsubscribe|privacy policy)\b|تسوق|خصم|اشتر|الغاء اشتراك'
    choices = []
    for offset,unit in _units(email.body or ''):
        text = ' '.join(words(unit))
        importance = max((score for score, pattern in signals if re.search(pattern,text,re.I)),default=0)
        if 15<=len(unit)<=500 and importance and not re.search(noise,text,re.I):
            choices.append(SupportedItem(email,unit,'body',(offset,offset+len(unit)),importance))
    return max(choices,key=lambda item:item.importance,default=None)


def thread_key(email):
    """Use explicit RFC references only, not a coincidental subject match."""
    payload = email.raw_payload or {}
    headers = {h.get('name','').lower(): h.get('value','') for h in payload.get('headers',[])
               if isinstance(h,dict)}
    for name in ('references','in-reply-to','message-id'):
        ids = re.findall(r'<[^<>\s]+>',headers.get(name,''))
        if ids:
            return email.account_id, ids[0]
    return email.account_id, email.id


def build_answer_plan(db,plan):
    rows=candidates(db,plan);items=[];seen=set();threads=set()
    for email in rows[:LIMIT]:
        if plan.kind=='existence':
            if not set(plan.entity)<=set(words(email.sender or '')):
                continue
            content=' '.join(words((email.subject or '')+' '+(email.body or '')[:12000]))
            if plan.newsletter and not re.search(r'\b(?:newsletter|digest|نشره|اسبوعيه|weekly)\b',content):
                continue
            item=SupportedItem(email,email.subject or '', 'metadata')
        else:
            item=meaningful(email)
            if item is None:
                continue
        if plan.kind != 'existence':
            fingerprint=(email.sender or '', ' '.join(words(item.text)))
            thread=thread_key(email)
            if fingerprint in seen or thread in threads:
                continue
            seen.add(fingerprint);threads.add(thread)
        items.append(item)
    # Stable order retains recency within the same importance tier. Thread rows
    # were read newest first, so a stale status cannot replace its later update.
    if plan.kind != 'existence':
        items.sort(key=lambda item:-item.importance)
    return AnswerPlan(plan.kind,plan.window['label'] if plan.window else None,items[:5],
                      len(rows)>LIMIT,more_matches=len(items)>5)


def render(db,query,answer):
    arabic=bool(re.search('[\u0600-\u06ff]',query))
    if not answer.items:
        period=f' ({answer.period})' if answer.period else ''
        message=('لم أجد رسالة مطابقة ضمن الرسائل التي فحصتها' if arabic else 'I found no matching evidence in the messages examined')+period+'.'
        return dict(status='insufficient_evidence',answer=message,sources=[],citations=[])
    from answer_presentation import human_date
    sources=[];lines=[];verified=[]
    for item in answer.items:
        email=item.email
        if item.basis=='body':
            a,b=item.span
            if (email.body or '')[a:b]!=item.text:
                continue
        # Metadata evidence does not require embeddings. Zero denotes no chunk.
        chunk=db.scalar(select(EmailEmbeddingChunk).where(EmailEmbeddingChunk.email_id==email.id).order_by(EmailEmbeddingChunk.chunk_index).limit(1))
        stamp=email.message_at or email.sent_at
        date=stamp.isoformat() if stamp else ('تاريخ غير متاح' if arabic else 'date unavailable')
        label = plain(email.subject or '')
        # Keep the complete source sentence, including conditions and negation.
        lines.append(f'- {label}: {plain(item.text)} [email_id={email.id}]' if label
                     else f'- {plain(item.text)} [email_id={email.id}]')
        verified.append(item)
        sources.append(dict(email_id=email.id,chunk_id=chunk.id if chunk else 0,chunk_index=chunk.chunk_index if chunk else 0,score=1.0,subject=email.subject or '',**{'from':email.sender or ''},date=date))
    if not lines:
        return dict(status='insufficient_evidence',answer='No verified evidence.',sources=[],citations=[])
    if answer.intent == 'existence':
        count=len(verified)
        lower_bound=answer.more_matches or answer.truncated
        names={parseaddr(item.email.sender or '')[0].strip('"') for item in verified}
        name=plain(next(iter(names))) if len(names)==1 else ''
        sender=(' من ' if arabic else ' from ')+name if name else ''
        amount=(f'{count} على الأقل' if arabic else f'at least {count}') if lower_bound else str(count)
        text=(f'نعم، وجدت {amount} رسائل تطابق سؤالك{sender}.' if arabic
              else f'Yes, I found {amount} matching {"email" if count==1 else "emails"}{sender}.')
        if answer.period:
            text+=(' خلال ' if arabic else ' During ')+answer.period+'.'
        stamps=[item.email.message_at or item.email.sent_at for item in verified]
        if all(stamps):
            text+=(' أحدث هذه الرسائل وصلت يوم ' if arabic else ' The latest of these arrived on ')+human_date(max(stamps),arabic)+'.'
        text+=' '+' '.join(f'[email_id={item.email.id}]' for item in verified)
    else:
        heading=('أبرز ما وجدته في رسائلك' if arabic else 'Highlights from your emails')
        if answer.period:
            heading+=(' خلال ' if arabic else ' for ')+answer.period
        if answer.truncated:
            heading+=(' (ضمن أحدث 120 رسالة)' if arabic else ' (among the latest 120 messages)')
        # The first line shares a citation with the scope heading.
        text=heading+': '+ '\n'.join(lines)
    from rag_service import _validate_citations
    sources=list({source['email_id']:source for source in sources}.values())
    _validate_citations(text,sources)
    return dict(status='answered',answer=text,sources=sources,citations=[{'email_id':s['email_id']} for s in sources],answer_mode='extractive',verification='source_supported')
