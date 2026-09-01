"""C21 task-matched exact GF(2) method-table experiment."""
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

from cmbench.recognition.gf2_decomposition import analyze_exact_gf2
from cmbench.recognition.gf2_work_policy import load_policy
from cmbench.recognition.gf2_work_policy_compiler import compile_work_policy

from .gf2_decomposition import decomposition_contract, delivered_sha256
from .gf2_method_table import METHODS, TIMING_FIELDS, execute_method

SCHEMA = "crse-c21-task-matched-gf2-method-table-experiment/v1"


@dataclass(frozen=True)
class C21Config:
    run_id: str
    seed: int = 20260831
    rounds: int = 5
    max_partitions: int = 64
    materialize_budget: int = 4
    memory_cases_per_width: int = 3
    max_seconds: float = 900.0

    def validate(self) -> None:
        if (
            not self.run_id
            or type(self.rounds) is not int
            or not 3 <= self.rounds <= 9
            or self.max_partitions != 64
            or self.materialize_budget != 4
            or type(self.memory_cases_per_width) is not int
            or not 1 <= self.memory_cases_per_width <= 4
            or type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or not 180 <= self.max_seconds <= 1800
        ):
            raise ValueError("invalid C21 experiment bounds")


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


def build_oracles(cases: list[dict[str, Any]], config: C21Config):
    documents, mismatches = {}, 0
    for case in cases:
        bits, n_vars = int(case["truth_bits_hex"], 16), case["n_vars"]
        analysis = analyze_exact_gf2(bits, n_vars, max_partitions=config.max_partitions)
        best = _best(analysis)
        exact = all(candidate.reconstruct() == bits for candidate in analysis.candidates)
        mismatches += int(not exact)
        documents[case["case_id"]] = {
            "best_artifact": best,
            "delivered_sha256": delivered_sha256(best),
            "partitions_tested": analysis.partitions_tested,
            "candidates": len(analysis.candidates),
        }
    return {"cases": len(cases), "mismatches": mismatches, "all_exact": mismatches == 0}, documents


def _measurement_row(case, method, round_index, result):
    timings = result["timings_ns"]
    return {
        "case_id": case["case_id"],
        "split": case["split"],
        "cluster_id": case["cluster_id"],
        "n_vars": case["n_vars"],
        "method": method,
        "round": round_index,
        "status": result["status"],
        "selected_exact_arm": result["selected_exact_arm"],
        "proposal": result["proposal"],
        "timings_ns": timings,
        "artifact_sha256": result["artifact"]["sha256"],
        "artifact_bytes": result["artifact"]["bytes"],
        "best_artifact_sha256": (
            result["identity"]["best_artifact"]["payload_sha256"]
            if result["identity"]["best_artifact"] else None),
        "source_sha256": result["identity"]["source_sha256"],
        "partitions_tested": result["identity"]["partitions_tested"],
        "descriptors_screened": result["identity"]["descriptors_screened"],
        "artifacts_materialized": result["identity"]["artifacts_materialized"],
        "exact_check_passed": result["identity"]["exact_check_passed"],
        "resources": result["resources"],
    }


def _median_rows(rows: list[dict[str, Any]]):
    grouped = {}
    for row in rows:
        grouped.setdefault((row["case_id"], row["method"]), []).append(row)
    medians = {}
    for key, values in grouped.items():
        medians[key] = {
            field: int(statistics.median(row["timings_ns"][field] for row in values))
            for field in (*TIMING_FIELDS, "task_total_ns")
        }
    return medians


def summarize(rows: list[dict[str, Any]], memory_rows: list[dict[str, Any]], functional: dict[str, Any]):
    med = _median_rows(rows)
    cases = sorted({row["case_id"] for row in rows})
    exhaustive = {case: med[(case, "cm_exhaustive")]["task_total_ns"] for case in cases}
    screened = {case: med[(case, "cm_screened")]["task_total_ns"] for case in cases}
    methods = {}
    for method in METHODS:
        selected = {case: med[(case, method)]["task_total_ns"] for case in cases}
        vs_exhaustive = [exhaustive[case] / selected[case] for case in cases]
        vs_screened = [screened[case] / selected[case] for case in cases]
        method_rows = [row for row in rows if row["method"] == method]
        memory = [row["peak_bytes"] for row in memory_rows if row["method"] == method]
        methods[method] = {
            "aggregate_speedup_over_exhaustive": sum(exhaustive.values()) / sum(selected.values()),
            "aggregate_speedup_over_screened": sum(screened.values()) / sum(selected.values()),
            "median_case_speedup_over_exhaustive": statistics.median(vs_exhaustive),
            "minimum_case_speedup_over_exhaustive": min(vs_exhaustive),
            "minimum_case_speedup_over_screened": min(vs_screened),
            "proposals": len({row["case_id"] for row in method_rows if row["proposal"]["status"] == "proposed"}),
            "abstentions": len({row["case_id"] for row in method_rows if row["proposal"]["status"] == "abstained"}),
            "median_case_sum_ns": {
                field: sum(med[(case, method)][field] for case in cases)
                for field in (*TIMING_FIELDS, "task_total_ns")
            },
            "memory_peak_bytes_median": int(statistics.median(memory)) if memory else None,
            "memory_peak_bytes_maximum": max(memory) if memory else None,
        }
    total_by_method = {
        method: methods[method]["median_case_sum_ns"]["task_total_ns"] for method in METHODS}
    best_fixed = min(METHODS, key=lambda method: (total_by_method[method], method))
    oracle_total = sum(min(med[(case, method)]["task_total_ns"] for method in METHODS) for case in cases)
    exact = functional["all_exact"] and all(row["exact_check_passed"] for row in rows)
    return {
        "exactness_gate": exact,
        "methods": methods,
        "best_fixed_method": best_fixed,
        "best_fixed_total_ns": total_by_method[best_fixed],
        "per_case_oracle_total_ns": oracle_total,
        "oracle_headroom_over_best_fixed": total_by_method[best_fixed] / oracle_total,
        "screened_control_gate": (
            methods["cm_screened"]["aggregate_speedup_over_exhaustive"] >= 1.0
            and methods["cm_screened"]["minimum_case_speedup_over_exhaustive"] >= 0.97),
        "compiled_no_regret_gate": (
            methods["cm_compiled_screened"]["aggregate_speedup_over_screened"] >= 0.97
            and methods["cm_compiled_screened"]["minimum_case_speedup_over_screened"] >= 0.90),
        "timing_is_retrospective_and_machine_specific": True,
    }


def _memory_cases(cases, count_per_width):
    selected = []
    for n_vars in sorted({case["n_vars"] for case in cases}):
        group = sorted((case for case in cases if case["n_vars"] == n_vars), key=lambda case: case["truth_sha256"])
        selected.extend(group[:count_per_width])
    return selected


def render_report(result):
    summary = result["summary"]
    lines = [
        "# C21 task-matched exact GF(2) method table",
        "",
        f"Status: **{result['status']}**  ",
        f"Best fixed method: **{summary['best_fixed_method']}**",
        "",
        "All methods started from the same frozen canonical expression input and delivered the",
        "same exhaustive-best exact artifact. Proposal methods retained screened exact completion;",
        "their reconstruction checks alone were not treated as a proof of global optimality.",
        "",
        "| Method | Aggregate vs exhaustive | Aggregate vs screened | Minimum vs exhaustive |",
        "|---|---:|---:|---:|",
    ]
    for method in METHODS:
        row = summary["methods"][method]
        lines.append(
            f"| {method} | {row['aggregate_speedup_over_exhaustive']:.4f}x | "
            f"{row['aggregate_speedup_over_screened']:.4f}x | "
            f"{row['minimum_case_speedup_over_exhaustive']:.4f}x |")
    lines += [
        "",
        f"Per-case oracle headroom over the best fixed method: "
        f"**{summary['oracle_headroom_over_best_fixed']:.4f}x**.",
        "",
        "This is a retrospective one-machine table over the already frozen C19 corpus. Production",
        "promotion remains false.",
    ]
    return "\n".join(lines) + "\n"


def run(config: C21Config, output: Path, dataset_path: Path, policy_path: Path, root: Path):
    config.validate()
    wall = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset, policy = json.loads(dataset_path.read_text()), load_policy(policy_path)
    cases = dataset["cases"]
    if dataset.get("status") != "frozen" or len(cases) != 96:
        raise ValueError("C21 frozen dataset changed")
    compiled = compile_work_policy(policy)
    if compiled.mode != "constant_leaf" or compiled.constant_arm != "explicit_cm_screened":
        raise ValueError("C21 compiled control requires the frozen screened C19 leaf")
    _write(output / "run_spec.json", {
        "schema": SCHEMA,
        "config": asdict(config),
        "dataset_path": str(dataset_path.relative_to(root)).replace("\\", "/"),
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "policy_path": str(policy_path.relative_to(root)).replace("\\", "/"),
        "policy_file_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "policy_sha256": policy["policy_sha256"],
        "methods": list(METHODS),
        "lifecycle": "fresh_engine_single_query",
        "input_contract": "canonical expression DAG plus frozen source identity/v1",
        "internal_exact_completion_charged": True,
        "external_correctness_oracle_outside_timing": True,
        "fresh_confirmation": False,
        "production_promotion": False,
    })
    functional, oracles = build_oracles(cases, config)
    if not functional["all_exact"]:
        raise RuntimeError("C21 exhaustive oracle failed exact replay")
    _write(output / "functional.json", functional)
    _write(output / "oracles.json", oracles)
    contracts = {
        case["case_id"]: decomposition_contract(
            contract_id=f"c21-{case['case_id']}", n_vars=case["n_vars"],
            required_output_sha256=oracles[case["case_id"]]["delivered_sha256"])
        for case in cases
    }
    _write(output / "contracts.json", contracts)

    rng = random.Random(f"{config.seed}:c21-balanced/v1")
    rows = []
    for round_index in range(config.rounds):
        order = [(case, method) for case in cases for method in METHODS]
        rng.shuffle(order)
        for case, method in order:
            if time.perf_counter() - wall > config.max_seconds:
                raise TimeoutError("C21 experiment exceeded wall bound")
            result = execute_method(
                case=case, contract=contracts[case["case_id"]], method=method,
                required_best=oracles[case["case_id"]]["best_artifact"],
                compiled_policy=compiled if method == "cm_compiled_screened" else None,
                max_partitions=config.max_partitions,
                materialize_budget=config.materialize_budget)
            rows.append(_measurement_row(case, method, round_index, result))
    _write_jsonl(output / "measurements.jsonl", rows)

    memory_rows = []
    for case in _memory_cases(cases, config.memory_cases_per_width):
        for method in METHODS:
            tracemalloc.start()
            try:
                result = execute_method(
                    case=case, contract=contracts[case["case_id"]], method=method,
                    required_best=oracles[case["case_id"]]["best_artifact"],
                    compiled_policy=compiled if method == "cm_compiled_screened" else None,
                    max_partitions=config.max_partitions,
                    materialize_budget=config.materialize_budget)
                current, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            memory_rows.append({"case_id": case["case_id"], "n_vars": case["n_vars"],
                                "method": method, "current_bytes": current, "peak_bytes": peak,
                                "exact_check_passed": result["identity"]["exact_check_passed"]})
    _write_jsonl(output / "memory_measurements.jsonl", memory_rows)
    summary = summarize(rows, memory_rows, functional)
    mismatches = sum(not row["exact_check_passed"] for row in rows)
    result = {
        "schema": SCHEMA,
        "status": "complete" if mismatches == 0 else "failed",
        "config": asdict(config),
        "wall_seconds": time.perf_counter() - wall,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "dd_version": importlib.metadata.version("dd"),
            "thread_environment": {name: os.environ.get(name) for name in
                                   ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        },
        "dataset": {"family": "LogikBench", "cases": len(cases), "source_files": 51,
                    "n_vars": [3, 4, 5, 6], "retrospective": True, "policy_refit": False},
        "measurement_rows": len(rows),
        "memory_measurement_rows": len(memory_rows),
        "semantic_or_artifact_mismatches": mismatches,
        "summary": summary,
        "claims": {"same_requested_artifact": True, "proposal_is_not_certificate": True,
                   "fresh_confirmation": False, "production_promotion": False},
        "runpod": {"used": False, "cost_usd": 0.0},
    }
    _write(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    sources = (
        "cmbench/comparative/gf2_decomposition.py",
        "cmbench/comparative/gf2_method_table.py",
        "cmbench/comparative/gf2_table_experiment.py",
        "scripts/cm_comparative_c21_gf2_table.py",
    )
    artifacts = ("run_spec.json", "functional.json", "oracles.json", "contracts.json",
                 "measurements.jsonl", "memory_measurements.jsonl", "results.json", "report.md")
    _write(output / "manifest.json", {
        "schema": "crse-c21-run-manifest/v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "policy_file_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "sources": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sources},
        "artifacts": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in artifacts},
    })
    return result

