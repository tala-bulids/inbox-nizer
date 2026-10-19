"""Authored development cases; never report these as human mailbox gold."""
import argparse
import json
from pathlib import Path
from quality.cases import TASKS, REFERENCE

CASES = [(name,body,[(fragment,deadline)] if fragment else []) for name,body,fragment,deadline in TASKS] + [
    ('free_invite', 'Please register for our free webinar.', []),
    ('free_invite_ar', 'يرجى التسجيل في الندوة المجانية قبل الخميس.', []),
    ('purchase', 'Complete your purchase before Friday.', []),
    ('purchase_ar', 'أكمل عملية الشراء قبل الجمعة.', []),
    ('collection', 'Please review our new collection.', []),
    ('collection_ar', 'راجع تشكيلتنا الجديدة.', []),
    ('issued_date', 'Please review the invoice issued before Friday.', [('Review the invoice', None)]),
    ('received_date', 'Please upload the document you received by Friday.', [('Upload the document', None)]),
    ('event_constraint', 'Please review the agenda for the meeting before Friday.', [('Review the agenda', None)]),
    ('arabic_issued', 'يرجى مراجعة الفاتورة الصادرة قبل الخميس.', [('مراجعة الفاتورة', None)]),
    ('conflicting_due', 'Please send the form by Friday. Deadline: before Monday.', [('Send the form', None)]),
    ('association', 'Please upload your ID before Friday. Your flight leaves on Saturday.', [('Upload your ID', 'before Friday')]),
    ('two_obligations', 'Please upload your ID by Friday. Please pay the invoice by Monday.', [('Upload your ID','by Friday'),('Pay the invoice','by Monday')]),
    ('two_obligations_ar', 'يرجى رفع الهوية قبل الخميس. يرجى سداد الفاتورة قبل الأحد.', [('رفع الهوية','قبل الخميس'),('سداد الفاتورة','قبل الأحد')]),
    ('generic_click', 'Click here to discover our range.', []),
    ('call_you', 'We will contact you by Friday.', []),
    ('call_you_ar', 'سوف نتواصل معك قبل الخميس.', []),
    ('reviewing_request', 'Your request is being reviewed.', []),
    ('completed_request', 'Your request was completed yesterday.', []),
    ('invoice_date', 'Your invoice was issued on 16 October 2026.', []),
    ('reminder_only', 'Registration closes Friday. We hope to see you there.', []),
    ('required_webinar', 'You must register for the mandatory training webinar by Friday.', [('Register for the mandatory training webinar','by Friday')]),
    ('paid_status_then_request', 'Your payment has been received. Please upload the signed contract by Friday.', [('Upload the signed contract','by Friday')]),
    ('relative_due', 'Please send the signed form tomorrow.', [('Send the signed form','tomorrow')]),
    ('event_relative', 'Please attend the workshop tomorrow.', [('Attend the workshop',None)]),
    ('separate_due', 'Please submit the report. Deadline: before Friday.', [('Submit the report','before Friday')]),
    ('arabic_other_actor', 'سنقوم بمراجعة الطلب وإرسال الرد قبل الخميس.', []),
    ('status_product', 'Uploading files is faster in the new version.', []),
]


def evaluate():
    from task_extractor import extract_action_items
    rows=[];tp=fp=fn=0;action_tp=action_fp=action_fn=0;deadline_tp=deadline_fp=deadline_fn=0
    for name,body,expected in CASES:
        actual=extract_action_items('',body,REFERENCE)
        tp+=bool(actual) and bool(expected);fp+=bool(actual) and not expected;fn+=not actual and bool(expected)
        unmatched=list(expected);matched=0;correct_deadlines=0
        for item in actual:
            index=next((i for i,(fragment,_) in enumerate(unmatched) if fragment.casefold() in item['task'].casefold()),None)
            target=unmatched.pop(index) if index is not None else None
            matched+=target is not None
            actual_due=item['deadline_text']
            expected_due=target[1] if target else None
            correct=bool(actual_due and expected_due and actual_due.casefold()==expected_due.casefold())
            correct_deadlines+=correct
            deadline_tp+=correct;deadline_fp+=bool(actual_due) and not correct
            deadline_fn+=bool(expected_due) and not correct
        deadline_fn+=sum(bool(due) for _,due in unmatched)
        action_tp+=matched;action_fp+=len(actual)-matched;action_fn+=len(unmatched)
        rows.append({'case':name,'tasks':len(actual),'expected':len(expected),'matched_actions':matched,
                     'deadlines':sum(bool(item['deadline_text']) for item in actual),
                     'expected_deadlines':sum(bool(due) for _,due in expected),'correct_deadline_associations':correct_deadlines})
    def score(tp,fp,fn):
        return {'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None}
    return {'evidence_type':'authored_development_regression','n':len(CASES),'detection':score(tp,fp,fn),
            'action':score(action_tp,action_fp,action_fn),'deadline_association':score(deadline_tp,deadline_fp,deadline_fn),'cases':rows}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=evaluate();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in result.items() if key!='cases'},indent=2))
