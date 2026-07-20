import numpy as np

from cm_exprlib import And, Not, Or, Var
from cmbench.expr.diagnostics import _expr_used_indices, expr_complexity_diagnostics, truth_table_diagnostics


def test_expr_complexity_diagnostics_contains_expected_keys() -> None:
    diag = expr_complexity_diagnostics(And(Var(0), Or(Not(Var(1)), Var(2))), 3)
    assert diag["expr_unique_var_count"] == 3
    assert diag["expr_uses_all_vars"] is True
    assert "expr_structural_hash_if_available" in diag


def test_truth_table_diagnostics_density_fields() -> None:
    diag = truth_table_diagnostics(np.array([0, 1, 1, 0], dtype=np.uint8))
    assert diag["tt_true_count"] == 2
    assert diag["tt_false_count"] == 2
    assert diag["tt_density"] == 0.5
    assert diag["tt_is_balancedish"] is True


def test_expr_used_indices_sorted() -> None:
    assert _expr_used_indices(And(Var(2), Or(Var(0), Var(2)))) == [0, 2]
