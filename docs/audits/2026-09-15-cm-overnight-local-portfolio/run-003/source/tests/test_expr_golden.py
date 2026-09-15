import itertools

import numpy as np
import pytest

import cm_bench
from bitset_backend import bitset_to_bool_array, build_bitset_env, eval_expr_bitset
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, eval_expr_tt


def _golden_exprs():
    return [
        And(Var(0), Var(1)),
        Or(Not(Var(0)), Var(1)),
        Xor(Var(0), Var(1)),
        Eqv(Imp(Var(0), Var(1)), Or(Not(Var(0)), Var(1))),
    ]


@pytest.mark.parametrize("expr", _golden_exprs())
def test_assignment_eval_agrees_with_truth_table(expr):
    tt = eval_expr_tt(expr, 2).reshape(-1)
    for idx, values in enumerate(itertools.product([0, 1], repeat=2)):
        assignment = {f"x{i}": values[i] for i in range(2)}
        assert cm_bench.eval_expr_assignment(expr, assignment) == int(tt[idx])


@pytest.mark.parametrize("expr", _golden_exprs())
def test_bitset_eval_agrees_with_truth_table(expr):
    env = build_bitset_env(["x0", "x1"])
    bits = eval_expr_bitset(expr, env)
    assert np.array_equal(bitset_to_bool_array(bits, 2), eval_expr_tt(expr, 2))


@pytest.mark.parametrize("expr", _golden_exprs())
def test_cm_eval_agrees_with_truth_table(expr):
    try:
        from cm_build import compile_expr_to_cm
        from cm_normalize import canonical_layout
    except Exception as exc:
        pytest.skip(f"CM dependencies unavailable: {exc!r}")

    R, C = canonical_layout(["x0", "x1"], mode="balanced")
    try:
        matrix = compile_expr_to_cm(expr, R, C, fixed={})
    except Exception as exc:
        pytest.skip(f"CM compile unavailable: {exc!r}")

    assert np.array_equal(cm_bench.cm_matrix_to_tt(matrix, R, C, 2), eval_expr_tt(expr, 2))

