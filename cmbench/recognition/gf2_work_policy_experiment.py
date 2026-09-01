"""C19 fit/validate/freeze/confirm study for a cheap exact GF(2) arm gate."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time
from typing import Any

from .gf2_decomposition import analyze_exact_gf2, analyze_screened_exact_gf2
from .gf2_task_dispatcher import (
    EXHAUSTIVE, SCREENED, GF2DecompositionTask, compile_gf2_dispatcher,
    load_gf2_dispatch_policy, verify_gf2_execution)
from .gf2_work_policy import (
    cheap_truth_features, evaluate_tree, fit_cost_tree, fixed_tree, freeze_policy,
    save_policy)

SCHEMA = "crse-c19-gf2-cheap-work-policy-experiment/v1"
CALIBRATION_METHODS = ("direct_exhaustive", "direct_screened")
CANDIDATES = ("always_exhaustive", "fixed_n3", "fixed_n4", "learned_stump", "learned_depth2")
CONFIRMATION_METHODS = (
    "direct_exhaustive", "direct_screened", "c17_wrapper",
    "direct_n3", "direct_n4", "c19_selected")


@dataclass(frozen=True)
class C19Config:
    run_id: str
    seed: int = 20260831
    rounds: int = 5
    max_partitions: int = 64
    materialize_budget: int = 4
    max_seconds: float = 600.0

    def validate(self) -> None:
        if (not self.run_id or type(self.rounds) is not int or not 3 <= self.rounds <= 11
                or self.max_partitions != 64 or self.materialize_budget != 4
                or type(self.max_seconds) not in (int, float) or not math.isfinite(self.max_seconds)
                or not 120 <= self.max_seconds <= 1800):
            raise ValueError("invalid C19 experiment bounds")


def _write(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _best(analysis):
    return analysis.best.to_dict() if analysis.best else None


def _bits(case):
    return int(case["truth_bits_hex"], 16)


def _analyze(arm: str, bits: int, n_vars: int, config: C19Config):
    if arm == EXHAUSTIVE:
        return analyze_exact_gf2(bits, n_vars, max_partitions=config.max_partitions)
    if arm == SCREENED:
        return analyze_screened_exact_gf2(
            bits, n_vars, max_partitions=config.max_partitions,
            materialize_budget=config.materialize_budget)
    raise ValueError("unknown C19 exact arm")


def _functional(cases, config):
    expected, mismatches = {}, 0
    for case in cases:
        bits, n_vars = _bits(case), case["n_vars"]
        exhaustive, screened = _analyze(EXHAUSTIVE, bits, n_vars, config), _analyze(SCREENED, bits, n_vars, config)
        expected[case["case_id"]] = _best(exhaustive)
        if (_best(exhaustive) != _best(screened)
                or any(item.reconstruct() != bits for item in exhaustive.candidates)
                or any(item.reconstruct() != bits for item in screened.candidates)):
            mismatches += 1
    return {"cases": len(cases), "mismatches": mismatches, "all_exact": mismatches == 0}, expected


def _measure_arm(case, arm, expected_best, config, method, round_index, decision_ns=0):
    bits, n_vars = _bits(case), case["n_vars"]
    started = time.perf_counter_ns()
    analysis = _analyze(arm, bits, n_vars, config)
    analysis_ns = max(1, time.perf_counter_ns() - started)
    checked = time.perf_counter_ns()
    best = _best(analysis)
    exact = all(item.reconstruct() == bits for item in analysis.candidates)
    exact_check_ns = max(1, time.perf_counter_ns() - checked)
    return {
        "case_id": case["case_id"], "split": case["split"], "cluster_id": case["cluster_id"],
        "n_vars": n_vars, "method": method, "round": round_index, "selected_arm": arm,
        "decision_ns": decision_ns, "analysis_ns": analysis_ns, "exact_check_ns": exact_check_ns,
        "total_ns": decision_ns + analysis_ns + exact_check_ns,
        "semantic_mismatches": int(not exact), "artifact_mismatches": int(best != expected_best[case["case_id"]]),
        "best_artifact_sha256": best["payload_sha256"] if best else None,
        "features": cheap_truth_features(bits, n_vars),
    }


def _select(candidate: str, tree: dict[str, Any], bits: int, n_vars: int) -> tuple[str, int]:
    started = time.perf_counter_ns()
    if candidate == "always_exhaustive":
        arm = EXHAUSTIVE
    elif candidate == "fixed_n3":
        arm = EXHAUSTIVE if n_vars <= 3 else SCREENED
    elif candidate == "fixed_n4":
        arm = EXHAUSTIVE if n_vars <= 4 else SCREENED
    else:
        arm = evaluate_tree(tree, cheap_truth_features(bits, n_vars))
    return arm, max(1, time.perf_counter_ns() - started)


def _measure_candidate(case, candidate, tree, expected_best, config, round_index):
    arm, decision_ns = _select(candidate, tree, _bits(case), case["n_vars"])
    return _measure_arm(case, arm, expected_best, config, candidate, round_index, decision_ns)


def _median_rows(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    grouped = {}
    for row in rows:
        grouped.setdefault((row["case_id"], row["method"]), []).append(row)
    result = {}
    for key, values in grouped.items():
        exemplar = values[0]
        result[key] = {
            "case_id": key[0], "method": key[1], "n_vars": exemplar["n_vars"],
            "features": exemplar["features"], "selected_arm": statistics.mode(row["selected_arm"] for row in values),
            "decision_ns": int(statistics.median(row["decision_ns"] for row in values)),
            "analysis_ns": int(statistics.median(row["analysis_ns"] for row in values)),
            "exact_check_ns": int(statistics.median(row["exact_check_ns"] for row in values)),
            "total_ns": int(statistics.median(row["total_ns"] for row in values)),
        }
    return result


def _candidate_summary(rows, candidates=CANDIDATES):
    med = _median_rows(rows)
    case_ids = sorted({row["case_id"] for row in rows})
    exhaustive = {case: med[(case, "direct_exhaustive")]["total_ns"] for case in case_ids}
    screened = {case: med[(case, "direct_screened")]["total_ns"] for case in case_ids}
    output = {}
    for candidate in candidates:
        selected = {case: med[(case, candidate)]["total_ns"] for case in case_ids}
        speedups = [exhaustive[case] / selected[case] for case in case_ids]
        regrets = [selected[case] / min(exhaustive[case], screened[case]) for case in case_ids]
        output[candidate] = {
            "aggregate_speedup_over_exhaustive": sum(exhaustive.values()) / sum(selected.values()),
            "minimum_case_speedup_over_exhaustive": min(speedups),
            "median_case_speedup_over_exhaustive": statistics.median(speedups),
            "maximum_regret_over_best_exact_arm": max(regrets),
            "screened_cases": sum(med[(case, candidate)]["selected_arm"] == SCREENED for case in case_ids),
            "cases": len(case_ids),
        }
    return output


def _confirmation_summary(rows):
    med = _median_rows(rows)
    case_ids = sorted({row["case_id"] for row in rows})
    base = {case: med[(case, "direct_exhaustive")]["total_ns"] for case in case_ids}
    screened = {case: med[(case, "direct_screened")]["total_ns"] for case in case_ids}
    output = {}
    for method in CONFIRMATION_METHODS:
        values = {case: med[(case, method)]["total_ns"] for case in case_ids}
        speedups = [base[case] / values[case] for case in case_ids]
        regrets = [values[case] / min(base[case], screened[case]) for case in case_ids]
        output[method] = {
            "aggregate_speedup_over_exhaustive": sum(base.values()) / sum(values.values()),
            "minimum_case_speedup_over_exhaustive": min(speedups),
            "median_case_speedup_over_exhaustive": statistics.median(speedups),
            "maximum_regret_over_best_direct_arm": max(regrets),
            "screened_cases": sum(med[(case, method)]["selected_arm"] == SCREENED for case in case_ids),
        }
    return output


def _fit_rows(development_rows):
    med = _median_rows(development_rows)
    case_ids = sorted({row["case_id"] for row in development_rows})
    return [{"features": med[(case, "direct_exhaustive")]["features"],
             "costs_ns": {EXHAUSTIVE: med[(case, "direct_exhaustive")]["total_ns"],
                          SCREENED: med[(case, "direct_screened")]["total_ns"]}}
            for case in case_ids]


def render_report(result):
    confirm, selected = result["confirmation"], result["policy"]["selected_candidate"]
    chosen = confirm["methods"]["c19_selected"]
    return f"""# C19 cheap exact CM/GF(2) work policy

Status: **{result['status']}**  
Selected validation policy: **{selected}**

The 96-case LogikBench corpus was split by source cluster before timing. Development fitting and
validation selection completed before the policy was serialized; only then was the 24-case
confirmation split timed. Every selected arm remained exact.

## Sealed confirmation

- C19 aggregate speedup over exhaustive: **{chosen['aggregate_speedup_over_exhaustive']:.4f}x**
- Minimum per-case speedup over exhaustive: **{chosen['minimum_case_speedup_over_exhaustive']:.4f}x**
- Maximum regret over the best direct exact arm: **{chosen['maximum_regret_over_best_direct_arm']:.4f}x**
- Screened cases: **{chosen['screened_cases']} / 24**

Production promotion remains false. Confirmation is source-disjoint but local and one-machine;
the policy must also survive repeated C18/VTR reporting as retrospective evidence and a fresh
second-source or second-machine confirmation.
"""


def run(config: C19Config, output: Path, dataset_path: Path, c17_policy_path: Path, root: Path):
    config.validate()
    wall = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset = json.loads(dataset_path.read_text())
    c17_policy = load_gf2_dispatch_policy(c17_policy_path)
    cases = dataset["cases"]
    by_split = {split: [case for case in cases if case["split"] == split]
                for split in ("development", "validation", "confirmation")}
    if {key: len(value) for key, value in by_split.items()} != {
            "development": 48, "validation": 24, "confirmation": 24}:
        raise ValueError("C19 frozen split changed")
    _write(output / "run_spec.json", {
        "schema": SCHEMA, "config": asdict(config), "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "phase_order": ["functional", "development_direct", "fit", "validation_candidates",
                        "freeze_policy", "confirmation"],
        "candidates": list(CANDIDATES), "confirmation_methods": list(CONFIRMATION_METHODS),
        "selection_gate": {"minimum_case_speedup_over_exhaustive": 0.97,
                           "aggregate_speedup_over_exhaustive": 1.0},
        "production_promotion": False})
    functional, expected = _functional(cases, config)
    _write(output / "functional.json", functional)
    rng = random.Random(f"{config.seed}:c19-balanced/v1")

    development_rows = []
    for round_index in range(config.rounds):
        order = [(case, method) for case in by_split["development"] for method in CALIBRATION_METHODS]
        rng.shuffle(order)
        for case, method in order:
            arm = EXHAUSTIVE if method == "direct_exhaustive" else SCREENED
            development_rows.append(_measure_arm(case, arm, expected, config, method, round_index))
    _write_jsonl(output / "development_measurements.jsonl", development_rows)
    fitted = _fit_rows(development_rows)
    stump, _ = fit_cost_tree(fitted, 1)
    depth2, _ = fit_cost_tree(fitted, 2)
    trees = {
        "always_exhaustive": {"kind": "leaf", "arm": EXHAUSTIVE},
        "fixed_n3": fixed_tree(3), "fixed_n4": fixed_tree(4),
        "learned_stump": stump, "learned_depth2": depth2,
    }

    validation_rows = []
    validation_methods = (*CALIBRATION_METHODS, *CANDIDATES)
    for round_index in range(config.rounds):
        order = [(case, method) for case in by_split["validation"] for method in validation_methods]
        rng.shuffle(order)
        for case, method in order:
            if method in CALIBRATION_METHODS:
                arm = EXHAUSTIVE if method == "direct_exhaustive" else SCREENED
                row = _measure_arm(case, arm, expected, config, method, round_index)
            else:
                row = _measure_candidate(case, method, trees[method], expected, config, round_index)
            validation_rows.append(row)
    _write_jsonl(output / "validation_measurements.jsonl", validation_rows)
    validation = _candidate_summary(validation_rows)
    eligible = [name for name in CANDIDATES
                if validation[name]["minimum_case_speedup_over_exhaustive"] >= 0.97
                and validation[name]["aggregate_speedup_over_exhaustive"] >= 1.0]
    selected = max(eligible, key=lambda name: (validation[name]["aggregate_speedup_over_exhaustive"], name)) if eligible else "always_exhaustive"
    calibration_sha = hashlib.sha256((output / "development_measurements.jsonl").read_bytes()
                                     + (output / "validation_measurements.jsonl").read_bytes()).hexdigest()
    policy = freeze_policy(
        selected_candidate=selected, tree=trees[selected],
        dataset_sha256=hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        calibration_sha256=calibration_sha, development_rows=48, validation_rows=24,
        candidate_validation=validation)
    save_policy(policy, output / "policy.json")
    confirmation_path = output / "confirmation_measurements.jsonl"
    if confirmation_path.exists():
        raise RuntimeError("C19 confirmation existed before policy freeze")
    _write(output / "freeze_event.json", {
        "schema": "crse-c19-policy-freeze-event/v1", "policy_sha256": policy["policy_sha256"],
        "confirmation_rows_existing_at_freeze": False,
        "confirmation_policy_refit_allowed": False})

    c17_dispatchers = {}
    for n_vars in sorted({case["n_vars"] for case in by_split["confirmation"]}):
        task = GF2DecompositionTask(n_vars, tuple(range(n_vars)), 64, 4)
        c17_dispatchers[n_vars] = compile_gf2_dispatcher(c17_policy, task)
    confirmation_rows = []
    for round_index in range(config.rounds):
        order = [(case, method) for case in by_split["confirmation"] for method in CONFIRMATION_METHODS]
        rng.shuffle(order)
        for case, method in order:
            if time.perf_counter() - wall > config.max_seconds:
                raise TimeoutError("C19 experiment exceeded wall bound")
            if method in CALIBRATION_METHODS:
                arm = EXHAUSTIVE if method == "direct_exhaustive" else SCREENED
                row = _measure_arm(case, arm, expected, config, method, round_index)
            elif method == "c17_wrapper":
                bits = _bits(case)
                started = time.perf_counter_ns()
                execution = c17_dispatchers[case["n_vars"]].execute(bits)
                call_ns = max(1, time.perf_counter_ns() - started)
                verify_gf2_execution(execution.to_dict(), bits, policy_sha256=c17_policy["policy_sha256"])
                best = execution.best_artifact
                row = {
                    "case_id": case["case_id"], "split": case["split"], "cluster_id": case["cluster_id"],
                    "n_vars": case["n_vars"], "method": method, "round": round_index,
                    "selected_arm": execution.selected_arm, "decision_ns": execution.policy_ns,
                    "analysis_ns": execution.analysis_ns, "exact_check_ns": execution.exact_check_ns,
                    "total_ns": call_ns + execution.policy_ns,
                    "semantic_mismatches": 0, "artifact_mismatches": int(best != expected[case["case_id"]]),
                    "best_artifact_sha256": best["payload_sha256"] if best else None,
                    "features": cheap_truth_features(bits, case["n_vars"]),
                }
            else:
                candidate = ("fixed_n3" if method == "direct_n3" else
                             "fixed_n4" if method == "direct_n4" else selected)
                row = _measure_candidate(case, candidate, trees[candidate], expected, config, round_index)
                row["method"] = method
            confirmation_rows.append(row)
    _write_jsonl(confirmation_path, confirmation_rows)
    confirmation_methods = _confirmation_summary(confirmation_rows)
    mismatches = functional["mismatches"] + sum(
        row["semantic_mismatches"] + row["artifact_mismatches"]
        for row in development_rows + validation_rows + confirmation_rows)
    chosen = confirmation_methods["c19_selected"]
    confirmation_gate = (chosen["minimum_case_speedup_over_exhaustive"] >= 0.97
                         and chosen["aggregate_speedup_over_exhaustive"] >= 1.0)
    result = {
        "schema": SCHEMA, "status": "complete" if mismatches == 0 else "failed",
        "config": asdict(config), "wall_seconds": time.perf_counter() - wall,
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "thread_environment": {name: os.environ.get(name) for name in
                                               ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
        "dataset": {"cases": 96, "development": 48, "validation": 24, "confirmation": 24,
                    "source_family": "LogikBench", "confirmation_policy_refit": False},
        "functional": functional, "policy": {"path": "policy.json", "policy_sha256": policy["policy_sha256"],
                                              "selected_candidate": selected},
        "validation": {"eligible_candidates": eligible, "methods": validation},
        "confirmation": {"methods": confirmation_methods, "gate": confirmation_gate,
                         "single_machine": True},
        "semantic_or_artifact_mismatches": mismatches,
        "claims": {"learned_truth_values": False, "exact_arm_selection_only": True,
                   "production_promotion": False},
        "runpod": {"used": False, "cost_usd": 0.0,
                   "reused_prior_verified_conversion_artifacts": True},
    }
    _write(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    source_names = ("cmbench/recognition/gf2_work_policy.py",
                    "cmbench/recognition/gf2_work_policy_experiment.py",
                    "scripts/cm_recognition_c19_gf2_work_policy.py")
    artifact_names = ("run_spec.json", "functional.json", "development_measurements.jsonl",
                      "validation_measurements.jsonl", "policy.json", "freeze_event.json",
                      "confirmation_measurements.jsonl", "results.json", "report.md")
    _write(output / "manifest.json", {
        "schema": "crse-c19-run-manifest/v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "sources": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in source_names},
        "artifacts": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in artifact_names},
    })
    return result
