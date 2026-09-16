"""Exact-count contracts across the native and both Python dd backends."""
import itertools
import operator
import random

import pytest
from dd import autoref, bdd, cudd

from reference import exact_cudd_count


@pytest.mark.parametrize("expression", [
    "TRUE", "FALSE", "x3", "~x3", "x1 & x7", "x1 | x7",
    "~(x1 & x7)", "(x1 & x3) | (~x1 & x7)",
    "(x1 ^ x3) & (x3 | ~x7)",
])
@pytest.mark.parametrize("width", [None, 8, 80, 1100])
def test_cross_backend(expression, width):
    results = []
    for backend in (bdd, autoref, cudd):
        manager = backend.BDD()
        manager.declare(*(f"x{i}" for i in range(8)))
        root = manager.add_expr(expression)
        result = manager.count(root, nvars=width)
        assert type(result) is int
        results.append(result)
        if backend is cudd:
            assert root.count(nvars=width) == result
            assert manager.count(root, nvars=8) == exact_cudd_count(manager, root)
        del root
    assert results[0] == results[1] == results[2]


@pytest.mark.parametrize("width", [0, 1, 31, 32, 33, 63, 64, 65, 1024, 15000])
def test_constants_and_apa_digit_boundaries(width):
    manager = cudd.BDD()
    assert manager.count(manager.true, width) == 1 << width
    assert manager.count(manager.false, width) == 0
    assert type(manager.count(manager.true, width)) is int


@pytest.mark.parametrize("width", [53, 54, 63, 64, 65, 127, 256])
def test_one_less_than_power_of_two(width):
    manager = cudd.BDD()
    manager.configure(reordering=False)
    manager.declare(*(f"x{i}" for i in range(width)))
    root = manager.false
    for name in manager.vars:
        root |= manager.var(name)
    expected = (1 << width) - 1
    assert manager.count(root) == expected
    assert manager.count(~root) == 1
    assert exact_cudd_count(manager, root) == expected
    if width > 53:
        assert int(manager.count_double(root)) != expected


def test_double_overflow_and_exact_large_result():
    manager = cudd.BDD()
    manager.declare("x")
    root = manager.var("x")
    assert manager.count(root, 1100) == 1 << 1099
    with pytest.raises(RuntimeError, match="overflow"):
        manager.count_double(root, 1100)


def test_validation():
    manager, other = cudd.BDD(), cudd.BDD()
    manager.declare("x", "y", "z")
    root = manager.add_expr("x & z")
    assert manager.count(root) == 1
    assert manager.count(root, 3) == 2
    assert manager.count(root, 4) == 4  # larger than the manager
    for width in (-1, 0, 1):
        with pytest.raises(ValueError):
            manager.count(root, width)
    for width in (2.0, 2.5, "3"):
        with pytest.raises(TypeError):
            manager.count(root, width)
    for width in (2**31 - 1, 2**31, 2**100):
        with pytest.raises(OverflowError):
            manager.count(root, width)
    with pytest.raises(ValueError, match="manager"):
        manager.count(other.true)

    class Width:
        def __index__(self):
            return 4

    assert manager.count(root, Width()) == 4


def test_seeded_dags_against_truth_table_and_reordering():
    rng = random.Random(1701)
    native, reference = cudd.BDD(), autoref.BDD()
    names = [f"x{i}" for i in range(7)]
    for manager in (native, reference):
        manager.declare(*names)
    assignments = list(itertools.product((False, True), repeat=len(names)))
    roots = [(native.var(name), reference.var(name),
              [row[i] for row in assignments]) for i, name in enumerate(names)]
    for _ in range(100):
        left, right = rng.choices(roots, k=2)
        op_name, operation = rng.choice([
            ("and", operator.and_), ("or", operator.or_), ("xor", operator.xor)])
        u = native.apply(op_name, left[0], right[0])
        v = reference.apply(op_name, left[1], right[1])
        truth = [operation(a, b) for a, b in zip(left[2], right[2])]
        if rng.getrandbits(1):
            u, v, truth = ~u, ~v, [not a for a in truth]
        roots.append((u, v, truth))
        assert native.count(u, len(names)) == reference.count(v, len(names)) == sum(truth)
        assert native.count(u) == reference.count(v)
    native.reorder({name: i for i, name in enumerate(reversed(names))})
    for u, v, truth in roots:
        assert native.count(u, len(names)) == sum(truth)
        assert exact_cudd_count(native, u) == sum(truth)
    del u, v, roots, left, right


def test_repeated_calls_leave_root_usable():
    manager = cudd.BDD()
    manager.declare("x", "y", "z")
    root = manager.add_expr("x | (y & ~z)")
    identity, refs = int(root), root.ref
    for _ in range(2000):
        assert manager.count(root, 256) == 5 << 253
        assert manager.count(~root, 256) == 3 << 253
    assert int(root) == identity
    assert root.ref == refs
    assert manager.count(root) == 5
