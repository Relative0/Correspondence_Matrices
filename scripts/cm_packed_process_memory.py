"""Separate post-campaign process-memory diagnostic on all consumed n24 cases.

Linux rusage persists across exec and can contain a fork/launcher high-water
floor. Preserve it, but also read the current process address space's VmHWM and
VmRSS. These kernel counters are approximate, not allocation-exact budgets.
"""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import tempfile

from scripts import cm_packed_io_campaign as campaign
from scripts import cm_packed_queries_campaign as prior


def process_memory():
    values = {}
    for line in Path('/proc/self/status').read_text().splitlines():
        key, _, value = line.partition(':')
        if key in ('VmHWM', 'VmRSS', 'VmPeak'):
            fields = value.split()
            if len(fields) != 2 or fields[1] != 'kB': raise ValueError('unexpected proc unit')
            values[key + '_KiB'] = int(fields[0])
    if set(values) != {'VmHWM_KiB', 'VmRSS_KiB', 'VmPeak_KiB'}:
        raise ValueError('required Linux memory counters absent')
    values['rusage_maxrss_KiB'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return values


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    cases = [case for case in campaign.fixtures() if case['n'] == 24]
    prior.write(output / 'FIXTURES.json', cases)
    schedule = [dict(case=case['id'], method=method, repeat=repeat)
                for case in cases for repeat in range(3)
                for method in (campaign.methods(case) if repeat % 2 == 0 else campaign.methods(case)[::-1])]
    prior.write(output / 'FREEZE.json', dict(
        scope='Post-campaign diagnostic on all three consumed n24 cases and all 13 arms; no new speed gate.',
        schedule=schedule, q=1, source_sha256=prior.sha(Path(__file__)),
        campaign_source_sha256=prior.sha(Path(campaign.__file__)),
        fixtures_sha256=prior.sha(output / 'FIXTURES.json'),
        counters='rusage_maxrss plus /proc/self/status VmHWM/VmRSS/VmPeak; KiB; no peak reset',
        limitations='Kernel RSS counters are approximate. Includes interpreter and libraries, excludes other processes.'))
    targets = {}
    for case in cases:
        prior.write(output / (case['id'] + '.json'), case['document'])
        target = campaign.oracle(case, {})
        targets[case['id']] = [target['count']] if case['task'] == 'count' else [
            {k: target[k] for k in ('sha256', 'bytes')}]
    prior.write(output / 'ORACLES.json', targets)
    gc.collect()
    rows = []
    for cell in schedule:
        child = subprocess.run([sys.executable, '-B', '-m', 'scripts.cm_packed_process_memory', 'worker',
                                '--output', str(output), '--case', cell['case'], '--method', cell['method']],
                               capture_output=True, text=True, timeout=90, check=True)
        row = json.loads(child.stdout)
        assert row['result'] == targets[cell['case']]
        assert row['after']['VmHWM_KiB'] >= row['after']['VmRSS_KiB'] > 0
        rows.append(dict(cell, **row, exact=True))
    prior.write(output / 'RAW.json', rows)
    summary = []
    for case in cases:
        for method in campaign.methods(case):
            selected = [r for r in rows if r['case'] == case['id'] and r['method'] == method]
            summary.append(dict(case=case['id'], method=method,
                                median_before={k: statistics.median(r['before'][k] for r in selected)
                                               for k in selected[0]['before']},
                                median_after={k: statistics.median(r['after'][k] for r in selected)
                                              for k in selected[0]['after']}))
    prior.write(output / 'SUMMARY.json', summary)
    prior.write(output / 'RESULT.json', dict(status='complete', exact_children=len(rows),
                                            schedule_verified=True, parent_memory=process_memory()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('run', 'worker'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case')
    parser.add_argument('--method')
    args = parser.parse_args()
    if args.action == 'run': run(args.output)
    else:
        case = next(c for c in json.loads((args.output / 'FIXTURES.json').read_text()) if c['id'] == args.case)
        before = process_memory()
        with tempfile.TemporaryDirectory(prefix='cm-memory-child-') as temporary:
            result, files, measures = campaign.session(case, args.method, 1,
                args.output / (case['id'] + '.json'), Path(temporary), warm=False)
            campaign.reread(files, result)
        after = process_memory()
        print(json.dumps(dict(result=result, before=before, after=after)))


if __name__ == '__main__':
    main()
