from __future__ import annotations

import copy
import json

import pytest

from cmbench.recognition import learning_benchmark_handoff as handoff
from cmbench.recognition import version_history_learning_protocol as history


def _replication(identifier: str, machine: str) -> dict:
    row = {
        "replication_id": identifier,
        "physical_machine_sha256": machine * 64,
        "compiler_sha256": ("c" if identifier == "machine-a" else "d") * 64,
        "independent_verification_sha256": (
            "e" if identifier == "machine-a" else "f"
        ) * 64,
        "verification_status": "verified_complete",
        "case_set_sha256": "7" * 64,
        "label_table_sha256": "8" * 64,
        "complete_cases": 32,
        "best_fixed_method": "sat/resident_engine",
        "best_fixed_sum_ns": 1_200_000.0,
        "oracle_sum_ns": 1_000_000.0,
        "gross_speedup": 0.0,
        "p95_costs_ns_per_case": {
            "feature_extraction_and_control": 700.0,
            "model_inference": 100.0,
            "exact_verification": 100.0,
            "expected_fallback": 100.0,
        },
        "p95_costs_measured_same_host": True,
        "fully_charged_speedup": 0.0,
        "sum_based_economics": True,
        "schedule_mismatches": 0,
        "semantic_mismatches": 0,
        "source_or_artifact_mismatches": 0,
    }
    economics = handoff.replication_economics(row)
    row["gross_speedup"] = economics["gross_speedup"]
    row["fully_charged_speedup"] = economics["fully_charged_speedup"]
    return row


@pytest.fixture
def eligible_handoff() -> dict:
    return {
        "schema": handoff.SCHEMA,
        "status": "verified_complete",
        "surface_id": "version_history_resident_v2",
        "task_contract_sha256": "1" * 64,
        "source_checkpoint": "2" * 64,
        "source_tree": "3" * 64,
        "freeze_sha256": "4" * 64,
        "baseline_closure": {
            "status": "verified_complete",
            "sha256": "5" * 64,
            "all_relevant_exact_baselines_included": True,
        },
        "cohort": {
            "role": "source_blind_development",
            "protocol_frozen_before_labels": True,
            "source_groups": 32,
            "source_groups_by_split": {
                "development_fit": 16,
                "development_validation": 8,
                "development_audit": 8,
            },
            "source_groups_per_label": {
                "cnf/resident_engine": 16,
                "sat/resident_engine": 16,
            },
            "cross_split_source_group_intersections": 0,
            "prospective_cases_consumed": 0,
            "case_set_sha256": "7" * 64,
            "label_table_sha256": "8" * 64,
        },
        "exact_methods": {
            "arms": ["cnf/resident_engine", "sat/resident_engine"],
            "refused_rows_retained": True,
            "task_identical_exact_outputs": True,
        },
        "replications": [
            _replication("machine-a", "a"),
            _replication("machine-b", "b"),
        ],
        "claim_boundary": {
            "development_training_eligibility_permitted": True,
            "prospective_consumption_permitted": False,
            "production_routing_permitted": False,
        },
    }


def _refresh_economics(replication: dict) -> None:
    economics = handoff.replication_economics(replication)
    replication["gross_speedup"] = economics["gross_speedup"]
    replication["fully_charged_speedup"] = economics["fully_charged_speedup"]


def test_complete_two_machine_sum_based_handoff_reaches_development_gate(
    eligible_handoff,
):
    result = handoff.assess_handoff(eligible_handoff)
    assert result["status"] == "eligible_for_development_experiment_design"
    assert result["development_training_eligible"] is True
    assert result["minimum_gross_speedup"] == pytest.approx(1.2)
    assert result["minimum_fully_charged_speedup"] > 1.10
    assert result["blockers"] == []
    assert result["training_performed"] is False
    assert result["prospective_data_consumption_permitted"] is False
    assert result["advice_enabled"] is False
    assert result["production_routing_permitted"] is False


@pytest.mark.parametrize(
    ("mutation", "blocker"),
    [
        (lambda value: value.update(status="incomplete"), "handoff_not_verified_complete"),
        (
            lambda value: value["baseline_closure"].update(
                all_relevant_exact_baselines_included=False
            ),
            "exact_baseline_closure_incomplete",
        ),
        (
            lambda value: value["cohort"].update(protocol_frozen_before_labels=False),
            "protocol_not_frozen_before_labels",
        ),
        (
            lambda value: value["cohort"].update(
                cross_split_source_group_intersections=1
            ),
            "source_group_split_leakage",
        ),
        (
            lambda value: value["claim_boundary"].update(
                development_training_eligibility_permitted=False
            ),
            "benchmark_claim_boundary_forbids_development_training",
        ),
    ],
)
def test_policy_and_provenance_failures_abstain(eligible_handoff, mutation, blocker):
    mutation(eligible_handoff)
    result = handoff.assess_handoff(eligible_handoff)
    assert blocker in result["blockers"]
    assert result["development_training_eligible"] is False
    assert result["complete_abstention"] is True


def test_requires_two_distinct_physical_machines(eligible_handoff):
    eligible_handoff["replications"][1]["physical_machine_sha256"] = "a" * 64
    result = handoff.assess_handoff(eligible_handoff)
    assert "physical_machines_not_distinct" in result["blockers"]
    assert result["development_training_eligible"] is False


def test_requires_stable_case_and_label_tables(eligible_handoff):
    eligible_handoff["replications"][1]["label_table_sha256"] = "9" * 64
    result = handoff.assess_handoff(eligible_handoff)
    assert "replication_label_table_mismatch" in result["blockers"]
    assert result["development_training_eligible"] is False


def test_requires_sum_based_same_host_fully_charged_economics(eligible_handoff):
    row = eligible_handoff["replications"][0]
    row["sum_based_economics"] = False
    row["p95_costs_measured_same_host"] = False
    row["p95_costs_ns_per_case"]["feature_extraction_and_control"] = 5_000.0
    _refresh_economics(row)
    result = handoff.assess_handoff(eligible_handoff)
    assert "sum_based_economics_missing:machine-a" in result["blockers"]
    assert "same_host_p95_costs_missing:machine-a" in result["blockers"]
    assert "charged_headroom_below_1_10:machine-a" in result["blockers"]
    assert result["development_training_eligible"] is False


def test_recomputes_and_rejects_tampered_economics(eligible_handoff):
    eligible_handoff["replications"][0]["fully_charged_speedup"] = 99.0
    with pytest.raises(ValueError, match="economics replay"):
        handoff.assess_handoff(eligible_handoff)
    result = handoff.assess_or_abstain(eligible_handoff)
    assert result["blockers"] == ["malformed_or_unverified_handoff"]
    assert result["development_training_eligible"] is False


def test_missing_charged_cost_fails_closed(eligible_handoff):
    eligible_handoff["replications"][0]["p95_costs_ns_per_case"][
        "exact_verification"
    ] = None
    result = handoff.assess_or_abstain(eligible_handoff)
    assert result["status"] == "abstained"
    assert result["development_training_eligible"] is False
    assert result["advice_enabled"] is False


def test_current_verified_evidence_has_explicit_nontraining_blockers():
    artifact = history.DEFAULT_BENCHMARK_ARTIFACT.parent / (
        "version-history-learning-development-20260904-004"
    )
    assessment = json.loads((artifact / "assessment.json").read_text(encoding="utf-8"))
    result = handoff.current_evidence_readiness(assessment)
    assert result["status"] == "abstained"
    assert result["verified_version_history_gross_speedup"] == pytest.approx(
        1.1375804204974516
    )
    assert result["query_ladder_q64_geomean_oracle_regret"] == pytest.approx(
        1.1078622156389766
    )
    assert result["query_ladder_metric_is_sum_based_charged_headroom"] is False
    assert result["blockers"] == [
        "insufficient_source_groups_by_split",
        "insufficient_source_groups_per_label",
        "protocol_not_frozen_before_current_labels",
        "query_ladder_sum_based_charged_headroom_missing",
        "query_ladder_cross_machine_replication_missing",
        "query_ladder_claim_boundary_forbids_learning",
        "fully_charged_cost_vector_incomplete",
        "recognition_timing_host_mismatch",
    ]
    assert result["development_training_eligible"] is False
    assert result["exact_fallback"] == "unchanged exact path"
