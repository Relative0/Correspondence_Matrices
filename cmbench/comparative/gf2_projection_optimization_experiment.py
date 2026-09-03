"""Counterbalanced development benchmark for exact projection-internal variants."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
import tracemalloc
from typing import Any

import numpy as np

from bitset_backend import (
    bitset_to_bool_array,
    build_bitset_env,
    clear_bitset_env_cache,
    eval_expr_bitset,
)
from cm_expr_serde import expr_from_json

from .contracts import canonical_bytes
from .gf2_projection_optimized import (
    compile_flat_projection_plan,
    compile_packed_cofactor_plan,
    project_packed_truth,
    projection_indices_typed,
)
from .gf2_restricted_evaluators import (
    compile_restricted_arena,
    eval_restricted_r2,
    prepare_restriction,
)
from .gf2_wide_repeated_queries import (
    CHECKPOINTS,
    oracle_document,
    project_truth_vector,
    projection_indices,
    semantic_document,
    semantic_row,
    validate_dataset,
    validate_query_trace,
    validate_wide_case,
)
from .schedule import balanced_orders


SCHEMA = "crse-projection-optimization-development/v1"
RAW_SCHEMA = "crse-projection-optimization-raw-session/v1"
METHODS = (
    "restricted_r2_reference",
    "projection_u32_control",
    "projection_u16_tuple",
    "projection_u16_flat",
    "projection_packed_cofactor",
)
PROJECTION_METHODS = METHODS[1:]
SOURCE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_projection_optimized.py",
    "cmbench/comparative/gf2_projection_optimization_experiment.py",
    "cmbench/comparative/gf2_restricted_evaluators.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "cmbench/comparative/schedule.py",
    "scripts/cm_projection_optimization_development.py",
    "scripts/crse_projection_optimization_development_verify.py",
    "scripts/crse_verify_c36_wide_repeated_query_dataset.py",
    "docs/recognition/c36_wide_repeated_query_dataset.json",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def _write_text(path: Path, value: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(value)


def _rss_bytes() -> int | None:
    try:
        import psutil
        return int(psutil.Process(os.getpid()).memory_info().rss)
    except (ImportError, OSError):
        return None


@dataclass(frozen=True)
class ProjectionOptimizationConfig:
    run_id: str
    seed: int = 20260902
    max_seconds: float = 900.0

    @property
    def blocks(self) -> int:
        return len(balanced_orders(METHODS))


def execute_session(
    *,
    case: Mapping[str, Any],
    method: str,
    expected_digest: str,
    role: str = "performance",
    clock: Callable[[], int] = time.perf_counter_ns,
    profile_python_allocations: bool = False,
) -> dict[str, Any]:
    """Execute all 64 exact queries with common stage boundaries."""
    if method not in METHODS or role not in ("performance", "memory_profile"):
        raise ValueError("invalid projection optimization session")
    normalized = validate_wide_case(case)
    trace = validate_query_trace(
        case.get("c36_trace"), normalized["case_id"], normalized["n_vars"])
    if expected_digest != case.get("c36_required_output_sha256"):
        raise ValueError("projection optimization oracle binding")
    # Each row is one complete resident-engine task.  Cross-arm reuse of the
    # process-global environment LRU otherwise warms projection with projection
    # and R2 with unrelated R0/R1 arms, making the comparison depend on which
    # other methods happen to share the process.  Preserve reuse within the 64
    # queries, but isolate task sessions from one another.
    clear_bitset_env_cache()
    if profile_python_allocations:
        tracemalloc.start()
    rss_start = _rss_bytes()
    task_started = clock()
    started = clock()
    expression = expr_from_json(case["expression_v2"])
    input_decode_ns = max(1, clock() - started)

    arena = None
    full_bits = None
    truth_vector = None
    tuple_plans = None
    flat_plan = None
    packed_plans = None
    resources: dict[str, Any] = {}
    started = clock()
    if method == "restricted_r2_reference":
        arena = compile_restricted_arena(case["expression_v2"])
        resources["arena_nodes"] = arena.node_count
    else:
        names = tuple(f"x{i}" for i in range(normalized["n_vars"]))
        full_bits = eval_expr_bitset(expression, build_bitset_env(names))
        if method != "projection_packed_cofactor":
            truth_vector = bitset_to_bool_array(full_bits, normalized["n_vars"])
            resources["materialized_truth_vector_bytes"] = int(truth_vector.nbytes)
        if method == "projection_u32_control":
            tuple_plans = []
            for query in trace:
                fixed = {row["variable"]: row["value"] for row in query["fixed"]}
                tuple_plans.append(projection_indices(
                    normalized["n_vars"], fixed, query["remaining_order"]))
            resources["compiled_projection_index_bytes"] = sum(
                plan.nbytes for plan in tuple_plans)
            resources["index_dtype"] = "uint32"
            resources["index_arrays"] = len(tuple_plans)
        elif method == "projection_u16_tuple":
            tuple_plans = []
            for query in trace:
                fixed = {row["variable"]: row["value"] for row in query["fixed"]}
                tuple_plans.append(projection_indices_typed(
                    normalized["n_vars"], fixed, query["remaining_order"]))
            resources["compiled_projection_index_bytes"] = sum(
                plan.nbytes for plan in tuple_plans)
            resources["index_dtype"] = "uint16"
            resources["index_arrays"] = len(tuple_plans)
        elif method == "projection_u16_flat":
            flat_plan = compile_flat_projection_plan(normalized["n_vars"], trace)
            resources["compiled_projection_index_bytes"] = flat_plan.index_bytes
            resources["index_dtype"] = flat_plan.dtype_name
            resources["index_arrays"] = 1
        else:
            packed_plans = []
            for query in trace:
                fixed = {row["variable"]: row["value"] for row in query["fixed"]}
                packed_plans.append(compile_packed_cofactor_plan(
                    normalized["n_vars"], fixed, query["remaining_order"]))
            resources["materialized_truth_packed_bytes"] = (1 << normalized["n_vars"]) // 8
            resources["compiled_cofactor_plan_bytes_estimate"] = sum(
                plan.plan_bytes_estimate for plan in packed_plans)
    representation_ns = max(1, clock() - started)

    rows: list[dict[str, Any]] = []
    query_timings: list[dict[str, Any]] = []
    checkpoint_query_ns: dict[str, int] = {}
    cumulative_query_ns = 0
    for query_index, query in enumerate(trace):
        started = clock()
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        remaining = tuple(query["remaining_order"])
        prepared = (prepare_restriction(fixed, remaining)
                    if method == "restricted_r2_reference" else None)
        restriction_setup_ns = max(1, clock() - started)

        started = clock()
        if method == "restricted_r2_reference":
            if arena is None or prepared is None:
                raise AssertionError("R2 session was not prepared")
            reduced = eval_restricted_r2(arena, prepared)
        elif method == "projection_u16_flat":
            reduced = project_truth_vector(truth_vector, flat_plan.query_indices(query_index))
        elif method == "projection_packed_cofactor":
            reduced = project_packed_truth(full_bits, packed_plans[query_index])
        else:
            reduced = project_truth_vector(truth_vector, tuple_plans[query_index])
        evaluation_ns = max(1, clock() - started)

        started = clock()
        delivered = semantic_row(query, int(reduced), normalized["n_vars"])
        row_digest = _digest(delivered)
        delivery_ns = max(1, clock() - started)
        rows.append(delivered)
        query_total_ns = restriction_setup_ns + evaluation_ns + delivery_ns
        cumulative_query_ns += query_total_ns
        query_timings.append({
            "query": query_index,
            "restriction_setup_ns": restriction_setup_ns,
            "evaluation_ns": evaluation_ns,
            "delivery_ns": delivery_ns,
            "total_ns": query_total_ns,
            "output_sha256": row_digest,
        })
        if query_index + 1 in CHECKPOINTS:
            checkpoint_query_ns[str(query_index + 1)] = cumulative_query_ns

    started = clock()
    expression = arena = full_bits = truth_vector = tuple_plans = flat_plan = packed_plans = None
    cleanup_ns = max(1, clock() - started)
    document = semantic_document(normalized["case_id"], rows)
    actual_digest = _digest(document)
    if actual_digest != expected_digest:
        raise RuntimeError(f"{method} failed exact canonical delivery equality")
    task_wall_ns = max(1, clock() - task_started)
    accounted_ns = input_decode_ns + representation_ns + cumulative_query_ns + cleanup_ns
    rss_end = _rss_bytes()
    resources.update({
        "rss_start_bytes": rss_start,
        "rss_end_bytes": rss_end,
        "rss_end_minus_start_bytes": (
            rss_end - rss_start if rss_start is not None and rss_end is not None else None),
    })
    if profile_python_allocations:
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        resources["tracemalloc_peak_bytes"] = int(peak)
    setup_ns = input_decode_ns + representation_ns
    return {
        "schema": RAW_SCHEMA,
        "role": role,
        "case_id": normalized["case_id"],
        "family": case["family"],
        "n_vars": normalized["n_vars"],
        "method": method,
        "status": "ok",
        "exact_check_passed": True,
        "output_sha256": actual_digest,
        "timings_ns": {
            "input_decode_ns": input_decode_ns,
            "representation_ns": representation_ns,
            "restriction_setup_ns": sum(row["restriction_setup_ns"] for row in query_timings),
            "evaluation_ns": sum(row["evaluation_ns"] for row in query_timings),
            "delivery_ns": sum(row["delivery_ns"] for row in query_timings),
            "query_total_ns": cumulative_query_ns,
            "cleanup_ns": cleanup_ns,
            "accounted_total_ns": accounted_ns,
            "observed_task_wall_ns": task_wall_ns,
        },
        "checkpoint_query_ns": checkpoint_query_ns,
        "checkpoint_total_ns": {
            key: setup_ns + value + cleanup_ns
            for key, value in checkpoint_query_ns.items()
        },
        "query_measurements": query_timings,
        "resources": resources,
    }


def _median_rows(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, int]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["role"] == "performance":
            grouped[(row["case_id"], row["method"])].append(row)
    output: dict[tuple[str, str], dict[str, int]] = {}
    for key, sessions in grouped.items():
        output[key] = {
            stage: int(statistics.median_low(
                session["timings_ns"][stage] for session in sessions))
            for stage in (
                "input_decode_ns", "representation_ns", "restriction_setup_ns",
                "evaluation_ns", "delivery_ns", "query_total_ns", "cleanup_ns",
                "accounted_total_ns",
            )
        }
    return output


def _summarize(rows: list[dict[str, Any]], cases: list[dict[str, Any]]) -> dict[str, Any]:
    medians = _median_rows(rows)
    case_ids = [case["case_id"] for case in cases]
    totals = {
        method: {
            stage: sum(medians[(case_id, method)][stage] for case_id in case_ids)
            for stage in next(iter(medians.values()))
        }
        for method in METHODS
    }
    q64 = {method: totals[method]["accounted_total_ns"] for method in METHODS}
    best_projection = min(PROJECTION_METHODS, key=lambda method: (q64[method], method))
    control = q64["projection_u32_control"]
    r2 = q64["restricted_r2_reference"]
    best = q64[best_projection]
    memory: dict[str, Any] = {}
    for method in METHODS:
        method_rows = [row for row in rows
                       if row["role"] == "memory_profile" and row["method"] == method]
        memory[method] = {
            "sessions": len(method_rows),
            "max_tracemalloc_peak_bytes": max(
                row["resources"].get("tracemalloc_peak_bytes", 0) for row in method_rows),
            "max_positive_rss_end_minus_start_bytes": max(
                max(0, row["resources"].get("rss_end_minus_start_bytes") or 0)
                for row in method_rows),
        }
    return {
        "cases": len(cases),
        "performance_sessions": sum(row["role"] == "performance" for row in rows),
        "memory_profile_sessions": sum(row["role"] == "memory_profile" for row in rows),
        "timed_queries": sum(64 for row in rows if row["role"] == "performance"),
        "aggregate_case_median_stage_ns": totals,
        "q64_accounted_total_ns": q64,
        "best_projection_method": best_projection,
        "best_projection_speedup_over_u32_control": control / best,
        "r2_speedup_over_best_projection": best / r2,
        "best_projection_speedup_over_r2": r2 / best,
        "projection_reaches_r2": best <= r2,
        "projection_cleanup_five_percent_gate": control / best >= 1.05,
        "memory_profiles": memory,
    }


def _environment(project_root: Path) -> dict[str, Any]:
    def git(*args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", *args], cwd=project_root, check=True,
                capture_output=True, text=True, timeout=10)
            return result.stdout.strip()
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
        "timing_scope": "local_machine_development_only",
    }


def run(
    config: ProjectionOptimizationConfig,
    output_dir: Path,
    dataset_path: Path,
    project_root: Path,
    *,
    progress: Callable[[str, int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Run, summarize, and bind one immutable development experiment."""
    output_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    cases = list(dataset["cases"])
    expected = {
        case["case_id"]: _digest(oracle_document(case, case["c36_trace"]))
        for case in cases
    }
    for case in cases:
        if expected[case["case_id"]] != case["c36_required_output_sha256"]:
            raise ValueError("projection optimization dataset oracle mismatch")

    # One untimed pass avoids charging import/first-call effects to an arbitrary arm.
    for method in METHODS:
        execute_session(
            case=cases[0], method=method,
            expected_digest=expected[cases[0]["case_id"]])

    rows: list[dict[str, Any]] = []
    orders = balanced_orders(METHODS)
    performance_total = len(orders) * len(cases) * len(METHODS)
    completed = 0
    for block, order in enumerate(orders):
        case_order = list(cases)
        random.Random(config.seed + block).shuffle(case_order)
        for case_position, case in enumerate(case_order):
            for method_position, method in enumerate(order):
                if time.perf_counter() - started > config.max_seconds:
                    raise TimeoutError("projection optimization exceeded max_seconds")
                row = execute_session(
                    case=case, method=method,
                    expected_digest=expected[case["case_id"]])
                row.update({
                    "block": block,
                    "case_position": case_position,
                    "method_position": method_position,
                    "method_order": list(order),
                })
                rows.append(row)
                completed += 1
                if progress:
                    progress("performance", completed, performance_total, case["case_id"])

    memory_total = len(cases) * len(METHODS)
    completed = 0
    for case_index, case in enumerate(cases):
        order = orders[case_index % len(orders)]
        for method_position, method in enumerate(order):
            row = execute_session(
                case=case, method=method,
                expected_digest=expected[case["case_id"]],
                role="memory_profile", profile_python_allocations=True)
            row.update({
                "block": None,
                "case_position": case_index,
                "method_position": method_position,
                "method_order": list(order),
            })
            rows.append(row)
            completed += 1
            if progress:
                progress("memory_profile", completed, memory_total, case["case_id"])

    summary = _summarize(rows, cases)
    result = {
        "schema": SCHEMA,
        "run_id": config.run_id,
        "status": "complete",
        "config": {
            "seed": config.seed,
            "blocks": config.blocks,
            "max_seconds": config.max_seconds,
            "bitset_environment_cache_policy": "cleared_before_each_session",
        },
        "dataset": {
            "path": dataset_path.relative_to(project_root).as_posix(),
            "sha256": _sha256(dataset_path),
            "classification": "development_exposed_c36_not_confirmation",
            "cases": len(cases),
            "queries_per_case": 64,
        },
        "methods": list(METHODS),
        "correctness": {
            "canonical_delivery_mismatches": 0,
            "exact_query_checks": len(rows) * 64,
        },
        "summary": summary,
        "decision": {
            "production_write": False,
            "production_promotion": False,
            "prospective_data_consumed": False,
            "best_projection_method": summary["best_projection_method"],
            "projection_reaches_r2": summary["projection_reaches_r2"],
            "continue_projection_optimization": summary["projection_reaches_r2"],
        },
        "elapsed_seconds": time.perf_counter() - started,
    }

    raw_path = output_dir / "raw_measurements.jsonl"
    with raw_path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False) + "\n")
    _write_json(output_dir / "results.json", result)
    _write_json(output_dir / "environment.json", _environment(project_root))
    _write_text(output_dir / "protocol.md", (
        "# Projection optimization development protocol\n\n"
        "Development-only reuse of the exposed C36 cases and frozen traces. Five exact "
        "methods run in the complete ten-block balanced order. Every session includes "
        "input decoding, representation construction, 64 queries, canonical semantic "
        "delivery, and cleanup. The process-global bitset-environment LRU is cleared "
        "before every session, while reuse within a session remains enabled. One "
        "separate memory-profile session per case/method is "
        "excluded from timing summaries. No C37 or production decision is permitted.\n"
    ))
    q64 = summary["q64_accounted_total_ns"]
    best = summary["best_projection_method"]
    _write_text(output_dir / "report.md", (
        f"# Projection optimization development result\n\n"
        f"Run: `{config.run_id}`. Exact mismatches: 0.\n\n"
        f"Best projection: `{best}` at {q64[best] / 1e6:.3f} ms aggregate q64. "
        f"The uint32 control took {q64['projection_u32_control'] / 1e6:.3f} ms "
        f"({summary['best_projection_speedup_over_u32_control']:.4f}x improvement). "
        f"Repaired R2 took {q64['restricted_r2_reference'] / 1e6:.3f} ms and is "
        f"{summary['r2_speedup_over_best_projection']:.4f}x faster than the best "
        f"projection variant. Projection reaches R2: "
        f"{str(summary['projection_reaches_r2']).lower()}.\n\n"
        "This exposed development result cannot promote a production policy or consume "
        "prospective confirmation data.\n"
    ))
    artifacts = {}
    for name in ("raw_measurements.jsonl", "results.json", "environment.json",
                 "protocol.md", "report.md"):
        path = output_dir / name
        artifacts[name] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    sources = {}
    for relative in SOURCE_PATHS:
        path = project_root / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        sources[relative] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    _write_json(output_dir / "manifest.json", {
        "schema": "crse-projection-optimization-manifest/v1",
        "run_id": config.run_id,
        "artifacts": artifacts,
        "sources": sources,
    })
    return result
