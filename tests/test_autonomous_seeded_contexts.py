"""Seeded repeated-context correctness with cache bypass, eviction and clear."""
from itertools import product
import random
import pytest
from dd import autoref
from cm_exprlib import Var, Not, And, Or, Xor, Imp, Eqv
from cm_ir import compile_expr_to_cm_ir
from cmbench.backends.factorized_counts import FactorizedCountPlan
from cmbench.backends.packed_mask_cache import PackedMaskCache

OPS = (And, Or, Xor, Imp, Eqv)

def fixture(seed):
    rng = random.Random(202610120000 + seed)
    n = 1 + seed % 6
    def build(depth):
        if depth == 1 or rng.random() < .3: return Var(rng.randrange(n))
        if rng.random() < .2: return Not(build(depth-1))
        return rng.choice(OPS)(build(depth-1), build(depth-1))
    # Leave one level for the complement metamorphism under the depth-6 cap.
    return build(5), n, rng

def scalar(expr, values):
    if isinstance(expr, Var): return bool(values[f'x{expr.i}'])
    if isinstance(expr, Not): return not scalar(expr.a, values)
    a, b = scalar(expr.a, values), scalar(expr.b, values)
    if isinstance(expr, And): return a and b
    if isinstance(expr, Or): return a or b
    if isinstance(expr, Xor): return a != b
    if isinstance(expr, Imp): return not a or b
    if isinstance(expr, Eqv): return a == b
    raise TypeError(type(expr))

def bdd_expr(manager, expr):
    if isinstance(expr, Var): return manager.var(f'x{expr.i}')
    if isinstance(expr, Not): return ~bdd_expr(manager, expr.a)
    op = {And:'and', Or:'or', Xor:'xor', Imp:'implies', Eqv:'equiv'}[type(expr)]
    return manager.apply(op, bdd_expr(manager, expr.a), bdd_expr(manager, expr.b))

@pytest.mark.parametrize('seed', range(200))
def test_repeated_contexts_survive_cache_policy_and_complement(seed):
    expr, n, rng = fixture(seed)
    basis = tuple(f'x{i}' for i in range(n))
    reverse = basis[::-1]
    axis = basis[seed % n]
    contexts = ({}, {axis:False}, {axis:True},
                {name:bool(rng.randrange(2)) for name in basis}, {}, {axis:False})
    node = compile_expr_to_cm_ir(expr, reuse_cache=False)
    manager = autoref.BDD()
    manager.declare(*basis)
    root = bdd_expr(manager, expr)
    for budget in (0, 512):
        cache = PackedMaskCache(max_bytes=budget, max_width=6)
        retained = cache.columns(6)
        cache.columns(5)
        assert cache.stats()['bypasses' if budget == 0 else 'evictions'] > 0
        plans = (FactorizedCountPlan.from_expr(expr, basis, cache=cache),
                 FactorizedCountPlan.from_cm_node(node, basis, cache=cache),
                 FactorizedCountPlan.from_expr(expr, reverse, cache=cache))
        complement = FactorizedCountPlan.from_expr(Not(expr), basis, cache=cache)
        for index, fixed in enumerate(contexts):
            if index == 4: cache.clear()
            live = tuple(name for name in basis if name not in fixed)
            expected = sum(scalar(expr, dict(zip(live, values)) | fixed)
                           for values in product((False, True), repeat=len(live)))
            assert [plan.count(fixed) for plan in plans] == [expected]*3
            restricted = manager.let(fixed, root)
            assert int(manager.count(restricted, nvars=n)) >> len(fixed) == expected
            assert complement.count(fixed) == (1 << len(live)) - expected
            assert cache.stats()['entry_bytes'] <= budget
        assert len(retained) == 6
    del restricted, root
    manager.collect_garbage()
