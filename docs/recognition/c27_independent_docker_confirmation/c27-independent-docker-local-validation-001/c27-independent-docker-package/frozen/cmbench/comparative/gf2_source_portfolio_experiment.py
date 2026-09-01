"""C24 end-to-end evaluation of the frozen C22 exact GF(2) portfolio."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time
import tracemalloc
from typing import Any

from cmbench.recognition.gf2_decomposition import ExactGF2Artifact
from cmbench.recognition.gf2_source_portfolio import load_source_portfolio_policy
from cmbench.recognition.gf2_source_portfolio_boundary import (
    execute_source_portfolio_boundary,
    verify_source_portfolio_boundary_result,
)
from cmbench.recognition.gf2_work_policy import load_policy
from cmbench.recognition.gf2_work_policy_compiler import compile_work_policy
from cmbench.recognition.yosys_unused_gf2_data import validate_dataset

from .contracts import canonical_bytes
from .gf2_decomposition import decomposition_contract, delivered_document, delivered_sha256
from .gf2_method_table import execute_method
from .gf2_table_experiment import C21Config, _memory_cases, build_oracles

SCHEMA = "crse-c24-c22-boundary-experiment/v1"
METHODS = (
    "direct_exhaustive",
    "direct_screened",
    "direct_compiled_screened",
    "direct_source_packed",
    "c22_advice_on",
    "c22_advice_off",
    "c22_advice_on_shadow",
    "c22_advice_off_shadow",
)
DEPLOYABLE_METHODS = tuple(method for method in METHODS if not method.endswith("_shadow"))
DIRECT_METHODS = {
    "direct_exhaustive": "cm_exhaustive",
    "direct_screened": "cm_screened",
    "direct_compiled_screened": "cm_compiled_screened",
    "direct_source_packed": "source_packed_anf",
}
BOUNDARY_SWITCHES = {
    "c22_advice_on": (True, False),
    "c22_advice_off": (False, False),
    "c22_advice_on_shadow": (True, True),
    "c22_advice_off_shadow": (False, True),
}
TIMING_FIELDS = ("request_ns", "response_serialization_verify_ns", "wrapper_ns")


@dataclass(frozen=True)
class C24Config:
    run_id: str
    seed: int = 20260831
    rounds: int = 9
    max_partitions: int = 64
    materialize_budget: int = 4
    memory_cases_per_width: int = 2
    max_seconds: float = 1200.0

    def validate(self) -> None:
        if (
            not self.run_id
            or type(self.rounds) is not int
            or not 3 <= self.rounds <= 9
            or self.max_partitions != 64
            or self.materialize_budget != 4
            or type(self.memory_cases_per_width) is not int
            or not 1 <= self.memory_cases_per_width <= 3
            or type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or not 180 <= self.max_seconds <= 1800
        ):
            raise ValueError("invalid C24 experiment bounds")

    def oracle_config(self) -> C21Config:
        return C21Config(
            run_id=self.run_id,
            seed=self.seed,
            rounds=self.rounds,
            max_partitions=self.max_partitions,
            materialize_budget=self.materialize_budget,
            memory_cases_per_width=self.memory_cases_per_width,
            max_seconds=self.max_seconds,
        )


def _write(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute_benchmark_method(
    *,
    case: dict[str, Any],
    contract: dict[str, Any],
    method: str,
    required_best: dict[str, Any] | None,
    policy_path: Path,
    compiled_policy,
    max_partitions: int,
    materialize_budget: int,
) -> dict[str, Any]:
    """Execute and serialize one complete fresh request under a common outer clock."""
    if method not in METHODS:
        raise ValueError("unknown C24 method")
    total_started = time.perf_counter_ns()
    started = time.perf_counter_ns()
    if method in DIRECT_METHODS:
        direct = DIRECT_METHODS[method]
        execution = execute_method(
            case=case,
            contract=contract,
            method=direct,
            required_best=required_best,
            compiled_policy=compiled_policy if direct == "cm_compiled_screened" else None,
            max_partitions=max_partitions,
            materialize_budget=materialize_budget,
        )
        best = execution["identity"]["best_artifact"]
        exact = execution["identity"]["exact_check_passed"]
        selected_arm = execution["selected_exact_arm"]
        requested_arm = direct
        fallback_used = False
        shadow_match = None
        stage_timings = execution["timings_ns"]
    else:
        advice_enabled, shadow = BOUNDARY_SWITCHES[method]
        boundary = execute_source_portfolio_boundary(
            case, policy_path, advice_enabled=advice_enabled, shadow=shadow)
        execution = boundary.to_dict()
        if execution["status"] != "ok":
            raise RuntimeError("C24 valid case was refused")
        verify_source_portfolio_boundary_result(execution, case, required_best=required_best)
        best = execution["best_artifact"]
        exact = execution["exact_check_passed"]
        selected_arm = execution["selected_arm"]
        requested_arm = execution["requested_arm"]
        fallback_used = execution["fallback_used"]
        shadow_match = execution["execution"]["shadow_best_identity_match"]
        stage_timings = execution["timings_ns"]
    request_ns = max(1, time.perf_counter_ns() - started)

    started = time.perf_counter_ns()
    delivered = canonical_bytes(delivered_document(best))
    artifact_sha256 = hashlib.sha256(delivered).hexdigest()
    frozen_bits = int(case["truth_bits_hex"], 16)
    exact = (
        exact
        and best == required_best
        and artifact_sha256 == delivered_sha256(required_best)
        and (best is None or ExactGF2Artifact.from_dict(best).reconstruct() == frozen_bits)
    )
    if not exact:
        raise RuntimeError("C24 response failed exact delivery verification")
    response_ns = max(1, time.perf_counter_ns() - started)
    elapsed = max(1, time.perf_counter_ns() - total_started)
    wrapper_ns = max(0, elapsed - request_ns - response_ns)
    timings = {
        "request_ns": request_ns,
        "response_serialization_verify_ns": response_ns,
        "wrapper_ns": wrapper_ns,
    }
    timings["task_total_ns"] = sum(timings.values())
    return {
        "status": "ok",
        "method": method,
        "requested_arm": requested_arm,
        "selected_arm": selected_arm,
        "fallback_used": fallback_used,
        "shadow_best_identity_match": shadow_match,
        "exact_check_passed": True,
        "best_artifact_sha256": best["payload_sha256"] if best else None,
        "artifact_sha256": artifact_sha256,
        "artifact_bytes": len(delivered),
        "timings_ns": timings,
        "stage_timings_ns": stage_timings,
    }


def _measurement_row(case: dict[str, Any], method: str, round_index: int,
                     execution: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "split": case["split"],
        "cluster_id": case["cluster_id"],
        "n_vars": case["n_vars"],
        "method": method,
        "round": round_index,
        **execution,
    }


def _median_rows(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, int]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["case_id"], row["method"]), []).append(row)
    return {
        key: {
            field: int(statistics.median(row["timings_ns"][field] for row in values))
            for field in (*TIMING_FIELDS, "task_total_ns")
        }
        for key, values in grouped.items()
    }


def summarize(rows: list[dict[str, Any]], memory_rows: list[dict[str, Any]],
              controls: dict[str, Any]) -> dict[str, Any]:
    medians = _median_rows(rows)
    cases = sorted({row["case_id"] for row in rows})
    exhaustive = {case: medians[(case, "direct_exhaustive")]["task_total_ns"] for case in cases}
    screened = {case: medians[(case, "direct_screened")]["task_total_ns"] for case in cases}
    methods = {}
    for method in METHODS:
        selected = {case: medians[(case, method)]["task_total_ns"] for case in cases}
        memory = [row["peak_bytes"] for row in memory_rows if row["method"] == method]
        methods[method] = {
            "aggregate_speedup_over_direct_exhaustive": sum(exhaustive.values()) / sum(selected.values()),
            "aggregate_speedup_over_direct_screened": sum(screened.values()) / sum(selected.values()),
            "median_case_speedup_over_direct_exhaustive": statistics.median(
                exhaustive[case] / selected[case] for case in cases),
            "minimum_case_speedup_over_direct_exhaustive": min(
                exhaustive[case] / selected[case] for case in cases),
            "minimum_case_speedup_over_direct_screened": min(
                screened[case] / selected[case] for case in cases),
            "median_case_sum_ns": {
                field: sum(medians[(case, method)][field] for case in cases)
                for field in (*TIMING_FIELDS, "task_total_ns")
            },
            "memory_peak_bytes_median": int(statistics.median(memory)) if memory else None,
            "memory_peak_bytes_maximum": max(memory) if memory else None,
        }
    totals = {
        method: methods[method]["median_case_sum_ns"]["task_total_ns"]
        for method in DEPLOYABLE_METHODS
    }
    best_fixed = min(DEPLOYABLE_METHODS, key=lambda method: (totals[method], method))
    oracle_total = sum(
        min(medians[(case, method)]["task_total_ns"] for method in DEPLOYABLE_METHODS)
        for case in cases)
    advice_on = methods["c22_advice_on"]
    local_gate = (
        controls.get("all_passed") is True
        and advice_on["aggregate_speedup_over_direct_screened"] >= 1.0
        and advice_on["minimum_case_speedup_over_direct_screened"] >= 0.90
    )
    return {
        "exactness_gate": all(row["exact_check_passed"] for row in rows),
        "functional_control_gate": controls.get("all_passed") is True,
        "methods": methods,
        "best_deployable_fixed_method": best_fixed,
        "best_deployable_fixed_total_ns": totals[best_fixed],
        "deployable_per_case_oracle_total_ns": oracle_total,
        "oracle_headroom_over_best_deployable_fixed": totals[best_fixed] / oracle_total,
        "wrapper_comparisons": {
            "c22_advice_on_speedup_over_direct_source_packed": (
                methods["direct_source_packed"]["median_case_sum_ns"]["task_total_ns"]
                / advice_on["median_case_sum_ns"]["task_total_ns"]),
            "c22_advice_off_speedup_over_direct_exhaustive": (
                methods["direct_exhaustive"]["median_case_sum_ns"]["task_total_ns"]
                / methods["c22_advice_off"]["median_case_sum_ns"]["task_total_ns"]),
            "advice_on_shadow_cost_ratio": (
                methods["c22_advice_on_shadow"]["median_case_sum_ns"]["task_total_ns"]
                / advice_on["median_case_sum_ns"]["task_total_ns"]),
            "advice_off_shadow_cost_ratio": (
                methods["c22_advice_off_shadow"]["median_case_sum_ns"]["task_total_ns"]
                / methods["c22_advice_off"]["median_case_sum_ns"]["task_total_ns"]),
        },
        "local_promotion_gate": local_gate,
        "local_promotion_gate_contract": {
            "all_functional_controls_pass": True,
            "c22_advice_on_aggregate_vs_direct_screened_minimum": 1.0,
            "c22_advice_on_minimum_case_vs_direct_screened_minimum": 0.90,
        },
        "timing_is_retrospective_and_machine_specific": True,
    }


def _run_controls(cases: list[dict[str, Any]], oracles: dict[str, Any],
                  policy_path: Path, output: Path) -> dict[str, Any]:
    fallback = []
    for case in cases:
        result = execute_source_portfolio_boundary(
            case, policy_path, force_source_refusal=True).to_dict()
        verify_source_portfolio_boundary_result(
            result, case, required_best=oracles[case["case_id"]]["best_artifact"])
        fallback.append({
            "case_id": case["case_id"],
            "status": result["status"],
            "selected_arm": result["selected_arm"],
            "fallback_used": result["fallback_used"],
            "exact_check_passed": result["exact_check_passed"],
            "artifact_sha256": result["artifact_sha256"],
        })

    seed_case = json.loads(json.dumps(cases[0]))
    ood = json.loads(json.dumps(seed_case))
    ood["n_vars"] = 7
    malformed = json.loads(json.dumps(seed_case))
    malformed["expression_v2"]["root"] = 2 ** 31
    mismatch = json.loads(json.dumps(seed_case))
    mismatch["truth_bits_hex"] = hex(int(mismatch["truth_bits_hex"], 16) ^ 1)
    policy = load_source_portfolio_policy(policy_path)
    tampered = dict(policy)
    tampered["selected_arm"] = "explicit_cm_exhaustive"
    tampered_path = output / "control_policy_tampered.json"
    _write(tampered_path, tampered)
    duplicate_path = output / "control_policy_duplicate.json"
    raw = policy_path.read_text(encoding="utf-8").strip()
    duplicate = raw[:-1] + ',"status":"frozen"}'
    with duplicate_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(duplicate + "\n")
    refusal_inputs = (
        ("unsupported_n7", ood, policy_path),
        ("malformed_expression", malformed, policy_path),
        ("truth_mismatch", mismatch, policy_path),
        ("tampered_policy", seed_case, tampered_path),
        ("duplicate_policy_key", seed_case, duplicate_path),
    )
    refusals = []
    for control_id, case, selected_policy in refusal_inputs:
        result = execute_source_portfolio_boundary(case, selected_policy).to_dict()
        verify_source_portfolio_boundary_result(result, case)
        refusals.append({
            "control_id": control_id,
            "status": result["status"],
            "reason": result["reason"],
            "exact_check_passed": result["exact_check_passed"],
            "selected_arm": result["selected_arm"],
        })
    fallback_pass = all(
        row["status"] == "ok"
        and row["selected_arm"] == "explicit_cm_exhaustive"
        and row["fallback_used"] is True
        and row["exact_check_passed"] is True
        for row in fallback
    )
    refusal_pass = all(
        row["status"] == "refused"
        and row["exact_check_passed"] is False
        and row["selected_arm"] is None
        for row in refusals
    )
    return {
        "schema": "crse-c24-c22-boundary-controls/v1",
        "fallback_cases": fallback,
        "refusal_cases": refusals,
        "fallback_cases_checked": len(fallback),
        "refusal_cases_checked": len(refusals),
        "fallback_gate": fallback_pass,
        "refusal_gate": refusal_pass,
        "all_passed": fallback_pass and refusal_pass,
    }


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# C24 frozen C22 end-to-end boundary evaluation",
        "",
        f"Status: **{result['status']}**  ",
        f"Local promotion gate: **{'pass' if summary['local_promotion_gate'] else 'fail'}**  ",
        f"Best deployable fixed method: **{summary['best_deployable_fixed_method']}**",
        "",
        "The C22 policy was not refit. Every request used the sealed C23 expression corpus,",
        "fresh policy load and compilation, exact completion, response serialization, and exact",
        "delivery verification. Shadow arms are diagnostics and are excluded from deployment rank.",
        "",
        "| Method | Aggregate vs direct exhaustive | Aggregate vs direct screened | Minimum vs screened |",
        "|---|---:|---:|---:|",
    ]
    for method in METHODS:
        row = summary["methods"][method]
        lines.append(
            f"| {method} | {row['aggregate_speedup_over_direct_exhaustive']:.4f}x | "
            f"{row['aggregate_speedup_over_direct_screened']:.4f}x | "
            f"{row['minimum_case_speedup_over_direct_screened']:.4f}x |"
        )
    comparisons = summary["wrapper_comparisons"]
    lines += [
        "",
        "The functional gate includes exact forced fallback on all 48 cases and five fail-closed",
        "controls for unsupported width, malformed input, truth mismatch, tampered policy, and a",
        "duplicate policy key.",
        "",
        f"Advice-on boundary vs direct packed source: **{comparisons['c22_advice_on_speedup_over_direct_source_packed']:.4f}x**.  ",
        f"Advice-off boundary vs direct exhaustive: **{comparisons['c22_advice_off_speedup_over_direct_exhaustive']:.4f}x**.  ",
        f"Deployable per-case oracle headroom: **{summary['oracle_headroom_over_best_deployable_fixed']:.4f}x**.",
        "",
        "This is a retrospective same-machine boundary-cost evaluation. Production promotion",
        "remains disabled regardless of the local gate.",
    ]
    return "\n".join(lines) + "\n"


def run(config: C24Config, output: Path, dataset_path: Path,
        dataset_verification_path: Path, c22_policy_path: Path,
        c19_policy_path: Path, root: Path) -> dict[str, Any]:
    config.validate()
    wall_started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    dataset_verification = json.loads(dataset_verification_path.read_text(encoding="utf-8"))
    if (
        len(dataset.get("cases", [])) != 48
        or dataset.get("revision", {}).get("id") != "task-complete-v2"
        or dataset_verification.get("status") != "verified"
        or dataset_verification.get("cases_replayed") != 48
        or dataset_verification.get("expression_truth_mismatches") != 0
        or dataset_verification.get("prior_truth_overlaps") != 0
    ):
        raise ValueError("C24 requires the sealed independently verified C23 corpus")
    c22_policy = load_source_portfolio_policy(c22_policy_path)
    c19_policy = load_policy(c19_policy_path)
    compiled = compile_work_policy(c19_policy)
    if (
        c22_policy["selected_arm"] != "source_packed_anf_screened"
        or c22_policy["advice_off_arm"] != "explicit_cm_exhaustive"
        or c22_policy["exact_fallback_arm"] != "explicit_cm_exhaustive"
        or c22_policy["training_use"] is not False
        or compiled.mode != "constant_leaf"
        or compiled.constant_arm != "explicit_cm_screened"
    ):
        raise ValueError("C24 frozen policy contract changed")
    _write(output / "run_spec.json", {
        "schema": SCHEMA,
        "config": asdict(config),
        "dataset_path": _rel(dataset_path, root),
        "dataset_sha256": _sha256(dataset_path),
        "dataset_verification_path": _rel(dataset_verification_path, root),
        "dataset_verification_sha256": _sha256(dataset_verification_path),
        "c22_policy_path": _rel(c22_policy_path, root),
        "c22_policy_file_sha256": _sha256(c22_policy_path),
        "c22_policy_sha256": c22_policy["policy_sha256"],
        "c19_policy_path": _rel(c19_policy_path, root),
        "c19_policy_file_sha256": _sha256(c19_policy_path),
        "c19_policy_sha256": c19_policy["policy_sha256"],
        "methods": list(METHODS),
        "deployable_methods": list(DEPLOYABLE_METHODS),
        "lifecycle": "fresh_engine_single_query",
        "full_response_serialization_and_exact_delivery_verification_charged": True,
        "retrospective_boundary_evaluation": True,
        "policy_refit": False,
        "production_promotion": False,
    })
    cases = dataset["cases"]
    functional, oracles = build_oracles(cases, config.oracle_config())
    if not functional["all_exact"]:
        raise RuntimeError("C24 exhaustive oracle replay failed")
    _write(output / "functional.json", functional)
    _write(output / "oracles.json", oracles)
    contracts = {
        case["case_id"]: decomposition_contract(
            contract_id=f"c24-{case['case_id']}",
            n_vars=case["n_vars"],
            required_output_sha256=oracles[case["case_id"]]["delivered_sha256"],
        )
        for case in cases
    }
    _write(output / "contracts.json", contracts)
    controls = _run_controls(cases, oracles, c22_policy_path, output)
    if not controls["all_passed"]:
        raise RuntimeError("C24 functional controls failed")
    _write(output / "functional_controls.json", controls)

    rng = random.Random(f"{config.seed}:c24-balanced/v1")
    rows = []
    for round_index in range(config.rounds):
        order = [(case, method) for case in cases for method in METHODS]
        rng.shuffle(order)
        for case, method in order:
            if time.perf_counter() - wall_started > config.max_seconds:
                raise TimeoutError("C24 experiment exceeded wall bound")
            execution = execute_benchmark_method(
                case=case,
                contract=contracts[case["case_id"]],
                method=method,
                required_best=oracles[case["case_id"]]["best_artifact"],
                policy_path=c22_policy_path,
                compiled_policy=compiled,
                max_partitions=config.max_partitions,
                materialize_budget=config.materialize_budget,
            )
            rows.append(_measurement_row(case, method, round_index, execution))
    _write_jsonl(output / "measurements.jsonl", rows)

    memory_rows = []
    for case in _memory_cases(cases, config.memory_cases_per_width):
        for method in METHODS:
            tracemalloc.start()
            try:
                execution = execute_benchmark_method(
                    case=case,
                    contract=contracts[case["case_id"]],
                    method=method,
                    required_best=oracles[case["case_id"]]["best_artifact"],
                    policy_path=c22_policy_path,
                    compiled_policy=compiled,
                    max_partitions=config.max_partitions,
                    materialize_budget=config.materialize_budget,
                )
                current, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            memory_rows.append({
                "case_id": case["case_id"],
                "n_vars": case["n_vars"],
                "method": method,
                "current_bytes": current,
                "peak_bytes": peak,
                "exact_check_passed": execution["exact_check_passed"],
            })
    _write_jsonl(output / "memory_measurements.jsonl", memory_rows)
    summary = summarize(rows, memory_rows, controls)
    mismatches = sum(not row["exact_check_passed"] for row in rows)
    result = {
        "schema": SCHEMA,
        "status": "complete" if mismatches == 0 and controls["all_passed"] else "failed",
        "config": asdict(config),
        "wall_seconds": time.perf_counter() - wall_started,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "dd_version": importlib.metadata.version("dd"),
            "thread_environment": {
                name: os.environ.get(name)
                for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
            },
        },
        "dataset": {
            "family": "YosysHQ/yosys-bench unused generator families",
            "cases": len(cases),
            "families": dataset["counts"]["families"],
            "n_vars": sorted({case["n_vars"] for case in cases}),
            "retrospective_boundary_evaluation": True,
            "policy_refit": False,
        },
        "measurement_rows": len(rows),
        "memory_measurement_rows": len(memory_rows),
        "fallback_controls": controls["fallback_cases_checked"],
        "refusal_controls": controls["refusal_cases_checked"],
        "semantic_or_artifact_mismatches": mismatches,
        "summary": summary,
        "claims": {
            "unchanged_c22_policy": True,
            "all_boundary_costs_charged": True,
            "fallback_and_refusal_controls_passed": controls["all_passed"],
            "fresh_confirmation": False,
            "production_promotion": False,
        },
        "runpod": {"used": False, "cost_usd": 0.0},
    }
    _write(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    sources = (
        "cmbench/comparative/gf2_source_portfolio_experiment.py",
        "cmbench/comparative/gf2_method_table.py",
        "cmbench/recognition/gf2_source_portfolio.py",
        "cmbench/recognition/gf2_source_portfolio_boundary.py",
        "scripts/cm_comparative_c24_source_portfolio.py",
    )
    artifacts = (
        "run_spec.json", "functional.json", "oracles.json", "contracts.json",
        "control_policy_tampered.json", "control_policy_duplicate.json",
        "functional_controls.json", "measurements.jsonl", "memory_measurements.jsonl",
        "results.json", "report.md",
    )
    _write(output / "manifest.json", {
        "schema": "crse-c24-run-manifest/v1",
        "dataset_sha256": _sha256(dataset_path),
        "dataset_verification_sha256": _sha256(dataset_verification_path),
        "c22_policy_file_sha256": _sha256(c22_policy_path),
        "c19_policy_file_sha256": _sha256(c19_policy_path),
        "sources": {name: _sha256(root / name) for name in sources},
        "artifacts": {name: _sha256(output / name) for name in artifacts},
    })
    return result
