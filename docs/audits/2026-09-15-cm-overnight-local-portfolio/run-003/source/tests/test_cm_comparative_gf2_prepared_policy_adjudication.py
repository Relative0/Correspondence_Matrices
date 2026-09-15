from __future__ import annotations

import pytest

from cmbench.comparative.gf2_prepared_policy_adjudication import (
    adjudicate_cross_machine,
    adjudicate_execution,
    median_lower_bound,
    median_lower_order_statistic_rank,
)
from cmbench.comparative.gf2_prepared_policy_experiment import (
    BASELINE,
    CANDIDATE,
    C30Config,
    build_schedule,
)


def rows(*, bad_blocks: int = 0):
    lifecycle_ns = 64
    result = []
    for cell in build_schedule(C30Config("test-c31")):
        candidate = cell["method"] == CANDIDATE
        raw_total = 1000 if candidate else 1100
        if candidate and cell["block"] < bad_blocks:
            raw_total = 1200
        row = {
            **cell,
            "status": "ok",
            "query_count": 8,
            "timings_ns": {
                "setup_ns": 10,
                "queries_ns": raw_total - 30,
                "close_ns": 10,
                "wrapper_ns": 10,
                "batch_total_ns": raw_total,
            },
            "lifecycle_preparation_charge_ns": 1 if candidate else 0,
            "exact_check_passed": True,
        }
        if candidate:
            row["setup_detail"] = {
                "prepared_context_bind_ns": 4,
                "session_initialize_ns": 6,
                "setup_total_ns": 10,
            }
        result.append(row)
    assert sum(row["lifecycle_preparation_charge_ns"] for row in result) == lifecycle_ns
    return result, lifecycle_ns


def execution(name: str, machine: str, *, bad_blocks: int = 0):
    timing_rows, lifecycle_ns = rows(bad_blocks=bad_blocks)
    return {
        "execution_id": name,
        "physical_machine_id": machine,
        "environment": {"platform": "test"},
        "measurements_sha256": "a" * 64,
        "independent_verification_sha256": "b" * 64,
        "lifecycle_preparation_ns": lifecycle_ns,
        "rows": timing_rows,
    }


def test_exact_median_lower_bound_contract_is_deterministic() -> None:
    rank, coverage = median_lower_order_statistic_rank()
    assert rank == 5
    assert coverage == 63019 / 65536
    assert median_lower_bound(list(range(1, 17))) == 5.0
    with pytest.raises(ValueError, match="exactly 16"):
        median_lower_bound([1.0] * 15)


def test_execution_passes_point_and_paired_lower_gates() -> None:
    timing_rows, lifecycle_ns = rows()
    result = adjudicate_execution(
        timing_rows, lifecycle_preparation_ns=lifecycle_ns)
    assert result["point_gate"] is True
    assert result["paired_lower_gate"] is True
    assert result["admissible"] is True
    assert result["measurement_batches"] == 128
    assert result["timed_queries"] == 1024


def test_five_bad_blocks_fail_lower_bound_while_point_estimate_passes() -> None:
    timing_rows, lifecycle_ns = rows(bad_blocks=5)
    result = adjudicate_execution(
        timing_rows, lifecycle_preparation_ns=lifecycle_ns)
    assert result["point_gate"] is True
    assert result["paired_lower_gate"] is False
    assert result["admissible"] is False


def test_cross_machine_adjudication_requires_two_machines_and_fails_closed() -> None:
    passed = adjudicate_cross_machine([
        execution("windows", "physical-a"),
        execution("linux", "physical-b"),
    ])
    assert passed["replication_admissible"] is True
    assert passed["eligible_for_separate_shadow_review"] is True
    assert passed["shadow_promotion"] is False
    refused = adjudicate_cross_machine([
        execution("windows", "physical-a"),
        execution("linux", "physical-b", bad_blocks=5),
    ])
    assert refused["point_gate_all_executions"] is True
    assert refused["paired_lower_gate_all_executions"] is False
    assert refused["replication_admissible"] is False
    with pytest.raises(ValueError, match="two physical machines"):
        adjudicate_cross_machine([
            execution("one", "same"), execution("two", "same")])


def test_adjudication_rejects_schedule_or_charge_changes() -> None:
    timing_rows, lifecycle_ns = rows()
    timing_rows[0]["pair_id"] = "changed"
    with pytest.raises(ValueError, match="schedule mismatch"):
        adjudicate_execution(timing_rows, lifecycle_preparation_ns=lifecycle_ns)
    timing_rows, lifecycle_ns = rows()
    candidate = next(row for row in timing_rows if row["method"] == CANDIDATE)
    candidate["lifecycle_preparation_charge_ns"] += 1
    with pytest.raises(ValueError, match="charge is not conserved"):
        adjudicate_execution(timing_rows, lifecycle_preparation_ns=lifecycle_ns)
