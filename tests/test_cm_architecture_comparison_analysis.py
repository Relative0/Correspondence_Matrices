from __future__ import annotations

import math

import pytest

from scripts import cm_analyze_architecture_comparison as analysis


def _row(case_id: str, block: int, arm: str, total: int) -> dict:
    return {
        "lane": "A",
        "status": "ok",
        "case_id": case_id,
        "block": block,
        "arm": arm,
        "timings_ns": {"accounted_total_ns": total},
    }


def test_paired_speedup_clusters_repeated_blocks_by_case() -> None:
    rows = [
        _row("case-a", 0, "baseline", 4),
        _row("case-a", 0, "candidate", 2),
        _row("case-a", 1, "baseline", 8),
        _row("case-a", 1, "candidate", 4),
        _row("case-b", 0, "baseline", 9),
        _row("case-b", 0, "candidate", 3),
        _row("case-b", 1, "baseline", 12),
        _row("case-b", 1, "candidate", 4),
    ]

    result = analysis.paired_speedup(
        rows, lane="A", baseline="baseline", candidate="candidate",
        label="synthetic", observed_case_ids={"case-a"},
    )

    assert result["paired_cells"] == 4
    assert result["case_clusters"] == 2
    assert result["case_speedups"]["case-a"] == pytest.approx(2.0)
    assert result["case_speedups"]["case-b"] == pytest.approx(3.0)
    assert result["case_cluster_geomean_speedup"] == pytest.approx(math.sqrt(6.0))
    assert result["candidate_case_wins"] == 2
    assert result["observed_regression"]["case_cluster_geomean_speedup"] == pytest.approx(2.0)
    assert result["fresh"]["case_cluster_geomean_speedup"] == pytest.approx(3.0)


def test_paired_speedup_rejects_an_incomplete_arm_cell() -> None:
    rows = [
        _row("case-a", 0, "baseline", 4),
        _row("case-a", 0, "candidate", 2),
        _row("case-a", 1, "baseline", 8),
    ]

    with pytest.raises(ValueError, match="incomplete paired cells"):
        analysis.paired_speedup(
            rows, lane="A", baseline="baseline", candidate="candidate",
            label="synthetic-incomplete",
        )


def test_retry_002_analysis_retains_decision_limits() -> None:
    recorded = analysis._load(
        analysis.ROOT
        / "docs/recognition/architecture_comparison_execution_retry_20260903/ANALYSIS.json"
    )

    assert recorded["status"] == "verified_interpretation_complete"
    assert recorded["verification"]["rows_checked"] == 19_646
    assert recorded["lanes"]["A"]["best_fixed_cm_arm"] == "cm_ir_recursive_packed"
    assert recorded["lanes"]["B"]["timed_query_counts"] == [64]
    assert recorded["lanes"]["B"]["correctness_checkpoint_counts"] == [1, 4, 16, 64]
    assert recorded["lanes"]["B"]["native_minimum_case_gate_passed"] is False
    assert recorded["measurement_limits"]["per_arm_memory_interpretation_permitted"] is False
    assert recorded["measurement_limits"]["website_update_permitted"] is False
