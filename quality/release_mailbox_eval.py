"""Read-only mailbox diagnostics; no message text or answers in output artifacts.

These are development probes, not a human-judged correctness benchmark.
Run before/after in separate processes so cold-model costs remain visible.
"""
import argparse
import hashlib
import json
import time
import traceback
from pathlib import Path

CASES = [
    ('travel_ar', 'متى رحلتي لجدة؟'),
    ('travel_en', 'when is my flight to Jeddah?'),
    ('travel_en_verb', 'when am I travelling to Jeddah?'),
    ('travel_mixed', 'متى flight حقي لجدة؟'),
    ('digest_ar', 'وش آخر المستجدات؟'),
    ('digest_en', 'What changed recently?'),
    ('digest_week', 'وش جاني هالأسبوع؟'),
    ('existence_ar', 'هل استلمت أي نشرة من فيصل؟'),
    ('existence_university', 'هل وصلني شيء من الجامعة؟'),
    ('status_ar', 'انقبلت بمعسكر؟'),
    ('status_plural', 'وش آخر تحديثات طلباتي؟'),
    ('unsupported', 'What is my submarine booking reference?'),
]


def fingerprint(connection):
    from sqlalchemy import text
    result = {}
    # Static table names only; hashes include every persisted column.
    for table in ('emails', 'email_tasks', 'email_predictions', 'email_facts',
                  'email_embedding_chunks', 'processing_states'):
        with connection.begin_nested():
            exists = connection.scalar(text('SELECT to_regclass(:name)'), {'name': table})
            if not exists:
                continue
            rows = connection.execute(text(f'SELECT md5(row_to_json(t)::text) FROM {table} t')).scalars()
            hashes = sorted(rows)
            result[table] = {'count': len(hashes), 'sha256': hashlib.sha256(''.join(hashes).encode()).hexdigest()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user-id', required=True, type=int)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--fingerprint-only', action='store_true')
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv('.env')
    from sqlalchemy import text
    from database import engine
    from ownership import OwnedSession
    from rag_service import answer_email_question
    from local_llm import get_llm_provider
    import psutil

    class LocalProvider:
        calls = 0

        def generate(self, messages):
            self.calls += 1
            return get_llm_provider().generate(messages)

    report = {'evidence_type': 'unjudged_development_diagnostics', 'human_correctness': None,
              'cases': [], 'production_writes': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')

    with engine.connect() as connection:
        transaction = connection.begin()
        connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
        report['fingerprint'] = fingerprint(connection)
        save()
        if not args.fingerprint_only:
            with OwnedSession(bind=connection, user_id=args.user_id, autoflush=False) as db:
                for name, question in CASES:
                    provider = LocalProvider()
                    started = time.perf_counter()
                    try:
                        # A timeout in one query must not poison every later case.
                        with db.begin_nested():
                            answer = answer_email_question(db, question, provider)
                        row = {'case': name, 'status': answer['status'], 'mode': answer.get('answer_mode'),
                               'verification': answer.get('verification'),
                               'sources': [source['email_id'] for source in answer['sources']],
                               'answer_sha256': hashlib.sha256(answer['answer'].encode()).hexdigest(),
                               'answer_chars': len(answer['answer'])}
                    except Exception as error:
                        row = {'case': name, 'status': 'error', 'error_type': type(error).__name__,
                               'sqlstate':getattr(getattr(error,'orig',None),'sqlstate',None),
                               'application_frames':[frame.name for frame in traceback.extract_tb(error.__traceback__)
                                   if Path(frame.filename).parent==Path.cwd()]}
                    row.update(seconds=round(time.perf_counter() - started, 4), llm_calls=provider.calls,
                               rss_mib=round(psutil.Process().memory_info().rss / 1024**2, 1),
                               available_mib=round(psutil.virtual_memory().available / 1024**2, 1))
                    report['cases'].append(row)
                    save()
                    print(json.dumps(row), flush=True)
        transaction.rollback()
    print('Read-only evaluation complete.', flush=True)


if __name__ == '__main__':
    main()
