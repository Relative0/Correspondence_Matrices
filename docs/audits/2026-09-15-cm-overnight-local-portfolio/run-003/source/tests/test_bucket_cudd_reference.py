import pytest

from cmbench.comparative.exact_cudd_count import exact_cudd_count

cudd = pytest.importorskip('dd.cudd')


def test_exact_counts_above_float_precision_and_complemented_edges():
    manager = cudd.BDD(); manager.configure(reordering=False)
    manager.declare(*(f'x{i}' for i in range(100)))
    root = manager.false
    for i in range(100): root |= manager.var(f'x{i}')
    assert exact_cudd_count(manager, root) == (1 << 100)-1
    assert exact_cudd_count(manager, ~root) == 1
    assert exact_cudd_count(manager, manager.true) == 1 << 100
    assert exact_cudd_count(manager, manager.false) == 0
    root = manager.apply('xor', manager.var('x3'), manager.var('x97'))
    assert exact_cudd_count(manager, root) == 1 << 99
    manager.reorder()
    assert exact_cudd_count(manager, root) == 1 << 99
    restricted = manager.let({'x3': True}, root)
    assert exact_cudd_count(manager, restricted) >> 1 == 1 << 98


def test_empty_manager_constants():
    manager = cudd.BDD()
    assert exact_cudd_count(manager, manager.true) == 1
    assert exact_cudd_count(manager, manager.false) == 0
