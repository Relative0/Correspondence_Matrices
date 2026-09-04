from __future__ import annotations

import copy
import json
import subprocess

import pytest

from cmbench.recognition import query_ladder_learning_freeze as freeze


ARTIFACT = (
    freeze.ROOT
    / "docs/recognition/runs/query-ladder-source-blind-learning-freeze-20260904-001"
)


@pytest.fixture(scope="module")
def frozen_protocol() -> dict:
    checkpoint = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=freeze.ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return freeze.build_freeze(
        project_root=freeze.ROOT,
        source_checkpoint=checkpoint,
    )


def _host(winner: str, runner: str, *, winner_ns=100.0, runner_ns=110.0):
    values = {arm: [200.0] * freeze.REPETITIONS for arm in freeze.EXACT_ARMS}
    values[winner] = [winner_ns] * freeze.REPETITIONS
    values[runner] = [runner_ns] * freeze.REPETITIONS
    return values


def test_freezes_new_source_blind_cohort_and_isolated_splits(frozen_protocol):
    freeze.validate_freeze(frozen_protocol)
    cohort = frozen_protocol["cohort"]
    assert cohort["case_count"] == 72
    assert cohort["source_groups"] == 72
    assert cohort["source_group_counts_by_split"] == {
        "development_fit": 40,
        "development_validation": 16,
        "development_audit": 16,
    }
    groups = [
        set(cohort["source_groups_by_split"][name])
        for name in freeze.SPLIT_COUNTS
    ]
    assert not groups[0] & groups[1]
    assert not groups[0] & groups[2]
    assert not groups[1] & groups[2]
    assert cohort["prior_alpha_structural_overlap_count"] == 0
    assert cohort["labels_produced"] is False
    assert cohort["prospective_cases_consumed"] == 0


def test_model_features_replay_without_identity_or_timing_fields(frozen_protocol):
    model = frozen_protocol["model_input_contract"]
    assert model["feature_names"] == list(freeze.FEATURE_NAMES)
    assert set(model["feature_names"]).isdisjoint(freeze.FORBIDDEN_MODEL_FIELDS)
    for row in frozen_protocol["cohort"]["cases"]:
        expected = freeze.extract_routing_features(
            row["expression_v2"], n_vars=row["n_vars"]
        )
        assert row["model_features"] == list(expected)
        assert row["model_features_sha256"] == freeze.digest(list(expected))
        assert row["analytical_control_arm"] in freeze.EXACT_ARMS


def test_clear_cross_host_label_is_accepted():
    timings = {
        "machine-a": _host("native_fused_slots", "cse_flat_bigint"),
        "machine-b": _host("native_fused_slots", "cse_flat_bigint"),
    }
    assert freeze.label_from_cross_host_blocks(timings) == "native_fused_slots"


def test_near_tie_abstains():
    timings = {
        "machine-a": _host(
            "native_fused_slots", "cse_flat_bigint", runner_ns=102.0
        ),
        "machine-b": _host(
            "native_fused_slots", "cse_flat_bigint", runner_ns=102.0
        ),
    }
    assert freeze.label_from_cross_host_blocks(timings) == freeze.ABSTAIN_LABEL


def test_cross_host_winner_disagreement_abstains():
    timings = {
        "machine-a": _host("native_fused_slots", "cse_flat_bigint"),
        "machine-b": _host("cse_flat_bigint", "native_fused_slots"),
    }
    assert freeze.label_from_cross_host_blocks(timings) == freeze.ABSTAIN_LABEL


def test_block_instability_abstains_even_when_medians_pass():
    unstable = _host("native_fused_slots", "cse_flat_bigint")
    unstable["cse_flat_bigint"][:4] = [90.0] * 4
    timings = {
        "machine-a": unstable,
        "machine-b": _host("native_fused_slots", "cse_flat_bigint"),
    }
    assert freeze.label_from_cross_host_blocks(timings) == freeze.ABSTAIN_LABEL


def test_charged_path_components_are_bounded_to_exact_arms(frozen_protocol):
    features = frozen_protocol["cohort"]["cases"][0]["model_features"]
    control = freeze.analytical_control(features)
    inferred = freeze.bounded_model_inference(features)
    assert control in freeze.EXACT_ARMS
    assert inferred in freeze.EXACT_ARMS
    assert freeze.verify_exact_arm_selection(inferred) is True
    assert freeze.verify_exact_arm_selection("not-an-exact-arm") is False
    assert freeze.fallback_dispatch(None) == "native_fused_slots"
    assert freeze.fallback_dispatch(inferred) == inferred


def test_charged_cost_harness_executes_no_exact_backend(frozen_protocol):
    result = freeze.measure_charged_cost_components(
        frozen_protocol["cohort"]["cases"][:2],
        batches=5,
        repetitions=1,
    )
    assert result["schema"] == "crse-query-ladder-charged-cost-components/v1"
    assert set(result["p95_ns_per_case"]) == {
        "feature_extraction_and_control",
        "model_inference",
        "exact_verification",
        "fallback_dispatch",
    }
    assert all(value > 0 for value in result["p95_ns_per_case"].values())
    assert result["exact_backend_executions"] == 0
    assert result["labels_consumed"] == 0


def test_expected_fallback_charges_abstention_regret_and_dispatch():
    timings = {
        "case-a": {arm: 200.0 for arm in freeze.EXACT_ARMS},
        "case-b": {arm: 200.0 for arm in freeze.EXACT_ARMS},
    }
    timings["case-a"]["native_fused_slots"] = 100.0
    timings["case-a"]["cse_flat_bigint"] = 120.0
    timings["case-b"]["native_fused_slots"] = 130.0
    timings["case-b"]["cse_flat_bigint"] = 100.0
    cost = freeze.expected_fallback_cost_ns_per_case(
        labels={
            "case-a": "native_fused_slots",
            "case-b": freeze.ABSTAIN_LABEL,
        },
        per_case_arm_medians_ns=timings,
        best_fixed_arm="native_fused_slots",
        fallback_dispatch_p95_ns=10.0,
    )
    assert cost == pytest.approx(20.0)


def test_feature_or_split_tampering_is_rejected(frozen_protocol):
    tampered = copy.deepcopy(frozen_protocol)
    tampered["cohort"]["cases"][0]["model_features"][0] += 1
    core = {key: value for key, value in tampered.items() if key != "freeze_sha256"}
    tampered["freeze_sha256"] = freeze.digest(core)
    with pytest.raises(ValueError, match="cohort boundary|model input boundary"):
        freeze.validate_freeze(tampered)


def test_source_closed_independent_replay(frozen_protocol):
    result = freeze.verify_freeze(frozen_protocol, freeze.ROOT)
    assert result["status"] == "verified_source_blind_freeze_no_labels"
    assert result["cohort_replayed_byte_identically"] is True
    assert result["label_policy_frozen_before_timings"] is True
    assert result["exact_backend_executions"] == 0
    assert result["timing_rows_produced"] == 0
    assert result["labels_produced"] == 0
    assert result["models_trained"] == 0
    assert result["prospective_cases_consumed"] == 0
    assert result["runpod_resources_created"] == 0


def test_canonical_freeze_artifact_is_independently_verified():
    frozen = json.loads((ARTIFACT / "FREEZE.json").read_text(encoding="utf-8"))
    manifest = json.loads((ARTIFACT / "MANIFEST.json").read_text(encoding="utf-8"))
    verification = json.loads(
        (ARTIFACT / "INDEPENDENT_VERIFICATION.json").read_text(encoding="utf-8")
    )
    assert manifest["schema"] == freeze.MANIFEST_SCHEMA
    assert freeze.file_sha256(ARTIFACT / "FREEZE.json") == manifest["artifacts"][
        "FREEZE.json"
    ]
    assert freeze.file_sha256(ARTIFACT / "REPORT.md") == manifest["artifacts"][
        "REPORT.md"
    ]
    assert verification["status"] == "verified_source_blind_freeze_no_labels"
    assert verification["freeze_file_sha256"] == manifest["artifacts"]["FREEZE.json"]
    assert verification["manifest_sha256"] == freeze.file_sha256(
        ARTIFACT / "MANIFEST.json"
    )
    assert verification["exact_backend_executions"] == 0
    assert verification["labels_produced"] == 0
    assert verification["models_trained"] == 0
    freeze.verify_freeze(frozen, freeze.ROOT)
