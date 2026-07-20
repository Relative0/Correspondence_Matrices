import importlib

import numpy as np
import pytest

from cm_exprlib import And, Or, Var, eval_expr_tt
from cmbench.backends.robdd_dd import (
    _empty_robdd_dd_result,
    compact_order_repr,
    robdd_variable_order,
    run_robdd_dd_backend,
    select_dd_module,
)


def test_robdd_variable_order_fixed_policy() -> None:
    assert robdd_variable_order(And(Var(1), Var(0)), 3, "fixed", None) == ["x0", "x1", "x2"]


def test_robdd_variable_order_expr_policy_uses_first_occurrence() -> None:
    expr = And(Or(Var(2), Var(0)), Var(1))
    assert robdd_variable_order(expr, 4, "expr", None) == ["x2", "x0", "x1", "x3"]


def test_compact_order_repr_short_and_long() -> None:
    assert compact_order_repr(["x0", "x1"]) == "x0,x1"
    compact = compact_order_repr([f"x{i}" for i in range(200)])
    assert compact.startswith("sha256:")
    assert compact.endswith(";len=200")


def test_select_dd_module_auto_does_not_raise() -> None:
    module, error = select_dd_module("auto")
    assert module is not None or isinstance(error, str)


def test_run_robdd_dd_backend_autoref_small_expr_if_available() -> None:
    if importlib.util.find_spec("dd.autoref") is None:
        pytest.skip("dd.autoref unavailable")
    expr = And(Var(0), Var(1))
    tt_ref = eval_expr_tt(expr, 2).astype(np.uint8).reshape(-1)
    row = run_robdd_dd_backend(expr, 2, backend_preference="autoref", tt_ref=tt_ref)
    assert row["robdd_status"] == "ok"
    assert row["robdd_ok"] is True
    assert row["robdd_backend"] == "dd.autoref"


def test_empty_robdd_result_preserves_legacy_keys() -> None:
    row = _empty_robdd_dd_result(
        backend_preference="cudd",
        order_policy="fixed",
        order_seed=None,
        order_sweeps=1,
        dynamic_reordering=False,
        reorder_method="sift",
        status="unavailable",
        error="missing",
    )
    expected = {
        "robdd_build_time_s",
        "robdd_reorder_time_s",
        "robdd_total_build_plus_reorder_time_s",
        "robdd_node_count",
        "robdd_backend",
        "robdd_backend_module",
        "robdd_backend_class",
        "robdd_is_cudd",
        "robdd_is_autoref",
        "robdd_cudd_available",
        "robdd_backend_preference",
        "robdd_order_policy",
        "robdd_order_seed",
        "robdd_order_sweeps",
        "robdd_order_used",
        "robdd_best_time_s",
        "robdd_median_time_s",
        "robdd_worst_time_s",
        "robdd_best_nodes",
        "robdd_median_nodes",
        "robdd_worst_nodes",
        "robdd_dynamic_reordering_requested",
        "robdd_dynamic_reordering_available",
        "robdd_dynamic_reordering_used",
        "robdd_reorder_method",
        "robdd_nodes_before_reorder",
        "robdd_nodes_after_reorder",
        "robdd_status",
        "robdd_error",
        "robdd_tt_extract_time_s",
        "robdd_tt_extract_elements",
        "robdd_tt_extract_ok",
        "robdd_total_build_plus_extract_time_s",
        "robdd_tt_extract_status",
        "robdd_extract_method",
        "robdd_tt_extract_error",
        "robdd_ok",
        "robdd_correctness_mode",
    }
    assert expected <= set(row)
