from __future__ import annotations

import copy

import pytest

from cmbench.recognition import learning_benchmark_handoff as handoff
from cmbench.recognition import query_ladder_learning_evidence as evidence


@pytest.fixture(scope="module")
def completed_evidence() -> dict:
    return evidence.build_evidence()


def test_replays_verified_cross_machine_sum_economics(completed_evidence):
    evidence.validate_evidence(completed_evidence)
    hosts = completed_evidence["hosts"]
    assert set(hosts) == {"gcc_epyc_9655", "clang_epyc_9575f"}
    assert hosts["gcc_epyc_9655"]["best_fixed_method"] == "native_fused_slots"
    assert hosts["gcc_epyc_9655"]["best_fixed_sum_ns"] == 141_549_155.0
    assert hosts["gcc_epyc_9655"]["oracle_sum_ns"] == 127_998_459.5
    assert hosts["gcc_epyc_9655"]["gross_speedup"] == pytest.approx(
        1.1058660827085969
    )
    assert hosts["clang_epyc_9575f"]["best_fixed_method"] == "native_fused_slots"
    assert hosts["clang_epyc_9575f"]["best_fixed_sum_ns"] == 127_877_156.0
    assert hosts["clang_epyc_9575f"]["oracle_sum_ns"] == 114_731_375.5
    assert hosts["clang_epyc_9575f"]["gross_speedup"] == pytest.approx(
        1.1145787753586203
    )
    assert completed_evidence["cross_host"][
        "gross_headroom_at_least_1_10_on_both_hosts"
    ] is True


def test_records_cross_host_oracle_label_instability(completed_evidence):
    cross = completed_evidence["cross_host"]
    assert cross["label_agreement_cases"] == 53
    assert cross["label_disagreement_cases"] == 1
    assert cross["labels_identical"] is False
    assert cross["disagreements"] == {
        "fresh-high-sharing-andor-k11-r0": [
            "native_fused_slots",
            "cse_flat_bigint",
        ]
    }


def test_normalized_incomplete_handoff_reaches_gate_and_abstains(completed_evidence):
    normalized = evidence.normalize_incomplete_handoff(completed_evidence)
    handoff.validate_handoff(normalized)
    result = handoff.assess_query_ladder_evidence(completed_evidence)
    assert result["minimum_gross_speedup"] == pytest.approx(1.1058660827085969)
    assert result["gross_headroom_at_least_1_10_on_both_hosts"] is True
    assert result["minimum_fully_charged_speedup"] is None
    assert result["cross_host_label_disagreement_cases"] == 1
    assert result["status"] == "abstained"
    assert result["development_training_eligible"] is False
    assert "replication_label_table_mismatch" in result["blockers"]
    assert "protocol_not_frozen_before_labels" in result["blockers"]
    assert "fully_charged_cost_vector_incomplete:gcc_epyc_9655" in result[
        "blockers"
    ]
    assert "benchmark_claim_boundary_forbids_development_training" in result[
        "blockers"
    ]
    assert result["advice_enabled"] is False
    assert result["exact_fallback"] == "unchanged exact path"


def test_evidence_economics_tampering_is_rejected(completed_evidence):
    tampered = copy.deepcopy(completed_evidence)
    tampered["hosts"]["gcc_epyc_9655"]["gross_speedup"] = 9.0
    with pytest.raises(ValueError, match="host economics"):
        evidence.validate_evidence(tampered)


def test_missing_costs_are_allowed_only_on_incomplete_handoff(completed_evidence):
    normalized = evidence.normalize_incomplete_handoff(completed_evidence)
    normalized["status"] = "verified_complete"
    with pytest.raises(ValueError, match="economics replay"):
        handoff.validate_handoff(normalized)
