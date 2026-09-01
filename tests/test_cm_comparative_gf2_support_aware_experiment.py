from __future__ import annotations

import pytest

from cmbench.comparative.gf2_resident_session_experiment import (
    BATCH_TIMING_FIELDS, N_VARS, QUERY_COUNTS,
)
from cmbench.comparative.gf2_support_aware_experiment import (
    C27Config, METHODS, summarize,
)


def rows(advice_total: int):
    totals = {
        "resident_direct_exhaustive": 100,
        "resident_direct_screened": 50,
        "resident_direct_compiled_screened": 49,
        "resident_direct_source_packed": 48,
        "support_aware_c27_advice_on": advice_total,
        "support_aware_c27_advice_off": 105,
    }
    result = []
    for n_vars in N_VARS:
        for count in QUERY_COUNTS:
            for method in METHODS:
                timings = {field: 0 for field in BATCH_TIMING_FIELDS}
                timings["queries_ns"] = totals[method] * count
                timings["batch_total_ns"] = totals[method] * count
                for round_index in range(3):
                    result.append({
                        "n_vars": n_vars,
                        "query_count": count,
                        "method": method,
                        "round": round_index,
                        "timings_ns": timings,
                        "exact_check_passed": True,
                    })
    return result


def test_c27_config_is_frozen():
    C27Config("run").validate()
    with pytest.raises(ValueError):
        C27Config("run", query_counts=(1, 2)).validate()


def test_c27_summary_applies_frozen_confirmation_gate():
    passing = summarize(rows(45), [], {"all_passed": True})
    assert passing["support_aware_break_even_query_count"] == 1
    assert passing["support_aware_confirmation_gate"] is True
    assert passing["by_query_count"]["1"]["methods"][
        "support_aware_c27_advice_on"]["by_width_speedup_over_direct_screened"] == {
            str(n): 50 / 45 for n in N_VARS}
    failing = summarize(rows(55), [], {"all_passed": True})
    assert failing["support_aware_break_even_query_count"] is None
    assert failing["support_aware_confirmation_gate"] is False
