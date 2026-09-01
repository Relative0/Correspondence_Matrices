from __future__ import annotations

import pytest

from cmbench.comparative.gf2_method_table import METHODS, TIMING_FIELDS
from cmbench.comparative.gf2_table_experiment import C21Config, summarize


def make_rows(compiled_b=51):
    costs = {
        "a": {method: 50 + index for index, method in enumerate(METHODS)},
        "b": {method: 100 + index for index, method in enumerate(METHODS)},
    }
    costs["a"]["cm_exhaustive"] = 100
    costs["a"]["cm_screened"] = 50
    costs["a"]["cm_compiled_screened"] = 51
    costs["b"]["cm_exhaustive"] = 100
    costs["b"]["cm_screened"] = 50
    costs["b"]["cm_compiled_screened"] = compiled_b
    rows = []
    for case, methods in costs.items():
        for method, total in methods.items():
            stages = {field: 0 for field in TIMING_FIELDS}
            stages["completion_ns"] = total
            stages["task_total_ns"] = total
            for round_index in range(3):
                rows.append({"case_id": case, "method": method, "round": round_index,
                             "timings_ns": stages, "proposal": {"status": "not_applicable"},
                             "exact_check_passed": True})
    return rows


def test_summary_selects_best_fixed_and_charges_compiled_tail():
    summary = summarize(make_rows(), [], {"all_exact": True})
    assert summary["best_fixed_method"] == "cm_screened"
    assert summary["methods"]["cm_screened"]["aggregate_speedup_over_exhaustive"] == 2.0
    assert summary["compiled_no_regret_gate"] is True


def test_summary_rejects_slow_compiled_tail_and_config_is_bounded():
    summary = summarize(make_rows(compiled_b=70), [], {"all_exact": True})
    assert summary["compiled_no_regret_gate"] is False
    C21Config("run").validate()
    with pytest.raises(ValueError):
        C21Config("run", rounds=2).validate()

