"""Small deterministic challenge evaluation; outputs no mailbox content."""
import argparse, json, time
from pathlib import Path
from .cases import TASKS, ASK, ASK_SOURCE, REFERENCE

def run():
    from task_extractor import extract_action_items
    from rag_grounding import resolve_answer
    start=time.perf_counter(); rows=[];tp=fp=fn=0;correct_deadline=pred_deadline=gold_deadline=0;quality=0
    for name,body,fragment,deadline in TASKS:
        items=extract_action_items('',body,REFERENCE)
        positive=fragment is not None
        tp+=bool(items) and positive; fp+=bool(items) and not positive; fn+=not items and positive
        text_ok=bool(items) and positive and fragment.casefold() in items[0]['task'].casefold()
        quality+=text_ok
        actual=items[0]['deadline_text'] if items else None
        pred_deadline+=bool(actual);gold_deadline+=bool(deadline)
        correct_deadline+=bool(actual and deadline and actual.casefold()==deadline.casefold())
        rows.append(dict(id=name,detected=len(items),action_and_actor_correct=bool(text_ok),deadline_correct=actual==deadline,tasks=items))
    elapsed=(time.perf_counter()-start)*1000/len(TASKS)
    precision=tp/max(tp+fp,1);recall=tp/max(tp+fn,1)
    answers=[];start=time.perf_counter()
    for question,expected in ASK:
        facts=resolve_answer(question,[ASK_SOURCE])
        value=facts[0]['value'] if len(facts)==1 else None
        answers.append(dict(question=question,expected=expected,actual=value,correct=value==expected))
    return dict(tasks=dict(n=len(rows),tp=tp,fp=fp,fn=fn,precision=precision,recall=recall,f1=2*precision*recall/max(precision+recall,1e-9),false_positive_rate=fp/sum(r[2] is None for r in TASKS),correct_action_actor=quality,predicted_tasks=sum(r['detected'] for r in rows),deadline_precision=correct_deadline/max(pred_deadline,1),deadline_recall=correct_deadline/max(gold_deadline,1),ms_per_case=elapsed,cases=rows),ask=dict(stage='role resolution with identical correct evidence (not end-to-end retrieval)',correct=sum(r['correct'] for r in answers),supported_correct=sum(r['correct'] and r['expected'] is not None for r in answers),unsupported_correct=sum(r['correct'] and r['expected'] is None for r in answers),ms_per_case=(time.perf_counter()-start)*1000/len(ASK),cases=answers))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--baseline',type=Path);args=parser.parse_args()
    if args.baseline:
        import importlib.util, sys
        for name in ('deadline_extractor','task_extractor','fact_roles'):
            spec=importlib.util.spec_from_file_location(name,args.baseline/(name+'.py'))
            module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    report=run();Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps({k:{a:b for a,b in v.items() if a!='cases'} for k,v in report.items()},indent=2))
