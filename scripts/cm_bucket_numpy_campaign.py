"""Frozen object-array extension of the full-CNF bucket campaign."""
import argparse
import gc
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

import bitset_backend as bs
from cm_exprlib import And, Or, Not, Var
from cm_ir import compile_expr_to_cm_ir
from cmbench.backends.bucket_counts import BucketCNFCountPlan, CountPlanLimit, parse_dimacs
from cmbench.backends.bucket_numpy import NumpyBucketCNFCountPlan
from cmbench.backends.packed_mask_cache import PackedMaskCache
from cmbench.backends.packed_queries import _execute
from cmbench.backends.factorized_counts import FactorizedCountPlan
from cmbench.comparative.exact_cudd_count import exact_cudd_count
from scripts import cm_scalar_research_campaign as common

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT/'docs/audits/2026-09-11-cm-bucket-counts'
SEED = 2026091162
LIMITS = dict(max_width=14, max_cells=1 << 18, max_work=1 << 18, max_order_checks=2_000_000)


def dimacs(n, clauses):
    return f'p cnf {n} {len(clauses)}\n' + ''.join(' '.join(map(str, c))+' 0\n' for c in clauses)


def methods(case):
    return ('bucket_min_fill', 'bucket_cm', 'numpy_min_fill', 'numpy_cm', 'cudd_natural', 'cudd_dynamic')


def freeze():
    # Original cases are reused diagnostics. New fixtures are fully specified in
    # NUMPY-PROTOCOL.md before this file generates the schedule or any timings.
    cases = json.loads((AUDIT/'FIXTURES.json').read_text())
    for n in (28, 48, 96):
        for distance in (4, 8):
            rng = random.Random(SEED+n*100+distance)
            signs = [rng.choice((-1, 1)) for _ in range(n)]
            clauses = [(-signs[i]*(i+1), -signs[j]*(j+1)) for i in range(n)
                       for j in range(i+1, min(n, i+distance+1))]
            cases.append(dict(id=f'fresh-exclusion-d{distance}-n{n}', task='cnf',
                              cohort='fresh structured', family='exclusion', distance=distance,
                              n=n, text=dimacs(n, clauses)))
    schedule = [dict(case=c['id'], q=q, repeat=r, method=m) for c in cases for q in (1, 8)
                for r in range(9) for m in (methods(c) if r % 2 == 0 else methods(c)[::-1])]
    for name, data in (('NUMPY-FIXTURES.json', cases), ('NUMPY-SCHEDULE.json', schedule)):
        path = AUDIT/name
        with path.open('x', encoding='utf-8') as stream: json.dump(data, stream, indent=2)
    print(json.dumps(dict(cases=len(cases), cells=len(schedule))))


def queries(case, q):
    if q == 1: return [{}]
    rng = random.Random(SEED+case['n'])
    return [{f'x{i}': rng.randrange(2) for i in rng.sample(range(case['n']), min(3, case['n']))} for _ in range(q)]


def expression(n, clauses):
    variable = Var(0)
    if not clauses: return Or(variable, Not(variable))
    return common.tree([common.tree([Var(abs(l)-1) if l > 0 else Not(Var(abs(l)-1)) for l in c], Or)
                        if c else And(variable, Not(variable)) for c in clauses], And)


def native_runner(clauses, basis, dynamic):
    from dd.cudd import BDD
    manager = BDD(memory_estimate=256 << 20)
    manager.configure(reordering=dynamic, max_memory=256 << 20)
    manager.declare(*basis)
    variables = [manager.var(n) for n in basis]
    root = manager.true
    for clause in clauses:
        term = manager.false
        for literal in clause:
            v = variables[abs(literal)-1]
            term |= v if literal > 0 else ~v
        root &= term
    if dynamic: manager.reorder()
    manager.configure(reordering=False)
    def count(fixed):
        restricted = manager.let({n: bool(v) for n, v in fixed.items()}, root)
        result = exact_cudd_count(manager, restricted)
        assert result % (1 << len(fixed)) == 0
        return result >> len(fixed)
    return count


def make_runner(case, method, cache):
    n, clauses = parse_dimacs(case['text'])
    basis = tuple(f'x{i}' for i in range(n))
    if method.startswith('cudd'): return native_runner(clauses, basis, method == 'cudd_dynamic'), {}
    if method in ('bucket_natural', 'bucket_min_fill'):
        plan = BucketCNFCountPlan(clauses, basis, order=method[7:], **LIMITS)
        return plan.count, plan.stats
    if method == 'numpy_min_fill':
        plan = NumpyBucketCNFCountPlan.from_cnf(clauses, basis, max_array_cells=1 << 18, **LIMITS)
        return plan.count, plan.stats
    expr = expression(n, clauses)
    if method == 'numpy_cm':
        plan = NumpyBucketCNFCountPlan.from_cm_node(compile_expr_to_cm_ir(expr), basis, max_array_cells=1 << 18, **LIMITS)
        return plan.count, plan.stats
    if method == 'bucket_cm':
        plan = BucketCNFCountPlan.from_cm_node(compile_expr_to_cm_ir(expr), basis, **LIMITS)
        return plan.count, plan.stats
    if method == 'factorized': return FactorizedCountPlan.from_expr(expr, basis, cache=cache).count, {}
    program = bs.compile_expr_cse(expr, flatten=True)
    return lambda fixed: _execute(program, tuple(n for n in basis if n not in fixed), fixed, cache).bit_count(), {}


def session(case, method, q, warm=True):
    started = time.perf_counter_ns()
    cache = PackedMaskCache(max_bytes=96 << 20, max_width=24)
    try: runner, stats = make_runner(case, method, cache)
    except CountPlanLimit as exc:
        return dict(status='refused', reason=str(exc), admission_ns=time.perf_counter_ns()-started)
    contexts = queries(case, q)
    setup = time.perf_counter_ns()-started
    start = time.perf_counter_ns()
    result = json.dumps([runner(c) for c in contexts], separators=(',', ':'))
    query = time.perf_counter_ns()-start
    warm_ns = None
    if warm:
        start = time.perf_counter_ns()
        again = json.dumps([runner(c) for c in contexts], separators=(',', ':'))
        warm_ns = time.perf_counter_ns()-start
        assert result == again
    start = time.perf_counter_ns(); del runner; cache.clear()
    cleanup = time.perf_counter_ns()-start
    return dict(status='complete', result=result, total_ns=setup+query+cleanup, setup_ns=setup,
                query_ns=query, cleanup_ns=cleanup, warm_ns=warm_ns, plan_stats=stats)


def case_worker(case, output):
    # A process hard limit complements admission limits and CUDD's own estimate.
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (3 << 30, 3 << 30))
    n, clauses = parse_dimacs(case['text'])
    runner = native_runner(clauses, tuple(f'x{i}' for i in range(n)), True)
    expected = {q: json.dumps([runner(c) for c in queries(case, q)], separators=(',', ':')) for q in (1, 8)}
    del runner
    if case.get('family') == 'exclusion':
        counts = [1]
        for width in range(1, n+1): counts.append(counts[-1] + counts[max(0, width-case['distance']-1)])
        assert json.loads(expected[1]) == [counts[-1]]
    if case.get('family') == 'cycle':
        for q in (1, 8):
            expected_values = [2 if not c else int(len(set(c.values())) == 1) for c in queries(case, q)]
            assert json.loads(expected[q]) == expected_values
    if case.get('family') == 'dense':
        for q in (1, 8):
            expected_values = []
            for c in queries(case, q):
                ones = sum(c.values())
                expected_values.append(0 if ones > 1 else 1 if ones == 1 else n-len(c)+1)
            assert json.loads(expected[q]) == expected_values
    common.write(output/'ORACLE.json', expected)
    schedule = [r for r in json.loads((AUDIT/'NUMPY-SCHEDULE.json').read_text()) if r['case'] == case['id']]
    with (output/'RAW.jsonl').open('x') as stream:
        for cell in schedule:
            gc.collect()
            row = dict(cell, **session(case, cell['method'], cell['q']))
            if row['status'] == 'complete':
                row['exact'] = row['result'] == expected[cell['q']]
                assert row['exact'], cell
            stream.write(json.dumps(row)+'\n'); stream.flush()
    common.write(output/'COMPLETE.json', dict(cells=len(schedule), status='complete'))


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    outcomes = []
    for case in json.loads((AUDIT/'NUMPY-FIXTURES.json').read_text()):
        target = output/case['id']; target.mkdir()
        start = time.monotonic()
        try:
            with (target/'WORKER.log').open('xb') as log:
                child = subprocess.run([sys.executable, '-B', '-m', 'scripts.cm_bucket_numpy_campaign', 'case',
                                        '--case', case['id'], '--output', str(target)], stdout=log, stderr=subprocess.STDOUT, timeout=180)
            outcome = dict(case=case['id'], status='complete' if child.returncode == 0 else 'failed', exit_code=child.returncode)
        except subprocess.TimeoutExpired:
            outcome = dict(case=case['id'], status='timeout', limit_s=180)
        outcome['elapsed_s'] = time.monotonic()-start; outcomes.append(outcome)
        common.write(target/'WORKER.json', outcome)
        print(json.dumps(outcome), flush=True)
        if outcome['status'] == 'failed': raise RuntimeError('case worker failed: '+case['id'])
    common.write(output/'OUTCOMES.json', outcomes)


def memory(output):
    cases = json.loads((AUDIT/'NUMPY-FIXTURES.json').read_text())
    selected = [c for c in cases if c['id'] in ('confirmation-band-n24', 'confirmation-band-n160', 'model-09', 'fresh-exclusion-d4-n96', 'fresh-exclusion-d8-n96')]
    rows = []
    for c in selected:
        for r in range(3):
            for method in methods(c) if r % 2 == 0 else methods(c)[::-1]:
                start = time.perf_counter_ns()
                child = subprocess.run([sys.executable, '-B', '-m', 'scripts.cm_bucket_numpy_campaign', 'memory-worker',
                                        '--case', c['id'], '--method', method], capture_output=True, text=True, check=True, timeout=90)
                row = dict(case=c['id'], repeat=r, method=method, lifecycle_ns=time.perf_counter_ns()-start, **json.loads(child.stdout))
                if row['status'] == 'complete':
                    expected = json.loads((output/c['id']/'ORACLE.json').read_text())['1']
                    assert row['result'] == expected
                rows.append(row)
    common.write(output/'MEMORY.json', rows)


def verify(output):
    schedule = json.loads((AUDIT/'NUMPY-SCHEDULE.json').read_text())
    rows = []; summaries = []
    for outcome in json.loads((output/'OUTCOMES.json').read_text()):
        if outcome['status'] != 'complete': continue
        folder = output/outcome['case']
        group = [json.loads(line) for line in (folder/'RAW.jsonl').read_text().splitlines()]
        assert [{k: r[k] for k in ('case', 'q', 'repeat', 'method')} for r in group] == [r for r in schedule if r['case'] == outcome['case']]
        expected = json.loads((folder/'ORACLE.json').read_text())
        assert all(r['status'] == 'refused' or r['exact'] and r['result'] == expected[str(r['q'])] for r in group)
        rows += group
        for q in (1, 8):
            baseline = 'cudd_natural'
            base = {r['repeat']: r for r in group if r['q'] == q and r['method'] == baseline}
            for method in sorted(set(r['method'] for r in group)):
                selected = [r for r in group if r['q'] == q and r['method'] == method]
                if all(r['status'] == 'refused' for r in selected):
                    summaries.append(dict(case=outcome['case'], q=q, method=method, status='refused', reason=selected[0]['reason'])); continue
                assert all(r['status'] == 'complete' for r in selected)
                logs = [math.log(base[r['repeat']]['total_ns']/r['total_ns']) for r in selected]
                rng = random.Random(SEED)
                draws = sorted(math.exp(statistics.mean(rng.choices(logs, k=9))) for _ in range(1000))
                summaries.append(dict(case=outcome['case'], q=q, method=method, status='complete', baseline=baseline,
                    median_total_ns=statistics.median(r['total_ns'] for r in selected), median_warm_ns=statistics.median(r['warm_ns'] for r in selected),
                    paired_speedup=math.exp(statistics.mean(logs)), ci95=[draws[24], draws[974]], plan_stats=selected[0]['plan_stats']))
    common.write(output/'SUMMARY.json', summaries)
    common.write(output/'RESULT.json', dict(schedule_complete=len(rows)==len(schedule), missing_cells=len(schedule)-len(rows), scheduled_cells=len(schedule), accounted_cells=len(rows), complete_cells=sum(r['status']=='complete' for r in rows),
                refused_cells=sum(r['status']=='refused' for r in rows), asserted_outputs=2*sum(r['q'] for r in rows if r['status']=='complete'),
                memory_children=len(json.loads((output/'MEMORY.json').read_text())), exact=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'run', 'case', 'memory', 'memory-worker', 'verify'))
    parser.add_argument('--output', type=Path); parser.add_argument('--case'); parser.add_argument('--method')
    args = parser.parse_args()
    if args.action == 'freeze': freeze()
    elif args.action == 'run': run(args.output)
    elif args.action == 'memory': memory(args.output)
    elif args.action == 'verify': verify(args.output)
    else:
        case = next(c for c in json.loads((AUDIT/'NUMPY-FIXTURES.json').read_text()) if c['id'] == args.case)
        if args.action == 'case': case_worker(case, args.output)
        else:
            before = common.process_memory(); row = session(case, args.method, 1, warm=False)
            print(json.dumps(dict(before=before, after=common.process_memory(), **row)))


if __name__ == '__main__': main()
