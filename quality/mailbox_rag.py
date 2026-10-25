"""Read-only, tenant-scoped runtime evaluation. No email bodies in output."""
import argparse, importlib.util, json, time, hashlib
from pathlib import Path
QUESTIONS=['متى بسافر؟','متى رحلتي؟','متى السفر؟','متى بروح جدة؟','وش موعد رحلتي؟','كم وقت الوصول؟','متى أوصل؟','وش آخر موعد؟','متى آخر يوم؟','متى ب اسافر لجده؟','What is the departure time to Jeddah?','What is the submarine booking number?']
def main():
    p=argparse.ArgumentParser();p.add_argument('--user-id',type=int,required=True);p.add_argument('--baseline',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    from dotenv import load_dotenv
    load_dotenv('.env')
    if a.baseline:
        import sys
        for name in ('fact_roles', 'rag_candidates'):
            spec=importlib.util.spec_from_file_location(name,a.baseline/(name+'.py'))
            old=importlib.util.module_from_spec(spec);sys.modules[name]=old;spec.loader.exec_module(old)
    from sqlalchemy import text
    from database import engine
    from ownership import OwnedSession
    import rag_service
    from semantic_search import semantic_search
    from local_llm import get_llm_provider
    class Provider:
        calls=0;seconds=0
        def generate(self,messages):
            self.calls+=1;start=time.perf_counter()
            answer=get_llm_provider().generate(messages)
            self.seconds+=time.perf_counter()-start
            return answer
    original=rag_service.prepare_rag_request;captured={}
    def capture(*args,**kwargs):
        prepared=original(*args,**kwargs);captured.clear();captured.update(prepared);return prepared
    rag_service.prepare_rag_request=capture
    report=[]
    with engine.connect() as c:
        tx=c.begin();c.execute(text('SET TRANSACTION READ ONLY'))
        with OwnedSession(bind=c,user_id=a.user_id,autoflush=False) as db:
            for question in QUESTIONS:
                start=time.perf_counter();search=semantic_search(db,question)
                llm=Provider();result=rag_service.answer_email_question(db,question,llm)
                row=dict(question=question,seconds=time.perf_counter()-start,search_ids=[r['email'].id for r in search],retrieved_ids=[r['email_id'] for r in captured.get('retrieved_chunks',[])],evidence_ids=[r['email_id'] for r in captured.get('permitted_evidence',[])],persisted_fact_count=len(captured.get('structured_facts',{}).get('facts',[])),selected_roles=[f['role'] for f in captured.get('resolved_facts',[])],selected_values=[f['value'] for f in captured.get('resolved_facts',[])],decision=captured.get('answer_mode'),status=result['status'],answer_mode=result.get('answer_mode'),citations=result['citations'],llm_calls=llm.calls,llm_seconds=llm.seconds,answer_sha256=hashlib.sha256(result['answer'].encode()).hexdigest())
                report.append(row);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(row,ensure_ascii=True),flush=True)
        tx.rollback()
if __name__=='__main__':main()
