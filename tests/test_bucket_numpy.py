from concurrent.futures import ThreadPoolExecutor
from itertools import product
import random
from unittest.mock import patch

import pytest

from cm_exprlib import And, Not, Or, Var
from cm_ir import compile_expr_to_cm_ir
from cmbench.backends.bucket_counts import BucketCNFCountPlan, CountPlanLimit
from cmbench.backends.bucket_numpy import NumpyBucketCNFCountPlan


def brute(clauses, basis, fixed):
    return sum(all(any(bool(row[abs(l)-1]) == (l > 0) for l in c) for c in clauses)
               for row in product((0, 1), repeat=len(basis))
               if all(row[basis.index(n)] == v for n, v in fixed.items()))


@pytest.mark.parametrize('order', ['natural', 'min_fill'])
def test_random_cnf_all_partial_assignments(order):
    rng = random.Random(2026091162)
    basis = ('z', 'a', 'q', 'b')
    for _ in range(35):
        clauses = [tuple(rng.choice((-1, 1))*v for v in rng.sample(range(1, 5), rng.randrange(1, 5)))
                   for _ in range(rng.randrange(1, 9))]
        plan = NumpyBucketCNFCountPlan.from_cnf(clauses, basis, order=order)
        for choices in product((None, 0, 1), repeat=4):
            fixed = {n: v for n, v in zip(basis, choices) if v is not None}
            assert plan.count(fixed) == brute(clauses, basis, fixed)


def test_intermediate_values_beyond_machine_integer_precision():
    # One connected narrow factor chain has Fib(102) models, not just a free-axis shift.
    n = 100
    plan = NumpyBucketCNFCountPlan.from_cnf([(-i, -i-1) for i in range(1, n)], tuple(f'x{i}' for i in range(n)))
    a, b = 1, 2
    for _ in range(1, n): a, b = b, a+b
    assert b > 2**64 and plan.count() == b
    free = NumpyBucketCNFCountPlan.from_cnf([], tuple(f'x{i}' for i in range(200)))
    assert free.count({'x99': 0}) == 2**199


@pytest.mark.parametrize('clauses', [[], [()], [(1,), (-1,)], [(1,), (2, -1)], [(1, -1)]])
def test_constant_unit_and_unused_contexts(clauses):
    basis = ('b', 'a', 'c')
    plan = NumpyBucketCNFCountPlan.from_cnf(clauses, basis)
    for choices in product((None, 0, 1), repeat=3):
        fixed = {n: v for n, v in zip(basis, choices) if v is not None}
        assert plan.count(fixed) == brute(clauses, basis, fixed)
        assert plan.exists(fixed) == bool(brute(clauses, basis, fixed))


def test_expression_and_cm_ingress():
    expr = And(Or(Var(0), Var(1)), Or(Not(Var(1)), Var(2)))
    basis = ('x2', 'x0', 'x1', 'unused')
    for plan in (NumpyBucketCNFCountPlan.from_expr(expr, basis),
                 NumpyBucketCNFCountPlan.from_cm_node(compile_expr_to_cm_ir(expr), basis)):
        assert plan.count() == 8
        assert plan.count({'x1': 0}) == 4


def test_parallel_queries_keep_inputs_readonly_and_context_unchanged():
    clauses = [(1, 2, -3), (-1, 3), (2, 4), (-2, -4)]
    basis = ('q', 'c', 'a', 'z')
    plan = NumpyBucketCNFCountPlan.from_cnf(clauses, basis)
    contexts = [{'c': i % 2, 'z': (i//2) % 2} for i in range(32)]
    before = [dict(c) for c in contexts]
    inputs = [t.tolist() for t in plan._tables]
    with ThreadPoolExecutor(max_workers=4) as pool: results = list(pool.map(plan.count, contexts))
    assert results == [brute(clauses, basis, c) for c in contexts]
    assert contexts == before and [t.tolist() for t in plan._tables] == inputs
    assert all(not t.flags.writeable for t in plan._tables)


def test_array_admission_precedes_array_allocation():
    base = BucketCNFCountPlan([(1, 2, 3), (-1, -2)], ('a', 'b', 'c'))
    bound = NumpyBucketCNFCountPlan(base).stats['array_cells_bound']
    with patch('cmbench.backends.bucket_numpy.np.array', side_effect=AssertionError('allocated')):
        with pytest.raises(CountPlanLimit, match='array table'): NumpyBucketCNFCountPlan(base, max_array_cells=bound-1)
    assert NumpyBucketCNFCountPlan(base, max_array_cells=bound).count() == 5


@pytest.mark.parametrize('fixed', [{'missing': 0}, {'a': 2}, {'a': 0.0}, {'a': '0'}])
def test_invalid_fixed_context_even_on_constant(fixed):
    plan = NumpyBucketCNFCountPlan.from_cnf([()], ('a',))
    with pytest.raises(ValueError): plan.count(fixed)


@pytest.mark.parametrize('limit', [-1, True, 1.5])
def test_invalid_array_budget(limit):
    with pytest.raises(ValueError): NumpyBucketCNFCountPlan.from_cnf([], (), max_array_cells=limit)
