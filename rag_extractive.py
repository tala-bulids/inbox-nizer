"""Literal answer spans from authorized retrieved content, never model prose."""
import re
import unicodedata
from sqlalchemy import select
from sqlalchemy.orm import load_only
from models import Email
from fact_roles import intent as fact_intent
from rag_evidence import select_evidence

MAX_AUDIT_CHUNKS = 64
_STOP = set('what when is are was has happened with to my your the a an in on at for of please tell me about regarding i do need should ما متي وش هو هي حاله حال حالة طلب طلبي الطلب طلبك في من الي عن ماذا حدث بخصوص احتاج علي ان افعل الاجراء المطلوب'.split())
_KINDS = {
    'status': {'status','application','applications','حاله','طلب','طلبي','تقديم'},
    'date': {'date','dates','event','conference','meeting','موعد','تاريخ','فعاليه','مؤتمر','اجتماع'},
    'action': {'action','actions','do','need','required','افعل','اجراء','مطلوب','احتاج'},
}
_UNSAFE = re.compile(r'\b(?:if|unless|might|possibly|not|never|old|previous|example|cancelled|canceled|ignore|assistant|system|pretend|output|اذا|لو|ربما|ليس|لم|ملغي|مثال|تجاهل)\b',re.I)
_MONTH = (r'January|February|March|April|May|June|July|August|September|October|November|December|'
          r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec|يناير|فبراير|مارس|أبريل|ابريل|مايو|يونيو|يوليو|أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر')
_DATE = re.compile(rf'(?<!\w)(?:\d{{1,2}}(?:\s*[-–—]\s*\d{{1,2}})?[\s-]+(?:{_MONTH})[\s,-]+\d{{4}}|\d{{4}}-\d{{2}}-\d{{2}})(?!\w)',re.I)
_STATUS = re.compile(
    r'\b(?:(?:we|our team) (?:are |is )?(?:currently )?reviewing your application|'
    r'(?:we have|we.ve) received your application|'
    r'your application(?: for .{1,100}?)? (?:is|has been|was|has) (?:currently )?'
    r'(?:under review|being reviewed|received|accepted|approved|rejected|unsuccessful|moved to the next stage))\b|'
    r'(?:طلبك|الطلب)\s+(?:حاليًا\s+|حاليا\s+)?(?:قيد المراجعة|تحت المراجعة|مقبول|مرفوض)|'
    r'تم\s+(?:استلام|قبول|رفض)\s+طلبك',re.I)
_ACTION = re.compile(r'^(?:please (?:register|submit|upload|reply|confirm|complete|pay)|'
    r'(?:register|submit|upload|reply|confirm|complete|pay) .{1,100}? to (?:complete|confirm)|'
    r'you (?:must|need to|are required to) |يرجى (?:التسجيل|رفع|إرسال|ارسال|الرد|دفع|إكمال)|'
    r'لاستكمال .{1,60}?[،,]\s*(?:نأمل|يرجى) التسجيل)',re.I)


def tokens(text):
    text=unicodedata.normalize('NFKC',text).casefold()
    text=re.sub(r'[\u064b-\u065f\u0670\u0640]','',text).translate(str.maketrans('أإآىة','ااايه'))
    return [w[2:] if w.startswith('ال') and len(w)>3 else w
            for w in re.findall(r'[^\W_]+(?:&[^\W_]+)*',text)]


def question_intent(question):
    from rag_status import request as status_request
    conversational = status_request(question)
    if conversational:
        return conversational
    words=tokens(question)
    if not words or fact_intent(question):
        return None
    if words[0] not in {'what','when','ما','متي','وش','ماذا'}:
        return None
    if set(words) & {'why','explain','compare','summarize','difference','not','except','لماذا','كيف','قارن','لخص','ليس'}:
        return None
    if words[0] in {'when','متي'} or set(words) & {'date','dates','تاريخ','موعد'}:
        kind='date'
    elif set(words) & _KINDS['action']:
        kind='action'
    elif set(words) & _KINDS['status']:
        kind='status'
    else:
        return None
    qualifiers=set(words)-_STOP-_KINDS[kind]
    return dict(kind=kind,qualifiers=qualifiers,arabic=bool(re.search(r'[\u0600-\u06ff]',question)))


def _units(content):
    for match in re.finditer(r'[^\n.!?؟]+(?:[.!?؟]|(?=\n|$))',content):
        value=match[0].strip()
        if value:
            start=match.start()+len(match[0])-len(match[0].lstrip())
            yield start,value


def _valid_date(value):
    from email_facts import normalize_value
    interval=re.fullmatch(r'(\d{1,2})\s*[-–—]\s*(\d{1,2})([\s-]+\D+[\s,-]+\d{4})',value)
    values=[value] if interval is None else [interval[1]+interval[3],interval[2]+interval[3]]
    return (interval is None or int(interval[1])<=int(interval[2])) and all(normalize_value('date',v) for v in values)


def _proofs(request, email, chunk):
    if 'domains' in request:
        from rag_status import proofs
        return proofs(request,email,chunk)
    content=chunk['text']
    context=(email.subject or '')+' '+content
    if not request['qualifiers'] <= set(tokens(context)):
        return []
    output=[]
    for offset,unit in _units(content):
        a=content.rfind('\n\n',0,offset)
        a=a+2 if a>=0 else 0
        b=content.find('\n\n',offset)
        paragraph=content[max(0,a):b if b>=0 else len(content)]
        if (len(unit)>500 or _UNSAFE.search(' '.join(tokens(paragraph)))
                or re.search(r'\bmay\s+(?:be|occur|change|take)\b',paragraph,re.I)
                or re.search(r'[<>\[\]]',unit)):
            continue
        if request['kind']=='date':
            matches=list(_DATE.finditer(unit))
            if not matches:
                continue
            # A date needs a date/event assertion, not a footer, invoice or offer expiry.
            names=set(tokens(unit))
            if names & {'copyright','expires','expiry','offer','invoice','sent','received','unsubscribe','حقوق','فاتوره','ينتهي'}:
                continue
            if not (_DATE.fullmatch(unit.rstrip('.')) or names & {'date','held','scheduled','takes','from','on','at','تاريخ','يقام','ستقام','موعد'}):
                continue
            values=[(m.start(),m[0]) for m in matches if _valid_date(m[0])]
        elif request['kind']=='status':
            # Wrapped/truncated assertions must not become incomplete answers.
            if re.search(r'\b(?:with|to|from|for|and|or|the|من|إلى|الى|في|على|مع|و)\s*$',unit,re.I):
                continue
            if not (_STATUS.search(unit) or re.match(r'^(?:status|application status|حالة الطلب)\s*:\s*[^:]{1,80}$',unit,re.I)):
                continue
            values=[(0,unit)]
        else:
            if not _ACTION.search(unit):
                continue
            values=[(0,unit)]
        # Require the entire assertion verbatim in the stored body, not a generated summary.
        body=email.body or ''
        body_start=body.find(unit)
        if body_start<0:
            continue
        for local,value in values:
            years={w for w in request['qualifiers'] if re.fullmatch(r'\d{4}',w)}
            if request['kind']=='date' and years and not years <= set(tokens(value)):
                continue
            output.append(dict(email_id=email.id,chunk_id=chunk['chunk_id'],chunk_index=chunk['chunk_index'],
                kind=request['kind'],value=value,span=[body_start+local,body_start+local+len(value)],
                evidence=unit,evidence_span=[body_start,body_start+len(unit)],
                chunk_span=[offset+local,offset+local+len(value)],span_basis='stored_body',
                subject=(email.subject or '')[:180],date=(email.email_date or '')[:100]))
    return output


def audit_answers(db, question, chunks):
    request=question_intent(question)
    if request is None or not chunks:
        return None
    # Bounded witness audit before the public chunk limit hides competing targets.
    chunks,_=select_evidence(question,chunks[:MAX_AUDIT_CHUNKS])
    ids={c['email_id'] for c in chunks}
    emails={e.id:e for e in db.scalars(select(Email).options(load_only(
        Email.id,Email.subject,Email.body,Email.email_date,Email.message_at,Email.sent_at)).where(Email.id.in_(ids)))}
    proofs={}
    for chunk in chunks:
        email=emails.get(chunk['email_id'])
        if email:
            for proof in _proofs(request,email,chunk):
                key=(proof['email_id'],proof['value'])
                proofs.setdefault(key,proof)
    selected=list(proofs.values())
    if request['kind']=='status':
        from rag_status import latest_same_application
        selected=latest_same_application(selected,emails,question)
    return dict(kind=request['kind'],qualifiers=sorted(request['qualifiers']),proofs=selected)


def decide(audit):
    if not audit:
        return 'generative'
    if not audit['proofs']:
        return 'insufficient_evidence' if audit['kind'] in {'date','status'} else 'generative'
    proofs=audit['proofs']
    if len(proofs)==1:
        return 'extractive'
    # Repeated announcements of an explicitly named event can corroborate one date.
    named={w for w in audit['qualifiers'] if not w.isdigit()}
    years={w for w in audit['qualifiers'] if re.fullmatch(r'\d{4}',w)}
    if audit['kind']=='date' and len(named)>=2 and years and len({p['value'].casefold() for p in proofs})==1:
        return 'extractive'
    return 'needs_clarification'


def verify_proof(db, proof, evidence):
    if not any(s['email_id']==proof['email_id'] and s['chunk_id']==proof['chunk_id']
               and proof['evidence'] in s['content'] for s in evidence):
        return False
    body=db.scalar(select(Email.body).where(Email.id==proof['email_id']))
    if body is None:
        return False
    a,b=proof['span']
    x,y=proof['evidence_span']
    return 0<=x<=a<b<=y<=len(body) and body[a:b]==proof['value'] and body[x:y]==proof['evidence']


def format_extractive(proof, question):
    prefix=''
    if re.search(r'[\u0600-\u06ff]',question):
        prefix={'date':'الموعد: ', 'status':'الحالة بحسب البريد: ', 'action':'الإجراء المذكور: '}[proof['kind']]
    return f"{prefix}{proof['value']} [email_id={proof['email_id']}]"
