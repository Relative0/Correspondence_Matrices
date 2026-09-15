from __future__ import annotations

import pytest

from cmbench.comparative.gf2_resident_session_experiment import (
    BATCH_TIMING_FIELDS,
    C25Config,
    METHODS,
    N_VARS,
    QUERY_COUNTS,
    summarize,
)


def _rows(advice_total: int):
    totals = {
        "resident_direct_exhaustive": 100,
        "resident_direct_screened": 50,
        "resident_direct_compiled_screened": 49,
        "resident_direct_source_packed": 48,
        "resident_c22_advice_on": advice_total,
        "resident_c22_advice_off": 105,
    }
    rows = []
    for n_vars in N_VARS:
        for count in QUERY_COUNTS:
            for method in METHODS:
                timings = {field: 0 for field in BATCH_TIMING_FIELDS}
                timings["queries_ns"] = totals[method] * count
                timings["batch_total_ns"] = totals[method] * count
                for round_index in range(3):
                    rows.append({
                        "n_vars": n_vars,
                        "query_count": count,
                        "method": method,
                        "round": round_index,
                        "timings_ns": timings,
                        "exact_check_passed": True,
                    })
    return rows


def test_c25_config_is_frozen():
    C25Config("run").validate()
    with pytest.raises(ValueError):
        C25Config("run", query_counts=(1, 2, 4)).validate()


def test_c25_summary_reports_break_even_and_excludes_false_gate():
    passing = summarize(_rows(45), [], {"all_passed": True})
    assert passing["advice_on_break_even_query_count"] == 1
    assert passing["resident_promotion_gate"] is True
    failing = summarize(_rows(55), [], {"all_passed": True})
    assert failing["advice_on_break_even_query_count"] is None
    assert failing["resident_promotion_gate"] is False
