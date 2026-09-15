from __future__ import annotations

from collections import Counter

import pytest

from cmbench.comparative.gf2_resident_session_experiment import N_VARS
from cmbench.comparative.gf2_variance_localization import (
    BASELINE,
    CANDIDATE,
    C29Config,
    build_schedule,
    localize_frozen_executions,
    summarize_interleaved,
)


def timing_row(method: str, n_vars: int, *, total: int, queries: int,
               block: int | None = None, round_index: int | None = None,
               arm_position: int = 0, width_position: int = 0):
    row = {
        "method": method,
        "n_vars": n_vars,
        "query_count": 8,
        "timings_ns": {
            "setup_ns": total - queries - 2,
            "queries_ns": queries,
            "close_ns": 1,
            "wrapper_ns": 1,
            "batch_total_ns": total,
        },
        "exact_check_passed": True,
        "arm_position": arm_position,
        "width_position": width_position,
    }
    if block is not None:
        row.update({"block": block, "pair_id": f"b{block:02d}-n{n_vars}"})
    if round_index is not None:
        row["round"] = round_index
    if method == CANDIDATE:
        row["setup_detail"] = {
            "c27_policy_load_validate_ns": 4,
            "c22_policy_load_validate_ns": 3,
            "session_initialize_ns": 2,
            "setup_total_ns": 9,
        }
    return row


def test_c29_schedule_is_adjacent_and_fully_counterbalanced() -> None:
    schedule = build_schedule(C29Config("test"))
    assert len(schedule) == 128
    for offset in range(0, len(schedule), 2):
        pair = schedule[offset:offset + 2]
        assert pair[0]["pair_id"] == pair[1]["pair_id"]
        assert {row["method"] for row in pair} == {BASELINE, CANDIDATE}
        assert [row["arm_position"] for row in pair] == [0, 1]
    assert Counter((row["method"], row["arm_position"]) for row in schedule) == Counter({
        (BASELINE, 0): 32, (BASELINE, 1): 32,
        (CANDIDATE, 0): 32, (CANDIDATE, 1): 32,
    })
    assert all(
        sum(row["n_vars"] == n_vars and row["width_position"] == position
            for row in schedule) == 8
        for n_vars in N_VARS for position in range(4)
    )


def test_c29_config_requires_complete_width_counterbalance_cycles() -> None:
    with pytest.raises(ValueError):
        C29Config("test", blocks=12).validate()
    with pytest.raises(ValueError):
        C29Config("test", query_count=16).validate()


def test_frozen_localization_separates_overhead_only_and_query_regressions() -> None:
    rows = []
    for n_vars in N_VARS:
        for round_index in range(5):
            rows.extend([
                timing_row(BASELINE, n_vars, total=110, queries=100,
                           round_index=round_index),
                timing_row(CANDIDATE, n_vars, total=120, queries=(90 if n_vars == 3 else 110),
                           round_index=round_index),
            ])
    result = localize_frozen_executions([{
        "execution_id": "one", "physical_machine_id": "machine",
        "environment": "test", "rows": rows,
    }])
    assert result["paired_cells"] == 20
    assert result["by_width"]["3"]["overhead_only_regression_cells"] == 5
    assert result["by_width"]["4"]["query_regression_cells"] == 5
    assert result["by_width"]["4"]["overhead_only_regression_cells"] == 0


def test_interleaved_summary_retains_component_and_order_diagnostics() -> None:
    schedule = build_schedule(C29Config("test", blocks=8))
    rows = []
    for cell in schedule:
        if cell["method"] == BASELINE:
            total, queries = 110, 100
        else:
            total, queries = 120, 90
        rows.append(timing_row(
            cell["method"], cell["n_vars"], total=total, queries=queries,
            block=cell["block"], arm_position=cell["arm_position"],
            width_position=cell["width_position"],
        ))
    result = summarize_interleaved(rows)
    assert result["measurement_batches"] == 64
    assert result["paired_batches"] == 32
    assert result["timed_queries"] == 512
    assert result["arm_order_balanced"] is True
    assert result["width_position_balanced"] is True
    assert result["candidate_policy_load_median_share_of_setup"] == pytest.approx(7 / 9)
    assert result["by_width"]["3"]["overhead_only_regression_blocks"] == 8
    assert result["by_width"]["3"]["ratio_of_median_total_speedup"] == pytest.approx(110 / 120)
    assert result["by_width"]["3"]["ratio_of_median_query_speedup"] == pytest.approx(100 / 90)


def test_interleaved_summary_rejects_unpaired_or_inexact_rows() -> None:
    baseline = timing_row(BASELINE, 3, total=110, queries=100, block=0)
    with pytest.raises(ValueError, match="unpaired"):
        summarize_interleaved([baseline])
    candidate = timing_row(CANDIDATE, 3, total=120, queries=100, block=0)
    candidate["exact_check_passed"] = False
    with pytest.raises(ValueError, match="inexact"):
        summarize_interleaved([baseline, candidate])
