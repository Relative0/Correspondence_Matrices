"""Corrected q1/q4/q16/q64 timing and isolated memory follow-up.

The verified architecture comparison timed a complete q64 trace and retained
q1/q4/q16 only as correctness checkpoints.  This module makes each query-count
prefix a separate timed cell.  Decision-bearing Linux cells execute in forked
children so ``wait4`` supplies a resettable per-cell RSS high-water mark.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time
from typing import Any

import numpy as np

from bitset_backend import clear_bitset_env_cache, clear_words_env_cache

from . import architecture_comparison_campaign as parent
from .architecture_comparison_freeze import verify_freeze as verify_parent_freeze
from .contracts import canonical_bytes
from .gf2_native_slots import NativeSlotLibrary, load_native_slot_library
from .gf2_wide_repeated_queries import (
    semantic_document as restriction_document,
    semantic_row as restriction_row,
)


FREEZE_SCHEMA = "cm-architecture-query-ladder-freeze/v1"
RAW_SCHEMA = "cm-architecture-query-ladder-timed-cell/v1"
RESULT_SCHEMA = "cm-architecture-query-ladder-result/v1"
VERIFICATION_SCHEMA = "cm-architecture-query-ladder-independent-verification/v1"
QUERY_COUNTS = (1, 4, 16, 64)
MEMORY_METHOD = "isolated_fork_child_wait4_ru_maxrss/v1"
FUNCTIONAL_MEMORY_METHOD = "functional_validation_not_measured"
STAGES = parent.STAGES


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _stage_timer(clock: Callable[[], int], function: Callable[[], Any]) -> tuple[int, Any]:
    start = clock()
    result = function()
    return clock() - start, result


def execute_query_count_cell(
    case: Mapping[str, Any], arm: str, oracle: Mapping[str, Any],
    native: NativeSlotLibrary | None, query_count: int,
    *, clock: Callable[[], int] = time.perf_counter_ns,
    isolated_process_cleanup: bool = False,
) -> dict[str, Any]:
    """Execute one separately charged query-count prefix."""
    _require(query_count in QUERY_COUNTS, "unsupported query count")
    trace = list(case["c36_trace"][:query_count])
    _require(len(trace) == query_count, "incomplete query trace")
    bounded_case = dict(case)
    bounded_case["c36_trace"] = trace
    clear_bitset_env_cache()
    clear_words_env_cache()
    timings, outputs, resources = parent._lane_b_outputs(
        bounded_case, arm, native, clock
    )

    def deliver() -> dict[str, Any]:
        rows = [
            restriction_row(query, output, case["n_vars"])
            for query, output in zip(trace, outputs, strict=True)
        ]
        return restriction_document(case["case_id"], rows)

    timings["delivery_ns"], document = _stage_timer(clock, deliver)
    actual = _digest(document)
    expected = oracle["checkpoints"][str(query_count)]
    _require(actual == expected, f"query-ladder oracle mismatch: {case['case_id']} {arm} q{query_count}")
    timings["serialization_ns_when_applicable"], payload = _stage_timer(
        clock, lambda: canonical_bytes(document)
    )
    if isolated_process_cleanup:
        def clear_process_caches() -> None:
            clear_bitset_env_cache()
            clear_words_env_cache()

        timings["cleanup_ns"], _ = _stage_timer(clock, clear_process_caches)
        cleanup_method = "cache_clear_then_isolated_child_exit"
    else:
        timings["cleanup_ns"], _ = _stage_timer(clock, gc.collect)
        cleanup_method = "gc_collect_in_process"
    _require(set(timings) == set(STAGES), "query-ladder timing stages")
    timings["accounted_total_ns"] = sum(timings[stage] for stage in STAGES)
    resources = dict(resources)
    resources["queries"] = query_count
    return {
        "schema": RAW_SCHEMA,
        "lane": "B",
        "case_id": case["case_id"],
        "arm": arm,
        "query_count": query_count,
        "status": "ok",
        "reason": "completed",
        "timings_ns": timings,
        "output_sha256": actual,
        "output_bytes": len(payload),
        "exact_check_passed": True,
        "cleanup_method": cleanup_method,
        "retained_bytes": int(resources.get("retained_bytes", 0)),
        "resources": resources,
        "memory_measurement": {
            "method": FUNCTIONAL_MEMORY_METHOD,
            "interpretation_permitted": False,
        },
    }


def _current_rss_bytes() -> int:
    """Return current Linux RSS without importing a third-party sampler."""
    statm = Path("/proc/self/statm")
    _require(sys.platform == "linux" and statm.is_file(), "Linux /proc RSS required")
    fields = statm.read_text(encoding="ascii").split()
    _require(len(fields) >= 2 and fields[1].isdigit(), "invalid /proc/self/statm")
    return int(fields[1]) * int(os.sysconf("SC_PAGE_SIZE"))


def _write_pipe(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        _require(written > 0, "isolated child pipe write failed")
        view = view[written:]


def execute_isolated_linux_cell(function: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Execute one cell in a fork child and attach its independent RSS peak."""
    _require(sys.platform == "linux" and hasattr(os, "fork") and hasattr(os, "wait4"), "Linux fork/wait4 required")
    baseline = _current_rss_bytes()
    read_fd, write_fd = os.pipe()
    lifecycle_started = time.perf_counter_ns()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        try:
            envelope = {"status": "ok", "row": function()}
        except Exception as exc:  # pragma: no cover - exercised by remote fail-closed checks
            envelope = {"status": "error", "error_type": type(exc).__name__, "error": str(exc)}
        try:
            _write_pipe(
                write_fd,
                json.dumps(envelope, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"),
            )
        finally:
            os.close(write_fd)
        os._exit(0 if envelope["status"] == "ok" else 1)

    os.close(write_fd)
    chunks: list[bytes] = []
    try:
        while True:
            chunk = os.read(read_fd, 65_536)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(read_fd)
    waited_pid, wait_status, usage = os.wait4(pid, 0)
    lifecycle_ns = time.perf_counter_ns() - lifecycle_started
    _require(waited_pid == pid, "isolated child identity mismatch")
    exit_code = os.waitstatus_to_exitcode(wait_status)
    envelope = json.loads(b"".join(chunks)) if chunks else {}
    if exit_code != 0 or envelope.get("status") != "ok":
        error_type = envelope.get("error_type", "IsolatedCellError")
        error = envelope.get("error", "isolated query-ladder cell failed without an envelope")
        raise RuntimeError(f"{error_type}: {error}")
    row = envelope["row"]
    peak = int(usage.ru_maxrss) * 1024
    _require(peak > 0 and baseline > 0, "isolated RSS measurement unavailable")
    row["memory_measurement"] = {
        "method": MEMORY_METHOD,
        "interpretation_permitted": True,
        "peak_rss_bytes": peak,
        "inherited_baseline_rss_bytes": baseline,
        "incremental_peak_rss_bytes": max(0, peak - baseline),
        "child_exit_code": exit_code,
        "isolation_lifecycle_ns": lifecycle_ns,
        "isolation_lifecycle_in_accounted_timing": False,
    }
    return row


def expected_schedule_rows(freeze: Mapping[str, Any]):
    schedule = freeze["schedule"]
    for block, order in enumerate(schedule["arm_orders"]):
        for query_position, query_count in enumerate(schedule["query_counts"]):
            for case_position, case_id in enumerate(schedule["case_order"]):
                for arm_position, arm in enumerate(order):
                    yield {
                        "lane": "B",
                        "case_id": case_id,
                        "arm": arm,
                        "query_count": query_count,
                        "block": block,
                        "query_position": query_position,
                        "case_position": case_position,
                        "arm_position": arm_position,
                        "arm_order": list(order),
                    }


def functional_smoke(
    root: Path, freeze: Mapping[str, Any], oracles: Mapping[str, Any], native_path: Path,
) -> dict[str, Any]:
    followup = validate_followup_freeze(freeze)
    parent_freeze = _load(root / followup["parent_freeze"]["path"])
    verify_parent_freeze(parent_freeze, root)
    parent.validate_oracles(oracles, root, parent_freeze)
    native = load_native_slot_library(native_path)
    catalog = parent.resolve_catalog(root, parent_freeze)["B"]
    case_id = next(
        case for case in followup["schedule"]["case_order"] if case.startswith("fresh-tree-")
    )
    clock = parent._DeterministicClock()
    rows = [
        execute_query_count_cell(
            catalog[case_id], arm, oracles["lanes"]["B"][case_id], native,
            query_count, clock=clock,
        )
        for query_count in QUERY_COUNTS
        for arm in followup["schedule"]["arms"]
    ]
    _require(all(row["exact_check_passed"] for row in rows), "functional query-ladder exactness")
    return {
        "schema": "cm-architecture-query-ladder-functional-smoke/v1",
        "status": "pass",
        "rows": len(rows),
        "case_id": case_id,
        "arms": list(followup["schedule"]["arms"]),
        "query_counts": list(QUERY_COUNTS),
        "synthetic_clock_used": True,
        "timing_evidence_produced": False,
        "memory_evidence_produced": False,
    }


def validate_followup_freeze(freeze: Mapping[str, Any]) -> Mapping[str, Any]:
    expected = {
        "schema", "status", "date", "source_checkpoint", "parent_freeze",
        "parent_analysis", "oracles", "source_closure", "source_closure_sha256",
        "schedule", "measurement_contract", "publication_gates", "permissions",
        "timing_evidence_produced", "memory_evidence_produced", "freeze_sha256",
    }
    _require(isinstance(freeze, Mapping) and set(freeze) == expected, "follow-up freeze fields")
    core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    _require(freeze["schema"] == FREEZE_SCHEMA and freeze["freeze_sha256"] == _digest(core), "follow-up freeze identity")
    schedule = freeze["schedule"]
    _require(tuple(schedule["query_counts"]) == QUERY_COUNTS, "follow-up query counts")
    _require(
        schedule["planned_cells"]
        == len(schedule["case_order"]) * len(schedule["arms"]) * len(schedule["arm_orders"]) * len(QUERY_COUNTS),
        "follow-up planned cells",
    )
    _require(sum(1 for _ in expected_schedule_rows(freeze)) == schedule["planned_cells"], "follow-up schedule expansion")
    memory = freeze["measurement_contract"]["memory"]
    _require(
        memory["method"] == MEMORY_METHOD
        and memory["one_fresh_child_per_timed_cell"] is True
        and memory["timing_inside_child_excludes_fork"] is True
        and memory["reports_inherited_baseline_and_incremental_peak"] is True,
        "follow-up memory contract",
    )
    _require(freeze["timing_evidence_produced"] is False and freeze["memory_evidence_produced"] is False, "follow-up evidence boundary")
    return freeze


def verify_followup_freeze(freeze: Mapping[str, Any], root: Path) -> dict[str, Any]:
    validate_followup_freeze(freeze)
    for binding in (freeze["parent_freeze"], freeze["parent_analysis"], freeze["oracles"]):
        path = (root / binding["path"]).resolve()
        _require(path.is_relative_to(root) and path.is_file(), "follow-up bound input missing")
        _require(path.stat().st_size == binding["bytes"] and _sha256(path) == binding["sha256"], "follow-up bound input mismatch")
    parent_freeze = _load(root / freeze["parent_freeze"]["path"])
    verify_parent_freeze(parent_freeze, root)
    _require(
        freeze["schedule"]["case_order"] == parent_freeze["schedules"]["B"]["case_order"]
        and freeze["schedule"]["arms"] == parent_freeze["schedules"]["B"]["arms"]
        and freeze["schedule"]["arm_orders"] == parent_freeze["schedules"]["B"]["arm_orders"],
        "follow-up does not preserve parent Lane B schedule",
    )
    closure = freeze["source_closure"]
    _require(freeze["source_closure_sha256"] == _digest(closure), "follow-up source closure digest")
    for item in closure:
        path = (root / item["path"]).resolve()
        _require(
            path.is_relative_to(root) and path.is_file()
            and path.stat().st_size == item["bytes"] and _sha256(path) == item["sha256"],
            f"follow-up source mismatch: {item['path']}",
        )
    return {
        "schema": "cm-architecture-query-ladder-freeze-verification/v1",
        "status": "verified_frozen_not_authorized",
        "freeze_sha256": freeze["freeze_sha256"],
        "planned_cells": freeze["schedule"]["planned_cells"],
        "query_counts": list(QUERY_COUNTS),
        "source_files": len(closure),
        "timing_evidence_produced": False,
        "memory_evidence_produced": False,
        "cloud_authorized": False,
    }


def run_campaign(
    *, project_root: Path, freeze_path: Path, oracles_path: Path,
    native_library_path: Path, output_dir: Path, max_seconds: float,
) -> dict[str, Any]:
    _require(sys.platform == "linux" and hasattr(os, "wait4"), "decision-bearing follow-up requires Linux wait4")
    root = project_root.resolve()
    output = output_dir.resolve()
    _require(output.is_relative_to(root) and not output.exists(), "new in-project output required")
    freeze = _load(freeze_path)
    verify_followup_freeze(freeze, root)
    parent_freeze = _load(root / freeze["parent_freeze"]["path"])
    oracles = _load(oracles_path)
    parent.validate_oracles(oracles, root, parent_freeze)
    native = load_native_slot_library(native_library_path)
    catalog = parent.resolve_catalog(root, parent_freeze)["B"]
    output.mkdir(parents=True)
    raw_path = output / "raw_measurements.jsonl"
    started = time.perf_counter()
    rows = 0
    with raw_path.open("x", encoding="utf-8", newline="\n") as stream:
        for planned in expected_schedule_rows(freeze):
            if time.perf_counter() - started > max_seconds:
                raise TimeoutError("architecture query-ladder follow-up exceeded wall bound")
            case = catalog[planned["case_id"]]
            oracle = oracles["lanes"]["B"][planned["case_id"]]
            row = execute_isolated_linux_cell(
                lambda case=case, arm=planned["arm"], oracle=oracle,
                query_count=planned["query_count"]: execute_query_count_cell(
                    case, arm, oracle, native, query_count,
                    isolated_process_cleanup=True,
                )
            )
            row.update({key: value for key, value in planned.items() if key not in {"lane", "case_id", "arm", "query_count"}})
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
            rows += 1
    expected = freeze["schedule"]["planned_cells"]
    _require(rows == expected, "query-ladder result cardinality")
    result = {
        "schema": RESULT_SCHEMA,
        "status": "complete",
        "freeze_sha256": _sha256(freeze_path),
        "freeze_canonical_sha256": freeze["freeze_sha256"],
        "oracles_sha256": _sha256(oracles_path),
        "native_library_sha256": _sha256(native_library_path),
        "raw_measurements_sha256": _sha256(raw_path),
        "expected_rows": expected,
        "counts": {"ok": rows, "refused": 0, "failed": 0},
        "query_counts": list(QUERY_COUNTS),
        "memory_method": MEMORY_METHOD,
        "elapsed_seconds": time.perf_counter() - started,
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "decision": {
            "performance_interpretation_deferred_to_independent_verifier": True,
            "memory_interpretation_deferred_to_independent_verifier": True,
            "selector_fitted": False,
            "neural_training": False,
            "production_routing_changed": False,
            "website_updated": False,
        },
    }
    _write_json(output / "results.json", result)
    return result
