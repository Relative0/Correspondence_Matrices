"""Development benchmark for native sibling-root union compilation."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
import random
import shutil
import statistics
import time
import tracemalloc
from typing import Any

import numpy as np

from bitset_backend import build_bitset_env, clear_bitset_env_cache, eval_expr_bitset

from .gf2_multi_root import MultiRootWorkload, sibling_output_workloads
from .gf2_native_slots import (
    NativeSlotLibrary,
    compile_native_multi_root_arena,
    compile_native_slot_arena,
    load_native_slot_library,
)
from .gf2_projection_optimization_experiment import (
    _digest, _environment, _rss_bytes, _sha256, _write_json, _write_text,
)
from .gf2_wide_repeated_queries import (
    CHECKPOINTS, restrict_full_truth, semantic_row,
)
from .schedule import balanced_orders


SCHEMA = "crse-native-multi-root-development/v1"
RAW_SCHEMA = "crse-native-multi-root-raw-session/v1"
SEMANTIC_SCHEMA = "crse-native-multi-root-output/v1"
METHODS = ("native_separate_roots", "native_union_roots")
SOURCE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_multi_root.py",
    "cmbench/comparative/gf2_multi_root_experiment.py",
    "cmbench/comparative/gf2_native_slots.py",
    "cmbench/comparative/gf2_projection_optimization_experiment.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "cmbench/comparative/schedule.py",
    "cmbench/recognition/yosys_unused_gf2_data.py",
    "native/cm_fused_slots/CMakeLists.txt",
    "native/cm_fused_slots/build_msvc.cmd",
    "native/cm_fused_slots/fused_slot_executor.c",
    "scripts/build_cm_fused_slots.py",
    "scripts/cm_native_multi_root_development.py",
    "scripts/crse_native_multi_root_development_verify.py",
)


@dataclass(frozen=True)
class MultiRootConfig:
    run_id: str
    seed: int = 20260902
    blocks: int = 20
    max_seconds: float = 900.0


def _oracle(workload: MultiRootWorkload) -> tuple[str, tuple[int, ...]]:
    names = tuple(f"x{index}" for index in range(workload.n_vars))
    full_truths = tuple(
        eval_expr_bitset(root, build_bitset_env(names)) for root in workload.roots)
    query_rows = []
    for query in workload.trace:
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        values = tuple(restrict_full_truth(bits, workload.n_vars, fixed)[1]
                       for bits in full_truths)
        query_rows.append(_delivery_row(workload, query, values))
    document = {
        "schema": SEMANTIC_SCHEMA,
        "workload_id": workload.workload_id,
        "rows": query_rows,
    }
    return _digest(document), full_truths


def _delivery_row(
    workload: MultiRootWorkload,
    query: dict[str, Any],
    values: tuple[int, ...],
) -> dict[str, Any]:
    return {
        "query": query["query"],
        "query_sha256": query["query_sha256"],
        "outputs": [
            {"output_index": index,
             "semantic": semantic_row(query, value, workload.n_vars)}
            for index, value in enumerate(values)
        ],
    }


def _allocate_single(arena: Any, live_widths: set[int]) -> None:
    for width in live_widths:
        words = max(1, ((1 << width) + 63) // 64)
        arena._workspaces[words] = (
            np.empty(arena.node_count * words, dtype=np.uint64),
            np.empty(words, dtype=np.uint64),
        )


def _allocate_multi(arena: Any, live_widths: set[int]) -> None:
    for width in live_widths:
        words = max(1, ((1 << width) + 63) // 64)
        arena._workspaces[words] = (
            np.empty(arena.node_count * words, dtype=np.uint64),
            np.empty(arena.root_count * words, dtype=np.uint64),
        )


def execute_session(
    *,
    workload: MultiRootWorkload,
    method: str,
    library: NativeSlotLibrary,
    expected_digest: str,
    role: str = "performance",
    clock: Callable[[], int] = time.perf_counter_ns,
    profile_python_allocations: bool = False,
) -> dict[str, Any]:
    if method not in METHODS or role not in ("performance", "memory_profile"):
        raise ValueError("invalid multi-root session")
    clear_bitset_env_cache()
    if profile_python_allocations:
        tracemalloc.start()
    rss_start = _rss_bytes()
    task_started = clock()
    started = clock()
    union_document = workload.union_document
    separate_documents = workload.separate_documents
    input_decode_ns = max(1, clock() - started)

    live_widths = {len(query["remaining_order"]) for query in workload.trace}
    started = clock()
    if method == "native_separate_roots":
        separate = tuple(
            compile_native_slot_arena(
                document, library, variable_count=workload.n_vars)
            for document in separate_documents)
        for arena in separate:
            _allocate_single(arena, live_widths)
        union = None
        representation_nodes = sum(arena.node_count for arena in separate)
        arena_bytes = sum(arena.arena_bytes for arena in separate)
        max_workspace = max(
            sum(arena.workspace_bytes(width) for arena in separate)
            for width in live_widths)
    else:
        union = compile_native_multi_root_arena(
            union_document, library, variable_count=workload.n_vars)
        _allocate_multi(union, live_widths)
        separate = None
        representation_nodes = union.node_count
        arena_bytes = union.arena_bytes
        max_workspace = max(union.workspace_bytes(width) for width in live_widths)
    representation_ns = max(1, clock() - started)

    rows = []
    query_measurements = []
    checkpoint_query_ns: dict[str, int] = {}
    cumulative = 0
    for query_index, query in enumerate(workload.trace):
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        remaining = tuple(query["remaining_order"])
        started = clock()
        binding_owner = union if union is not None else separate[0]
        bindings = binding_owner.prepare_bindings(fixed, remaining)
        restriction_setup_ns = max(1, clock() - started)

        started = clock()
        if union is not None:
            values = union.evaluate(bindings, len(remaining))
        else:
            values = tuple(arena.evaluate(bindings, len(remaining)) for arena in separate)
        evaluation_ns = max(1, clock() - started)

        started = clock()
        delivered = _delivery_row(workload, query, values)
        row_digest = _digest(delivered)
        delivery_ns = max(1, clock() - started)
        rows.append(delivered)
        query_total = restriction_setup_ns + evaluation_ns + delivery_ns
        cumulative += query_total
        query_measurements.append({
            "query": query_index,
            "restriction_setup_ns": restriction_setup_ns,
            "evaluation_ns": evaluation_ns,
            "delivery_ns": delivery_ns,
            "total_ns": query_total,
            "output_sha256": row_digest,
        })
        if query_index + 1 in CHECKPOINTS:
            checkpoint_query_ns[str(query_index + 1)] = cumulative

    started = clock()
    union = separate = None
    cleanup_ns = max(1, clock() - started)
    document = {
        "schema": SEMANTIC_SCHEMA,
        "workload_id": workload.workload_id,
        "rows": rows,
    }
    actual_digest = _digest(document)
    if actual_digest != expected_digest:
        raise RuntimeError("native multi-root exact delivery mismatch")
    accounted = input_decode_ns + representation_ns + cumulative + cleanup_ns
    wall = max(1, clock() - task_started)
    rss_end = _rss_bytes()
    resources: dict[str, Any] = {
        "root_count": len(workload.roots),
        "sum_separate_nodes": sum(len(document["nodes"])
                                  for document in separate_documents),
        "union_nodes": len(union_document["nodes"]),
        "compiled_representation_nodes": representation_nodes,
        "arena_array_bytes": arena_bytes,
        "max_workspace_bytes": max_workspace,
        "native_library_sha256": library.sha256,
        "native_abi_version": library.abi_version,
        "rss_start_bytes": rss_start,
        "rss_end_bytes": rss_end,
        "rss_end_minus_start_bytes": (
            rss_end - rss_start if rss_start is not None and rss_end is not None else None),
    }
    if profile_python_allocations:
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        resources["tracemalloc_peak_bytes"] = int(peak)
    setup = input_decode_ns + representation_ns
    return {
        "schema": RAW_SCHEMA,
        "role": role,
        "workload_id": workload.workload_id,
        "family": workload.family,
        "n_vars": workload.n_vars,
        "method": method,
        "status": "ok",
        "exact_check_passed": True,
        "output_sha256": actual_digest,
        "timings_ns": {
            "input_decode_ns": input_decode_ns,
            "representation_ns": representation_ns,
            "restriction_setup_ns": sum(row["restriction_setup_ns"] for row in query_measurements),
            "evaluation_ns": sum(row["evaluation_ns"] for row in query_measurements),
            "delivery_ns": sum(row["delivery_ns"] for row in query_measurements),
            "query_total_ns": cumulative,
            "cleanup_ns": cleanup_ns,
            "accounted_total_ns": accounted,
            "observed_task_wall_ns": wall,
        },
        "checkpoint_query_ns": checkpoint_query_ns,
        "checkpoint_total_ns": {
            key: setup + value + cleanup_ns for key, value in checkpoint_query_ns.items()
        },
        "query_measurements": query_measurements,
        "resources": resources,
    }


def _summarize(rows: list[dict[str, Any]], workloads: tuple[MultiRootWorkload, ...]) -> dict[str, Any]:
    stages = (
        "input_decode_ns", "representation_ns", "restriction_setup_ns",
        "evaluation_ns", "delivery_ns", "query_total_ns", "cleanup_ns",
        "accounted_total_ns",
    )
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["role"] == "performance":
            grouped[(row["workload_id"], row["method"])].append(row)
    medians = {
        (workload.workload_id, method): {
            stage: int(statistics.median_low(
                row["timings_ns"][stage]
                for row in grouped[(workload.workload_id, method)]))
            for stage in stages
        }
        for workload in workloads for method in METHODS
    }
    totals = {
        method: {
            stage: sum(medians[(workload.workload_id, method)][stage]
                       for workload in workloads)
            for stage in stages
        }
        for method in METHODS
    }
    separate = totals["native_separate_roots"]["accounted_total_ns"]
    union = totals["native_union_roots"]["accounted_total_ns"]
    return {
        "workloads": len(workloads),
        "roots_per_workload": 3,
        "performance_sessions": sum(row["role"] == "performance" for row in rows),
        "memory_profile_sessions": sum(row["role"] == "memory_profile" for row in rows),
        "timed_output_query_rows": sum(3 * 64 for row in rows
                                       if row["role"] == "performance"),
        "aggregate_workload_median_stage_ns": totals,
        "union_speedup_over_separate": separate / union,
        "union_ten_percent_gate": separate / union >= 1.10,
        "all_workloads_union_node_reduction": all(
            len(workload.union_document["nodes"])
            < sum(len(document["nodes"]) for document in workload.separate_documents)
            for workload in workloads),
    }


def run(
    config: MultiRootConfig,
    output_dir: Path,
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
    shutil.copyfile(library_path.resolve(), resident_library)
    library = load_native_slot_library(resident_library)
    if not library.supports_multi_root:
        raise ValueError("native library lacks multi-root ABI")
    workloads = sibling_output_workloads()
    expected = {workload.workload_id: _oracle(workload)[0] for workload in workloads}
    started = time.perf_counter()
    for method in METHODS:
        execute_session(
            workload=workloads[0], method=method, library=library,
            expected_digest=expected[workloads[0].workload_id])

    base_orders = balanced_orders(METHODS)
    if config.blocks % len(base_orders):
        raise ValueError("blocks must be a multiple of the balanced schedule")
    orders = base_orders * (config.blocks // len(base_orders))
    rows = []
    total = len(orders) * len(workloads) * len(METHODS)
    completed = 0
    for block, order in enumerate(orders):
        workload_order = list(workloads)
        random.Random(config.seed + block).shuffle(workload_order)
        for workload_position, workload in enumerate(workload_order):
            for method_position, method in enumerate(order):
                if time.perf_counter() - started > config.max_seconds:
                    raise TimeoutError("multi-root experiment exceeded max_seconds")
                row = execute_session(
                    workload=workload, method=method, library=library,
                    expected_digest=expected[workload.workload_id])
                row.update({
                    "block": block,
                    "workload_position": workload_position,
                    "method_position": method_position,
                    "method_order": list(order),
                })
                rows.append(row)
                completed += 1
                if progress:
                    progress("performance", completed, total, workload.workload_id)
    for workload_position, workload in enumerate(workloads):
        for method_position, method in enumerate(METHODS):
            row = execute_session(
                workload=workload, method=method, library=library,
                expected_digest=expected[workload.workload_id],
                role="memory_profile", profile_python_allocations=True)
            row.update({
                "block": None, "workload_position": workload_position,
                "method_position": method_position, "method_order": list(METHODS),
            })
            rows.append(row)

    summary = _summarize(rows, workloads)
    workload_document = {
        "schema": "crse-native-multi-root-workloads/v1",
        "selection_uses_timings": False,
        "workloads": [
            {
                "workload_id": workload.workload_id,
                "family": workload.family,
                "n_vars": workload.n_vars,
                "roots": len(workload.roots),
                "trace_sha256": _digest(workload.trace),
                "union_document": workload.union_document,
                "separate_document_sha256": [
                    _digest(document) for document in workload.separate_documents],
                "sum_separate_nodes": sum(len(document["nodes"])
                                          for document in workload.separate_documents),
                "union_nodes": len(workload.union_document["nodes"]),
                "required_output_sha256": expected[workload.workload_id],
            }
            for workload in workloads
        ],
    }
    result = {
        "schema": SCHEMA,
        "run_id": config.run_id,
        "status": "complete",
        "config": {"seed": config.seed, "blocks": config.blocks,
                   "max_seconds": config.max_seconds},
        "dataset": {
            "classification": "development_generated_sibling_outputs_not_confirmation",
            "workloads": len(workloads), "queries_per_workload": 64,
            "roots_per_workload": 3,
        },
        "native_library": {
            "path": resident_library.relative_to(project_root).as_posix(),
            "sha256": library.sha256, "abi_version": library.abi_version,
            "supports_multi_root": library.supports_multi_root,
        },
        "methods": list(METHODS),
        "correctness": {"canonical_delivery_mismatches": 0,
                        "exact_output_query_checks": len(rows) * 64 * 3},
        "summary": summary,
        "decision": {
            "production_write": False, "production_promotion": False,
            "prospective_data_consumed": False,
            "continue_multi_root": summary["union_ten_percent_gate"],
        },
        "elapsed_seconds": time.perf_counter() - started,
    }
    raw_path = output_dir / "raw_measurements.jsonl"
    with raw_path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False) + "\n")
    _write_json(output_dir / "workloads.json", workload_document)
    _write_json(output_dir / "results.json", result)
    _write_json(output_dir / "environment.json", _environment(project_root))
    _write_text(output_dir / "protocol.md", (
        "# Native multi-root development protocol\n\n"
        "Six genuine three-output Yosys-style arithmetic workloads are fixed before "
        "timing. Separate native root arenas are compared with one union arena across "
        "20 balanced blocks and identical 64-query exact delivery. The native library "
        "is copied into the immutable run. Continue at >=1.10x total gain.\n"
    ))
    totals = summary["aggregate_workload_median_stage_ns"]
    _write_text(output_dir / "report.md", (
        f"# Native multi-root development result\n\n"
        f"Separate roots: {totals['native_separate_roots']['accounted_total_ns'] / 1e6:.3f} ms. "
        f"Union roots: {totals['native_union_roots']['accounted_total_ns'] / 1e6:.3f} ms. "
        f"Speedup: {summary['union_speedup_over_separate']:.4f}x. "
        f"Ten-percent gate: {str(summary['union_ten_percent_gate']).lower()}. "
        "Exact mismatches: 0. Development-only; no production promotion.\n"
    ))
    artifacts = {}
    for name in ("raw_measurements.jsonl", "workloads.json", "results.json",
                 "environment.json", "protocol.md", "report.md", f"native/{library_path.name}"):
        path = output_dir / name
        artifacts[name] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    sources = {}
    for relative in SOURCE_PATHS:
        path = project_root / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        sources[relative] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    _write_json(output_dir / "manifest.json", {
        "schema": "crse-native-multi-root-manifest/v1",
        "run_id": config.run_id,
        "artifacts": artifacts,
        "sources": sources,
    })
    return result
