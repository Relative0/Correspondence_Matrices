"""Profile-driven binding fix against frozen code and equally improved M4RI."""
import argparse
import gc
import importlib.util
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

from scripts import cm_scalar_research_campaign as campaign
from scripts import cm_scalar_m4ri_control as native
from cmbench.backends.affine_constraints import AffineConstraintPlan, parse_alist

AUDIT = campaign.AUDIT
spec = importlib.util.spec_from_file_location('scalar_pre_binding', AUDIT/'revisions/pre-binding/affine_constraints.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
METHODS = ('rows_legacy', 'rows_indexed', 'm4ri_legacy', 'm4ri_indexed')


class IndexedM4ri(native.M4riControl):
    def count(self, fixed=None):
        # Identical native conversion/elimination; only validation uses the index.
        context = self.plan._context(fixed)
        mask = sum(1 << self.positions[n] for n in context)
        ones = sum(1 << self.positions[n] for n, v in context.items() if v)
        rows = [r & ~mask for r in self.plan.rows]
        rhs = [b ^ ((r & ones).bit_count() & 1) for r, b in zip(self.plan.rows, self.plan.rhs)]
        n = len(self.plan.basis)
        rank = self.rank(rows, n)
        if any(rhs) and self.rank([r | (b << n) for r, b in zip(rows, rhs)], n+1) != rank: return 0
        return 1 << (n-len(context)-rank)


def freeze():
    cases = [c for c in json.loads((AUDIT/'FIXTURES.json').read_text()) if c['task'] == 'affine']
    for n in (1024, 2048):
        rng = random.Random(2026091147+n)
        columns = [[] for _ in range(n)]; rows = []
        for j in range(n//2):
            indexes = sorted(rng.sample(range(n), 8)); rows.append([i+1 for i in indexes])
            for i in indexes: columns[i].append(j+1)
        lines = [[n, len(rows)], [max(map(len, columns)), 8], list(map(len, columns)), [8]*len(rows)]
        lines += [c if c else [0] for c in columns] + rows
        alist = '\n'.join(' '.join(map(str, line)) for line in lines)+'\n'
        assert parse_alist(alist)[0] == n
        cases.append(dict(id=f'fresh-binding-n{n}', task='affine', n=n, alist=alist,
                          cohort='fresh synthetic binding confirmation'))
    campaign.write(AUDIT/'BINDING-FIXTURES.json', cases)
    schedule = [dict(case=c['id'], q=q, repeat=r, method=m) for c in cases for q in (1, 8)
                for r in range(9) for m in (METHODS if r % 2 == 0 else METHODS[::-1])]
    campaign.write(AUDIT/'BINDING-SCHEDULE.json', schedule)


def session(case, method, q, warm=True):
    start = time.perf_counter_ns()
    n, rows = parse_alist(case['alist']); basis = tuple(f'x{i}' for i in range(n))
    cls = {'rows_legacy': legacy.AffineConstraintPlan, 'rows_indexed': AffineConstraintPlan,
           'm4ri_legacy': native.M4riControl, 'm4ri_indexed': IndexedM4ri}[method]
    runner = cls(rows, [0]*len(rows), basis)
    contexts = campaign.queries(case, q)
    setup = time.perf_counter_ns()-start
    start = time.perf_counter_ns()
    result = json.dumps([runner.count(c) for c in contexts], separators=(',', ':'))
    query = time.perf_counter_ns()-start
    warm_ns = None
    if warm:
        start = time.perf_counter_ns()
        again = json.dumps([runner.count(c) for c in contexts], separators=(',', ':'))
        warm_ns = time.perf_counter_ns()-start
        assert again == result
    start = time.perf_counter_ns(); del runner
    cleanup = time.perf_counter_ns()-start
    return dict(result=result, total_ns=setup+query+cleanup, setup_ns=setup, query_ns=query,
                cleanup_ns=cleanup, warm_ns=warm_ns)


def run(output):
    native.correctness(output)
    cases = json.loads((AUDIT/'BINDING-FIXTURES.json').read_text())
    schedule = json.loads((AUDIT/'BINDING-SCHEDULE.json').read_text())
    indexed = {c['id']: c for c in cases}
    expected = {(c['id'], q): campaign.session(c, 'flint', q)['result'] for c in cases for q in (1, 8)}
    campaign.write(output/'ORACLES.json', [dict(case=k[0], q=k[1], result=v) for k, v in expected.items()])
    campaign.write(output/'CORPUS-CHECKS.json', campaign.corpus_checks())
    rows = []
    with (output/'RAW.jsonl').open('x') as stream:
        for cell in schedule:
            gc.collect()
            row = dict(cell, **session(indexed[cell['case']], cell['method'], cell['q']))
            assert row['result'] == expected[(cell['case'], cell['q'])]
            row['exact'] = True
            stream.write(json.dumps(row)+'\n'); stream.flush(); rows.append(row)
    summaries = []
    for c in cases:
        for q in (1, 8):
            selected = [r for r in rows if r['case'] == c['id'] and r['q'] == q]
            for m in METHODS:
                a = [r for r in selected if r['method'] == m]
                base = {r['repeat']: r for r in selected if r['method'] == ('m4ri_legacy' if m.startswith('m4ri') else 'rows_legacy')}
                ratios = [base[r['repeat']]['total_ns']/r['total_ns'] for r in a]
                summaries.append(dict(case=c['id'], q=q, method=m,
                    median_total_ns=statistics.median(r['total_ns'] for r in a),
                    median_warm_ns=statistics.median(r['warm_ns'] for r in a),
                    paired_geomean=statistics.geometric_mean(ratios), min_pair=min(ratios), max_pair=max(ratios)))
    campaign.write(output/'SUMMARY.json', summaries)
    records = []
    for r in range(3):
        for m in METHODS:
            start = time.perf_counter_ns()
            child = subprocess.run([sys.executable, '-B', '-m', 'scripts.cm_affine_binding_diagnostic', 'worker', '--method', m],
                                   capture_output=True, text=True, check=True, timeout=90)
            row = dict(method=m, repeat=r, lifecycle_ns=time.perf_counter_ns()-start, **json.loads(child.stdout))
            assert row['result'] == expected[(cases[-1]['id'], 8)]
            records.append(row)
    campaign.write(output/'MEMORY.json', records)
    reread = [json.loads(line) for line in (output/'RAW.jsonl').read_text().splitlines()]
    assert [{k: r[k] for k in ('case', 'q', 'repeat', 'method')} for r in reread] == schedule
    assert all(r['result'] == expected[(r['case'], r['q'])] for r in reread)
    campaign.write(output/'RESULT.json', dict(cells=len(rows), asserted_outputs=2*sum(r['q'] for r in rows),
                   memory_children=len(records), source_before_sha256=campaign.sha(AUDIT/'revisions/pre-binding/affine_constraints.py'),
                   source_after_sha256=campaign.sha(campaign.ROOT/'cmbench/backends/affine_constraints.py'), exact=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'run', 'worker'))
    parser.add_argument('--output', type=Path); parser.add_argument('--method')
    args = parser.parse_args()
    if args.action == 'freeze': freeze()
    elif args.action == 'run': run(args.output)
    else:
        case = json.loads((AUDIT/'BINDING-FIXTURES.json').read_text())[-1]
        before = campaign.process_memory()
        row = session(case, args.method, 8, warm=False)
        print(json.dumps(dict(before=before, after=campaign.process_memory(), **row)))


if __name__ == '__main__': main()
