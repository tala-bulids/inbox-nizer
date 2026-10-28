"""Deterministic, source-extractive temporal/task reasoning for the curated corpus.

Not an LLM, trained task detector or evidence of broad mailbox accuracy.
"""
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from task_extractor import extract_action_items


def metadata():
    return json.loads(Path(__file__).with_name('provenance.json').read_text(encoding='utf-8'))


def norm(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    text = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', text)
    return text.translate(str.maketrans('أإآى', 'اااي'))


def unsafe(text):
    return bool(re.search(r'ignore (?:all |previous |system )?instructions|system prompt|\[source |<\|im_|passwords?|تجاهل.*تعليمات|كلم[ةا] المرور|تعليمات النظام', norm(text)))


def visible(email):
    return datetime.fromisoformat(email['date']) <= datetime.fromisoformat(metadata()['reference_datetime'])


def spans(text):
    # Keep original offsets. Quoted mail is evidence history, not a new request.
    for match in re.finditer(r'[^\n]+', text):
        if match[0].lstrip().startswith(('>', '```')) or unsafe(match[0]):
            continue
        yield match.start(), match.end(), match[0]


def chunks(emails):
    result = []
    for email in emails:
        # Small original spans, envelope metadata repeated for semantic context.
        for start,end,line in spans(email['body']):
            cursor=start
            while cursor < end:
                stop=min(cursor+320,end)
                if stop<end:
                    boundary=email['body'].rfind(' ',cursor,stop)
                    if boundary>cursor: stop=boundary
                text=email['body'][cursor:stop]
                if text.strip():
                    result.append({'email_id':email['id'], 'chunk_index':cursor,
                        'chunk_id':f"{email['id']}:{cursor}:{stop}", 'start':cursor,'end':stop,
                        'text':text,'subject':email['subject'],
                        'embedding_text':unicodedata.normalize('NFC',email['subject'][:100]+'\n'+email['sender']+'\n'+email['date']+'\n'+text)})
                cursor=stop
    return result


def index_version(emails):
    payload=json.dumps({'emails':emails,'encoder':'intfloat/multilingual-e5-small','chunk_policy':'original-line-320-v1'},sort_keys=True,ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def cancellation(email):
    return bool(re.search(r'\bcancell?ed\b|تم الغاء|الغي الاجتماع',norm(email['body']+' '+email['subject'])))


def task_records(email, emails=()):
    if cancellation(email): return []
    reference=datetime.fromisoformat(email['date'])
    owner_match=re.search(r'(?m)^(?:Responsible|Owner|المسؤول):\s*([^\n]+)',email['body'],re.I)
    owner=owner_match[1].strip() if owner_match else None
    newer=[e for e in emails if email.get('thread_id') and e.get('thread_id')==email['thread_id']
           and e['id']!=email['id'] and visible(e) and e['date']>email['date'] and cancellation(e)]
    result=[]
    for start,end,source in spans(email['body']):
        if re.search(r'\b(?:already|completed|no action|no reply|do not)\b|لا ترسل|لا تدفع|تم بالفعل|لا داعي',norm(source)):
            continue
        named=re.match(r'^([^,،:]{1,40})[,،]\s*(?=(?:please|kindly|يرجى|الرجاء)\b)',source,re.I)
        request=source[named.end():] if named else source
        for item in extract_action_items('',request,reference):
            # The old extractor deliberately leaves uncertain constraints null.
            uncertain=bool(re.search(r'\b(?:by|before|deadline|soon)\b|قبل|بحلول|موعد|قريبا',norm(item['task'])))
            day=item['deadline_date']
            moment=item['deadline_at']
            status='explicit' if day or moment else 'ambiguous' if uncertain else 'missing'
            result.append({**item,'email_id':email['id'],
                'responsible':named[1].strip() if named else owner,
                'deadline_state':status, 'state':'superseded' if newer else 'open',
                'superseded_by':[e['id'] for e in newer],
                'conditional':bool(re.search(r'\bif\b|اذا',norm(item['task']))),
                'evidence':{'subject':email['subject'],'body':email['body'],
                            'text':source,'start':start,'end':end},
                'method':'deterministic rules; not learned task detection'})
    return result[:8]


def intent(question):
    q=norm(question)
    if unsafe(q): return None
    if re.search(r'overdue|متاخر',q): return 'overdue'
    if re.search(r'deadlines?|due dates?|مواعيد.*(?:تسليم|نهائي)|مهل',q): return 'deadlines'
    if re.search(r'which.*repl|messages.*respond|رسائل.*(?:الرد|رد)|تحتاج.*رد',q): return 'reply'
    if re.search(r'latest|newest|اخر تحديث|احدث',q): return 'latest'
    if re.search(r'interview|مقابل',q): return 'interviews'
    if re.search(r'meeting|review.*happening|اجتماع|سيجتمع',q): return 'meetings'
    return None


def date_fields(email, kind):
    pattern=r'(?im)^(?:Meeting date|تاريخ الاجتماع)\s*:\s*(\d{4}-\d{2}-\d{2})' if kind=='meetings' else r'(?im)^(?:Interview date|تاريخ المقابلة)\s*:\s*(\d{4}-\d{2}-\d{2})'
    found=[]
    for m in re.finditer(pattern,email['body']):
        try: value=date.fromisoformat(m[1])
        except ValueError: continue
        found.append((value,m[0]))
    return found


def compose(question, ranked, emails):
    """Compose exact quotations only; ranking is learned elsewhere."""
    kind=intent(question)
    if not kind: return None
    q=norm(question); today=datetime.fromisoformat(metadata()['reference_datetime']).date()
    monday=today-timedelta(days=today.weekday())
    by_id={e['id']:e for e in emails if visible(e)}
    # Only records actually retrieved enter evidence, in learned ranking order.
    candidates=[by_id[r['email_id']] for r in ranked if r['email_id'] in by_id]
    labels={norm(e.get('thread_id','')) for e in candidates if e.get('thread_id')}
    exact={label for label in labels if re.search(r'(?<!\w)'+re.escape(label)+r'(?!\w)',q)}
    matched=exact or {label for label in labels if not re.search(r'\d',label)
                     and any(len(t)>3 and re.search(r'(?<!\w)'+re.escape(t)+r'(?!\w)',q) for t in label.split('-'))}
    if matched:
        candidates=[e for e in candidates if norm(e.get('thread_id','')) in matched]
    elif kind in ('meetings','interviews'):
        # Explicit subject qualifiers narrow a calendar/summary request. Generic
        # intent words do not turn a mailbox-wide question into one message.
        stop=set('what when which my have this week the a is are do show list messages mail mailbox meeting meetings review interview interviews invitations date latest update ما متي اي عندي هل في هذا الاسبوع موعد تاريخ اجتماع مقابلة مقابلات رسائل لي لخص'.split())
        def words(value):
            return {w[2:] if w.startswith('ال') else w for w in re.findall(r'\w+',norm(value)) if len(w)>2}
        terms=words(question)-words(' '.join(stop))
        qualified=[e for e in candidates if terms & words(e['subject'])]
        if qualified: candidates=qualified
    statements=[]; selected=[]; conflict=False
    def add(email, quote):
        if unsafe(quote): return
        statements.append(f"{email['subject']} — {email['sender']} — {email['date'][:10]}\n{quote} [email_id={email['id']}]")
        if email['id'] not in selected: selected.append(email['id'])
    if kind in ('reply','deadlines','overdue'):
        for email in candidates:
            for task in task_records(email,emails):
                if task['state']!='open': continue
                day=task['deadline_date'] or (task['deadline_at'].date() if task['deadline_at'] else None)
                if kind=='reply' and not re.search(r'\breply\b|\brespond\b|الرد|\bرد\b',norm(task['task'])): continue
                if kind=='deadlines' and (not day or day<today): continue
                if kind=='overdue' and (not day or day>=today): continue
                quote=task['evidence']['text']
                if day:
                    heading='الموعد المحسوب' if re.search('[\u0600-\u06ff]',question) else 'Resolved date'
                    quote+=f"\n{heading}: {day.isoformat()}"
                add(email,quote)
    elif kind in ('meetings','interviews'):
        dates_by_thread={}
        for email in candidates:
            if cancellation(email):
                if matched: add(email,email['body'])
                continue
            thread=email.get('thread_id')
            if any(e.get('thread_id')==thread and thread and e['date']>email['date'] and cancellation(e) for e in candidates): continue
            fields=date_fields(email,kind)
            if not fields: continue
            if re.search(r'this week|هذا الاسبوع|الاسبوع',q):
                fields=[f for f in fields if monday<=f[0]<monday+timedelta(days=7)]
            if not fields: continue
            dates_by_thread.setdefault(thread or email['id'],set()).update(f[0] for f in fields)
            safe='\n'.join(text for _,_,text in spans(email['body']))
            add(email,safe)
        conflict=any(len(values)>1 for values in dates_by_thread.values())
    elif kind=='latest':
        # An unspecified request spanning multiple threads needs clarification.
        candidates=[e for e in candidates if re.search(r'(?im)^(?:Status|الحالة|Order reference|Application reference|مرجع الطلب):',e['body'])]
        threads={e.get('thread_id',e['id']) for e in candidates}
        if len(threads)>1:
            return {'status':'needs_clarification','answer':'Specify the request/reference. حدد مرجع الطلب.',
                    'mode':'extractive_composition','verification':'no_verified_answer','sources':[]}
        if candidates:
            latest=max(e['date'] for e in candidates)
            chosen=[e for e in candidates if e['date']==latest]
            conflict=len(chosen)>1 and len({e['body'] for e in chosen})>1
            for email in chosen: add(email,'\n'.join(text for _,_,text in spans(email['body'])))
    if not statements: return None
    prefix=('أدلة متعارضة؛ لم يتم اختيار موعد واحد.\n' if re.search('[\u0600-\u06ff]',question) else 'Conflicting evidence; no single date selected.\n') if conflict else ''
    if kind=='overdue': prefix+='Past stated deadlines; completion is not known. مواعيد سابقة؛ حالة الإنجاز غير معروفة.\n'
    sources=[]
    for eid in selected:
        email=by_id[eid]; match=next(r for r in ranked if r['email_id']==eid)
        sources.append({**match,'content':email['body'],'sender':email['sender'],'date':email['date']})
    return {'status':'conflicting_evidence' if conflict else 'answered','answer':prefix+'\n\n'.join(statements),
            'mode':'extractive_composition','verification':'source_supported','sources':sources,
            'reference_datetime':metadata()['reference_datetime'], 'scope':'bounded curated collection; not a personal calendar'}
