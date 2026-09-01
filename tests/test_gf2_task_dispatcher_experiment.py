from __future__ import annotations

import pytest

from cmbench.recognition.gf2_task_dispatcher_experiment import (
    GF2DispatcherConfig,
    METHODS,
    summarize,
)


def test_config_bounds() -> None:
    GF2DispatcherConfig("test", rounds=1, max_seconds=30).validate()
    with pytest.raises(ValueError):
        GF2DispatcherConfig("", rounds=1, max_seconds=30).validate()
    with pytest.raises(ValueError):
        GF2DispatcherConfig("test", rounds=0, max_seconds=30).validate()


def test_summary_uses_per_case_medians_and_frozen_gates() -> None:
    rows = []
    totals = {
        "direct_exhaustive": (200, 220, 240),
        "direct_screened": (100, 110, 120),
        "c17_dispatch": (100, 110, 120),
        "c17_advice_off": (200, 220, 240),
    }
    for method in METHODS:
        for round_index, total in enumerate(totals[method]):
            rows.append({
                "case_id": "case", "method": method, "round": round_index,
                "representation_ns": 10, "policy_ns": 0, "analysis_ns": total - 20,
                "exact_check_ns": 10, "total_ns": total,
                "semantic_mismatches": 0, "artifact_mismatches": 0,
            })
    functional = {"all_exact": True}
    summary = summarize(rows, functional)
    assert summary["median_case_sum_ns"]["direct_exhaustive"]["total_ns"] == 220
    assert summary["speedup"]["c17_over_direct_exhaustive"] == 2.0
    assert summary["criteria"]["advice_off_within_3_percent"] is True
    assert summary["local_research_gate"] is True
