"""Frozen local profile-first gate for H2 compact keys and H3 dense CM costs.

This is research-only instrumentation.  It calls unchanged production entry points,
retains raw timings/profiles/memory observations, and fails closed on any semantic or
identity disagreement.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
import cProfile
import ctypes
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import pstats
import statistics
import sys
import threading
import time
import tracemalloc
from typing import Any

import numpy as np

from bitset_backend import (
    clear_bitset_env_cache,
    clear_words_env_cache,
    eval_cm_node_flat,
    get_flat_program,
)
from cm_expr_serde import expr_from_json
from cm_ir import (
    clear_cm_ir_alignment_cache,
    clear_cm_ir_compile_cache,
    clear_cm_ir_persistent_cache,
    compile_expr_to_cm_ir,
    materialize_cm,
)
from cm_normalize import canonical_layout, clear_cm_normalize_caches

from .architecture_comparison_campaign import (
    MULTI_SCHEMA,
    _digest,
    _truth_record,
    build_query_trace,
    execute_lane_d,
    resolve_catalog,
)
from .architecture_comparison_freeze import validate_freeze as validate_parent_freeze
from .contracts import canonical_bytes
from .gf2_multi_root_python import compile_python_multi_root_arena
from .ir import cm_dag_signature
from .gf2_wide_repeated_queries import (
    semantic_document as restriction_document,
    semantic_row as restriction_row,
)


SCHEMA = "cm-h2-h3-profile-freeze/v1"
RAW_SCHEMA = "cm-h2-h3-profile-row/v1"
SUMMARY_SCHEMA = "cm-h2-h3-profile-summary/v1"
SOURCE_CHECKPOINT = "c9af2a3c80388e467944bd706036996db9eed9b8"
PARENT_FREEZE = "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json"
PARENT_ORACLES = "docs/recognition/architecture_comparison_execution_retry_20260903/ORACLES.json"
PARENT_FREEZE_CANONICAL_SHA256 = "f00c688efd2d939936d78814794e5638e21bb2352f65863adf5c612b92c99148"
WARMUPS = 2
REPETITIONS = 7
RSS_SAMPLE_INTERVAL_SECONDS = 0.001
COMPONENTS = (
    "key_creation",
    "hashing",
    "interning",
    "serialization",
    "dense_lifting",
    "allocation",
    "conversion",
    "temporary_copies",
)
H2_COMPONENTS = ("key_creation", "hashing", "interning")
H3_COMPONENTS = ("dense_lifting", "allocation", "conversion", "temporary_copies")
SOURCE_CLOSURE = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_ir.py",
    "cm_normalize.py",
    "cmbench/comparative/architecture_comparison_campaign.py",
    "cmbench/comparative/architecture_comparison_freeze.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_multi_root.py",
    "cmbench/comparative/gf2_multi_root_python.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "cmbench/comparative/h2_h3_profile_gate.py",
    PARENT_FREEZE,
    PARENT_ORACLES,
    "docs/research/CM_HARDWARE_BEHAVIOR_CHANGE_CORPUS_RESULT_2026_09_04.md",
    "docs/research/CM_ARCHITECTURE_AUDIT_DISPOSITION_AFTER_C38_2026_09_03.md",
    "docs/research/CM_H2_H3_CURRENT_SOURCE_PROFILE_GATE_PROTOCOL_2026_09_08.md",
)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        stream.write("\n")


def _file_record(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    _require(path.is_file(), f"missing source-closure file: {relative}")
    return {"path": relative, "bytes": path.stat().st_size, "sha256": _sha256(path)}


def _fresh_profile_ids(parent: Mapping[str, Any]) -> list[str]:
    return [
        row["case_id"]
        for row in parent["fresh_corpus"]["single_root_cases"]
        if row["replicate"] == 0 and row["n_vars"] in (8, 14)
    ]


def build_freeze(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    parent_path = root / PARENT_FREEZE
    parent = _load(parent_path)
    # The admitted parent freeze is historically source-bound.  Validate its
    # canonical contents and deterministic corpus here; do not pretend its old
    # source closure is the current checkpoint.
    validate_parent_freeze(parent)
    _require(parent["freeze_sha256"] == PARENT_FREEZE_CANONICAL_SHA256, "parent freeze identity")
    fresh = _fresh_profile_ids(parent)
    observed_a = [
        case_id
        for case_id in parent["observed_regression_bindings"]["public_complete_relation_regression"]["case_ids"]
        if case_id.startswith("controlled_live_") and "-n20-" in case_id
    ]
    observed_b = list(
        parent["observed_regression_bindings"]["repeated_restriction_regression"]["case_ids"]
    )
    lane_c = list(parent["schedules"]["C"]["case_order"])
    lane_d = [
        case_id
        for case_id in parent["schedules"]["D"]["case_order"]
        if case_id == "architecture-refresh-control-k6" or "-k8-" in case_id
    ]
    _require(len(fresh) == 12 and len(observed_a) == 3 and len(observed_b) == 18, "profile panel cardinality")
    _require(len(lane_c) == 12 and len(lane_d) == 3, "control panel cardinality")
    closure = [_file_record(root, relative) for relative in SOURCE_CLOSURE]
    core = {
        "schema": SCHEMA,
        "date": "2026-09-08",
        "status": "frozen_before_decision_bearing_execution",
        "source_checkpoint": SOURCE_CHECKPOINT,
        "fetch_status": "attempted_github_unreachable_local_origin_main_equal_to_head",
        "parent_freeze": {
            "path": PARENT_FREEZE,
            "file_sha256": _sha256(parent_path),
            "canonical_sha256": parent["freeze_sha256"],
        },
        "parent_oracles": {
            "path": PARENT_ORACLES,
            "file_sha256": _sha256(root / PARENT_ORACLES),
        },
        "workload": {
            "selection_blind_to_outputs_and_timings": True,
            "complete_relation": {
                "operation": "current_cm_dense_full_reinflation",
                "case_ids": observed_a + fresh,
                "lifecycles": ["cold", "reused"],
            },
            "repeated_restriction": {
                "operation": "current_cm_ir_bigint",
                "case_ids": observed_b + fresh,
                "query_counts": [1, 64],
                "lifecycles": ["cold", "reused"],
            },
            "related_multi_root": {
                "operations": ["python_sharing_union", "python_sharing_separate"],
                "case_ids": lane_c,
                "query_count": 64,
                "lifecycles": ["cold", "reused"],
            },
            "smaller_query": {
                "case_ids": lane_d,
                "sublanes": [
                    "exact_count", "sat_status", "witness", "partial_context",
                    "version_history", "equivalence_delta", "structural_reload",
                ],
                "arms": ["cm/fresh_engine", "cm/resident_engine"],
                "structural_reload_arm": "cm",
            },
            "refusals_and_unfavorable_cells_retained": True,
        },
        "measurement": {
            "warmups": WARMUPS,
            "repetitions": REPETITIONS,
            "clock": "time.perf_counter_ns",
            "aggregation": "median_of_retained_raw_repetitions",
            "cache_clear_and_gc_outside_timed_span": True,
            "timing_pass": "uninstrumented",
            "profile_pass": "separate_cProfile_exclusive_internal_time",
            "memory_pass": "separate_sampled_current_rss_plus_tracemalloc",
            "rss_sample_interval_seconds": RSS_SAMPLE_INTERVAL_SECONDS,
            "output_cache_allowed": False,
            "component_categories": list(COMPONENTS),
            "component_classification": "exclusive_first_match_rules_in_frozen_instrumentation_source",
            "memory": {
                "baseline": "after_reused_preparation_or_cold_cache_reset_and_gc",
                "peak": "max_current_rss_samples_during_operation_minus_baseline_nonnegative",
                "retained": "current_rss_before_artifact_release_minus_baseline_signed",
                "post_release": "current_rss_after_artifact_release_and_gc_minus_baseline_signed",
                "python_allocations": "tracemalloc_current_and_peak_with_same_boundaries",
            },
        },
        "materiality_gate": {
            "h2_components": list(H2_COMPONENTS),
            "h2_scope": {"workload_classes": ["complete_relation", "repeated_restriction"], "lifecycle": "cold"},
            "h3_components": list(H3_COMPONENTS),
            "h3_scope": {"workload_classes": ["complete_relation"], "lifecycles": ["cold", "reused"]},
            "minimum_exact_cells": 6,
            "aggregate_exclusive_share_min": 0.15,
            "median_cell_share_min": 0.10,
            "median_component_ns_min": 50_000,
            "cell_prevalence_share_floor": 0.10,
            "cell_prevalence_min": 0.50,
            "observed_and_fresh_aggregate_share_min": 0.10,
            "allocation_copy_peak_excess_over_output_min": 0.25,
            "single_candidate_priority": "largest_aggregate_exclusive_share_then_component_name",
        },
        "candidate_gate": {
            "only_one_small_reversible_candidate": True,
            "targeted_end_to_end_geomean_speedup_min": 1.03,
            "targeted_component_speedup_min": 1.05,
            "individual_applicable_speedup_min": 0.95,
            "low_sharing_speedup_min": 0.97,
            "peak_memory_ratio_max": 1.05,
            "retained_memory_ratio_max": 1.05,
            "exact_oracle_mismatches_max": 0,
            "ordering_or_hash_mismatches_max": 0,
        },
        "continuation": {
            "no_material_component": "close_h2_h3_still_deferred",
            "material_component": "test_one_candidate_against_unchanged_current_source",
            "runpod_request": "prepare_only_if_every_local_identity_exactness_stability_memory_performance_replay_and_test_gate_passes",
            "cloud_execution_authorized": False,
            "production_behavior_change_authorized_during_profile": False,
            "h9_work_authorized": False,
            "publication_authorized": False,
        },
        "source_closure": closure,
        "source_closure_sha256": hashlib.sha256(canonical_bytes(closure)).hexdigest(),
    }
    return {**core, "freeze_sha256": hashlib.sha256(canonical_bytes(core)).hexdigest()}


def validate_freeze(freeze: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    _require(freeze.get("schema") == SCHEMA, "freeze schema")
    core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    _require(freeze.get("freeze_sha256") == hashlib.sha256(canonical_bytes(core)).hexdigest(), "freeze digest")
    replay = build_freeze(root)
    _require(canonical_bytes(replay) == canonical_bytes(freeze), "freeze replay")
    return dict(freeze)


def _reset_caches() -> None:
    clear_bitset_env_cache()
    clear_words_env_cache()
    clear_cm_ir_alignment_cache()
    clear_cm_ir_compile_cache()
    clear_cm_ir_persistent_cache()
    clear_cm_normalize_caches()


def _timed(stages: dict[str, int], name: str, function: Callable[[], Any]) -> Any:
    started = time.perf_counter_ns()
    value = function()
    stages[name] = time.perf_counter_ns() - started
    return value


def _node_sha(node: Any) -> str:
    return hashlib.sha256(canonical_bytes(cm_dag_signature(node))).hexdigest()


def _pack_dense(dense: np.ndarray) -> int:
    packed = np.packbits(np.asarray(dense, dtype=np.uint8).reshape(-1), bitorder="little")
    return int.from_bytes(packed.tobytes(), "little")


def _prepare_a(case: Mapping[str, Any]) -> dict[str, Any]:
    expression = expr_from_json(case["expression_v2"])
    node = compile_expr_to_cm_ir(expression, reuse_cache=False, persistent_cache=False, share_aware_flatten=True)
    return {"expression": expression, "node": node, "layout": canonical_layout(list(case["variable_order"]))}


def _run_a(case: Mapping[str, Any], oracle: Mapping[str, Any], state: dict[str, Any] | None, instrument: bool) -> dict[str, Any]:
    stages: dict[str, int] = {}
    diagnostics: dict[str, Any] = {"ir_timing_enabled": 1} if instrument else {}
    if state is None:
        expression = _timed(stages, "parse_normalization", lambda: expr_from_json(case["expression_v2"]))
        node = _timed(stages, "representation_construction", lambda: compile_expr_to_cm_ir(
            expression, diagnostics=diagnostics, reuse_cache=False, persistent_cache=False,
            share_aware_flatten=True,
        ))
        layout = _timed(stages, "binding_layout", lambda: canonical_layout(list(case["variable_order"])))
    else:
        node, layout = state["node"], state["layout"]
        stages.update({"parse_normalization": 0, "representation_construction": 0, "binding_layout": 0})
    dense = _timed(stages, "evaluation_materialization", lambda: materialize_cm(
        node, layout[0], layout[1], fixed=case["fixed"], diagnostics=diagnostics if instrument else None,
    ))
    bits = _timed(stages, "conversion", lambda: _pack_dense(dense))
    record = _timed(stages, "delivery", lambda: _truth_record(bits, case["n_vars"]))
    payload = _timed(stages, "serialization", lambda: canonical_bytes(record))
    _require(record == oracle["truth"], f"complete-relation oracle mismatch: {case['case_id']}")
    return {
        "stages_ns": stages,
        "output_sha256": record["sha256"],
        "output_bytes": record["bytes"],
        "required_artifact_bytes": int(dense.nbytes),
        "ordering_sha256": _digest(list(case["variable_order"])),
        "structure_sha256": _node_sha(node),
        "diagnostics": diagnostics,
        "anchor": (dense, payload, node),
    }


def _prepare_b(case: Mapping[str, Any]) -> dict[str, Any]:
    expression = expr_from_json(case["expression_v2"])
    node = compile_expr_to_cm_ir(expression, reuse_cache=False, persistent_cache=False, share_aware_flatten=True)
    return {"expression": expression, "node": node, "program": get_flat_program(node)}


def _run_b(case: Mapping[str, Any], oracle: Mapping[str, Any], query_count: int, state: dict[str, Any] | None, instrument: bool) -> dict[str, Any]:
    stages: dict[str, int] = {}
    diagnostics: dict[str, Any] = {"ir_timing_enabled": 1} if instrument else {}
    if state is None:
        expression = _timed(stages, "parse_normalization", lambda: expr_from_json(case["expression_v2"]))
        node = _timed(stages, "representation_construction", lambda: compile_expr_to_cm_ir(
            expression, diagnostics=diagnostics, reuse_cache=False, persistent_cache=False,
            share_aware_flatten=True,
        ))
        _timed(stages, "compilation", lambda: get_flat_program(node))
    else:
        node = state["node"]
        stages.update({"parse_normalization": 0, "representation_construction": 0, "compilation": 0})
    trace = case["c36_trace"][:query_count]
    query_inputs = _timed(stages, "binding", lambda: [
        ({item["variable"]: item["value"] for item in query["fixed"]}, tuple(query["remaining_order"]))
        for query in trace
    ])
    outputs = _timed(stages, "evaluation", lambda: tuple(
        int(eval_cm_node_flat(node, remaining, fixed=fixed)) for fixed, remaining in query_inputs
    ))
    document = _timed(stages, "delivery", lambda: restriction_document(
        case["case_id"],
        [restriction_row(query, output, case["n_vars"]) for query, output in zip(trace, outputs, strict=True)],
    ))
    actual = _digest(document)
    _require(actual == oracle["checkpoints"][str(query_count)], f"restriction oracle mismatch: {case['case_id']} q{query_count}")
    payload = _timed(stages, "serialization", lambda: canonical_bytes(document))
    return {
        "stages_ns": stages,
        "output_sha256": actual,
        "output_bytes": len(payload),
        "required_artifact_bytes": len(payload),
        "ordering_sha256": _digest([query["remaining_order"] for query in trace]),
        "structure_sha256": _node_sha(node),
        "diagnostics": diagnostics,
        "anchor": (outputs, document, payload, node),
    }


def _prepare_c(workload: Any, operation: str) -> dict[str, Any]:
    documents = (workload.union_document, workload.separate_documents)
    if operation == "python_sharing_union":
        arenas = (compile_python_multi_root_arena(documents[0], variable_count=workload.n_vars),)
    else:
        arenas = tuple(compile_python_multi_root_arena(document, variable_count=workload.n_vars) for document in documents[1])
    trace = build_query_trace(workload.workload_id, workload.n_vars)
    inputs = [
        ({item["variable"]: item["value"] for item in query["fixed"]}, tuple(query["remaining_order"]))
        for query in trace
    ]
    return {"documents": documents, "arenas": arenas, "trace": trace, "inputs": inputs}


def _run_c(workload: Any, oracle: Mapping[str, Any], operation: str, state: dict[str, Any] | None, instrument: bool) -> dict[str, Any]:
    _ = instrument
    stages: dict[str, int] = {}
    if state is None:
        documents = _timed(stages, "parse_normalization", lambda: (workload.union_document, workload.separate_documents))
        if operation == "python_sharing_union":
            arenas = _timed(stages, "representation_construction", lambda: (
                compile_python_multi_root_arena(documents[0], variable_count=workload.n_vars),
            ))
        else:
            arenas = _timed(stages, "representation_construction", lambda: tuple(
                compile_python_multi_root_arena(document, variable_count=workload.n_vars) for document in documents[1]
            ))
        trace = build_query_trace(workload.workload_id, workload.n_vars)
        inputs = _timed(stages, "binding", lambda: [
            ({item["variable"]: item["value"] for item in query["fixed"]}, tuple(query["remaining_order"]))
            for query in trace
        ])
    else:
        documents, arenas, trace, inputs = state["documents"], state["arenas"], state["trace"], state["inputs"]
        stages.update({"parse_normalization": 0, "representation_construction": 0, "binding": 0})
    def evaluate() -> tuple[tuple[int, ...], ...]:
        if operation == "python_sharing_union":
            return tuple(arenas[0].evaluate(fixed, remaining) for fixed, remaining in inputs)
        return tuple(tuple(arena.evaluate(fixed, remaining)[0] for arena in arenas) for fixed, remaining in inputs)
    values = _timed(stages, "evaluation", evaluate)
    document = _timed(stages, "delivery", lambda: {
        "schema": MULTI_SCHEMA,
        "workload_id": workload.workload_id,
        "rows": [
            {
                "query": query["query"],
                "query_sha256": query["query_sha256"],
                "outputs": [
                    {"output_index": index, "semantic": restriction_row(query, int(value), workload.n_vars)}
                    for index, value in enumerate(outputs)
                ],
            }
            for query, outputs in zip(trace, values, strict=True)
        ],
    })
    actual = _digest(document)
    _require(actual == oracle["output_sha256"], f"multi-root oracle mismatch: {workload.workload_id}")
    payload = _timed(stages, "serialization", lambda: canonical_bytes(document))
    return {
        "stages_ns": stages,
        "output_sha256": actual,
        "output_bytes": len(payload),
        "required_artifact_bytes": len(payload),
        "ordering_sha256": _digest(list(range(len(workload.roots)))),
        "structure_sha256": _digest({
            "union": documents[0], "separate": list(documents[1]), "operation": operation,
        }),
        "diagnostics": {},
        "anchor": (arenas, values, document, payload),
    }


def _run_d(catalog: Mapping[str, Any], oracles: Mapping[str, Any], case_id: str, sublane: str, arm: str) -> dict[str, Any]:
    row = execute_lane_d(catalog["D"][case_id], sublane, arm, oracles["lanes"]["D"][case_id])
    _require(row["status"] == "ok" and row["exact_check_passed"], f"smaller-query exactness: {case_id} {sublane} {arm}")
    return {
        "stages_ns": {"task_total": int(row["timings_ns"]["accounted_total_ns"])},
        "output_sha256": row["output_sha256"],
        "output_bytes": int(row["output_bytes"]),
        "required_artifact_bytes": int(row["output_bytes"]),
        "ordering_sha256": _digest({"case_id": case_id, "sublane": sublane, "arm": arm}),
        "structure_sha256": row["output_sha256"],
        "diagnostics": {},
        "anchor": row,
    }


def _profile_category(filename: str, name: str) -> str | None:
    path = filename.replace("\\", "/").lower()
    lname = name.lower()
    if lname in {"__hash__", "_structural_digest", "_persistent_digest", "hash"} or "builtins.hash" in lname:
        return "hashing"
    if lname == "_intern":
        return "interning"
    if "cm_ir.py" in path and lname in {
        "_canonicalize_commutative_args", "make_and", "make_or", "make_xor",
        "make_eqv", "make_imp", "negate", "const", "var", "_node_uid",
    }:
        return "key_creation"
    if "json/" in path or lname in {"canonical_bytes", "expr_to_json_dag", "encode", "iterencode"}:
        return "serialization"
    if lname in {"align_to_vars", "align_to_vars_with_stats", "lift_cm", "_permute_bits_rows", "_permute_bits_cols", "_alignment_plan"}:
        return "dense_lifting"
    if lname in {"copy", "_serial_combine", "combine_pointwise", "copyto"} or "'copy'" in lname or "copyto" in lname:
        return "temporary_copies"
    if lname in {
        "_pack_dense", "bitset_to_bool_array", "bitset_to_bool_hypercube", "packbits",
        "unpackbits", "astype", "asarray", "tobytes", "from_bytes", "to_bytes",
    } or any(f"'{item}'" in lname for item in ("astype", "tobytes", "from_bytes", "to_bytes")):
        return "conversion"
    if lname in {
        "array", "empty", "zeros", "ones", "full", "arange", "empty_like",
        "zeros_like", "ones_like", "broadcast_to", "expand_dims",
    }:
        return "allocation"
    return None


def _profile_once(function: Callable[[], dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    profiler = cProfile.Profile()
    profiler.enable()
    result = function()
    profiler.disable()
    stats = pstats.Stats(profiler).stats
    components = {name: 0 for name in COMPONENTS}
    top: list[dict[str, Any]] = []
    accounted = 0
    for (filename, line, name), (_cc, _nc, internal, cumulative, _callers) in stats.items():
        internal_ns = max(0, round(internal * 1_000_000_000))
        accounted += internal_ns
        category = _profile_category(filename, name)
        if category is not None:
            components[category] += internal_ns
        top.append({
            "file": Path(filename).name, "line": int(line), "function": name,
            "internal_ns": internal_ns, "cumulative_ns": max(0, round(cumulative * 1_000_000_000)),
            "category": category,
        })
    top.sort(key=lambda row: (-row["internal_ns"], row["file"], row["line"], row["function"]))
    mapped = sum(components.values())
    return result, {
        "exclusive_self_ns": components,
        "accounted_self_ns": accounted,
        "mapped_self_ns": mapped,
        "unmapped_self_ns": max(0, accounted - mapped),
        "top_internal_functions": top[:20],
    }


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
    ]


if os.name == "nt":
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _psapi = ctypes.WinDLL("psapi", use_last_error=True)
    # ctypes otherwise assumes a 32-bit int return and truncates the pseudo
    # handle on 64-bit Windows, making GetProcessMemoryInfo fail with ERROR_INVALID_HANDLE.
    _kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    _psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(_ProcessMemoryCounters), ctypes.c_ulong,
    ]
    _psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    _current_process_handle = _kernel32.GetCurrentProcess()
else:
    _psapi = None
    _current_process_handle = None


def _current_rss() -> int | None:
    if os.name == "nt":
        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        ok = _psapi.GetProcessMemoryInfo(_current_process_handle, ctypes.byref(counters), counters.cb)
        return int(counters.WorkingSetSize) if ok else None
    statm = Path("/proc/self/statm")
    if statm.is_file():
        resident_pages = int(statm.read_text(encoding="ascii").split()[1])
        return resident_pages * os.sysconf("SC_PAGE_SIZE")
    return None


class _RssSampler:
    def __init__(self) -> None:
        self.samples: list[int] = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop.is_set():
            value = _current_rss()
            if value is not None:
                self.samples.append(value)
            self.stop.wait(RSS_SAMPLE_INTERVAL_SECONDS)

    def __enter__(self) -> "_RssSampler":
        self.thread.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self.stop.set()
        self.thread.join(timeout=1.0)
        value = _current_rss()
        if value is not None:
            self.samples.append(value)


def _memory_once(function: Callable[[], dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    gc.collect()
    baseline_rss = _current_rss()
    tracemalloc.start()
    traced_baseline, _ = tracemalloc.get_traced_memory()
    with _RssSampler() as sampler:
        result = function()
    retained_rss = _current_rss()
    traced_retained, traced_peak = tracemalloc.get_traced_memory()
    sample_count = len(sampler.samples)
    sampled_peak = max(sampler.samples) if sampler.samples else retained_rss
    anchor = result.pop("anchor", None)
    del anchor
    gc.collect()
    post_release_rss = _current_rss()
    traced_post_release, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, {
        "rss_available": baseline_rss is not None and retained_rss is not None and sampled_peak is not None,
        "rss_baseline_bytes": baseline_rss,
        "rss_sampled_peak_bytes": sampled_peak,
        "rss_retained_bytes": retained_rss,
        "rss_post_release_bytes": post_release_rss,
        "rss_incremental_peak_bytes": None if baseline_rss is None or sampled_peak is None else max(0, sampled_peak - baseline_rss),
        "rss_retained_delta_bytes": None if baseline_rss is None or retained_rss is None else retained_rss - baseline_rss,
        "rss_post_release_delta_bytes": None if baseline_rss is None or post_release_rss is None else post_release_rss - baseline_rss,
        "rss_sample_count": sample_count,
        "rss_sampler_interval_seconds": RSS_SAMPLE_INTERVAL_SECONDS,
        "rss_sampler_stopped": not sampler.thread.is_alive(),
        "tracemalloc_baseline_bytes": traced_baseline,
        "tracemalloc_peak_bytes": traced_peak,
        "tracemalloc_retained_bytes": traced_retained,
        "tracemalloc_post_release_bytes": traced_post_release,
        "tracemalloc_incremental_peak_bytes": max(0, traced_peak - traced_baseline),
        "tracemalloc_retained_delta_bytes": traced_retained - traced_baseline,
        "tracemalloc_post_release_delta_bytes": traced_post_release - traced_baseline,
    }


def _measure_row(
    *, row_id: str, workload_class: str, cohort: str, case_id: str, operation: str,
    lifecycle: str, query_count: int | None, run_once: Callable[[dict[str, Any] | None, bool], dict[str, Any]],
    prepare_reused: Callable[[], dict[str, Any]] | None, hypothesis_scope: Sequence[str], low_sharing_control: bool,
) -> dict[str, Any]:
    def new_state() -> dict[str, Any] | None:
        if lifecycle == "cold":
            return None
        if prepare_reused is None:
            return None
        _reset_caches()
        gc.collect()
        return prepare_reused()

    state = new_state()
    for _ in range(WARMUPS):
        if lifecycle == "cold":
            _reset_caches()
            gc.collect()
        warm = run_once(state, False)
        del warm
    trials = []
    identities: set[tuple[str, str, str]] = set()
    for _ in range(REPETITIONS):
        if lifecycle == "cold":
            _reset_caches()
            gc.collect()
        result = run_once(state, False)
        stages = {key: int(value) for key, value in result["stages_ns"].items()}
        trials.append({"stages_ns": stages, "accounted_total_ns": sum(stages.values())})
        identities.add((result["output_sha256"], result["ordering_sha256"], result["structure_sha256"]))
        del result
    profile_state = new_state()
    for _ in range(WARMUPS if lifecycle != "cold" else 0):
        warm = run_once(profile_state, False)
        del warm
    if lifecycle == "cold":
        _reset_caches()
        gc.collect()
    profile_result, profile = _profile_once(lambda: run_once(profile_state, True))
    identities.add((profile_result["output_sha256"], profile_result["ordering_sha256"], profile_result["structure_sha256"]))
    diagnostics = profile_result["diagnostics"]
    del profile_result
    memory_state = new_state()
    for _ in range(WARMUPS if lifecycle != "cold" else 0):
        warm = run_once(memory_state, False)
        del warm
    if lifecycle == "cold":
        _reset_caches()
    memory_result, memory = _memory_once(lambda: run_once(memory_state, False))
    identities.add((memory_result["output_sha256"], memory_result["ordering_sha256"], memory_result["structure_sha256"]))
    output_sha, ordering_sha, structure_sha = sorted(identities)[0]
    exact_stable = len(identities) == 1
    stage_names = sorted({name for trial in trials for name in trial["stages_ns"]})
    medians = {
        name: round(statistics.median(trial["stages_ns"].get(name, 0) for trial in trials))
        for name in stage_names
    }
    total_median = round(statistics.median(trial["accounted_total_ns"] for trial in trials))
    component_shares = {
        name: (profile["exclusive_self_ns"][name] / profile["accounted_self_ns"] if profile["accounted_self_ns"] else 0.0)
        for name in COMPONENTS
    }
    return {
        "schema": RAW_SCHEMA,
        "row_id": row_id,
        "workload_class": workload_class,
        "cohort": cohort,
        "case_id": case_id,
        "operation": operation,
        "lifecycle": lifecycle,
        "query_count": query_count,
        "hypothesis_scope": list(hypothesis_scope),
        "low_sharing_control": low_sharing_control,
        "status": "ok" if exact_stable else "mismatch",
        "exact_oracle_agreement": True,
        "stable_output_order_and_hashes": exact_stable,
        "output_sha256": output_sha,
        "ordering_sha256": ordering_sha,
        "structure_sha256": structure_sha,
        "output_bytes": int(memory_result["output_bytes"]),
        "required_artifact_bytes": int(memory_result["required_artifact_bytes"]),
        "raw_timing_trials": trials,
        "median_stages_ns": medians,
        "median_accounted_total_ns": total_median,
        "profile": {**profile, "exclusive_share": component_shares},
        "memory": memory,
        "instrumentation_diagnostics": diagnostics,
    }


def _cohort(case_id: str) -> str:
    return "fresh" if case_id.startswith(("fresh-", "history-fresh-")) else "observed"


def run_profile(project_root: str | Path, freeze: Mapping[str, Any], raw_path: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    validate_freeze(freeze, root)
    parent = _load(root / freeze["parent_freeze"]["path"])
    oracles = _load(root / freeze["parent_oracles"]["path"])
    # Rebuild/validate the independent oracles only after the profile freeze exists.
    from .architecture_comparison_campaign import validate_oracles
    validate_oracles(oracles, root, parent)
    catalog = resolve_catalog(root, parent)
    output = Path(raw_path).resolve()
    _require(output.is_relative_to(root) and not output.exists(), "new in-project raw output required")
    output.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        def emit(row: dict[str, Any]) -> None:
            nonlocal rows_written
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
            stream.flush()
            rows_written += 1

        for case_id in freeze["workload"]["complete_relation"]["case_ids"]:
            case, oracle = catalog["A"][case_id], oracles["lanes"]["A"][case_id]
            _require(oracle["status"] == "runnable", f"frozen complete case refused: {case_id}")
            for lifecycle in ("cold", "reused"):
                emit(_measure_row(
                    row_id=f"A:{case_id}:{lifecycle}", workload_class="complete_relation", cohort=_cohort(case_id),
                    case_id=case_id, operation="current_cm_dense_full_reinflation", lifecycle=lifecycle,
                    query_count=1, run_once=lambda state, instrument, c=case, o=oracle: _run_a(c, o, state, instrument),
                    prepare_reused=lambda c=case: _prepare_a(c), hypothesis_scope=("H2", "H3") if lifecycle == "cold" else ("H3",),
                    low_sharing_control=(case_id.startswith("controlled_live_") or "fresh-tree-" in case_id),
                ))

        for case_id in freeze["workload"]["repeated_restriction"]["case_ids"]:
            case, oracle = catalog["B"][case_id], oracles["lanes"]["B"][case_id]
            for query_count in (1, 64):
                for lifecycle in ("cold", "reused"):
                    emit(_measure_row(
                        row_id=f"B:{case_id}:q{query_count}:{lifecycle}", workload_class="repeated_restriction",
                        cohort=_cohort(case_id), case_id=case_id, operation="current_cm_ir_bigint",
                        lifecycle=lifecycle, query_count=query_count,
                        run_once=lambda state, instrument, c=case, o=oracle, q=query_count: _run_b(c, o, q, state, instrument),
                        prepare_reused=lambda c=case: _prepare_b(c), hypothesis_scope=("H2",) if lifecycle == "cold" else (),
                        low_sharing_control=("fresh-tree-" in case_id),
                    ))

        for case_id in freeze["workload"]["related_multi_root"]["case_ids"]:
            workload, oracle = catalog["C"][case_id], oracles["lanes"]["C"][case_id]
            for operation in freeze["workload"]["related_multi_root"]["operations"]:
                for lifecycle in ("cold", "reused"):
                    emit(_measure_row(
                        row_id=f"C:{case_id}:{operation}:{lifecycle}", workload_class="related_multi_root",
                        cohort=_cohort(case_id), case_id=case_id, operation=operation, lifecycle=lifecycle,
                        query_count=64,
                        run_once=lambda state, instrument, w=workload, o=oracle, op=operation: _run_c(w, o, op, state, instrument),
                        prepare_reused=lambda w=workload, op=operation: _prepare_c(w, op), hypothesis_scope=(),
                        low_sharing_control=(operation == "python_sharing_separate"),
                    ))

        for case_id in freeze["workload"]["smaller_query"]["case_ids"]:
            for sublane in freeze["workload"]["smaller_query"]["sublanes"]:
                arms = ["cm"] if sublane == "structural_reload" else freeze["workload"]["smaller_query"]["arms"]
                for arm in arms:
                    lifecycle = "serialized_reload" if sublane == "structural_reload" else arm.split("/", 1)[1]
                    emit(_measure_row(
                        row_id=f"D:{case_id}:{sublane}:{arm}", workload_class="smaller_query",
                        cohort=_cohort(case_id), case_id=case_id, operation=sublane, lifecycle=lifecycle,
                        query_count=None,
                        run_once=lambda _state, _instrument, c=case_id, s=sublane, a=arm: _run_d(catalog, oracles, c, s, a),
                        prepare_reused=(lambda: {}) if lifecycle != "fresh_engine" else None,
                        hypothesis_scope=(), low_sharing_control=True,
                    ))
    return {"rows_written": rows_written, "raw_sha256": _sha256(output)}


def _geomean(values: Sequence[float]) -> float:
    _require(values and all(value > 0 for value in values), "positive geomean values")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def _materiality(rows: Sequence[Mapping[str, Any]], freeze: Mapping[str, Any], hypothesis: str, component: str) -> dict[str, Any]:
    if hypothesis == "H2":
        applicable = [row for row in rows if hypothesis in row["hypothesis_scope"]]
    else:
        applicable = [row for row in rows if hypothesis in row["hypothesis_scope"]]
    exact = [row for row in applicable if row["status"] == "ok" and row["exact_oracle_agreement"] and row["stable_output_order_and_hashes"]]
    component_ns = [int(row["profile"]["exclusive_self_ns"][component]) for row in exact]
    total_ns = [int(row["profile"]["accounted_self_ns"]) for row in exact]
    shares = [part / total if total else 0.0 for part, total in zip(component_ns, total_ns, strict=True)]
    gate = freeze["materiality_gate"]
    cohort_shares: dict[str, float] = {}
    for cohort in ("observed", "fresh"):
        selected = [(part, total) for row, part, total in zip(exact, component_ns, total_ns, strict=True) if row["cohort"] == cohort]
        if selected:
            cohort_shares[cohort] = sum(part for part, _ in selected) / sum(total for _, total in selected)
    peak_excess = []
    for row in exact:
        peak = max(
            int(row["memory"].get("rss_incremental_peak_bytes") or 0),
            int(row["memory"].get("tracemalloc_incremental_peak_bytes") or 0),
        )
        required = int(row["required_artifact_bytes"])
        peak_excess.append(max(0.0, (peak - required) / max(1, required)))
    conditions = {
        "minimum_exact_cells": len(exact) >= gate["minimum_exact_cells"],
        "aggregate_exclusive_share": bool(total_ns) and sum(component_ns) / sum(total_ns) >= gate["aggregate_exclusive_share_min"],
        "median_cell_share": bool(shares) and statistics.median(shares) >= gate["median_cell_share_min"],
        "median_component_ns": bool(component_ns) and statistics.median(component_ns) >= gate["median_component_ns_min"],
        "cell_prevalence": bool(shares) and sum(value >= gate["cell_prevalence_share_floor"] for value in shares) / len(shares) >= gate["cell_prevalence_min"],
        "observed_and_fresh_floor": all(value >= gate["observed_and_fresh_aggregate_share_min"] for value in cohort_shares.values()) and set(cohort_shares) == {"observed", "fresh"},
        "allocation_copy_peak_excess": component not in {"allocation", "temporary_copies"} or (bool(peak_excess) and statistics.median(peak_excess) >= gate["allocation_copy_peak_excess_over_output_min"]),
    }
    return {
        "hypothesis": hypothesis,
        "component": component,
        "applicable_cells": len(applicable),
        "exact_cells": len(exact),
        "aggregate_exclusive_share": (sum(component_ns) / sum(total_ns) if total_ns and sum(total_ns) else 0.0),
        "median_cell_share": (statistics.median(shares) if shares else 0.0),
        "median_component_ns": (statistics.median(component_ns) if component_ns else 0.0),
        "cell_prevalence": (sum(value >= gate["cell_prevalence_share_floor"] for value in shares) / len(shares) if shares else 0.0),
        "cohort_aggregate_shares": cohort_shares,
        "median_peak_excess_over_output": (statistics.median(peak_excess) if peak_excess else 0.0),
        "conditions": conditions,
        "passes": all(conditions.values()),
    }


def summarize(raw_path: str | Path, freeze: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(raw_path).resolve()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    expected = (
        len(freeze["workload"]["complete_relation"]["case_ids"]) * 2
        + len(freeze["workload"]["repeated_restriction"]["case_ids"]) * 2 * 2
        + len(freeze["workload"]["related_multi_root"]["case_ids"]) * 2 * 2
        + len(freeze["workload"]["smaller_query"]["case_ids"])
        * (6 * 2 + 1)
    )
    _require(len(rows) == expected, f"raw row cardinality: {len(rows)} != {expected}")
    _require(len({row["row_id"] for row in rows}) == len(rows), "duplicate raw row")
    exact_failures = [row["row_id"] for row in rows if row["status"] != "ok" or not row["exact_oracle_agreement"]]
    stability_failures = [row["row_id"] for row in rows if not row["stable_output_order_and_hashes"]]
    memory_failures = [
        row["row_id"] for row in rows
        if not row["memory"]["rss_available"]
        or not row["memory"]["rss_sampler_stopped"]
        or row["memory"]["rss_sample_count"] < 1
    ]
    decisions = [
        *[_materiality(rows, freeze, "H2", component) for component in H2_COMPONENTS],
        *[_materiality(rows, freeze, "H3", component) for component in H3_COMPONENTS],
    ]
    passing = sorted(
        [row for row in decisions if row["passes"]],
        key=lambda row: (-row["aggregate_exclusive_share"], row["component"]),
    )
    local_prerequisites = not exact_failures and not stability_failures and not memory_failures
    if not local_prerequisites:
        decision = "stop_local_validity_failure"
    elif not passing:
        decision = "no_go_close_h2_h3_still_deferred"
    else:
        decision = "material_component_requires_one_local_reversible_candidate"
    core = {
        "schema": SUMMARY_SCHEMA,
        "freeze_sha256": freeze["freeze_sha256"],
        "raw_measurements_sha256": _sha256(path),
        "rows": len(rows),
        "rows_by_workload": dict(sorted((key, sum(row["workload_class"] == key for row in rows)) for key in {row["workload_class"] for row in rows})),
        "exact_failures": exact_failures,
        "stability_failures": stability_failures,
        "memory_accounting_failures": memory_failures,
        "materiality": decisions,
        "qualifying_components": [{"hypothesis": row["hypothesis"], "component": row["component"], "aggregate_exclusive_share": row["aggregate_exclusive_share"]} for row in passing],
        "selected_candidate_component": (passing[0]["component"] if passing else None),
        "decision": decision,
        "candidate_implemented": False,
        "runpod_authorization_request_permitted": False,
        "environment": {
            "python": sys.version,
            "executable": sys.executable,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
    }
    return {**core, "summary_sha256": hashlib.sha256(canonical_bytes(core)).hexdigest()}


def freeze_to_path(project_root: str | Path, output_path: str | Path) -> dict[str, Any]:
    freeze = build_freeze(project_root)
    _write_new(Path(output_path), freeze)
    return freeze


def summary_to_path(raw_path: str | Path, freeze_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    freeze = _load(Path(freeze_path))
    summary = summarize(raw_path, freeze)
    _write_new(Path(output_path), summary)
    return summary
