from __future__ import annotations

import math

from scripts import cm_heldout_abc_i10_selector as selector


def _row(k: int, ratio: float, scale: int = 10) -> dict:
    return {
        "corpus": "bx1",
        "live_k": str(k),
        "structural_dag_nodes_source": str(scale),
        "unfolded_tree_nodes": str(scale * 2),
        "cm_instructions": str(scale),
        "cm_executed_bigint_ops": str(scale + 1),
        "cm_executed_word_ops": str(scale + 2),
        "cm_peak_live_word_buffers": "2",
        "raw_instructions": str(scale),
        "raw_executed_bigint_ops": str(scale + 1),
        "raw_executed_word_ops": str(scale + 2),
        "raw_flat_ns_median": "100",
        "raw_words_ns_median": str(100 * ratio),
        "cm_flat_ns_median": "100",
        "cm_words_ns_median": str(100 * ratio),
    }


def test_select_evenly_keeps_endpoints_and_refuses_duplicates() -> None:
    rows = [{"value": index} for index in range(10)]
    selected = selector._select_evenly(rows, 4)
    assert [row["value"] for row in selected] == [0, 3, 6, 9]
    assert len({row["value"] for row in selected}) == 4


def test_ridge_fit_and_prediction_are_finite() -> None:
    rows = [_row(k, 2.0 if k < 12 else 0.5, k + 5) for k in range(6, 17)]
    model = selector._fit_ridge(rows, "cm", 1.0)
    predictions = [selector._predict(model, row) for row in rows]
    assert all(math.isfinite(value) for value in predictions)
    assert len(model["coefficient"]) == 7


def test_lambda_choice_is_training_only_and_deterministic() -> None:
    rows = []
    for k in (6, 8, 10, 12, 14, 16):
        rows.extend([_row(k, 1.5 if k < 14 else 0.7, k + offset) for offset in (1, 2)])
    first, first_diagnostics = selector._choose_lambda(rows, "raw")
    second, second_diagnostics = selector._choose_lambda(rows, "raw")
    assert first in selector.RIDGE_LAMBDAS
    assert first == second
    assert first_diagnostics == second_diagnostics
