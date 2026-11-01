"""Fail closed when a receipt cannot establish the provisional Linux resource gate."""
import argparse
import json
from pathlib import Path


def assess(report):
    reasons=[]
    if report.get('platform')!='linux':reasons.append('No Linux container measurement')
    if report.get('status')!='completed':reasons.append('Combined inference probe did not complete')
    if not report.get('real_inference') or report.get('mocked_inference'):reasons.append('Real inference not established')
    cgroup=report.get('observer_final',report.get('snapshots',{}).get('final',{})).get('cgroup_v2',{})
    try:
        quota,period=map(int,cgroup['cpu.max'].split())
        if quota<=0 or period<=0 or not .09<=quota/period<=.11:reasons.append('CPU quota is not approximately 0.1 CPU')
        if not 0<int(cgroup['memory.max'])<=512*2**20:reasons.append('Memory limit is outside the 512 MiB budget')
        if int(cgroup['memory.swap.max'])!=0:reasons.append('Swap was not disabled')
        if not 0<int(cgroup['memory.peak'])<=400*2**20:reasons.append('Container peak is outside the provisional 400 MiB target')
        events=dict(line.split() for line in cgroup['memory.events'].splitlines())
        if any(int(events[key])!=0 for key in ('oom','oom_kill')):reasons.append('Container OOM recorded')
    except (KeyError,ValueError,ZeroDivisionError):reasons.append('Complete finite cgroup limits and peak evidence unavailable')
    return {'technical_gate':'FAIL' if reasons else 'PASS','reasons':reasons,
            'render_accepted':False,'note':'Local container engineering gate only; never deployment authorization.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt',type=Path)
    args=parser.parse_args()
    result=assess(json.loads(args.receipt.read_text(encoding='utf-8')))
    print(json.dumps(result,indent=2))
    if result['technical_gate']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
