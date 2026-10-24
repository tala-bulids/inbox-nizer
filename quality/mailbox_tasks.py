"""Read-only task drift sample. Counts are not accuracy without human labels."""
import argparse,importlib.util,json,sys,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--user-id',type=int,required=True);p.add_argument('--baseline',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.baseline:
        for name in ('deadline_extractor','task_extractor'):
            spec=importlib.util.spec_from_file_location(name,a.baseline/(name+'.py'));module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    from dotenv import load_dotenv
    load_dotenv('.env')
    from database import engine
    from sqlalchemy import select,text
    from ownership import OwnedSession
    from models import Email
    from task_extractor import extract_action_items
    from deadline_extractor import parse_email_datetime
    rows=[];start=time.perf_counter()
    with engine.connect() as c:
        tx=c.begin();c.execute(text('SET TRANSACTION READ ONLY'))
        with OwnedSession(bind=c,user_id=a.user_id,autoflush=False) as db:
            for email in db.scalars(select(Email).where(Email.id%8==0).order_by(Email.id)):
                items=extract_action_items(email.subject or '',email.body or '',parse_email_datetime(email.email_date))
                rows.append(dict(email_id=email.id,tasks=len(items),deadlines=sum(bool(i['deadline_text']) for i in items)))
        tx.rollback()
    result=dict(sample='owned email_id modulo 8 = 0',emails=len(rows),tasks=sum(r['tasks'] for r in rows),deadlines=sum(r['deadlines'] for r in rows),seconds=time.perf_counter()-start,rows=rows,note='No writes. Count changes are diagnostic drift, not a precision estimate.')
    a.output.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
if __name__=='__main__':main()
