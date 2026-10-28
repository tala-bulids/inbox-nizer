"""Reuse local AI primitives with a small immutable, authored corpus.

No ORM/session adapter: corpus vectors live in memory, not production pgvector.
No stored predictions: inference executes on each Analyze/Ask request.
"""
import json
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from threading import Lock

from embedding_service import embed_passages, embed_query
from onnx_classifier import classify
from rag_evidence import select_evidence
from rag_grounding import resolve_answer, format_facts, is_abstention
from rag_prompt import build_rag_messages
from summarizer import summarize_email
from task_extractor import extract_action_items

ROOT = Path(__file__).resolve().parents[1]


def collection():
    # Fresh decoded objects prevent a caller from mutating the shared corpus.
    return json.loads((Path(__file__).parent / 'collection.json').read_text(encoding='utf-8'))


def lab():
    evidence = json.loads((ROOT / 'docs/release/v03-v10-20261024.json').read_text(encoding='utf-8'))
    return {
        'checkpoint': 'checkpoint-3159',
        'weight_sha256': evidence['source_files_sha256']['model.safetensors'],
        'provenance': evidence['provenance_verdict'],
        'quality': evidence['quality_verdict'],
        'development': evidence['fresh_development_metrics'],
        'languages': {name: {'n': value['n'], 'correct': value['correct']}
                      for name, value in evidence['dominance_language_metrics'].items()
                      if name in ('English', 'Arabic-heavy')},
        'evidence_date': evidence['verified_at'],
        'methodology': 'DistilBERT multilabel training; sigmoid scores with top-one serving. '
            'The original baseline training split/report is unavailable. '
            'Development diagnostics are consumed and are not a representative holdout.',
        'training_entry': 'app.py', 'evaluation_entry': 'evaluate.py',
        'evidence_path': 'docs/release/V03_V10_EVIDENCE.md',
        'inference': 'FP32 ONNX classifier; multilingual-e5-small retrieval; optional local Qwen3-0.6B.',
    }


def tasks(email):
    items = extract_action_items(email['subject'], email['body'], datetime.fromisoformat(email['date']))
    # The extractor may normalize capitalization. Include the complete original
    # source rather than inventing offsets or labelling a paraphrase an exact span.
    return [{'email_id': email['id'], **item,
             'evidence': {'subject': email['subject'], 'body': email['body']}} for item in items]


class Engine:
    def __init__(self):
        self._vectors = None
        self._load_lock = Lock()
        self._classifier_verified = False

    def verify_classifier(self):
        if self._classifier_verified:
            return
        root = Path(os.environ.get('CLASSIFIER_ONNX_PATH', 'local_models/render/classifier'))
        if not root.is_absolute():
            root = ROOT / root
        manifest = json.loads((ROOT / 'docs/release/v03-v10-20261024.json').read_text(encoding='utf-8'))
        for name in ('model.onnx', 'weights.bin', 'config.json', 'tokenizer.json'):
            with (root / name).open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != manifest['export_files_sha256'][name]:
                    raise ValueError('Classifier differs from the recorded experiment')
        self._classifier_verified = True

    def analyze(self, subject, body):
        from email_utils import clean_email_body
        self.verify_classifier()
        prediction = classify((subject.strip() + ' ' + clean_email_body(body)).strip())
        return {'predictions': prediction, 'summary': summarize_email(subject, body),
                'classifier_status': 'experimental; quality gate failed',
                'summary_method': 'extractive; not generated prose'}

    def retrieve(self, question):
        emails = collection()
        with self._load_lock:
            if self._vectors is None:
                self._vectors = embed_passages([e['subject'] + '\n' + e['body'] for e in emails])
        query = embed_query(question)
        ranked = sorted(zip(emails, self._vectors),
                        key=lambda item: sum(a*b for a,b in zip(query, item[1])), reverse=True)
        # Small corpus has one short passage per message. E5 cosine is a ranking
        # signal, not calibrated confidence or proof that an answer is present.
        return [{'email_id': e['id'], 'chunk_index': 0, 'chunk_id': e['id'],
                 'score': sum(a*b for a,b in zip(query, v)), 'text': e['body'],
                 'subject': e['subject']} for e,v in ranked[:3]]

    def ask(self, question, mode='grounded'):
        chunks, _ = select_evidence(question, self.retrieve(question))
        sources = [dict(c, content=c['text']) for c in chunks]
        facts = resolve_answer(question, sources)
        if facts:
            cited = {f['email_id'] for f in facts}
            return {'status': 'answered', 'answer': format_facts(facts),
                    'mode': 'literal_fact', 'verification': 'source_supported',
                    'sources': [s for s in sources if s['email_id'] in cited]}
        if mode == 'synthesis':
            from local_llm import get_llm_provider
            from rag_citations import validate_citations
            from llm_provider import InvalidGeneration
            context = '\n\n'.join(
                f"[SOURCE email_id={s['email_id']}]\n" +
                json.dumps({'subject': s['subject'], 'content': s['content']}, ensure_ascii=True)
                    .replace('[', '\\u005b').replace(']', '\\u005d').replace('<', '\\u003c').replace('>', '\\u003e') +
                '\n[END SOURCE]' for s in sources)
            answer = get_llm_provider().generate(build_rag_messages(question, context))
            if not is_abstention(answer):
                try:
                    cited = validate_citations(answer, sources)
                except InvalidGeneration:
                    pass
                else:
                    return {'status': 'answered', 'answer': answer, 'mode': 'generated_synthesis',
                            'verification': 'not_semantically_verified',
                            'sources': [s for s in sources if s['email_id'] in cited]}
        return {'status': 'insufficient_evidence', 'answer': (
            'لم أجد إجابة حرفية موثوقة في المصادر. راجع المقاطع المسترجعة.'
            if re.search(r'[\u0600-\u06ff]', question) else
            'No verified literal answer was found. Review the retrieved passages.'),
            'mode': 'retrieval_only', 'verification': 'no_verified_answer', 'sources': sources}
