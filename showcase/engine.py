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
from showcase.intelligence import chunks as document_chunks, index_version, compose, metadata, task_records, unsafe

ROOT = Path(__file__).resolve().parents[1]


def collection():
    # Fresh decoded objects prevent a caller from mutating the shared corpus.
    rows = json.loads((Path(__file__).parent / 'collection.json').read_text(encoding='utf-8'))
    if (len(rows)>50 or len({e['id'] for e in rows})!=len(rows)
            or any(not e['sender'].endswith('@example.invalid') or len(e['body'])>12000 for e in rows)):
        raise ValueError('Invalid curated collection')
    return rows


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
    return task_records(email, collection())


class Engine:
    def __init__(self):
        self._vectors = None
        self._load_lock = Lock()
        self._classifier_verified = False
        self._index_version = None
        self._chunks = []

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
            version = index_version(emails)
            if self._vectors is None or version != self._index_version:
                passages = document_chunks(emails)
                vectors = []
                # Bound encoder batch memory on the public CPU process.
                for i in range(0,len(passages),4):
                    vectors.extend(embed_passages([p['embedding_text'] for p in passages[i:i+4]]))
                self._chunks, self._vectors, self._index_version = passages, vectors, version
        query = embed_query(question)
        ranked = sorted(zip(self._chunks, self._vectors),
                        key=lambda item: (-sum(a*b for a,b in zip(query,item[1])), item[0]['chunk_id']))
        unique = {}
        for chunk, vector in ranked:
            if chunk['email_id'] not in unique:
                email=next(e for e in emails if e['id']==chunk['email_id'])
                unique[chunk['email_id']]={k:v for k,v in chunk.items() if k!='embedding_text'}
                unique[chunk['email_id']].update(score=sum(a*b for a,b in zip(query,vector)),
                    text=email['body'],matched_text=chunk['text'],sender=email['sender'],date=email['date'])
        # All documents in this bounded corpus are candidates for exhaustive
        # task/calendar filtering; ranking remains actual E5 max-chunk cosine.
        return list(unique.values())

    def ask(self, question, mode='grounded'):
        ranked = self.retrieve(question)
        composed = compose(question, ranked, collection())
        if composed:
            return composed
        chunks, _ = select_evidence(question, ranked[:3])
        sources = [dict(c, content=c['text']) for c in chunks]
        # Do not feed an embedded control instruction into fact composition.
        sources = [s for s in sources if not unsafe(s['content'])]
        facts = resolve_answer(question, sources) if not unsafe(question) else []
        if facts:
            cited = {f['email_id'] for f in facts}
            return {'status': 'answered', 'answer': format_facts(facts),
                    'mode': 'literal_fact', 'verification': 'source_supported',
                    'sources': [s for s in sources if s['email_id'] in cited]}
        if mode == 'synthesis' and not unsafe(question):
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
