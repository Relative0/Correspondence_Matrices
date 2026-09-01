"""C17 bounded evidence run for the conservative exact CM/GF(2) dispatcher."""
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

from cm_expr_serde import expr_from_json

from .gf2_decomposition import analyze_exact_gf2, analyze_screened_exact_gf2
from .gf2_task_dispatcher import (
    EXHAUSTIVE,
    SCREENED,
    GF2DecompositionTask,
    compile_gf2_dispatcher,
    current_platform_identity,
    freeze_gf2_dispatch_policy,
    save_gf2_dispatch_policy,
    select_gf2_arm,
    verify_gf2_execution,
)
from .portfolio import reference_bits


SCHEMA = "crse-c17-gf2-task-dispatcher-experiment/v1"
METHODS = (
    "direct_exhaustive",
    "direct_screened",
    "c17_dispatch",
    "c17_advice_off",
)


@dataclass(frozen=True)
class GF2DispatcherConfig:
    run_id: str
    seed: int = 20260831
    rounds: int = 3
    max_partitions: int = 64
    materialize_budget: int = 4
    max_seconds: float = 420.0

    def validate(self) -> None:
        if (
            not self.run_id
            or type(self.seed) is not int
            or type(self.rounds) is not int
            or not 1 <= self.rounds <= 10
            or type(self.max_partitions) is not int
            or not 1 <= self.max_partitions <= 64
            or type(self.materialize_budget) is not int
            or not 1 <= self.materialize_budget <= 4
            or type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or not 30 <= self.max_seconds <= 1800
        ):
            raise ValueError("invalid bounded C17 configuration")


def _write_json(path: Path, value: Any, *, exclusive: bool = True) -> None:
    mode = "x" if exclusive else "w"
    with path.open(mode, encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False))
            handle.write("\n")


def _best(analysis) -> dict[str, Any] | None:
    return analysis.best.to_dict() if analysis.best else None


def _task(n_vars: int, config: GF2DispatcherConfig) -> GF2DecompositionTask:
    return GF2DecompositionTask(
        n_vars=n_vars,
        variable_order=tuple(range(n_vars)),
        max_partitions=config.max_partitions,
        materialize_budget=config.materialize_budget,
    )


def functional_replay(
    cases: list[dict[str, Any]], policy: dict[str, Any], config: GF2DispatcherConfig
) -> tuple[dict[str, Any], dict[str, int], dict[str, int], dict[str, dict[str, Any] | None]]:
    decisions: dict[str, int] = {}
    expected: dict[str, int] = {}
    expected_bests: dict[str, dict[str, Any] | None] = {}
    semantic_mismatches = artifact_mismatches = shadow_mismatches = 0
    for case in cases:
        n_vars = case["n_vars"]
        bits = reference_bits(expr_from_json(case["expression_v2"]), n_vars)
        exhaustive = analyze_exact_gf2(bits, n_vars, max_partitions=config.max_partitions)
        screened = analyze_screened_exact_gf2(
            bits, n_vars, max_partitions=config.max_partitions,
            materialize_budget=config.materialize_budget,
        )
        expected_best = _best(exhaustive)
        if _best(screened) != expected_best:
            artifact_mismatches += 1
        expected[case["case_id"]] = bits
        expected_bests[case["case_id"]] = expected_best
        if any(candidate.reconstruct() != bits for candidate in exhaustive.candidates):
            semantic_mismatches += 1
        if any(candidate.reconstruct() != bits for candidate in screened.candidates):
            semantic_mismatches += 1
        task = _task(n_vars, config)
        selected = select_gf2_arm(policy, task, advice_enabled=True)
        advice_off = select_gf2_arm(policy, task, advice_enabled=False)
        for decision in (selected, advice_off):
            decisions[decision.reason] = decisions.get(decision.reason, 0) + 1
        expected_arm = EXHAUSTIVE if n_vars <= 3 else SCREENED
        if selected.selected_arm != expected_arm or advice_off.selected_arm != EXHAUSTIVE:
            artifact_mismatches += 1
        # Shadow proof is the independently computed exhaustive/screened identity
        # comparison above.  Re-executing both arms through the wrapper would add
        # no new semantic observation and would multiply the bounded precheck cost.
        if _best(screened) != expected_best:
            shadow_mismatches += 1
    summary = {
        "cases": len(cases),
        "semantic_mismatches": semantic_mismatches,
        "artifact_or_policy_mismatches": artifact_mismatches,
        "shadow_mismatches": shadow_mismatches,
        "all_exact": not (semantic_mismatches or artifact_mismatches or shadow_mismatches),
    }
    return summary, decisions, expected, expected_bests


def _measure_direct(method: str, case: dict[str, Any], expression: Any,
                    expected_bits: int, expected_best: dict[str, Any] | None,
                    config: GF2DispatcherConfig, round_index: int) -> dict[str, Any]:
    n_vars = case["n_vars"]
    started = time.perf_counter_ns()
    bits = reference_bits(expression, n_vars)
    representation_ns = max(1, time.perf_counter_ns() - started)
    analysis_started = time.perf_counter_ns()
    if method == "direct_exhaustive":
        analysis = analyze_exact_gf2(bits, n_vars, max_partitions=config.max_partitions)
        selected_arm = EXHAUSTIVE
    else:
        analysis = analyze_screened_exact_gf2(
            bits, n_vars, max_partitions=config.max_partitions,
            materialize_budget=config.materialize_budget,
        )
        selected_arm = SCREENED
    analysis_ns = max(1, time.perf_counter_ns() - analysis_started)
    check_started = time.perf_counter_ns()
    best = _best(analysis)
    exact = analysis.source_sha256 and all(item.reconstruct() == bits for item in analysis.candidates)
    exact_check_ns = max(1, time.perf_counter_ns() - check_started)
    return {
        "case_id": case["case_id"], "split": case["split"], "source_kind": case["source_kind"],
        "n_vars": n_vars, "method": method, "round": round_index,
        "selected_arm": selected_arm, "decision_reason": "direct_control",
        "representation_ns": representation_ns, "policy_ns": 0,
        "analysis_ns": analysis_ns, "exact_check_ns": exact_check_ns,
        "shadow_ns": 0, "total_ns": representation_ns + analysis_ns + exact_check_ns,
        "partitions_tested": analysis.partitions_tested,
        "descriptors_screened": analysis.descriptors_screened,
        "artifacts_materialized": analysis.artifacts_materialized,
        "semantic_mismatches": int(bits != expected_bits or not exact),
        "artifact_mismatches": int(best != expected_best),
        "best_artifact_sha256": best["payload_sha256"] if best else None,
        "source_sha256": analysis.source_sha256,
    }


def _measure_dispatch(method: str, case: dict[str, Any], expression: Any,
                      expected_bits: int, expected_best: dict[str, Any] | None,
                      dispatcher: Any, policy_sha256: str, round_index: int) -> dict[str, Any]:
    started = time.perf_counter_ns()
    bits = reference_bits(expression, case["n_vars"])
    representation_ns = max(1, time.perf_counter_ns() - started)
    execution = dispatcher.execute(bits)
    document = execution.to_dict()
    verify_gf2_execution(document, bits, policy_sha256=policy_sha256)
    best = execution.best_artifact
    return {
        "case_id": case["case_id"], "split": case["split"], "source_kind": case["source_kind"],
        "n_vars": case["n_vars"], "method": method, "round": round_index,
        "selected_arm": execution.selected_arm, "decision_reason": execution.decision_reason,
        "representation_ns": representation_ns, "policy_ns": execution.policy_ns,
        "analysis_ns": execution.analysis_ns, "exact_check_ns": execution.exact_check_ns,
        "shadow_ns": execution.shadow_ns, "total_ns": representation_ns + execution.total_ns,
        "partitions_tested": execution.partitions_tested,
        "descriptors_screened": execution.descriptors_screened,
        "artifacts_materialized": execution.artifacts_materialized,
        "semantic_mismatches": int(bits != expected_bits),
        "artifact_mismatches": int(best != expected_best),
        "best_artifact_sha256": best["payload_sha256"] if best else None,
        "source_sha256": execution.source_sha256,
    }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))]


def summarize(measurements: list[dict[str, Any]], functional: dict[str, Any]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in measurements:
        groups.setdefault((row["case_id"], row["method"]), []).append(row)
    medians: dict[tuple[str, str], dict[str, int]] = {}
    fields = ("representation_ns", "policy_ns", "analysis_ns", "exact_check_ns", "total_ns")
    for key, rows in groups.items():
        medians[key] = {field: int(statistics.median(row[field] for row in rows)) for field in fields}
    case_ids = sorted({row["case_id"] for row in measurements})
    totals = {
        method: {field: sum(medians[(case_id, method)][field] for case_id in case_ids)
                 for field in fields}
        for method in METHODS
    }
    dispatch_speeds = [
        medians[(case_id, "direct_exhaustive")]["total_ns"]
        / medians[(case_id, "c17_dispatch")]["total_ns"]
        for case_id in case_ids
    ]
    screened_speeds = [
        medians[(case_id, "direct_exhaustive")]["total_ns"]
        / medians[(case_id, "direct_screened")]["total_ns"]
        for case_id in case_ids
    ]
    speedup = {
        "c17_over_direct_exhaustive": totals["direct_exhaustive"]["total_ns"] / totals["c17_dispatch"]["total_ns"],
        "c17_case_median": statistics.median(dispatch_speeds),
        "c17_case_minimum": min(dispatch_speeds),
        "c17_case_p95_slow_tail": _percentile(dispatch_speeds, 0.05),
        "direct_screened_over_exhaustive": totals["direct_exhaustive"]["total_ns"] / totals["direct_screened"]["total_ns"],
        "advice_off_over_direct_exhaustive": totals["direct_exhaustive"]["total_ns"] / totals["c17_advice_off"]["total_ns"],
        "screened_case_minimum": min(screened_speeds),
    }
    criteria = {
        "functional_exactness": functional["all_exact"],
        "timed_exactness": not any(row["semantic_mismatches"] or row["artifact_mismatches"] for row in measurements),
        "aggregate_speedup_at_least_1_25x": speedup["c17_over_direct_exhaustive"] >= 1.25,
        "slow_tail_at_least_1_20x": speedup["c17_case_p95_slow_tail"] >= 1.20,
        "minimum_case_at_least_0_97x": speedup["c17_case_minimum"] >= 0.97,
        "advice_off_within_3_percent": 0.97 <= speedup["advice_off_over_direct_exhaustive"] <= 1.03,
    }
    return {
        "median_case_sum_ns": totals,
        "speedup": speedup,
        "criteria": criteria,
        "exactness_gate": criteria["functional_exactness"] and criteria["timed_exactness"],
        "local_research_gate": all(criteria.values()),
        "timing_is_machine_specific": True,
    }


def render_report(result: dict[str, Any]) -> str:
    summary, speed = result["summary"], result["summary"]["speedup"]
    return f"""# C17 exact CM/GF(2) task dispatcher run

Status: **{result['status']}**  
Local research gate: **{'pass' if summary['local_research_gate'] else 'not passed'}**

The frozen dispatcher bypasses screening for `n <= 3`, selects the exact screened tail for
larger admitted tasks on the calibrated platform, and returns to exhaustive analysis when
advice is disabled. This is reused C16 engineering evidence, not an independent transfer set.

## Results

- Exact functional, timed, and shadow mismatches: **{result['semantic_or_artifact_mismatches']}**
- C17 versus direct exhaustive, whole path: **{speed['c17_over_direct_exhaustive']:.4f}x**
- Slow-tail (5th percentile) per-case speedup: **{speed['c17_case_p95_slow_tail']:.4f}x**
- Minimum per-case speedup: **{speed['c17_case_minimum']:.4f}x**
- Advice-off versus direct exhaustive: **{speed['advice_off_over_direct_exhaustive']:.4f}x**

Production promotion remains false until C18 tests the frozen policy on independent source
families. No learned or approximate truth values are used.
"""


def run_gf2_dispatcher_experiment(
    config: GF2DispatcherConfig, output: Path, dataset_path: Path, root: Path
) -> dict[str, Any]:
    config.validate()
    wall_started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = dataset["cases"]
    if len(cases) != 40:
        raise ValueError("C17 requires the frozen 40-case C16 engineering corpus")
    policy = freeze_gf2_dispatch_policy()
    save_gf2_dispatch_policy(policy, output / "policy.json")
    _write_json(output / "run_spec.json", {
        "schema": SCHEMA, "config": asdict(config), "methods": list(METHODS),
        "corpus_role": "reused_post_hoc_engineering_evidence",
        "predeclared_gates": {"aggregate_speedup": 1.25, "slow_tail": 1.20,
                              "minimum_case": 0.97, "advice_off_tolerance": 0.03},
        "production_promotion": False,
    })
    _write_json(output / "dataset_manifest.json", {
        "schema": "crse-c17-reused-c16-dataset-manifest/v1",
        "source_path": str(dataset_path.relative_to(root)).replace("\\", "/"),
        "source_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "rows": len(cases), "training_use": False,
        "independent_transfer": False, "reused_from": "C16",
    })
    functional, decisions, expected_bits, expected_best = functional_replay(cases, policy, config)
    _write_json(output / "functional.json", {"summary": functional, "decisions": decisions})

    expressions = {}
    for case in cases:
        expression = expr_from_json(case["expression_v2"])
        expressions[case["case_id"]] = expression
    dispatchers = {}
    for method, advice in (("c17_dispatch", True), ("c17_advice_off", False)):
        for n_vars in sorted({case["n_vars"] for case in cases}):
            dispatchers[(method, n_vars)] = compile_gf2_dispatcher(
                policy, _task(n_vars, config), advice_enabled=advice
            )

    measurements: list[dict[str, Any]] = []
    rng = random.Random(f"{config.seed}:c17-balanced-method-order/v1")
    for round_index in range(config.rounds):
        order = [(case, method) for case in cases for method in METHODS]
        rng.shuffle(order)
        for case, method in order:
            if time.perf_counter() - wall_started > config.max_seconds:
                raise TimeoutError("C17 experiment exceeded wall budget")
            case_id = case["case_id"]
            if method.startswith("direct_"):
                row = _measure_direct(method, case, expressions[case_id], expected_bits[case_id],
                                      expected_best[case_id], config, round_index)
            else:
                row = _measure_dispatch(method, case, expressions[case_id], expected_bits[case_id],
                                        expected_best[case_id], dispatchers[(method, case["n_vars"])],
                                        policy["policy_sha256"], round_index)
            measurements.append(row)
    _write_jsonl(output / "measurements.jsonl", measurements)
    summary = summarize(measurements, functional)
    mismatches = (
        functional["semantic_mismatches"] + functional["artifact_or_policy_mismatches"]
        + functional["shadow_mismatches"]
        + sum(row["semantic_mismatches"] + row["artifact_mismatches"] for row in measurements)
    )
    result = {
        "schema": SCHEMA,
        "status": "complete" if not mismatches and summary["exactness_gate"] else "failed",
        "config": asdict(config), "wall_seconds": time.perf_counter() - wall_started,
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "identity": current_platform_identity(),
                        "thread_environment": {name: os.environ.get(name) for name in
                                               ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
        "dataset": {"rows": len(cases), "reused_from": "C16", "independent_transfer": False},
        "functional": functional, "decision_counts": decisions,
        "measurement_rows": len(measurements),
        "semantic_or_artifact_mismatches": mismatches, "summary": summary,
        "claims": {"learned_or_approximate_values": False, "exact_dispatch": True,
                   "production_promotion": False, "requires_c18_transfer": True},
        "runpod": {"used": False, "cost_usd": 0.0, "reason": "local policy engineering run"},
    }
    _write_json(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")

    source_rel = (
        "cmbench/recognition/gf2_decomposition.py",
        "cmbench/recognition/gf2_task_dispatcher.py",
        "cmbench/recognition/gf2_task_dispatcher_experiment.py",
        "scripts/cm_recognition_gf2_task_dispatcher.py",
        "scripts/crse_gf2_task_dispatcher_verify.py",
    )
    artifact_rel = ("run_spec.json", "dataset_manifest.json", "policy.json", "functional.json",
                    "measurements.jsonl", "results.json", "report.md")
    manifest = {
        "schema": "crse-c17-run-manifest/v1",
        "sources": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in source_rel},
        "artifacts": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in artifact_rel},
    }
    _write_json(output / "manifest.json", manifest)
    return result
