"""Fresh owned-process and cache-retention diagnostics for the packed-mask audit."""
from __future__ import annotations

import argparse
import ctypes
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]


class Counters(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong),
                ("peak", ctypes.c_size_t), ("working", ctypes.c_size_t),
                ("pool_peak", ctypes.c_size_t), ("pool", ctypes.c_size_t),
                ("nonpaged_peak", ctypes.c_size_t), ("nonpaged", ctypes.c_size_t),
                ("pagefile", ctypes.c_size_t), ("pagefile_peak", ctypes.c_size_t)]


def rss():
    if os.name != "nt":
        return {"unavailable": "this local diagnostic uses Windows process counters"}
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = (ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong)
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {"working_bytes": counters.working, "lifetime_peak_bytes": counters.peak}


def child(args):
    started = time.perf_counter_ns()
    sys.path.insert(0, str(ROOT))
    from scripts import cm_packed_mask_audit as audit
    audit.load_baseline(args.output)
    import_ns = time.perf_counter_ns() - started
    names = tuple(f"x{i}" for i in range(args.n))
    with audit.arm_scope(args.arm):
        gc.collect()
        baseline = rss()
        # Uninstrumented operation, then a separate allocation pass.
        start = time.perf_counter_ns()
        result = audit.bs.build_bitset_env(names)
        operation_ns = time.perf_counter_ns() - start
        retained = rss()
        digest = hashlib.sha256(b"".join(value.to_bytes(max(1, (1 << args.n) // 8), "little")
                                         for value in result.values())).hexdigest()
        del result
        audit.bs.clear_bitset_env_cache()
        gc.collect()
        released = rss()
        tracemalloc.start()
        result = audit.bs.build_bitset_env(names)
        traced_retained, traced_peak = tracemalloc.get_traced_memory()
        del result
        audit.bs.clear_bitset_env_cache()
        gc.collect()
        traced_released, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return dict(n=args.n, arm=args.arm, pid=os.getpid(), import_ns=import_ns,
                operation_ns=operation_ns, baseline=baseline, retained=retained,
                released=released, traced_peak=traced_peak, traced_retained=traced_retained,
                traced_released=traced_released, output_sha256=digest)


def run(args):
    rows = []
    for n in (16, 22):
        for repeat in range(5):
            for arm in (("baseline", "candidate") if repeat % 2 == 0 else ("candidate", "baseline")):
                command = [sys.executable, "-B", str(Path(__file__).resolve()), "--output", str(args.output),
                           "--child", "--n", str(n), "--arm", arm]
                start = time.perf_counter_ns()
                process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                         check=True, timeout=60)
                elapsed = time.perf_counter_ns() - start
                row = json.loads(process.stdout)
                row.update(repeat=repeat, lifecycle_ns=elapsed)
                rows.append(row)
                print(n, repeat, arm, flush=True)
    for n in (16, 22):
        assert len({row["output_sha256"] for row in rows if row["n"] == n}) == 1
    with (args.output / "fresh_process.json").open("x", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, sort_keys=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--n", type=int)
    parser.add_argument("--arm", choices=("baseline", "candidate"))
    args = parser.parse_args()
    if args.child:
        print(json.dumps(child(args)))
    else:
        run(args)


if __name__ == "__main__":
    main()
