"""Fail-closed development evaluation for the frozen q64 learning surface.

This module deliberately does not train a model or execute an exact backend.
It binds future labels and candidate predictions to the pre-label source-blind
freeze, exposes only the fit split to a caller-supplied fitter, and evaluates
validation/audit predictions against chance, majority, and the frozen
analytical control.
"""
from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any, Callable, Mapping, Sequence

from cmbench.recognition import learning_benchmark_handoff as benchmark_handoff
from cmbench.recognition import query_ladder_learning_freeze as query_freeze


DATASET_SCHEMA = "crse-query-ladder-labeled-development-dataset/v1"
PREDICTION_SCHEMA = "crse-query-ladder-development-predictions/v1"
ASSESSMENT_SCHEMA = "crse-query-ladder-development-prediction-assessment/v1"
FIT_ASSESSMENT_SCHEMA = "crse-query-ladder-development-fit-assessment/v1"
NEURAL_ASSESSMENT_SCHEMA = "crse-query-ladder-neural-seed-assessment/v1"
ROUTING_EVIDENCE_SCHEMA = "crse-query-ladder-development-routing-evidence/v1"
ROUTING_ASSESSMENT_SCHEMA = "crse-query-ladder-development-routing-assessment/v1"
EVALUATION_SPLITS = ("development_validation", "development_audit")
MIN_NEURAL_TRAINING_SEEDS = 3
MIN_FULLY_CHARGED_SPEEDUP = 1.10
MIN_BALANCED_ACCURACY = 0.65
MIN_BALANCED_ACCURACY_ABOVE_CHANCE = 0.15
MIN_ACCURACY_ABOVE_MAJORITY = 0.10
MIN_BALANCED_ACCURACY_ABOVE_ANALYTICAL_CONTROL = 0.03
MIN_NON_ABSTAIN_COVERAGE = 0.80
SHA256 = re.compile(r"[0-9a-f]{64}")


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _safe_abstention(schema: str, blocker: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "status": "abstained",
        "blockers": [blocker],
        "development_fit_invoked": False,
        "development_signal_established": False,
        "training_performed": False,
        "prospective_cases_consumed": 0,
        "advice_enabled": False,
        "complete_abstention": True,
        "exact_fallback": "unchanged exact path",
        "production_routing_permitted": False,
    }


def validate_labeled_development_dataset(
    dataset: Mapping[str, Any],
    handoff: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> None:
    """Validate labels without allowing a new cohort or a changed feature view."""
    benchmark_handoff.validate_handoff_against_learning_freeze(
        handoff,
        freeze,
        freeze_file_sha256=freeze_file_sha256,
    )
    _require(
        dataset.get("schema") == DATASET_SCHEMA
        and dataset.get("status") == "verified_development_labels"
        and dataset.get("freeze_file_sha256") == freeze_file_sha256
        and dataset.get("case_set_sha256") == freeze["cohort"]["case_set_sha256"]
        and dataset.get("label_table_sha256")
        == handoff["cohort"]["label_table_sha256"]
        and dataset.get("prospective_cases_consumed") == 0,
        "development dataset identity",
    )
    records = dataset.get("records")
    _require(
        isinstance(records, list)
        and dataset.get("records_sha256") == query_freeze.digest(records),
        "development dataset records digest",
    )
    frozen_by_id = {
        row["case_id"]: row for row in freeze["cohort"]["cases"]
    }
    _require(
        len(records) == len(frozen_by_id)
        and len({row.get("case_id") for row in records if isinstance(row, Mapping)})
        == len(records)
        and {row.get("case_id") for row in records if isinstance(row, Mapping)}
        == set(frozen_by_id),
        "development dataset case closure",
    )
    labels = Counter()
    for row in records:
        _require(
            isinstance(row, Mapping)
            and set(row)
            == {
                "case_id",
                "source_group_sha256",
                "split",
                "model_features",
                "label",
            },
            "development dataset record shape",
        )
        frozen = frozen_by_id[row["case_id"]]
        _require(
            row["source_group_sha256"] == frozen["source_group_sha256"]
            and row["split"] == frozen["split"]
            and row["model_features"] == frozen["model_features"],
            "development dataset frozen feature or split mismatch",
        )
        _require(
            row["label"] in query_freeze.EXACT_ARMS
            or row["label"] == query_freeze.ABSTAIN_LABEL,
            "development dataset label",
        )
        if row["label"] != query_freeze.ABSTAIN_LABEL:
            labels[row["label"]] += 1
    _require(
        dict(sorted(labels.items()))
        == dict(sorted(handoff["cohort"]["source_groups_per_label"].items())),
        "development dataset label count binding",
    )


def validate_prediction_document(
    predictions: Mapping[str, Any],
    dataset: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> None:
    """Validate a complete, development-only prediction table."""
    _require(
        predictions.get("schema") == PREDICTION_SCHEMA
        and predictions.get("status") == "development_candidate_predictions"
        and predictions.get("freeze_file_sha256") == freeze_file_sha256
        and predictions.get("label_table_sha256")
        == dataset["label_table_sha256"]
        and predictions.get("feature_names")
        == freeze["model_input_contract"]["feature_names"]
        and predictions.get("trained_on_splits") == ["development_fit"]
        and predictions.get("validation_labels_visible_to_fit") is False
        and predictions.get("audit_labels_visible_to_fit") is False
        and predictions.get("prospective_cases_consumed") == 0
        and type(predictions.get("candidate_id")) is str
        and bool(predictions["candidate_id"])
        and predictions.get("candidate_kind")
        in {"analytical", "bounded_tree", "linear", "tiny_neural"},
        "prediction identity or isolation boundary",
    )
    _require(
        (
            predictions["candidate_kind"] == "tiny_neural"
            and type(predictions.get("training_seed")) is int
        )
        or (
            predictions["candidate_kind"] != "tiny_neural"
            and predictions.get("training_seed") is None
        ),
        "prediction training seed boundary",
    )
    rows = predictions.get("rows")
    _require(
        isinstance(rows, list)
        and predictions.get("rows_sha256") == query_freeze.digest(rows),
        "prediction rows digest",
    )
    case_ids = {row["case_id"] for row in freeze["cohort"]["cases"]}
    _require(
        len(rows) == len(case_ids)
        and all(
            isinstance(row, Mapping)
            and set(row) == {"case_id", "predicted_arm"}
            for row in rows
        )
        and {row["case_id"] for row in rows} == case_ids
        and len({row["case_id"] for row in rows}) == len(rows)
        and all(
            row["predicted_arm"] in query_freeze.EXACT_ARMS
            or row["predicted_arm"] == query_freeze.ABSTAIN_LABEL
            for row in rows
        ),
        "prediction case or arm closure",
    )


def _metrics(
    records: Sequence[Mapping[str, Any]],
    predicted_by_case: Mapping[str, str],
    analytical_by_case: Mapping[str, str],
    *,
    all_labels: Sequence[str],
) -> dict[str, Any]:
    labeled = [
        row for row in records if row["label"] != query_freeze.ABSTAIN_LABEL
    ]
    _require(labeled, "evaluation split has no non-abstain labels")
    present = sorted({row["label"] for row in labeled})
    correct = 0
    control_correct = 0
    covered = 0
    recalls: list[float] = []
    control_recalls: list[float] = []
    for label in all_labels:
        class_rows = [row for row in labeled if row["label"] == label]
        if not class_rows:
            continue
        recalls.append(
            sum(predicted_by_case[row["case_id"]] == label for row in class_rows)
            / len(class_rows)
        )
        control_recalls.append(
            sum(analytical_by_case[row["case_id"]] == label for row in class_rows)
            / len(class_rows)
        )
    for row in labeled:
        prediction = predicted_by_case[row["case_id"]]
        correct += prediction == row["label"]
        control_correct += analytical_by_case[row["case_id"]] == row["label"]
        covered += prediction != query_freeze.ABSTAIN_LABEL
    counts = Counter(row["label"] for row in labeled)
    accuracy = correct / len(labeled)
    balanced = sum(recalls) / len(recalls)
    control_balanced = sum(control_recalls) / len(control_recalls)
    majority = max(counts.values()) / len(labeled)
    chance = 1.0 / len(all_labels)
    required_balanced = max(
        MIN_BALANCED_ACCURACY,
        chance + MIN_BALANCED_ACCURACY_ABOVE_CHANCE,
    )
    return {
        "cases": len(records),
        "labeled_cases": len(labeled),
        "abstained_labels": len(records) - len(labeled),
        "labels_present": present,
        "all_development_labels_present": present == list(all_labels),
        "candidate_accuracy": accuracy,
        "candidate_balanced_accuracy": balanced,
        "candidate_non_abstain_coverage": covered / len(labeled),
        "balanced_chance_baseline": chance,
        "majority_accuracy_baseline": majority,
        "analytical_control_accuracy": control_correct / len(labeled),
        "analytical_control_balanced_accuracy": control_balanced,
        "required_balanced_accuracy": required_balanced,
        "accuracy_above_majority": accuracy - majority,
        "balanced_accuracy_above_analytical_control": balanced - control_balanced,
    }


def assess_candidate_predictions(
    predictions: Mapping[str, Any],
    dataset: Mapping[str, Any],
    handoff: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> dict[str, Any]:
    """Recompute the precommitted development-signal tests.

    Passing this assessment is evidence only for continued development.  It is
    never permission to use prospective data or change production routing.
    """
    readiness = benchmark_handoff.assess_frozen_handoff_or_abstain(
        handoff,
        freeze,
        freeze_file_sha256=freeze_file_sha256,
    )
    _require(readiness["development_training_eligible"], "handoff is not eligible")
    validate_labeled_development_dataset(
        dataset,
        handoff,
        freeze,
        freeze_file_sha256=freeze_file_sha256,
    )
    validate_prediction_document(
        predictions,
        dataset,
        freeze,
        freeze_file_sha256=freeze_file_sha256,
    )
    records = dataset["records"]
    predicted_by_case = {
        row["case_id"]: row["predicted_arm"] for row in predictions["rows"]
    }
    analytical_by_case = {
        row["case_id"]: row["analytical_control_arm"]
        for row in freeze["cohort"]["cases"]
    }
    all_labels = sorted({
        row["label"]
        for row in records
        if row["label"] != query_freeze.ABSTAIN_LABEL
    })
    _require(len(all_labels) >= 2, "fewer than two development labels")
    split_metrics = {}
    blockers: list[str] = []
    for split in EVALUATION_SPLITS:
        metrics = _metrics(
            [row for row in records if row["split"] == split],
            predicted_by_case,
            analytical_by_case,
            all_labels=all_labels,
        )
        split_metrics[split] = metrics
        if not metrics["all_development_labels_present"]:
            blockers.append(f"label_support_incomplete:{split}")
        if not math.isclose(
            metrics["balanced_chance_baseline"], 1.0 / len(all_labels)
        ):
            blockers.append(f"chance_baseline_replay_failed:{split}")
        if metrics["candidate_balanced_accuracy"] < metrics["required_balanced_accuracy"]:
            blockers.append(f"balanced_accuracy_below_threshold:{split}")
        if metrics["accuracy_above_majority"] < MIN_ACCURACY_ABOVE_MAJORITY:
            blockers.append(f"accuracy_does_not_beat_majority:{split}")
        if (
            metrics["balanced_accuracy_above_analytical_control"]
            < MIN_BALANCED_ACCURACY_ABOVE_ANALYTICAL_CONTROL
        ):
            blockers.append(f"does_not_beat_analytical_control:{split}")
        if metrics["candidate_non_abstain_coverage"] < MIN_NON_ABSTAIN_COVERAGE:
            blockers.append(f"coverage_below_threshold:{split}")
    signal = not blockers
    return {
        "schema": ASSESSMENT_SCHEMA,
        "status": (
            "development_signal_established" if signal else "development_signal_rejected"
        ),
        "candidate_id": predictions["candidate_id"],
        "candidate_kind": predictions["candidate_kind"],
        "thresholds": {
            "minimum_balanced_accuracy": MIN_BALANCED_ACCURACY,
            "minimum_balanced_accuracy_above_chance": (
                MIN_BALANCED_ACCURACY_ABOVE_CHANCE
            ),
            "minimum_accuracy_above_majority": MIN_ACCURACY_ABOVE_MAJORITY,
            "minimum_balanced_accuracy_above_analytical_control": (
                MIN_BALANCED_ACCURACY_ABOVE_ANALYTICAL_CONTROL
            ),
            "minimum_non_abstain_coverage": MIN_NON_ABSTAIN_COVERAGE,
        },
        "split_metrics": split_metrics,
        "blockers": blockers,
        "development_fit_invoked": False,
        "development_signal_established": signal,
        "training_performed": False,
        "prospective_cases_consumed": 0,
        "advice_enabled": False,
        "complete_abstention": not signal,
        "exact_fallback": "unchanged exact path",
        "production_routing_permitted": False,
    }


def assess_candidate_predictions_or_abstain(
    predictions: Mapping[str, Any],
    dataset: Mapping[str, Any],
    handoff: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> dict[str, Any]:
    try:
        return assess_candidate_predictions(
            predictions,
            dataset,
            handoff,
            freeze,
            freeze_file_sha256=freeze_file_sha256,
        )
    except (KeyError, TypeError, ValueError):
        return _safe_abstention(
            ASSESSMENT_SCHEMA,
            "malformed_unverified_ineligible_or_leaked_development_evidence",
        )


def assess_neural_seed_predictions(
    seed_predictions: Sequence[Mapping[str, Any]],
    dataset: Mapping[str, Any],
    handoff: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> dict[str, Any]:
    """Require the full development signal independently for three neural seeds."""
    _require(
        len(seed_predictions) >= MIN_NEURAL_TRAINING_SEEDS,
        "insufficient neural training seeds",
    )
    _require(
        all(row.get("candidate_kind") == "tiny_neural" for row in seed_predictions)
        and len({row.get("training_seed") for row in seed_predictions})
        == len(seed_predictions)
        and len({row.get("candidate_id") for row in seed_predictions})
        == len(seed_predictions),
        "neural seed identity closure",
    )
    assessments = [
        assess_candidate_predictions(
            predictions,
            dataset,
            handoff,
            freeze,
            freeze_file_sha256=freeze_file_sha256,
        )
        for predictions in seed_predictions
    ]
    blockers = [
        f"seed_failed:{predictions['training_seed']}:{blocker}"
        for predictions, assessment in zip(seed_predictions, assessments, strict=True)
        for blocker in assessment["blockers"]
    ]
    signal = not blockers
    worst_case = {
        split: {
            "minimum_candidate_accuracy": min(
                row["split_metrics"][split]["candidate_accuracy"]
                for row in assessments
            ),
            "minimum_candidate_balanced_accuracy": min(
                row["split_metrics"][split]["candidate_balanced_accuracy"]
                for row in assessments
            ),
            "minimum_candidate_non_abstain_coverage": min(
                row["split_metrics"][split]["candidate_non_abstain_coverage"]
                for row in assessments
            ),
            "minimum_accuracy_above_majority": min(
                row["split_metrics"][split]["accuracy_above_majority"]
                for row in assessments
            ),
            "minimum_balanced_accuracy_above_analytical_control": min(
                row["split_metrics"][split][
                    "balanced_accuracy_above_analytical_control"
                ]
                for row in assessments
            ),
        }
        for split in EVALUATION_SPLITS
    }
    return {
        "schema": NEURAL_ASSESSMENT_SCHEMA,
        "status": (
            "replicated_development_signal_established"
            if signal
            else "replicated_development_signal_rejected"
        ),
        "minimum_training_seeds": MIN_NEURAL_TRAINING_SEEDS,
        "evaluated_training_seeds": [
            row["training_seed"] for row in seed_predictions
        ],
        "per_seed_assessments": assessments,
        "worst_case_split_metrics": worst_case,
        "blockers": blockers,
        "development_fit_invoked": False,
        "development_signal_established": signal,
        "training_performed": False,
        "prospective_cases_consumed": 0,
        "advice_enabled": False,
        "complete_abstention": not signal,
        "exact_fallback": "unchanged exact path",
        "production_routing_permitted": False,
    }


def assess_neural_seed_predictions_or_abstain(
    seed_predictions: Sequence[Mapping[str, Any]],
    dataset: Mapping[str, Any],
    handoff: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> dict[str, Any]:
    try:
        return assess_neural_seed_predictions(
            seed_predictions,
            dataset,
            handoff,
            freeze,
            freeze_file_sha256=freeze_file_sha256,
        )
    except (KeyError, TypeError, ValueError):
        return _safe_abstention(
            NEURAL_ASSESSMENT_SCHEMA,
            "malformed_unverified_ineligible_or_unreplicated_neural_evidence",
        )


def validate_routing_evidence(
    routing_evidence: Mapping[str, Any],
    predictions: Mapping[str, Any],
    dataset: Mapping[str, Any],
    handoff: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> None:
    """Bind candidate timing and exact-arm medians to every handoff host."""
    validate_labeled_development_dataset(
        dataset,
        handoff,
        freeze,
        freeze_file_sha256=freeze_file_sha256,
    )
    validate_prediction_document(
        predictions,
        dataset,
        freeze,
        freeze_file_sha256=freeze_file_sha256,
    )
    _require(
        routing_evidence.get("schema") == ROUTING_EVIDENCE_SCHEMA
        and routing_evidence.get("status") == "verified_development_routing_evidence"
        and routing_evidence.get("freeze_file_sha256") == freeze_file_sha256
        and routing_evidence.get("case_set_sha256")
        == freeze["cohort"]["case_set_sha256"]
        and routing_evidence.get("label_table_sha256")
        == dataset["label_table_sha256"]
        and routing_evidence.get("prediction_rows_sha256")
        == predictions["rows_sha256"]
        and routing_evidence.get("prospective_cases_consumed") == 0,
        "routing evidence identity",
    )
    hosts = routing_evidence.get("hosts")
    replications = {
        row["replication_id"]: row for row in handoff["replications"]
    }
    _require(
        isinstance(hosts, list)
        and len(hosts) == len(replications)
        and {row.get("replication_id") for row in hosts if isinstance(row, Mapping)}
        == set(replications),
        "routing evidence host closure",
    )
    case_ids = {row["case_id"] for row in freeze["cohort"]["cases"]}
    for host in hosts:
        _require(
            isinstance(host, Mapping)
            and set(host)
            == {
                "replication_id",
                "physical_machine_sha256",
                "independent_verification_sha256",
                "independent_routing_verification_sha256",
                "case_set_sha256",
                "label_table_sha256",
                "prediction_rows_sha256",
                "p95_costs_measured_same_host",
                "candidate_inference_p95_ns_per_case",
                "fallback_dispatch_p95_ns_per_case",
                "per_case_arm_medians_ns",
                "per_case_arm_medians_sha256",
                "schedule_mismatches",
                "semantic_mismatches",
                "source_or_artifact_mismatches",
            },
            "routing evidence host shape",
        )
        replication = replications[host["replication_id"]]
        _require(
            host["physical_machine_sha256"]
            == replication["physical_machine_sha256"]
            and host["independent_verification_sha256"]
            == replication["independent_verification_sha256"]
            and SHA256.fullmatch(host["independent_routing_verification_sha256"])
            is not None
            and host["case_set_sha256"] == replication["case_set_sha256"]
            and host["label_table_sha256"] == replication["label_table_sha256"]
            and host["prediction_rows_sha256"] == predictions["rows_sha256"]
            and host["p95_costs_measured_same_host"] is True
            and all(
                host[name] == 0
                for name in (
                    "schedule_mismatches",
                    "semantic_mismatches",
                    "source_or_artifact_mismatches",
                )
            )
            and type(host["candidate_inference_p95_ns_per_case"]) in (int, float)
            and host["candidate_inference_p95_ns_per_case"] >= 0
            and type(host["fallback_dispatch_p95_ns_per_case"]) in (int, float)
            and host["fallback_dispatch_p95_ns_per_case"] >= 0,
            "routing evidence host binding or cost",
        )
        medians = host["per_case_arm_medians_ns"]
        _require(
            isinstance(medians, Mapping)
            and set(medians) == case_ids
            and host["per_case_arm_medians_sha256"] == query_freeze.digest(medians)
            and all(
                isinstance(values, Mapping)
                and set(values) == set(query_freeze.EXACT_ARMS)
                and all(
                    type(value) in (int, float)
                    and math.isfinite(value)
                    and value > 0
                    for value in values.values()
                )
                for values in medians.values()
            ),
            "routing exact-median table",
        )
        arm_sums = {
            arm: sum(medians[case_id][arm] for case_id in case_ids)
            for arm in query_freeze.EXACT_ARMS
        }
        oracle_sum = sum(min(medians[case_id].values()) for case_id in case_ids)
        best_fixed = min(
            query_freeze.EXACT_ARMS,
            key=lambda arm: (arm_sums[arm], query_freeze.EXACT_ARMS.index(arm)),
        )
        _require(
            best_fixed == replication["best_fixed_method"]
            and math.isclose(
                arm_sums[best_fixed],
                replication["best_fixed_sum_ns"],
                rel_tol=1e-15,
                abs_tol=1e-6,
            )
            and math.isclose(
                oracle_sum,
                replication["oracle_sum_ns"],
                rel_tol=1e-15,
                abs_tol=1e-6,
            ),
            "routing exact economics replay",
        )


def assess_candidate_routing_economics(
    routing_evidence: Mapping[str, Any],
    predictions: Mapping[str, Any],
    dataset: Mapping[str, Any],
    handoff: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> dict[str, Any]:
    """Recompute actual candidate routing economics, including abstention."""
    signal = assess_candidate_predictions(
        predictions,
        dataset,
        handoff,
        freeze,
        freeze_file_sha256=freeze_file_sha256,
    )
    _require(signal["development_signal_established"], "development signal failed")
    validate_routing_evidence(
        routing_evidence,
        predictions,
        dataset,
        handoff,
        freeze,
        freeze_file_sha256=freeze_file_sha256,
    )
    predicted = {
        row["case_id"]: row["predicted_arm"] for row in predictions["rows"]
    }
    labels = {row["case_id"]: row["label"] for row in dataset["records"]}
    analytical = {
        row["case_id"]: row["analytical_control_arm"]
        for row in freeze["cohort"]["cases"]
    }
    replications = {
        row["replication_id"]: row for row in handoff["replications"]
    }
    blockers: list[str] = []
    unstable_not_abstained = sorted(
        case_id
        for case_id, label in labels.items()
        if label == query_freeze.ABSTAIN_LABEL
        and predicted[case_id] != query_freeze.ABSTAIN_LABEL
    )
    if unstable_not_abstained:
        blockers.append("unstable_cross_host_labels_not_abstained")
    host_economics = {}
    for host in routing_evidence["hosts"]:
        replication = replications[host["replication_id"]]
        medians = host["per_case_arm_medians_ns"]
        best_fixed = replication["best_fixed_method"]
        candidate_exact_sum = 0.0
        analytical_exact_sum = 0.0
        candidate_abstentions = 0
        for case_id in sorted(medians):
            candidate_arm = predicted[case_id]
            if (
                candidate_arm == query_freeze.ABSTAIN_LABEL
                or labels[case_id] == query_freeze.ABSTAIN_LABEL
            ):
                candidate_arm = best_fixed
                candidate_abstentions += 1
            candidate_exact_sum += medians[case_id][candidate_arm]
            analytical_exact_sum += medians[case_id][analytical[case_id]]
        cases = len(medians)
        fixed_costs = replication["p95_costs_ns_per_case"]
        candidate_non_backend_p95 = (
            fixed_costs["feature_extraction_and_control"]
            + host["candidate_inference_p95_ns_per_case"]
            + fixed_costs["exact_verification"]
        )
        candidate_total = (
            candidate_exact_sum
            + cases * candidate_non_backend_p95
            + candidate_abstentions * host["fallback_dispatch_p95_ns_per_case"]
        )
        analytical_non_backend_p95 = (
            fixed_costs["feature_extraction_and_control"]
            + fixed_costs["exact_verification"]
        )
        analytical_total = (
            analytical_exact_sum + cases * analytical_non_backend_p95
        )
        candidate_speedup = replication["best_fixed_sum_ns"] / candidate_total
        analytical_speedup = replication["best_fixed_sum_ns"] / analytical_total
        host_economics[host["replication_id"]] = {
            "cases": cases,
            "best_fixed_method": best_fixed,
            "best_fixed_sum_ns": replication["best_fixed_sum_ns"],
            "oracle_sum_ns": replication["oracle_sum_ns"],
            "candidate_selected_exact_sum_ns": candidate_exact_sum,
            "candidate_abstentions": candidate_abstentions,
            "candidate_non_backend_p95_ns_per_case": candidate_non_backend_p95,
            "candidate_fully_charged_sum_ns": candidate_total,
            "candidate_fully_charged_speedup": candidate_speedup,
            "analytical_control_selected_exact_sum_ns": analytical_exact_sum,
            "analytical_control_non_backend_p95_ns_per_case": (
                analytical_non_backend_p95
            ),
            "analytical_control_fully_charged_sum_ns": analytical_total,
            "analytical_control_fully_charged_speedup": analytical_speedup,
            "candidate_beats_analytical_control": candidate_total < analytical_total,
        }
        if candidate_speedup < MIN_FULLY_CHARGED_SPEEDUP:
            blockers.append(
                f"candidate_fully_charged_speedup_below_1_10:{host['replication_id']}"
            )
        if candidate_total >= analytical_total:
            blockers.append(
                f"candidate_does_not_beat_analytical_control:{host['replication_id']}"
            )
    eligible = not blockers
    return {
        "schema": ROUTING_ASSESSMENT_SCHEMA,
        "status": (
            "development_routing_economics_passed"
            if eligible
            else "development_routing_economics_rejected"
        ),
        "minimum_fully_charged_speedup": MIN_FULLY_CHARGED_SPEEDUP,
        "host_economics": host_economics,
        "blockers": blockers,
        "development_fit_invoked": False,
        "development_signal_established": signal["development_signal_established"],
        "development_routing_economics_passed": eligible,
        "training_performed": False,
        "prospective_cases_consumed": 0,
        "advice_enabled": False,
        "complete_abstention": not eligible,
        "exact_fallback": "unchanged exact path",
        "production_routing_permitted": False,
    }


def assess_candidate_routing_economics_or_abstain(
    routing_evidence: Mapping[str, Any],
    predictions: Mapping[str, Any],
    dataset: Mapping[str, Any],
    handoff: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
) -> dict[str, Any]:
    try:
        return assess_candidate_routing_economics(
            routing_evidence,
            predictions,
            dataset,
            handoff,
            freeze,
            freeze_file_sha256=freeze_file_sha256,
        )
    except (KeyError, TypeError, ValueError):
        result = _safe_abstention(
            ROUTING_ASSESSMENT_SCHEMA,
            "malformed_unverified_ineligible_or_economically_incomplete_routing_evidence",
        )
        result["development_routing_economics_passed"] = False
        return result


def fit_development_candidate_or_abstain(
    dataset: Mapping[str, Any],
    handoff: Mapping[str, Any],
    freeze: Mapping[str, Any],
    *,
    freeze_file_sha256: str,
    fitter: Callable[[Sequence[Mapping[str, Any]]], Any],
) -> tuple[dict[str, Any], Any | None]:
    """Invoke a fitter only after the exact gate, with identity-free fit rows."""
    readiness = benchmark_handoff.assess_frozen_handoff_or_abstain(
        handoff,
        freeze,
        freeze_file_sha256=freeze_file_sha256,
    )
    if not readiness["development_training_eligible"]:
        return (
            _safe_abstention(FIT_ASSESSMENT_SCHEMA, "handoff_not_eligible"),
            None,
        )
    try:
        validate_labeled_development_dataset(
            dataset,
            handoff,
            freeze,
            freeze_file_sha256=freeze_file_sha256,
        )
        fit_rows = tuple(
            {
                "model_features": tuple(row["model_features"]),
                "label": row["label"],
            }
            for row in dataset["records"]
            if row["split"] == "development_fit"
            and row["label"] != query_freeze.ABSTAIN_LABEL
        )
        _require(fit_rows, "empty development fit set")
    except (KeyError, TypeError, ValueError):
        return (
            _safe_abstention(
                FIT_ASSESSMENT_SCHEMA,
                "malformed_unverified_or_leaked_development_dataset",
            ),
            None,
        )
    model = fitter(fit_rows)
    return (
        {
            "schema": FIT_ASSESSMENT_SCHEMA,
            "status": "development_fit_completed",
            "blockers": [],
            "development_fit_invoked": True,
            "development_fit_rows": len(fit_rows),
            "fit_row_fields": ["model_features", "label"],
            "abstained_labels_excluded_from_fit": True,
            "training_performed": True,
            "prospective_cases_consumed": 0,
            "advice_enabled": False,
            "complete_abstention": False,
            "exact_fallback": "unchanged exact path",
            "production_routing_permitted": False,
        },
        model,
    )
