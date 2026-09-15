from __future__ import annotations

import pytest

from cmbench.comparative.gf2_source_portfolio_experiment import (
    C24Config,
    METHODS,
    TIMING_FIELDS,
    summarize,
)


def _rows():
    rows = []
    totals = {
        "direct_exhaustive": 100,
        "direct_screened": 50,
        "direct_compiled_screened": 48,
        "direct_source_packed": 45,
        "c22_advice_on": 55,
        "c22_advice_off": 105,
        "c22_advice_on_shadow": 150,
        "c22_advice_off_shadow": 150,
    }
    for case_id in ("a", "b"):
        for method in METHODS:
            timings = {field: 0 for field in TIMING_FIELDS}
            timings["request_ns"] = totals[method]
            timings["task_total_ns"] = totals[method]
            for round_index in range(3):
                rows.append({
                    "case_id": case_id,
                    "method": method,
                    "round": round_index,
                    "timings_ns": timings,
                    "exact_check_passed": True,
                })
    return rows


def test_c24_config_bounds():
    C24Config("run").validate()
    with pytest.raises(ValueError):
        C24Config("run", rounds=2).validate()
    with pytest.raises(ValueError):
        C24Config("run", memory_cases_per_width=4).validate()


def test_c24_summary_excludes_shadow_from_deployable_rank_and_applies_gate():
    summary = summarize(_rows(), [], {"all_passed": True})
    assert summary["best_deployable_fixed_method"] == "direct_source_packed"
    assert summary["local_promotion_gate"] is False
    assert summary["functional_control_gate"] is True
    assert summary["wrapper_comparisons"][
        "c22_advice_on_speedup_over_direct_source_packed"] == pytest.approx(45 / 55)
