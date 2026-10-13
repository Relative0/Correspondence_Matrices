"""Independent regression oracles for the 2026-10-10 computational audit."""
from __future__ import annotations

from itertools import permutations, product
from pathlib import Path
import random

import numpy as np
import pytest

from bitset_backend import (
    build_bitset_env,
    eval_cm_node_bitset,
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_bitset,
    eval_expr_flat_bitset,
    eval_expr_words_bitset,
    prepare_expr_flat_evaluation,
)
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir
from cm_normalize import lift_cm
from cmbench.comparative.gf2_native_slots import (
    compile_native_multi_root_arena,
    compile_native_slot_arena,
    load_native_slot_library,
)
from cmbench.comparative.gf2_projection_optimized import (
    compile_packed_cofactor_plan,
    project_packed_truth,
)


ROOT = Path(__file__).resolve().parents[1]


def _row_index(names, assignment):
    return sum(assignment[name] << (len(names) - 1 - i)
               for i, name in enumerate(names))


def _restricted_truth(bits, names, remaining, fixed):
    result = 0
    for row, values in enumerate(product((0, 1), repeat=len(remaining))):
        assignment = dict(zip(remaining, values)) | fixed
        result |= ((bits >> _row_index(names, assignment)) & 1) << row
    return result


@pytest.mark.parametrize("n", [3, 4, 5])
@pytest.mark.parametrize("axis", ["row", "column"])
def test_lift_every_axis_permutation_matches_named_scalar_assignments(n, axis):
    names = tuple(f"x{i}" for i in range(n))
    rng = random.Random(20261010 + n)
    truths = [rng.getrandbits(1 << n)]
    # Single-coordinate functions distinguish every axis even if random bits
    # happen to have a symmetry.
    truths.extend(sum(values[i] << row for row, values in enumerate(product((0, 1), repeat=n)))
                  for i in range(n))
    for bits in truths:
        vector = np.array([(bits >> row) & 1 for row in range(1 << n)], dtype=bool)
        for target in permutations(names):
            expected = _restricted_truth(bits, names, target, {})
            if axis == "row":
                actual = lift_cm(vector[:, None], list(names), [], list(target), [])
            else:
                actual = lift_cm(vector[None, :], [], list(names), [], list(target))
            packed = sum(int(value) << row for row, value in enumerate(actual.flat))
            assert packed == expected, (axis, names, target, bits)


def test_lift_reorders_both_axes_and_broadcasts_folded_fixed_and_padding_axes():
    rows, cols = ("x0", "x1", "x2"), ("x3", "x4", "x5")

    def value(a):
        return ((a["x0"] and not a["x4"]) != (a["x1"] and a["x3"])) or (a["x2"] and a["x5"])

    small = np.array([value(dict(zip(rows + cols, values)))
                      for values in product((0, 1), repeat=6)], dtype=bool).reshape(8, 8)
    for row_order, col_order in product(permutations(rows), permutations(cols)):
        target_rows = ("__pad0__",) + row_order + ("fixed",)
        target_cols = col_order + ("__pad1__",)
        actual = lift_cm(small, list(rows), list(cols), list(target_rows), list(target_cols),
                         fixed={"fixed": 1})
        expected = np.array([value(dict(zip(target_rows + target_cols, values)))
                             for values in product((0, 1), repeat=9)], dtype=bool)
        assert np.array_equal(actual.reshape(-1), expected)
        assert actual.flags.writeable


@pytest.mark.parametrize("n", [1, 2, 3])
def test_cofactors_exhaust_small_truth_functions_fixed_values_and_residual_orders(n):
    names = tuple(f"x{i}" for i in range(n))
    for states in product((None, 0, 1), repeat=n):
        fixed = {name: state for name, state in zip(names, states) if state is not None}
        live = tuple(name for name in names if name not in fixed)
        for remaining in permutations(live) if live else ():
            plan = compile_packed_cofactor_plan(n, fixed, remaining)
            for bits in range(1 << (1 << n)):
                assert project_packed_truth(bits, plan) == _restricted_truth(bits, names, remaining, fixed)


@pytest.mark.parametrize("n", [4, 5, 6, 7])
def test_cofactor_permutations_across_packed_word_boundaries(n):
    names = tuple(f"x{i}" for i in range(n))
    rng = random.Random(20261010 + n)
    for fixed in ({}, {names[0]: 0}, {names[-1]: 1}, {names[1]: 1, names[-1]: 0}):
        live = tuple(name for name in names if name not in fixed)
        orders = list(permutations(live)) if n <= 5 else [live, live[::-1], live[1:] + live[:1]]
        if n > 5:
            orders.extend(tuple(rng.sample(live, len(live))) for _ in range(8))
        for remaining in orders:
            plan = compile_packed_cofactor_plan(n, fixed, remaining)
            for bits in (0, (1 << (1 << n)) - 1, rng.getrandbits(1 << n)):
                assert project_packed_truth(bits, plan) == _restricted_truth(bits, names, remaining, fixed)


@pytest.mark.parametrize("remaining", [("x0", "x1", "x1"), ("x1", "x1")])
def test_cofactor_rejects_duplicate_residual_axes(remaining):
    with pytest.raises(ValueError, match="axis partition"):
        compile_packed_cofactor_plan(2, {} if "x0" in remaining else {"x0": 0}, remaining)


@pytest.fixture(params=["scalar", "multi"])
def native_boundary_arena(request):
    run = "native-fused-slot-development-20260902-002" if request.param == "scalar" else "native-multi-root-development-20260902-002"
    path = ROOT / "docs/recognition/runs" / run / "native/cm_fused_slots.dll"
    if not path.is_file():
        pytest.skip("historical native boundary library unavailable")
    library = load_native_slot_library(path)
    if request.param == "scalar":
        return compile_native_slot_arena(
            {"version": 2, "nodes": [{"op": "var", "i": 1}], "root": 0},
            library, variable_count=2)
    return compile_native_multi_root_arena(
        {"version": 2, "nodes": [{"op": "var", "i": 0}, {"op": "var", "i": 1}], "roots": [0, 1]},
        library, variable_count=2)


@pytest.mark.parametrize("layout", ["strided", "reversed", "readonly"])
@pytest.mark.parametrize("width", [2, 7])
def test_native_binding_views_match_scalar_truth_without_mutation(native_boundary_arena, layout, width):
    # Even before the fix, contiguous C reads remain inside these allocations.
    if layout == "strided":
        backing = np.array([0, 0, 1, 0], dtype=np.int16)
        bindings = backing[::2]
    elif layout == "reversed":
        backing = np.array([1, 0, 0, 0], dtype=np.int16)
        bindings = backing[1::-1]
    else:
        backing = bindings = np.array([0, 1], dtype=np.int16)
        bindings.flags.writeable = False
    before = backing.copy()
    expected = tuple(sum(values[i] << row for row, values in enumerate(product((0, 1), repeat=width)))
                     for i in range(2))
    actual = native_boundary_arena.evaluate(bindings, width)
    assert actual == (expected if hasattr(native_boundary_arena, "roots") else expected[1])
    assert np.array_equal(backing, before)


def _scalar(expr, assignment):
    if isinstance(expr, Var):
        return bool(assignment[f"x{expr.i}"])
    if isinstance(expr, Not):
        return not _scalar(expr.a, assignment)
    a, b = _scalar(expr.a, assignment), _scalar(expr.b, assignment)
    if isinstance(expr, And):
        return a and b
    if isinstance(expr, Or):
        return a or b
    if isinstance(expr, Xor):
        return a != b
    if isinstance(expr, Imp):
        return not a or b
    return a == b


@pytest.mark.parametrize("width", [2, 7])
@pytest.mark.parametrize("fixed_value", [0, 1])
def test_fixed_overrides_live_masks_in_all_packed_evaluators(width, fixed_value):
    names = tuple(f"x{i}" for i in reversed(range(width)))
    fixed = {"x0": fixed_value, "x2": 1}
    exprs = (Var(0), Not(Var(0)), Xor(Var(0), Var(1)),
             Eqv(Imp(Xor(Var(0), Var(1)), Not(Var(2))), Or(Var(1), And(Var(0), Var(2)))))
    for expr in exprs:
        expected = sum(int(_scalar(expr, dict(zip(names, values)) | fixed)) << row
                       for row, values in enumerate(product((0, 1), repeat=width)))
        node = compile_expr_to_cm_ir(expr)
        actuals = (
            eval_expr_bitset(expr, build_bitset_env(names), fixed=fixed),
            eval_expr_flat_bitset(expr, names, fixed=fixed),
            prepare_expr_flat_evaluation(expr, names, fixed=fixed).evaluate(),
            eval_expr_words_bitset(expr, names, fixed=fixed),
            eval_cm_node_bitset(node, names, fixed=fixed),
            eval_cm_node_flat(node, names, fixed=fixed),
            eval_cm_node_words(node, names, fixed=fixed),
        )
        assert actuals == (expected,) * len(actuals)


@pytest.mark.parametrize("expr, constant", [
    (Eqv(Var(0), Var(0)), 1), (Xor(Var(0), Var(0)), 0),
    (Or(Var(0), Not(Var(0))), 1), (And(Var(0), Not(Var(0))), 0),
    (Var(0), None),
])
def test_symbolic_benchmark_validation_accepts_constants_and_nonconstant_controls(expr, constant):
    from cm_bench import time_backends_on_expr
    from cmbench.config import BenchmarkConfig

    config = BenchmarkConfig(sizes=(3,), trials=1, seed=1, max_depth=2,
                             no_robdd=True, no_dd=True, no_robdd_dd=True,
                             no_numba=True, no_espresso=True)
    expected = np.full(8, constant, dtype=np.uint8) if constant is not None else np.array([0] * 4 + [1] * 4, dtype=np.uint8)
    row = time_backends_on_expr(3, expr, False, False, False, config=config, tt_ref=expected)
    assert row["cm_ok"] is True
    assert row["bitset_ok"] is True
    assert row["sympy_ok"] is True
    assert row["bdd_sop_ok"] is True
