"""Export a blind local review set. Never writes to the mailbox or invents gold labels."""
import argparse,csv,hashlib,json,random,re
from pathlib import Path
from collections import defaultdict
from email.utils import parseaddr
from sqlalchemy import select,text
from sqlalchemy.orm import selectinload
from dotenv import load_dotenv


def safe(value):
    value=str(value or '')
    return "'"+value if value.startswith(('=','+','-','@','\t','\r')) else value


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--user-id',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--per-stratum',type=int,default=6)
    args=parser.parse_args()
    if args.output.exists():
        raise SystemExit('Output exists; refusing to overwrite review labels.')
    load_dotenv('.env')
    from database import engine
    from ownership import OwnedSession
    from models import Email
    from quality.dataset import LABELS
    strata=defaultdict(list)
    with engine.connect() as connection:
        tx=connection.begin();connection.execute(text('SET TRANSACTION READ ONLY'))
        with OwnedSession(bind=connection,user_id=args.user_id,autoflush=False) as db:
            for email in db.scalars(select(Email).options(selectinload(Email.predictions)).order_by(Email.id)).all():
                predictions=sorted(email.predictions,key=lambda p:p.confidence,reverse=True)
                top=predictions[0] if predictions else None
                language='ar' if re.search('[\u0600-\u06ff]',(email.subject or '')+(email.body or '')[:500]) else 'en'
                category=top.category if top else 'unclassified'
                confidence=top.confidence if top else 0
                domain=parseaddr(email.sender or '')[1].rpartition('@')[2]
                template=re.sub(r'\d+','',(email.subject or '').casefold()).strip()
                group=hashlib.sha256((domain+'|'+template).encode()).hexdigest()
                split='holdout' if int(group[:8],16)%10<3 else 'development'
                strata[(category,language,confidence>=.8,split)].append(dict(email_id=email.id,sender=email.sender,subject=email.subject,body=email.body,date=email.email_date,gold_label='',ambiguous='',reviewer='',label_source='',reviewed_at='',notes='',split=split,group=group,language=language,baseline=category,confidence=confidence))
        tx.rollback()
    rng=random.Random(42);chosen=[]
    for key,rows in sorted(strata.items()):
        rng.shuffle(rows);seen=set()
        for row in rows:
            if row['group'] not in seen:
                chosen.append(row);seen.add(row['group'])
            if len(seen)>=args.per_stratum:break
    args.output.mkdir(parents=True)
    fields=['email_id','sender','subject','date','body','gold_label','ambiguous','reviewer','label_source','reviewed_at','notes']
    for split in ('development','holdout'):
        with (args.output/(split+'.csv')).open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
            writer.writerows({k:safe(row.get(k,'')) for k in fields} for row in chosen if row['split']==split)
    manifest=[{k:v for k,v in row.items() if k not in {'body','subject','sender','date'}} for row in chosen]
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (args.output/'review-policy.json').write_text(json.dumps({
        'label_policy_version':'inbox-categories-v1',
        'label_source':'unreviewed',
        'sampling':'predicted-class/language/confidence-stratified; one subject-template per stratum',
        'representative':False,
        'holdout_used_for_selection':False,
        'note':'This queue prioritizes review coverage. Unweighted metrics on it are not representative mailbox accuracy.'
    },indent=2),encoding='utf-8')
    (args.output/'REVIEW.md').write_text('Local private mailbox review. Do not share or commit these files.\n\nFill gold_label using exactly one of: '+', '.join(LABELS)+'. Mark ambiguous=yes when policy is unclear; do not force a label. Record a reviewer name. Existing predictions are hidden to avoid anchoring. Development is for policy/training; holdout is for one final evaluation only, never candidate selection. Same sender-domain/subject template stays in one split. Sampling uses predicted class and confidence only as strata, not truth.\n\nBusiness: professional networking and operational work. Job Application: a specific application, selection or hiring process. Finance & Bills: actual charges, invoices, balances or payment obligations, not occupational mentions of banking. Newsletters: recurring editorial digests. Promotions: marketing offers. Personal: interpersonal correspondence. Human review must adjudicate overlap.\n',encoding='utf-8')
    with (args.output/'REVIEW.md').open('a',encoding='utf-8') as stream:
        stream.write('\nOnly a human reviewer should set label_source=human_reviewed and reviewed_at to an ISO date after reviewing a row. Generated/weak labels must use label_source=weak and never qualify as human gold. Ambiguous rows are excluded from accuracy denominators. Do not open holdout while selecting models. This stratified review queue is a diagnostic set, not a representative release sample. Final evaluation tooling requires a frozen artifact hash and consumes a holdout only once.\n')
    print(json.dumps({'sampled':len(chosen),'development':sum(r['split']=='development' for r in chosen),'holdout':sum(r['split']=='holdout' for r in chosen),'human_labels':0}))

if __name__=='__main__':main()
