#!/usr/bin/env python3
"""Reproducible core CM performance and correctness benchmark.

The public CLI is intentionally benchmarked separately because its import,
backend-discovery, aggregation, and CSV costs are useful pipeline measurements.
This script isolates CM compilation and explicit-output kernels while retaining
per-repetition wall/CPU time, Python allocation peaks, process memory, GC
activity, deterministic result signatures, and reference-output checks.
"""

from __future__ import annotations

import argparse
import ctypes
import gc
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bitset_backend import bitset_to_bool_array  # noqa: E402
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, eval_expr_tt  # noqa: E402
from cm_ir import compile_expr_to_cm_ir, materialize_cm, materialize_hybrid_no_reinflate  # noqa: E402
from cm_normalize import canonical_layout  # noqa: E402


def _balanced(op: Callable[[Any, Any], Any], leaves: Iterable[Any]) -> Any:
    level = list(leaves)
    if not level:
        raise ValueError("at least one leaf is required")
    while len(level) > 1:
        next_level = []
        iterator = iter(level)
        for left in iterator:
            right = next(iterator, None)
            next_level.append(left if right is None else op(left, right))
        level = next_level
    return level[0]


def _balanced_mixed(n_vars: int) -> Any:
    level = [Var(i) for i in range(n_vars)]
    operators = (And, Or, Xor, Imp, Eqv)
    depth = 0
    while len(level) > 1:
        next_level = []
        iterator = iter(level)
        op = operators[depth % len(operators)]
        for index, left in enumerate(iterator):
            right = next(iterator, None)
            if right is None:
                next_level.append(left)
            else:
                node = op(left, right)
                next_level.append(Not(node) if (index + depth) % 11 == 7 else node)
        level = next_level
        depth += 1
    return level[0]


def _expression(case: dict[str, Any]) -> Any:
    kind = case["kind"]
    width = int(case.get("width", case.get("n_vars", 1)))
    if kind == "compile_and":
        return _balanced(And, (Var(i) for i in range(width)))
    if kind == "compile_or":
        return _balanced(Or, (Var(i) for i in range(width)))
    if kind in {"eval", "dense"}:
        return _balanced_mixed(width)
    if kind == "sparse_ambient":
        live_k = int(case["live_k"])
        return _balanced(Xor, (Var(i) for i in range(live_k)))
    raise ValueError(f"unknown case kind: {kind}")


def _sha256_repr(value: Any) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def _process_memory_bytes() -> tuple[int | None, int | None]:
    """Return current and peak resident bytes without an external dependency."""
    if os.name == "nt":
        class ProcessMemoryCounters(ctypes.Structure):
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

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ProcessMemoryCounters),
            ctypes.c_ulong,
        )
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int
        handle = kernel32.GetCurrentProcess()
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return None, None
        return int(counters.WorkingSetSize), int(counters.PeakWorkingSetSize)

    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        scale = 1024 if sys.platform != "darwin" else 1
        peak = int(usage.ru_maxrss) * scale
        return None, peak
    except (ImportError, OSError):
        return None, None


def _gc_collections() -> int:
    return sum(int(generation["collections"]) for generation in gc.get_stats())


def _result_to_array(result: Any, n_vars: int) -> np.ndarray:
    if result.bits is not None:
        return bitset_to_bool_array(int(result.bits), n_vars).astype(np.uint8, copy=False)
    if result.tt is None:
        raise AssertionError("no-reinflate result had neither bits nor truth table")
    return np.asarray(result.tt, dtype=np.uint8).reshape(-1)


def _prepare_operation(case: dict[str, Any]) -> tuple[Callable[[], Any], Callable[[Any], dict[str, Any]]]:
    expr = _expression(case)
    kind = case["kind"]

    if kind in {"compile_and", "compile_or"}:
        def operation() -> Any:
            return compile_expr_to_cm_ir(expr)

        def validate(node: Any) -> dict[str, Any]:
            width = int(case["width"])
            return {
                "correct": (
                    node.kind == "binary"
                    and node.op == ("AND" if kind == "compile_and" else "OR")
                    and tuple(node.vars) == tuple(f"x{i}" for i in range(width))
                ),
                "deviation_count": 0,
                "result_signature": _sha256_repr(node.key),
                "result_elements": len(node.args),
            }

        return operation, validate

    node = compile_expr_to_cm_ir(expr)
    if kind == "eval":
        n_vars = int(case["n_vars"])
        expected = eval_expr_tt(expr, n_vars).astype(np.uint8, copy=False).reshape(-1)

        def operation() -> Any:
            return materialize_hybrid_no_reinflate(
                node,
                [f"x{i}" for i in range(n_vars)],
                fixed={},
                hybrid_threshold=n_vars,
                flat_eval=True,
                words_eval=True,
            )

        def validate(result: Any) -> dict[str, Any]:
            actual = _result_to_array(result, n_vars)
            mismatches = int(np.count_nonzero(actual != expected))
            return {
                "correct": mismatches == 0,
                "deviation_count": mismatches,
                "result_signature": hashlib.sha256(actual.tobytes()).hexdigest(),
                "result_elements": int(actual.size),
            }

        return operation, validate

    if kind == "dense":
        n_vars = int(case["n_vars"])
        row_vars, column_vars = canonical_layout([f"x{i}" for i in range(n_vars)])
        expected = eval_expr_tt(expr, n_vars).astype(np.uint8, copy=False).reshape(-1)

        def operation() -> Any:
            return materialize_cm(
                node,
                row_vars,
                column_vars,
                fixed={},
                materialize_mode="numpy",
            )

        def validate(matrix: Any) -> dict[str, Any]:
            variables = list(row_vars) + list(column_vars)
            actual = np.asarray(matrix).reshape((2,) * len(variables))
            permutation = [variables.index(f"x{i}") for i in range(n_vars)]
            actual = np.transpose(actual, axes=permutation).reshape(-1).astype(np.uint8, copy=False)
            mismatches = int(np.count_nonzero(actual != expected))
            return {
                "correct": mismatches == 0,
                "deviation_count": mismatches,
                "result_signature": hashlib.sha256(actual.tobytes()).hexdigest(),
                "result_elements": int(actual.size),
            }

        return operation, validate

    if kind == "sparse_ambient":
        ambient_n = int(case["ambient_n"])
        live_k = int(case["live_k"])
        expected = eval_expr_tt(expr, live_k).astype(np.uint8, copy=False).reshape(-1)

        def operation() -> Any:
            return materialize_hybrid_no_reinflate(
                node,
                [f"x{i}" for i in range(ambient_n)],
                fixed={},
                hybrid_threshold=live_k,
                allow_reduced_output=True,
                max_full_output_vars=int(case["max_full_output_vars"]),
                flat_eval=True,
                words_eval=True,
            )

        def validate(result: Any) -> dict[str, Any]:
            actual = _result_to_array(result, live_k)
            mismatches = int(np.count_nonzero(actual != expected))
            return {
                "correct": mismatches == 0 and tuple(result.output_vars) == tuple(f"x{i}" for i in range(live_k)),
                "deviation_count": mismatches,
                "result_signature": hashlib.sha256(actual.tobytes()).hexdigest(),
                "result_elements": int(actual.size),
            }

        return operation, validate

    raise ValueError(f"unknown case kind: {kind}")


def _run_worker(case: dict[str, Any], warmups: int, repetitions: int) -> dict[str, Any]:
    operation, validate = _prepare_operation(case)
    for _ in range(warmups):
        validate(operation())

    gc.collect()
    rss_start, peak_rss_start = _process_memory_bytes()
    tracemalloc.start()
    samples = []
    signature: str | None = None
    batch_size = int(case.get("batch_size", 1))
    for repetition in range(repetitions):
        tracemalloc.reset_peak()
        gc_before = _gc_collections()
        cpu_start = time.process_time_ns()
        wall_start = time.perf_counter_ns()
        result = None
        for _ in range(batch_size):
            result = operation()
        batch_wall_ns = time.perf_counter_ns() - wall_start
        batch_cpu_ns = time.process_time_ns() - cpu_start
        wall_ns = batch_wall_ns / batch_size
        cpu_ns = batch_cpu_ns / batch_size
        current_alloc, peak_alloc = tracemalloc.get_traced_memory()
        checked = validate(result)
        if not checked["correct"]:
            raise AssertionError(f"correctness failure in {case['name']}: {checked}")
        if signature is None:
            signature = str(checked["result_signature"])
        elif signature != str(checked["result_signature"]):
            raise AssertionError(f"non-deterministic result signature in {case['name']}")
        samples.append(
            {
                "repetition": repetition,
                "batch_size": batch_size,
                "batch_wall_ns": batch_wall_ns,
                "batch_cpu_ns": batch_cpu_ns,
                "wall_ns": wall_ns,
                "cpu_ns": cpu_ns,
                "throughput_per_s": 1e9 / wall_ns,
                "tracemalloc_current_bytes": current_alloc,
                "tracemalloc_peak_bytes": peak_alloc,
                "gc_collections": _gc_collections() - gc_before,
                **checked,
            }
        )
    tracemalloc.stop()
    rss_end, peak_rss_end = _process_memory_bytes()
    peak_delta = None
    if peak_rss_end is not None and rss_start is not None:
        peak_delta = max(0, peak_rss_end - rss_start)
    return {
        "case": case,
        "warmups": warmups,
        "repetitions": repetitions,
        "batch_size": batch_size,
        "rss_start_bytes": rss_start,
        "rss_end_bytes": rss_end,
        "peak_rss_start_bytes": peak_rss_start,
        "peak_rss_end_bytes": peak_rss_end,
        "peak_rss_delta_bytes": peak_delta,
        "samples": samples,
    }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _summarize(worker_result: dict[str, Any]) -> dict[str, Any]:
    samples = worker_result["samples"]
    walls = [float(sample["wall_ns"]) for sample in samples]
    cpus = [float(sample["cpu_ns"]) for sample in samples]
    peaks = [float(sample["tracemalloc_peak_bytes"]) for sample in samples]
    median_wall = statistics.median(walls)
    deviations = [abs(value - median_wall) for value in walls]
    first = samples[0]
    return {
        **worker_result["case"],
        "warmups": worker_result["warmups"],
        "repetitions": worker_result["repetitions"],
        "wall_ns_median": median_wall,
        "wall_ns_mad": statistics.median(deviations),
        "wall_ns_p10": _percentile(walls, 0.10),
        "wall_ns_p90": _percentile(walls, 0.90),
        "cpu_ns_median": statistics.median(cpus),
        "throughput_per_s_median": 1e9 / median_wall,
        "tracemalloc_peak_bytes_median": statistics.median(peaks),
        "peak_rss_delta_bytes": worker_result["peak_rss_delta_bytes"],
        "correct": all(bool(sample["correct"]) for sample in samples),
        "deviation_count_max": max(int(sample["deviation_count"]) for sample in samples),
        "result_signature": first["result_signature"],
        "result_elements": first["result_elements"],
    }


def _cases(suite: str) -> list[dict[str, Any]]:
    smoke = [
        {"name": "compile_and_w64", "kind": "compile_and", "width": 64, "batch_size": 25},
        {"name": "eval_mixed_n8", "kind": "eval", "n_vars": 8, "batch_size": 1000},
        {"name": "dense_numpy_n8", "kind": "dense", "n_vars": 8, "batch_size": 100},
        {
            "name": "sparse_ambient32_live5",
            "kind": "sparse_ambient",
            "ambient_n": 32,
            "live_k": 5,
            "max_full_output_vars": 16,
            "batch_size": 1000,
        },
    ]
    local = [
        *(
            {
                "name": f"compile_{op}_w{width}",
                "kind": f"compile_{op}",
                "width": width,
                "batch_size": {32: 50, 64: 25, 128: 10, 256: 5, 512: 3}[width],
            }
            for op in ("and", "or")
            for width in (32, 64, 128, 256, 512)
        ),
        *(
            {"name": f"eval_mixed_n{n}", "kind": "eval", "n_vars": n, "batch_size": 1000}
            for n in (4, 8, 12, 16)
        ),
        *(
            {"name": f"dense_numpy_n{n}", "kind": "dense", "n_vars": n, "batch_size": 100}
            for n in (8, 12, 16)
        ),
        smoke[-1],
    ]
    large = [
        *local,
        *(
            {
                "name": f"compile_{op}_w{width}",
                "kind": f"compile_{op}",
                "width": width,
                "batch_size": 1,
            }
            for op in ("and", "or")
            for width in (1024, 2048)
        ),
        *(
            {"name": f"eval_mixed_n{n}", "kind": "eval", "n_vars": n, "batch_size": 500}
            for n in (18, 20)
        ),
        {"name": "dense_numpy_n18", "kind": "dense", "n_vars": 18, "batch_size": 50},
    ]
    return {"smoke": smoke, "local": local, "large": large}[suite]


def _run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _environment(command: list[str], label: str, suite: str) -> dict[str, Any]:
    thread_names = (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    )
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "suite": suite,
        "command": command,
        "git_head": _run_git("rev-parse", "HEAD"),
        "git_status_short": _run_git("status", "--short").splitlines(),
        "cm_ir_sha256": _file_sha256(REPO_ROOT / "cm_ir.py"),
        "bitset_backend_sha256": _file_sha256(REPO_ROOT / "bitset_backend.py"),
        "script_sha256": _file_sha256(Path(__file__).resolve()),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "machine": platform.machine(),
        "logical_cpu_count": os.cpu_count(),
        "numpy_version": np.__version__,
        "thread_settings": {name: os.environ.get(name) for name in thread_names},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("smoke", "local", "large"), default="smoke")
    parser.add_argument("--label", default="measurement")
    parser.add_argument("--output-prefix", type=Path)
    parser.add_argument("--warmups", type=int, default=3)
    parser.add_argument("--repetitions", type=int, default=11)
    parser.add_argument("--worker-case", help=argparse.SUPPRESS)
    parsed = parser.parse_args()

    if parsed.worker_case:
        print(json.dumps(_run_worker(json.loads(parsed.worker_case), parsed.warmups, parsed.repetitions)))
        return 0
    if parsed.output_prefix is None:
        parser.error("--output-prefix is required")
    if parsed.warmups < 0 or parsed.repetitions < 3:
        parser.error("warmups must be >= 0 and repetitions must be >= 3")

    environment = _environment(sys.argv, parsed.label, parsed.suite)
    raw_results = []
    summaries = []
    for case in _cases(parsed.suite):
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker-case",
            json.dumps(case, separators=(",", ":")),
            "--warmups",
            str(parsed.warmups),
            "--repetitions",
            str(parsed.repetitions),
        ]
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"worker failed for {case['name']} (exit {completed.returncode}):\n{completed.stderr}"
            )
        worker_result = json.loads(completed.stdout)
        raw_results.append(worker_result)
        summaries.append(_summarize(worker_result))
        print(f"{case['name']}: {summaries[-1]['wall_ns_median'] / 1e6:.3f} ms")

    prefix = parsed.output_prefix
    prefix.parent.mkdir(parents=True, exist_ok=True)
    raw_path = prefix.with_name(prefix.name + "_raw.jsonl")
    summary_path = prefix.with_name(prefix.name + "_summary.json")
    with raw_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({"record_type": "environment", **environment}, sort_keys=True) + "\n")
        for result in raw_results:
            handle.write(
                json.dumps(
                    {"record_type": "case", "label": parsed.label, **result},
                    sort_keys=True,
                )
                + "\n"
            )
    summary_payload = {"environment": environment, "results": summaries}
    summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {raw_path}")
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
