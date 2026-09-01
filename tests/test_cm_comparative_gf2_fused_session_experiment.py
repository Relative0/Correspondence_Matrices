from __future__ import annotations

import pytest

from cmbench.comparative.gf2_fused_session_experiment import (
    C26Config, METHODS, summarize,
)
from cmbench.comparative.gf2_resident_session_experiment import (
    BATCH_TIMING_FIELDS, N_VARS, QUERY_COUNTS,
)


def rows(advice_total: int):
    totals = {
        "resident_direct_exhaustive": 100,
        "resident_direct_screened": 50,
        "resident_direct_compiled_screened": 49,
        "resident_direct_source_packed": 48,
        "fused_c22_advice_on": advice_total,
        "fused_c22_advice_off": 105,
    }
    result = []
    for n_vars in N_VARS:
        for count in QUERY_COUNTS:
            for method in METHODS:
                timings = {field: 0 for field in BATCH_TIMING_FIELDS}
                timings["queries_ns"] = totals[method] * count
                timings["batch_total_ns"] = totals[method] * count
                for round_index in range(3):
                    result.append({"n_vars": n_vars, "query_count": count,
                                   "method": method, "round": round_index,
                                   "timings_ns": timings, "exact_check_passed": True})
    return result


def test_c26_config_is_frozen():
    C26Config("run").validate()
    with pytest.raises(ValueError):
        C26Config("run", query_counts=(1, 2)).validate()


def test_c26_summary_applies_break_even_gate():
    passing = summarize(rows(45), [], {"all_passed": True})
    assert passing["fused_advice_on_break_even_query_count"] == 1
    assert passing["fused_promotion_gate"] is True
    failing = summarize(rows(55), [], {"all_passed": True})
    assert failing["fused_advice_on_break_even_query_count"] is None
    assert failing["fused_promotion_gate"] is False
