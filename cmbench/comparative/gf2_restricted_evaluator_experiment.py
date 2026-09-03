"""Development-only R0/R1/R2 restricted-evaluator experiment and re-oracle.

The experiment deliberately reuses the exposed C36 corpus.  It is not C37,
does not fit or promote a selector, and includes the existing CSE, CM-IR, and
projection arms only to recompute the exact backend oracle after repairing the
direct evaluator comparison.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
import ctypes
import hashlib
import importlib.metadata
import json
import math
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

from bitset_backend import (
    bitset_to_bool_array,
    build_bitset_env,
    eval_cm_node_words,
    eval_expr_bitset,
    eval_expr_words_cse,
    get_expr_cse_program,
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json
from cm_ir import compile_expr_to_cm_ir

from .contracts import canonical_bytes
from .gf2_restricted_evaluators import (
    RESTRICTED_METHODS,
    RestrictedArena,
    arena_structural_profile,
    compile_restricted_arena,
    eval_restricted_r0,
    eval_restricted_r1,
    eval_restricted_r2,
    method_work_counters,
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


SCHEMA = "crse-restricted-evaluator-development/v1"
METHODS = RESTRICTED_METHODS + (
    "flattened_cse_words",
    "cm_ir_words",
    "compiled_truth_projection",
)
OPTIMIZED_METHODS = METHODS[1:]
RAW_SCHEMA = "crse-restricted-evaluator-raw-session/v1"
MANIFEST_SCHEMA = "crse-restricted-evaluator-manifest/v1"

REQUIRED_SOURCE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_restricted_evaluators.py",
    "cmbench/comparative/gf2_restricted_evaluator_experiment.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "cmbench/comparative/schedule.py",
    "cmbench/recognition/yosys_wide_restriction_data.py",
    "scripts/cm_comparative_restricted_evaluator_development.py",
    "scripts/crse_restricted_evaluator_development_verify.py",
    "scripts/crse_verify_c36_wide_repeated_query_dataset.py",
    "docs/recognition/c36_wide_repeated_query_dataset.json",
    "docs/recognition/c36_wide_repeated_query_dataset_verification.json",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-research-ci.txt",
)


@dataclass(frozen=True)
class RestrictedEvaluatorConfig:
    run_id: str
    seed: int = 20260902
    blocks: int = 12
    checkpoints: tuple[int, ...] = CHECKPOINTS
    high_expansion_threshold: int = 10
    max_seconds: float = 900.0

    def validate(self) -> None:
        if (
            not self.run_id
            or self.blocks != len(balanced_orders(METHODS))
            or tuple(self.checkpoints) != CHECKPOINTS
            or self.high_expansion_threshold != 10
            or type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or not 60 <= self.max_seconds <= 1800
        ):
            raise ValueError("invalid restricted-evaluator development bounds")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False) + "\n")


def _git_value(root: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL,
            timeout=10,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _rss_snapshot() -> tuple[int | None, int | None]:
    """Return current RSS and process high-water RSS when the OS exposes them."""
    if os.name == "nt":
        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            get_current_process = kernel32.GetCurrentProcess
            get_current_process.argtypes = []
            get_current_process.restype = ctypes.c_void_p
            get_process_memory_info = psapi.GetProcessMemoryInfo
            get_process_memory_info.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(_ProcessMemoryCounters),
                ctypes.c_ulong,
            ]
            get_process_memory_info.restype = ctypes.c_int
            ok = get_process_memory_info(
                get_current_process(),
                ctypes.byref(counters),
                counters.cb,
            )
        except (AttributeError, OSError):
            return None, None
        if not ok:
            return None, None
        return int(counters.WorkingSetSize), int(counters.PeakWorkingSetSize)
    current = None
    try:
        statm = Path("/proc/self/statm").read_text(encoding="ascii").split()
        current = int(statm[1]) * int(os.sysconf("SC_PAGE_SIZE"))
    except (OSError, ValueError, IndexError, AttributeError):
        pass
    peak = None
    try:
        import resource
        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        peak = value if sys.platform == "darwin" else value * 1024
    except (ImportError, OSError, ValueError):
        pass
    return current, peak


def build_schedule(
    cases: Sequence[Mapping[str, Any]], blocks: int, seed: int,
) -> list[dict[str, Any]]:
    orders = balanced_orders(METHODS)
    if blocks != len(orders):
        raise ValueError("development schedule requires one counterbalance cycle")
    rows: list[dict[str, Any]] = []
    for block in range(blocks):
        ordered = list(cases)
        random.Random(f"restricted-evaluator:{seed}:{block}").shuffle(ordered)
        order = orders[(block + seed) % len(orders)]
        for position, case in enumerate(ordered):
            core = {
                "block": block,
                "case_position": position,
                "case_id": case["case_id"],
                "family": case["family"],
                "n_vars": case["n_vars"],
                "method_order": list(order),
            }
            core["order_sha256"] = _digest(core)
            rows.append(core)
    return rows


def validate_schedule(
    rows: Sequence[Mapping[str, Any]], cases: Sequence[Mapping[str, Any]], blocks: int,
) -> None:
    if len(rows) != len(cases) * blocks:
        raise ValueError("development schedule cardinality")
    case_ids = {case["case_id"] for case in cases}
    for row in rows:
        core = {key: row[key] for key in (
            "block", "case_position", "case_id", "family", "n_vars", "method_order")}
        if (
            row.get("order_sha256") != _digest(core)
            or row["case_id"] not in case_ids
            or set(row["method_order"]) != set(METHODS)
        ):
            raise ValueError("development schedule identity")
    for case_id in case_ids:
        selected = [row for row in rows if row["case_id"] == case_id]
        if Counter(row["block"] for row in selected) != Counter(range(blocks)):
            raise ValueError("development case/block balance")
        for method in METHODS:
            positions = Counter(row["method_order"].index(method) for row in selected)
            if positions != Counter({index: 2 for index in range(len(METHODS))}):
                raise ValueError("development arm-position balance")


def _sample_rss(samples: list[int], process_peaks: list[int]) -> None:
    current, peak = _rss_snapshot()
    if current is not None:
        samples.append(current)
    if peak is not None:
        process_peaks.append(peak)


def execute_session(
    *,
    case: Mapping[str, Any],
    method: str,
    structural_profile: Mapping[str, Any],
    role: str,
    clock: Callable[[], int] = time.perf_counter_ns,
    profile_python_allocations: bool = False,
) -> dict[str, Any]:
    """Execute all 64 exact C36 queries with explicit stage measurements."""
    normalized = validate_wide_case(case)
    if method not in METHODS or role not in ("performance", "memory_profile"):
        raise ValueError("invalid development session")
    trace = validate_query_trace(
        case.get("c36_trace"), normalized["case_id"], normalized["n_vars"])
    expected_document = oracle_document(case, trace)
    expected_digest = _digest(expected_document)
    if expected_digest != case.get("c36_required_output_sha256"):
        raise ValueError("development oracle binding")

    if profile_python_allocations:
        tracemalloc.start()
    rss_samples: list[int] = []
    process_peaks: list[int] = []
    _sample_rss(rss_samples, process_peaks)
    task_started = clock()
    started = clock()
    expression = expr_from_json(case["expression_v2"])
    input_decode_ns = max(1, clock() - started)
    _sample_rss(rss_samples, process_peaks)

    arena: RestrictedArena | None = None
    node = program = truth_vector = plans = None
    resources: dict[str, Any] = {}
    started = clock()
    if method == RESTRICTED_METHODS[2]:
        arena = compile_restricted_arena(case["expression_v2"])
        resources.update(method_work_counters(method, structural_profile))
        resources["arena_nodes"] = arena.node_count
    elif method == "flattened_cse_words":
        program = get_expr_cse_program(expression, flatten=True)
        resources.update(program_metrics(program))
    elif method == "cm_ir_words":
        node = compile_expr_to_cm_ir(
            expression, reuse_cache=False, persistent_cache=False,
            share_aware_flatten=True)
        program = get_flat_program(node)
        resources.update(program_metrics(program))
    elif method == "compiled_truth_projection":
        names = tuple(f"x{i}" for i in range(normalized["n_vars"]))
        full_bits = eval_expr_bitset(expression, build_bitset_env(names))
        truth_vector = bitset_to_bool_array(full_bits, normalized["n_vars"])
        plans = []
        for query in trace:
            fixed = {row["variable"]: row["value"] for row in query["fixed"]}
            plans.append(projection_indices(
                normalized["n_vars"], fixed, query["remaining_order"]))
        resources.update({
            "materialized_truth_bits": 1 << normalized["n_vars"],
            "compiled_projection_index_bytes": sum(plan.nbytes for plan in plans),
        })
    elif method in RESTRICTED_METHODS:
        resources.update(method_work_counters(method, structural_profile))
    representation_ns = max(1, clock() - started)
    _sample_rss(rss_samples, process_peaks)

    rows: list[dict[str, Any]] = []
    query_timings: list[dict[str, int]] = []
    checkpoint_query_ns: dict[str, int] = {}
    cumulative_query_ns = 0
    for index, query in enumerate(trace):
        started = clock()
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        remaining = tuple(query["remaining_order"])
        prepared = (prepare_restriction(fixed, remaining)
                    if method in RESTRICTED_METHODS else None)
        restriction_setup_ns = max(1, clock() - started)

        started = clock()
        if method == RESTRICTED_METHODS[0]:
            reduced = eval_restricted_r0(expression, prepared)
        elif method == RESTRICTED_METHODS[1]:
            reduced = eval_restricted_r1(expression, prepared)
        elif method == RESTRICTED_METHODS[2]:
            if arena is None:
                raise AssertionError("R2 arena was not compiled")
            reduced = eval_restricted_r2(arena, prepared)
        elif method == "flattened_cse_words":
            reduced = eval_expr_words_cse(
                expression, remaining, fixed=fixed, flatten=True)
        elif method == "cm_ir_words":
            reduced = eval_cm_node_words(node, remaining, fixed=fixed)
        else:
            reduced = project_truth_vector(truth_vector, plans[index])
        evaluation_ns = max(1, clock() - started)

        started = clock()
        semantic = semantic_row(query, int(reduced), normalized["n_vars"])
        row_digest = _digest(semantic)
        delivery_ns = max(1, clock() - started)
        rows.append(semantic)
        query_total = restriction_setup_ns + evaluation_ns + delivery_ns
        cumulative_query_ns += query_total
        query_timings.append({
            "query": index,
            "restriction_setup_ns": restriction_setup_ns,
            "evaluation_ns": evaluation_ns,
            "delivery_ns": delivery_ns,
            "total_ns": query_total,
            "output_sha256": row_digest,
        })
        if index + 1 in CHECKPOINTS:
            checkpoint_query_ns[str(index + 1)] = cumulative_query_ns
        _sample_rss(rss_samples, process_peaks)

    started = clock()
    expression = arena = node = program = truth_vector = plans = None
    cleanup_ns = max(1, clock() - started)
    _sample_rss(rss_samples, process_peaks)
    document = semantic_document(normalized["case_id"], rows)
    actual_digest = _digest(document)
    if actual_digest != expected_digest:
        raise RuntimeError(f"{method} failed exact canonical delivery equality")
    task_total_ns = max(1, clock() - task_started)
    accounted_ns = (input_decode_ns + representation_ns + cumulative_query_ns
                    + cleanup_ns)
    checkpoint_total_ns = {
        key: input_decode_ns + representation_ns + value + cleanup_ns
        for key, value in checkpoint_query_ns.items()
    }
    resources.update({
        "session_sampled_start_rss_bytes": rss_samples[0] if rss_samples else None,
        "session_sampled_peak_rss_bytes": max(rss_samples) if rss_samples else None,
        "session_sampled_peak_rss_delta_bytes": (
            max(rss_samples) - rss_samples[0] if rss_samples else None),
        "process_peak_rss_bytes": max(process_peaks) if process_peaks else None,
        "rss_sampling_points": len(rss_samples),
    })
    if profile_python_allocations:
        _current_python_bytes, peak_python_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        resources["tracemalloc_peak_bytes"] = int(peak_python_bytes)
    return {
        "schema": RAW_SCHEMA,
        "role": role,
        "case_id": normalized["case_id"],
        "family": case["family"],
        "n_vars": normalized["n_vars"],
        "method": method,
        "status": "ok",
        "timings_ns": {
            "input_decode_ns": input_decode_ns,
            "representation_ns": representation_ns,
            "restriction_setup_ns": sum(
                row["restriction_setup_ns"] for row in query_timings),
            "evaluation_ns": sum(row["evaluation_ns"] for row in query_timings),
            "delivery_ns": sum(row["delivery_ns"] for row in query_timings),
            "query_total_ns": cumulative_query_ns,
            "cleanup_ns": cleanup_ns,
            "accounted_total_ns": accounted_ns,
            "observed_task_wall_ns": task_total_ns,
        },
        "checkpoint_query_ns": checkpoint_query_ns,
        "checkpoint_total_ns": checkpoint_total_ns,
        "query_measurements": query_timings,
        "artifact_sha256": actual_digest,
        "artifact_bytes": len(canonical_bytes(document)),
        "resources": resources,
        "structural_profile": dict(structural_profile),
        "exact_check_passed": True,
    }


def _performance_medians(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[tuple[str, str, int], int], list[str]]:
    values: dict[tuple[str, str, int], list[int]] = {}
    cases = sorted({str(row["case_id"]) for row in rows if row["role"] == "performance"})
    for row in rows:
        if row["role"] != "performance":
            continue
        for checkpoint in CHECKPOINTS:
            values.setdefault((row["case_id"], row["method"], checkpoint), []).append(
                int(row["checkpoint_total_ns"][str(checkpoint)]))
    medians = {key: int(statistics.median(samples)) for key, samples in values.items()}
    if len(medians) != len(cases) * len(METHODS) * len(CHECKPOINTS):
        raise ValueError("incomplete development performance medians")
    return medians, cases


def _subgroup_summary(
    selected: Sequence[str], medians: Mapping[tuple[str, str, int], int], checkpoint: int,
) -> dict[str, Any]:
    totals = {method: sum(medians[(case, method, checkpoint)] for case in selected)
              for method in METHODS}
    optimized_totals = {method: totals[method] for method in OPTIMIZED_METHODS}
    return {
        "cases": len(selected),
        "method_total_ns": totals,
        "best_method": min(METHODS, key=lambda method: (totals[method], method)),
        "best_optimized_method": min(
            OPTIMIZED_METHODS, key=lambda method: (optimized_totals[method], method)),
    }


def summarize(
    rows: Sequence[Mapping[str, Any]], profiles: Mapping[str, Mapping[str, Any]],
    high_expansion_threshold: int,
) -> dict[str, Any]:
    medians, cases = _performance_medians(rows)
    metadata = {row["case_id"]: (row["family"], row["n_vars"])
                for row in rows if row["role"] == "performance"}
    checkpoints: dict[str, Any] = {}
    for checkpoint in CHECKPOINTS:
        totals = {method: sum(medians[(case, method, checkpoint)] for case in cases)
                  for method in METHODS}
        best = min(METHODS, key=lambda method: (totals[method], method))
        optimized_best = min(
            OPTIMIZED_METHODS, key=lambda method: (totals[method], method))
        winners = {
            case: min(METHODS, key=lambda method: (medians[(case, method, checkpoint)], method))
            for case in cases
        }
        optimized_winners = {
            case: min(OPTIMIZED_METHODS,
                      key=lambda method: (medians[(case, method, checkpoint)], method))
            for case in cases
        }
        oracle_total = sum(medians[(case, winners[case], checkpoint)] for case in cases)
        optimized_oracle_total = sum(
            medians[(case, optimized_winners[case], checkpoint)] for case in cases)
        checkpoints[str(checkpoint)] = {
            "method_total_ns": totals,
            "best_fixed_method": best,
            "best_optimized_fixed_method": optimized_best,
            "per_case_winners": winners,
            "per_case_optimized_winners": optimized_winners,
            "per_case_oracle_total_ns": oracle_total,
            "per_case_optimized_oracle_total_ns": optimized_oracle_total,
            "oracle_speedup_over_best_fixed": totals[best] / oracle_total,
            "optimized_oracle_speedup_over_best_optimized_fixed": (
                totals[optimized_best] / optimized_oracle_total),
            "r1_speedup_over_r0": (
                totals[RESTRICTED_METHODS[0]] / totals[RESTRICTED_METHODS[1]]),
            "r2_speedup_over_r0": (
                totals[RESTRICTED_METHODS[0]] / totals[RESTRICTED_METHODS[2]]),
            "r2_speedup_over_r1": (
                totals[RESTRICTED_METHODS[1]] / totals[RESTRICTED_METHODS[2]]),
        }

    by_width: dict[str, Any] = {}
    for width in sorted({width for _family, width in metadata.values()}):
        selected = [case for case in cases if metadata[case][1] == width]
        by_width[str(width)] = _subgroup_summary(selected, medians, 64)
    by_family: dict[str, Any] = {}
    for family in sorted({family for family, _width in metadata.values()}):
        selected = [case for case in cases if metadata[case][0] == family]
        by_family[family] = _subgroup_summary(selected, medians, 64)
    high_cases = [case for case in cases if (
        int(profiles[case]["unfolded_visits"])
        > high_expansion_threshold * int(profiles[case]["unique_nodes"]))]
    low_cases = [case for case in cases if case not in set(high_cases)]
    by_expansion = {
        "low_or_equal_10": _subgroup_summary(low_cases, medians, 64),
        "high_over_10": _subgroup_summary(high_cases, medians, 64),
        "threshold_role": "historical_descriptive_subgroup_only_not_a_policy",
    }
    memory_rows = [row for row in rows if row["role"] == "memory_profile"]
    memory: dict[str, Any] = {}
    for method in METHODS:
        selected = [row for row in memory_rows if row["method"] == method]
        memory[method] = {
            "profile_sessions": len(selected),
            "max_session_sampled_peak_rss_delta_bytes": max(
                (row["resources"]["session_sampled_peak_rss_delta_bytes"] or 0)
                for row in selected),
            "max_tracemalloc_peak_bytes": max(
                row["resources"].get("tracemalloc_peak_bytes", 0) for row in selected),
            "max_process_peak_rss_bytes": max(
                (row["resources"]["process_peak_rss_bytes"] or 0) for row in selected),
        }
    final = checkpoints["64"]
    r1_work_reduction = sum(
        int(profiles[case]["unfolded_visits"]) for case in cases) / sum(
        int(profiles[case]["unique_nodes"]) for case in cases)
    return {
        "cases": len(cases),
        "performance_sessions": sum(row["role"] == "performance" for row in rows),
        "memory_profile_sessions": len(memory_rows),
        "timed_queries": sum(
            len(row["query_measurements"]) for row in rows
            if row["role"] == "performance"),
        "checkpoints": checkpoints,
        "by_width_at_q64": by_width,
        "by_family_at_q64": by_family,
        "by_expansion_at_q64": by_expansion,
        "memory_profiles": memory,
        "complexity": {
            "aggregate_r0_to_r1_node_evaluation_reduction": r1_work_reduction,
            "all_r1_node_evaluations_bounded_by_unique_nodes": True,
            "all_r2_node_evaluations_equal_unique_nodes": True,
            "all_r2_peak_live_slots_bounded_by_unique_nodes": True,
        },
        "decision": {
            "finding_supported_by_q64_timing": final["r1_speedup_over_r0"] > 1.0,
            "fastest_repaired_direct_method": min(
                RESTRICTED_METHODS[1:],
                key=lambda method: (final["method_total_ns"][method], method)),
            "best_recomputed_fixed_backend": final["best_fixed_method"],
            "best_recomputed_optimized_fixed_backend": (
                final["best_optimized_fixed_method"]),
            "optimized_per_case_oracle_speedup": (
                final["optimized_oracle_speedup_over_best_optimized_fixed"]),
            "formal_c37_or_production_promotion_permitted": False,
        },
        "timing_is_local_and_machine_specific": True,
        "memory_timing_excluded_from_performance_summary": True,
    }


def render_protocol(
    config: RestrictedEvaluatorConfig, dataset_path: Path,
    dataset_verification_path: Path, root: Path,
) -> str:
    return "\n".join([
        "# Restricted evaluator development protocol",
        "",
        f"Run ID: `{config.run_id}`",
        "",
        "Status: development-only, exposed C36 data; not prospective C37 evidence.",
        "",
        "The exact C36 task contract is unchanged: each of 64 restrictions must emit",
        "the reduced relation, relation digest, exact count, SAT status, and canonical",
        "witness in the frozen remaining-variable order.",
        "",
        "Compared arms: R0 occurrence recursion, R1 query-local identity memoization,",
        "R2 topological DAG-v2 slots with last-use release, flattened CSE words, CM-IR",
        "words, and compiled full-truth projection.",
        "",
        f"Dataset: `{dataset_path.relative_to(root).as_posix()}`",
        f"Dataset verification: `{dataset_verification_path.relative_to(root).as_posix()}`",
        f"Counterbalanced blocks: {config.blocks}; seed: {config.seed}.",
        "",
        "Performance rows run without tracemalloc. Separate memory-profile rows run once",
        "per case/arm with tracemalloc and are excluded from performance aggregation.",
        "RSS is sampled at stage boundaries; process peak RSS is an OS high-water mark.",
        "R0 remains available unchanged in the C36 module; its development control only",
        "splits environment construction from the same recursive gate evaluation.",
        "",
        "No threshold is fitted, no confirmation data is consumed, and no production",
        "write or promotion is authorized by this run.",
        "",
    ])


def render_report(result: Mapping[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Restricted evaluator development result",
        "",
        f"Status: **{result['status']}**",
        "",
        "All six methods produced byte-identical canonical C36 deliveries with zero",
        "relation, count, SAT, or witness mismatches.",
        "",
        "| Q | Best fixed | R1 vs R0 | R2 vs R0 | R2 vs R1 |",
        "|---:|---|---:|---:|---:|",
    ]
    for checkpoint in CHECKPOINTS:
        row = summary["checkpoints"][str(checkpoint)]
        lines.append(
            f"| {checkpoint} | {row['best_fixed_method']} | "
            f"{row['r1_speedup_over_r0']:.4f}x | {row['r2_speedup_over_r0']:.4f}x | "
            f"{row['r2_speedup_over_r1']:.4f}x |")
    final = summary["checkpoints"]["64"]
    decision = summary["decision"]
    high = summary["by_expansion_at_q64"]["high_over_10"]
    lines += [
        "",
        "## Measured conclusion",
        "",
        f"The memoization finding is **{'supported' if decision['finding_supported_by_q64_timing'] else 'not supported'}** "
        f"on this development run. The fastest repaired direct arm is "
        f"`{decision['fastest_repaired_direct_method']}`.",
        "",
        f"The recomputed q64 best fixed backend is `{final['best_fixed_method']}`. "
        f"The optimized per-case oracle retains {decision['optimized_per_case_oracle_speedup']:.4f}x "
        "headroom over the best optimized fixed backend.",
        "",
        f"The descriptive high-expansion subgroup contains {high['cases']} cases and its "
        f"best optimized arm is `{high['best_optimized_method']}`. This is exposed-data "
        "diagnosis, not a frozen routing policy.",
        "",
        "Memory-profile timings were excluded from performance aggregates. RSS values are",
        "stage-boundary samples plus the process-wide high-water mark; tracemalloc reports",
        "Python allocations for the separate profile sessions.",
        "",
        "No C37 or production promotion is permitted by this result.",
        "",
    ]
    return "\n".join(lines)


def source_fingerprints(root: Path, relative_paths: Sequence[str]) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for relative in sorted(set(relative_paths)):
        path = root.joinpath(*Path(relative).parts).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise FileNotFoundError(f"manifest source is missing or escaped: {relative}")
        fingerprints[relative] = _sha256(path)
    return fingerprints


def collect_reproducibility_manifest(
    root: Path, artifacts: Mapping[str, str], extra_sources: Sequence[str] = (),
) -> dict[str, Any]:
    local_paths = set(REQUIRED_SOURCE_PATHS) | set(extra_sources)
    native_modules: dict[str, dict[str, str]] = {}
    root_resolved = root.resolve()
    for name, module in sorted(sys.modules.items()):
        raw = getattr(module, "__file__", None)
        if not raw:
            continue
        try:
            path = Path(raw).resolve()
        except (OSError, RuntimeError):
            continue
        if not path.is_file():
            continue
        if path.is_relative_to(root_resolved):
            local_paths.add(path.relative_to(root_resolved).as_posix())
        elif path.suffix.lower() in (".pyd", ".so", ".dll", ".dylib"):
            native_modules[name] = {"path": str(path), "sha256": _sha256(path)}
    executable = Path(sys.executable).resolve()
    return {
        "schema": MANIFEST_SCHEMA,
        "local_sources": source_fingerprints(root, tuple(local_paths)),
        "native_modules": native_modules,
        "interpreter": {"path": str(executable), "sha256": _sha256(executable)},
        "artifacts": dict(sorted(artifacts.items())),
        "closure_method": (
            "required performance/verifier sources plus all loaded project modules; "
            "all loaded native extension modules; interpreter executable"),
    }


def _environment(
    root: Path, dataset_path: Path, dataset_verification_path: Path,
) -> dict[str, Any]:
    status = _git_value(root, "status", "--short", "--untracked-files=all")
    dependencies = {}
    for package in ("numpy", "pytest"):
        try:
            dependencies[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            dependencies[package] = None
    current_rss, process_peak = _rss_snapshot()
    return {
        "schema": "crse-restricted-evaluator-environment/v1",
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "dependencies": dependencies,
        "git": {
            "head": _git_value(root, "rev-parse", "HEAD"),
            "dirty": bool(status),
            "changed_path_count": len(status.splitlines()) if status else 0,
        },
        "dataset": {
            "path": dataset_path.relative_to(root).as_posix(),
            "sha256": _sha256(dataset_path),
            "verification_path": dataset_verification_path.relative_to(root).as_posix(),
            "verification_sha256": _sha256(dataset_verification_path),
            "classification": "development_exposed_c36_not_confirmation",
        },
        "rss_at_environment_capture_bytes": current_rss,
        "process_peak_rss_at_environment_capture_bytes": process_peak,
    }


def run(
    config: RestrictedEvaluatorConfig,
    output: Path,
    dataset_path: Path,
    dataset_verification_path: Path,
    root: Path,
    *,
    progress: Callable[[str, int, int, str], None] | None = None,
) -> dict[str, Any]:
    config.validate()
    wall_started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    protocol = render_protocol(config, dataset_path, dataset_verification_path, root)
    (output / "protocol.md").write_text(protocol, encoding="utf-8", newline="\n")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    dataset_verification = json.loads(
        dataset_verification_path.read_text(encoding="utf-8"))
    if (
        dataset_verification.get("status") != "verified"
        or dataset_verification.get("dataset_sha256") != _sha256(dataset_path)
    ):
        raise ValueError("development dataset verification binding")
    validate_dataset(dataset)
    cases = list(dataset["cases"])
    profiles = {
        case["case_id"]: arena_structural_profile(
            compile_restricted_arena(case["expression_v2"]))
        for case in cases
    }
    schedule = build_schedule(cases, config.blocks, config.seed)
    validate_schedule(schedule, cases, config.blocks)
    case_map = {case["case_id"]: case for case in cases}

    rows: list[dict[str, Any]] = []
    for schedule_index, planned in enumerate(schedule):
        case = case_map[planned["case_id"]]
        for method_position, method in enumerate(planned["method_order"]):
            session = execute_session(
                case=case,
                method=method,
                structural_profile=profiles[case["case_id"]],
                role="performance",
            )
            session.update({
                "block": planned["block"],
                "case_position": planned["case_position"],
                "method_position": method_position,
                "method_order": planned["method_order"],
                "order_sha256": planned["order_sha256"],
            })
            rows.append(session)
        if progress is not None:
            progress("performance", schedule_index + 1, len(schedule), case["case_id"])
        if time.perf_counter() - wall_started > config.max_seconds:
            raise TimeoutError("development experiment exceeded wall bound")

    memory_total = len(cases) * len(METHODS)
    memory_index = 0
    for case_index, case in enumerate(cases):
        order = balanced_orders(METHODS)[case_index % len(balanced_orders(METHODS))]
        for method_position, method in enumerate(order):
            session = execute_session(
                case=case,
                method=method,
                structural_profile=profiles[case["case_id"]],
                role="memory_profile",
                profile_python_allocations=True,
            )
            session.update({
                "block": None,
                "case_position": case_index,
                "method_position": method_position,
                "method_order": list(order),
                "order_sha256": _digest({
                    "role": "memory_profile", "case_id": case["case_id"],
                    "method_order": list(order)}),
            })
            rows.append(session)
            memory_index += 1
            if progress is not None:
                progress("memory", memory_index, memory_total, case["case_id"])
        if time.perf_counter() - wall_started > config.max_seconds:
            raise TimeoutError("development experiment exceeded wall bound")

    _write_jsonl(output / "raw_measurements.jsonl", rows)
    summary = summarize(rows, profiles, config.high_expansion_threshold)
    result = {
        "schema": SCHEMA,
        "status": "complete",
        "run_id": config.run_id,
        "config": {**asdict(config), "checkpoints": list(config.checkpoints)},
        "methods": list(METHODS),
        "dataset": {
            "path": dataset_path.relative_to(root).as_posix(),
            "sha256": _sha256(dataset_path),
            "verification_path": dataset_verification_path.relative_to(root).as_posix(),
            "verification_sha256": _sha256(dataset_verification_path),
            "cases": len(cases),
            "queries_per_case": 64,
            "classification": "development_exposed_c36_not_confirmation",
        },
        "structural_profiles": profiles,
        "summary": summary,
        "correctness": {
            "relation_mismatches": 0,
            "count_mismatches": 0,
            "sat_mismatches": 0,
            "witness_mismatches": 0,
            "canonical_delivery_mismatches": 0,
        },
        "decision": {
            "training_performed": False,
            "threshold_refit": False,
            "prospective_data_consumed": False,
            "production_write": False,
            "production_promotion": False,
        },
        "elapsed_seconds": time.perf_counter() - wall_started,
    }
    _write_json(output / "results.json", result)
    (output / "report.md").write_text(
        render_report(result), encoding="utf-8", newline="\n")
    _write_json(
        output / "environment.json",
        _environment(root, dataset_path, dataset_verification_path),
    )
    artifact_names = (
        "protocol.md", "raw_measurements.jsonl", "environment.json",
        "results.json", "report.md")
    artifacts = {name: _sha256(output / name) for name in artifact_names}
    manifest = collect_reproducibility_manifest(root, artifacts)
    _write_json(output / "manifest.json", manifest)
    return result
