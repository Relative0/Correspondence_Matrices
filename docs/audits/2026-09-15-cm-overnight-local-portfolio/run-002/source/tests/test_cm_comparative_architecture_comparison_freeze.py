from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cmbench.comparative import architecture_comparison_freeze as freeze


ROOT = Path(__file__).resolve().parents[1]


def _build():
    return freeze.build_freeze(
        project_root=ROOT,
        source_checkpoint="4c88b8269836c8568d0ff7a8d18ad2a7827c2471",
    )


def test_fresh_structural_corpus_is_deterministic_source_blind_and_balanced():
    result = _build()
    fresh = result["fresh_corpus"]
    assert len(fresh["single_root_cases"]) == 36
    assert len(fresh["multi_root_cases"]) == 6
    assert len(fresh["history_pairs"]) == 6
    assert fresh["truth_outputs_inspected"] is False
    assert fresh["method_outputs_inspected"] is False
    assert fresh["method_timings_inspected"] is False
    assert {row["shape"] for row in fresh["single_root_cases"]} == {"tree", "high_sharing"}
    assert all(
        row["union_nodes"] < row["sum_separate_nodes"]
        for row in fresh["multi_root_cases"]
    )
    assert result == _build()


def test_observed_regressions_and_current_arms_are_bound_without_reusing_results():
    result = _build()
    assert set(result["observed_regression_bindings"]) == set(freeze.OBSERVED_SOURCES)
    assert result["observed_regression_bindings"]["public_complete_relation_regression"]["case_count"] > 0
    assert set(result["arm_configurations"]) == {"A", "B", "C", "D"}
    assert result["schedules"]["B"]["query_counts"] == [1, 4, 16, 64]
    assert result["publication_gates"]["historical_1_472x_retained_as_windows_only"] is True


def test_freeze_does_not_authorize_timing_cloud_training_or_publication():
    result = _build()
    assert result["status"] == "frozen_not_authorized"
    assert result["permissions"]["source_identity_freeze_complete"] is True
    assert all(
        value is False
        for name, value in result["permissions"].items()
        if name not in {"source_identity_freeze_complete", "local_functional_replay"}
    )
    assert result["timing_evidence_produced"] is False
    assert result["cloud_resource_created"] is False


def test_tampered_freeze_fails_closed():
    result = _build()
    mutations = []
    changed = copy.deepcopy(result)
    changed["permissions"]["runpod_execution"] = True
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["fresh_corpus"]["method_timings_inspected"] = True
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["fresh_corpus"]["single_root_cases"][0]["case_id"] = "tampered"
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["schedules"]["A"]["arm_orders"][0].reverse()
    mutations.append(changed)
    for item in mutations:
        with pytest.raises(ValueError):
            freeze.validate_freeze(item)


def test_checked_in_historical_freeze_is_self_consistent():
    artifact = ROOT / "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json"
    if not artifact.exists():
        pytest.skip("freeze artifact not generated yet")
    recorded = json.loads(artifact.read_text(encoding="utf-8"))
    verification = json.loads(
        artifact.with_name("VERIFICATION.json").read_text(encoding="utf-8")
    )
    assert freeze.validate_freeze(recorded) == recorded
    assert verification["status"] == "verified_frozen_not_authorized"
    assert verification["freeze_sha256"] == recorded["freeze_sha256"]
    assert verification["source_closure_match"] is True
    assert verification["replay_byte_identical"] is True


def test_live_freeze_verification_still_fails_closed_on_source_drift(monkeypatch):
    recorded = _build()
    original = freeze._file_identity

    def drifted_identity(root, relative):
        identity = original(root, relative)
        if relative == freeze.SOURCE_CLOSURE_PATHS[0]:
            return {**identity, "sha256": "0" * 64}
        return identity

    monkeypatch.setattr(freeze, "_file_identity", drifted_identity)
    with pytest.raises(ValueError, match="freeze verification"):
        freeze.verify_freeze(recorded, ROOT)
