from __future__ import annotations

import copy
import json
import sys

import pytest

from cmbench.recognition import learning_benchmark_handoff as benchmark_handoff
from cmbench.recognition import query_ladder_development_experiment as experiment
from cmbench.recognition import query_ladder_learning_freeze as query_freeze
from scripts import cm_query_ladder_development_experiment as experiment_cli


ARTIFACT = (
    query_freeze.ROOT
    / "docs/recognition/runs/query-ladder-source-blind-learning-freeze-20260904-001"
)
LABELS = (
    "native_fused_slots",
    "cse_flat_bigint",
    "direct_bitset_restriction",
)


@pytest.fixture(scope="module")
def frozen_protocol() -> tuple[dict, str]:
    frozen = json.loads((ARTIFACT / "FREEZE.json").read_text(encoding="utf-8"))
    return frozen, query_freeze.file_sha256(ARTIFACT / "FREEZE.json")


def _replication(identifier: str, machine: str, frozen: dict) -> dict:
    row = {
        "replication_id": identifier,
        "physical_machine_sha256": machine * 64,
        "compiler_sha256": ("c" if identifier == "machine-a" else "d") * 64,
        "independent_verification_sha256": (
            "e" if identifier == "machine-a" else "f"
        ) * 64,
        "verification_status": "verified_complete",
        "case_set_sha256": frozen["cohort"]["case_set_sha256"],
        "label_table_sha256": "8" * 64,
        "complete_cases": 72,
        "best_fixed_method": "native_fused_slots",
        "best_fixed_sum_ns": 960_000.0,
        "oracle_sum_ns": 720_000.0,
        "gross_speedup": 0.0,
        "p95_costs_ns_per_case": {
            "feature_extraction_and_control": 100.0,
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
    economics = benchmark_handoff.replication_economics(row)
    row["gross_speedup"] = economics["gross_speedup"]
    row["fully_charged_speedup"] = economics["fully_charged_speedup"]
    return row


def _dataset_and_handoff(frozen: dict, freeze_sha256: str) -> tuple[dict, dict]:
    records = []
    counts: dict[str, int] = {}
    for index, row in enumerate(frozen["cohort"]["cases"]):
        label = LABELS[index % len(LABELS)]
        counts[label] = counts.get(label, 0) + 1
        records.append({
            "case_id": row["case_id"],
            "source_group_sha256": row["source_group_sha256"],
            "split": row["split"],
            "model_features": list(row["model_features"]),
            "label": label,
        })
    dataset = {
        "schema": experiment.DATASET_SCHEMA,
        "status": "verified_development_labels",
        "freeze_file_sha256": freeze_sha256,
        "case_set_sha256": frozen["cohort"]["case_set_sha256"],
        "label_table_sha256": "8" * 64,
        "records_sha256": query_freeze.digest(records),
        "prospective_cases_consumed": 0,
        "records": records,
    }
    handoff = {
        "schema": benchmark_handoff.SCHEMA,
        "status": "verified_complete",
        "surface_id": "architecture_query_ladder_q64",
        "task_contract_sha256": query_freeze.digest(frozen["exact_task_contract"]),
        "source_checkpoint": query_freeze.digest(frozen["source_checkpoint"]),
        "source_tree": frozen["source_closure_sha256"],
        "freeze_sha256": freeze_sha256,
        "baseline_closure": {
            "status": "verified_complete",
            "sha256": "5" * 64,
            "all_relevant_exact_baselines_included": True,
        },
        "cohort": {
            "role": "source_blind_development",
            "protocol_frozen_before_labels": True,
            "source_groups": 72,
            "source_groups_by_split": dict(
                frozen["cohort"]["source_group_counts_by_split"]
            ),
            "source_groups_per_label": counts,
            "cross_split_source_group_intersections": 0,
            "prospective_cases_consumed": 0,
            "case_set_sha256": frozen["cohort"]["case_set_sha256"],
            "label_table_sha256": "8" * 64,
        },
        "exact_methods": {
            "arms": list(query_freeze.EXACT_ARMS),
            "refused_rows_retained": True,
            "task_identical_exact_outputs": True,
        },
        "replications": [
            _replication("machine-a", "a", frozen),
            _replication("machine-b", "b", frozen),
        ],
        "claim_boundary": {
            "development_training_eligibility_permitted": True,
            "prospective_consumption_permitted": False,
            "production_routing_permitted": False,
        },
    }
    return dataset, handoff


def _predictions(
    frozen: dict,
    freeze_sha256: str,
    dataset: dict,
    *,
    perfect: bool,
    candidate_kind: str = "bounded_tree",
    training_seed: int | None = None,
) -> dict:
    label_by_case = {row["case_id"]: row["label"] for row in dataset["records"]}
    rows = [
        {
            "case_id": row["case_id"],
            "predicted_arm": (
                label_by_case[row["case_id"]] if perfect else LABELS[0]
            ),
        }
        for row in frozen["cohort"]["cases"]
    ]
    result = {
        "schema": experiment.PREDICTION_SCHEMA,
        "status": "development_candidate_predictions",
        "freeze_file_sha256": freeze_sha256,
        "label_table_sha256": dataset["label_table_sha256"],
        "candidate_id": (
            f"{candidate_kind}-test-seed-{training_seed}"
            if training_seed is not None
            else "bounded-tree-test-v1"
        ),
        "candidate_kind": candidate_kind,
        "feature_names": list(query_freeze.FEATURE_NAMES),
        "trained_on_splits": ["development_fit"],
        "validation_labels_visible_to_fit": False,
        "audit_labels_visible_to_fit": False,
        "prospective_cases_consumed": 0,
        "rows_sha256": query_freeze.digest(rows),
        "rows": rows,
    }
    if training_seed is not None:
        result["training_seed"] = training_seed
    return result


def _routing_evidence(
    frozen: dict,
    freeze_sha256: str,
    dataset: dict,
    handoff: dict,
    predictions: dict,
    *,
    inference_p95: float = 100.0,
) -> dict:
    labels = {row["case_id"]: row["label"] for row in dataset["records"]}
    medians = {}
    for case_id, label in labels.items():
        values = {arm: 20_000.0 for arm in query_freeze.EXACT_ARMS}
        values["native_fused_slots"] = 10_000.0 if label == "native_fused_slots" else 15_000.0
        values["cse_flat_bigint"] = 10_000.0 if label == "cse_flat_bigint" else 15_500.0
        values["direct_bitset_restriction"] = (
            10_000.0 if label == "direct_bitset_restriction" else 15_500.0
        )
        medians[case_id] = values
    hosts = []
    for index, replication in enumerate(handoff["replications"]):
        hosts.append({
            "replication_id": replication["replication_id"],
            "physical_machine_sha256": replication["physical_machine_sha256"],
            "independent_verification_sha256": replication[
                "independent_verification_sha256"
            ],
            "independent_routing_verification_sha256": str(index + 1) * 64,
            "case_set_sha256": frozen["cohort"]["case_set_sha256"],
            "label_table_sha256": dataset["label_table_sha256"],
            "prediction_rows_sha256": predictions["rows_sha256"],
            "p95_costs_measured_same_host": True,
            "candidate_inference_p95_ns_per_case": inference_p95,
            "fallback_dispatch_p95_ns_per_case": 100.0,
            "per_case_arm_medians_ns": copy.deepcopy(medians),
            "per_case_arm_medians_sha256": query_freeze.digest(medians),
            "schedule_mismatches": 0,
            "semantic_mismatches": 0,
            "source_or_artifact_mismatches": 0,
        })
    return {
        "schema": experiment.ROUTING_EVIDENCE_SCHEMA,
        "status": "verified_development_routing_evidence",
        "freeze_file_sha256": freeze_sha256,
        "case_set_sha256": frozen["cohort"]["case_set_sha256"],
        "label_table_sha256": dataset["label_table_sha256"],
        "prediction_rows_sha256": predictions["rows_sha256"],
        "prospective_cases_consumed": 0,
        "hosts": hosts,
    }


def test_eligible_fit_receives_only_identity_free_fit_rows(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    received = []

    def fitter(rows):
        received.extend(rows)
        return "model"

    assessment, model = experiment.fit_development_candidate_or_abstain(
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
        fitter=fitter,
    )
    assert assessment["status"] == "development_fit_completed"
    assert assessment["development_fit_rows"] == 40
    assert model == "model"
    assert received
    assert all(set(row) == {"model_features", "label"} for row in received)
    assert all(isinstance(row["model_features"], tuple) for row in received)
    assert assessment["production_routing_permitted"] is False


def test_ineligible_handoff_never_invokes_fitter(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    handoff["freeze_sha256"] = "0" * 64
    invoked = False

    def fitter(_rows):
        nonlocal invoked
        invoked = True

    assessment, model = experiment.fit_development_candidate_or_abstain(
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
        fitter=fitter,
    )
    assert invoked is False
    assert model is None
    assert assessment["status"] == "abstained"
    assert assessment["exact_fallback"] == "unchanged exact path"


@pytest.mark.parametrize("field", ["model_features", "split"])
def test_frozen_feature_or_split_tampering_never_invokes_fitter(
    frozen_protocol, field
):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    if field == "model_features":
        dataset["records"][0][field][0] += 1
    else:
        dataset["records"][0][field] = (
            "development_audit"
            if dataset["records"][0][field] != "development_audit"
            else "development_validation"
        )
    dataset["records_sha256"] = query_freeze.digest(dataset["records"])
    invoked = False

    def fitter(_rows):
        nonlocal invoked
        invoked = True

    assessment, model = experiment.fit_development_candidate_or_abstain(
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
        fitter=fitter,
    )
    assert invoked is False
    assert model is None
    assert assessment["status"] == "abstained"


def test_abstained_labels_are_retained_but_excluded_from_fit(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    fit_row = next(
        row for row in dataset["records"] if row["split"] == "development_fit"
    )
    old_label = fit_row["label"]
    fit_row["label"] = query_freeze.ABSTAIN_LABEL
    dataset["records_sha256"] = query_freeze.digest(dataset["records"])
    handoff["cohort"]["source_groups_per_label"][old_label] -= 1
    captured = []

    def fitter(rows):
        captured.extend(rows)
        return object()

    assessment, _model = experiment.fit_development_candidate_or_abstain(
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
        fitter=fitter,
    )
    assert assessment["development_fit_rows"] == 39
    assert all(row["label"] != query_freeze.ABSTAIN_LABEL for row in captured)


def test_perfect_predictions_beat_chance_majority_and_control(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    predictions = _predictions(
        frozen, freeze_sha256, dataset, perfect=True
    )
    result = experiment.assess_candidate_predictions(
        predictions,
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "development_signal_established"
    assert result["development_signal_established"] is True
    assert result["blockers"] == []
    for metrics in result["split_metrics"].values():
        assert metrics["candidate_accuracy"] == 1.0
        assert metrics["candidate_balanced_accuracy"] == 1.0
        assert metrics["balanced_chance_baseline"] == pytest.approx(1 / 3)
        assert metrics["all_development_labels_present"] is True
    assert result["advice_enabled"] is False
    assert result["production_routing_permitted"] is False


def test_majority_prediction_is_not_mistaken_for_learning(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    predictions = _predictions(
        frozen, freeze_sha256, dataset, perfect=False
    )
    result = experiment.assess_candidate_predictions(
        predictions,
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "development_signal_rejected"
    assert result["development_signal_established"] is False
    assert any(
        blocker.startswith("balanced_accuracy_below_threshold")
        for blocker in result["blockers"]
    )
    assert any(
        blocker.startswith("accuracy_does_not_beat_majority")
        for blocker in result["blockers"]
    )


def test_prediction_leakage_or_prospective_consumption_fails_closed(
    frozen_protocol,
):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    predictions = _predictions(
        frozen, freeze_sha256, dataset, perfect=True
    )
    predictions["audit_labels_visible_to_fit"] = True
    result = experiment.assess_candidate_predictions_or_abstain(
        predictions,
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "abstained"
    assert result["development_signal_established"] is False
    assert result["advice_enabled"] is False

    predictions["audit_labels_visible_to_fit"] = False
    dataset["prospective_cases_consumed"] = 1
    result = experiment.assess_candidate_predictions_or_abstain(
        predictions,
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "abstained"
    assert result["prospective_cases_consumed"] == 0


def test_prediction_digest_tampering_fails_closed(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    predictions = _predictions(
        frozen, freeze_sha256, dataset, perfect=True
    )
    predictions["rows"][0]["predicted_arm"] = "cse_flat_words"
    result = experiment.assess_candidate_predictions_or_abstain(
        predictions,
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "abstained"
    assert result["exact_fallback"] == "unchanged exact path"


def test_neural_signal_requires_three_independently_passing_seeds(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    predictions = [
        _predictions(
            frozen,
            freeze_sha256,
            dataset,
            perfect=True,
            candidate_kind="tiny_neural",
            training_seed=seed,
        )
        for seed in (11, 23, 47)
    ]
    result = experiment.assess_neural_seed_predictions(
        predictions,
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "replicated_development_signal_established"
    assert result["evaluated_training_seeds"] == [11, 23, 47]
    assert result["development_signal_established"] is True
    assert all(
        metrics["minimum_candidate_balanced_accuracy"] == 1.0
        for metrics in result["worst_case_split_metrics"].values()
    )


def test_neural_seed_instability_and_duplicate_seeds_fail_closed(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    predictions = [
        _predictions(
            frozen,
            freeze_sha256,
            dataset,
            perfect=index < 2,
            candidate_kind="tiny_neural",
            training_seed=seed,
        )
        for index, seed in enumerate((11, 23, 47))
    ]
    result = experiment.assess_neural_seed_predictions(
        predictions,
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "replicated_development_signal_rejected"
    assert any(blocker.startswith("seed_failed:47") for blocker in result["blockers"])

    predictions[2]["training_seed"] = 23
    result = experiment.assess_neural_seed_predictions_or_abstain(
        predictions,
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "abstained"
    assert result["development_signal_established"] is False


def test_read_only_cli_recomputes_prediction_assessment(
    frozen_protocol, monkeypatch, capsys
):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    predictions = _predictions(frozen, freeze_sha256, dataset, perfect=True)
    documents = {
        "freeze.json": frozen,
        "handoff.json": handoff,
        "dataset.json": dataset,
        "predictions.json": predictions,
    }
    monkeypatch.setattr(
        experiment_cli,
        "_read_json",
        lambda path: documents[path.name],
    )
    monkeypatch.setattr(query_freeze, "file_sha256", lambda _path: freeze_sha256)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cm_query_ladder_development_experiment.py",
            "--freeze",
            "freeze.json",
            "--handoff",
            "handoff.json",
            "--dataset",
            "dataset.json",
            "--predictions",
            "predictions.json",
        ],
    )
    assert experiment_cli.main() == 0
    assessment = json.loads(capsys.readouterr().out)
    assert assessment["status"] == "development_signal_established"

    documents["routing.json"] = _routing_evidence(
        frozen, freeze_sha256, dataset, handoff, predictions
    )
    sys.argv.extend(["--routing-evidence", "routing.json"])
    assert experiment_cli.main() == 0
    assessment = json.loads(capsys.readouterr().out)
    assert assessment["status"] == "development_routing_economics_passed"


def test_candidate_routing_economics_are_recomputed_on_every_host(
    frozen_protocol,
):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    predictions = _predictions(frozen, freeze_sha256, dataset, perfect=True)
    routing = _routing_evidence(
        frozen, freeze_sha256, dataset, handoff, predictions
    )
    result = experiment.assess_candidate_routing_economics(
        routing,
        predictions,
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "development_routing_economics_passed"
    assert result["development_routing_economics_passed"] is True
    assert set(result["host_economics"]) == {"machine-a", "machine-b"}
    for economics in result["host_economics"].values():
        assert economics["candidate_selected_exact_sum_ns"] == 720_000.0
        assert economics["candidate_fully_charged_speedup"] > 1.10
        assert economics["candidate_beats_analytical_control"] is True
    assert result["production_routing_permitted"] is False


def test_expensive_candidate_fails_even_with_perfect_accuracy(frozen_protocol):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    predictions = _predictions(frozen, freeze_sha256, dataset, perfect=True)
    routing = _routing_evidence(
        frozen,
        freeze_sha256,
        dataset,
        handoff,
        predictions,
        inference_p95=10_000.0,
    )
    result = experiment.assess_candidate_routing_economics(
        routing,
        predictions,
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "development_routing_economics_rejected"
    assert result["development_signal_established"] is True
    assert result["development_routing_economics_passed"] is False
    assert any(
        blocker.startswith("candidate_fully_charged_speedup_below_1_10")
        for blocker in result["blockers"]
    )


def test_routing_timing_tampering_and_cross_host_reuse_fail_closed(
    frozen_protocol,
):
    frozen, freeze_sha256 = frozen_protocol
    dataset, handoff = _dataset_and_handoff(frozen, freeze_sha256)
    predictions = _predictions(frozen, freeze_sha256, dataset, perfect=True)
    routing = _routing_evidence(
        frozen, freeze_sha256, dataset, handoff, predictions
    )
    case_id = next(iter(routing["hosts"][0]["per_case_arm_medians_ns"]))
    routing["hosts"][0]["per_case_arm_medians_ns"][case_id][
        "native_fused_slots"
    ] += 1.0
    result = experiment.assess_candidate_routing_economics_or_abstain(
        routing,
        predictions,
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "abstained"
    assert result["development_routing_economics_passed"] is False

    routing = _routing_evidence(
        frozen, freeze_sha256, dataset, handoff, predictions
    )
    routing["hosts"][1]["physical_machine_sha256"] = routing["hosts"][0][
        "physical_machine_sha256"
    ]
    result = experiment.assess_candidate_routing_economics_or_abstain(
        routing,
        predictions,
        dataset,
        handoff,
        frozen,
        freeze_file_sha256=freeze_sha256,
    )
    assert result["status"] == "abstained"
    assert result["exact_fallback"] == "unchanged exact path"
