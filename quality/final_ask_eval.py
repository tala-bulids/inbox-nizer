"""Read-only request diagnostics. No source bodies are written to artifacts."""
import argparse,json,time,importlib.util,sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
CASES=[('travel_ar','متى رحلتي لجدة؟',4),('travel_en','when am I travelling to Jeddah?',4),('travel_mixed','متى flight حقي؟',None),('digest_ar','وش آخر المستجدات؟',None),('digest_en','What changed recently?',None),('existence','هل استلمت أي نشرة من فيصل؟',None),('status','انقبلت بمعسكر؟',None),('unsupported','What is my submarine booking reference?',None)]

def main():
    p=argparse.ArgumentParser();p.add_argument('--user-id',required=True,type=int);p.add_argument('--baseline',action='store_true');args=p.parse_args()
    load_dotenv('.env')
    root=Path('results/ask-final-20261013')
    if args.baseline:
        for name in ('question_understanding','rag_candidates','rag_retrieval','rag_service'):
            spec=importlib.util.spec_from_file_location(name,root/'baseline'/(name+'.py'))
            module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    import rag_service
    from database import engine
    from ownership import OwnedSession
    from local_llm import get_llm_provider
    class LLM:
        calls=0
        def generate(self,messages):
            self.calls+=1
            return get_llm_provider().generate(messages)
    captured={}
    original=rag_service.prepare_rag_request
    def prepare(*args,**kwargs):
        result=original(*args,**kwargs);captured.update(result);return result
    rag_service.prepare_rag_request=prepare
    rows=[]
    with engine.connect() as c:
        tx=c.begin();c.execute(text('SET TRANSACTION READ ONLY'))
        with OwnedSession(bind=c,user_id=args.user_id,autoflush=False) as db:
            for name,q,known in CASES:
                captured.clear()
                model=LLM();start=time.perf_counter()
                answer=rag_service.answer_email_question(db,q,model)
                ids=[r['email_id'] for r in answer['sources']]
                row=dict(case=name,status=answer['status'],mode=answer.get('answer_mode'),sources=ids,seconds=time.perf_counter()-start,llm_calls=model.calls,expected_source_recovered=(known in ids) if known else None,answer_chars=len(answer['answer']))
                row['retrieved_ids']=[c['email_id'] for c in captured.get('retrieved_chunks',[])]
                row['retrieval_recall_at_returned_k']=float(known in row['retrieved_ids']) if known else None
                if name=='travel_ar':row['answer']=answer['answer']
                rows.append(row);print(json.dumps(row,ensure_ascii=True),flush=True)
                (root/('before.json' if args.baseline else 'after.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        tx.rollback()
if __name__=='__main__':main()
