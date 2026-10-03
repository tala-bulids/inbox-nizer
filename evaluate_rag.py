"""Opt-in local evaluation; read-only DB, no downloads, no saved email bodies."""

import argparse
import json
import os
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--question', action='append', required=True)
    parser.add_argument('--chunk-limit', type=int, default=4)
    parser.add_argument('--max-context-chars', type=int, default=6000)
    parser.add_argument('--show-evidence', action='store_true')
    parser.add_argument('--preview-facts', action='store_true', help='Extract facts in memory; no database writes')
    args = parser.parse_args()
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    from sqlalchemy import text
    from database import SessionLocal
    from local_llm import get_llm_provider
    from rag_service import prepare_rag_request, answer_email_question

    for question in args.question:
        with SessionLocal() as db:
            db.execute(text('SET TRANSACTION READ ONLY'))
            prepared = prepare_rag_request(db, question, chunk_limit=args.chunk_limit,
                                           max_context_chars=args.max_context_chars, preview_facts=args.preview_facts)
            report = {'question': question,
                      'retrieved': [{k: c[k] for k in ('email_id', 'chunk_index', 'score')}
                                    for c in prepared['retrieved_chunks']],
                      'evidence_selection': prepared['evidence_audit'],
                      'explicit_answer_candidate': prepared['answer_candidate'],
                      'resolved_facts': prepared['resolved_facts'], 'llm_calls': 0,
                      'structured_facts': prepared['structured_facts']}
            if args.show_evidence:
                report['context'] = prepared['context']
            class RecordingProvider:
                def generate(self, messages):
                    report['llm_calls'] += 1
                    started = time.perf_counter()
                    answer = get_llm_provider().generate(messages)
                    report['generation_seconds'] = time.perf_counter() - started
                    report['raw_answer'] = answer
                    return answer
            try:
                started = time.perf_counter()
                result = answer_email_question(db, question, RecordingProvider(), chunk_limit=args.chunk_limit,
                                               max_context_chars=args.max_context_chars, preview_facts=args.preview_facts)
                report['service_seconds'] = time.perf_counter() - started
                report['status'] = result['status']
                report['final_answer'] = result['answer']
                report['application_changed_answer'] = result['answer'] != report.get('raw_answer', '').strip()
                report['answer_path'] = (
                    'deterministic' if result['status'] == 'answered' and report['llm_calls'] == 0
                    else 'application_abstention' if result['status'] == 'insufficient_evidence'
                    else 'model_answer')
                report['citations'] = result['citations']
                report['citation_validation'] = 'passed' if result['status'] == 'answered' else 'not_applicable'
            except Exception as error:
                report['error'] = type(error).__name__
            # JSON ASCII escaping keeps Arabic legible as Unicode escapes on Windows.
            print(json.dumps(report, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
