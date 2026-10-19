"""Top-one product metrics and multi-label diagnostic metrics are separate."""
import numpy as np
from classifier_contract import LABELS


def metrics(scores, labels):
    scores=np.asarray(scores, dtype=float)
    if scores.shape != (len(labels), len(LABELS)) or not len(labels):
        raise ValueError('Scores must be a nonempty N x category-count matrix.')
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError('Confidence scores must be finite and between zero and one.')
    if any(not row or set(row) - set(LABELS) for row in labels):
        raise ValueError('Each example requires known reference labels.')
    y=np.array([[l in row for l in LABELS] for row in labels])
    chosen=scores.argmax(axis=1); pred=np.eye(len(LABELS),dtype=bool)[chosen]
    tp=(pred&y).sum(0);fp=(pred&~y).sum(0);fn=(~pred&y).sum(0)
    precision=tp/np.maximum(tp+fp,1);recall=tp/np.maximum(tp+fn,1)
    f1=2*tp/np.maximum(2*tp+fp+fn,1)
    correct=y[np.arange(len(y)),chosen];confidence=scores.max(1)
    confusion=np.zeros((len(LABELS),len(LABELS)))
    for row,index in zip(y,chosen):
        # Fractional rows avoid inventing a single gold label for multi-label data.
        confusion[:,index]+=row/max(row.sum(),1)
    bins=[];ece=0
    for bin_index in range(10):
        low=bin_index/10
        mask=(np.minimum((confidence*10).astype(int),9)==bin_index)
        if mask.any():
            accuracy=float(correct[mask].mean());mean=float(confidence[mask].mean())
            ece+=mask.mean()*abs(accuracy-mean)
            bins.append(dict(low=float(low),count=int(mask.sum()),accuracy=accuracy,confidence=mean))
    finance=LABELS.index('Finance & Bills')
    pairs={}
    for first,second in [('Business','Job Application'),('Newsletters','Promotions'),('Reminders','Events & Invitations')]:
        a,b=LABELS.index(first),LABELS.index(second)
        pairs[first+' / '+second]={
            'first_to_second':int((y[:,a]&~y[:,b]&(chosen==b)).sum()),
            'second_to_first':int((y[:,b]&~y[:,a]&(chosen==a)).sum())}
    return {'n':len(y),'top1_accuracy':float(correct.mean()),'top1_macro_f1':float(f1.mean()),
        'per_class':{l:dict(precision=float(precision[i]),recall=float(recall[i]),f1=float(f1[i]),support=int(y[:,i].sum())) for i,l in enumerate(LABELS)},
        'confusion_matrix':confusion.tolist(),'confusion_note':'Rows gold, columns predicted; multi-label gold rows weighted 1/label-count.',
        'finance_false_positives':int(fp[finance]),'confidence_bins':bins,'top1_ece':float(ece),
        'finance_false_positive_rate':float(fp[finance]/max((~y[:,finance]).sum(),1)),
        'pair_confusions':pairs,
        'confidence_semantics':'Raw independent classifier scores; not a calibrated probability of correctness.',
        'top1_brier_correctness':float(np.mean((confidence-correct.astype(float))**2)),
        'selective_accuracy':{str(threshold):{
            'coverage':float((confidence>=threshold).mean()),
            'n':int((confidence>=threshold).sum()),
            'accuracy':float(correct[confidence>=threshold].mean()) if (confidence>=threshold).any() else None}
            for threshold in (.5,.7,.8,.9)},
        'wrong_confident_ge_080':int((~correct&(confidence>=.8)).sum()),
        'wrong_confident_rate':float((~correct&(confidence>=.8)).mean()),
        'mean_confidence_correct':float(confidence[correct].mean()) if correct.any() else None,
        'mean_confidence_wrong':float(confidence[~correct].mean()) if (~correct).any() else None}
