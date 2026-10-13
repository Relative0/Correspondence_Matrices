"""Prospective scalar panels; exclusive evidence, explicit ingress and controls."""
from __future__ import annotations

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
from cm_exprlib import And, Or, Xor, Not, Imp, Eqv, Var
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_ir import compile_expr_to_cm_ir
from cmbench.backends.packed_mask_cache import PackedMaskCache
from cmbench.backends.packed_queries import IndependentCountPlan, _execute
from cmbench.backends.factorized_counts import FactorizedCountPlan
from cmbench.backends.affine_constraints import AffineConstraintPlan, parse_alist

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'docs/audits/2026-09-11-cm-scalar-research'
SEED, REPEATS = 2026091139, 9


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(nodes, op):
    while len(nodes) > 1:
        nodes = [op(nodes[i], nodes[i+1]) if i+1 < len(nodes) else nodes[i] for i in range(0, len(nodes), 2)]
    return nodes[0]


def fixtures():
    cases = []
    for cohort, widths, offset in [('development', (12, 16), 0), ('confirmation', (22, 24), 1000)]:
        for n in widths:
            axes = list(range(n)); random.Random(SEED+n+offset).shuffle(axes)
            groups = [axes[i:i+4] for i in range(0, n, 4)]
            blocks = [tree([Var(i) for i in g], Eqv) for g in groups]
            for family in ('or', 'xor', 'mixed', 'cycle'):
                if family == 'or': e = tree(blocks, Or)
                elif family == 'xor': e = tree(blocks, Xor)
                elif family == 'mixed':
                    mid = len(blocks)//2
                    e = Imp(tree(blocks[:mid], And), Not(tree(blocks[mid:], Or)))
                else:
                    e = tree([Or(Var(axes[i]), Not(Var(axes[(i+1) % n]))) for i in range(n)], And)
                cases.append(dict(id=f'{cohort}-{family}-n{n}', cohort=cohort, family=family, task='factor',
                                  n=n, order=axes, document_json=json.dumps(expr_to_json_dag(e), separators=(',', ':'))))
    corpus = json.loads((AUDIT/'CORPUS.json').read_text(encoding='utf-8'))
    selected = {}
    for item in corpus['files']:
        path = AUDIT/'corpus'/item['name']
        assert sha(path) == item['sha256']
        n, rows = parse_alist(path.read_text())
        assert [n, len(rows)] == item['dimensions']
        selected[n] = item
    for n, item in sorted(selected.items()):
        cases.append(dict(id=item['name'][:-6], cohort='public-corpus', task='affine', n=n,
                          alist=(AUDIT/'corpus'/item['name']).read_text(), source_sha256=item['sha256']))
    return cases


def methods(case):
    if case['task'] == 'affine': return ('affine_rows', 'affine_expr', 'affine_cm', 'flint')
    return ('cse', 'and_only', 'factor_expr', 'factor_cm', 'cudd_natural', 'cudd_grouped', 'cudd_dynamic')


def queries(case, q):
    if q == 1: return [{}]
    n = case['n']
    if case['task'] == 'factor':
        return [{f'x{(i+j*5) % n}': i >> j & 1 for j in range(3)} for i in range(q)]
    rng = random.Random(SEED+n)
    contexts = [{}, {f'x{i}': 0 for i in range(n)}, {f'x{i}': 1 for i in range(n)}]
    for fraction in (.95, .25, .5, .75):
        contexts.append({f'x{i}': rng.randrange(2) for i in rng.sample(range(n), int(n*fraction))})
    contexts.append({f'x{i}': rng.randrange(2) for i in range(8)})
    return contexts


def bdd_runner(document, basis, order, dynamic):
    from dd.cudd import BDD
    manager = BDD(); manager.configure(reordering=dynamic); manager.declare(*order)
    values = []
    for node in document['nodes']:
        op = node['op']
        if op == 'var': value = manager.var(f"x{node['i']}")
        elif op == 'not': value = ~values[node['a']]
        else:
            a, b = values[node['a']], values[node['b']]
            if op == 'and': value = a & b
            elif op == 'or': value = a | b
            elif op == 'xor': value = manager.apply('xor', a, b)
            elif op == 'eqv': value = ~manager.apply('xor', a, b)
            elif op == 'imp': value = ~a | b
            else: raise ValueError(op)
        values.append(value)
    root = values[document['root']]
    if dynamic: manager.reorder()  # Explicit sift even below automatic threshold; charged.
    return lambda fixed: int(manager.count(manager.let({n: bool(v) for n, v in fixed.items()}, root),
                                            nvars=len(basis)-len(fixed)))


def affine_expression(rows):
    clauses = []
    for row in rows:
        variables = []
        while row:
            bit = row & -row; variables.append(Var(bit.bit_length()-1)); row ^= bit
        if not variables: continue  # Corpus uses homogeneous constraints; 0=0 is a tautology.
        clauses.append(Not(tree(variables, Xor)))
    if not clauses: return Eqv(Var(0), Var(0))
    return tree(clauses, And)


def flint_runner(rows, rhs, basis):
    from flint import nmod_mat
    dense = []
    for row in rows:
        vector = [0] * len(basis)
        while row:
            bit = row & -row; vector[bit.bit_length()-1] = 1; row ^= bit
        dense.append(vector)
    positions = {name: i for i, name in enumerate(basis)}
    def count(fixed):
        assigned = {positions[name]: v for name, v in fixed.items()}
        live = [i for i in range(len(basis)) if i not in assigned]
        b = [rhs[j] ^ (sum(row[i]*v for i, v in assigned.items()) & 1) for j, row in enumerate(dense)]
        if not live: return int(not any(b))
        residual = [[row[i] for i in live] for row in dense]
        rank = nmod_mat(residual, 2).rank() if residual else 0
        if any(b) and nmod_mat([row+[v] for row, v in zip(residual, b)], 2).rank() != rank: return 0
        return 1 << (len(live)-rank)
    return count


def make_runner(case, method, cache):
    basis = tuple(f'x{i}' for i in range(case['n']))
    if case['task'] == 'affine':
        n, rows = parse_alist(case['alist'])
        if method == 'flint': return flint_runner(rows, [0]*len(rows), basis)
        if method == 'affine_rows': return AffineConstraintPlan(rows, [0]*len(rows), basis).count
        expr = affine_expression(rows)
        if method == 'affine_expr': return AffineConstraintPlan.from_expr(expr, basis).count
        return AffineConstraintPlan.from_cm_node(compile_expr_to_cm_ir(expr), basis).count
    doc = json.loads(case['document_json'])
    if method.startswith('cudd_'):
        order = tuple(f'x{i}' for i in case['order']) if method == 'cudd_grouped' else basis
        return bdd_runner(doc, basis, order, method == 'cudd_dynamic')
    expr = expr_from_json(doc)
    if method == 'and_only': return IndependentCountPlan.from_expr(expr, basis, cache=cache).count
    if method == 'factor_expr': return FactorizedCountPlan.from_expr(expr, basis, cache=cache).count
    if method == 'factor_cm': return FactorizedCountPlan.from_cm_node(compile_expr_to_cm_ir(expr), basis, cache=cache).count
    program = bs.compile_expr_cse(expr, flatten=True)
    return lambda fixed: _execute(program, tuple(n for n in basis if n not in fixed), fixed, cache).bit_count()


def session(case, method, q, warm=True):
    start = time.perf_counter_ns()
    cache = PackedMaskCache(max_bytes=96 << 20, max_width=24)
    runner = make_runner(case, method, cache)
    contexts = queries(case, q)
    setup = time.perf_counter_ns()-start
    start = time.perf_counter_ns()
    result = json.dumps([runner(c) for c in contexts], separators=(',', ':'))
    query = time.perf_counter_ns()-start
    warm_ns = None
    if warm:
        start = time.perf_counter_ns()
        again = json.dumps([runner(c) for c in contexts], separators=(',', ':'))
        warm_ns = time.perf_counter_ns()-start
        assert again == result
    start = time.perf_counter_ns()
    del runner
    cache.clear()
    cleanup = time.perf_counter_ns()-start
    return dict(total_ns=setup+query+cleanup, setup_ns=setup, query_ns=query, cleanup_ns=cleanup,
                warm_ns=warm_ns, result=result)


def freeze():
    cases = fixtures()
    write(AUDIT/'FIXTURES.json', cases)
    schedule = [dict(case=c['id'], q=q, repeat=r, method=m) for c in cases for q in (1, 8)
                for r in range(REPEATS) for m in (methods(c) if r % 2 == 0 else methods(c)[::-1])]
    write(AUDIT/'SCHEDULE.json', schedule)
    print(json.dumps(dict(cases=len(cases), cells=len(schedule))))


def corpus_checks():
    records = []
    for item in json.loads((AUDIT/'CORPUS.json').read_text())['files']:
        n, rows = parse_alist((AUDIT/'corpus'/item['name']).read_text())
        basis = tuple(f'x{i}' for i in range(n))
        p = AffineConstraintPlan(rows, [0]*len(rows), basis)
        native = flint_runner(rows, [0]*len(rows), basis)
        contexts = queries(dict(n=n, task='affine'), 8)
        result = [p.count(c) for c in contexts]
        assert result == [native(c) for c in contexts]
        records.append(dict(name=item['name'], n=n, rows=len(rows), rank=n-(result[0].bit_length()-1),
                            outputs=[str(x) for x in result], exact=True))
    return records


def summarize(rows):
    result = []
    rng = random.Random(SEED)
    for key in sorted(set((r['case'], r['q']) for r in rows)):
        group = [r for r in rows if (r['case'], r['q']) == key]
        baseline = 'flint' if group[0]['case'].startswith('n_') else 'cse'
        base = {r['repeat']: r for r in group if r['method'] == baseline}
        for method in sorted(set(r['method'] for r in group)):
            subset = [r for r in group if r['method'] == method]
            logs = [math.log(base[r['repeat']]['total_ns']/r['total_ns']) for r in subset]
            draws = sorted(math.exp(statistics.mean(rng.choices(logs, k=len(logs)))) for _ in range(1000))
            result.append(dict(case=key[0], q=key[1], method=method, baseline=baseline,
                               median_total_ns=statistics.median(r['total_ns'] for r in subset),
                               median_warm_ns=statistics.median(r['warm_ns'] for r in subset),
                               paired_speedup=math.exp(statistics.mean(logs)), ci95=[draws[24], draws[974]]))
    return result


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    cases = json.loads((AUDIT/'FIXTURES.json').read_text())
    schedule = json.loads((AUDIT/'SCHEDULE.json').read_text())
    write(output/'CORPUS-CHECKS.json', corpus_checks())
    indexed = {c['id']: c for c in cases}
    oracles = {}
    for c in cases:
        for q in (1, 8):
            method = 'flint' if c['task'] == 'affine' else 'cudd_grouped'
            oracles[(c['id'], q)] = session(c, method, q)['result']
    write(output/'ORACLES.json', [dict(case=k[0], q=k[1], result=v) for k, v in oracles.items()])
    rows = []
    with (output/'RAW.jsonl').open('x') as stream:
        for i, cell in enumerate(schedule):
            gc.collect()
            row = dict(cell, **session(indexed[cell['case']], cell['method'], cell['q']))
            row['exact'] = row['result'] == oracles[(cell['case'], cell['q'])]
            stream.write(json.dumps(row)+'\n'); stream.flush()
            assert row['exact'], cell
            rows.append(row)
            if i % 100 == 0: print(json.dumps(dict(completed=i+1, total=len(schedule))), flush=True)
    write(output/'SUMMARY.json', summarize(rows))
    write(output/'RESULT.json', dict(status='complete', cells=len(rows),
                                    asserted_query_outputs=2*sum(r['q'] for r in rows), exact=True))


def process_memory():
    return {k: int(v.split()[0]) for line in Path('/proc/self/status').read_text().splitlines()
            for k, _, v in [line.partition(':')] if k in ('VmHWM', 'VmRSS', 'VmPeak')}


def memory(output):
    cases = json.loads((AUDIT/'FIXTURES.json').read_text())
    selected = [c for c in cases if c['n'] == 24 or c['n'] == 1800]
    records = []
    for c in selected:
        for r in range(3):
            for m in methods(c) if r % 2 == 0 else methods(c)[::-1]:
                start = time.perf_counter_ns()
                child = subprocess.run([sys.executable, '-B', '-m', 'scripts.cm_scalar_research_campaign',
                                        'worker', '--case', c['id'], '--method', m], capture_output=True,
                                       text=True, check=True, timeout=120)
                row = dict(case=c['id'], method=m, repeat=r, lifecycle_ns=time.perf_counter_ns()-start,
                           **json.loads(child.stdout))
                expected = next(x['result'] for x in json.loads((output/'ORACLES.json').read_text())
                                if x['case'] == c['id'] and x['q'] == 1)
                assert row['result'] == expected
                records.append(row)
    write(output/'MEMORY.json', records)


def verify(output):
    rows = [json.loads(line) for line in (output/'RAW.jsonl').read_text().splitlines()]
    schedule = json.loads((AUDIT/'SCHEDULE.json').read_text())
    assert [{k: r[k] for k in ('case', 'q', 'repeat', 'method')} for r in rows] == schedule
    oracles = {(r['case'], r['q']): r['result'] for r in json.loads((output/'ORACLES.json').read_text())}
    assert all(r['exact'] and r['result'] == oracles[(r['case'], r['q'])] for r in rows)
    assert all(r['total_ns'] == r['setup_ns']+r['query_ns']+r['cleanup_ns'] for r in rows)
    assert summarize(rows) == json.loads((output/'SUMMARY.json').read_text())
    memory_rows = json.loads((output/'MEMORY.json').read_text())
    assert len(memory_rows) == 96
    assert all(r['result'] == oracles[(r['case'], 1)] and r['after']['VmHWM'] >= r['after']['VmRSS'] > 0 for r in memory_rows)
    write(output/'VERIFIED.json', dict(cells=len(rows), memory_children=len(memory_rows), exact=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'run', 'memory', 'worker', 'verify'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--case'); parser.add_argument('--method')
    args = parser.parse_args()
    if args.action == 'freeze': freeze()
    elif args.action == 'run': run(args.output)
    elif args.action == 'memory': memory(args.output)
    elif args.action == 'verify': verify(args.output)
    else:
        case = next(c for c in json.loads((AUDIT/'FIXTURES.json').read_text()) if c['id'] == args.case)
        before = process_memory()
        row = session(case, args.method, 1, warm=False)
        print(json.dumps(dict(before=before, after=process_memory(), **row)))


if __name__ == '__main__': main()
