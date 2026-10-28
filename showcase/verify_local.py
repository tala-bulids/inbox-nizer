"""Opt-in real model smoke on authored inputs; no DB, Gmail or quality claim."""
import argparse
import json
from pathlib import Path
import time

from showcase.engine import Engine, collection, tasks


def verify():
    engine = Engine()
    report = {'input_provenance': 'authored fictional showcase collection',
              'database_used': False, 'google_used': False, 'quality_evaluation': False,
              'classification': [], 'ask': []}
    for email in collection()[:2]:
        start = time.perf_counter()
        result = engine.analyze(email['subject'], email['body'])
        assert len(result['predictions']) == 1 and result['summary']
        report['classification'].append({'language': email['language'], 'returned_prediction': True,
                                        'seconds': time.perf_counter()-start})
    for language, question, value in [('en', 'What is the Atlas workshop date?', '2026-11-05'),
                                      ('ar', 'ما تاريخ الورشة؟', '2026-11-08')]:
        start = time.perf_counter()
        result = engine.ask(question)
        assert result['status'] == 'answered' and value in result['answer'], result['status']
        report['ask'].append({'language': language, 'literal_answer_matches_source': True,
                             'seconds': time.perf_counter()-start})
    assert engine.ask('What is my bank account password?')['status'] == 'insufficient_evidence'
    report['unknown_question_abstained'] = True
    report['extracted_tasks'] = sum(len(tasks(email)) for email in collection())
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Do not overwrite evidence')
    result = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2)
    print(json.dumps(result))
