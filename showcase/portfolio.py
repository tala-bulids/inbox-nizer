"""Read-only evidence and hash-verified Phase 2 research-model inference."""
import hashlib
import json
import os
from pathlib import Path
from threading import Lock
import time

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def evidence():
    comparison=read('docs/phase2/evidence/experiment-comparison.json')
    historical=read('docs/release/v03-v10-20261024.json')
    rag=read('docs/phase3/benchmark-v1.json')
    return {
        'selected':comparison['selected_research_candidate'],
        'models':[{'id':row['run']['candidate'],'run':row['run'],
                   'metrics':{k:row['metrics'][k] for k in ('n','top1_accuracy','top1_macro_f1','top1_weighted_f1','per_class','confusion_matrix','confusion_note','top1_ece','wrong_confident_ge_080','error_patterns')},
                   'history':row['training_history']} for row in comparison['runs']],
        'dataset':read('docs/phase2/evidence/dataset-card.json'),
        'configuration':read('docs/phase2/evidence/training-configuration.json'),
        'historical':{'development':historical['fresh_development_metrics'],
                      'languages':{k:{'n':v['n'],'correct':v['correct']} for k,v in historical['dominance_language_metrics'].items() if k in ('English','Arabic-heavy')}},
        'rag':{'qa':rag['qa'],'by_language':rag['by_language'],'tasks':rag['tasks']['overall'],
               'memory_mib':rag['process_peak_wset_mib'],'evaluation':rag['evaluation']},
        'error_analysis':(ROOT/'docs/phase2/ERROR_ANALYSIS.md').read_text(encoding='utf-8'),
        'training_curves_available':False, 'test_evaluated':False,
        'arabic_classifier_evaluated':False, 'production_approved':False,
        'evidence_version':'phase2@5b7cf7b + phase3@96fc1c0',
    }


class SelectedClassifier:
    def __init__(self):
        self._artifact=None
        self._lock=Lock()

    def predict(self, subject, body):
        start=time.perf_counter()
        comparison=read('docs/phase2/evidence/experiment-comparison.json')
        selected=next(row for row in comparison['runs'] if row['run']['candidate']==comparison['selected_research_candidate'])
        if selected['run']['candidate']!='A':
            raise ValueError('Only the reviewed sparse research artifact is supported')
        sha=selected['run']['artifact_sha256']
        with self._lock:
            cold=self._artifact is None
            if cold:
                path=Path(os.environ.get('SHOWCASE_CLASSIFIER_PATH',str(ROOT/'results/phase2-A/candidate.joblib')))
                with path.open('rb') as stream:
                    if hashlib.file_digest(stream,'sha256').hexdigest()!=sha:
                        raise ValueError('Selected research artifact identity mismatch')
                    # Deserialize the same verified handle, not a second path open.
                    stream.seek(0)
                    import joblib
                    import sklearn
                    if sklearn.__version__!=selected['run']['environment']['packages']['scikit-learn']:
                        raise ValueError('Use the recorded sklearn runtime for this artifact')
                    artifact=joblib.load(stream)
                from classifier_contract import LABELS
                if artifact['labels']!=LABELS or artifact['features'] is None:
                    raise ValueError('Invalid sparse classifier contract')
                self._artifact=artifact
            from ml_phase2.data import normalize
            from summarizer import summarize_email
            import numpy as np
            from threadpoolctl import threadpool_limits
            text=normalize(subject,body)
            if not text: raise ValueError('Empty normalized input')
            with threadpool_limits(limits=1):
                features=self._artifact['features'].transform([text])
                scores=self._artifact['classifier'].predict_proba(features)[0]
            if len(scores)!=len(self._artifact['labels']) or not np.isfinite(scores).all():
                raise ValueError('Invalid model output')
            index=int(np.argmax(scores))
            summary=summarize_email(subject,body)
        return {'predictions':[{'category':self._artifact['labels'][index],'confidence':float(scores[index])}],
                'summary':summary,'summary_method':'extractive','classifier_status':'English research baseline; not production approved',
                'model_version':'phase2-A','artifact_sha256':sha,'processing_ms':(time.perf_counter()-start)*1000,
                'cold_load_included':cold,'score_semantics':'Raw independent model score; not probability of correctness'}
