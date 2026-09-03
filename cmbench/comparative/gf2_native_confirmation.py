"""Prospective, no-refit confirmation of the exact native slot backends."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any

import numpy as np

from .gf2_multi_root import prospective_sibling_output_workloads
from .gf2_multi_root_experiment import (
    METHODS as MULTI_METHODS,
    _oracle as multi_oracle,
    execute_session as execute_multi_session,
)
from .gf2_native_slot_experiment import (
    METHODS as SINGLE_METHODS,
    _execute as execute_single_session,
)
from .gf2_native_slots import load_native_slot_library
from .gf2_projection_optimization_experiment import _rss_bytes
from .schedule import balanced_orders
from cmbench.recognition.yosys_native_confirmation_data import validate_dataset


SCHEMA = "crse-c37-native-exact-prospective-confirmation/v1"
RAW_SCHEMA = "crse-c37-native-exact-confirmation-session/v1"
STAGES = (
    "input_decode_ns", "representation_ns", "restriction_setup_ns",
    "evaluation_ns", "delivery_ns", "query_total_ns", "cleanup_ns",
    "accounted_total_ns",
)


@dataclass(frozen=True)
class NativeConfirmationConfig:
    run_id: str
    seed: int = 20260903
    single_blocks: int = 12
    multi_blocks: int = 20
    max_seconds: float = 1200.0

    def validate(self) -> None:
        if (
            not self.run_id
            or self.single_blocks != 12
            or self.multi_blocks != 20
            or self.single_blocks % len(balanced_orders(SINGLE_METHODS))
            or self.multi_blocks % len(balanced_orders(MULTI_METHODS))
            or not math.isfinite(self.max_seconds)
            or not 300 <= self.max_seconds <= 3600
        ):
            raise ValueError("invalid frozen C37 confirmation configuration")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(
                row, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                allow_nan=False,
            ) + "\n")


def _percentile(values: list[int], percentile: float) -> int:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty percentile")
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _medians(
    rows: list[dict[str, Any]],
    identity_key: str,
    identities: list[str],
    methods: tuple[str, ...],
) -> dict[tuple[str, str], dict[str, int]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["role"] == "performance":
            grouped[(row[identity_key], row["method"])].append(row)
    return {
        (identity, method): {
            stage: int(statistics.median_low(
                row["timings_ns"][stage] for row in grouped[(identity, method)]
            ))
            for stage in STAGES
        }
        for identity in identities for method in methods
    }


def summarize_single(rows: list[dict[str, Any]], cases: list[dict[str, Any]]) -> dict[str, Any]:
    identities = [case["case_id"] for case in cases]
    medians = _medians(rows, "case_id", identities, SINGLE_METHODS)
    totals = {
        method: {stage: sum(medians[(identity, method)][stage] for identity in identities)
                 for stage in STAGES}
        for method in SINGLE_METHODS
    }
    r2 = "restricted_r2_reference"
    native = "native_fused_slots"
    case_speedups = {
        identity: medians[(identity, r2)]["accounted_total_ns"]
        / medians[(identity, native)]["accounted_total_ns"]
        for identity in identities
    }
    width_speedups = {}
    for width in range(11, 17):
        selected = [case["case_id"] for case in cases if case["n_vars"] == width]
        width_speedups[str(width)] = (
            sum(medians[(identity, r2)]["accounted_total_ns"] for identity in selected)
            / sum(medians[(identity, native)]["accounted_total_ns"] for identity in selected)
        )
    performance = [row for row in rows if row["role"] == "performance"]
    p95 = {
        method: _percentile([
            row["timings_ns"]["accounted_total_ns"] for row in performance
            if row["method"] == method
        ], 0.95)
        for method in SINGLE_METHODS
    }
    native_rows = [row for row in rows if row["method"] == native]
    max_workspace = max(row["resources"]["max_workspace_bytes"] for row in native_rows)
    gates = {
        "aggregate_speedup_at_least_1_10": (
            totals[r2]["accounted_total_ns"] / totals[native]["accounted_total_ns"] >= 1.10
        ),
        "minimum_case_speedup_at_least_0_95": min(case_speedups.values()) >= 0.95,
        "minimum_width_speedup_at_least_1_00": min(width_speedups.values()) >= 1.00,
        "p95_session_speedup_at_least_0_95": p95[r2] / p95[native] >= 0.95,
        "max_workspace_at_most_64_mib": max_workspace <= 64 * 1024 * 1024,
    }
    return {
        "cases": len(cases),
        "performance_sessions": len(performance),
        "memory_profile_sessions": sum(row["role"] == "memory_profile" for row in rows),
        "timed_queries": len(performance) * 64,
        "aggregate_case_median_stage_ns": totals,
        "native_speedup_over_python_r2": (
            totals[r2]["accounted_total_ns"] / totals[native]["accounted_total_ns"]
        ),
        "native_speedup_over_projection_u16": (
            totals["projection_u16_tuple"]["accounted_total_ns"]
            / totals[native]["accounted_total_ns"]
        ),
        "case_median_speedups_over_python_r2": case_speedups,
        "width_aggregate_speedups_over_python_r2": width_speedups,
        "minimum_case_speedup_over_python_r2": min(case_speedups.values()),
        "minimum_width_speedup_over_python_r2": min(width_speedups.values()),
        "p95_session_ns": p95,
        "p95_session_speedup_over_python_r2": p95[r2] / p95[native],
        "max_native_workspace_bytes": max_workspace,
        "gates": gates,
        "all_gates_passed": all(gates.values()),
    }


def summarize_multi(rows: list[dict[str, Any]], workloads: tuple[Any, ...]) -> dict[str, Any]:
    identities = [workload.workload_id for workload in workloads]
    medians = _medians(rows, "workload_id", identities, MULTI_METHODS)
    totals = {
        method: {stage: sum(medians[(identity, method)][stage] for identity in identities)
                 for stage in STAGES}
        for method in MULTI_METHODS
    }
    separate = "native_separate_roots"
    union = "native_union_roots"
    workload_speedups = {
        identity: medians[(identity, separate)]["accounted_total_ns"]
        / medians[(identity, union)]["accounted_total_ns"]
        for identity in identities
    }
    performance = [row for row in rows if row["role"] == "performance"]
    p95 = {
        method: _percentile([
            row["timings_ns"]["accounted_total_ns"] for row in performance
            if row["method"] == method
        ], 0.95)
        for method in MULTI_METHODS
    }
    memory_by_identity = {
        identity: {
            row["method"]: row["resources"]
            for row in rows if row["role"] == "memory_profile"
            and row["workload_id"] == identity
        }
        for identity in identities
    }
    node_reduction = all(
        resources[union]["union_nodes"] < resources[separate]["sum_separate_nodes"]
        for resources in memory_by_identity.values()
    )
    workspace_no_regret = all(
        resources[union]["max_workspace_bytes"]
        <= resources[separate]["max_workspace_bytes"]
        for resources in memory_by_identity.values()
    )
    gates = {
        "aggregate_speedup_at_least_1_10": (
            totals[separate]["accounted_total_ns"] / totals[union]["accounted_total_ns"]
            >= 1.10
        ),
        "minimum_workload_speedup_at_least_1_00": min(workload_speedups.values()) >= 1.00,
        "p95_session_speedup_at_least_0_95": p95[separate] / p95[union] >= 0.95,
        "all_workloads_reduce_nodes": node_reduction,
        "all_workloads_union_workspace_no_larger": workspace_no_regret,
    }
    return {
        "workloads": len(workloads),
        "roots_per_workload": 3,
        "performance_sessions": len(performance),
        "memory_profile_sessions": sum(row["role"] == "memory_profile" for row in rows),
        "timed_output_query_rows": len(performance) * 64 * 3,
        "aggregate_workload_median_stage_ns": totals,
        "union_speedup_over_separate": (
            totals[separate]["accounted_total_ns"] / totals[union]["accounted_total_ns"]
        ),
        "workload_median_speedups": workload_speedups,
        "minimum_workload_speedup": min(workload_speedups.values()),
        "p95_session_ns": p95,
        "p95_session_speedup": p95[separate] / p95[union],
        "gates": gates,
        "all_gates_passed": all(gates.values()),
    }


def _verify_frozen_inputs(
    root: Path, freeze_path: Path, dataset_path: Path, verification_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    freeze = _load(freeze_path)
    dataset = _load(dataset_path)
    verification = _load(verification_path)
    validate_dataset(dataset)
    if (
        freeze.get("status") != "frozen_before_dataset_and_timing"
        or dataset.get("provenance", {}).get("freeze_sha256") != _sha256(freeze_path)
        or verification.get("status") != "verified"
        or verification.get("dataset_sha256") != _sha256(dataset_path)
        or verification.get("timing_or_method_output_used") is not False
    ):
        raise ValueError("C37 frozen input boundary failed")
    for relative, identity in freeze["sources"].items():
        path = root.joinpath(*Path(relative).parts)
        if (not path.is_file() or path.stat().st_size != identity["bytes"]
                or _sha256(path) != identity["sha256"]):
            raise ValueError(f"C37 frozen source changed: {relative}")
    library = root.joinpath(*Path(freeze["native_library"]["path"]).parts)
    if (not library.is_file() or library.stat().st_size != freeze["native_library"]["bytes"]
            or _sha256(library) != freeze["native_library"]["sha256"]):
        raise ValueError("C37 frozen library changed")
    return freeze, dataset, library


def _environment(root: Path) -> dict[str, Any]:
    def git(*args: str) -> str | None:
        try:
            value = subprocess.run(
                ["git", *args], cwd=root, check=True, capture_output=True,
                text=True, timeout=10,
            )
            return value.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None
    return {
        "python": sys.version,
        "python_executable": sys.executable,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "git_head": git("rev-parse", "HEAD"),
        "git_status_short": git("status", "--short"),
        "timing_scope": "local_machine_prospective_confirmation",
    }


def run(
    config: NativeConfirmationConfig,
    output_dir: Path,
    freeze_path: Path,
    dataset_path: Path,
    dataset_verification_path: Path,
    project_root: Path,
    *,
    progress: Callable[[str, int, int, str], None] | None = None,
) -> dict[str, Any]:
    config.validate()
    root = project_root.resolve()
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(root):
        raise ValueError("C37 run must stay inside the project")
    freeze, dataset, frozen_library = _verify_frozen_inputs(
        root, freeze_path.resolve(), dataset_path.resolve(),
        dataset_verification_path.resolve(),
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    native_dir = output_dir / "native"
    native_dir.mkdir()
    resident_library = native_dir / frozen_library.name
    shutil.copyfile(frozen_library, resident_library)
    library = load_native_slot_library(resident_library)
    if (library.sha256 != freeze["native_library"]["sha256"]
            or library.abi_version != 1 or not library.supports_multi_root):
        raise ValueError("C37 resident native identity mismatch")
    cases = list(dataset["cases"])
    workloads = prospective_sibling_output_workloads()
    workload_rows = dataset.get("multi_root", {}).get("workloads", [])
    expected_multi = {row["workload_id"]: row["required_output_sha256"]
                      for row in workload_rows}
    if [row["workload_id"] for row in workload_rows] != [row.workload_id for row in workloads]:
        raise ValueError("C37 multi-root dataset identity mismatch")
    expected_single = {case["case_id"]: case["c36_required_output_sha256"] for case in cases}
    started = time.perf_counter()

    for method in SINGLE_METHODS:
        execute_single_session(
            cases[0], method, library, expected_single[cases[0]["case_id"]],
            "performance", False,
        )
    single_rows: list[dict[str, Any]] = []
    base_single_orders = balanced_orders(SINGLE_METHODS)
    single_orders = base_single_orders * (config.single_blocks // len(base_single_orders))
    single_total = len(single_orders) * len(cases) * len(SINGLE_METHODS)
    completed = 0
    for block, order in enumerate(single_orders):
        case_order = list(cases)
        random.Random(f"{config.seed}:single:{block}").shuffle(case_order)
        for position, case in enumerate(case_order):
            for method_position, method in enumerate(order):
                if time.perf_counter() - started > config.max_seconds:
                    raise TimeoutError("C37 confirmation exceeded wall bound")
                row = execute_single_session(
                    case, method, library, expected_single[case["case_id"]],
                    "performance", False,
                )
                row.update({
                    "schema": RAW_SCHEMA, "track": "single_root", "block": block,
                    "case_position": position, "method_position": method_position,
                    "method_order": list(order),
                })
                single_rows.append(row)
                completed += 1
                if progress:
                    progress("single_performance", completed, single_total, case["case_id"])
    for position, case in enumerate(cases):
        order = base_single_orders[position % len(base_single_orders)]
        for method_position, method in enumerate(order):
            row = execute_single_session(
                case, method, library, expected_single[case["case_id"]],
                "memory_profile", True,
            )
            row.update({
                "schema": RAW_SCHEMA, "track": "single_root", "block": None,
                "case_position": position, "method_position": method_position,
                "method_order": list(order),
            })
            single_rows.append(row)

    for method in MULTI_METHODS:
        execute_multi_session(
            workload=workloads[0], method=method, library=library,
            expected_digest=expected_multi[workloads[0].workload_id],
        )
    multi_rows: list[dict[str, Any]] = []
    base_multi_orders = balanced_orders(MULTI_METHODS)
    multi_orders = base_multi_orders * (config.multi_blocks // len(base_multi_orders))
    multi_total = len(multi_orders) * len(workloads) * len(MULTI_METHODS)
    completed = 0
    for block, order in enumerate(multi_orders):
        workload_order = list(workloads)
        random.Random(f"{config.seed}:multi:{block}").shuffle(workload_order)
        for position, workload in enumerate(workload_order):
            for method_position, method in enumerate(order):
                if time.perf_counter() - started > config.max_seconds:
                    raise TimeoutError("C37 confirmation exceeded wall bound")
                row = execute_multi_session(
                    workload=workload, method=method, library=library,
                    expected_digest=expected_multi[workload.workload_id],
                )
                row.update({
                    "schema": RAW_SCHEMA, "track": "multi_root", "block": block,
                    "workload_position": position, "method_position": method_position,
                    "method_order": list(order),
                })
                multi_rows.append(row)
                completed += 1
                if progress:
                    progress("multi_performance", completed, multi_total, workload.workload_id)
    for position, workload in enumerate(workloads):
        for method_position, method in enumerate(MULTI_METHODS):
            row = execute_multi_session(
                workload=workload, method=method, library=library,
                expected_digest=expected_multi[workload.workload_id],
                role="memory_profile", profile_python_allocations=True,
            )
            row.update({
                "schema": RAW_SCHEMA, "track": "multi_root", "block": None,
                "workload_position": position, "method_position": method_position,
                "method_order": list(MULTI_METHODS),
            })
            multi_rows.append(row)

    single_summary = summarize_single(single_rows, cases)
    multi_summary = summarize_multi(multi_rows, workloads)
    all_gates = single_summary["all_gates_passed"] and multi_summary["all_gates_passed"]
    result = {
        "schema": SCHEMA,
        "run_id": config.run_id,
        "status": "complete",
        "config": {**asdict(config),
                   "bitset_environment_cache_policy": "cleared_before_each_session"},
        "freeze": {"path": freeze_path.resolve().relative_to(root).as_posix(),
                   "sha256": _sha256(freeze_path)},
        "dataset": {
            "path": dataset_path.resolve().relative_to(root).as_posix(),
            "sha256": _sha256(dataset_path),
            "verification_path": dataset_verification_path.resolve().relative_to(root).as_posix(),
            "verification_sha256": _sha256(dataset_verification_path),
            "classification": "prospective_parameter_and_truth_disjoint_confirmation",
            "single_root_cases": len(cases), "multi_root_workloads": len(workloads),
        },
        "native_library": {"path": resident_library.relative_to(root).as_posix(),
                           "sha256": library.sha256, "abi_version": library.abi_version,
                           "supports_multi_root": library.supports_multi_root},
        "single_root": single_summary,
        "multi_root": multi_summary,
        "correctness": {
            "canonical_delivery_mismatches": 0,
            "single_root_exact_query_checks": len(single_rows) * 64,
            "multi_root_exact_output_query_checks": len(multi_rows) * 64 * 3,
        },
        "decision": {
            "all_predeclared_gates_passed": all_gates,
            "eligible_for_guarded_integration": all_gates,
            "training": False, "policy_refit": False, "gate_refit": False,
            "production_promotion": False,
        },
        "elapsed_seconds": time.perf_counter() - started,
    }
    all_rows = [*single_rows, *multi_rows]
    _write_jsonl(output_dir / "raw_measurements.jsonl", all_rows)
    _write_json(output_dir / "results.json", result)
    _write_json(output_dir / "environment.json", _environment(root))
    shutil.copyfile(
        root / "docs/recognition/c37_native_exact_confirmation/FROZEN_PROTOCOL_V3_2026_09_03.md",
        output_dir / "protocol.md",
    )
    (output_dir / "report.md").write_text(
        "# C37 prospective native exact confirmation\n\n"
        f"Single-root native/R2 speedup: {single_summary['native_speedup_over_python_r2']:.4f}x; "
        f"minimum case: {single_summary['minimum_case_speedup_over_python_r2']:.4f}x; "
        f"minimum width: {single_summary['minimum_width_speedup_over_python_r2']:.4f}x; "
        f"p95: {single_summary['p95_session_speedup_over_python_r2']:.4f}x.\n\n"
        f"Multi-root union/separate speedup: {multi_summary['union_speedup_over_separate']:.4f}x; "
        f"minimum workload: {multi_summary['minimum_workload_speedup']:.4f}x; "
        f"p95: {multi_summary['p95_session_speedup']:.4f}x.\n\n"
        f"All predeclared gates passed: {str(all_gates).lower()}. Exact mismatches: 0. "
        "No training, refit, or production promotion occurred.\n",
        encoding="utf-8", newline="\n",
    )
    artifact_names = (
        "raw_measurements.jsonl", "results.json", "environment.json", "protocol.md",
        "report.md", f"native/{resident_library.name}",
    )
    _write_json(output_dir / "manifest.json", {
        "schema": "crse-c37-native-exact-confirmation-manifest/v1",
        "run_id": config.run_id,
        "freeze_sha256": _sha256(freeze_path),
        "dataset_sha256": _sha256(dataset_path),
        "dataset_verification_sha256": _sha256(dataset_verification_path),
        "sources": freeze["sources"],
        "artifacts": {
            name: {"bytes": (output_dir / name).stat().st_size,
                   "sha256": _sha256(output_dir / name)}
            for name in artifact_names
        },
    })
    return result
