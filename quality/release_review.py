"""Private human review queues and transparent metrics; never invent review labels.

Prepare task queues with a read-only mailbox snapshot. Ask CSVs accept human
questions/judgements; the development runner fills only machine answer fields.
Final scoring requires an explicit frozen review hash and consumes one receipt.
"""
import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

ASK_FIELDS = ['case_id', 'question', 'history', 'selected_email_id', 'language', 'intent',
    'answer', 'source_evidence', 'status', 'answerable', 'answer_correct', 'source_correct',
    'citation_correct', 'unsupported_factual_answer', 'reviewer', 'label_source', 'reviewed_at']
TASK_FIELDS = ['email_id', 'subject', 'sender', 'date', 'body', 'predicted_tasks',
    'gold_task_count', 'correct_task_indices', 'gold_deadline_count', 'correct_deadline_indices',
    'ambiguous', 'reviewer', 'label_source', 'reviewed_at']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, fields, rows):
    # Exclusive creation protects existing reviewer work.
    from quality.mailbox_gold import safe
    with Path(path).open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: safe(row.get(key, '')) for key in fields} for row in rows)


def reviewed(row):
    from datetime import date
    try:
        date.fromisoformat(row.get('reviewed_at', ''))
    except ValueError:
        return False
    return bool(row.get('reviewer', '').strip()) and row.get('label_source') == 'human_reviewed'


def _indices(value, size):
    result = json.loads(value)
    if (not isinstance(result, list) or any(type(i) is not int or not 1 <= i <= size for i in result)
            or len(set(result)) != len(result)):
        raise ValueError('Review indices must be unique one-based prediction numbers')
    return set(result)


def task_metrics(rows):
    totals = dict(reviewed=0, pending=0, ambiguous=0, tp=0, fp=0, fn=0,
                  deadline_tp=0, deadline_fp=0, deadline_fn=0)
    for row in rows:
        if not reviewed(row):
            totals['pending'] += 1
            continue
        if row['ambiguous'] == 'yes':
            totals['ambiguous'] += 1
            continue
        if row['ambiguous'] != 'no':
            raise ValueError('Human must mark ambiguous yes/no')
        predicted = json.loads(row['predicted_tasks'])
        gold, dates = int(row['gold_task_count']), int(row['gold_deadline_count'])
        correct = _indices(row['correct_task_indices'], len(predicted))
        deadlines = _indices(row['correct_deadline_indices'], len(predicted))
        emitted = {i for i, task in enumerate(predicted, 1) if any(task.get(k) for k in ('deadline_text', 'deadline_date', 'deadline_at'))}
        if gold < len(correct) or dates < len(deadlines) or dates > gold or not deadlines <= correct & emitted:
            raise ValueError('Inconsistent action/deadline adjudication')
        totals['reviewed'] += 1
        for key, count in dict(tp=len(correct), fp=len(predicted)-len(correct), fn=gold-len(correct),
            deadline_tp=len(deadlines), deadline_fp=len(emitted)-len(deadlines), deadline_fn=dates-len(deadlines)).items():
            totals[key] += count
    for prefix in ('', 'deadline_'):
        tp, fp, fn = (totals[prefix+k] for k in ('tp', 'fp', 'fn'))
        totals[prefix+'precision'] = tp/(tp+fp) if tp+fp else None
        totals[prefix+'recall'] = tp/(tp+fn) if tp+fn else None
    totals['deadline_association_accuracy'] = totals['deadline_precision']
    return totals


def ask_metrics(rows):
    totals = dict(reviewed=0, pending=0, answered=0, answerable=0, answer_correct=0,
        source_correct=0, citation_correct=0, false_abstentions=0, unsupported_factual_answers=0)
    for row in rows:
        if not reviewed(row):
            totals['pending'] += 1
            continue
        keys = ('answerable', 'answer_correct', 'source_correct', 'citation_correct', 'unsupported_factual_answer')
        if any(row.get(key) not in ('yes', 'no') for key in keys):
            raise ValueError('Every Ask judgement needs an explicit human yes/no')
        answered = row['status'] == 'answered'
        totals['reviewed'] += 1
        totals['answered'] += answered
        totals['answerable'] += row['answerable'] == 'yes'
        totals['answer_correct'] += row['answer_correct'] == 'yes'
        totals['source_correct'] += answered and row['source_correct'] == 'yes'
        totals['citation_correct'] += answered and row['citation_correct'] == 'yes'
        totals['false_abstentions'] += row['status'] == 'insufficient_evidence' and row['answerable'] == 'yes'
        totals['unsupported_factual_answers'] += row['unsupported_factual_answer'] == 'yes'
    for metric, numerator, denominator in (
        ('answer_accuracy', 'answer_correct', 'reviewed'),
        ('source_accuracy', 'source_correct', 'answered'),
        ('citation_accuracy', 'citation_correct', 'answered'),
        ('false_abstention_rate', 'false_abstentions', 'answerable'),
        ('unsupported_factual_answer_rate', 'unsupported_factual_answers', 'reviewed')):
        totals[metric] = totals[numerator]/totals[denominator] if totals[denominator] else None
    return totals


def evaluate(path, kind, *, final=False, freeze=None):
    path = Path(path)
    if 'holdout' in path.name.lower() and not final:
        raise ValueError('Holdout is available only through final evaluation')
    if final:
        if freeze is None:
            raise ValueError('Final evaluation requires a freeze manifest')
        frozen = json.loads(Path(freeze).read_text(encoding='utf-8'))
        if (frozen.get('selection_complete') is not True or frozen.get('holdout_used_for_selection') is not False
                or frozen.get('review_sha256') != digest(path)
                or not isinstance(frozen.get('artifact_sha256'), str)
                or len(frozen['artifact_sha256']) != 64):
            raise ValueError('Freeze must bind reviewed evidence and a selected artifact')
        with path.with_suffix('.consumed.json').open('x', encoding='utf-8') as stream:
            json.dump({'review_sha256': digest(path), 'freeze_sha256': digest(freeze)}, stream)
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    return dict(kind=kind, evidence='human_attestation_not_independently_verified', final=final,
                representative_release_pass=False,
                metrics=(task_metrics if kind == 'tasks' else ask_metrics)(rows))


def prepare_tasks(user_id, output, count=100):
    from dotenv import load_dotenv
    load_dotenv('.env')
    from sqlalchemy import select, text
    from database import engine
    from models import Email
    from ownership import OwnedSession
    from task_extractor import extract_action_items
    from deadline_extractor import parse_email_datetime
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    with engine.connect() as connection:
        tx = connection.begin()
        connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
        with OwnedSession(bind=connection, user_id=user_id, autoflush=False) as db:
            # Random, deterministic email sampling. Thread/domain representativeness
            # is not asserted; human review must flag related/ambiguous examples.
            ids = list(db.scalars(select(Email.id).order_by(Email.id)))
            random.Random(171026).shuffle(ids)
            groups = {'development': ids[:count], 'holdout': ids[count:2*count]}
            for split, selected in groups.items():
                rows = []
                for email in db.scalars(select(Email).where(Email.id.in_(selected)).order_by(Email.id)):
                    tasks = extract_action_items(email.subject or '', email.body or '', parse_email_datetime(email.email_date))
                    rows.append(dict(email_id=email.id, subject=email.subject, sender=email.sender,
                        date=email.email_date, body=email.body,
                        predicted_tasks=json.dumps(tasks, ensure_ascii=False, default=str)))
                write_csv(output / f'tasks-{split}.csv', TASK_FIELDS, rows)
        tx.rollback()
    (output/'sampling.json').write_text(json.dumps({'seed':171026,'counts':{k:len(v) for k,v in groups.items()},
        'selection':'uniform owned email sample, disjoint row splits; thread/domain independence unproven',
        'representative_release_pass':False,'human_labels_created':0}), encoding='utf-8')


def prepare_ask(user_id, output, measurements):
    """Existing development probes only; blank holdout questions require humans."""
    from dotenv import load_dotenv
    load_dotenv('.env')
    from time import perf_counter
    from sqlalchemy import select, text
    from database import engine
    from ownership import OwnedSession
    from models import Email
    from rag_service import answer_email_question
    from rag_api import _LazyProvider
    from semantic_search import semantic_search
    from quality.release_mailbox_eval import CASES, fingerprint
    import psutil
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    rows, timings = [], []
    with engine.connect() as connection:
        tx = connection.begin()
        connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
        before = fingerprint(connection)
        with OwnedSession(bind=connection, user_id=user_id, autoflush=False) as db:
            cases = [(name, question, [], None) for name, question in CASES]
            cases += [('followup', 'طيب K&A بس؟', ['وش صار على طلباتي؟'], None),
                      ('ambiguity', 'متى رحلتي؟', [], None)]
            for name, question, history, selected in cases:
                started = perf_counter()
                try:
                    with db.begin_nested():
                        answer = answer_email_question(db, question, _LazyProvider(), history=history, email_id=selected)
                        ids = {s['email_id'] for s in answer['sources']}
                        ids.update(s['email_id'] for s in answer.get('clarification_options', []) or [])
                        evidence = [dict(email_id=e.id, subject=e.subject, sender=e.sender, date=e.email_date, body=e.body)
                            for e in db.scalars(select(Email).where(Email.id.in_(ids)))]
                    rows.append(dict(case_id=name, question=question, history=json.dumps(history, ensure_ascii=False),
                        selected_email_id=selected or '', language='mixed' if name=='travel_mixed' else 'ar' if any('\u0600'<=c<='\u06ff' for c in question) else 'en',
                        intent=name, answer=answer['answer'], source_evidence=json.dumps(evidence, ensure_ascii=False), status=answer['status']))
                    timings.append(dict(case=name, seconds=round(perf_counter()-started,4), status=answer['status'],
                        mode=answer.get('answer_mode'), rss_mib=round(psutil.Process().memory_info().rss/2**20,1)))
                    if name == 'ambiguity' and answer.get('clarification_options'):
                        cases.append(('clarification_selection', question, [], answer['clarification_options'][0]['email_id']))
                except Exception as error:
                    timings.append(dict(case=name, seconds=round(perf_counter()-started,4), error_type=type(error).__name__))
                print(json.dumps(timings[-1]), flush=True)
            for language, query in [('ar','مواعيد السفر'),('en','travel bookings'),('mixed','flight إلى جدة')]:
                started = perf_counter()
                with db.begin_nested():
                    matches = semantic_search(db, query)
                timings.append(dict(case='search_'+language, seconds=round(perf_counter()-started,4), returned=len(matches)))
        after = fingerprint(connection)
        tx.rollback()
    write_csv(output/'ask-development.csv', ASK_FIELDS, rows)
    write_csv(output/'ask-holdout.csv', ASK_FIELDS, [])
    Path(measurements).write_text(json.dumps(dict(evidence='unjudged_development_only',
        measurements=timings, before=before, after=after, read_only=True,
        source_checksums_unchanged=before==after, human_labels_created=0),indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('prepare-tasks')
    prepare.add_argument('--user-id', type=int, required=True)
    prepare.add_argument('--output', type=Path, required=True)
    ask = sub.add_parser('prepare-ask')
    ask.add_argument('--user-id', type=int, required=True)
    ask.add_argument('--output', type=Path, required=True)
    ask.add_argument('--measurements', type=Path, required=True)
    score = sub.add_parser('score')
    score.add_argument('--csv', type=Path, required=True)
    score.add_argument('--kind', choices=['tasks', 'ask'], required=True)
    score.add_argument('--final', action='store_true')
    score.add_argument('--freeze', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare-tasks':
        prepare_tasks(args.user_id, args.output)
        print('Private task queues created; zero human labels. Do not open holdout during development.')
    elif args.command == 'prepare-ask':
        prepare_ask(args.user_id, args.output, args.measurements)
    else:
        print(json.dumps(evaluate(args.csv, args.kind, final=args.final, freeze=args.freeze), indent=2))


if __name__ == '__main__':
    main()
