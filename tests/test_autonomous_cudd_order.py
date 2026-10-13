"""Linux-native control: force a real order change without an exponential table."""
import pytest
from cmbench.comparative.exact_cudd_count import exact_cudd_count
from itertools import product
from test_autonomous_seeded_contexts import fixture, scalar, bdd_expr

cudd = pytest.importorskip('dd.cudd')

def test_forced_reverse_order_complement_and_restriction_above_float_precision():
    manager = cudd.BDD()
    manager.configure(reordering=False)
    names = tuple(f'x{i}' for i in range(100))
    manager.declare(*names)
    root = manager.apply('xor', manager.var('x3'), manager.var('x97'))
    assert exact_cudd_count(manager, root) == 1 << 99
    reverse = {name:99-index for index, name in enumerate(names)}
    manager.reorder(reverse)
    assert all(manager.level_of_var(name) == level for name, level in reverse.items())
    assert exact_cudd_count(manager, root) == 1 << 99
    assert exact_cudd_count(manager, ~root) == 1 << 99
    restricted = manager.let({'x3':True, 'x97':False}, root)
    assert exact_cudd_count(manager, restricted) >> 2 == 1 << 98
    unsat = manager.let({'x3':True, 'x97':True}, root)
    assert exact_cudd_count(manager, unsat) == 0

@pytest.mark.parametrize('seed', range(200))
def test_native_count_contexts_before_and_after_forced_reorder(seed):
    expr, n, rng = fixture(seed)
    names = tuple(f'x{i}' for i in range(n))
    axis = names[seed % n]
    contexts = ({}, {axis:False}, {axis:True},
                {name:bool(rng.randrange(2)) for name in names}, {}, {axis:False})
    manager = cudd.BDD()
    manager.configure(reordering=False)
    manager.declare(*names)
    root = bdd_expr(manager, expr)
    for reordered in (False, True):
        if reordered:
            order = {name:n-1-index for index, name in enumerate(names)}
            manager.reorder(order)
            assert all(manager.level_of_var(name) == level for name, level in order.items())
        for fixed in contexts:
            live = tuple(name for name in names if name not in fixed)
            expected = sum(scalar(expr, dict(zip(live, values)) | fixed)
                           for values in product((False, True), repeat=len(live)))
            restricted = manager.let(fixed, root)
            assert exact_cudd_count(manager, restricted) >> len(fixed) == expected
            assert exact_cudd_count(manager, ~restricted) >> len(fixed) == (1 << len(live))-expected
