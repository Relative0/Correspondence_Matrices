from __future__ import annotations

from collections import Counter

import pytest

from cmbench.comparative.gf2_prepared_policy_experiment import (
    BASELINE,
    CANDIDATE,
    C30Config,
    build_schedule,
    summarize,
)
from cmbench.comparative.gf2_resident_session_experiment import N_VARS


def row(cell, *, total: int, queries: int, charge: int):
    result = {
        **cell,
        "query_count": 8,
        "exact_check_passed": True,
        "lifecycle_preparation_charge_ns": charge,
        "timings_ns": {
            "setup_ns": total - queries - 2,
            "queries_ns": queries,
            "close_ns": 1,
            "wrapper_ns": 1,
            "batch_total_ns": total,
        },
    }
    if cell["method"] == CANDIDATE:
        result["setup_detail"] = {
            "prepared_context_bind_ns": 2,
            "session_initialize_ns": 3,
            "setup_total_ns": 5,
        }
    return result


def test_c30_schedule_is_adjacent_and_counterbalanced() -> None:
    schedule = build_schedule(C30Config("test"))
    assert len(schedule) == 128
    assert Counter((item["method"], item["arm_position"]) for item in schedule) == Counter({
        (BASELINE, 0): 32, (BASELINE, 1): 32,
        (CANDIDATE, 0): 32, (CANDIDATE, 1): 32,
    })
    for offset in range(0, len(schedule), 2):
        assert schedule[offset]["pair_id"] == schedule[offset + 1]["pair_id"]


def test_c30_summary_conserves_preparation_and_charges_candidate() -> None:
    schedule = build_schedule(C30Config("test", blocks=8))
    rows = []
    remaining = 32
    for cell in schedule:
        if cell["method"] == BASELINE:
            rows.append(row(cell, total=110, queries=100, charge=0))
        else:
            rows.append(row(cell, total=100, queries=95, charge=1))
            remaining -= 1
    assert remaining == 0
    result = summarize(rows, lifecycle_preparation_ns=32)
    assert result["measurement_batches"] == 64
    assert result["paired_batches"] == 32
    assert result["timed_queries"] == 512
    assert result["aggregate_ratio_of_median_charged_total_speedup"] == pytest.approx(110 / 101)
    assert result["minimum_width_ratio_of_median_charged_total_speedup"] == pytest.approx(110 / 101)
    assert result["prepared_no_regret_gate"] is True
    assert result["arm_order_balanced"] is True
    assert result["width_position_balanced"] is True


def test_c30_summary_rejects_missing_or_misallocated_charge() -> None:
    schedule = build_schedule(C30Config("test", blocks=8))
    rows = [row(cell, total=100, queries=90, charge=0) for cell in schedule]
    with pytest.raises(ValueError, match="not conserved"):
        summarize(rows, lifecycle_preparation_ns=1)
    rows[0]["exact_check_passed"] = False
    with pytest.raises(ValueError, match="inexact"):
        summarize(rows, lifecycle_preparation_ns=1)


def test_c30_config_requires_q8_complete_width_cycles() -> None:
    with pytest.raises(ValueError):
        C30Config("test", query_count=16).validate()
    with pytest.raises(ValueError):
        C30Config("test", blocks=12).validate()
