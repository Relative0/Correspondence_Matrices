"""Independent truth and resource checks for scalar research APIs."""
from concurrent.futures import ThreadPoolExecutor
from itertools import product
import random

import pytest

from bitset_backend import FlatProgram, _FLAT_OP_NOT
from cm_exprlib import And, Or, Xor, Not, Imp, Eqv, Var
from cm_ir import CMIRBuilder, compile_expr_to_cm_ir
from cmbench.backends.factorized_counts import FactorizedCountPlan
from cmbench.backends.affine_constraints import AffineConstraintPlan, parse_alist
from cmbench.backends.packed_mask_cache import PackedMaskCache


def scalar(e, row):
    if isinstance(e, Var): return bool(row['x'+str(e.i)])
    if isinstance(e, Not): return not scalar(e.a, row)
    a, b = scalar(e.a, row), scalar(e.b, row)
    return {And: a and b, Or: a or b, Xor: a != b, Imp: not a or b, Eqv: a == b}[type(e)]


def oracle(e, names, fixed):
    live = [n for n in names if n not in fixed]
    return sum(scalar(e, dict(zip(live, row)) | fixed) for row in product((0, 1), repeat=len(live)))


def factor(e, names, width=8):
    return FactorizedCountPlan.from_expr(e, names, cache=PackedMaskCache(max_bytes=1 << 18, max_width=width))


@pytest.mark.parametrize('seed', range(24))
def test_random_shared_dags_all_operators(seed):
    rng = random.Random(seed)
    names = ('x3', 'x1', 'x0', 'x2', 'unused')
    nodes = [Var(i) for i in range(4)]
    for _ in range(14):
        a, b = rng.choices(nodes, k=2)
        nodes.append(rng.choice((And, Or, Xor, Imp, Eqv))(a, b))
        if rng.random() < .3: nodes.append(Not(nodes[-1]))
    e = nodes[-1]
    plans = [factor(e, names), FactorizedCountPlan.from_cm_node(compile_expr_to_cm_ir(e), names,
             cache=PackedMaskCache(max_bytes=0, max_width=8))]
    for vals in product((None, 0, 1), repeat=4):
        fixed = {n: v for n, v in zip(names, vals) if v is not None}
        expected = oracle(e, names, fixed)
        assert all(p.count(fixed) == expected and p.exists(fixed) == bool(expected) for p in plans)


@pytest.mark.parametrize('op', [And, Or, Xor, Imp, Eqv])
def test_large_disjoint_counts_and_overlap(op):
    e = op(Or(Var(0), Var(1)), Xor(Var(2), Var(3)))
    names = tuple('x'+str(i) for i in range(100))
    p = factor(e, names, 0)
    assert p.count() == oracle(e, names[:4], {}) << 96
    overlap = op(Eqv(Var(0), Var(1)), Eqv(Var(1), Var(2)))
    p = factor(overlap, names[:3], 2)
    before = p.cache.stats()
    with pytest.raises(ValueError, match='component live width'): p.count()
    assert p.cache.stats() == before
    assert p.count({'x1': 1}) == oracle(overlap, names[:3], {'x1': 1})


def test_duplicate_xor_group_constants_and_iterative_depth():
    a = Or(Var(0), Var(1))
    e = Xor(Xor(a, a), Var(2))
    p = factor(e, ('x0', 'x1', 'x2'))
    assert p.count() == 4
    assert p.count({'x2': 0}) == 0
    for b in (0, 1):
        p = FactorizedCountPlan.from_cm_node(CMIRBuilder().const(b), ('unused',),
                                             cache=PackedMaskCache(max_bytes=0, max_width=0))
        assert p.count() == 2*b
    program = FlatProgram(3001, 3000, ((0, 'var', 'x0'),),
                          tuple((i, _FLAT_OP_NOT, (i-1,)) for i in range(1, 3001)))
    p = FactorizedCountPlan(program, ('x0',), cache=PackedMaskCache(max_bytes=0, max_width=0))
    assert p.count({'x0': 1}) == 1


@pytest.mark.parametrize('seed', range(24))
def test_affine_random_rows_against_assignment_enumeration(seed):
    rng = random.Random(seed)
    n = 6
    names = tuple('x'+str(i) for i in range(n))
    rows = [rng.randrange(1 << n) for _ in range(rng.randrange(10))]
    rhs = [rng.randrange(2) for _ in rows]
    p = AffineConstraintPlan(rows, rhs, names)
    for i in range(12):
        fixed = {names[j]: rng.randrange(2) for j in rng.sample(range(n), i % (n+1))}
        expected = sum(all(((r & x).bit_count() & 1) == b for r, b in zip(rows, rhs))
                       for x in range(1 << n) if all((x >> j & 1) == v for j, name in enumerate(names)
                                                                    for k, v in fixed.items() if k == name))
        assert p.count(fixed) == expected


def test_affine_expression_cm_cancellation_nonlinearity_and_constants():
    e = And(Eqv(Xor(Var(0), Var(1)), Not(Var(2))), Not(Xor(Var(0), Var(0))))
    names = ('x2', 'x0', 'x1', 'unused')
    for p in (AffineConstraintPlan.from_expr(e, names),
              AffineConstraintPlan.from_cm_node(compile_expr_to_cm_ir(e), names)):
        for vals in product((None, 0, 1), repeat=3):
            fixed = {n: v for n, v in zip(names, vals) if v is not None}
            assert p.count(fixed) == oracle(e, names, fixed)
    for e in (Or(Var(0), Var(1)), Xor(And(Var(0), Var(1)), Var(2)), Imp(Var(0), Var(1))):
        with pytest.raises(ValueError, match='non-affine'): AffineConstraintPlan.from_expr(e, names)
    for b in (0, 1):
        assert AffineConstraintPlan.from_cm_node(CMIRBuilder().const(b), names).count() == b*16


@pytest.mark.parametrize('rows,rhs,names,limits', [([4], [0], ('a', 'b'), {}),
    ([1], [], ('a',), {}), ([1], [2], ('a',), {}), ([1], [0], ('a', 'a'), {}),
    ([1], [0], ('a',), {'max_width': 0}), ([1], [0], ('a',), {'max_rows': 0})])
def test_affine_guards(rows, rhs, names, limits):
    with pytest.raises(ValueError): AffineConstraintPlan(rows, rhs, names, **limits)


def test_fixed_guards_and_concurrent_reuse():
    e = Or(Var(0), Var(1))
    plans = [factor(e, ('x0', 'x1')), AffineConstraintPlan([3], [0], ('x0', 'x1'))]
    for p in plans:
        for fixed in ({'missing': 0}, {'x0': 2}, {'x0': 0.0}):
            with pytest.raises(ValueError): p.count(fixed)
        contexts = [{'x0': i % 2, 'x1': i // 2 % 2} for i in range(40)]
        expected = [p.count(c) for c in contexts]
        with ThreadPoolExecutor(max_workers=4) as executor:
            assert list(executor.map(p.count, contexts)) == expected


def test_alist_redundant_directions_and_validation():
    text = '3 2\n2 2\n1 2 1\n2 2\n1 0\n1 2\n2 0\n1 2\n2 3\n'
    assert parse_alist(text) == (3, (3, 6))
    for bad in (text.replace('2 3\n', '1 3\n'), text + '1\n', text.replace('1 2\n2 3', '1 1\n2 3')):
        with pytest.raises(ValueError): parse_alist(bad)
    with pytest.raises(ValueError): parse_alist(text, max_width=2)
