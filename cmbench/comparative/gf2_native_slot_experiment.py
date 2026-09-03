"""Development-only benchmark for the fused native exact slot executor."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import random
import shutil
import statistics
import time
import tracemalloc
from typing import Any

from bitset_backend import clear_bitset_env_cache
from cm_expr_serde import expr_from_json

from .gf2_native_slots import (
    NativeSlotLibrary,
    compile_native_slot_arena,
    load_native_slot_library,
)
from .gf2_projection_optimization_experiment import (
    _digest,
    _environment,
    _rss_bytes,
    _sha256,
    _write_json,
    _write_text,
    execute_session as execute_reference_session,
)
from .gf2_wide_repeated_queries import (
    CHECKPOINTS,
    oracle_document,
    semantic_document,
    semantic_row,
    validate_dataset,
    validate_query_trace,
    validate_wide_case,
)
from .schedule import balanced_orders


SCHEMA = "crse-native-fused-slot-development/v1"
RAW_SCHEMA = "crse-native-fused-slot-raw-session/v1"
METHODS = (
    "restricted_r2_reference",
    "projection_u16_tuple",
    "native_fused_slots",
)
SOURCE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_native_slots.py",
    "cmbench/comparative/gf2_native_slot_experiment.py",
    "cmbench/comparative/gf2_projection_optimized.py",
    "cmbench/comparative/gf2_projection_optimization_experiment.py",
    "cmbench/comparative/gf2_restricted_evaluators.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "cmbench/comparative/schedule.py",
    "native/cm_fused_slots/CMakeLists.txt",
    "native/cm_fused_slots/build_msvc.cmd",
    "native/cm_fused_slots/fused_slot_executor.c",
    "scripts/build_cm_fused_slots.py",
    "scripts/cm_native_fused_slot_development.py",
    "scripts/crse_native_fused_slot_development_verify.py",
    "scripts/crse_verify_c36_wide_repeated_query_dataset.py",
    "docs/recognition/c36_wide_repeated_query_dataset.json",
)


@dataclass(frozen=True)
class NativeSlotConfig:
    run_id: str
    seed: int = 20260902
    max_seconds: float = 900.0

    @property
    def blocks(self) -> int:
        return len(balanced_orders(METHODS))


def execute_native_session(
    *,
    case: Mapping[str, Any],
    library: NativeSlotLibrary,
    expected_digest: str,
    role: str = "performance",
    clock: Callable[[], int] = time.perf_counter_ns,
    profile_python_allocations: bool = False,
) -> dict[str, Any]:
    normalized = validate_wide_case(case)
    trace = validate_query_trace(
        case.get("c36_trace"), normalized["case_id"], normalized["n_vars"])
    if expected_digest != case.get("c36_required_output_sha256"):
        raise ValueError("native slot oracle binding")
    clear_bitset_env_cache()
    if profile_python_allocations:
        tracemalloc.start()
    rss_start = _rss_bytes()
    task_started = clock()
    started = clock()
    expression = expr_from_json(case["expression_v2"])
    input_decode_ns = max(1, clock() - started)

    started = clock()
    arena = compile_native_slot_arena(case["expression_v2"], library)
    # Allocate every workspace width before the timed query loop.
    for live_count in sorted({len(query["remaining_order"]) for query in trace}):
        words = max(1, ((1 << live_count) + 63) // 64)
        arena._workspaces[words] = (
            __import__("numpy").empty(arena.node_count * words, dtype="uint64"),
            __import__("numpy").empty(words, dtype="uint64"),
        )
    representation_ns = max(1, clock() - started)

    rows: list[dict[str, Any]] = []
    query_timings: list[dict[str, Any]] = []
    checkpoints: dict[str, int] = {}
    cumulative = 0
    for query_index, query in enumerate(trace):
        started = clock()
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        remaining = tuple(query["remaining_order"])
        bindings = arena.prepare_bindings(fixed, remaining)
        restriction_setup_ns = max(1, clock() - started)

        started = clock()
        reduced = arena.evaluate(bindings, len(remaining))
        evaluation_ns = max(1, clock() - started)

        started = clock()
        delivered = semantic_row(query, reduced, normalized["n_vars"])
        row_digest = _digest(delivered)
        delivery_ns = max(1, clock() - started)
        rows.append(delivered)
        total = restriction_setup_ns + evaluation_ns + delivery_ns
        cumulative += total
        query_timings.append({
            "query": query_index,
            "restriction_setup_ns": restriction_setup_ns,
            "evaluation_ns": evaluation_ns,
            "delivery_ns": delivery_ns,
            "total_ns": total,
            "output_sha256": row_digest,
        })
        if query_index + 1 in CHECKPOINTS:
            checkpoints[str(query_index + 1)] = cumulative

    started = clock()
    expression = arena = None
    cleanup_ns = max(1, clock() - started)
    document = semantic_document(normalized["case_id"], rows)
    actual_digest = _digest(document)
    if actual_digest != expected_digest:
        raise RuntimeError("native fused slots failed exact canonical delivery equality")
    wall_ns = max(1, clock() - task_started)
    accounted_ns = input_decode_ns + representation_ns + cumulative + cleanup_ns
    rss_end = _rss_bytes()
    resources: dict[str, Any] = {
        "native_library_path": str(library.path),
        "native_library_sha256": library.sha256,
        "native_abi_version": library.abi_version,
        "arena_nodes": len(case["expression_v2"]["nodes"]),
        "arena_array_bytes": (
            len(case["expression_v2"]["nodes"])
            * (1 + 4 + 4 + 2)),
        "max_workspace_bytes": max(
            compile_native_slot_arena(case["expression_v2"], library).workspace_bytes(width)
            for width in {len(query["remaining_order"]) for query in trace}),
        "rss_start_bytes": rss_start,
        "rss_end_bytes": rss_end,
        "rss_end_minus_start_bytes": (
            rss_end - rss_start if rss_start is not None and rss_end is not None else None),
    }
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
        "method": "native_fused_slots",
        "status": "ok",
        "exact_check_passed": True,
        "output_sha256": actual_digest,
        "timings_ns": {
            "input_decode_ns": input_decode_ns,
            "representation_ns": representation_ns,
            "restriction_setup_ns": sum(row["restriction_setup_ns"] for row in query_timings),
            "evaluation_ns": sum(row["evaluation_ns"] for row in query_timings),
            "delivery_ns": sum(row["delivery_ns"] for row in query_timings),
            "query_total_ns": cumulative,
            "cleanup_ns": cleanup_ns,
            "accounted_total_ns": accounted_ns,
            "observed_task_wall_ns": wall_ns,
        },
        "checkpoint_query_ns": checkpoints,
        "checkpoint_total_ns": {
            key: setup_ns + value + cleanup_ns for key, value in checkpoints.items()
        },
        "query_measurements": query_timings,
        "resources": resources,
    }


def _execute(
    case: Mapping[str, Any], method: str, library: NativeSlotLibrary,
    expected_digest: str, role: str, memory: bool,
) -> dict[str, Any]:
    if method == "native_fused_slots":
        return execute_native_session(
            case=case, library=library, expected_digest=expected_digest,
            role=role, profile_python_allocations=memory)
    row = execute_reference_session(
        case=case, method=method, expected_digest=expected_digest,
        role=role, profile_python_allocations=memory)
    row["schema"] = RAW_SCHEMA
    return row


def _summarize(rows: list[dict[str, Any]], cases: list[dict[str, Any]]) -> dict[str, Any]:
    stages = (
        "input_decode_ns", "representation_ns", "restriction_setup_ns",
        "evaluation_ns", "delivery_ns", "query_total_ns", "cleanup_ns",
        "accounted_total_ns",
    )
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["role"] == "performance":
            grouped[(row["case_id"], row["method"])].append(row)
    medians = {
        (case["case_id"], method): {
            stage: int(statistics.median_low(
                row["timings_ns"][stage]
                for row in grouped[(case["case_id"], method)]))
            for stage in stages
        }
        for case in cases for method in METHODS
    }
    totals = {
        method: {
            stage: sum(medians[(case["case_id"], method)][stage] for case in cases)
            for stage in stages
        }
        for method in METHODS
    }
    q64 = {method: totals[method]["accounted_total_ns"] for method in METHODS}
    best = min(METHODS, key=lambda method: (q64[method], method))
    oracle = sum(min(medians[(case["case_id"], method)]["accounted_total_ns"]
                     for method in METHODS) for case in cases)
    memory = {}
    for method in METHODS:
        selected = [row for row in rows
                    if row["role"] == "memory_profile" and row["method"] == method]
        memory[method] = {
            "sessions": len(selected),
            "max_tracemalloc_peak_bytes": max(
                row["resources"].get("tracemalloc_peak_bytes", 0) for row in selected),
        }
    return {
        "cases": len(cases),
        "performance_sessions": sum(row["role"] == "performance" for row in rows),
        "memory_profile_sessions": sum(row["role"] == "memory_profile" for row in rows),
        "timed_queries": sum(64 for row in rows if row["role"] == "performance"),
        "aggregate_case_median_stage_ns": totals,
        "q64_accounted_total_ns": q64,
        "best_method": best,
        "native_speedup_over_python_r2": (
            q64["restricted_r2_reference"] / q64["native_fused_slots"]),
        "native_speedup_over_projection_u16": (
            q64["projection_u16_tuple"] / q64["native_fused_slots"]),
        "native_ten_percent_gate": (
            q64["restricted_r2_reference"] / q64["native_fused_slots"] >= 1.10),
        "per_case_oracle_total_ns": oracle,
        "oracle_speedup_over_best_fixed": q64[best] / oracle,
        "memory_profiles": memory,
    }


def run(
    config: NativeSlotConfig,
    output_dir: Path,
    dataset_path: Path,
    library_path: Path,
    project_root: Path,
    *,
    progress: Callable[[str, int, int, str], None] | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    output_dir = output_dir.resolve()
    library_path = library_path.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    native_dir = output_dir / "native"
    native_dir.mkdir()
    resident_library = native_dir / library_path.name
    shutil.copyfile(library_path, resident_library)
    started = time.perf_counter()
    library = load_native_slot_library(resident_library)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    cases = list(dataset["cases"])
    expected = {
        case["case_id"]: _digest(oracle_document(case, case["c36_trace"]))
        for case in cases
    }
    for method in METHODS:
        _execute(cases[0], method, library, expected[cases[0]["case_id"]],
                 "performance", False)

    rows: list[dict[str, Any]] = []
    orders = balanced_orders(METHODS)
    total = len(orders) * len(cases) * len(METHODS)
    completed = 0
    for block, order in enumerate(orders):
        case_order = list(cases)
        random.Random(config.seed + block).shuffle(case_order)
        for case_position, case in enumerate(case_order):
            for method_position, method in enumerate(order):
                if time.perf_counter() - started > config.max_seconds:
                    raise TimeoutError("native slot experiment exceeded max_seconds")
                row = _execute(
                    case, method, library, expected[case["case_id"]],
                    "performance", False)
                row.update({
                    "block": block, "case_position": case_position,
                    "method_position": method_position, "method_order": list(order),
                })
                rows.append(row)
                completed += 1
                if progress:
                    progress("performance", completed, total, case["case_id"])

    memory_total = len(cases) * len(METHODS)
    completed = 0
    for case_position, case in enumerate(cases):
        order = orders[case_position % len(orders)]
        for method_position, method in enumerate(order):
            row = _execute(
                case, method, library, expected[case["case_id"]],
                "memory_profile", True)
            row.update({
                "block": None, "case_position": case_position,
                "method_position": method_position, "method_order": list(order),
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
            "seed": config.seed, "blocks": config.blocks,
            "max_seconds": config.max_seconds,
            "bitset_environment_cache_policy": "cleared_before_each_session",
        },
        "dataset": {
            "path": dataset_path.relative_to(project_root).as_posix(),
            "sha256": _sha256(dataset_path),
            "classification": "development_exposed_c36_not_confirmation",
            "cases": len(cases), "queries_per_case": 64,
        },
        "native_library": {
            "path": library.path.relative_to(project_root).as_posix(),
            "sha256": library.sha256, "abi_version": library.abi_version,
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
            "continue_native_executor": summary["native_ten_percent_gate"],
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
        "# Native fused-slot development protocol\n\n"
        "Development-only exposed C36 comparison of Python R2, uint16 projection, "
        "and one C11 native word-array slot loop. Six complete balanced blocks; "
        "cache-isolated task sessions; identical 64-query exact semantic delivery; "
        "separate memory sessions excluded from timing. Continue at >=1.10x native "
        "gain over Python R2. No confirmation or production promotion.\n"
    ))
    q64 = summary["q64_accounted_total_ns"]
    _write_text(output_dir / "report.md", (
        f"# Native fused-slot development result\n\n"
        f"Exact mismatches: 0. Native: {q64['native_fused_slots'] / 1e6:.3f} ms; "
        f"Python R2: {q64['restricted_r2_reference'] / 1e6:.3f} ms; "
        f"uint16 projection: {q64['projection_u16_tuple'] / 1e6:.3f} ms. "
        f"Native/Python R2 speedup: {summary['native_speedup_over_python_r2']:.4f}x. "
        f"Ten-percent continuation gate: "
        f"{str(summary['native_ten_percent_gate']).lower()}.\n"
    ))
    artifacts = {}
    for name in ("raw_measurements.jsonl", "results.json", "environment.json",
                 "protocol.md", "report.md", f"native/{library_path.name}"):
        path = output_dir / name
        artifacts[name] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    sources = {}
    for relative in SOURCE_PATHS:
        path = project_root / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        sources[relative] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    _write_json(output_dir / "manifest.json", {
        "schema": "crse-native-fused-slot-manifest/v1",
        "run_id": config.run_id,
        "artifacts": artifacts,
        "sources": sources,
        "native_library": {
            "path": library.path.relative_to(project_root).as_posix(),
            "bytes": library.path.stat().st_size,
            "sha256": library.sha256,
            "abi_version": library.abi_version,
        },
    })
    return result
