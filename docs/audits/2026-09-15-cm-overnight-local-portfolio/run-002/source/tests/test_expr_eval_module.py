from types import SimpleNamespace

import numpy as np

from cm_exprlib import And, Not, Or, Var, eval_expr_tt
from cmbench.expr.eval import eval_expr_assignment, result_value_for_assignment, sampled_correctness_check


def test_eval_expr_assignment_matches_truth_table() -> None:
    expr = Or(Not(Var(0)), Var(1))
    tt = eval_expr_tt(expr, 2).astype(np.uint8).reshape(-1)
    for idx in range(4):
        assignment = {"x0": (idx >> 1) & 1, "x1": idx & 1}
        assert eval_expr_assignment(expr, assignment) == int(tt[idx])


def test_result_value_for_assignment_reads_bits_and_tt() -> None:
    row = SimpleNamespace(output_vars=["x0", "x1"], bits=0b1000, tt=None)
    assert result_value_for_assignment(row, {"x0": 1, "x1": 1}) == 1
    row = SimpleNamespace(output_vars=["x0", "x1"], bits=None, tt=np.array([0, 0, 0, 1], dtype=np.uint8))
    assert result_value_for_assignment(row, {"x0": 1, "x1": 1}) == 1


def test_sampled_correctness_check_reports_zero_mismatches() -> None:
    expr = And(Var(0), Var(1))
    row = SimpleNamespace(output_vars=["x0", "x1"], bits=None, tt=eval_expr_tt(expr, 2).astype(np.uint8).reshape(-1))
    check = sampled_correctness_check(expr, row, 2, 8, np.random.default_rng(0))
    assert check["sampled_correctness_samples"] == 8
    assert check["sampled_correctness_mismatches"] == 0
