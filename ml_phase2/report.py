"""Publish only allowlisted aggregates, never data/model/row-level predictions."""
import argparse
import csv
from pathlib import Path

from classifier_contract import LABELS
from .data import CONFIG, digest, read, write


def compare(runs):
    manifests={r['run']['data_manifest_sha256'] for r in runs}
    configurations={r['run']['config_sha256'] for r in runs}
    if len(manifests)!=1 or len(configurations)!=1:
        raise ValueError('Cannot compare different data/config freezes')
    if any(r['run']['test_evaluated'] or r['metrics']['test_evaluated'] for r in runs):
        raise ValueError('Test results cannot enter development selection')
    eligible=[r for r in runs if r['run']['eligible_research_selection'] and r['run']['candidate'] != 'B']
    best=max(eligible,key=lambda r:(r['metrics']['top1_macro_f1'],r['metrics']['top1_accuracy'],-r['run']['benchmark']['p95_ms']))
    return {'selected_research_candidate':best['run']['candidate'], 'production_selected_model':None,
        'selection_rule':read(CONFIG)['selection'], 'test_results':None,
        'test_status':'Not evaluated; historically exposed public corpus is not an untouched release holdout',
        'arabic_results':None, 'arabic_status':'No valid Arabic labels in the admitted source',
        'quality_gate':'NOT PASSED; unchanged V10 remains FAIL',
        'runs':runs}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs',nargs='+',type=Path,required=True)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    values=[{'run':read(p/'run.json'),'metrics':read(p/'metrics.json'),'training_history':read(p/'training-history.json')} for p in args.runs]
    result=compare(values)
    if any(r['run']['data_manifest_sha256'] != digest(args.data/'manifest.json') for r in values):
        raise ValueError('Dataset card must match measured runs')
    args.output.mkdir(parents=True,exist_ok=False)
    write(args.output/'experiment-comparison.json',result)
    write(args.output/'dataset-card.json',read(args.data/'dataset-card.json'))
    write(args.output/'training-configuration.json',read(CONFIG))
    write(args.output/'code-manifest.json',{p.relative_to(Path(__file__).parents[1]).as_posix():digest(p)
        for p in sorted(Path(__file__).parent.glob('*.py'))})
    for row in values:
        name=row['run']['candidate']
        write(args.output/f'{name}-evaluation.json',row['metrics'])
        write(args.output/f'{name}-training-history.json',row['training_history'])
        with (args.output/f'{name}-confusion.csv').open('x',newline='',encoding='utf-8') as stream:
            writer=csv.writer(stream);writer.writerow(['gold/predicted',*LABELS])
            writer.writerows([label,*counts] for label,counts in zip(LABELS,row['metrics']['confusion_matrix']))
        with (args.output/f'{name}-per-class.csv').open('x',newline='',encoding='utf-8') as stream:
            writer=csv.writer(stream);writer.writerow(['label','precision','recall','f1','support'])
            writer.writerows([label,*[m[k] for k in ('precision','recall','f1','support')]] for label,m in row['metrics']['per_class'].items())
    print(result['selected_research_candidate'])


if __name__ == '__main__':
    main()
