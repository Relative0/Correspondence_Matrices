#!/usr/bin/env python3
"""Bounded, opt-in memory study; candidate models never change CM admission.

Only a 64-row functional smoke is allowed locally. Larger studies require an
explicit Runpod execution mode and a Runpod Linux environment. This is not a
cloud launcher: it installs nothing, uploads nothing, and creates no resources.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.output_budget import OutputBudget, estimate_explicit_output
from cmbench.reporting.provenance import sha256_file
from cmbench.tracing.replay import write_json_exclusive

SCHEMA = "cm-memory-study/v1"
MODEL = "cm-memory-structure-v1-candidate"
CALIBRATION = ("mixed-chain", "shared-diamond", "wide-and")
HELDOUT = ("alternating-tree", "reconvergent-xor")
REPRESENTATIONS = ("dense", "bigint", "words")
MAX_NODES, MAX_EDGES, MAX_K = 1024, 2048, 16
MAX_TEMPORARY = 32 << 20
MAX_OUTPUT = 1 << 16
MAX_JOB_BYTES = 512 << 10


def bounded_int(value, name, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError(f"{name} outside diagnostic bounds")
    return value


def candidate_estimate(*, k, representation, nodes, slots, edges, buffers):
    """Allocation mechanism envelope, with an explicit 25% safety allowance.

    Metadata envelopes are provisional, not fitted to measurement. Dense memo
    arrays are bounded at full width; bigints use CPython limbs; words include
    retained bigint masks, read-only word masks, plan scratch and return copies.
    Cold mask construction above k=10 uses uint32 row/shift temporaries. Return
    peak includes output. This is NOT an OS RSS cap or a production estimator.
    """
    for name, value, cap in (("k", k, MAX_K), ("nodes", nodes, MAX_NODES),
                             ("slots", slots, MAX_NODES), ("edges", edges, MAX_EDGES),
                             ("buffers", buffers, MAX_NODES)):
        bounded_int(value, name, cap)
    if representation not in REPRESENTATIONS:
        raise ValueError("unknown representation")
    elements = 1 << k
    packed = (elements + 7) // 8
    limb_bytes = sys.int_info.sizeof_digit
    integer_bytes = sys.getsizeof(0) + limb_bytes * ((elements + sys.int_info.bits_per_digit - 1)
                                                   // sys.int_info.bits_per_digit)
    # Dictionaries, tuple keys, views, recursion frames and shape/stride metadata.
    metadata = 16384 + 512 * (nodes + edges + k) + 32 * k * (nodes + 2)
    cold_masks = 16 * elements if k > 10 else (k + 4) * integer_bytes
    if representation == "dense":
        storage = (nodes + 6) * elements
        output = elements
    elif representation == "bigint" or k < 6:
        storage = (slots + k + 6) * integer_bytes + cold_masks
        output = packed
    else:
        # k bigint masks coexist with k byte-backed word views; include two
        # constants, the word-plan scratch pool, tobytes and final PyLong.
        storage = (k + buffers + 4) * (max(8, packed) + 192)
        storage += (k + 2) * integer_bytes + cold_masks
        output = packed
    return {"model": MODEL, "output_bytes": output,
            "metadata_bytes": metadata, "storage_bytes": storage,
            "temporary_bytes": ((metadata + storage) * 5 + 3) // 4,
            "margin_fraction": 0.25, "is_rss_guarantee": False}


def profiles():
    return {
        "legacy-direct": OutputBudget(max_output_bytes=1 << 18),
        "legacy-benchmark": OutputBudget(max_output_bytes=1 << 16, max_output_vars=16),
        "legacy-remote": OutputBudget(max_output_bytes=1 << 16),
        "production-balanced-v1-benchmark-remote": OutputBudget(
            max_output_bytes=1 << 16, max_temporary_bytes=16 << 20, max_output_vars=16),
        "production-balanced-v1-direct": OutputBudget(
            max_output_bytes=1 << 18, max_temporary_bytes=64 << 20),
        "strict-diagnostic": OutputBudget(
            max_output_bytes=1 << 14, max_temporary_bytes=4 << 20, max_output_vars=14),
        "permissive-diagnostic": OutputBudget(
            max_output_bytes=1 << 18, max_temporary_bytes=64 << 20, max_output_vars=16),
    }


def profile_decisions(k, output_bytes, temporary_bytes, peak=None):
    result = []
    for name, budget in profiles().items():
        reason = None
        if budget.max_output_vars is not None and k > budget.max_output_vars:
            reason = "variables"
        elif output_bytes > budget.max_output_bytes:
            reason = "output_bytes"
        elif budget.max_temporary_bytes is not None and temporary_bytes > budget.max_temporary_bytes:
            reason = "temporary_bytes"
        observed_fits = (None if peak is None or budget.max_temporary_bytes is None
                         else peak <= budget.max_temporary_bytes)
        result.append({"profile": name, "status": "ok" if reason is None else "refused",
                       "reason": reason, "resolved_limits": budget.__dict__,
                       "false_admission": None if observed_fits is None else reason is None and not observed_fits,
                       "false_refusal": None if observed_fits is None else reason == "temporary_bytes" and observed_fits})
    return result


def build_expression(family, k, seed):
    from cm_exprlib import And, Not, Or, Var, Xor
    bounded_int(k, "k", MAX_K)
    if k < 2 or family not in CALIBRATION + HELDOUT:
        raise ValueError("unsupported structural family or support")
    leaves = [Var(i) for i in range(k)]
    rng = random.Random(seed)
    if family == "mixed-chain":
        expr = Xor(leaves[0], Not(leaves[1]))
        for i in range(2, k):
            expr = Xor(And(expr, Or(leaves[i], leaves[i - 1])), Not(And(leaves[i], leaves[i - 1])))
        return expr
    if family == "shared-diamond":
        expr = Xor(leaves[0], leaves[1])
        for leaf in leaves[2:]:
            expr = Or(And(expr, leaf), And(Not(expr), Not(leaf)))
        return expr
    if family == "wide-and":
        expr = leaves[0]
        for leaf in leaves[1:]:
            expr = And(expr, leaf)
        return expr
    if family == "reconvergent-xor":
        expr = Xor(leaves[0], leaves[1])
        for leaf in leaves[2:]:
            shared = Or(expr, leaf)
            expr = Xor(And(shared, Not(leaf)), Or(Not(shared), expr))
        return expr
    level = [Not(v) if rng.randrange(2) else v for v in leaves]
    depth = 0
    while len(level) > 1:
        op = (And, Xor, Or)[depth % 3]
        level = [op(level[i], level[i + 1]) if i + 1 < len(level) else level[i]
                 for i in range(0, len(level), 2)]
        depth += 1
    return level[0]


def rss_sample():
    """Current RSS and process-lifetime high-water; never a window peak."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                    (name, ctypes.c_size_t) for name in
                    ("peak", "current", "paged_peak", "paged", "nonpaged_peak", "nonpaged", "pagefile", "pagefile_peak")]

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                raise OSError(ctypes.get_last_error())
            return {"method": "Windows GetProcessMemoryInfo working set", "current_bytes": counters.current,
                    "lifetime_peak_bytes": counters.peak}
        import resource
        high = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        current = None
        if sys.platform.startswith("linux"):
            current = int(Path("/proc/self/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")
        return {"method": "getrusage lifetime ru_maxrss; /proc/self/statm current where available",
                "current_bytes": current, "lifetime_peak_bytes": int(high * (1 if sys.platform == "darwin" else 1024))}
    except (OSError, ValueError, ImportError, AttributeError) as exc:
        return {"method": "unavailable: " + type(exc).__name__, "current_bytes": None, "lifetime_peak_bytes": None}


def measure(fn):
    gc.collect()
    before = rss_sample()
    tracemalloc.start()
    started = time.perf_counter_ns()
    try:
        result = fn()
        elapsed = time.perf_counter_ns() - started
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, {"elapsed_ns": elapsed, "tracemalloc_current_bytes": current,
                    "tracemalloc_peak_bytes": peak, "rss_before": before, "rss_after": rss_sample()}


def prepare_job(job):
    from cm_expr_serde import expr_from_json, expr_to_json_dag
    if "record" in job:
        from scripts.cm_deep_performance_audit import _evaluation_context
        record = job["record"]
        document = record["expression_v2"]
        if document.get("version") != 2 or len(document.get("nodes", [])) > MAX_NODES:
            raise ValueError("corpus expression outside diagnostic DAG bounds")
        expr = expr_from_json(document)
        variables, fixed = _evaluation_context(job["corpus"], record, expr, job["k"])
        # Frozen EPFL checking can expand syntactic support; cap it in advance.
        if int(record.get("synt_support_size", job["k"])) > MAX_K:
            raise ValueError("frozen truth verification exceeds support cap")
    else:
        expr = build_expression(job["family"], job["k"], job["seed"])
        document = expr_to_json_dag(expr)
        variables = tuple(f"x{i}" for i in range(job["k"]))
        fixed = {}
        if job["context"] != "none":
            stride = 2 if job["context"] == "half" else 1
            fixed = {v: i % 2 for i, v in enumerate(variables) if i % stride == 0}
            variables = tuple(v for v in variables if v not in fixed)
    nodes = len(document["nodes"])
    edges = sum(int("a" in row) + int("b" in row) for row in document["nodes"])
    bounded_int(nodes, "nodes", MAX_NODES)
    bounded_int(edges, "edges", MAX_EDGES)
    bounded_int(len(variables), "output k", MAX_K)
    if (1 << len(variables)) > MAX_OUTPUT:
        raise ValueError("diagnostic output cap")
    # Conservative preflight before compilation, not a claim about compiler RSS.
    preflight = candidate_estimate(k=len(variables), representation=job["representation"],
                                   nodes=nodes, slots=nodes, edges=edges, buffers=nodes)
    if preflight["temporary_bytes"] > MAX_TEMPORARY:
        raise ValueError("diagnostic preflight memory cap")
    return expr, variables, fixed, document


def validate_job_execution(job):
    if job.get("execution", "local-smoke") == "runpod":
        if not sys.platform.startswith("linux") or not os.environ.get("RUNPOD_POD_ID"):
            raise ValueError("nontrivial child requires a Runpod Linux environment")
    elif (job.get("record") is not None or job["k"] > 6 or job["repetitions"] != 1
          or job["family"] != "mixed-chain" or job["context"] != "none" or job["schedule"] != "cold"):
        raise ValueError("child exceeds local tiny smoke bounds")


def run_job(job, rows=None, emit=None):
    validate_job_execution(job)
    import numpy as np
    from bitset_backend import (bitset_to_bool_array, eval_cm_node_flat, eval_cm_node_words,
                                eval_expr_flat_cse, get_flat_program, program_metrics)
    from cm_ir import compile_expr_to_cm_ir, materialize_cm, materialize_ir, _cm_node_count
    from cm_normalize import canonical_layout

    expr, variables, fixed, document = prepare_job(job)
    k = len(variables)
    def compile_one():
        node = compile_expr_to_cm_ir(expr, reuse_cache=False, persistent_cache=False)
        get_flat_program(node)
        return node

    retained_node = None
    rows = [] if rows is None else rows
    repeats = job["repetitions"]
    # Warmup precedes recorded repetitions, and stays inside the same child.
    for repetition in range(-1 if job["schedule"] == "warm" else 0, repeats):
        node, preparation = measure(compile_one)
        if retained_node is None:
            retained_node = node
        else:
            node = retained_node
        program = get_flat_program(node)
        metrics = program_metrics(program)
        s = _cm_node_count(node)
        started = time.perf_counter_ns()
        candidate = candidate_estimate(k=k, representation=job["representation"], nodes=s,
                                       slots=program.n_slots, edges=metrics["argument_edges"],
                                       buffers=metrics["peak_live_word_buffers"])
        estimate_ns = time.perf_counter_ns() - started
        representation = "dense_bool" if job["representation"] == "dense" else "packed_bitset"
        legacy = estimate_explicit_output(k, representation, operation_slots=s)
        if candidate["temporary_bytes"] > MAX_TEMPORARY:
            raise ValueError("diagnostic model cap")
        R, C = canonical_layout(list(variables))
        windows = [("preparation_compile_and_lower", preparation, None)]
        actual_engine = job["representation"] if job["representation"] != "words" or k >= 6 else "bigint-fallback"
        if job["representation"] == "dense":
            # The guarded whole-call window must precede the unguarded IR probe:
            # otherwise the probe silently warms alignment/allocator state.
            output, sample = measure(lambda: materialize_cm(node, R, C, fixed, materialize_mode="numpy", output_budget=None))
            flat = output.reshape(-1).astype(np.uint8)
            packed = int.from_bytes(np.packbits(flat, bitorder="little").tobytes(), "little")
            windows.append(("materialization_dense_whole_call", sample, packed))
            del output, flat
            evaluated, sample = measure(lambda: materialize_ir(node, fixed=fixed, materialize_mode="numpy"))
            del evaluated
            windows.append(("evaluation_dense_ir_after_materialization", sample, None))
        else:
            evaluate = eval_cm_node_flat if job["representation"] == "bigint" else eval_cm_node_words
            packed, sample = measure(lambda: evaluate(node, variables, fixed=fixed))
            windows.append(("evaluation_packed_whole_call", sample, packed))
        converted, conversion = measure(lambda: bitset_to_bool_array(packed, k))
        windows.append(("conversion_packed_to_uint8", conversion, packed))
        serialized, serialization = measure(lambda: json.dumps(converted.tolist(), separators=(",", ":")))
        windows.append(("serialization_dense_json", serialization, packed))
        del converted, serialized
        # CSE-flat reference and frozen digest checks are outside measurement.
        expected = eval_expr_flat_cse(expr, variables, fixed=fixed)
        if packed != expected:
            raise AssertionError("exact packed result/order mismatch")
        frozen = None
        if "record" in job:
            from scripts.cm_deep_performance_audit import _verify_frozen_truth
            frozen = _verify_frozen_truth(job["corpus"], job["record"], expr, packed, k)
        digest = hashlib.sha256(packed.to_bytes((1 << k) // 8 or 1, "little")).hexdigest()
        if repetition < 0:
            continue
        for window, sample, _ in windows:
            # Only compare estimator and policy to their actual guarded window.
            comparable = window in {"materialization_dense_whole_call", "evaluation_packed_whole_call"}
            peak = sample["tracemalloc_peak_bytes"] if comparable else None
            rows.append({"schema": SCHEMA, "case_id": job["case_id"], "family": job["family"],
                         "role": job["role"], "seed": job["seed"], "context": job["context"],
                         "schedule": job["schedule"], "repetition": repetition, "window": window,
                         "representation": job["representation"], "actual_engine": actual_engine,
                         "s": s, "expression_s": len(document["nodes"]), "k": k, "m": len(program.ops),
                         "live_k": len([v for v in node.vars if v not in fixed]),
                         "fixed_count": len(fixed), "slots": program.n_slots, "metrics": metrics,
                         "operator_mix": dict(Counter(str(op) for _, op, _ in program.ops)),
                         "output_bytes": legacy.output_bytes, "legacy_estimator": "legacy-output-v1",
                         "legacy_estimate": legacy.temporary_bytes, "candidate": candidate,
                         "estimate_elapsed_ns": estimate_ns, "comparison_eligible": comparable,
                         "window_cache_state": ("after_compile_and_feature_extraction" if comparable
                                                else "sequential_diagnostic_window"),
                         "status": "ok", "exact": True, "output_sha256": digest,
                         "frozen_truth_sha256_verified": frozen, **sample,
                         "profiles": {"legacy": profile_decisions(k, legacy.output_bytes, legacy.temporary_bytes, peak),
                                      "candidate": profile_decisions(k, legacy.output_bytes, candidate["temporary_bytes"], peak)}
                         if comparable else None})
            if emit is not None:
                emit(rows[-1])
    return rows


def incomplete_rows(job, previous, status, reason):
    completed = {row.get("repetition") for row in previous}
    missing = [i for i in range(job["repetitions"]) if i not in completed]
    base = {key: job[key] for key in ("case_id", "family", "role", "schedule", "representation")}
    return [{**base, "repetition": repetition, "status": status if index == 0 else "skipped",
             "reason": reason} for index, repetition in enumerate(missing or [None])]


def parse_child_rows(output):
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    rows = []
    for line in (output or "").splitlines(keepends=True):
        if not line.endswith("\n"):
            break  # Interrupted final JSON is never accepted as a result.
        rows.append(json.loads(line))
    return rows


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row.get("role"), row.get("schedule"), row.get("representation"), row.get("window"))].append(row)
    summaries = []
    for key, group in groups.items():
        valid = [r for r in group if r["status"] == "ok" and r.get("comparison_eligible")]
        entry = dict(zip(("role", "schedule", "representation", "window"), key))
        entry.update(rows=len(group), statuses=dict(Counter(r["status"] for r in group)),
                     measured_comparable=len(valid))
        for name in ("legacy", "candidate"):
            ratios = [r["tracemalloc_peak_bytes"] / (r["legacy_estimate"] if name == "legacy"
                                                   else r["candidate"]["temporary_bytes"]) for r in valid]
            entry[name] = {"underestimates": sum(x > 1 for x in ratios),
                           "max_peak_over_estimate": max(ratios, default=None),
                           "median_peak_over_estimate": statistics.median(ratios) if ratios else None,
                           "max_estimate_over_peak": max((1 / x for x in ratios if x), default=None),
                           "estimate_over_peak_distribution": sorted(1 / x for x in ratios if x)}
        summaries.append(entry)
    policy = Counter()
    for row in rows:
        for model, decisions in (row.get("profiles") or {}).items():
            for d in decisions:
                policy[(row["role"], row["schedule"], row["representation"], model, d["profile"], d["status"],
                        d["reason"], d["false_admission"], d["false_refusal"])] += 1
    return {"schema": SCHEMA, "rows": len(rows), "statuses": dict(Counter(r["status"] for r in rows)),
            "groups": summaries, "policy_counts": [dict(zip(
                ("role", "schedule", "representation", "model", "profile", "status", "reason", "false_admission", "false_refusal", "rows"),
                (*key, value))) for key, value in policy.items()],
            "production_estimator_accepted": False,
            "acceptance_note": "Diagnostic evidence only; full gate review and full regression required.",
            "real_workload_compatibility": "not measured"}


def make_jobs(args):
    jobs = []
    for family in args.families:
        for k in args.supports:
            for context in args.contexts:
                role = "calibration" if family in CALIBRATION else "heldout-structural"
                jobs.append({"case_id": f"{family}-k{k}-{context}", "family": family, "k": k,
                             "context": context, "role": role, "seed": 20260827 if role == "calibration" else 20260828})
    if args.corpora:
        from scripts.cm_deep_performance_audit import _records
        for corpus in args.corpora:
            for index, record in enumerate(_records(corpus)):
                k = int(record.get("live_k") or record.get("stratum_live_k") or record.get("sem_support_size"))
                jobs.append({"case_id": f"{corpus}-{index}", "family": str(record.get("circuit", corpus)),
                             "k": k, "context": "frozen", "role": "benchmark-corpus-reused",
                             "seed": None, "corpus": corpus, "record": record})
    expanded = []
    for job in jobs:
        for representation in REPRESENTATIONS:
            for schedule in args.schedules:
                for repetition in range(args.repetitions if schedule == "cold" else 1):
                    expanded.append({**job, "representation": representation, "schedule": schedule,
                                     "execution": args.execution,
                                     "cold_repetition": repetition,
                                     "repetitions": 1 if schedule == "cold" else args.repetitions})
    return expanded


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--execution", choices=["local-smoke", "runpod"], default="local-smoke")
    parser.add_argument("--supports", type=int, nargs="+", default=[6])
    parser.add_argument("--families", choices=CALIBRATION + HELDOUT, nargs="+", default=["mixed-chain"])
    parser.add_argument("--contexts", choices=["none", "half", "all"], nargs="+", default=["none"])
    parser.add_argument("--schedules", choices=["cold", "warm"], nargs="+", default=["cold"])
    parser.add_argument("--corpora", choices=["bx1", "b2", "epfl"], nargs="*", default=[])
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.child:
        raw = sys.stdin.read(MAX_JOB_BYTES + 1)
        if len(raw.encode()) > MAX_JOB_BYTES:
            raise ValueError("job exceeds input cap")
        job = json.loads(raw)
        result = []
        def emit(row):
            print(json.dumps(row, allow_nan=False), flush=True)
        try:
            run_job(job, rows=result, emit=emit)
        except (AssertionError, MemoryError, ValueError, RecursionError) as exc:
            status = "exactness_failure" if isinstance(exc, AssertionError) else "oom" if isinstance(exc, MemoryError) else "refused"
            for row in incomplete_rows(job, result, status, str(exc)):
                emit(row)
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required")
    if not 1 <= args.repetitions <= 5 or any(k < 2 or k > MAX_K for k in args.supports):
        parser.error("supports must be 2..16; repetitions 1..5")
    if args.execution == "local-smoke":
        if (args.supports != [6] or args.repetitions != 1 or args.families != ["mixed-chain"]
                or args.contexts != ["none"] or args.schedules != ["cold"] or args.corpora):
            parser.error("local execution is restricted to the default tiny smoke; use authorized Runpod")
    elif not sys.platform.startswith("linux") or not os.environ.get("RUNPOD_POD_ID"):
        parser.error("nontrivial study requires a Runpod Linux environment")
    if args.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite: {args.output_dir}")
    jobs = make_jobs(args)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_json_exclusive(args.output_dir / "jobs.json", jobs)
    environment = {"schema": SCHEMA, "platform": platform.platform(), "python": sys.version,
                   "machine": platform.machine(), "processor": platform.processor(), "logical_cpus": os.cpu_count(),
                   "executable": sys.executable, "execution": args.execution, "command": sys.argv,
                   "packages": {}, "rss_definition": "process lifetime high-water, not window peak",
                   "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None}
    for name in ("numpy", "sympy", "pytest", "psutil"):
        try:
            environment["packages"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            environment["packages"][name] = None
    write_json_exclusive(args.output_dir / "environment.json", environment)
    source_paths = ["scripts/cm_memory_estimator_study.py", "bitset_backend.py", "cm_ir.py", "cm_normalize.py",
                    "cm_exprlib.py", "cm_expr_serde.py", "cmbench/output_budget.py", "cmbench/backends/bitset_engine.py",
                    "cmbench/__init__.py", "cmbench/backends/__init__.py", "cmbench/reporting/__init__.py",
                    "cmbench/reporting/provenance.py", "cmbench/reporting/summary_tables.py",
                    "cmbench/tracing/__init__.py", "cmbench/tracing/replay.py", "cmbench/tracing/schema.py",
                    "cmbench/tracing/sink.py", "cmbench/tracing/opportunity.py", "cmbench/tracing/workload_manifest.py"]
    if args.corpora:
        from scripts.cm_deep_performance_audit import CORPORA, SOURCE_PATHS
        source_paths.extend(SOURCE_PATHS)
        source_paths.extend(str(CORPORA[name].relative_to(ROOT)) for name in args.corpora)
    source_hashes = {path: sha256_file(ROOT / path) for path in sorted(set(source_paths))}
    write_json_exclusive(args.output_dir / "source-manifest.json", source_hashes)
    for path in source_hashes:
        snapshot = args.output_dir / "source_snapshot" / path
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        with snapshot.open("xb") as stream:
            stream.write((ROOT / path).read_bytes())
        if sha256_file(snapshot) != source_hashes[path]:
            raise RuntimeError("source changed during snapshot")
    all_rows = []
    started = time.monotonic()
    stopped = False
    with (args.output_dir / "raw.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for job_index, job in enumerate(jobs):
            remaining = 1200 - (time.monotonic() - started)
            base = {key: job[key] for key in ("case_id", "family", "role", "schedule", "representation")}
            if stopped or remaining <= 0:
                rows = incomplete_rows(job, [], "skipped", "campaign stop rule")
            else:
                try:
                    proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--child"],
                                          input=json.dumps(job), capture_output=True, text=True,
                                          timeout=min(30, remaining), cwd=ROOT)
                    if proc.returncode:
                        rows = parse_child_rows(proc.stdout)
                        rows.extend(incomplete_rows(job, rows, "error", proc.stderr[-2000:]))
                    else:
                        rows = parse_child_rows(proc.stdout)
                except subprocess.TimeoutExpired as exc:
                    rows = parse_child_rows(exc.stdout)
                    rows.extend(incomplete_rows(job, rows, "timeout", "isolated child deadline"))
                stopped = any(row["status"] == "exactness_failure" for row in rows)
            for row in rows:
                row["job_index"] = job_index
                if job["schedule"] == "cold":
                    row["repetition"] = job["cold_repetition"]
                stream.write(json.dumps(row, allow_nan=False) + "\n")
                stream.flush()
                all_rows.append(row)
    summary = summarize(all_rows)
    summary["source_unchanged"] = all(sha256_file(ROOT / p) == digest for p, digest in source_hashes.items())
    summary["elapsed_s"] = time.monotonic() - started
    write_json_exclusive(args.output_dir / "summary.json", summary)
    fields = ["role", "schedule", "representation", "window", "rows", "measured_comparable", "statuses", "legacy", "candidate"]
    with (args.output_dir / "summary.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in summary["groups"]:
            writer.writerow({k: json.dumps(v) if isinstance(v, dict) else v for k, v in row.items()})
    print(json.dumps({"rows": len(all_rows), "statuses": summary["statuses"], "source_unchanged": summary["source_unchanged"]}))
    return int(not summary["source_unchanged"] or any(row["status"] != "ok" for row in all_rows))


if __name__ == "__main__":
    raise SystemExit(main())
