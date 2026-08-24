#!/usr/bin/env python3
"""Fail-closed k=17..20 boundary sweep in one isolated process per case."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bitset_backend import (  # noqa: E402
    compile_expr_flat,
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_flat_bitset,
    eval_expr_words_bitset,
    get_flat_program,
    program_metrics,
)
from cm_exprlib import And, Imp, Or, Var, Xor  # noqa: E402
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate  # noqa: E402
from cmbench.output_budget import OutputBudgetExceeded  # noqa: E402

K_VALUES = (17, 18, 19, 20)
FAMILIES = {"and": And, "or": Or, "xor": Xor, "imp": Imp}


def _balanced(values, op):
    layer = list(values)
    while len(layer) > 1:
        layer = [op(layer[index], layer[index + 1]) if index + 1 < len(layer) else layer[index]
                 for index in range(0, len(layer), 2)]
    return layer[0]


def _expr(k: int, family: str):
    values = [Var(index) for index in range(k)]
    if family == "imp":
        value = values[-1]
        for item in reversed(values[:-1]):
            value = Imp(item, value)
        return value
    return _balanced(values, FAMILIES[family])


def _peak_rss_bytes() -> int | None:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.windll.psapi
        psapi.GetProcessMemoryInfo.argtypes = (
            wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD
        )
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if psapi.GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            return int(counters.PeakWorkingSetSize)
        return None
    try:
        import resource

        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform == "darwin" else value * 1024)
    except Exception:
        return None


def _median_ns(fn, repetitions: int) -> tuple[float, int]:
    samples, value = [], 0
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        value = int(fn())
        samples.append(time.perf_counter_ns() - start)
    return float(statistics.median(samples)), value


def _worker(k: int, family: str, estimate_cap: int, rss_cap: int, repetitions: int) -> int:
    expression = _expr(k, family)
    support = tuple(f"x{i}" for i in range(k))
    node = compile_expr_to_cm_ir(expression)
    production_refused = False
    refusal_reason = None
    try:
        materialize_hybrid_no_reinflate(
            node, support, fixed={}, hybrid_threshold=16,
            allow_reduced_output=False, max_full_output_vars=16,
            flat_eval=True, words_eval=True,
        )
    except OutputBudgetExceeded as exc:
        production_refused = True
        refusal_reason = str(exc)

    raw_program = compile_expr_flat(expression)
    cm_program = get_flat_program(node)
    raw_metrics = program_metrics(raw_program)
    cm_metrics = program_metrics(cm_program)
    output_bytes = (1 << k) // 8
    n_words = (1 << k) // 64
    estimates = {
        "output_bytes": output_bytes,
        "raw_flat_temporary_bytes": raw_program.n_slots * output_bytes,
        "raw_words_temporary_bytes": (k + int(raw_metrics["peak_live_word_buffers"])) * n_words * 8,
        "cm_flat_temporary_bytes": cm_program.n_slots * output_bytes,
        "cm_words_temporary_bytes": (k + int(cm_metrics["peak_live_word_buffers"])) * n_words * 8,
    }
    max_estimate = max(value for key, value in estimates.items() if key != "output_bytes")
    base = {
        "live_k": k, "family": family, "production_wrapper_refused": production_refused,
        "production_refusal_reason": refusal_reason, **estimates,
        "max_estimated_temporary_bytes": max_estimate,
        "estimate_cap_bytes": estimate_cap, "rss_cap_bytes": rss_cap,
    }
    if max_estimate > estimate_cap:
        print(json.dumps({**base, "status": "refused_estimate_budget", "pass": False}))
        return 0

    arms = {
        "raw_flat": lambda: eval_expr_flat_bitset(expression, support),
        "raw_words": lambda: eval_expr_words_bitset(expression, support),
        "cm_flat": lambda: eval_cm_node_flat(node, support),
        "cm_words": lambda: eval_cm_node_words(node, support),
    }
    timings, values = {}, {}
    for name, fn in arms.items():
        timings[name + "_ns_median"], values[name] = _median_ns(fn, repetitions)
    equal = len(set(values.values())) == 1
    digest = hashlib.sha256(values["cm_flat"].to_bytes(output_bytes, "little")).hexdigest()
    peak_rss = _peak_rss_bytes()
    passed = production_refused and equal and peak_rss is not None and peak_rss <= rss_cap
    print(json.dumps({
        **base, **timings, "packed_sha256": digest, "packed_equal_all_arms": equal,
        "peak_rss_bytes": peak_rss, "status": "ok" if passed else "failed_gate",
        "pass": passed,
    }))
    return 0


def _write_csv(path: Path, rows: list[dict]) -> None:
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-prefix", type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    parser.add_argument("--estimate-cap-bytes", type=int, default=64 << 20)
    parser.add_argument("--rss-cap-bytes", type=int, default=512 << 20)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--k", type=int)
    parser.add_argument("--family", choices=tuple(FAMILIES))
    args = parser.parse_args()
    if args.worker:
        return _worker(args.k, args.family, args.estimate_cap_bytes, args.rss_cap_bytes, args.repetitions)
    if args.output_prefix is None:
        parser.error("--output-prefix is required")
    prefix = args.output_prefix if args.output_prefix.is_absolute() else ROOT / args.output_prefix
    paths = {
        "raw": prefix.with_name(prefix.name + "_raw.csv"),
        "audit": prefix.with_name(prefix.name + "_audit.json"),
    }
    existing = [str(path) for path in paths.values() if path.exists()]
    if existing:
        parser.error("refusing to overwrite: " + ", ".join(existing))
    prefix.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for k in K_VALUES:
        for family in FAMILIES:
            command = [
                sys.executable, str(Path(__file__).resolve()), "--worker", "--k", str(k),
                "--family", family, "--estimate-cap-bytes", str(args.estimate_cap_bytes),
                "--rss-cap-bytes", str(args.rss_cap_bytes), "--repetitions", str(args.repetitions),
            ]
            started = time.perf_counter()
            try:
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                        timeout=args.timeout_seconds, check=False)
                if result.returncode:
                    row = {"live_k": k, "family": family, "status": "worker_error",
                           "returncode": result.returncode, "stderr_tail": result.stderr[-1000:], "pass": False}
                else:
                    row = json.loads(result.stdout.strip().splitlines()[-1])
            except subprocess.TimeoutExpired:
                row = {"live_k": k, "family": family, "status": "timeout", "pass": False}
            row["wall_seconds"] = time.perf_counter() - started
            rows.append(row)
            print(f"k={k} {family}: {row['status']} wall={row['wall_seconds']:.2f}s", flush=True)
    acceptance = {
        "pass": len(rows) == len(K_VALUES) * len(FAMILIES) and all(row.get("pass") for row in rows),
        "expected_cases": len(K_VALUES) * len(FAMILIES),
        "completed_cases": sum(row.get("status") == "ok" for row in rows),
        "timeout_count": sum(row.get("status") == "timeout" for row in rows),
        "mismatch_count": sum(row.get("packed_equal_all_arms") is False for row in rows),
        "wrapper_non_refusal_count": sum(row.get("production_wrapper_refused") is False for row in rows),
    }
    _write_csv(paths["raw"], rows)
    paths["audit"].write_text(json.dumps({
        "protocol": "one subprocess per case; pre-allocation estimate cap; hard parent timeout; peak RSS gate",
        "environment": {"python": sys.version, "platform": platform.platform()},
        "limits": {"timeout_seconds": args.timeout_seconds, "estimate_cap_bytes": args.estimate_cap_bytes,
                   "rss_cap_bytes": args.rss_cap_bytes, "repetitions": args.repetitions},
        "acceptance": acceptance,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"paths": {key: str(value) for key, value in paths.items()}, "acceptance": acceptance}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
