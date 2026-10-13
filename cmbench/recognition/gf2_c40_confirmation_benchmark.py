"""C40 development-blind GF(2) confirmation and peak-memory benchmark.

The C39 freeze remains immutable.  This successor uses a newly acquired,
separately pinned public BLIF collection and records memory in cold child
processes so that the two analysis procedures cannot inherit one another's
allocator state.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import base64
import ctypes
from ctypes import wintypes
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc
from typing import Any, Iterable, Mapping

from .blif import BlifConeMetadata, parse_blif
from .gf2_decomposition import ExactGF2Analysis, analyze_exact_gf2, analyze_screened_exact_gf2, truth_sha256
from .gf2_decomposition_experiment import make_gf2_controls


ROOT = Path(__file__).resolve().parents[2]
FREEZE_SCHEMA = "crse-c40-gf2-development-blind-freeze/v1"
RUN_SCHEMA = "crse-c40-gf2-development-blind-run/v1"
MEMORY_WORKER_SCHEMA = "crse-c40-gf2-cold-memory-worker/v1"
METHODS = ("c15_exhaustive", "c16_screened")
CORPUS_RELATIVE = Path("external/c40_boolean_function_benchmarks")
BLIF_RELATIVE = CORPUS_RELATIVE / "benchmarks/blif"
SOURCE_CLOSURE_PATHS = (
    "cmbench/recognition/blif.py",
    "cmbench/recognition/gf2_decomposition.py",
    "cmbench/recognition/gf2_decomposition_experiment.py",
    "cmbench/recognition/gf2_c40_confirmation_benchmark.py",
)


@dataclass(frozen=True)
class C40Config:
    """All C40 choices that affect the frozen selection or measurement plan."""

    seed: int = 20260916
    case_count: int = 20
    primary_rounds: int = 5
    memory_rounds: int = 3
    max_partitions: int = 64
    materialize_budget: int = 4
    min_support: int = 3
    max_support: int = 8
    min_source_nodes: int = 8
    max_source_nodes: int = 256
    worker_timeout_seconds: float = 60.0
    max_wall_seconds: float = 1200.0

    def validate(self) -> None:
        if (
            type(self.seed) is not int
            or type(self.case_count) is not int or not 8 <= self.case_count <= 40
            or type(self.primary_rounds) is not int or not 3 <= self.primary_rounds <= 9
            or type(self.memory_rounds) is not int or not 2 <= self.memory_rounds <= 7
            or type(self.max_partitions) is not int or not 8 <= self.max_partitions <= 128
            or type(self.materialize_budget) is not int or not 1 <= self.materialize_budget <= 16
            or type(self.min_support) is not int or type(self.max_support) is not int
            or not 2 <= self.min_support <= self.max_support <= 10
            or type(self.min_source_nodes) is not int or type(self.max_source_nodes) is not int
            or not 1 <= self.min_source_nodes <= self.max_source_nodes <= 4096
            or type(self.worker_timeout_seconds) not in (int, float) or not 5 <= self.worker_timeout_seconds <= 600
            or type(self.max_wall_seconds) not in (int, float) or not 60 <= self.max_wall_seconds <= 3600
        ):
            raise ValueError("invalid C40 GF(2) confirmation config")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _write_json_x(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl_x(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, allow_nan=False) + "\n")


def _git_revision(path: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True, encoding="utf-8"
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("C40 public corpus checkout has no readable Git revision") from exc


def _source_closure(root: Path) -> list[dict[str, Any]]:
    result = []
    for relative in SOURCE_CLOSURE_PATHS:
        path = root / relative
        if not path.is_file():
            raise ValueError(f"C40 source closure path is missing: {relative}")
        result.append({"path": relative, "bytes": path.stat().st_size, "sha256": _sha256_file(path)})
    return result


def _metadata_document(metadata: BlifConeMetadata) -> dict[str, Any]:
    return {
        "source_nodes": metadata.source_nodes,
        "source_edges": metadata.source_edges,
        "depth": metadata.depth,
        "local_fanin": metadata.local_fanin,
        "local_cubes": metadata.local_cubes,
        "local_literals": metadata.local_literals,
    }


def _candidate_key(seed: int, source_sha256: str, metadata: BlifConeMetadata) -> str:
    return _digest({
        "selection_schema": "c40-boolfunc-one-cone-per-source/v1",
        "seed": seed,
        "source_sha256": source_sha256,
        "root_node": metadata.node,
        "support": list(metadata.support),
        "metadata": _metadata_document(metadata),
    })


def _schedule(cases: list[Mapping[str, Any]], *, seed: int, rounds: int, lane: str) -> list[dict[str, Any]]:
    result = []
    for round_index in range(rounds):
        ordered_cases = sorted(
            cases,
            key=lambda row: _digest({"seed": seed, "round": round_index, "case_id": row["case_id"], "lane": lane}),
        )
        for position, case in enumerate(ordered_cases):
            methods = METHODS if (round_index + position) % 2 == 0 else tuple(reversed(METHODS))
            for within_case_order, method in enumerate(methods):
                core = {
                    "round": round_index,
                    "case_id": case["case_id"],
                    "method": method,
                    "within_case_order": within_case_order,
                    "case_position": position,
                    "lane": lane,
                }
                result.append({**core, "schedule_sha256": _digest(core)})
    return result


def _freeze_controls(seed: int) -> list[dict[str, Any]]:
    return [
        {
            "case_id": control["case_id"],
            "n_vars": control["n_vars"],
            "required_kind": control["required_kind"],
            "row_partitions": control["row_partitions"],
            "source_sha256": truth_sha256(control["bits"], control["n_vars"]),
        }
        for control in make_gf2_controls(seed)
    ]


def build_freeze(*, project_root: str | Path, config: C40Config,
                 created_utc: str | None = None) -> dict[str, Any]:
    """Create a pre-analysis, independently sourced C40 selection contract."""
    config.validate()
    root = Path(project_root).resolve()
    corpus = root / CORPUS_RELATIVE
    blif_root = root / BLIF_RELATIVE
    source_paths = sorted(blif_root.glob("*.blif"))
    if not corpus.is_dir() or len(source_paths) < config.case_count:
        raise ValueError("C40 Boolean Function Suite BLIF corpus is unavailable or too small")

    source_rows = []
    selected = []
    for path in source_paths:
        source_sha256 = _sha256_file(path)
        netlist = parse_blif(path)
        eligible = [
            metadata for metadata in netlist.candidate_metadata(
                min_support=config.min_support,
                max_support=config.max_support,
                max_source_nodes=config.max_source_nodes,
            ) if metadata.source_nodes >= config.min_source_nodes
        ]
        source_rows.append({
            "path": _relative(root, path),
            "bytes": path.stat().st_size,
            "sha256": source_sha256,
            "eligible_cones": len(eligible),
        })
        if not eligible:
            continue
        metadata = min(eligible, key=lambda row: (_candidate_key(config.seed, source_sha256, row), row.node))
        bits, support = netlist.packed_value(metadata.node)
        if tuple(support) != metadata.support:
            raise RuntimeError("C40 cone support identity disagrees with packed evaluation")
        selection_sha256 = _candidate_key(config.seed, source_sha256, metadata)
        selected.append({
            "case_id": f"boolfunc-c40-{selection_sha256[:16]}",
            "selection_sha256": selection_sha256,
            "source": _relative(root, path),
            "source_sha256": source_sha256,
            "root_node": metadata.node,
            "support": list(metadata.support),
            "n_vars": len(metadata.support),
            "truth_bits_hex": hex(bits),
            "truth_sha256": truth_sha256(bits, len(metadata.support)),
            "cone": _metadata_document(metadata),
        })
    if len(selected) < config.case_count:
        raise ValueError("insufficient C40 sources with a bounded eligible cone")
    cases = sorted(selected, key=lambda row: (row["selection_sha256"], row["case_id"]))[:config.case_count]
    if len({row["case_id"] for row in cases}) != len(cases):
        raise RuntimeError("C40 case identifier collision")

    created = created_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    core = {
        "schema": FREEZE_SCHEMA,
        "status": "frozen_before_c40_analysis",
        "created_utc": created,
        "c40_analysis_results_inspected": False,
        "config": asdict(config),
        "corpus": {
            "collection": "General Boolean Function Suite BLIF collection",
            "public_repository": "https://github.com/boolean-function-benchmarks/benchmarks",
            "upstream_commit": _git_revision(corpus),
            "source_glob": "benchmarks/blif/*.blif",
            "one_cone_per_source_file": True,
            "selection_policy": "Hash-rank eligible bounded cones within each source file, then hash-rank source representatives. Selection uses source identity and cone metadata only; no C40 timing, memory, candidate count, or decomposition outcome enters selection.",
            "development_blindness": {
                "scope": "C15/C16 implementation and C39 benchmark development",
                "freshly_acquired_for_c40": True,
                "used_to_develop_c15_c16": False,
                "used_to_select_c39": False,
                "selection_frozen_before_c40_analysis": True,
                "limitation": "This is a reproducible repository-local provenance statement. It cannot prove that no contributor had prior familiarity with the public function families, and it does not make C15/C16 an independently implemented algorithm.",
            },
            "source_files": source_rows,
        },
        "cases": cases,
        "primary_schedule": _schedule(cases, seed=config.seed, rounds=config.primary_rounds, lane="primary"),
        "memory_schedule": _schedule(cases, seed=config.seed, rounds=config.memory_rounds, lane="cold_memory"),
        "controls": _freeze_controls(config.seed),
        "analysis_contract": {
            "input": "Frozen packed truth vector. Parsing and truth-vector construction are excluded from the C15/C16 analysis and cold-memory scopes.",
            "c15_control": "analyze_exact_gf2 with every accepted artifact materialized.",
            "c16_candidate": "analyze_screened_exact_gf2 with complete descriptor evaluation and frozen materialize budget four.",
            "canonical_result": "C15 and C16 selected artifact documents must be byte-identical for every public case and structured control.",
            "primary_statistic": "Sum of per-case medians across balanced in-process analysis-only calls.",
            "memory_statistic": "For each scheduled method/case cell a cold Python child process records Windows process peak working set, sampled working set, private usage, and tracemalloc peak. The baseline is after imports and before one analysis call.",
            "memory_comparison_limit": "Peak working-set deltas can be zero when import initialization already set the child high-water mark. Raw baseline, final, OS high-water, sampled, and tracemalloc values are retained; no single metric is treated as a universal memory cost.",
        },
        "source_closure": _source_closure(root),
    }
    freeze = {**core, "source_closure_sha256": _digest(core["source_closure"])}
    freeze["freeze_sha256"] = _digest(freeze)
    validate_freeze(freeze)
    return freeze


def validate_freeze(freeze: Mapping[str, Any]) -> None:
    expected = {
        "schema", "status", "created_utc", "c40_analysis_results_inspected", "config", "corpus", "cases",
        "primary_schedule", "memory_schedule", "controls", "analysis_contract", "source_closure",
        "source_closure_sha256", "freeze_sha256",
    }
    if not isinstance(freeze, Mapping) or set(freeze) != expected:
        raise ValueError("invalid C40 freeze fields")
    if freeze["schema"] != FREEZE_SCHEMA or freeze["status"] != "frozen_before_c40_analysis":
        raise ValueError("invalid C40 freeze identity")
    if freeze["c40_analysis_results_inspected"] is not False:
        raise ValueError("C40 freeze must precede C40 analysis")
    config = C40Config(**freeze["config"])
    config.validate()
    core = {key: freeze[key] for key in expected if key != "freeze_sha256"}
    if freeze["freeze_sha256"] != _digest(core):
        raise ValueError("C40 freeze digest mismatch")
    if freeze["source_closure_sha256"] != _digest(freeze["source_closure"]):
        raise ValueError("C40 source closure digest mismatch")
    cases = freeze["cases"]
    if not isinstance(cases, list) or len(cases) != config.case_count:
        raise ValueError("C40 case count mismatch")
    case_ids = [row.get("case_id") for row in cases if isinstance(row, Mapping)]
    if len(case_ids) != len(cases) or len(set(case_ids)) != len(cases):
        raise ValueError("C40 duplicate or invalid case identifiers")
    for row in cases:
        expected_case = {"case_id", "selection_sha256", "source", "source_sha256", "root_node", "support",
                         "n_vars", "truth_bits_hex", "truth_sha256", "cone"}
        if set(row) != expected_case or not isinstance(row["support"], list):
            raise ValueError("invalid C40 case fields")
        if row["n_vars"] != len(row["support"]) or not config.min_support <= row["n_vars"] <= config.max_support:
            raise ValueError("C40 support bounds mismatch")
        if truth_sha256(int(row["truth_bits_hex"], 16), row["n_vars"]) != row["truth_sha256"]:
            raise ValueError("C40 truth identity mismatch")
    if freeze["primary_schedule"] != _schedule(cases, seed=config.seed, rounds=config.primary_rounds, lane="primary"):
        raise ValueError("C40 primary balanced schedule mismatch")
    if freeze["memory_schedule"] != _schedule(cases, seed=config.seed, rounds=config.memory_rounds, lane="cold_memory"):
        raise ValueError("C40 memory balanced schedule mismatch")
    if len(freeze["controls"]) != 12:
        raise ValueError("C40 control freeze mismatch")


def verify_freeze(freeze: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    """Verify code, corpus sources, selected metadata, and truth identity."""
    validate_freeze(freeze)
    root = Path(project_root).resolve()
    closure = _source_closure(root)
    source_closure_match = closure == freeze["source_closure"]
    source_rows = {row["path"]: row for row in freeze["corpus"]["source_files"]}
    source_checks = []
    for relative, expected in sorted(source_rows.items()):
        path = root / relative
        source_checks.append({
            "path": relative,
            "present": path.is_file(),
            "bytes_match": path.is_file() and path.stat().st_size == expected["bytes"],
            "sha256_match": path.is_file() and _sha256_file(path) == expected["sha256"],
        })
    case_checks = []
    for case in freeze["cases"]:
        path = root / case["source"]
        match, detail = False, None
        try:
            netlist = parse_blif(path)
            metadata = netlist.bounded_metadata(case["root_node"], min_support=1, max_support=16, max_source_nodes=4096)
            bits, support = netlist.packed_value(case["root_node"])
            match = (
                metadata is not None
                and tuple(support) == tuple(case["support"])
                and _metadata_document(metadata) == case["cone"]
                and truth_sha256(bits, case["n_vars"]) == case["truth_sha256"]
                and _candidate_key(freeze["config"]["seed"], case["source_sha256"], metadata) == case["selection_sha256"]
            )
        except (OSError, ValueError, RuntimeError) as exc:
            detail = f"{type(exc).__name__}: {exc}"
        case_checks.append({"case_id": case["case_id"], "match": match, "detail": detail})
    return {
        "schema": "crse-c40-gf2-development-blind-freeze-verification/v1",
        "freeze_sha256": freeze["freeze_sha256"],
        "source_closure_match": source_closure_match,
        "source_files": source_checks,
        "cases": case_checks,
        "verified": source_closure_match and all(
            row["present"] and row["bytes_match"] and row["sha256_match"] for row in source_checks
        ) and all(row["match"] for row in case_checks),
    }


def _load_cases(freeze: Mapping[str, Any], root: Path) -> dict[str, tuple[int, int]]:
    result = {}
    for row in freeze["cases"]:
        netlist = parse_blif(root / row["source"])
        bits, support = netlist.packed_value(row["root_node"])
        if tuple(support) != tuple(row["support"]) or truth_sha256(bits, row["n_vars"]) != row["truth_sha256"]:
            raise ValueError(f"C40 frozen source changed for {row['case_id']}")
        result[row["case_id"]] = (bits, row["n_vars"])
    return result


def _analyze(method: str, bits: int, n_vars: int, config: C40Config) -> ExactGF2Analysis:
    if method == "c15_exhaustive":
        return analyze_exact_gf2(bits, n_vars, max_partitions=config.max_partitions)
    if method == "c16_screened":
        return analyze_screened_exact_gf2(
            bits, n_vars, max_partitions=config.max_partitions, materialize_budget=config.materialize_budget
        )
    raise ValueError("unknown C40 analysis method")


def _best_document(analysis: ExactGF2Analysis) -> dict[str, Any] | None:
    return analysis.best.to_dict() if analysis.best is not None else None


def _functional_rows(cases: Mapping[str, tuple[int, int]], config: C40Config
                     ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    for case_id, (bits, n_vars) in sorted(cases.items()):
        exhaustive = _analyze("c15_exhaustive", bits, n_vars, config)
        screened = _analyze("c16_screened", bits, n_vars, config)
        rows.append({
            "case_id": case_id,
            "n_vars": n_vars,
            "exact_best_identity_match": _best_document(exhaustive) == _best_document(screened),
            "exhaustive_exact": all(item.reconstruct() == bits for item in exhaustive.candidates),
            "screened_exact": all(item.reconstruct() == bits for item in screened.candidates),
            "exhaustive_candidate_count": len(exhaustive.candidates),
            "screened_unique_descriptors": screened.descriptors_screened,
            "screened_artifacts_materialized": screened.artifacts_materialized,
            "best_digest": screened.best.digest if screened.best else None,
        })
    controls = []
    for row in make_gf2_controls(config.seed):
        kwargs = {"row_partitions": row["row_partitions"]} if row["row_partitions"] else {"max_partitions": 32}
        exhaustive = analyze_exact_gf2(row["bits"], row["n_vars"], **kwargs)
        screened = analyze_screened_exact_gf2(
            row["bits"], row["n_vars"], materialize_budget=config.materialize_budget, **kwargs
        )
        controls.append({
            "case_id": row["case_id"],
            "required_kind": row["required_kind"],
            "exact_best_identity_match": _best_document(exhaustive) == _best_document(screened),
            "screened_exact": all(item.reconstruct() == row["bits"] for item in screened.candidates),
            "required_kind_recovered": (row["required_kind"] in screened.kinds
                                        if row["required_kind"] else not screened.candidates),
        })
    return rows, controls


def _primary_measurements(freeze: Mapping[str, Any], cases: Mapping[str, tuple[int, int]],
                          config: C40Config, started: float) -> list[dict[str, Any]]:
    rows = []
    for planned in freeze["primary_schedule"]:
        if time.perf_counter() - started > config.max_wall_seconds:
            raise TimeoutError("C40 primary benchmark exceeded wall budget")
        bits, n_vars = cases[planned["case_id"]]
        measured = time.perf_counter_ns()
        analysis = _analyze(planned["method"], bits, n_vars, config)
        rows.append({
            "schema": "crse-c40-gf2-primary-measurement/v1",
            **planned,
            "n_vars": n_vars,
            "analysis_ns": max(1, time.perf_counter_ns() - measured),
            "partitions_tested": analysis.partitions_tested,
            "descriptors_screened": analysis.descriptors_screened,
            "artifacts_materialized": analysis.artifacts_materialized,
            "candidate_count": len(analysis.candidates),
            "best_digest": analysis.best.digest if analysis.best else None,
        })
    return rows


class _PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def _windows_process_memory() -> dict[str, int]:
    """Read Windows process counters without a third-party package."""
    if os.name != "nt":
        raise RuntimeError("C40 cold-memory worker currently requires Windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.argtypes = ()
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = (
        wintypes.HANDLE, ctypes.POINTER(_PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD,
    )
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    process = kernel32.GetCurrentProcess()
    counters = _PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(counters)
    ok = psapi.GetProcessMemoryInfo(
        process, ctypes.byref(counters), ctypes.sizeof(counters)
    )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "working_set_bytes": int(counters.WorkingSetSize),
        "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
        "private_usage_bytes": int(counters.PrivateUsage),
        "peak_pagefile_usage_bytes": int(counters.PeakPagefileUsage),
    }


def _cold_memory_worker(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Run exactly one analysis after a cold-child baseline and report peaks."""
    if set(payload) != {"method", "bits_hex", "n_vars", "config"}:
        raise ValueError("invalid C40 memory worker payload")
    config = C40Config(**payload["config"])
    config.validate()
    method, bits, n_vars = payload["method"], int(payload["bits_hex"], 16), payload["n_vars"]
    if method not in METHODS or type(n_vars) is not int:
        raise ValueError("invalid C40 memory worker analysis request")
    if truth_sha256(bits, n_vars) != truth_sha256(bits, n_vars):
        raise RuntimeError("unreachable truth identity failure")
    gc.collect()
    before = _windows_process_memory()
    sampled_peak = before["working_set_bytes"]
    stop = threading.Event()

    def sample() -> None:
        nonlocal sampled_peak
        while not stop.wait(0.001):
            sampled_peak = max(sampled_peak, _windows_process_memory()["working_set_bytes"])

    monitor = threading.Thread(target=sample, daemon=True)
    tracemalloc.start()
    monitor.start()
    started = time.perf_counter_ns()
    try:
        analysis = _analyze(method, bits, n_vars, config)
    finally:
        elapsed_ns = max(1, time.perf_counter_ns() - started)
        stop.set()
        monitor.join(timeout=2.0)
        current_python, peak_python = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    after = _windows_process_memory()
    sampled_peak = max(sampled_peak, after["working_set_bytes"])
    return {
        "schema": MEMORY_WORKER_SCHEMA,
        "method": method,
        "n_vars": n_vars,
        "truth_sha256": truth_sha256(bits, n_vars),
        "analysis_ns": elapsed_ns,
        "best_digest": analysis.best.digest if analysis.best else None,
        "analysis": {
            "partitions_tested": analysis.partitions_tested,
            "descriptors_screened": analysis.descriptors_screened,
            "artifacts_materialized": analysis.artifacts_materialized,
            "candidate_count": len(analysis.candidates),
        },
        "memory": {
            "platform_metric": "Windows PROCESS_MEMORY_COUNTERS_EX",
            "baseline_after_imports_and_gc": before,
            "final": after,
            "sampled_working_set_peak_bytes": sampled_peak,
            "delta_peak_working_set_bytes": max(0, after["peak_working_set_bytes"] - before["peak_working_set_bytes"]),
            "delta_sampled_working_set_bytes": max(0, sampled_peak - before["working_set_bytes"]),
            "delta_final_working_set_bytes": after["working_set_bytes"] - before["working_set_bytes"],
            "delta_private_usage_bytes": after["private_usage_bytes"] - before["private_usage_bytes"],
            "tracemalloc_current_bytes": current_python,
            "tracemalloc_peak_bytes": peak_python,
            "sampling_interval_ms": 1,
        },
    }


def _worker_payload(method: str, bits: int, n_vars: int, config: C40Config) -> str:
    raw = _canonical({"method": method, "bits_hex": hex(bits), "n_vars": n_vars, "config": asdict(config)})
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _run_memory_worker(method: str, bits: int, n_vars: int, config: C40Config) -> tuple[dict[str, Any], int, str, str]:
    payload = _worker_payload(method, bits, n_vars, config)
    command = [sys.executable, "-B", "-m", "cmbench.recognition.gf2_c40_confirmation_benchmark", "memory-worker", "--payload", payload]
    completed = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        timeout=config.worker_timeout_seconds, check=False,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"C40 memory worker emitted invalid JSON: {completed.stderr.strip()}") from exc
    return result, completed.returncode, completed.stdout, completed.stderr


def _memory_measurements(freeze: Mapping[str, Any], cases: Mapping[str, tuple[int, int]],
                         config: C40Config, started: float) -> list[dict[str, Any]]:
    rows = []
    for planned in freeze["memory_schedule"]:
        if time.perf_counter() - started > config.max_wall_seconds:
            raise TimeoutError("C40 memory benchmark exceeded wall budget")
        bits, n_vars = cases[planned["case_id"]]
        result, returncode, stdout, stderr = _run_memory_worker(planned["method"], bits, n_vars, config)
        valid = (
            returncode == 0
            and result.get("schema") == MEMORY_WORKER_SCHEMA
            and result.get("method") == planned["method"]
            and result.get("n_vars") == n_vars
            and result.get("truth_sha256") == truth_sha256(bits, n_vars)
            and (result.get("best_digest") is None or type(result.get("best_digest")) is str)
        )
        if not valid:
            raise RuntimeError(f"invalid C40 memory worker result for {planned['case_id']}/{planned['method']}: {stderr}")
        rows.append({
            "schema": "crse-c40-gf2-cold-memory-measurement/v1",
            **planned,
            "n_vars": n_vars,
            "returncode": returncode,
            "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
            "worker": result,
        })
    return rows


def _memory_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    metrics = (
        "delta_peak_working_set_bytes", "delta_sampled_working_set_bytes", "delta_final_working_set_bytes",
        "delta_private_usage_bytes", "tracemalloc_peak_bytes",
    )
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["case_id"], row["method"])].append(row)
    medians = {
        (case_id, method): {
            metric: statistics.median(row["worker"]["memory"][metric] for row in values)
            for metric in metrics
        }
        for (case_id, method), values in grouped.items()
    }
    aggregate = {
        method: {
            metric: {
                "sum_case_medians_bytes": int(sum(values[metric] for (case_id, name), values in medians.items() if name == method)),
                "median_case_median_bytes": statistics.median(
                    values[metric] for (case_id, name), values in medians.items() if name == method
                ),
                "max_case_median_bytes": max(values[metric] for (case_id, name), values in medians.items() if name == method),
            }
            for metric in metrics
        }
        for method in METHODS
    }
    best_identity = all(
        grouped[(case_id, "c15_exhaustive")][0]["worker"]["best_digest"]
        == grouped[(case_id, "c16_screened")][0]["worker"]["best_digest"]
        for case_id in sorted({row["case_id"] for row in rows})
    )
    return {
        "cold_processes_per_method_case": len(next(iter(grouped.values()))),
        "case_method_medians": {
            f"{case_id}/{method}": values for (case_id, method), values in sorted(medians.items())
        },
        "aggregate": aggregate,
        "cold_worker_best_identity_match": best_identity,
        "interpretation_limit": "The OS peak-working-set high-water mark is process-wide and may include import-time allocations. The paired cold-worker baseline and Python tracemalloc peak are reported alongside it; only raw measurements support detailed interpretation.",
    }


def _summary(primary: list[Mapping[str, Any]], memory: list[Mapping[str, Any]],
             functional: list[Mapping[str, Any]], controls: list[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in primary:
        grouped[(row["case_id"], row["method"])].append(row["analysis_ns"])
    case_ids = sorted({row["case_id"] for row in primary})
    totals = {
        method: sum(statistics.median(grouped[(case_id, method)]) for case_id in case_ids)
        for method in METHODS
    }
    return {
        "primary_median_case_sum_ns": {method: int(value) for method, value in totals.items()},
        "screened_over_exhaustive_speedup": totals["c15_exhaustive"] / totals["c16_screened"],
        "functional": {
            "public_cases_exact_best_identity": all(row["exact_best_identity_match"] for row in functional),
            "public_cases_exact_reconstruction": all(row["exhaustive_exact"] and row["screened_exact"] for row in functional),
            "controls_exact_best_identity": all(row["exact_best_identity_match"] for row in controls),
            "controls_expected_behavior": all(row["required_kind_recovered"] for row in controls),
        },
        "memory": _memory_summary(memory),
    }


def run_benchmark(*, project_root: str | Path, freeze_path: str | Path, output: str | Path) -> dict[str, Any]:
    """Verify a C40 pre-analysis freeze then run functional, time, and memory lanes."""
    root = Path(project_root).resolve()
    freeze_file = Path(freeze_path)
    if not freeze_file.is_absolute():
        freeze_file = root / freeze_file
    output_path = Path(output)
    freeze = json.loads(freeze_file.read_text(encoding="utf-8"))
    config = C40Config(**freeze["config"])
    verification = verify_freeze(freeze, root)
    if not verification["verified"]:
        raise ValueError("C40 freeze verification failed before analysis")
    output_path.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    cases = _load_cases(freeze, root)
    functional, controls = _functional_rows(cases, config)
    primary = _primary_measurements(freeze, cases, config, started)
    memory = _memory_measurements(freeze, cases, config, started)
    summary = _summary(primary, memory, functional, controls)
    status = "complete" if all(summary["functional"].values()) and summary["memory"]["cold_worker_best_identity_match"] else "failed"
    result = {
        "schema": RUN_SCHEMA,
        "status": status,
        "freeze_path": _relative(root, freeze_file),
        "freeze_sha256": freeze["freeze_sha256"],
        "config": asdict(config),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "thread_environment": {name: os.environ.get(name) for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        },
        "wall_seconds": time.perf_counter() - started,
        "summary": summary,
    }
    _write_json_x(output_path / "freeze_verification.json", verification)
    _write_json_x(output_path / "functional.json", {"public_cases": functional, "controls": controls})
    _write_jsonl_x(output_path / "primary_measurements.jsonl", primary)
    _write_jsonl_x(output_path / "memory_measurements.jsonl", memory)
    _write_json_x(output_path / "results.json", result)
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    freeze = subparsers.add_parser("freeze", help="create immutable C40 Boolean Function Suite selection")
    freeze.add_argument("--project-root", type=Path, default=ROOT)
    freeze.add_argument("--output", type=Path, required=True)
    run = subparsers.add_parser("run", help="verify and execute C40 freeze")
    run.add_argument("--project-root", type=Path, default=ROOT)
    run.add_argument("--freeze", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    worker = subparsers.add_parser("memory-worker", help="internal cold-process memory worker")
    worker.add_argument("--payload", required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.command == "freeze":
        freeze = build_freeze(project_root=args.project_root, config=C40Config())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        _write_json_x(args.output, freeze)
        print(f"wrote frozen C40 confirmation corpus: {args.output}")
    elif args.command == "run":
        result = run_benchmark(project_root=args.project_root, freeze_path=args.freeze, output=args.output)
        print(json.dumps({"status": result["status"], "speedup": result["summary"]["screened_over_exhaustive_speedup"]}, sort_keys=True))
    else:
        payload = json.loads(base64.urlsafe_b64decode(args.payload.encode("ascii")).decode("utf-8"))
        print(json.dumps(_cold_memory_worker(payload), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
