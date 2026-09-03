from __future__ import annotations

import copy
from pathlib import Path

import pytest

from cmbench.recognition import version_history_learning_protocol as protocol


SOURCE_BINDINGS = {"synthetic/protocol.py": "a" * 64}
SOURCE_CHECKPOINT = "b" * 40


@pytest.fixture(scope="module")
def verified_bundle():
    return protocol.load_verified_benchmark_artifact()


@pytest.fixture(scope="module")
def verified_query_ladder():
    return protocol.load_verified_query_ladder_result()


@pytest.fixture(scope="module")
def rows_and_cases(verified_bundle):
    return protocol.build_source_blind_rows(verified_bundle)


@pytest.fixture(scope="module")
def timing(verified_bundle, rows_and_cases):
    _, cases = rows_and_cases
    surface = verified_bundle["assessment"]["surfaces"][protocol.SURFACE_ID]
    return protocol.benchmark_analytical_controls(
        cases,
        budget_ns_per_case=surface[
            "maximum_overhead_ns_per_case_preserving_1_10x"
        ],
        batches=5,
        repetitions=100,
    )


@pytest.fixture(scope="module")
def assessment(verified_bundle, verified_query_ladder, timing):
    return protocol.build_assessment(
        verified_bundle,
        verified_query_ladder,
        timing,
        source_bindings=SOURCE_BINDINGS,
        source_checkpoint=SOURCE_CHECKPOINT,
    )


def test_consumes_only_completed_independently_verified_benchmark(verified_bundle):
    assert verified_bundle["verification"]["status"] == "verified_no_training"
    assert verified_bundle["assessment"]["decision"]["training_allowed"] is False
    surface = verified_bundle["assessment"]["surfaces"][protocol.SURFACE_ID]
    assert surface["gross_headroom_speedup"] == pytest.approx(1.1375804204974516)
    assert surface["complete_cases"] == 3


def test_consumes_query_ladder_handoff_without_replaying_benchmark(
    verified_query_ladder,
):
    summary = verified_query_ladder["summary"]
    assert summary["status"] == "verified_interpretation_complete"
    assert summary["rows_checked"] == 27_648
    assert summary["q64_best_fixed_arm"] == "cse_flat_bigint"
    assert summary[
        "q64_best_fixed_case_median_geomean_slowdown_to_oracle"
    ] == pytest.approx(1.1078622156389766)
    assert summary["metric_is_sum_based_charged_headroom"] is False
    assert summary["selector_or_neural_claim_permitted"] is False
    assert summary["cross_machine_claim_permitted"] is False


def test_source_blind_features_exclude_identity_label_and_timing(rows_and_cases):
    rows, cases = rows_and_cases
    assert len(rows) == 3
    assert all(len(row["features"]) == len(protocol.FEATURE_NAMES) for row in rows)
    assert all(set(protocol.FORBIDDEN_MODEL_FIELDS).isdisjoint(protocol.FEATURE_NAMES)
               for _ in [0])
    scenario, trace = cases[0]
    renamed = copy.deepcopy(scenario)
    renamed["id"] = "different-source-name"
    renamed["source"] = {"kind": "renamed", "purpose": "must_not_enter_features"}
    assert protocol.extract_cheap_features(scenario, trace) == (
        protocol.extract_cheap_features(renamed, trace)
    )


def test_salted_source_group_splits_are_isolated_but_too_small(assessment):
    audit = assessment["dataset"]["split_audit"]
    assert audit["cross_split_source_group_intersections"] == 0
    assert audit["split_isolation_passed"] is True
    assert audit["minimum_split_sizes_passed"] is False
    assert assessment["gates"]["minimum_label_support"] is False


def test_analytical_controls_time_full_extraction_without_exact_execution(
    timing, assessment,
):
    assert timing["exact_backend_executions"] == 0
    assert timing["feature_extraction"]["p95_ns_per_case"] > 0
    assert set(timing["combined_feature_and_control"]) == set(protocol.CONTROLS)
    assert assessment["analytical_controls"][
        "bounded_control_matches_current_oracle_labels"
    ] is True
    assert assessment["analytical_controls"]["credit_toward_training_gate"] is False


def test_charged_economics_refuse_missing_costs():
    complete = {
        "feature_extraction_and_control": 1_000,
        "model_inference": 0,
        "exact_verification": 0,
        "expected_fallback": 0,
    }
    assert protocol.charged_speedup(
        best_fixed_ns=200,
        selected_exact_ns=100,
        cases=2,
        per_case_costs_ns=complete,
    ) == pytest.approx(200 / 2_100)
    incomplete = dict(complete)
    incomplete["exact_verification"] = None
    assert protocol.charged_speedup(
        best_fixed_ns=200,
        selected_exact_ns=100,
        cases=2,
        per_case_costs_ns=incomplete,
    ) is None
    invalid = dict(complete)
    invalid["expected_fallback"] = -1
    with pytest.raises(ValueError, match="invalid charged cost"):
        protocol.charged_speedup(
            best_fixed_ns=200,
            selected_exact_ns=100,
            cases=2,
            per_case_costs_ns=invalid,
        )


def test_training_and_advice_stay_disabled_after_gross_gate(assessment):
    assert assessment["gates"]["gross_exact_headroom_at_least_1_10"] is True
    assert assessment["gates"]["query_ladder_result_independently_verified"] is True
    assert assessment["gates"][
        "query_ladder_sum_based_charged_headroom_available"
    ] is False
    assert assessment["economics"]["fully_charged_speedup"] is None
    assert assessment["gates"][
        "all_recognition_verification_and_fallback_costs_measured"
    ] is False
    assert assessment["decision"]["training_allowed"] is False
    assert assessment["decision"]["selector_fitted"] is False
    assert assessment["decision"]["advice_enabled"] is False
    assert assessment["decision"]["complete_abstention"] is True


def test_missing_or_unverified_input_abstains(timing):
    missing = protocol.evaluate_or_abstain(
        Path("does-not-exist"),
        protocol.DEFAULT_QUERY_LADDER_ANALYSIS,
        timing,
        source_bindings=SOURCE_BINDINGS,
        source_checkpoint=SOURCE_CHECKPOINT,
    )
    assert missing == protocol.fail_closed_decision()
    missing_query_ladder = protocol.evaluate_or_abstain(
        protocol.DEFAULT_BENCHMARK_ARTIFACT,
        Path("does-not-exist-query-ladder"),
        timing,
        source_bindings=SOURCE_BINDINGS,
        source_checkpoint=SOURCE_CHECKPOINT,
    )
    assert missing_query_ladder == protocol.fail_closed_decision()


def test_tampered_benchmark_provenance_is_rejected(monkeypatch):
    original = protocol.file_sha256

    def tampered(path: Path) -> str:
        if path.name == "assessment.json" and path.parent == protocol.DEFAULT_BENCHMARK_ARTIFACT:
            return "0" * 64
        return original(path)

    monkeypatch.setattr(protocol, "file_sha256", tampered)
    with pytest.raises(ValueError, match="benchmark artifact hash mismatch"):
        protocol.load_verified_benchmark_artifact()


def test_tampered_independent_verification_is_rejected(monkeypatch):
    original = protocol._read_json

    def tampered(path: Path):
        value = original(path)
        if path.name == "independent_verification.json" and path.parent == (
            protocol.DEFAULT_BENCHMARK_ARTIFACT
        ):
            value = copy.deepcopy(value)
            value["status"] = "not_verified"
        return value

    monkeypatch.setattr(protocol, "_read_json", tampered)
    with pytest.raises(ValueError, match="independent verification boundary"):
        protocol.load_verified_benchmark_artifact()


def test_tampered_query_ladder_binding_is_rejected(monkeypatch):
    original = protocol.file_sha256

    def tampered(path: Path) -> str:
        if path.name == "raw_measurements.jsonl" and "query-ladder" in str(path):
            return "0" * 64
        return original(path)

    monkeypatch.setattr(protocol, "file_sha256", tampered)
    with pytest.raises(ValueError, match="query-ladder analysis evidence binding"):
        protocol.load_verified_query_ladder_result()


def test_tampered_split_assignment_and_economics_are_rejected(assessment):
    changed = copy.deepcopy(assessment)
    changed["dataset"]["rows"][0]["split"] = "development_audit"
    with pytest.raises(ValueError, match="split isolation"):
        protocol.validate_assessment(changed)

    changed = copy.deepcopy(assessment)
    changed["economics"]["fully_charged_speedup"] = 1.11
    changed["gates"]["fully_charged_speedup_at_least_1_10"] = True
    with pytest.raises(ValueError, match="charged economics boundary"):
        protocol.validate_assessment(changed)


def test_abstention_preserves_exact_fallback(assessment):
    calls = []

    def exact(value):
        calls.append(value)
        return {"exact": value * 2}

    expected = exact(7)
    calls.clear()
    actual = protocol.run_with_exact_fallback(assessment, exact, 7)
    assert actual == expected
    assert calls == [7]


def test_c5_requires_sound_global_certificate_and_material_work_avoidance():
    absent = assessment_record = {
        "certificate_present": False,
        "global_objective_bound_sound": False,
        "all_unexplored_partitions_covered": False,
        "checker_independent_of_model": False,
        "candidate_reconstruction_exact": True,
        "exact_fallback_unchanged": True,
        "completion_search_not_run": False,
        "measured_global_work_avoided_fraction": 0.0,
        "certificate_verification_ns_per_case": None,
        "adversarial_certificate_failures": None,
        "variable_renaming_failures": 0,
        "sharing_or_operand_order_failures": None,
    }
    assert protocol.evaluate_partition_certificate(absent)[
        "partition_learning_eligible"
    ] is False

    complete = dict(assessment_record)
    complete.update({
        "certificate_present": True,
        "global_objective_bound_sound": True,
        "all_unexplored_partitions_covered": True,
        "checker_independent_of_model": True,
        "completion_search_not_run": True,
        "measured_global_work_avoided_fraction": 0.25,
        "certificate_verification_ns_per_case": 100,
        "adversarial_certificate_failures": 0,
        "sharing_or_operand_order_failures": 0,
    })
    assert protocol.evaluate_partition_certificate(complete)[
        "partition_learning_eligible"
    ] is True
    complete["all_unexplored_partitions_covered"] = False
    assert protocol.evaluate_partition_certificate(complete)[
        "partition_learning_eligible"
    ] is False


def test_assessment_validation_and_report(assessment):
    protocol.validate_assessment(assessment)
    report = protocol.render_report(assessment)
    assert "training remains disabled" in report
    assert "No exact backend was executed" in report
    assert "C5 supplies no such certificate" in report
