"""C23 fresh-generator task-matched exact GF(2) method table."""
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
import sys
import time
import tracemalloc
from typing import Any

from cmbench.recognition.gf2_work_policy import load_policy
from cmbench.recognition.gf2_work_policy_compiler import compile_work_policy
from cmbench.recognition.yosys_unused_gf2_data import DATASET_SCHEMA, validate_dataset

from .gf2_decomposition import decomposition_contract
from .gf2_method_table import METHODS, execute_method
from .gf2_table_experiment import (
    C21Config,
    _measurement_row,
    _memory_cases,
    build_oracles,
    summarize,
)

SCHEMA = "crse-c23-fresh-task-matched-gf2-method-table-experiment/v1"


@dataclass(frozen=True)
class C23Config:
    run_id: str
    seed: int = 20260831
    rounds: int = 5
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
            raise ValueError("invalid C23 experiment bounds")

    def oracle_config(self) -> C21Config:
        return C21Config(
            run_id=self.run_id,
            seed=self.seed,
            rounds=self.rounds,
            max_partitions=self.max_partitions,
            materialize_budget=self.materialize_budget,
            memory_cases_per_width=min(self.memory_cases_per_width, 3),
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


def fresh_summary(rows, memory_rows, functional):
    result = summarize(rows, memory_rows, functional)
    result.pop("timing_is_retrospective_and_machine_specific")
    result["timing_is_fresh_and_machine_specific"] = True
    return result


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# C23 fresh Yosys-generator exact GF(2) method table",
        "",
        f"Status: **{result['status']}**  ",
        f"Best fixed method: **{summary['best_fixed_method']}**",
        "",
        "All methods used the unchanged C21 implementations and delivered the same",
        "bounded exhaustive-best exact artifact from the same frozen expression input.",
        "",
        "| Method | Aggregate vs exhaustive | Aggregate vs screened | Minimum vs exhaustive |",
        "|---|---:|---:|---:|",
    ]
    for method in METHODS:
        row = summary["methods"][method]
        lines.append(
            f"| {method} | {row['aggregate_speedup_over_exhaustive']:.4f}x | "
            f"{row['aggregate_speedup_over_screened']:.4f}x | "
            f"{row['minimum_case_speedup_over_exhaustive']:.4f}x |"
        )
    lines += [
        "",
        "Per-case oracle headroom over the best fixed method: "
        f"**{summary['oracle_headroom_over_best_fixed']:.4f}x**.",
        "",
        "The generator paths and truth identities were sealed before timing and did not",
        "participate in C22 selection. Production promotion remains false.",
    ]
    return "\n".join(lines) + "\n"


def run(config: C23Config, output: Path, dataset_path: Path,
        dataset_verification_path: Path, policy_path: Path, root: Path) -> dict[str, Any]:
    config.validate()
    wall = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    dataset_verification = json.loads(dataset_verification_path.read_text(encoding="utf-8"))
    if (
        dataset.get("schema") != DATASET_SCHEMA
        or len(dataset["cases"]) != 48
        or dataset.get("revision", {}).get("id") != "task-complete-v2"
        or dataset.get("provenance", {}).get("partition_contract_complete") is not True
        or dataset_verification.get("status") != "verified"
        or dataset_verification.get("cases_replayed") != 48
        or dataset_verification.get("dataset_reconstruction_mismatches") != 0
        or dataset_verification.get("expression_truth_mismatches") != 0
        or dataset_verification.get("prior_truth_overlaps") != 0
        or dataset_verification.get("out_of_task_support_cases") != 0
        or dataset_verification.get("partition_contract_complete") is not True
        or dataset_verification.get("fresh_confirmation") is not True
    ):
        raise ValueError("C23 requires the independently verified fresh dataset")
    policy = load_policy(policy_path)
    compiled = compile_work_policy(policy)
    if compiled.mode != "constant_leaf" or compiled.constant_arm != "explicit_cm_screened":
        raise ValueError("C23 compiled control requires the unchanged screened C19 leaf")
    _write(output / "run_spec.json", {
        "schema": SCHEMA,
        "config": asdict(config),
        "dataset_path": str(dataset_path.relative_to(root)).replace("\\", "/"),
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "dataset_verification_path": str(dataset_verification_path.relative_to(root)).replace("\\", "/"),
        "dataset_verification_sha256": hashlib.sha256(dataset_verification_path.read_bytes()).hexdigest(),
        "policy_path": str(policy_path.relative_to(root)).replace("\\", "/"),
        "policy_file_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "policy_sha256": policy["policy_sha256"],
        "methods": list(METHODS),
        "method_implementation_contract": "unchanged C21 seven-method adapters/v1",
        "lifecycle": "fresh_engine_single_query",
        "input_contract": "canonical expression DAG plus frozen source identity/v1",
        "internal_exact_completion_charged": True,
        "external_correctness_oracle_outside_timing": True,
        "policy_refit": False,
        "fresh_confirmation": True,
        "production_promotion": False,
    })
    cases = dataset["cases"]
    oracle_config = config.oracle_config()
    functional, oracles = build_oracles(cases, oracle_config)
    if not functional["all_exact"]:
        raise RuntimeError("C23 exhaustive oracle failed exact replay")
    _write(output / "functional.json", functional)
    _write(output / "oracles.json", oracles)
    contracts = {
        case["case_id"]: decomposition_contract(
            contract_id=f"c23-{case['case_id']}",
            n_vars=case["n_vars"],
            required_output_sha256=oracles[case["case_id"]]["delivered_sha256"],
        )
        for case in cases
    }
    _write(output / "contracts.json", contracts)

    rng = random.Random(f"{config.seed}:c23-balanced/v1")
    rows = []
    for round_index in range(config.rounds):
        order = [(case, method) for case in cases for method in METHODS]
        rng.shuffle(order)
        for case, method in order:
            if time.perf_counter() - wall > config.max_seconds:
                raise TimeoutError("C23 experiment exceeded wall bound")
            execution = execute_method(
                case=case,
                contract=contracts[case["case_id"]],
                method=method,
                required_best=oracles[case["case_id"]]["best_artifact"],
                compiled_policy=compiled if method == "cm_compiled_screened" else None,
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
                execution = execute_method(
                    case=case,
                    contract=contracts[case["case_id"]],
                    method=method,
                    required_best=oracles[case["case_id"]]["best_artifact"],
                    compiled_policy=compiled if method == "cm_compiled_screened" else None,
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
                "exact_check_passed": execution["identity"]["exact_check_passed"],
            })
    _write_jsonl(output / "memory_measurements.jsonl", memory_rows)
    summary = fresh_summary(rows, memory_rows, functional)
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
        "dataset": {
            "family": "YosysHQ/yosys-bench unused generator families",
            "repository_seen_in_prior_work": True,
            "generator_families_seen_in_c7": False,
            "cases": len(cases),
            "families": dataset["counts"]["families"],
            "n_vars": sorted({case["n_vars"] for case in cases}),
            "fresh_confirmation": True,
            "policy_refit": False,
        },
        "measurement_rows": len(rows),
        "memory_measurement_rows": len(memory_rows),
        "semantic_or_artifact_mismatches": mismatches,
        "summary": summary,
        "claims": {
            "same_requested_artifact": True,
            "proposal_is_not_certificate": True,
            "unchanged_c21_methods": True,
            "fresh_confirmation": True,
            "production_promotion": False,
        },
        "runpod": {"used": False, "cost_usd": 0.0},
    }
    _write(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    sources = (
        "cmbench/comparative/gf2_decomposition.py",
        "cmbench/comparative/gf2_method_table.py",
        "cmbench/comparative/gf2_table_experiment.py",
        "cmbench/comparative/gf2_fresh_table_experiment.py",
        "scripts/cm_comparative_c23_fresh_gf2_table.py",
    )
    artifacts = (
        "run_spec.json", "functional.json", "oracles.json", "contracts.json",
        "measurements.jsonl", "memory_measurements.jsonl", "results.json", "report.md",
    )
    _write(output / "manifest.json", {
        "schema": "crse-c23-run-manifest/v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "dataset_verification_sha256": hashlib.sha256(dataset_verification_path.read_bytes()).hexdigest(),
        "policy_file_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "sources": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sources},
        "artifacts": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in artifacts},
    })
    return result
