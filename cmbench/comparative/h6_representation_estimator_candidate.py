"""Frozen development-only H6 retained-memory estimator candidate.

The candidate never participates in production evaluation or routing.  It compares one
arm-specific affine upper envelope with an otherwise identical pooled control using the
already sealed H6 fresh-process evidence.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from itertools import combinations
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any

from .contracts import canonical_bytes
from . import h6_fresh_process_memory_gate as h6


SCHEMA = "cm-h6-representation-estimator-freeze/v1"
SUMMARY_SCHEMA = "cm-h6-representation-estimator-summary/v1"
PROTOCOL = "docs/research/CM_H6_REPRESENTATION_ESTIMATOR_CANDIDATE_PROTOCOL_2026_09_08.md"
H6_FREEZE = "docs/research/verification/cm-h6-fresh-process-memory-freeze-2026-09-08/FREEZE.json"
H6_RAW = "docs/research/verification/cm-h6-fresh-process-memory-attempt-001-2026-09-08/RAW.jsonl"
H6_SUMMARY = "docs/research/verification/cm-h6-fresh-process-memory-attempt-001-2026-09-08/SUMMARY.json"
H6_VERIFICATION = "docs/research/verification/cm-h6-fresh-process-memory-attempt-001-2026-09-08/INDEPENDENT_VERIFICATION.json"
SOURCE_CLOSURE = (
    "cmbench/comparative/h6_representation_estimator_candidate.py",
    "scripts/cm_h6_representation_estimator_candidate.py",
    "scripts/crse_verify_h6_representation_estimator_candidate.py",
    PROTOCOL,
    H6_FREEZE,
    H6_RAW,
    H6_SUMMARY,
    H6_VERIFICATION,
)
RESOLUTION_FLOOR_BYTES = 65_536
ARMS = h6.B_ARMS


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        stream.write("\n")


def _file_record(root: Path, relative: str) -> dict[str, Any]:
    path = (root / relative).resolve()
    _require(path.is_relative_to(root) and path.is_file(), f"missing estimator source: {relative}")
    return {"path": relative, "bytes": path.stat().st_size, "sha256": _sha256(path)}


def build_freeze(project_root: str | Path) -> dict[str, Any]:
    """Build the candidate freeze without parsing decision-bearing raw memory values."""
    root = Path(project_root).resolve()
    parent_freeze = _load(root / H6_FREEZE)
    h6.validate_freeze(parent_freeze, root)
    parent_summary = _load(root / H6_SUMMARY)
    parent_verification = _load(root / H6_VERIFICATION)
    _require(parent_summary.get("decision") ==
             "go_memory_calibration_only_requires_separate_candidate_freeze",
             "H6 calibration did not permit candidate freeze")
    _require(parent_summary.get("candidate_implemented") is False, "H6 candidate state")
    _require(parent_summary.get("production_routing_changed") is False, "H6 routing state")
    _require(parent_verification.get("status") == "verified", "H6 independent replay")
    _require(parent_verification.get("summary_replay_mismatches") == 0,
             "H6 independent summary mismatches")
    _require(_sha256(root / H6_RAW) == parent_summary["raw_sha256"], "H6 raw hash")
    _require(parent_verification.get("raw_sha256") == parent_summary["raw_sha256"],
             "H6 independent raw hash")
    _require(parent_verification.get("freeze_sha256") == parent_freeze["freeze_sha256"],
             "H6 independent freeze hash")
    b_cases = list(parent_freeze["workload"]["B"]["case_ids"])
    calibration = [case_id for case_id in b_cases if case_id.startswith("fresh-")]
    holdout = [case_id for case_id in b_cases if not case_id.startswith("fresh-")]
    _require(len(calibration) == 6 and len(holdout) == 5, "candidate cohort cardinality")
    closure = [_file_record(root, relative) for relative in SOURCE_CLOSURE]
    core = {
        "schema": SCHEMA,
        "date": "2026-09-08",
        "status": "frozen_before_decision_bearing_candidate_evaluation",
        "scope": "one_development_only_h6_lane_b_representation_estimator",
        "parent": {
            "freeze_path": H6_FREEZE,
            "freeze_sha256": parent_freeze["freeze_sha256"],
            "raw_path": H6_RAW,
            "raw_sha256": parent_summary["raw_sha256"],
            "summary_path": H6_SUMMARY,
            "summary_file_sha256": _sha256(root / H6_SUMMARY),
            "summary_canonical_sha256": parent_summary["summary_sha256"],
            "verification_path": H6_VERIFICATION,
            "verification_file_sha256": _sha256(root / H6_VERIFICATION),
        },
        "selection": {
            "lane": "B",
            "lifecycle": "reused",
            "arms": list(ARMS),
            "query_counts": [1, 64],
            "replicates": [0, 1, 2],
            "calibration_case_ids": calibration,
            "holdout_case_ids": holdout,
            "source_rows_per_case_arm": 6,
            "calibration_cells": 24,
            "holdout_cells": 20,
            "selection_blind_to_case_memory_values": True,
        },
        "target": {
            "row_value": "max(0,working_set_prepared_retained_delta_bytes,private_prepared_retained_delta_bytes)",
            "cell_aggregation": "median_across_q1_q64_and_three_replicates",
            "resolution_floor_bytes": RESOLUTION_FLOOR_BYTES,
        },
        "feature": {
            "name": "expression_bytes",
            "availability": "preconstruction_frozen_expression_document",
            "excluded": [
                "case_identity", "family", "timing", "target_memory", "query_result",
                "postconstruction_metrics",
            ],
        },
        "models": {
            "shared_rule": "nonnegative_slope_ols_plus_smallest_training_upper_envelope_margin",
            "control": "one_pooled_affine_model_all_arms",
            "candidate": "one_affine_model_per_representation_arm",
            "prediction_rounding": "ceil_nonnegative_whole_bytes",
            "candidate_count": 1,
        },
        "gate": {
            "holdout_median_log_error_improvement_min": 0.15,
            "material_underprediction_prevalence_max": 0.20,
            "median_overprediction_factor_max": 2.0,
            "pairwise_order_agreement_min": 0.70,
            "near_minimum_case_prevalence_min": 0.80,
            "loocv_candidate_better_folds_min": 4,
            "independent_replay_mismatches_max": 0,
        },
        "continuation": {
            "pass": "go_local_estimator_evidence_request_runpod_authorization",
            "fail": "no_go_h6_estimator_and_routing_deferred",
            "production_routing_change_authorized": False,
            "runpod_authorized": False,
            "h2_h3_reopened": False,
            "h8_activated": False,
            "h9_work_authorized": False,
            "second_candidate_authorized": False,
            "publication_authorized": False,
        },
        "source_closure": closure,
        "source_closure_sha256": _digest(closure),
    }
    return {**core, "freeze_sha256": _digest(core)}


def validate_freeze(freeze: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    _require(freeze.get("schema") == SCHEMA, "candidate freeze schema")
    core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    _require(freeze.get("freeze_sha256") == _digest(core), "candidate freeze digest")
    replay = build_freeze(project_root)
    _require(canonical_bytes(replay) == canonical_bytes(freeze), "candidate freeze replay")
    return dict(freeze)


def freeze_to_path(project_root: str | Path, output_path: str | Path) -> dict[str, Any]:
    freeze = build_freeze(project_root)
    _write_new(Path(output_path), freeze)
    return freeze


def _read_raw(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    _require(len(rows) == 708, "candidate parent row count")
    _require(len({row.get("row_id") for row in rows}) == len(rows), "candidate parent row ids")
    _require(all(row.get("status") == "ok" and row.get("exact_oracle_agreement") is True
                 and row.get("child_exit_code") == 0 for row in rows),
             "candidate parent row validity")
    return rows


def _target(row: Mapping[str, Any]) -> int:
    memory = row["memory"]
    return max(
        0,
        int(memory["working_set_prepared_retained_delta_bytes"]),
        int(memory["private_prepared_retained_delta_bytes"]),
    )


def aggregate_cells(rows: Sequence[Mapping[str, Any]], freeze: Mapping[str, Any]) -> list[dict[str, Any]]:
    selected = freeze["selection"]
    allowed_cases = set(selected["calibration_case_ids"] + selected["holdout_case_ids"])
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if (row.get("lane") == "B" and row.get("lifecycle") == "reused"
                and row.get("case_id") in allowed_cases and row.get("arm") in ARMS
                and row.get("query_count") in {1, 64}
                and row.get("replicate") in {0, 1, 2}):
            groups[(str(row["case_id"]), str(row["arm"]))].append(row)
    expected_keys = {(case_id, arm) for case_id in allowed_cases for arm in ARMS}
    _require(set(groups) == expected_keys, "candidate cell keys")
    cells = []
    for case_id, arm in sorted(groups):
        group = groups[(case_id, arm)]
        _require(len(group) == selected["source_rows_per_case_arm"], "candidate cell rows")
        _require({(int(row["query_count"]), int(row["replicate"])) for row in group}
                 == {(query, replicate) for query in (1, 64) for replicate in (0, 1, 2)},
                 "candidate cell schedule")
        features = {int(row["features"]["expression_bytes"]) for row in group}
        _require(len(features) == 1, "candidate feature invariance")
        cells.append({
            "case_id": case_id,
            "arm": arm,
            "cohort": "calibration" if case_id in selected["calibration_case_ids"] else "holdout",
            "expression_bytes": features.pop(),
            "actual_bytes": int(statistics.median(_target(row) for row in group)),
            "source_row_ids": sorted(str(row["row_id"]) for row in group),
        })
    _require(sum(cell["cohort"] == "calibration" for cell in cells) == 24,
             "candidate calibration cells")
    _require(sum(cell["cohort"] == "holdout" for cell in cells) == 20,
             "candidate holdout cells")
    return cells


def fit_upper_envelope(cells: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _require(len(cells) >= 2, "candidate fit observations")
    xs = [float(cell["expression_bytes"]) for cell in cells]
    ys = [float(cell["actual_bytes"]) for cell in cells]
    x_mean, y_mean = statistics.mean(xs), statistics.mean(ys)
    denominator = sum((value - x_mean) ** 2 for value in xs)
    raw_slope = (sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True))
                 / denominator if denominator else 0.0)
    slope = max(0.0, raw_slope)
    intercept = statistics.mean(y - slope * x for x, y in zip(xs, ys, strict=True))
    margin = max(0.0, max(y - max(0.0, intercept + slope * x)
                          for x, y in zip(xs, ys, strict=True)))
    return {
        "training_cells": len(cells),
        "raw_slope": raw_slope,
        "slope": slope,
        "intercept": intercept,
        "upper_envelope_margin": margin,
    }


def predict(model: Mapping[str, Any], expression_bytes: int) -> int:
    return int(math.ceil(max(
        0.0,
        float(model["intercept"]) + float(model["slope"]) * expression_bytes
        + float(model["upper_envelope_margin"]),
    )))


def _log_error(prediction: int, actual: int) -> float:
    floor = RESOLUTION_FLOOR_BYTES
    return abs(math.log2((prediction + floor) / (actual + floor)))


def _models(calibration: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    control = fit_upper_envelope(calibration)
    candidate = {
        arm: fit_upper_envelope([cell for cell in calibration if cell["arm"] == arm])
        for arm in ARMS
    }
    return control, candidate


def _loocv(calibration: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    cases = sorted({str(cell["case_id"]) for cell in calibration})
    results = []
    for case_id in cases:
        training = [cell for cell in calibration if cell["case_id"] != case_id]
        held = [cell for cell in calibration if cell["case_id"] == case_id]
        control, candidate = _models(training)
        control_error = statistics.median(
            _log_error(predict(control, int(cell["expression_bytes"])), int(cell["actual_bytes"]))
            for cell in held
        )
        candidate_error = statistics.median(
            _log_error(predict(candidate[str(cell["arm"])], int(cell["expression_bytes"])),
                       int(cell["actual_bytes"]))
            for cell in held
        )
        results.append({
            "held_out_case_id": case_id,
            "control_median_log_error": control_error,
            "candidate_median_log_error": candidate_error,
            "candidate_better": candidate_error < control_error,
        })
    return results


def evaluate(project_root: str | Path, freeze_path: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    freeze = _load(Path(freeze_path))
    validate_freeze(freeze, root)
    raw_path = root / freeze["parent"]["raw_path"]
    _require(_sha256(raw_path) == freeze["parent"]["raw_sha256"], "candidate raw drift")
    cells = aggregate_cells(_read_raw(raw_path), freeze)
    calibration = [cell for cell in cells if cell["cohort"] == "calibration"]
    holdout = [cell for cell in cells if cell["cohort"] == "holdout"]
    control, candidate = _models(calibration)
    predictions = []
    for cell in holdout:
        control_prediction = predict(control, int(cell["expression_bytes"]))
        candidate_prediction = predict(candidate[str(cell["arm"])], int(cell["expression_bytes"]))
        predictions.append({
            **cell,
            "control_prediction_bytes": control_prediction,
            "candidate_prediction_bytes": candidate_prediction,
            "control_log_error": _log_error(control_prediction, int(cell["actual_bytes"])),
            "candidate_log_error": _log_error(candidate_prediction, int(cell["actual_bytes"])),
            "material_underprediction": int(cell["actual_bytes"]) - candidate_prediction
            > RESOLUTION_FLOOR_BYTES,
            "overprediction_factor": max(
                1.0,
                (candidate_prediction + RESOLUTION_FLOOR_BYTES)
                / (int(cell["actual_bytes"]) + RESOLUTION_FLOOR_BYTES),
            ),
        })
    control_error = statistics.median(item["control_log_error"] for item in predictions)
    candidate_error = statistics.median(item["candidate_log_error"] for item in predictions)
    improvement = ((control_error - candidate_error) / control_error
                   if control_error > 0.0 else (1.0 if candidate_error == 0.0 else -1.0))
    underprediction = statistics.mean(item["material_underprediction"] for item in predictions)
    overprediction = statistics.median(item["overprediction_factor"] for item in predictions)
    by_case = defaultdict(dict)
    for item in predictions:
        by_case[item["case_id"]][item["arm"]] = item
    ordered_pairs = 0
    agreed_pairs = 0
    near_minimum_cases = 0
    case_decisions = []
    for case_id in sorted(by_case):
        arms = by_case[case_id]
        _require(set(arms) == set(ARMS), "candidate holdout arm completeness")
        for left, right in combinations(ARMS, 2):
            actual_delta = arms[left]["actual_bytes"] - arms[right]["actual_bytes"]
            if abs(actual_delta) <= RESOLUTION_FLOOR_BYTES:
                continue
            ordered_pairs += 1
            predicted_delta = (arms[left]["candidate_prediction_bytes"]
                               - arms[right]["candidate_prediction_bytes"])
            agreed_pairs += (predicted_delta > 0) == (actual_delta > 0) and predicted_delta != 0
        chosen = min(ARMS, key=lambda arm: (arms[arm]["candidate_prediction_bytes"], arm))
        measured_minimum = min(arms[arm]["actual_bytes"] for arm in ARMS)
        near = arms[chosen]["actual_bytes"] <= measured_minimum + RESOLUTION_FLOOR_BYTES
        near_minimum_cases += near
        case_decisions.append({
            "case_id": case_id,
            "candidate_selected_arm": chosen,
            "selected_actual_bytes": arms[chosen]["actual_bytes"],
            "measured_minimum_bytes": measured_minimum,
            "within_resolution_floor": near,
        })
    pairwise_agreement = agreed_pairs / ordered_pairs if ordered_pairs else 0.0
    near_minimum_prevalence = near_minimum_cases / len(by_case)
    loocv = _loocv(calibration)
    better_folds = sum(item["candidate_better"] for item in loocv)
    gate = freeze["gate"]
    conditions = {
        "parent_validity": True,
        "cell_schedule": len(calibration) == 24 and len(holdout) == 20,
        "holdout_error_improvement": improvement >= gate["holdout_median_log_error_improvement_min"],
        "underprediction_safety": underprediction <= gate["material_underprediction_prevalence_max"],
        "overprediction_bound": overprediction <= gate["median_overprediction_factor_max"],
        "pairwise_ordering": pairwise_agreement >= gate["pairwise_order_agreement_min"],
        "near_minimum_selection": near_minimum_prevalence >= gate["near_minimum_case_prevalence_min"],
        "loocv_robustness": better_folds >= gate["loocv_candidate_better_folds_min"],
    }
    decision = (freeze["continuation"]["pass"] if all(conditions.values())
                else freeze["continuation"]["fail"])
    core = {
        "schema": SUMMARY_SCHEMA,
        "freeze_sha256": freeze["freeze_sha256"],
        "parent_raw_sha256": freeze["parent"]["raw_sha256"],
        "candidate": "per_arm_nonnegative_affine_upper_envelope",
        "control": "pooled_nonnegative_affine_upper_envelope",
        "calibration_cells": len(calibration),
        "holdout_cells": len(holdout),
        "control_model": control,
        "candidate_models": candidate,
        "holdout_predictions": predictions,
        "loocv": loocv,
        "metrics": {
            "control_median_log_error": control_error,
            "candidate_median_log_error": candidate_error,
            "holdout_median_log_error_improvement": improvement,
            "material_underprediction_prevalence": underprediction,
            "median_overprediction_factor": overprediction,
            "materially_ordered_pairs": ordered_pairs,
            "pairwise_order_agreements": agreed_pairs,
            "pairwise_order_agreement": pairwise_agreement,
            "near_minimum_cases": near_minimum_cases,
            "near_minimum_case_prevalence": near_minimum_prevalence,
            "loocv_candidate_better_folds": better_folds,
        },
        "case_decisions": case_decisions,
        "conditions": conditions,
        "decision": decision,
        "candidate_implemented_in_production": False,
        "production_routing_changed": False,
        "runpod_authorization_request_permitted": decision == freeze["continuation"]["pass"],
    }
    return {**core, "summary_sha256": _digest(core)}


def evaluate_to_path(project_root: str | Path, freeze_path: str | Path,
                     output_path: str | Path) -> dict[str, Any]:
    summary = evaluate(project_root, freeze_path)
    _write_new(Path(output_path), summary)
    return summary
