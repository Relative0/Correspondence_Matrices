from concurrent.futures import ThreadPoolExecutor
from itertools import product
import random

import pytest

from cmbench.backends.bucket_counts import BucketCNFCountPlan, CountPlanLimit, parse_dimacs
from cm_exprlib import And, Or, Not, Var, Xor
from cm_ir import CMIRBuilder, compile_expr_to_cm_ir


def oracle(clauses, names, fixed):
    return sum(all(any(bool(row[abs(l)-1]) == (l > 0) for l in clause) for clause in clauses)
               for row in product((0, 1), repeat=len(names))
               if all(row[i] == fixed[n] for i, n in enumerate(names) if n in fixed))


@pytest.mark.parametrize('seed', range(24))
def test_random_cnf_all_partial_assignments(seed):
    rng = random.Random(seed); names = ('d', 'a', 'unused', 'b')
    clauses = [tuple(rng.choice((-1, 1))*rng.randrange(1, 5) for _ in range(rng.randrange(1, 5)))
               for _ in range(rng.randrange(12))]
    for order in ('natural', 'min_fill'):
        plan = BucketCNFCountPlan(clauses, names, order=order)
        for values in product((None, 0, 1), repeat=4):
            fixed = {n: v for n, v in zip(names, values) if v is not None}
            expected = oracle(clauses, names, fixed)
            assert plan.count(fixed) == expected
            assert plan.exists(fixed) == bool(expected)


def test_large_counts_unused_axes_units_and_contradictions():
    names = tuple(f'x{i}' for i in range(100))
    plan = BucketCNFCountPlan([(1,), (-1, 2), (3, 4), (-4, 3)], names)
    assert plan.count() == 1 << 97
    assert plan.count({'x99': 0}) == 1 << 96
    assert plan.count({'x0': 0}) == 0
    for clauses in ([()], [(1,), (-1,)], [(1,), (-1, 2), (-2,)]):
        assert BucketCNFCountPlan(clauses, names).count() == 0
    assert BucketCNFCountPlan([], names).count() == 1 << 100
    assert BucketCNFCountPlan([(1, -1, 2)], names).count() == 1 << 100


def test_expr_cm_ingress_and_constants():
    e = And(Or(Var(0), Not(Var(1))), And(Var(2), Or(Var(1), Var(3))))
    names = ('x3', 'x1', 'x0', 'x2', 'unused')
    clauses = [(3, -2), (4,), (2, 1)]
    for plan in (BucketCNFCountPlan.from_expr(e, names), BucketCNFCountPlan.from_cm_node(compile_expr_to_cm_ir(e), names)):
        for values in product((None, 0, 1), repeat=4):
            fixed = {n: v for n, v in zip(names, values) if v is not None}
            assert plan.count(fixed) == oracle(clauses, names, fixed)
    for bit in (0, 1):
        assert BucketCNFCountPlan.from_cm_node(CMIRBuilder().const(bit), names).count() == bit*32
    with pytest.raises(ValueError, match='syntactic CNF'):
        BucketCNFCountPlan.from_expr(Xor(Var(0), Var(1)), names)


def test_cycle_known_count_and_thread_private_queries():
    # Implication around a cycle forces all values equal.
    n = 100
    clauses = [(-(i+1), (i+1) % n+1) for i in range(n)]
    names = tuple(f'x{i}' for i in range(n))
    plan = BucketCNFCountPlan(clauses, names)
    assert plan.stats['width'] == 3
    assert plan.count() == 2
    contexts = [{'x0': i % 2, 'x99': i // 2 % 2} for i in range(40)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(plan.count, contexts)) == [int(c['x0'] == c['x99']) for c in contexts]


@pytest.mark.parametrize('limits', [{'max_width': 2}, {'max_cells': 1}, {'max_work': 1},
                                   {'max_order_checks': 0}, {'max_vars': 3}, {'max_clauses': 2}])
def test_admission_refuses_before_tables(limits):
    clauses = [(1, 2), (2, 3), (3, 4), (4, 1)]
    with pytest.raises(CountPlanLimit): BucketCNFCountPlan(clauses, ('a', 'b', 'c', 'd'), **limits)


def test_bad_inputs_contexts_and_empty_basis():
    for clauses in ([(0,)], [(2,)], [(1.0,)], [(True,)]):
        with pytest.raises(ValueError): BucketCNFCountPlan(clauses, ('a',))
    for kwargs in ({'max_width': 21}, {'max_cells': -1}, {'max_work': True}, {'order': 'auto'}):
        with pytest.raises(ValueError): BucketCNFCountPlan([], (), **kwargs)
    plan = BucketCNFCountPlan([], ('a',))
    for fixed in ({'b': 0}, {'a': 2}, {'a': 0.0}):
        with pytest.raises(ValueError): plan.count(fixed)
    assert BucketCNFCountPlan([], ()).count() == 1
    assert BucketCNFCountPlan([()], ()).count() == 0


def test_dimacs_strict_records_multiline_comments_and_guards():
    assert parse_dimacs('c source\np cnf 3 2\n1\n-2 0 3 0\n') == (3, ((1, -2), (3,)))
    for text in ('p cnf 1 1\n2 0', '1 0\np cnf 1 1', 'p cnf 1 1\n1',
                 'p cnf 1 0\n1 0', 'p cnf 1 0\np cnf 1 0', 'p cnf 1 -1'):
        with pytest.raises(ValueError): parse_dimacs(text)
    with pytest.raises(ValueError): parse_dimacs('p cnf 1 0', max_bytes=2)


def test_early_contradiction_does_not_skip_context_validation():
    p = BucketCNFCountPlan([()], ('a',))
    with pytest.raises(ValueError): p.count({'unknown': 0})
