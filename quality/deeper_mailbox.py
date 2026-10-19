"""Read-only real Ask comparison; private source bodies are never logged."""
import argparse,importlib.util,sys,json,time,hashlib
from pathlib import Path
CASES=[('متى رحلتي لجدة؟',None),('متى ب اسافر لجده؟',None),('متى رحلتي لجدة؟',4),('انقبلت بمعسكر؟',None),('جاني قبول قريب؟',None),('وش صار على طلباتي آخر أسبوعين؟',None),('هل وصلني شيء جديد من الجامعة؟',None),('وش آخر تحديث على طلبي؟',None),('What is the submarine booking number?',None)]
def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',action='store_true');p.add_argument('--user-id',type=int,required=True);args=p.parse_args()
    from dotenv import load_dotenv
    load_dotenv('.env')
    if args.baseline:
        for name in ('rag_extractive','rag_candidates','rag_retrieval','rag_service'):
            spec=importlib.util.spec_from_file_location(name,Path('results/quality-deeper-20261012/baseline')/(name+'.py'))
            module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    import rag_service
    from database import engine
    from ownership import OwnedSession
    from sqlalchemy import text
    from local_llm import get_llm_provider
    class LLM:
        calls=0
        def generate(self,messages):
            self.calls+=1;return get_llm_provider().generate(messages)
    capture={};original=rag_service.prepare_rag_request
    def prepare(*a,**kw):
        out=original(*a,**kw);capture.clear();capture.update(out);return out
    rag_service.prepare_rag_request=prepare
    rows=[]
    output=Path('results/quality-deeper-20261012')/('ask-before.json' if args.baseline else 'ask-after.json')
    with engine.connect() as connection:
        transaction=connection.begin();connection.execute(text('SET TRANSACTION READ ONLY'))
        with OwnedSession(bind=connection,user_id=args.user_id,autoflush=False) as db:
            for question,email_id in CASES:
                llm=LLM();start=time.perf_counter()
                result=rag_service.answer_email_question(db,question,llm,email_id=email_id)
                row=dict(question=question,selected_email_id=email_id,status=result['status'],mode=result.get('answer_mode'),citations=result['citations'],llm_calls=llm.calls,seconds=time.perf_counter()-start,retrieved_ids=[c['email_id'] for c in capture['retrieved_chunks']],facts=[dict(role=f['role'],value=f['value'],email_id=f['email_id'],record=f['record_index']) for f in capture['resolved_facts']],answer_sha256=hashlib.sha256(result['answer'].encode()).hexdigest())
                # Travel output is already explicitly supplied in the user's request.
                if email_id==4:row['answer']=result['answer']
                rows.append(row);output.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in row.items() if k not in ('answer','facts')},ensure_ascii=True),flush=True)
        transaction.rollback()
if __name__=='__main__':main()
