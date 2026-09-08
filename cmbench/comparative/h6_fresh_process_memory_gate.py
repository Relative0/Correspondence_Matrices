"""Fresh-process H6 memory calibration for unchanged exact CM backends.

The measured worker and the external controller use a line-delimited handshake so
process startup and imports are outside task-incremental memory.  This module is
research-only and never changes production routing.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
import ctypes
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import queue
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc
from typing import Any

from bitset_backend import build_bitset_env
from cm_expr_serde import expr_from_json

from . import architecture_comparison_campaign as parent
from .architecture_comparison_freeze import validate_freeze as validate_parent_freeze
from .contracts import canonical_bytes
from .gf2_native_slots import NativeSlotLibrary, load_native_slot_library
from . import h2_h3_profile_gate as profile


SCHEMA = "cm-h6-fresh-process-memory-freeze/v1"
RAW_SCHEMA = "cm-h6-fresh-process-memory-row/v1"
SUMMARY_SCHEMA = "cm-h6-fresh-process-memory-summary/v1"
SOURCE_CHECKPOINT = "c9af2a3c80388e467944bd706036996db9eed9b8"
PARENT_FREEZE = "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json"
PARENT_ORACLES = "docs/recognition/architecture_comparison_execution_retry_20260903/ORACLES.json"
NATIVE_LIBRARY = "docs/recognition/c37_native_exact_confirmation/frozen_native_v3/cm_fused_slots.dll"
PROTOCOL = "docs/research/CM_H6_FRESH_PROCESS_MEMORY_CALIBRATION_PROTOCOL_2026_09_08.md"
REPLICATES = 3
SAMPLE_INTERVAL_SECONDS = 0.001
QUERY_COUNTS = (1, 64)
LIFECYCLES = ("cold", "reused")
A_ARMS = ("cm_dense_full_reinflation", "direct_expression_bitset")
B_ARMS = (
    "r2_topological_liveness",
    "cm_ir_bigint",
    "cse_flat_bigint",
    "native_fused_slots",
)
C_ARMS = ("python_sharing_union", "python_sharing_separate")
OBSERVED_B_PREFIXES = (
    "c36-decoder_index-",
    "c36-decoder_reverse_shift-",
    "c36-multiply_low_cone-",
    "c36-addertree_sum-",
    "c36-multiply_add_low_cone-",
)
FRESH_CASE_IDS = (
    "fresh-tree-andor-k8-r0",
    "fresh-high-sharing-andor-k14-r0",
    "fresh-tree-xor-eqv-k14-r0",
    "fresh-high-sharing-xor-eqv-k8-r0",
    "fresh-tree-mixed-k8-r0",
    "fresh-high-sharing-mixed-k14-r0",
)
SOURCE_CLOSURE = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cm_normalize.py",
    "cmbench/backends/native_restriction.py",
    "cmbench/comparative/architecture_comparison_campaign.py",
    "cmbench/comparative/architecture_comparison_freeze.py",
    "cmbench/comparative/architecture_refresh_harness.py",
    "cmbench/comparative/arms.py",
    "cmbench/comparative/comparison_prefreeze.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_multi_root.py",
    "cmbench/comparative/gf2_multi_root_python.py",
    "cmbench/comparative/gf2_native_slots.py",
    "cmbench/comparative/gf2_restricted_evaluators.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "cmbench/comparative/h2_h3_profile_gate.py",
    "cmbench/comparative/h6_fresh_process_memory_gate.py",
    "cmbench/comparative/persistence.py",
    "cmbench/comparative/tasks.py",
    "native/cm_fused_slots/fused_slot_executor.c",
    "scripts/cm_h6_fresh_process_memory_gate.py",
    "scripts/crse_verify_h6_fresh_process_memory_gate.py",
    PARENT_FREEZE,
    PARENT_ORACLES,
    NATIVE_LIBRARY,
    PROTOCOL,
    "docs/research/CM_ARCHITECTURE_AUDIT_DISPOSITION_AFTER_C38_2026_09_03.md",
    "docs/research/CM_HARDWARE_BEHAVIOR_CHANGE_CORPUS_RESULT_2026_09_04.md",
    "docs/research/CM_H2_H3_CURRENT_SOURCE_PROFILE_GATE_RESULT_2026_09_08.md",
)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


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
    path = (root / relative).resolve()
    _require(path.is_relative_to(root) and path.is_file(), f"missing H6 source: {relative}")
    return {"path": relative, "bytes": path.stat().st_size, "sha256": _sha256(path)}


def _fresh_profile_ids(parent_freeze: Mapping[str, Any]) -> list[str]:
    available = {
        row["case_id"] for row in parent_freeze["fresh_corpus"]["single_root_cases"]
    }
    _require(set(FRESH_CASE_IDS).issubset(available), "missing balanced fresh H6 cases")
    return list(FRESH_CASE_IDS)


def _first_prefixed(case_ids: Sequence[str], prefix: str) -> str:
    selected = [case_id for case_id in case_ids if case_id.startswith(prefix)]
    _require(bool(selected), f"missing observed family: {prefix}")
    return selected[0]


def _case_selections(parent_freeze: Mapping[str, Any]) -> dict[str, list[str]]:
    fresh = _fresh_profile_ids(parent_freeze)
    observed_a = [
        case_id
        for case_id in parent_freeze["observed_regression_bindings"][
            "public_complete_relation_regression"
        ]["case_ids"]
        if case_id.startswith("controlled_live_") and "-n20-" in case_id
    ]
    observed_b_all = list(
        parent_freeze["observed_regression_bindings"]["repeated_restriction_regression"][
            "case_ids"
        ]
    )
    observed_b = [_first_prefixed(observed_b_all, prefix) for prefix in OBSERVED_B_PREFIXES]
    lane_c_all = list(parent_freeze["schedules"]["C"]["case_order"])
    lane_c = (
        [case_id for case_id in lane_c_all if case_id.startswith("c37-")][:3]
        + [case_id for case_id in lane_c_all if case_id.startswith("fresh-")][:3]
    )
    _require(len(fresh) == 6 and len(observed_a) == 3, "H6 single-root selection")
    _require(len(observed_b) == 5 and len(set(observed_b)) == 5, "H6 observed family selection")
    _require(len(lane_c) == 6 and len(set(lane_c)) == 6, "H6 multi-root selection")
    return {"A": observed_a + fresh, "B": observed_b + fresh, "C": lane_c}


def expected_schedule_rows(freeze: Mapping[str, Any]):
    workload = freeze["workload"]
    for lane, arms in (("A", A_ARMS), ("B", B_ARMS), ("C", C_ARMS)):
        counts = QUERY_COUNTS if lane == "B" else ((1,) if lane == "A" else (64,))
        for case_id in workload[lane]["case_ids"]:
            for query_count in counts:
                for arm in arms:
                    for lifecycle in LIFECYCLES:
                        for replicate in range(REPLICATES):
                            yield {
                                "row_id": f"{lane}:{case_id}:q{query_count}:{arm}:{lifecycle}:r{replicate}",
                                "logical_id": f"{lane}:{case_id}:q{query_count}:{arm}:{lifecycle}",
                                "lane": lane,
                                "case_id": case_id,
                                "query_count": query_count,
                                "arm": arm,
                                "lifecycle": lifecycle,
                                "replicate": replicate,
                                "cohort": "fresh" if case_id.startswith("fresh-") else "observed",
                            }


def build_freeze(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    parent_path = root / PARENT_FREEZE
    parent_freeze = _load(parent_path)
    validate_parent_freeze(parent_freeze)
    selections = _case_selections(parent_freeze)
    catalog = parent.resolve_catalog(root, parent_freeze)
    oracles = _load(root / PARENT_ORACLES)
    _validate_stored_oracles(oracles, parent_freeze)
    payloads = {
        "catalog": {
            "A": {case_id: catalog["A"][case_id] for case_id in selections["A"]},
            "B": {case_id: catalog["B"][case_id] for case_id in selections["B"]},
            "C": {
                case_id: {
                    "workload_id": catalog["C"][case_id].workload_id,
                    "family": catalog["C"][case_id].family,
                    "n_vars": catalog["C"][case_id].n_vars,
                    "separate_documents": list(catalog["C"][case_id].separate_documents),
                }
                for case_id in selections["C"]
            },
        },
        "oracles": {
            "lanes": {
                lane: {case_id: oracles["lanes"][lane][case_id] for case_id in selections[lane]}
                for lane in ("A", "B", "C")
            }
        },
    }
    closure = [_file_record(root, relative) for relative in SOURCE_CLOSURE]
    core = {
        "schema": SCHEMA,
        "date": "2026-09-08",
        "status": "frozen_before_decision_bearing_execution",
        "source_checkpoint": SOURCE_CHECKPOINT,
        "fetch_status": "verified_origin_main_equal_to_head",
        "scope": "H6_fresh_process_memory_calibration_only",
        "parent_freeze": {
            "path": PARENT_FREEZE,
            "bytes": parent_path.stat().st_size,
            "sha256": _sha256(parent_path),
            "canonical_sha256": parent_freeze["freeze_sha256"],
        },
        "parent_oracles": {
            "path": PARENT_ORACLES,
            "bytes": (root / PARENT_ORACLES).stat().st_size,
            "sha256": _sha256(root / PARENT_ORACLES),
        },
        "native_library": {
            "path": NATIVE_LIBRARY,
            "bytes": (root / NATIVE_LIBRARY).stat().st_size,
            "sha256": _sha256(root / NATIVE_LIBRARY),
            "activation": "existing_opt_in_exact_control_only",
        },
        "workload": {
            "selection_blind_to_memory_results": True,
            "A": {"case_ids": selections["A"], "arms": list(A_ARMS), "query_counts": [1]},
            "B": {"case_ids": selections["B"], "arms": list(B_ARMS), "query_counts": list(QUERY_COUNTS)},
            "C": {"case_ids": selections["C"], "arms": list(C_ARMS), "query_counts": [64]},
            "lifecycles": list(LIFECYCLES),
            "replicates": REPLICATES,
            "all_failures_zeroes_and_unfavorable_rows_retained": True,
        },
        "frozen_payloads": payloads,
        "measurement": {
            "process_creation": "subprocess.Popen_new_interpreter_per_row_no_fork",
            "common_baseline": "post_import_catalog_oracle_native_load_cache_clear_gc",
            "cold_boundary": "construction_through_serialization_with_state_and_output_retained",
            "reused_boundary": "separate_preparation_then_execution_above_prepared_baseline",
            "release_boundary": "drop_state_and_output_clear_caches_gc",
            "controller_sampling_interval_seconds": SAMPLE_INTERVAL_SECONDS,
            "controller_external_to_measured_worker": True,
            "windows_metrics": [
                "working_set_bytes", "private_usage_bytes", "process_peak_working_set_bytes",
                "process_peak_pagefile_bytes",
            ],
            "python_metrics": "tracemalloc_current_and_peak_at_matching_worker_handshakes",
            "elapsed_time_interpretation": "descriptive_lifecycle_only_no_performance_claim",
        },
        "calibration_gate": {
            "per_arm_lifecycle_positive_os_peak_prevalence_min": 0.75,
            "per_cohort_positive_os_peak_prevalence_min": 0.70,
            "reused_prepared_retained_floor_bytes": 65_536,
            "reused_prepared_retained_prevalence_min": 0.50,
            "stable_signal_floor_bytes": 65_536,
            "minimum_stable_signal_logical_cells": 24,
            "replicate_range_over_median_max": 1.0,
            "stable_signal_prevalence_min": 0.75,
            "arm_discrimination_absolute_floor_bytes": 65_536,
            "arm_discrimination_relative_floor": 0.10,
            "arm_discrimination_prevalence_min": 0.50,
            "exact_mismatches_max": 0,
            "stability_mismatches_max": 0,
            "memory_accounting_mismatches_max": 0,
            "independent_replay_mismatches_max": 0,
        },
        "continuation": {
            "pass": "go_memory_calibration_only_requires_separate_candidate_freeze",
            "fail": "no_go_h6_routing_still_deferred",
            "production_routing_change_authorized": False,
            "selector_fit_authorized": False,
            "runpod_authorized": False,
            "h2_h3_reopened": False,
            "h8_activated": False,
            "h9_work_authorized": False,
            "publication_authorized": False,
        },
        "expected_rows": 708,
        "source_closure": closure,
        "source_closure_sha256": _digest(closure),
    }
    return {**core, "freeze_sha256": _digest(core)}


def validate_freeze(freeze: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    _require(freeze.get("schema") == SCHEMA, "H6 freeze schema")
    core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    _require(freeze.get("freeze_sha256") == _digest(core), "H6 freeze digest")
    replay = build_freeze(root)
    _require(canonical_bytes(replay) == canonical_bytes(freeze), "H6 freeze replay")
    rows = list(expected_schedule_rows(freeze))
    _require(len(rows) == freeze["expected_rows"] == 708, "H6 schedule cardinality")
    _require(len({row["row_id"] for row in rows}) == len(rows), "H6 schedule identities")
    return dict(freeze)


def freeze_to_path(project_root: str | Path, output_path: str | Path) -> dict[str, Any]:
    freeze = build_freeze(project_root)
    _write_new(Path(output_path), freeze)
    return freeze


def _validate_stored_oracles(oracles: Mapping[str, Any], parent_freeze: Mapping[str, Any]) -> None:
    _require(oracles.get("schema") == parent.ORACLE_SCHEMA, "stored oracle schema")
    core = {key: oracles[key] for key in oracles if key != "oracles_sha256"}
    _require(oracles.get("oracles_sha256") == _digest(core), "stored oracle digest")
    _require(oracles.get("parent_freeze_sha256") == parent_freeze["freeze_sha256"], "stored oracle parent")


def _catalog_from_frozen_payloads(
    freeze: Mapping[str, Any], planned: Mapping[str, Any]
) -> dict[str, Any]:
    payload = freeze["frozen_payloads"]["catalog"]
    lane, case_id = planned["lane"], planned["case_id"]
    catalog: dict[str, dict[str, Any]] = {"A": {}, "B": {}, "C": {}}
    if lane in {"A", "B"}:
        catalog[lane][case_id] = payload[lane][case_id]
    else:
        row = payload["C"][case_id]
        catalog["C"][case_id] = parent.MultiRootWorkload(
            row["workload_id"], row["family"], int(row["n_vars"]),
            tuple(expr_from_json(document) for document in row["separate_documents"]),
        )
    return catalog


def _validate_worker_freeze(freeze: Mapping[str, Any]) -> None:
    _require(freeze.get("schema") == SCHEMA, "H6 worker freeze schema")
    core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    _require(freeze.get("freeze_sha256") == _digest(core), "H6 worker freeze digest")
    _require(freeze.get("source_checkpoint") == SOURCE_CHECKPOINT, "H6 worker checkpoint")


def _prepare_a_direct(case: Mapping[str, Any]) -> dict[str, Any]:
    expression = expr_from_json(case["expression_v2"])
    return {"expression": expression, "env": build_bitset_env(case["variable_order"])}


def _run_a_direct(
    case: Mapping[str, Any], oracle: Mapping[str, Any], state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = state or _prepare_a_direct(case)
    bits = parent._eval_expr_bitset_fixed(
        state["expression"], case["variable_order"], case["fixed"], state["env"]
    )
    record = parent._truth_record(bits, case["n_vars"])
    _require(record == oracle["truth"], f"H6 direct oracle: {case['case_id']}")
    payload = canonical_bytes(record)
    return {
        "output_sha256": record["sha256"],
        "ordering_sha256": _digest(list(case["variable_order"])),
        "structure_sha256": _digest(case["expression_v2"]),
        "output_bytes": len(payload),
        "required_artifact_bytes": record["bytes"],
        "anchor": (state, record, payload),
    }


def _prepare_b_arm(
    case: Mapping[str, Any], arm: str, native: NativeSlotLibrary | None,
) -> dict[str, Any]:
    expression = expr_from_json(case["expression_v2"])
    state: dict[str, Any] = {"expression": expression}
    if arm == "r2_topological_liveness":
        state["arena"] = parent.compile_restricted_arena(case["expression_v2"])
    elif arm == "cm_ir_bigint":
        state["node"] = parent.compile_expr_to_cm_ir(
            expression, reuse_cache=False, persistent_cache=False, share_aware_flatten=True
        )
        state["program"] = parent.get_flat_program(state["node"])
    elif arm == "cse_flat_bigint":
        state["program"] = parent.get_expr_cse_program(expression, flatten=True)
    elif arm == "native_fused_slots":
        _require(native is not None, "H6 native library missing")
        state["arena"] = parent.compile_native_slot_arena(
            case["expression_v2"], native, variable_count=case["n_vars"]
        )
    else:
        raise ValueError(f"unknown H6 lane B arm: {arm}")
    return state


def _run_b_arm(
    case: Mapping[str, Any], oracle: Mapping[str, Any], arm: str,
    query_count: int, native: NativeSlotLibrary | None, state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = state or _prepare_b_arm(case, arm, native)
    trace = list(case["c36_trace"][:query_count])
    inputs = [
        ({item["variable"]: item["value"] for item in query["fixed"]}, tuple(query["remaining_order"]))
        for query in trace
    ]
    plans: list[Any] = []
    if arm == "r2_topological_liveness":
        plans = [parent.prepare_restriction(fixed, remaining) for fixed, remaining in inputs]
        outputs = tuple(parent.eval_restricted_r2(state["arena"], plan) for plan in plans)
    elif arm == "cm_ir_bigint":
        outputs = tuple(
            parent.eval_cm_node_flat(state["node"], remaining, fixed=fixed)
            for fixed, remaining in inputs
        )
    elif arm == "cse_flat_bigint":
        outputs = tuple(
            parent.eval_expr_flat_cse(state["expression"], remaining, fixed=fixed, flatten=True)
            for fixed, remaining in inputs
        )
    elif arm == "native_fused_slots":
        plans = [state["arena"].prepare_bindings(fixed, remaining) for fixed, remaining in inputs]
        outputs = tuple(
            state["arena"].evaluate(plan, len(remaining))
            for plan, (_, remaining) in zip(plans, inputs, strict=True)
        )
    else:  # pragma: no cover - guarded by preparation
        raise ValueError(f"unknown H6 lane B arm: {arm}")
    rows = [
        parent.restriction_row(query, int(output), case["n_vars"])
        for query, output in zip(trace, outputs, strict=True)
    ]
    document = parent.restriction_document(case["case_id"], rows)
    actual = _digest(document)
    _require(actual == oracle["checkpoints"][str(query_count)], f"H6 B oracle: {case['case_id']} {arm}")
    payload = canonical_bytes(document)
    return {
        "output_sha256": actual,
        "ordering_sha256": _digest([query["remaining_order"] for query in trace]),
        "structure_sha256": _digest({"arm": arm, "expression": case["expression_v2"]}),
        "output_bytes": len(payload),
        "required_artifact_bytes": len(payload),
        "anchor": (state, inputs, plans, outputs, document, payload),
    }


def _prepare_operation(
    planned: Mapping[str, Any], catalog: Mapping[str, Any], native: NativeSlotLibrary | None,
) -> dict[str, Any]:
    lane, case_id, arm = planned["lane"], planned["case_id"], planned["arm"]
    if lane == "A":
        case = catalog["A"][case_id]
        return profile._prepare_a(case) if arm == "cm_dense_full_reinflation" else _prepare_a_direct(case)
    if lane == "B":
        return _prepare_b_arm(catalog["B"][case_id], arm, native)
    if lane == "C":
        return profile._prepare_c(catalog["C"][case_id], arm)
    raise ValueError(f"unknown H6 lane: {lane}")


def _execute_operation(
    planned: Mapping[str, Any], catalog: Mapping[str, Any], oracles: Mapping[str, Any],
    native: NativeSlotLibrary | None, state: dict[str, Any] | None,
) -> dict[str, Any]:
    lane, case_id, arm = planned["lane"], planned["case_id"], planned["arm"]
    if lane == "A":
        case, oracle = catalog["A"][case_id], oracles["lanes"]["A"][case_id]
        if arm == "cm_dense_full_reinflation":
            return profile._run_a(case, oracle, state, False)
        return _run_a_direct(case, oracle, state)
    if lane == "B":
        return _run_b_arm(
            catalog["B"][case_id], oracles["lanes"]["B"][case_id], arm,
            int(planned["query_count"]), native, state,
        )
    if lane == "C":
        return profile._run_c(
            catalog["C"][case_id], oracles["lanes"]["C"][case_id], arm, state, False
        )
    raise ValueError(f"unknown H6 lane: {lane}")


def _features(planned: Mapping[str, Any], catalog: Mapping[str, Any]) -> dict[str, Any]:
    lane, case_id = planned["lane"], planned["case_id"]
    if lane in {"A", "B"}:
        case = catalog[lane][case_id]
        document = case["expression_v2"]

        def node_count(value: Any) -> int:
            if isinstance(value, Mapping) and isinstance(value.get("nodes"), list):
                return len(value["nodes"])
            if isinstance(value, Mapping) and "op" in value:
                return 1 + sum(node_count(value.get(name)) for name in ("a", "b"))
            return 0

        return {
            "n_vars": int(case["n_vars"]),
            "expression_nodes": node_count(document),
            "expression_bytes": len(canonical_bytes(document)),
            "query_count": int(planned["query_count"]),
        }
    workload = catalog["C"][case_id]
    return {
        "n_vars": int(workload.n_vars),
        "union_nodes": len(workload.union_document["nodes"]),
        "sum_separate_nodes": sum(len(item["nodes"]) for item in workload.separate_documents),
        "roots": len(workload.roots),
        "query_count": 64,
    }


def _emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False), flush=True)


def _command() -> str:
    line = sys.stdin.readline()
    _require(bool(line), "H6 controller closed worker input")
    value = json.loads(line)
    _require(isinstance(value, dict) and isinstance(value.get("command"), str), "H6 worker command")
    return value["command"]


def _trace_snapshot() -> dict[str, int]:
    current, peak = tracemalloc.get_traced_memory()
    return {"traced_current_bytes": int(current), "traced_peak_bytes": int(peak)}


def worker_main(project_root: str | Path, freeze_path: str | Path, row_id: str) -> int:
    root = Path(project_root).resolve()
    try:
        freeze = _load(Path(freeze_path))
        _validate_worker_freeze(freeze)
        planned_by_id = {row["row_id"]: row for row in expected_schedule_rows(freeze)}
        _require(row_id in planned_by_id, "unknown H6 worker row")
        planned = planned_by_id[row_id]
        oracles = freeze["frozen_payloads"]["oracles"]
        catalog = _catalog_from_frozen_payloads(freeze, planned)
        native = load_native_slot_library(root / freeze["native_library"]["path"])
        profile._reset_caches()
        gc.collect()
        tracemalloc.start()
        _emit({"phase": "ready", "pid": os.getpid(), **_trace_snapshot()})
        state: dict[str, Any] | None = None
        if planned["lifecycle"] == "reused":
            _require(_command() == "prepare", "H6 expected prepare")
            traced_before, _ = tracemalloc.get_traced_memory()
            tracemalloc.reset_peak()
            started = time.perf_counter_ns()
            state = _prepare_operation(planned, catalog, native)
            preparation_ns = time.perf_counter_ns() - started
            traced_current, traced_peak = tracemalloc.get_traced_memory()
            _emit({
                "phase": "prepared",
                "preparation_ns_descriptive": preparation_ns,
                "traced_current_bytes": traced_current,
                "traced_peak_bytes": traced_peak,
                "traced_peak_delta_bytes": max(0, traced_peak - traced_before),
                "traced_retained_delta_bytes": traced_current - traced_before,
            })
        _require(_command() == "execute", "H6 expected execute")
        traced_before, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        started = time.perf_counter_ns()
        result = _execute_operation(planned, catalog, oracles, native, state)
        execution_ns = time.perf_counter_ns() - started
        anchor = result.pop("anchor")
        traced_current, traced_peak = tracemalloc.get_traced_memory()
        _emit({
            "phase": "result",
            "execution_ns_descriptive": execution_ns,
            "exact_oracle_agreement": True,
            "features": _features(planned, catalog),
            **result,
            "traced_current_bytes": traced_current,
            "traced_peak_bytes": traced_peak,
            "traced_peak_delta_bytes": max(0, traced_peak - traced_before),
            "traced_retained_delta_bytes": traced_current - traced_before,
        })
        _require(_command() == "release", "H6 expected release")
        del anchor, result, state
        profile._reset_caches()
        gc.collect()
        _emit({"phase": "released", **_trace_snapshot()})
        tracemalloc.stop()
        return 0
    except Exception as exc:  # pragma: no cover - fail-closed subprocess envelope
        _emit({"phase": "error", "error_type": type(exc).__name__, "error": str(exc)})
        return 1


if os.name == "nt":
    class _ProcessMemoryCountersEx(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _psapi = ctypes.WinDLL("psapi", use_last_error=True)
    _kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    _kernel32.OpenProcess.restype = ctypes.c_void_p
    _kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    _kernel32.CloseHandle.restype = ctypes.c_int
    _psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(_ProcessMemoryCountersEx), ctypes.c_ulong,
    ]
    _psapi.GetProcessMemoryInfo.restype = ctypes.c_int


class _ExternalProcessMetrics:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.handle: Any = None
        if os.name == "nt":
            self.handle = _kernel32.OpenProcess(0x1000 | 0x0010, False, pid)
            _require(bool(self.handle), f"OpenProcess failed: {ctypes.get_last_error()}")

    def close(self) -> None:
        if self.handle:
            _kernel32.CloseHandle(self.handle)
            self.handle = None

    def sample(self) -> dict[str, int]:
        if os.name == "nt":
            counters = _ProcessMemoryCountersEx()
            counters.cb = ctypes.sizeof(counters)
            ok = _psapi.GetProcessMemoryInfo(self.handle, ctypes.byref(counters), counters.cb)
            _require(bool(ok), f"GetProcessMemoryInfo failed: {ctypes.get_last_error()}")
            return {
                "working_set_bytes": int(counters.WorkingSetSize),
                "private_usage_bytes": int(counters.PrivateUsage),
                "process_peak_working_set_bytes": int(counters.PeakWorkingSetSize),
                "process_peak_pagefile_bytes": int(counters.PeakPagefileUsage),
            }
        status = Path(f"/proc/{self.pid}/status").read_text(encoding="ascii")
        fields: dict[str, int] = {}
        for line in status.splitlines():
            if line.startswith(("VmRSS:", "VmHWM:")):
                name, value, _unit = line.split()
                fields[name.rstrip(":")] = int(value) * 1024
        private = 0
        rollup = Path(f"/proc/{self.pid}/smaps_rollup")
        if rollup.is_file():
            for line in rollup.read_text(encoding="ascii").splitlines():
                if line.startswith(("Private_Clean:", "Private_Dirty:")):
                    private += int(line.split()[1]) * 1024
        _require(fields.get("VmRSS", 0) > 0, "external Linux RSS unavailable")
        return {
            "working_set_bytes": fields["VmRSS"],
            "private_usage_bytes": private,
            "process_peak_working_set_bytes": fields.get("VmHWM", fields["VmRSS"]),
            "process_peak_pagefile_bytes": 0,
        }


class _ExternalSampler:
    def __init__(self, metrics: _ExternalProcessMetrics) -> None:
        self.metrics = metrics
        self.samples: list[dict[str, int]] = []
        self.error: Exception | None = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop.is_set():
            try:
                self.samples.append(self.metrics.sample())
            except Exception as exc:  # pragma: no cover - OS race fails the row
                self.error = exc
                return
            self.stop.wait(SAMPLE_INTERVAL_SECONDS)

    def __enter__(self) -> "_ExternalSampler":
        self.thread.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self.stop.set()
        self.thread.join(timeout=2.0)
        _require(not self.thread.is_alive(), "external H6 sampler did not stop")
        if self.error is not None:
            raise self.error
        try:
            self.samples.append(self.metrics.sample())
        except Exception:
            pass


class _LineReader:
    def __init__(self, stream: Any) -> None:
        self.values: queue.Queue[str | None] = queue.Queue()
        self.thread = threading.Thread(target=self._run, args=(stream,), daemon=True)
        self.thread.start()

    def _run(self, stream: Any) -> None:
        for line in stream:
            self.values.put(line)
        self.values.put(None)

    def get(self, timeout: float) -> dict[str, Any]:
        try:
            line = self.values.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError("H6 worker phase timeout") from exc
        _require(line is not None, "H6 worker output closed")
        value = json.loads(line)
        if value.get("phase") == "error":
            raise RuntimeError(f"{value.get('error_type')}: {value.get('error')}")
        return value


def _send(process: subprocess.Popen[str], command: str) -> None:
    _require(process.stdin is not None, "H6 worker stdin")
    process.stdin.write(json.dumps({"command": command}, separators=(",", ":")) + "\n")
    process.stdin.flush()


def _phase(
    process: subprocess.Popen[str], reader: _LineReader, metrics: _ExternalProcessMetrics,
    command: str, expected_phase: str, timeout: float,
) -> tuple[dict[str, Any], list[dict[str, int]]]:
    with _ExternalSampler(metrics) as sampler:
        _send(process, command)
        response = reader.get(timeout)
    _require(response.get("phase") == expected_phase, f"H6 expected {expected_phase}")
    _require(bool(sampler.samples), "H6 phase has no samples")
    return response, sampler.samples


def _metric_peak(samples: Sequence[Mapping[str, int]], name: str) -> int:
    return max(int(sample[name]) for sample in samples)


def _delta(value: int, baseline: int) -> int:
    return value - baseline


def run_child_cell(
    *, project_root: Path, freeze_path: Path, planned: Mapping[str, Any],
    python_executable: Path, worker_script: Path, phase_timeout_seconds: float,
) -> dict[str, Any]:
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    started = time.perf_counter_ns()
    process = subprocess.Popen(
        [str(python_executable), "-B", str(worker_script), "worker", "--project-root", str(project_root),
         "--freeze", str(freeze_path), "--row-id", planned["row_id"]],
        cwd=project_root, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", bufsize=1, creationflags=creationflags,
    )
    _require(process.stdout is not None and process.stderr is not None, "H6 worker pipes")
    reader = _LineReader(process.stdout)
    metrics: _ExternalProcessMetrics | None = None
    try:
        ready = reader.get(phase_timeout_seconds)
        _require(ready.get("phase") == "ready" and int(ready.get("pid", 0)) > 0, "H6 ready identity")
        worker_pid = int(ready["pid"])
        metrics = _ExternalProcessMetrics(worker_pid)
        common = metrics.sample()
        preparation_samples: list[dict[str, int]] = []
        prepared = ready
        if planned["lifecycle"] == "reused":
            prepared, preparation_samples = _phase(
                process, reader, metrics, "prepare", "prepared", phase_timeout_seconds
            )
        prepared_endpoint = metrics.sample()
        result, execution_samples = _phase(
            process, reader, metrics, "execute", "result", phase_timeout_seconds
        )
        retained = metrics.sample()
        released, release_samples = _phase(
            process, reader, metrics, "release", "released", phase_timeout_seconds
        )
        post_release = metrics.sample()
        process.wait(timeout=phase_timeout_seconds)
        stderr = process.stderr.read()
        _require(process.returncode == 0, f"H6 worker exit {process.returncode}: {stderr[-1000:]}")
        all_task_samples = [*preparation_samples, *execution_samples, retained]
        _require(bool(all_task_samples), "H6 task samples")
        memory = {
            "method": "external_controller_fresh_spawn_sampling/v1",
            "sample_interval_seconds": SAMPLE_INTERVAL_SECONDS,
            "common_baseline": common,
            "prepared_endpoint": prepared_endpoint,
            "retained_endpoint": retained,
            "post_release_endpoint": post_release,
            "preparation_sample_count": len(preparation_samples),
            "execution_sample_count": len(execution_samples),
            "release_sample_count": len(release_samples),
            "samplers_stopped": True,
            "working_set_task_peak_bytes": _metric_peak(all_task_samples, "working_set_bytes"),
            "working_set_task_peak_delta_bytes": max(
                0, _metric_peak(all_task_samples, "working_set_bytes") - common["working_set_bytes"]
            ),
            "private_task_peak_bytes": _metric_peak(all_task_samples, "private_usage_bytes"),
            "private_task_peak_delta_bytes": max(
                0, _metric_peak(all_task_samples, "private_usage_bytes") - common["private_usage_bytes"]
            ),
            "working_set_prepared_retained_delta_bytes": _delta(
                prepared_endpoint["working_set_bytes"], common["working_set_bytes"]
            ),
            "private_prepared_retained_delta_bytes": _delta(
                prepared_endpoint["private_usage_bytes"], common["private_usage_bytes"]
            ),
            "working_set_execution_peak_above_prepared_bytes": max(
                0, _metric_peak(execution_samples, "working_set_bytes") - prepared_endpoint["working_set_bytes"]
            ),
            "private_execution_peak_above_prepared_bytes": max(
                0, _metric_peak(execution_samples, "private_usage_bytes") - prepared_endpoint["private_usage_bytes"]
            ),
            "working_set_retained_delta_bytes": _delta(
                retained["working_set_bytes"], common["working_set_bytes"]
            ),
            "private_retained_delta_bytes": _delta(
                retained["private_usage_bytes"], common["private_usage_bytes"]
            ),
            "working_set_post_release_delta_bytes": _delta(
                post_release["working_set_bytes"], common["working_set_bytes"]
            ),
            "private_post_release_delta_bytes": _delta(
                post_release["private_usage_bytes"], common["private_usage_bytes"]
            ),
            "process_peak_working_set_bytes": post_release["process_peak_working_set_bytes"],
            "process_peak_pagefile_bytes": post_release["process_peak_pagefile_bytes"],
            "tracemalloc_common_bytes": int(ready["traced_current_bytes"]),
            "tracemalloc_prepared_bytes": int(prepared["traced_current_bytes"]),
            "tracemalloc_retained_bytes": int(result["traced_current_bytes"]),
            "tracemalloc_post_release_bytes": int(released["traced_current_bytes"]),
            "tracemalloc_task_peak_delta_bytes": max(
                int(prepared.get("traced_peak_delta_bytes", 0)), int(result["traced_peak_delta_bytes"])
            ),
            "tracemalloc_prepared_retained_delta_bytes": int(prepared["traced_current_bytes"])
            - int(ready["traced_current_bytes"]),
            "tracemalloc_retained_delta_bytes": int(result["traced_current_bytes"])
            - int(ready["traced_current_bytes"]),
            "tracemalloc_post_release_delta_bytes": int(released["traced_current_bytes"])
            - int(ready["traced_current_bytes"]),
        }
        return {
            "schema": RAW_SCHEMA,
            **dict(planned),
            "status": "ok",
            "child_pid": worker_pid,
            "launcher_pid": process.pid,
            "child_exit_code": process.returncode,
            "spawn_lifecycle_ns_descriptive": time.perf_counter_ns() - started,
            "preparation_ns_descriptive": int(prepared.get("preparation_ns_descriptive", 0)),
            "execution_ns_descriptive": int(result["execution_ns_descriptive"]),
            "exact_oracle_agreement": bool(result["exact_oracle_agreement"]),
            "output_sha256": result["output_sha256"],
            "ordering_sha256": result["ordering_sha256"],
            "structure_sha256": result["structure_sha256"],
            "output_bytes": int(result["output_bytes"]),
            "required_artifact_bytes": int(result["required_artifact_bytes"]),
            "features": result["features"],
            "memory": memory,
        }
    finally:
        if metrics is not None:
            metrics.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def run_campaign(
    *, project_root: str | Path, freeze_path: str | Path, output_dir: str | Path,
    python_executable: str | Path, worker_script: str | Path,
    phase_timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    freeze_file = Path(freeze_path).resolve()
    freeze = _load(freeze_file)
    validate_freeze(freeze, root)
    parent_freeze = _load(root / freeze["parent_freeze"]["path"])
    oracles = _load(root / freeze["parent_oracles"]["path"])
    parent.validate_oracles(oracles, root, parent_freeze)
    load_native_slot_library(root / freeze["native_library"]["path"])
    output = Path(output_dir).resolve()
    _require(output.is_relative_to(root) and not output.exists(), "new in-project H6 output required")
    output.mkdir(parents=True)
    raw_path = output / "RAW.jsonl"
    planned_rows = list(expected_schedule_rows(freeze))
    started = time.perf_counter()
    with raw_path.open("x", encoding="utf-8", newline="\n") as stream:
        for index, planned in enumerate(planned_rows, 1):
            row = run_child_cell(
                project_root=root, freeze_path=freeze_file, planned=planned,
                python_executable=Path(python_executable).resolve(),
                worker_script=Path(worker_script).resolve(),
                phase_timeout_seconds=phase_timeout_seconds,
            )
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
            stream.flush()
            if index == 1 or index % 25 == 0 or index == len(planned_rows):
                print(f"H6 rows {index}/{len(planned_rows)}", flush=True)
    return {
        "rows_written": len(planned_rows),
        "raw_sha256": _sha256(raw_path),
        "elapsed_seconds": time.perf_counter() - started,
    }


def _median(values: Sequence[int]) -> float:
    return float(statistics.median(values))


def _logical_records(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["logical_id"]].append(row)
    logical = []
    for logical_id, selected in sorted(grouped.items()):
        _require(len(selected) == REPLICATES, f"H6 replicate count: {logical_id}")
        first = selected[0]
        os_peaks = [
            max(
                int(row["memory"]["working_set_task_peak_delta_bytes"]),
                int(row["memory"]["private_task_peak_delta_bytes"]),
            )
            for row in selected
        ]
        prepared = [
            max(
                0,
                int(row["memory"]["working_set_prepared_retained_delta_bytes"]),
                int(row["memory"]["private_prepared_retained_delta_bytes"]),
            )
            for row in selected
        ]
        median_peak = _median(os_peaks)
        logical.append({
            "logical_id": logical_id,
            "lane": first["lane"],
            "case_id": first["case_id"],
            "query_count": first["query_count"],
            "arm": first["arm"],
            "lifecycle": first["lifecycle"],
            "cohort": first["cohort"],
            "median_os_task_peak_delta_bytes": median_peak,
            "median_prepared_retained_delta_bytes": _median(prepared),
            "replicate_range_over_median": (
                (max(os_peaks) - min(os_peaks)) / median_peak if median_peak > 0 else None
            ),
        })
    return logical


def summarize(raw_path: str | Path, freeze: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(raw_path).resolve()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    expected = list(expected_schedule_rows(freeze))
    _require(len(rows) == len(expected) == freeze["expected_rows"], "H6 raw cardinality")
    _require([row["row_id"] for row in rows] == [row["row_id"] for row in expected], "H6 raw schedule")
    exact_failures = [row["row_id"] for row in rows if row["status"] != "ok" or not row["exact_oracle_agreement"]]
    lifecycle_failures = [
        row["row_id"] for row in rows
        if row["child_exit_code"] != 0
        or not row["memory"]["samplers_stopped"]
        or row["memory"]["execution_sample_count"] < 1
    ]
    memory_failures = []
    for row in rows:
        memory = row["memory"]
        for name in ("working_set_bytes", "private_usage_bytes"):
            if any(int(memory[endpoint][name]) < 0 for endpoint in (
                "common_baseline", "prepared_endpoint", "retained_endpoint", "post_release_endpoint"
            )):
                memory_failures.append(row["row_id"])
                break
        if int(memory["working_set_task_peak_bytes"]) < int(memory["common_baseline"]["working_set_bytes"]):
            memory_failures.append(row["row_id"])
    stability_failures = []
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["logical_id"]].append(row)
    for logical_id, selected in grouped.items():
        identities = {
            (row["output_sha256"], row["ordering_sha256"], row["structure_sha256"])
            for row in selected
        }
        if len(identities) != 1 or len({row["child_pid"] for row in selected}) != REPLICATES:
            stability_failures.append(logical_id)
    logical = _logical_records(rows)
    gate = freeze["calibration_gate"]
    group_prevalence = {}
    for arm, lifecycle in sorted({(row["arm"], row["lifecycle"]) for row in logical}):
        selected = [row for row in logical if row["arm"] == arm and row["lifecycle"] == lifecycle]
        group_prevalence[f"{arm}/{lifecycle}"] = sum(
            row["median_os_task_peak_delta_bytes"] > 0 for row in selected
        ) / len(selected)
    cohort_prevalence = {}
    for cohort in ("observed", "fresh"):
        selected = [row for row in logical if row["cohort"] == cohort]
        cohort_prevalence[cohort] = sum(
            row["median_os_task_peak_delta_bytes"] > 0 for row in selected
        ) / len(selected)
    reused = [row for row in logical if row["lifecycle"] == "reused"]
    reused_prepared_prevalence = sum(
        row["median_prepared_retained_delta_bytes"] >= gate["reused_prepared_retained_floor_bytes"]
        for row in reused
    ) / len(reused)
    stable_signal = [
        row for row in logical
        if row["median_os_task_peak_delta_bytes"] >= gate["stable_signal_floor_bytes"]
    ]
    stable_signal_prevalence = (
        sum(
            row["replicate_range_over_median"] is not None
            and row["replicate_range_over_median"] <= gate["replicate_range_over_median_max"]
            for row in stable_signal
        ) / len(stable_signal)
        if stable_signal else 0.0
    )
    matched: dict[tuple[str, str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in logical:
        matched[(row["lane"], row["case_id"], row["query_count"], row["lifecycle"])].append(row)
    discriminating = 0
    for selected in matched.values():
        values = [row["median_os_task_peak_delta_bytes"] for row in selected]
        low, high = min(values), max(values)
        relative_floor = low * gate["arm_discrimination_relative_floor"] if low > 0 else 0
        if high - low >= max(gate["arm_discrimination_absolute_floor_bytes"], relative_floor):
            discriminating += 1
    discrimination_prevalence = discriminating / len(matched)
    conditions = {
        "validity": not exact_failures and not stability_failures and not lifecycle_failures and not memory_failures,
        "per_arm_lifecycle_positive_os_peak": all(
            value >= gate["per_arm_lifecycle_positive_os_peak_prevalence_min"]
            for value in group_prevalence.values()
        ),
        "per_cohort_positive_os_peak": all(
            value >= gate["per_cohort_positive_os_peak_prevalence_min"]
            for value in cohort_prevalence.values()
        ),
        "reused_prepared_retained": reused_prepared_prevalence >= gate["reused_prepared_retained_prevalence_min"],
        "minimum_stable_signal_cells": len(stable_signal) >= gate["minimum_stable_signal_logical_cells"],
        "stable_replicates": stable_signal_prevalence >= gate["stable_signal_prevalence_min"],
        "representation_discrimination": discrimination_prevalence >= gate["arm_discrimination_prevalence_min"],
    }
    if not conditions["validity"]:
        decision = "stop_local_validity_failure"
    elif all(conditions.values()):
        decision = "go_memory_calibration_only_requires_separate_candidate_freeze"
    else:
        decision = "no_go_h6_routing_still_deferred"
    core = {
        "schema": SUMMARY_SCHEMA,
        "freeze_sha256": freeze["freeze_sha256"],
        "raw_sha256": _sha256(path),
        "rows": len(rows),
        "logical_cells": len(logical),
        "rows_by_lane": {lane: sum(row["lane"] == lane for row in rows) for lane in ("A", "B", "C")},
        "exact_failures": exact_failures,
        "stability_failures": stability_failures,
        "lifecycle_failures": lifecycle_failures,
        "memory_accounting_failures": sorted(set(memory_failures)),
        "group_positive_os_peak_prevalence": group_prevalence,
        "cohort_positive_os_peak_prevalence": cohort_prevalence,
        "reused_prepared_retained_prevalence": reused_prepared_prevalence,
        "stable_signal_logical_cells": len(stable_signal),
        "stable_signal_prevalence": stable_signal_prevalence,
        "matched_arm_groups": len(matched),
        "discriminating_arm_groups": discriminating,
        "arm_discrimination_prevalence": discrimination_prevalence,
        "conditions": conditions,
        "decision": decision,
        "candidate_implemented": False,
        "production_routing_changed": False,
        "runpod_authorization_request_permitted": False,
        "environment": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
    }
    return {**core, "summary_sha256": _digest(core)}


def summary_to_path(raw_path: str | Path, freeze_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    freeze = _load(Path(freeze_path))
    summary = summarize(raw_path, freeze)
    _write_new(Path(output_path), summary)
    return summary
