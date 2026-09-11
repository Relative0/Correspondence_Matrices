"""Prospectively frozen full/projected counting with independent exact controls."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time

from cmbench.backends.bucket_counts import BucketCNFCountPlan, CountPlanLimit, parse_dimacs
from cmbench.backends.bucket_numpy import NumpyBucketCNFCountPlan
from cmbench.backends.projected_counts import ProjectedCNFCountPlan
from cmbench.comparative.exact_cudd_count import exact_cudd_count

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT/'docs/audits/2026-09-11-cm-next-research'
LIMITS = dict(max_width=14, max_cells=262144, max_work=262144, max_order_checks=2000000)
METHODS = ('bucket_natural', 'bucket_min_fill', 'array_min_fill', 'cudd_natural', 'cudd_dynamic')
SEED = 2026091193


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')


def freeze():
    corpus = json.loads((AUDIT/'CORPUS.json').read_text())
    cases = []
    for row in corpus['files']:
        if not row['admitted']: continue
        text = (AUDIT/'corpus'/row['filename']).read_text()
        n, clauses = parse_dimacs(text)
        cases.append(dict(id=row['id'], cohort='additional_public', n=n,
                          clauses=clauses, projected=list(range(0, n, 2))))
    for m in (8, 12, 24, 48):
        for family in ('independent_aux', 'adjacent_exclusion'):
            clauses = [(2*i+1, 2*i+2) for i in range(m)]
            if family == 'adjacent_exclusion': clauses += [(-2*i-1, -2*i-3) for i in range(m-1)]
            cases.append(dict(id=f'{family}-{m}', cohort='development' if m < 24 else 'confirmation',
                              n=2*m, clauses=clauses, projected=list(range(0, 2*m, 2)), family=family))
    for m in (24, 48):
        cases.append(dict(id=f'hidden_star-{m}', cohort='confirmation', family='hidden_star', n=m+1,
                          clauses=[(i+1, m+1) for i in range(m)], projected=list(range(m))))
    for position, case in enumerate(cases):
        rng = random.Random(SEED+position)
        case['contexts'] = [{}] + [{f'x{i}':rng.randrange(2) for i in rng.sample(range(case['n']), min(3, case['n']))}
                                  for _ in range(31)]
    schedule = [dict(case=c['id'], mode=mode, repeat=r, method=m) for c in cases
                for mode in ('full', 'projected') for r in range(9)
                for m in (METHODS if r % 2 == 0 else METHODS[::-1])]
    write(AUDIT/'COUNT-FIXTURES.json', cases)
    write(AUDIT/'COUNT-SCHEDULE.json', schedule)
    print(json.dumps(dict(cases=len(cases), scheduled_cells=len(schedule))))


def native_runner(case, projected, dynamic):
    from dd.cudd import BDD
    basis = tuple(f'x{i}' for i in range(case['n']))
    manager = BDD(memory_estimate=256 << 20)
    manager.configure(reordering=dynamic, max_memory=256 << 20)
    manager.declare(*basis)
    variables = [manager.var(n) for n in basis]
    root = manager.true
    for clause in case['clauses']:
        term = manager.false
        for literal in clause:
            v = variables[abs(literal)-1]
            term |= v if literal > 0 else ~v
        root &= term
    if dynamic: manager.reorder()
    manager.configure(reordering=False)
    hidden = set(basis) - set(projected)
    def count(fixed):
        restricted = manager.let({n:bool(v) for n,v in fixed.items()}, root)
        if hidden: restricted = manager.exist(hidden, restricted)
        answer = exact_cudd_count(manager, restricted)
        exponent = len(hidden) + len(set(fixed) & set(projected))
        assert answer % (1 << exponent) == 0
        return answer >> exponent
    return count, dict(bdd_nodes=len(manager))


def runner(case, mode, method):
    basis = tuple(f'x{i}' for i in range(case['n']))
    projected = tuple(basis[i] for i in case['projected']) if mode == 'projected' else basis
    if method.startswith('cudd'): return native_runner(case, projected, method == 'cudd_dynamic')
    plan = ProjectedCNFCountPlan(case['clauses'], basis, projected,
                                order='natural' if method == 'bucket_natural' else 'min_fill', **LIMITS)
    if method == 'array_min_fill': plan = NumpyBucketCNFCountPlan(plan, max_array_cells=262144)
    return plan.count, plan.stats


def analytic(case, mode, fixed):
    """Independent weighted path recurrence for the prespecified synthetic CNFs."""
    m = len(case['projected'])
    if case['family'] == 'hidden_star':
        # h=1 allows all p; h=0 forces all p=1. The first set contains the second.
        p = {int(n[1:]):v for n,v in fixed.items() if int(n[1:]) < m}
        h = fixed.get(f'x{m}')
        free = m-len(p)
        one = int(not any(v == 0 for v in p.values()))
        all_p = 1 << free
        if h == 0: return one
        if h == 1 or mode == 'projected': return all_p
        return all_p+one
    previous = (1, 0)
    for i in range(m):
        weights = []
        for p in (0, 1):
            if f'x{2*i}' in fixed and fixed[f'x{2*i}'] != p: weights.append(0); continue
            hs = [fixed[f'x{2*i+1}']] if f'x{2*i+1}' in fixed else (0, 1)
            multiplicity = sum(bool(p or h) for h in hs)
            weights.append(int(bool(multiplicity)) if mode == 'projected' else multiplicity)
        a, b = previous
        previous = ((a+b)*weights[0], (a if case['family'] == 'adjacent_exclusion' else a+b)*weights[1])
    return sum(previous)


def case_worker(case, mode, output):
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    count, _ = runner(case, mode, 'cudd_dynamic')
    expected = [count(c) for c in case['contexts']]
    del count
    second, _ = runner(case, mode, 'cudd_natural')
    assert expected == [second(c) for c in case['contexts']]
    del second
    if 'family' in case: assert expected == [analytic(case, mode, c) for c in case['contexts']]
    write(output/'ORACLE.json', expected)
    schedule = [r for r in json.loads((AUDIT/'COUNT-SCHEDULE.json').read_text()) if r['case'] == case['id'] and r['mode'] == mode]
    with (output/'RAW.jsonl').open('x') as stream:
        for cell in schedule:
            gc.collect()
            start = time.perf_counter_ns()
            try:
                count, stats = runner(case, mode, cell['method'])
            except CountPlanLimit as exc:
                row = dict(cell, status='refused', reason=str(exc), admission_ns=time.perf_counter_ns()-start)
            else:
                setup_ns = time.perf_counter_ns()-start
                start = time.perf_counter_ns()
                values = [count(c) for c in case['contexts']]
                query_ns = time.perf_counter_ns()-start
                start = time.perf_counter_ns()
                warm = [count(c) for c in case['contexts']]
                warm_ns = time.perf_counter_ns()-start
                assert values == warm == expected, cell
                start = time.perf_counter_ns(); del count
                cleanup_ns = time.perf_counter_ns()-start
                row = dict(cell, status='complete', exact=True, values=values, setup_ns=setup_ns,
                           query_ns=query_ns, warm_ns=warm_ns, cleanup_ns=cleanup_ns,
                           total_ns=setup_ns+query_ns+cleanup_ns, stats=stats)
            stream.write(json.dumps(row)+'\n'); stream.flush()
    write(output/'COMPLETE.json', dict(cells=len(schedule), exact=True,
          process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))


def run(cohort, output):
    output.mkdir(parents=True, exist_ok=False)
    outcomes = []
    for case in json.loads((AUDIT/'COUNT-FIXTURES.json').read_text()):
        if (case['cohort'] == 'additional_public') != (cohort == 'public'): continue
        for mode in ('full', 'projected'):
            target = output/(case['id']+'-'+mode); target.mkdir()
            start = time.monotonic()
            try:
                with (target/'WORKER.log').open('xb') as stream:
                    child = subprocess.run([sys.executable, '-B', '-m', 'scripts.cm_next_count_campaign', 'case',
                            '--case', case['id'], '--mode', mode, '--output', str(target)],
                            stdout=stream, stderr=subprocess.STDOUT, timeout=120)
                status = 'complete' if child.returncode == 0 else 'failed'
                outcome = dict(case=case['id'], mode=mode, status=status, exit_code=child.returncode)
            except subprocess.TimeoutExpired:
                outcome = dict(case=case['id'], mode=mode, status='timeout', limit_s=120)
            outcome['elapsed_s'] = time.monotonic()-start
            outcomes.append(outcome); write(target/'WORKER.json', outcome)
            print(json.dumps(outcome), flush=True)
    write(output/'OUTCOMES.json', outcomes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=('freeze','run','case'))
    parser.add_argument('--cohort', choices=('public','synthetic')); parser.add_argument('--case')
    parser.add_argument('--mode', choices=('full','projected')); parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'freeze': freeze()
    elif args.action == 'run': run(args.cohort, args.output)
    else:
        case = next(c for c in json.loads((AUDIT/'COUNT-FIXTURES.json').read_text()) if c['id'] == args.case)
        case_worker(case, args.mode, args.output)
