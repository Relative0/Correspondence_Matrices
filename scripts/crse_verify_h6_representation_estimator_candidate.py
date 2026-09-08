"""Independent standard-library replay of the H6 estimator candidate."""
from __future__ import annotations

import argparse
from collections import defaultdict
from itertools import combinations
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence


FLOOR = 65_536
SUMMARY_SCHEMA = "cm-h6-representation-estimator-summary/v1"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _fit(cells: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _require(len(cells) >= 2, "fit observations")
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
        "training_cells": len(cells), "raw_slope": raw_slope, "slope": slope,
        "intercept": intercept, "upper_envelope_margin": margin,
    }


def _predict(model: Mapping[str, Any], expression_bytes: int) -> int:
    return int(math.ceil(max(
        0.0, float(model["intercept"]) + float(model["slope"]) * expression_bytes
        + float(model["upper_envelope_margin"]),
    )))


def _error(prediction: int, actual: int) -> float:
    return abs(math.log2((prediction + FLOOR) / (actual + FLOOR)))


def _models(cells: Sequence[Mapping[str, Any]], arms: Sequence[str]):
    return _fit(cells), {
        arm: _fit([cell for cell in cells if cell["arm"] == arm]) for arm in arms
    }


def _aggregate(rows: Sequence[Mapping[str, Any]], freeze: Mapping[str, Any]):
    selection = freeze["selection"]
    arms = tuple(selection["arms"])
    allowed = set(selection["calibration_case_ids"] + selection["holdout_case_ids"])
    groups = defaultdict(list)
    for row in rows:
        if (row.get("lane") == "B" and row.get("lifecycle") == "reused"
                and row.get("case_id") in allowed and row.get("arm") in arms
                and row.get("query_count") in {1, 64}
                and row.get("replicate") in {0, 1, 2}):
            groups[(row["case_id"], row["arm"])].append(row)
    _require(set(groups) == {(case, arm) for case in allowed for arm in arms}, "cell keys")
    cells = []
    for case_id, arm in sorted(groups):
        group = groups[(case_id, arm)]
        _require(len(group) == 6, "cell cardinality")
        _require({(row["query_count"], row["replicate"]) for row in group}
                 == {(query, replicate) for query in (1, 64) for replicate in (0, 1, 2)},
                 "cell schedule")
        features = {int(row["features"]["expression_bytes"]) for row in group}
        _require(len(features) == 1, "feature invariance")
        values = [max(
            0,
            int(row["memory"]["working_set_prepared_retained_delta_bytes"]),
            int(row["memory"]["private_prepared_retained_delta_bytes"]),
        ) for row in group]
        cells.append({
            "case_id": case_id, "arm": arm,
            "cohort": ("calibration" if case_id in selection["calibration_case_ids"]
                       else "holdout"),
            "expression_bytes": features.pop(),
            "actual_bytes": int(statistics.median(values)),
            "source_row_ids": sorted(row["row_id"] for row in group),
        })
    return cells


def _loocv(calibration, arms):
    result = []
    for case_id in sorted({cell["case_id"] for cell in calibration}):
        training = [cell for cell in calibration if cell["case_id"] != case_id]
        held = [cell for cell in calibration if cell["case_id"] == case_id]
        control, candidate = _models(training, arms)
        control_error = statistics.median(
            _error(_predict(control, cell["expression_bytes"]), cell["actual_bytes"])
            for cell in held)
        candidate_error = statistics.median(
            _error(_predict(candidate[cell["arm"]], cell["expression_bytes"]),
                   cell["actual_bytes"]) for cell in held)
        result.append({
            "held_out_case_id": case_id,
            "control_median_log_error": control_error,
            "candidate_median_log_error": candidate_error,
            "candidate_better": candidate_error < control_error,
        })
    return result


def _replay(freeze: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    arms = tuple(freeze["selection"]["arms"])
    cells = _aggregate(rows, freeze)
    calibration = [cell for cell in cells if cell["cohort"] == "calibration"]
    holdout = [cell for cell in cells if cell["cohort"] == "holdout"]
    _require(len(calibration) == 24 and len(holdout) == 20, "split cardinality")
    control, candidate = _models(calibration, arms)
    predictions = []
    for cell in holdout:
        control_prediction = _predict(control, cell["expression_bytes"])
        candidate_prediction = _predict(candidate[cell["arm"]], cell["expression_bytes"])
        predictions.append({
            **cell,
            "control_prediction_bytes": control_prediction,
            "candidate_prediction_bytes": candidate_prediction,
            "control_log_error": _error(control_prediction, cell["actual_bytes"]),
            "candidate_log_error": _error(candidate_prediction, cell["actual_bytes"]),
            "material_underprediction": cell["actual_bytes"] - candidate_prediction > FLOOR,
            "overprediction_factor": max(
                1.0, (candidate_prediction + FLOOR) / (cell["actual_bytes"] + FLOOR)),
        })
    control_error = statistics.median(row["control_log_error"] for row in predictions)
    candidate_error = statistics.median(row["candidate_log_error"] for row in predictions)
    improvement = ((control_error - candidate_error) / control_error
                   if control_error > 0.0 else (1.0 if candidate_error == 0.0 else -1.0))
    underprediction = statistics.mean(row["material_underprediction"] for row in predictions)
    overprediction = statistics.median(row["overprediction_factor"] for row in predictions)
    by_case = defaultdict(dict)
    for row in predictions:
        by_case[row["case_id"]][row["arm"]] = row
    ordered_pairs = agreements = near_cases = 0
    decisions = []
    for case_id in sorted(by_case):
        values = by_case[case_id]
        _require(set(values) == set(arms), "arm completeness")
        for left, right in combinations(arms, 2):
            actual_delta = values[left]["actual_bytes"] - values[right]["actual_bytes"]
            if abs(actual_delta) <= FLOOR:
                continue
            ordered_pairs += 1
            predicted_delta = (values[left]["candidate_prediction_bytes"]
                               - values[right]["candidate_prediction_bytes"])
            agreements += ((predicted_delta > 0) == (actual_delta > 0)
                           and predicted_delta != 0)
        chosen = min(arms, key=lambda arm: (values[arm]["candidate_prediction_bytes"], arm))
        measured_minimum = min(values[arm]["actual_bytes"] for arm in arms)
        near = values[chosen]["actual_bytes"] <= measured_minimum + FLOOR
        near_cases += near
        decisions.append({
            "case_id": case_id, "candidate_selected_arm": chosen,
            "selected_actual_bytes": values[chosen]["actual_bytes"],
            "measured_minimum_bytes": measured_minimum,
            "within_resolution_floor": near,
        })
    pairwise = agreements / ordered_pairs if ordered_pairs else 0.0
    near_prevalence = near_cases / len(by_case)
    loocv = _loocv(calibration, arms)
    better_folds = sum(row["candidate_better"] for row in loocv)
    gate = freeze["gate"]
    conditions = {
        "parent_validity": True,
        "cell_schedule": len(calibration) == 24 and len(holdout) == 20,
        "holdout_error_improvement": improvement >= gate["holdout_median_log_error_improvement_min"],
        "underprediction_safety": underprediction <= gate["material_underprediction_prevalence_max"],
        "overprediction_bound": overprediction <= gate["median_overprediction_factor_max"],
        "pairwise_ordering": pairwise >= gate["pairwise_order_agreement_min"],
        "near_minimum_selection": near_prevalence >= gate["near_minimum_case_prevalence_min"],
        "loocv_robustness": better_folds >= gate["loocv_candidate_better_folds_min"],
    }
    decision = freeze["continuation"]["pass"] if all(conditions.values()) else freeze["continuation"]["fail"]
    core = {
        "schema": SUMMARY_SCHEMA, "freeze_sha256": freeze["freeze_sha256"],
        "parent_raw_sha256": freeze["parent"]["raw_sha256"],
        "candidate": "per_arm_nonnegative_affine_upper_envelope",
        "control": "pooled_nonnegative_affine_upper_envelope",
        "calibration_cells": len(calibration), "holdout_cells": len(holdout),
        "control_model": control, "candidate_models": candidate,
        "holdout_predictions": predictions, "loocv": loocv,
        "metrics": {
            "control_median_log_error": control_error,
            "candidate_median_log_error": candidate_error,
            "holdout_median_log_error_improvement": improvement,
            "material_underprediction_prevalence": underprediction,
            "median_overprediction_factor": overprediction,
            "materially_ordered_pairs": ordered_pairs,
            "pairwise_order_agreements": agreements,
            "pairwise_order_agreement": pairwise,
            "near_minimum_cases": near_cases,
            "near_minimum_case_prevalence": near_prevalence,
            "loocv_candidate_better_folds": better_folds,
        },
        "case_decisions": decisions, "conditions": conditions, "decision": decision,
        "candidate_implemented_in_production": False, "production_routing_changed": False,
        "runpod_authorization_request_permitted": decision == freeze["continuation"]["pass"],
    }
    return {**core, "summary_sha256": _digest(core)}


def verify(root: Path, freeze_path: Path, raw_path: Path, summary_path: Path) -> dict[str, Any]:
    freeze, summary = _load(freeze_path), _load(summary_path)
    freeze_core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    _require(freeze["freeze_sha256"] == _digest(freeze_core), "freeze digest")
    _require(freeze["source_closure_sha256"] == _digest(freeze["source_closure"]), "closure digest")
    closure_mismatches = []
    for record in freeze["source_closure"]:
        path = (root / record["path"]).resolve()
        if (not path.is_relative_to(root) or not path.is_file()
                or path.stat().st_size != record["bytes"] or _sha256(path) != record["sha256"]):
            closure_mismatches.append(record["path"])
    _require(not closure_mismatches, f"source closure mismatches: {closure_mismatches}")
    _require(_sha256(raw_path) == freeze["parent"]["raw_sha256"], "raw hash")
    parent_summary = _load(root / freeze["parent"]["summary_path"])
    parent_verification = _load(root / freeze["parent"]["verification_path"])
    _require(_sha256(root / freeze["parent"]["summary_path"])
             == freeze["parent"]["summary_file_sha256"], "parent summary hash")
    _require(_sha256(root / freeze["parent"]["verification_path"])
             == freeze["parent"]["verification_file_sha256"], "parent verification hash")
    _require(parent_summary["decision"] ==
             "go_memory_calibration_only_requires_separate_candidate_freeze", "parent decision")
    _require(parent_verification["status"] == "verified"
             and parent_verification["summary_replay_mismatches"] == 0, "parent verification")
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line]
    _require(len(rows) == 708 and len({row["row_id"] for row in rows}) == 708, "parent rows")
    _require(all(row["status"] == "ok" and row["exact_oracle_agreement"] is True
                 and row["child_exit_code"] == 0 for row in rows), "parent exactness")
    replay = _replay(freeze, rows)
    mismatches = [] if _canonical(replay) == _canonical(summary) else ["summary"]
    _require(not mismatches, "candidate summary replay")
    return {
        "schema": "cm-h6-representation-estimator-independent-verification/v1",
        "status": "verified",
        "freeze_sha256": freeze["freeze_sha256"],
        "parent_raw_sha256": freeze["parent"]["raw_sha256"],
        "summary_sha256": _sha256(summary_path),
        "source_closure_mismatches": closure_mismatches,
        "schedule_mismatches": 0,
        "fit_mismatches": 0,
        "prediction_mismatches": 0,
        "metric_mismatches": 0,
        "decision_mismatches": 0,
        "summary_replay_mismatches": len(mismatches),
        "decision": replay["decision"],
        "production_routing_changed": False,
        "runpod_request_permitted": replay["runpod_authorization_request_permitted"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = verify(
        Path(args.project_root).resolve(), Path(args.freeze).resolve(), Path(args.raw).resolve(),
        Path(args.summary).resolve(),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
