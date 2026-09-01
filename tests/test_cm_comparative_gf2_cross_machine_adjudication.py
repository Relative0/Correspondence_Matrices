from __future__ import annotations

import pytest

from cmbench.comparative.gf2_cross_machine_adjudication import (
    BASELINE,
    CANDIDATE,
    adjudicate_cross_machine,
    adjudicate_execution,
    monotonic_suffix_start,
    paired_round_resamples,
    percentile_nearest_rank,
)
from cmbench.comparative.gf2_resident_session_experiment import N_VARS, QUERY_COUNTS


def rows(candidate_total: int = 100, q32_candidate_total: int | None = None):
    result = []
    for method in (BASELINE, CANDIDATE):
        for n_vars in N_VARS:
            for query_count in QUERY_COUNTS:
                for round_index in range(5):
                    total = 110 if method == BASELINE else candidate_total
                    if method == CANDIDATE and query_count == 32 and q32_candidate_total:
                        total = q32_candidate_total
                    result.append({
                        "method": method,
                        "n_vars": n_vars,
                        "query_count": query_count,
                        "round": round_index,
                        "timings_ns": {"batch_total_ns": total + round_index},
                        "exact_check_passed": True,
                    })
    return result


def execution(name: str, machine: str, timing_rows):
    return {
        "execution_id": name,
        "physical_machine_id": machine,
        "environment": "test",
        "independent_verification_sha256": "a" * 64,
        "measurements_sha256": "b" * 64,
        "rows": timing_rows,
    }


def test_complete_paired_resampling_and_nearest_rank_are_deterministic() -> None:
    assert len(paired_round_resamples()) == 5**5
    assert paired_round_resamples()[0] == (0, 0, 0, 0, 0)
    assert paired_round_resamples()[-1] == (4, 4, 4, 4, 4)
    assert percentile_nearest_rank([4, 1, 3, 2], 0.50) == 2
    with pytest.raises(ValueError):
        percentile_nearest_rank([], 0.05)
    with pytest.raises(ValueError):
        percentile_nearest_rank([1, 0], 0.05)


def test_execution_adjudication_requires_complete_exact_paired_surface() -> None:
    result = adjudicate_execution(rows())
    assert result["paired_round_resamples"] == 3125
    assert all(row["admissible"] for row in result["by_query_count"].values())
    broken = rows()
    broken[0]["exact_check_passed"] = False
    with pytest.raises(ValueError, match="invalid or inexact"):
        adjudicate_execution(broken)
    with pytest.raises(ValueError, match="surface mismatch"):
        adjudicate_execution(rows()[:-1])


def test_cross_machine_adjudicator_fails_closed_without_monotonic_suffix() -> None:
    result = adjudicate_cross_machine([
        execution("machine-a-good", "machine-a", rows()),
        execution("machine-b-q32-regression", "machine-b", rows(q32_candidate_total=120)),
    ])
    assert result["physical_machine_count"] == 2
    assert result["by_query_count"]["8"]["admissible"] is True
    assert result["by_query_count"]["32"]["admissible"] is False
    assert result["uncertainty_monotonic_suffix_start"] is None
    assert result["shadow_promotion"] is False
    assert result["production_promotion"] is False
    assert result["decision"] == "refuse_shadow_promotion_no_uncertainty_safe_monotonic_suffix"


def test_monotonic_suffix_helper_does_not_assume_profitability_is_monotonic() -> None:
    assert monotonic_suffix_start([8]) is None
    assert monotonic_suffix_start([8, 16, 32]) == 8
    assert monotonic_suffix_start([16, 32]) == 16
    assert monotonic_suffix_start([32]) == 32
    assert monotonic_suffix_start([]) is None


def test_cross_machine_adjudication_rejects_one_physical_machine() -> None:
    with pytest.raises(ValueError, match="at least two physical machines"):
        adjudicate_cross_machine([
            execution("windows", "local", rows()),
            execution("docker", "local", rows()),
        ])
