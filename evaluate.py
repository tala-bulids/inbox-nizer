import argparse
import json
from pathlib import Path

from email_utils import clean_email_body
from classifier_config import model_path as resolve_model_path
from predict import load_classifier, predict_with_classifier


def evaluate_emails(model_path, emails):
    model_path = resolve_model_path(model_path)
    tokenizer, model = load_classifier(model_path)
    results = []
    for email in emails:
        body = clean_email_body(email.get('body', ''))
        result = {
            'subject': email.get('subject', ''), 'body': body,
            'predictions': predict_with_classifier(tokenizer, model, email.get('subject'), email.get('body'))
        }
        if 'expected_labels' in email:
            result['expected_labels'] = email['expected_labels']
            result['correct'] = result['predictions'][0]['category'] in email['expected_labels']
        results.append(result)
    labeled = [row for row in results if 'correct' in row]
    return {'model': str(model_path), 'emails': results,
            'top1_accuracy': sum(row['correct'] for row in labeled) / len(labeled) if labeled else None,
            'labeled_count': len(labeled)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='Local artifact directory; defaults to EMAIL_MODEL_PATH.')
    parser.add_argument('--samples', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    emails = json.loads(Path(args.samples).read_text(encoding='utf-8'))['emails']
    report = evaluate_emails(args.model, emails)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'emails': len(emails), 'labeled_count': report['labeled_count'],
                      'top1_accuracy': report['top1_accuracy']}))


if __name__ == '__main__':
    main()
