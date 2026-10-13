"""Independent truth, resource and lifecycle checks for opt-in packed queries."""
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from types import SimpleNamespace
import random

import pytest

from bitset_backend import bitset_env_cache_stats, clear_bitset_env_cache
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import CMIRBuilder, compile_expr_to_cm_ir
from cmbench.backends import packed_mask_cache as masks
from cmbench.backends.packed_mask_cache import PackedMaskCache
from cmbench.backends.packed_queries import IndependentCountPlan, PackedStreamPlan


def scalar(expr, assignment):
    if isinstance(expr, Var):
        return bool(assignment[f"x{expr.i}"])
    if isinstance(expr, Not):
        return not scalar(expr.a, assignment)
    a, b = scalar(expr.a, assignment), scalar(expr.b, assignment)
    return {And: lambda: a and b, Or: lambda: a or b, Xor: lambda: a != b,
            Imp: lambda: not a or b, Eqv: lambda: a == b}[type(expr)]()


def oracle(expr, basis, fixed):
    live = tuple(name for name in basis if name not in fixed)
    return [scalar(expr, dict(zip(live, row)) | fixed)
            for row in product((0, 1), repeat=len(live))]


def packed(rows):
    bits = sum(int(value) << index for index, value in enumerate(rows))
    return bits.to_bytes((len(rows) + 7) // 8, "little")


def cache(**kwargs):
    return PackedMaskCache(max_bytes=kwargs.get("max_bytes", 1 << 20),
                           max_width=kwargs.get("max_width", 16))


def test_positional_cache_shares_across_names_and_keeps_global_cache_empty():
    clear_bitset_env_cache()
    pool = cache()
    first = pool.environment(tuple(f"x{i}" for i in range(12)))
    second = pool.environment(tuple(f"axis-{i}" for i in range(12)))
    assert all(first[f"x{i}"] is second[f"axis-{i}"] for i in range(12))
    assert tuple(first) == tuple(f"x{i}" for i in range(12))
    with pytest.raises(TypeError):
        first["x0"] = 0
    for row in range(1 << 12):
        assert all((first[f"x{i}"] >> row) & 1 == (row >> (11 - i)) & 1 for i in range(12))
    assert pool.stats()["hits"] == 1
    assert bitset_env_cache_stats()["size"] == 0


def test_budget_eviction_bypass_and_caller_retention():
    probe = cache()
    probe.columns(10)
    budget = probe.stats()["entry_bytes"]
    pool = cache(max_bytes=budget)
    held = pool.columns(10)
    assert pool.columns(10) is held
    pool.columns(9)
    assert pool.stats()["evictions"] == 1
    pool.columns(16)
    assert pool.stats()["bypasses"] == 1
    assert pool.stats()["entry_bytes"] <= budget
    pool.clear()
    assert pool.stats()["entry_bytes"] == pool.stats()["entries"] == 0
    assert pool.columns(10) == held
    assert pool.columns(10) is not held
    uncached = cache(max_bytes=0)
    uncached.columns(10)
    assert uncached.stats()["entries"] == 0


def test_cache_uses_recency_and_serializes_same_width_misses():
    pool = cache(max_bytes=15000)
    with ThreadPoolExecutor(max_workers=8) as executor:
        values = list(executor.map(pool.columns, [12] * 24))
    assert all(value is values[0] for value in values)
    assert pool.stats()["misses"] == 1
    assert pool.stats()["hits"] == 23
    probe = cache()
    probe.columns(10)
    probe.columns(11)
    limited = cache(max_bytes=probe.stats()["entry_bytes"])
    old = limited.columns(10)
    limited.columns(11)
    limited.columns(10)
    limited.columns(9)
    assert limited.columns(10) is old


def test_guards_precede_mask_build_and_exceptions_are_not_cached(monkeypatch):
    calls = []

    def fail(names):
        calls.append(names)
        raise RuntimeError("controlled build failure")

    monkeypatch.setattr(masks, "_build_bitset_env_cached", SimpleNamespace(__wrapped__=fail))
    pool = cache(max_width=8)
    with pytest.raises(ValueError):
        pool.columns(9)
    assert calls == []
    for _ in range(2):
        with pytest.raises(RuntimeError):
            pool.columns(8)
    assert len(calls) == 2
    assert pool.stats()["entries"] == pool.stats()["entry_bytes"] == 0


@pytest.mark.parametrize("kwargs", [{"max_bytes": -1}, {"max_bytes": True},
                                    {"max_bytes": 1, "max_width": 31}])
def test_bad_cache_limits(kwargs):
    with pytest.raises(ValueError):
        PackedMaskCache(**kwargs)


def test_disjoint_counts_overlap_merge_unused_axes_and_large_declared_basis():
    expr = And(Or(Var(0), Var(1)), And(Xor(Var(2), Var(3)), Eqv(Var(4), Var(5))))
    pool = cache(max_width=3)
    plan = IndependentCountPlan.from_expr(expr, tuple(f"x{i}" for i in range(80)), cache=pool)
    assert len(plan.component_supports) == 3
    assert plan.count() == 3 * 2 * 2 * (1 << 74)
    assert plan.count({"x0": 0, "x79": 1}) == 1 * 2 * 2 * (1 << 73)
    assert not plan.exists({"x2": 1, "x3": 1})
    overlap = And(Or(Var(0), Var(1)), And(Xor(Var(2), Var(3)), Eqv(Var(1), Var(2))))
    merged = IndependentCountPlan.from_expr(overlap, tuple(f"x{i}" for i in range(4)), cache=pool)
    assert len(merged.component_supports) == 1
    before = pool.stats()
    with pytest.raises(ValueError, match="component live width"):
        merged.count()
    assert pool.stats() == before
    assert merged.count({"x1": 1}) == sum(oracle(overlap, merged.basis, {"x1": 1}))


@pytest.mark.parametrize("value", [0, 1])
def test_cm_constants_empty_basis_and_unused_axes(value):
    node = CMIRBuilder().const(value)
    for basis in ((), ("unused",)):
        pool = cache()
        plan = IndependentCountPlan.from_cm_node(node, basis, cache=pool)
        assert plan.count() == value * (1 << len(basis))
        assert plan.exists() is bool(value)
        stream = PackedStreamPlan.from_cm_node(node, basis, cache=pool)
        chunks = list(stream.iter_chunks(chunk_vars=3, max_total_bits=2))
        assert len(chunks) == 1
        assert chunks[0].valid_bits == 1 << len(basis)
        assert chunks[0].data == bytes([(1 << (1 << len(basis))) - 1 if value else 0])


def test_all_three_variable_functions_and_all_partial_assignments():
    basis = ("x2", "x0", "x1")
    pool = cache()
    for truth in range(256):
        terms = []
        for row in range(8):
            if (truth >> row) & 1:
                literals = [Var(i) if (row >> (2 - i)) & 1 else Not(Var(i)) for i in range(3)]
                terms.append(And(literals[0], And(literals[1], literals[2])))
        expr = And(Var(0), Not(Var(0))) if not terms else terms[0]
        for term in terms[1:]:
            expr = Or(expr, term)
        plan = IndependentCountPlan.from_expr(expr, basis, cache=pool)
        stream = PackedStreamPlan.from_expr(expr, basis, cache=pool)
        for values in product((None, 0, 1), repeat=3):
            fixed = {name: value for name, value in zip(basis, values) if value is not None}
            rows = oracle(expr, basis, fixed)
            assert plan.count(fixed) == sum(rows)
            assert plan.exists(fixed) == any(rows)
            chunks = list(stream.iter_chunks(chunk_vars=3, max_total_bits=8, fixed=fixed))
            assert b"".join(c.data for c in chunks) == packed(rows)


def test_random_dags_reordered_fixed_axes_and_stream_boundaries():
    rng = random.Random(20260911)
    basis = ("x4", "x1", "unused", "x5", "x3", "x0", "x2")
    for _ in range(80):
        nodes = [Var(i) for i in range(6)]
        for _ in range(25):
            op = rng.choice((And, Or, Xor, Imp, Eqv, Not))
            a = rng.choice(nodes)
            nodes.append(op(a) if op is Not else op(a, rng.choice(nodes)))
        expr = nodes[-1]
        node = compile_expr_to_cm_ir(expr)
        pool = cache()
        count = IndependentCountPlan.from_expr(expr, basis, cache=pool)
        cm_count = IndependentCountPlan.from_cm_node(node, basis, cache=pool)
        stream = PackedStreamPlan.from_cm_node(node, basis, cache=pool)
        for fixed in ({}, {"x4": 1, "x0": 0}, {name: rng.randrange(2) for name in basis}):
            rows = oracle(expr, basis, fixed)
            assert count.count(fixed) == cm_count.count(fixed) == sum(rows)
            assert count.exists(fixed) == any(rows)
            for width in (3, 4, 7):
                chunks = list(stream.iter_chunks(chunk_vars=width, max_total_bits=128, fixed=fixed))
                assert b"".join(chunk.data for chunk in chunks) == packed(rows)
                assert sum(chunk.valid_bits for chunk in chunks) == len(rows)
                assert [c.offset for c in chunks] == list(range(0, len(rows), 1 << min(width, len(rows).bit_length() - 1)))


def test_query_guards_and_eager_stream_refusal():
    pool = cache(max_width=8)
    expr = Or(Var(0), Var(1))
    for bad_basis in (("x0",), ("x0", "x0"), ("x0", "")):
        with pytest.raises(ValueError):
            IndependentCountPlan.from_expr(expr, bad_basis, cache=pool)
    basis = tuple(f"x{i}" for i in range(12))
    plan = IndependentCountPlan.from_expr(expr, basis, cache=pool)
    stream = PackedStreamPlan.from_expr(expr, basis, cache=pool)
    for fixed in ({"missing": 1}, {"x0": 2}, {"x0": "1"}):
        with pytest.raises(ValueError):
            plan.count(fixed)
        with pytest.raises(ValueError):
            stream.iter_chunks(chunk_vars=8, max_total_bits=4096, fixed=fixed)
    for width, total in ((9, 4096), (2, 4096), (8, 4095), (8, 0)):
        with pytest.raises(ValueError):
            stream.iter_chunks(chunk_vars=width, max_total_bits=total)
    assert pool.stats()["misses"] == 0


def test_stream_close_concurrent_queries_and_no_bound_context_retention():
    pool = cache()
    expr = Imp(Xor(Var(0), Var(5)), Or(Var(2), Var(3)))
    basis = tuple(f"x{i}" for i in range(12))
    plan = PackedStreamPlan.from_expr(expr, basis, cache=pool)
    iterator = plan.iter_chunks(chunk_vars=8, max_total_bits=4096)
    first = next(iterator)
    assert first.offset == 0 and first.valid_bits == 256
    iterator.close()
    assert iterator.gi_frame is None
    contexts = [{"x0": i & 1, "x5": (i >> 1) & 1} for i in range(16)]

    def run(fixed):
        return b"".join(c.data for c in plan.iter_chunks(chunk_vars=8, max_total_bits=4096, fixed=fixed))

    with ThreadPoolExecutor(max_workers=4) as executor:
        outputs = list(executor.map(run, contexts))
    assert all(output == packed(oracle(expr, basis, fixed)) for output, fixed in zip(outputs, contexts))
    assert plan.program.bound_cache == {}
    assert pool.stats()["entry_bytes"] <= pool.stats()["max_bytes"]


def test_stream_copies_fixed_context_at_request_time():
    expr = Xor(Var(0), Var(1))
    basis = tuple(f"x{i}" for i in range(6))
    plan = PackedStreamPlan.from_expr(expr, basis, cache=cache())
    fixed = {"x0": 0}
    chunks = plan.iter_chunks(chunk_vars=3, max_total_bits=64, fixed=fixed)
    fixed["x0"] = 1
    actual = b"".join(chunk.data for chunk in chunks)
    assert actual == packed(oracle(expr, basis, {"x0": 0}))
