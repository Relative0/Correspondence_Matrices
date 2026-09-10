"""Fail-closed development assessment for memory-aware exact-arm learning.

This module validates already measured memory evidence and candidate prediction
documents.  It never measures a process, executes an exact backend, fits a model,
or changes routing.  Its thresholds intentionally mirror the useful H6 estimator
checks while requiring a source-blind, split-isolated, multi-host decision surface.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
import hashlib
import json
import math
import statistics
from typing import Any, Mapping, Sequence

from cmbench.recognition import version_history_learning_protocol as history


MEASUREMENT_SCHEMA = "crse-memory-learning-measurements/v1"
PREDICTION_SCHEMA = "crse-memory-learning-predictions/v1"
NEURAL_PROTOCOL_SCHEMA = "crse-memory-learning-neural-protocol/v1"
SURFACE_ASSESSMENT_SCHEMA = "crse-memory-learning-surface-assessment/v1"
PREDICTION_ASSESSMENT_SCHEMA = "crse-memory-learning-prediction-assessment/v1"
NEURAL_ASSESSMENT_SCHEMA = "crse-memory-learning-neural-seed-assessment/v1"
ABSTAIN_LABEL = "__abstain__"
EVALUATION_SPLITS = ("development_validation", "development_audit")
MIN_NEURAL_TRAINING_SEEDS = 3
MIN_NON_ABSTAIN_COVERAGE = 0.80
MAX_MATERIAL_UNDERPREDICTION_PREVALENCE = 0.20
MAX_MEDIAN_OVERPREDICTION_FACTOR = 2.0
MIN_PAIRWISE_ORDER_AGREEMENT = 0.70
MIN_NEAR_MINIMUM_SELECTION_PREVALENCE = 0.80
HEX = frozenset("0123456789abcdef")


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _hash(value: Any, label: str) -> str:
    _require(
        type(value) is str and len(value) == 64 and set(value) <= HEX,
        f"invalid SHA-256: {label}",
    )
    return value


def _finite_nonnegative(value: Any, label: str) -> float:
    _require(
        type(value) in (int, float) and math.isfinite(value) and value >= 0,
        f"invalid nonnegative value: {label}",
    )
    return float(value)


def _safe_abstention(schema: str, blocker: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "status": "abstained",
        "blockers": [blocker],
        "development_signal_established": False,
        "training_performed": False,
        "prospective_cases_consumed": 0,
        "advice_enabled": False,
        "complete_abstention": True,
        "exact_fallback": "unchanged exact path",
        "production_routing_permitted": False,
    }


def validate_measurements(document: Mapping[str, Any]) -> None:
    """Validate a source-blind, multi-host memory decision surface."""
    _require(
        isinstance(document, Mapping)
        and set(document)
        == {
            "schema",
            "status",
            "surface_id",
            "task_contract_sha256",
            "case_set_sha256",
            "metric",
            "protocol",
            "arms",
            "hosts",
            "cases_sha256",
            "cases",
        }
        and document.get("schema") == MEASUREMENT_SCHEMA
        and document.get("status") in {"verified_complete", "incomplete"}
        and type(document.get("surface_id")) is str
        and bool(document["surface_id"]),
        "memory measurement identity",
    )
    _hash(document["task_contract_sha256"], "task contract")
    _hash(document["case_set_sha256"], "case set")
    metric = document["metric"]
    _require(
        isinstance(metric, Mapping)
        and set(metric)
        == {
            "name",
            "unit",
            "lifecycle",
            "optimization",
            "resolution_floor_bytes",
            "minimum_relative_runner_up_gap",
        }
        and type(metric.get("name")) is str
        and bool(metric["name"])
        and metric.get("unit") == "bytes"
        and type(metric.get("lifecycle")) is str
        and bool(metric["lifecycle"])
        and metric.get("optimization") == "minimize"
        and type(metric.get("resolution_floor_bytes")) is int
        and metric["resolution_floor_bytes"] > 0
        and type(metric.get("minimum_relative_runner_up_gap")) in (int, float)
        and math.isfinite(metric["minimum_relative_runner_up_gap"])
        and metric["minimum_relative_runner_up_gap"] >= 0,
        "memory metric contract",
    )
    protocol = document["protocol"]
    _require(
        isinstance(protocol, Mapping)
        and set(protocol)
        == {
            "role",
            "frozen_before_targets",
            "source_group_split_isolated",
            "prospective_cases_consumed",
            "exact_outputs_verified",
            "refused_rows_retained",
        }
        and protocol.get("role")
        in {"source_blind_development", "retrospective_development"}
        and all(
            type(protocol.get(name)) is bool
            for name in (
                "frozen_before_targets",
                "source_group_split_isolated",
                "exact_outputs_verified",
                "refused_rows_retained",
            )
        )
        and type(protocol.get("prospective_cases_consumed")) is int
        and protocol["prospective_cases_consumed"] >= 0,
        "memory protocol boundary",
    )
    arms = document["arms"]
    _require(
        type(arms) is list
        and len(arms) >= 2
        and len(set(arms)) == len(arms)
        and all(type(arm) is str and arm for arm in arms),
        "memory arm closure",
    )
    hosts = document["hosts"]
    _require(type(hosts) is list and len(hosts) >= 2, "memory host closure")
    host_ids: set[str] = set()
    machines: set[str] = set()
    verifications: set[str] = set()
    for host in hosts:
        _require(
            isinstance(host, Mapping)
            and set(host)
            == {
                "replication_id",
                "physical_machine_sha256",
                "independent_verification_sha256",
            }
            and type(host.get("replication_id")) is str
            and bool(host["replication_id"])
            and host["replication_id"] not in host_ids,
            "memory host identity",
        )
        host_ids.add(host["replication_id"])
        machines.add(_hash(host["physical_machine_sha256"], "physical machine"))
        verifications.add(
            _hash(host["independent_verification_sha256"], "memory verification")
        )
    _require(
        len(machines) == len(hosts) and len(verifications) == len(hosts),
        "memory host or verification independence",
    )
    cases = document["cases"]
    _require(
        type(cases) is list
        and bool(cases)
        and document["cases_sha256"] == digest(cases),
        "memory cases digest",
    )
    case_ids: set[str] = set()
    source_groups: set[str] = set()
    identities = []
    allowed_splits = set(history.MIN_SPLIT_SOURCE_GROUPS)
    for case in cases:
        _require(
            isinstance(case, Mapping)
            and set(case)
            == {
                "case_id",
                "source_group_sha256",
                "split",
                "measurements_by_host",
            }
            and type(case.get("case_id")) is str
            and bool(case["case_id"])
            and case["case_id"] not in case_ids
            and case.get("split") in allowed_splits,
            "memory case identity",
        )
        case_ids.add(case["case_id"])
        source_group = _hash(case["source_group_sha256"], "source group")
        _require(source_group not in source_groups, "duplicate memory source group")
        source_groups.add(source_group)
        measurements = case["measurements_by_host"]
        _require(
            isinstance(measurements, Mapping)
            and set(measurements) == host_ids
            and all(
                isinstance(values, Mapping)
                and set(values) == set(arms)
                and all(
                    _finite_nonnegative(value, f"memory:{arm}") >= 0
                    for arm, value in values.items()
                )
                for values in measurements.values()
            ),
            "memory case measurement closure",
        )
        identities.append({
            "case_id": case["case_id"],
            "source_group_sha256": source_group,
            "split": case["split"],
        })
    _require(document["case_set_sha256"] == digest(identities), "memory case-set digest")


def _material_winner(
    values: Mapping[str, Any],
    arms: Sequence[str],
    *,
    resolution_floor: int,
    relative_gap: float,
) -> str | None:
    ranked = sorted(arms, key=lambda arm: (float(values[arm]), arms.index(arm)))
    winner, runner_up = ranked[:2]
    best = float(values[winner])
    second = float(values[runner_up])
    absolute_pass = second - best >= resolution_floor
    relative_pass = best == 0 or (second - best) / best >= relative_gap
    return winner if absolute_pass and relative_pass else None


def assess_decision_surface(document: Mapping[str, Any]) -> dict[str, Any]:
    """Derive only stable, materially separated cross-host labels."""
    validate_measurements(document)
    arms = document["arms"]
    metric = document["metric"]
    protocol = document["protocol"]
    floor = metric["resolution_floor_bytes"]
    relative_gap = float(metric["minimum_relative_runner_up_gap"])
    labels = []
    disagreement_cases = []
    threshold_abstention_cases = []
    for case in document["cases"]:
        winners = [
            _material_winner(
                case["measurements_by_host"][host["replication_id"]],
                arms,
                resolution_floor=floor,
                relative_gap=relative_gap,
            )
            for host in document["hosts"]
        ]
        if None in winners:
            label = ABSTAIN_LABEL
            threshold_abstention_cases.append(case["case_id"])
        elif len(set(winners)) != 1:
            label = ABSTAIN_LABEL
            disagreement_cases.append(case["case_id"])
        else:
            label = winners[0]
        labels.append({
            "case_id": case["case_id"],
            "source_group_sha256": case["source_group_sha256"],
            "split": case["split"],
            "label": label,
        })
    non_abstain = [row for row in labels if row["label"] != ABSTAIN_LABEL]
    label_counts = Counter(row["label"] for row in non_abstain)
    split_counts = Counter(row["split"] for row in labels)
    usable_by_split = Counter(row["split"] for row in non_abstain)
    coverage = len(non_abstain) / len(labels)
    coverage_by_split = {
        split: usable_by_split[split] / split_counts[split] if split_counts[split] else 0.0
        for split in history.MIN_SPLIT_SOURCE_GROUPS
    }
    blockers = []
    if document["status"] != "verified_complete":
        blockers.append("memory_measurements_not_verified_complete")
    if protocol["role"] != "source_blind_development":
        blockers.append("memory_cohort_is_retrospective")
    if not protocol["frozen_before_targets"]:
        blockers.append("memory_protocol_not_frozen_before_targets")
    if not protocol["source_group_split_isolated"]:
        blockers.append("memory_source_group_split_not_isolated")
    if protocol["prospective_cases_consumed"] != 0:
        blockers.append("memory_prospective_data_consumed_early")
    if not protocol["exact_outputs_verified"] or not protocol["refused_rows_retained"]:
        blockers.append("memory_exact_or_refusal_closure_incomplete")
    if any(
        split_counts[split] < minimum
        for split, minimum in history.MIN_SPLIT_SOURCE_GROUPS.items()
    ):
        blockers.append("memory_insufficient_source_groups_by_split")
    if (
        len(label_counts) < 2
        or any(
            count < history.MIN_SOURCE_GROUPS_PER_LABEL
            for count in label_counts.values()
        )
    ):
        blockers.append("memory_insufficient_material_winner_support")
    if coverage < MIN_NON_ABSTAIN_COVERAGE:
        blockers.append("memory_decision_surface_coverage_below_0_80")
    if any(value < MIN_NON_ABSTAIN_COVERAGE for value in coverage_by_split.values()):
        blockers.append("memory_decision_surface_split_coverage_below_0_80")
    supported_labels = set(label_counts)
    if any(
        not supported_labels.issubset({
            row["label"]
            for row in labels
            if row["split"] == split and row["label"] != ABSTAIN_LABEL
        })
        for split in EVALUATION_SPLITS
    ):
        blockers.append("memory_evaluation_label_support_incomplete")
    eligible = not blockers
    return {
        "schema": SURFACE_ASSESSMENT_SCHEMA,
        "status": "eligible_for_memory_learning_development" if eligible else "abstained",
        "surface_id": document["surface_id"],
        "metric": dict(metric),
        "source_groups": len(labels),
        "source_groups_by_split": dict(sorted(split_counts.items())),
        "source_groups_per_label": dict(sorted(label_counts.items())),
        "stable_material_winner_source_groups": len(non_abstain),
        "cross_host_winner_disagreement_cases": sorted(disagreement_cases),
        "threshold_abstention_cases": sorted(threshold_abstention_cases),
        "non_abstain_coverage": coverage,
        "non_abstain_coverage_by_split": coverage_by_split,
        "labels_sha256": digest(labels),
        "labels": labels,
        "blockers": blockers,
        "development_training_eligible": eligible,
        "training_performed": False,
        "prospective_cases_consumed": 0,
        "advice_enabled": False,
        "complete_abstention": not eligible,
        "exact_fallback": "unchanged exact path",
        "production_routing_permitted": False,
    }


def assess_decision_surface_or_abstain(document: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return assess_decision_surface(document)
    except (KeyError, TypeError, ValueError):
        return _safe_abstention(
            SURFACE_ASSESSMENT_SCHEMA,
            "malformed_or_unverified_memory_measurements",
        )


def validate_neural_protocol(
    protocol: Mapping[str, Any],
    measurements: Mapping[str, Any],
) -> None:
    """Validate a candidate and seed schedule frozen before neural evaluation."""

    _require(
        isinstance(protocol, Mapping)
        and set(protocol)
        == {
            "schema",
            "status",
            "surface_id",
            "measurement_cases_sha256",
            "candidate_family_id",
            "candidate_spec_sha256",
            "independent_verification_sha256",
            "training_seeds",
            "trained_on_splits",
            "validation_targets_visible_to_fit",
            "audit_targets_visible_to_fit",
            "candidate_spec_frozen_before_training",
            "candidate_locked_before_audit",
            "all_declared_seeds_required",
            "prospective_cases_consumed",
            "protocol_sha256",
        }
        and protocol.get("schema") == NEURAL_PROTOCOL_SCHEMA
        and protocol.get("status") == "frozen_before_training_and_evaluation"
        and protocol.get("surface_id") == measurements["surface_id"]
        and protocol.get("measurement_cases_sha256")
        == measurements["cases_sha256"]
        and type(protocol.get("candidate_family_id")) is str
        and bool(protocol["candidate_family_id"])
        and protocol.get("trained_on_splits") == ["development_fit"]
        and protocol.get("validation_targets_visible_to_fit") is False
        and protocol.get("audit_targets_visible_to_fit") is False
        and protocol.get("candidate_spec_frozen_before_training") is True
        and protocol.get("candidate_locked_before_audit") is True
        and protocol.get("all_declared_seeds_required") is True
        and protocol.get("prospective_cases_consumed") == 0,
        "memory neural protocol identity or isolation",
    )
    _hash(protocol["candidate_spec_sha256"], "memory neural candidate spec")
    _hash(
        protocol["independent_verification_sha256"],
        "memory neural protocol verification",
    )
    seeds = protocol["training_seeds"]
    _require(
        type(seeds) is list
        and len(seeds) >= MIN_NEURAL_TRAINING_SEEDS
        and all(type(seed) is int and 0 <= seed < 2**63 for seed in seeds)
        and seeds == sorted(seeds)
        and len(set(seeds)) == len(seeds),
        "memory neural seed schedule",
    )
    core = {key: protocol[key] for key in protocol if key != "protocol_sha256"}
    _require(
        protocol["protocol_sha256"] == digest(core),
        "memory neural protocol digest",
    )


def validate_predictions(
    predictions: Mapping[str, Any],
    measurements: Mapping[str, Any],
) -> None:
    base_fields = {
        "schema",
        "status",
        "surface_id",
        "measurement_cases_sha256",
        "candidate_id",
        "candidate_kind",
        "trained_on_splits",
        "validation_targets_visible_to_fit",
        "audit_targets_visible_to_fit",
        "prospective_cases_consumed",
        "rows_sha256",
        "rows",
    }
    candidate_kind = (
        predictions.get("candidate_kind") if isinstance(predictions, Mapping) else None
    )
    expected_fields = (
        base_fields | {"training_seed", "neural_protocol_sha256"}
        if candidate_kind == "tiny_neural"
        else base_fields
    )
    _require(
        isinstance(predictions, Mapping)
        and set(predictions) == expected_fields
        and predictions.get("schema") == PREDICTION_SCHEMA
        and predictions.get("status") == "development_candidate_predictions"
        and predictions.get("surface_id") == measurements["surface_id"]
        and predictions.get("measurement_cases_sha256") == measurements["cases_sha256"]
        and type(predictions.get("candidate_id")) is str
        and bool(predictions["candidate_id"])
        and candidate_kind in {"analytical", "bounded_tree", "linear", "tiny_neural"}
        and predictions.get("trained_on_splits") == ["development_fit"]
        and predictions.get("validation_targets_visible_to_fit") is False
        and predictions.get("audit_targets_visible_to_fit") is False
        and predictions.get("prospective_cases_consumed") == 0,
        "memory prediction identity or isolation",
    )
    if candidate_kind == "tiny_neural":
        _require(
            type(predictions.get("training_seed")) is int
            and 0 <= predictions["training_seed"] < 2**63,
            "memory neural training seed",
        )
        _hash(predictions["neural_protocol_sha256"], "memory neural protocol")
    rows = predictions["rows"]
    case_ids = {case["case_id"] for case in measurements["cases"]}
    arms = measurements["arms"]
    _require(
        type(rows) is list
        and predictions["rows_sha256"] == digest(rows)
        and len(rows) == len(case_ids)
        and len({row.get("case_id") for row in rows if isinstance(row, Mapping)})
        == len(rows)
        and {row.get("case_id") for row in rows if isinstance(row, Mapping)} == case_ids,
        "memory prediction rows",
    )
    for row in rows:
        _require(
            isinstance(row, Mapping)
            and set(row) == {"case_id", "predicted_bytes_by_arm", "selected_arm"}
            and isinstance(row["predicted_bytes_by_arm"], Mapping)
            and set(row["predicted_bytes_by_arm"]) == set(arms)
            and all(
                _finite_nonnegative(value, f"predicted memory:{arm}") >= 0
                for arm, value in row["predicted_bytes_by_arm"].items()
            )
            and row["selected_arm"] in set(arms) | {ABSTAIN_LABEL},
            "memory prediction row shape",
        )
        if row["selected_arm"] != ABSTAIN_LABEL:
            predicted = row["predicted_bytes_by_arm"]
            expected = min(arms, key=lambda arm: (float(predicted[arm]), arms.index(arm)))
            _require(row["selected_arm"] == expected, "memory selected arm is not predicted minimum")


def _pair_is_material(left: float, right: float, floor: int, relative_gap: float) -> bool:
    smaller = min(left, right)
    difference = abs(left - right)
    return difference >= floor and (smaller == 0 or difference / smaller >= relative_gap)


def _assess_candidate_predictions(
    predictions: Mapping[str, Any],
    measurements: Mapping[str, Any],
    *,
    allow_neural: bool,
) -> dict[str, Any]:
    """Evaluate memory estimates and their implied arm choice on validation/audit."""
    surface = assess_decision_surface(measurements)
    _require(surface["development_training_eligible"], "memory surface is not eligible")
    validate_predictions(predictions, measurements)
    _require(
        predictions["candidate_kind"] != "tiny_neural" or allow_neural,
        "memory neural predictions require replicated-seed assessment",
    )
    case_by_id = {case["case_id"]: case for case in measurements["cases"]}
    label_by_id = {row["case_id"]: row["label"] for row in surface["labels"]}
    prediction_by_id = {row["case_id"]: row for row in predictions["rows"]}
    arms = measurements["arms"]
    floor = measurements["metric"]["resolution_floor_bytes"]
    relative_gap = float(measurements["metric"]["minimum_relative_runner_up_gap"])
    split_metrics = {}
    blockers = []
    for split in EVALUATION_SPLITS:
        cases = [case for case in measurements["cases"] if case["split"] == split]
        cell_underpredictions = []
        cell_overprediction_factors = []
        materially_ordered_pairs = 0
        pairwise_agreements = 0
        selected_cases = 0
        near_minimum_cases = 0
        selection_regret_bytes = []
        unstable_not_abstained = []
        for case in cases:
            case_id = case["case_id"]
            prediction = prediction_by_id[case_id]
            selected = prediction["selected_arm"]
            if label_by_id[case_id] == ABSTAIN_LABEL and selected != ABSTAIN_LABEL:
                unstable_not_abstained.append(case_id)
            if selected != ABSTAIN_LABEL:
                selected_cases += 1
            for values in case["measurements_by_host"].values():
                for arm in arms:
                    actual = float(values[arm])
                    predicted = float(prediction["predicted_bytes_by_arm"][arm])
                    cell_underpredictions.append(actual - predicted > floor)
                    cell_overprediction_factors.append(
                        max(1.0, (predicted + floor) / (actual + floor))
                    )
                for left, right in combinations(arms, 2):
                    actual_left = float(values[left])
                    actual_right = float(values[right])
                    if not _pair_is_material(
                        actual_left,
                        actual_right,
                        floor,
                        relative_gap,
                    ):
                        continue
                    materially_ordered_pairs += 1
                    predicted_delta = (
                        float(prediction["predicted_bytes_by_arm"][left])
                        - float(prediction["predicted_bytes_by_arm"][right])
                    )
                    actual_delta = actual_left - actual_right
                    pairwise_agreements += (
                        predicted_delta != 0
                        and (predicted_delta > 0) == (actual_delta > 0)
                    )
                if selected != ABSTAIN_LABEL:
                    measured_minimum = min(float(values[arm]) for arm in arms)
                    selected_actual = float(values[selected])
                    regret = selected_actual - measured_minimum
                    selection_regret_bytes.append(regret)
                    near_minimum_cases += regret <= floor
        host_selected_cells = selected_cases * len(measurements["hosts"])
        underprediction = statistics.mean(cell_underpredictions)
        overprediction = statistics.median(cell_overprediction_factors)
        pairwise = (
            pairwise_agreements / materially_ordered_pairs
            if materially_ordered_pairs
            else 0.0
        )
        near_minimum = (
            near_minimum_cases / host_selected_cells if host_selected_cells else 0.0
        )
        coverage = selected_cases / len(cases)
        metrics = {
            "cases": len(cases),
            "candidate_non_abstain_coverage": coverage,
            "material_underprediction_prevalence": underprediction,
            "median_overprediction_factor": overprediction,
            "materially_ordered_pairs": materially_ordered_pairs,
            "pairwise_order_agreements": pairwise_agreements,
            "pairwise_order_agreement": pairwise,
            "near_minimum_case_host_cells": near_minimum_cases,
            "near_minimum_selection_prevalence": near_minimum,
            "median_selection_regret_bytes": (
                statistics.median(selection_regret_bytes)
                if selection_regret_bytes
                else None
            ),
            "unstable_not_abstained_cases": sorted(unstable_not_abstained),
        }
        split_metrics[split] = metrics
        if unstable_not_abstained:
            blockers.append(f"unstable_memory_labels_not_abstained:{split}")
        if coverage < MIN_NON_ABSTAIN_COVERAGE:
            blockers.append(f"memory_prediction_coverage_below_0_80:{split}")
        if underprediction > MAX_MATERIAL_UNDERPREDICTION_PREVALENCE:
            blockers.append(f"memory_underprediction_safety_failed:{split}")
        if overprediction > MAX_MEDIAN_OVERPREDICTION_FACTOR:
            blockers.append(f"memory_overprediction_bound_failed:{split}")
        if pairwise < MIN_PAIRWISE_ORDER_AGREEMENT:
            blockers.append(f"memory_pairwise_ordering_failed:{split}")
        if near_minimum < MIN_NEAR_MINIMUM_SELECTION_PREVALENCE:
            blockers.append(f"memory_near_minimum_selection_failed:{split}")
    signal = not blockers
    return {
        "schema": PREDICTION_ASSESSMENT_SCHEMA,
        "status": (
            "memory_development_signal_established"
            if signal
            else "memory_development_signal_rejected"
        ),
        "surface_labels_sha256": surface["labels_sha256"],
        "candidate_id": predictions["candidate_id"],
        "candidate_kind": predictions["candidate_kind"],
        "thresholds": {
            "minimum_non_abstain_coverage": MIN_NON_ABSTAIN_COVERAGE,
            "maximum_material_underprediction_prevalence": (
                MAX_MATERIAL_UNDERPREDICTION_PREVALENCE
            ),
            "maximum_median_overprediction_factor": MAX_MEDIAN_OVERPREDICTION_FACTOR,
            "minimum_pairwise_order_agreement": MIN_PAIRWISE_ORDER_AGREEMENT,
            "minimum_near_minimum_selection_prevalence": (
                MIN_NEAR_MINIMUM_SELECTION_PREVALENCE
            ),
        },
        "split_metrics": split_metrics,
        "blockers": blockers,
        "development_signal_established": signal,
        "training_performed": False,
        "prospective_cases_consumed": 0,
        "advice_enabled": False,
        "complete_abstention": not signal,
        "exact_fallback": "unchanged exact path",
        "production_routing_permitted": False,
    }


def assess_candidate_predictions(
    predictions: Mapping[str, Any],
    measurements: Mapping[str, Any],
) -> dict[str, Any]:
    """Assess a non-neural memory candidate; neural evidence must use all seeds."""

    return _assess_candidate_predictions(
        predictions,
        measurements,
        allow_neural=False,
    )


def assess_neural_seed_predictions(
    protocol: Mapping[str, Any],
    seed_predictions: Sequence[Mapping[str, Any]],
    measurements: Mapping[str, Any],
) -> dict[str, Any]:
    """Require every predeclared neural seed to pass both memory splits."""

    surface = assess_decision_surface(measurements)
    _require(surface["development_training_eligible"], "memory surface is not eligible")
    validate_neural_protocol(protocol, measurements)
    seeds = protocol["training_seeds"]
    _require(
        type(seed_predictions) in (list, tuple)
        and len(seed_predictions) == len(seeds)
        and all(isinstance(row, Mapping) for row in seed_predictions)
        and all(row.get("candidate_kind") == "tiny_neural" for row in seed_predictions)
        and {row.get("training_seed") for row in seed_predictions} == set(seeds)
        and len({row.get("training_seed") for row in seed_predictions})
        == len(seed_predictions)
        and len({row.get("candidate_id") for row in seed_predictions})
        == len(seed_predictions)
        and all(
            row.get("neural_protocol_sha256") == protocol["protocol_sha256"]
            for row in seed_predictions
        ),
        "memory neural seed or protocol binding",
    )
    ordered_predictions = sorted(
        seed_predictions, key=lambda row: row["training_seed"]
    )
    assessments = [
        _assess_candidate_predictions(
            predictions,
            measurements,
            allow_neural=True,
        )
        for predictions in ordered_predictions
    ]
    blockers = [
        f"seed_failed:{predictions['training_seed']}:{blocker}"
        for predictions, assessment in zip(
            ordered_predictions, assessments, strict=True
        )
        for blocker in assessment["blockers"]
    ]
    signal = not blockers

    worst_case = {}
    for split in EVALUATION_SPLITS:
        metrics = [assessment["split_metrics"][split] for assessment in assessments]
        regrets = [
            row["median_selection_regret_bytes"]
            for row in metrics
            if row["median_selection_regret_bytes"] is not None
        ]
        worst_case[split] = {
            "minimum_candidate_non_abstain_coverage": min(
                row["candidate_non_abstain_coverage"] for row in metrics
            ),
            "maximum_material_underprediction_prevalence": max(
                row["material_underprediction_prevalence"] for row in metrics
            ),
            "maximum_median_overprediction_factor": max(
                row["median_overprediction_factor"] for row in metrics
            ),
            "minimum_pairwise_order_agreement": min(
                row["pairwise_order_agreement"] for row in metrics
            ),
            "minimum_near_minimum_selection_prevalence": min(
                row["near_minimum_selection_prevalence"] for row in metrics
            ),
            "maximum_median_selection_regret_bytes": max(regrets) if regrets else None,
        }

    return {
        "schema": NEURAL_ASSESSMENT_SCHEMA,
        "status": (
            "replicated_memory_development_signal_established"
            if signal
            else "replicated_memory_development_signal_rejected"
        ),
        "neural_protocol_sha256": protocol["protocol_sha256"],
        "candidate_family_id": protocol["candidate_family_id"],
        "candidate_spec_sha256": protocol["candidate_spec_sha256"],
        "surface_labels_sha256": surface["labels_sha256"],
        "minimum_training_seeds": MIN_NEURAL_TRAINING_SEEDS,
        "evaluated_training_seeds": [
            row["training_seed"] for row in ordered_predictions
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
    protocol: Mapping[str, Any],
    seed_predictions: Sequence[Mapping[str, Any]],
    measurements: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        return assess_neural_seed_predictions(
            protocol,
            seed_predictions,
            measurements,
        )
    except (KeyError, TypeError, ValueError):
        return _safe_abstention(
            NEURAL_ASSESSMENT_SCHEMA,
            "malformed_unverified_ineligible_or_unreplicated_memory_neural_evidence",
        )


def assess_candidate_predictions_or_abstain(
    predictions: Mapping[str, Any],
    measurements: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        return assess_candidate_predictions(predictions, measurements)
    except (KeyError, TypeError, ValueError):
        return _safe_abstention(
            PREDICTION_ASSESSMENT_SCHEMA,
            "malformed_unverified_ineligible_or_leaked_memory_evidence",
        )
