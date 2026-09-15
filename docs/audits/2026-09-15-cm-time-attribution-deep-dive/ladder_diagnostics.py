"""Audit-local, opt-in diagnostic ladder. Never imported by production code.

Run from the exact-commit worktree with -B. Refuses to overwrite evidence.
Profiler/phase/memory runs are separate from whole-call measurement.
"""
from __future__ import annotations

import time
ENTRY_WALL, ENTRY_CPU = time.perf_counter(), time.process_time()
import argparse
import contextlib
import cProfile
import functools
import gc
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import platform
import pstats
import random
import statistics
import subprocess
import sys
import tracemalloc
from collections import defaultdict

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import bitset_backend as bb
import cm_ir as ir
import cm_expr_serde as serde
import cmbench.backends.bitset_engine as engine
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, eval_expr_tt
from cmbench.comparative.ir import expression_stats, cm_ir_stats, flat_program_record

IMPORT_WALL = time.perf_counter() - ENTRY_WALL
IMPORT_CPU = time.process_time() - ENTRY_CPU
TRACE = None


def timed_call(fn, *args, **kwargs):
    w, c = time.perf_counter(), time.process_time()
    value = fn(*args, **kwargs)
    return value, {"wall_s": time.perf_counter() - w, "cpu_s": time.process_time() - c}


def stage(phase, fn, *args, **kwargs):
    if TRACE is None:
        return fn(*args, **kwargs)
    return TRACE.call(phase, getattr(fn, "__qualname__", repr(fn)), fn, *args, **kwargs)


class ExclusiveTracer:
    """Nested spans: subtract child inclusive time from parent, including recursion.

    No change to diagnostics arguments or algorithm selection. Timing probe cost
    outside a child is charged to the parent or harness remainder. This pass is
    intentionally NOT an unbiased timing estimator for tiny helpers.
    """
    def __init__(self):
        self.stack = []
        self.phases = defaultdict(lambda: {"wall_s": 0.0, "cpu_s": 0.0, "calls": 0})
        self.helpers = defaultdict(lambda: {"self_wall_s": 0.0, "self_cpu_s": 0.0,
                                           "inclusive_wall_s": 0.0, "calls": 0})
        self.restore = []

    def call(self, phase, name, fn, *args, **kwargs):
        frame = [time.perf_counter(), time.process_time(), 0.0, 0.0]
        self.stack.append(frame)
        try:
            return fn(*args, **kwargs)
        finally:
            wall, cpu = time.perf_counter() - frame[0], time.process_time() - frame[1]
            self.stack.pop()
            own_w, own_c = wall - frame[2], cpu - frame[3]
            row = self.phases[phase]
            row["wall_s"] += own_w
            row["cpu_s"] += own_c
            row["calls"] += 1
            helper = self.helpers[name]
            helper["self_wall_s"] += own_w
            helper["self_cpu_s"] += own_c
            helper["inclusive_wall_s"] += wall
            helper["calls"] += 1
            if self.stack:
                self.stack[-1][2] += wall
                self.stack[-1][3] += cpu

    def patch(self, owner, name, phase):
        old = inspect.getattr_static(owner, name)
        is_static = isinstance(old, staticmethod)
        fn = old.__func__ if is_static else getattr(owner, name)
        @functools.wraps(fn)
        def wrapped(*a, **k):
            return self.call(phase, fn.__qualname__, fn, *a, **k)
        self.restore.append((owner, name, old))
        setattr(owner, name, staticmethod(wrapped) if is_static else wrapped)

    def __enter__(self):
        global TRACE
        if TRACE is not None:
            raise RuntimeError("nested global diagnostic scopes are not supported")
        TRACE = self
        targets = {
            ir: {
                "compile_expr_to_cm_ir": "compile_lifecycle",
                "compile_expr_to_cm_ir_cached": "compile_cache_lookup_and_lifecycle",
                "compile_expr_to_cm_ir_persistent": "persistent_cache_lookup_validation_and_lifecycle",
                "_persistent_digest": "structural_digest_hashing",
                "_sorted_unique_vars": "support_propagation",
                "materialize_hybrid_no_reinflate": "public_wrapper_lifecycle",
                "_cm_node_count": "public_budget_guard_source_traversal",
                "_effective_output_budget": "public_budget_guards",
                "estimate_explicit_output": "public_budget_guards",
                "decide_output_budget": "public_budget_guards",
                "require_output_budget": "public_budget_guards",
                "materialize_cm": "complete_materialization",
                "_materialize_ir_tagged": "numpy_materialization_and_execution",
                "align_to_vars": "basis_alignment",
                "align_to_vars_with_stats": "basis_alignment",
                "eval_cm_node_bitset": "cm_recursive_kernel_and_allocation",
                "eval_cm_node_flat": "kernel_and_intermediate_allocation_release",
                "eval_cm_node_words": "words_api_dispatch",
            },
            ir.CMIRBuilder: {
                "_shared_assoc_uids": "source_traversal_structural_uid",
                "build": "build_lifecycle",
                "_build_rec": "source_traversal_build_memo",
                "_intern": "keys_and_interning",
                "_node_uid": "intern_uid_lookup",
                "_adopt_foreign": "foreign_node_cache_adoption",
                "_live_vars_union": "support_propagation",
                "_canonicalize_commutative_args": "canonical_sort_and_keys",
                **{n: "rewrites_and_key_construction" for n in
                   ("make_and", "make_or", "make_xor", "make_eqv", "make_imp", "negate", "var", "const")},
            },
            bb: {
                "compile_flat": "lowering_cm_flat",
                "compile_expr_cse": "structural_cse_and_lowering",
                "compile_expr_flat": "lowering_occurrence_flat",
                "get_flat_program": "flat_cache_lookup",
                "get_expr_cse_program": "flat_cache_lookup",
                "get_expr_flat_program": "flat_cache_lookup",
                "_bind_flat_program": "restriction_key_validation_cache_and_binding",
                "build_bitset_env": "positional_masks_cache_and_construction",
                "_build_words_env_cached": "words_masks_cache_and_construction",
                "_compute_word_plan": "liveness_release_plan",
                "_last_use_releases": "liveness_release_plan",
                "_eval_prepared_flat": "kernel_and_intermediate_allocation_release",
                "eval_expr_bitset": "memo_ast_kernel_and_allocation",
                "eval_cm_node_flat": "kernel_and_intermediate_allocation_release",
                "eval_cm_node_bitset": "cm_recursive_kernel_and_allocation",
                "_eval_words": "words_execution_binding_scratch_and_integer_conversion",
                "bitset_to_bool_array": "packed_to_array_conversion",
            },
            # Imported aliases in the selector are distinct attributes: patch
            # them explicitly or public kernel self-time is mislabelled wrapper.
            engine: {
                "eval_cm_node_flat": "kernel_and_intermediate_allocation_release",
                "eval_cm_node_bitset": "cm_recursive_kernel_and_allocation",
                "eval_cm_node_words": "words_api_dispatch",
                "eval_expr_bitset": "memo_ast_kernel_and_allocation",
                "eval_expr_flat_bitset": "kernel_and_intermediate_allocation_release",
                "eval_expr_words_bitset": "words_api_dispatch",
            },
        }
        for owner, names in targets.items():
            for name, phase in names.items():
                self.patch(owner, name, phase)
        return self

    def __exit__(self, *_):
        global TRACE
        for owner, name, old in reversed(self.restore):
            setattr(owner, name, old)
        TRACE = None

    def record(self, total):
        phases = {name: dict(row) for name, row in self.phases.items()}
        phases["unresolved_harness_and_probe_remainder"] = {
            "wall_s": total["wall_s"] - sum(x["wall_s"] for x in phases.values()),
            "cpu_s": total["cpu_s"] - sum(x["cpu_s"] for x in phases.values()), "calls": None,
        }
        for row in phases.values():
            row["percent_of_phase_pass_caller_wall"] = 100 * row["wall_s"] / total["wall_s"]
        helpers = []
        for name, row in self.helpers.items():
            helpers.append({"helper": name, **row,
                            "mean_self_wall_s": row["self_wall_s"] / row["calls"]})
        return {"total": total, "exclusive_phases": phases,
                "helpers": sorted(helpers, key=lambda r: -r["self_wall_s"])}


def raw_recursive(expr, env):
    """Diagnostic-only uncached historical algorithm; current direct API memoizes."""
    mask = (1 << (1 << len(env))) - 1
    def rec(e):
        if isinstance(e, Var): return env[f"x{e.i}"]
        if isinstance(e, Not): return (~rec(e.a)) & mask
        if isinstance(e, And): return rec(e.a) & rec(e.b)
        if isinstance(e, Or): return rec(e.a) | rec(e.b)
        if isinstance(e, Xor): return rec(e.a) ^ rec(e.b)
        if isinstance(e, Imp): return ((~rec(e.a)) | rec(e.b)) & mask
        if isinstance(e, Eqv): return (~(rec(e.a) ^ rec(e.b))) & mask
        raise TypeError(type(e))
    return rec(expr)


def cases():
    spec = importlib.util.spec_from_file_location("audit_disclosed_cse_tests", ROOT / "tests/test_bitset_cse.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    output = []
    def add(name, expr, n, source, encoding=2):
        doc = serde.expr_to_json_dag(expr) if encoding == 2 else serde.expr_to_json(expr)
        payload = json.dumps(doc, sort_keys=True)
        stats = expression_stats(expr, unfolded_limit=100000)
        assert not stats["unfolded_capped"] and n <= 18
        output.append({"id": name, "n": n, "source": source, "payload": payload,
                       "encoding": encoding, "original_structure": stats})
    for seed in (0, 1):
        add(f"random-shared-seed{seed}-k8", mod._random_expr(random.Random(seed), 8, 20), 8,
            "tests/test_bitset_cse.py::test_cse_matches_raw_on_random_shared_expressions")
    for n in (3, 8, 12, 16):
        add(f"random-existing-k{n}", mod._random_expr(random.Random(1000+n), n, 24), n,
            "tests/test_bitset_cse.py::test_cse_bigint_and_words_arms_are_identical")
    h = Xor(Xor(Var(0), Var(1)), Var(2))
    add("shared-h", And(Or(h, Var(3)), Xor(h, Var(4))), 5,
        "tests/test_bitset_cse.py::test_cse_compiles_each_distinct_subtree_once")
    def make_h(): return Xor(Xor(Var(0), Var(1)), Var(2))
    add("equal-separate-h", And(Or(make_h(), Var(3)), Xor(make_h(), Var(4))), 5,
        "tests/test_bitset_cse.py::test_cse_compiles_each_distinct_subtree_once", encoding=1)
    chain = Var(0)
    for i in range(1, 12): chain = Xor(chain, Var(i))
    add("single-consumer-chain-k12", chain, 12,
        "tests/test_bitset_cse.py::test_fanout1_chains_do_flatten")
    for n in (4, 8, 16, 18):
        add(f"fixed-structure-output-k{n}", Imp(And(Var(0), Var(1)), Or(Var(2), Var(3))), n,
            "tests/test_prepared_flat_evaluation.py::test_prepared_expr_and_cm_evaluation_match_recursive_reference"
            + ("; disclosed width-only extension to18" if n == 18 else ""))
    return output


def clear_caches():
    bb.clear_bitset_env_cache()
    bb.clear_words_env_cache()
    ir.clear_cm_ir_compile_cache()
    ir.clear_cm_ir_persistent_cache()
    ir.clear_cm_ir_alignment_cache()


ARMS = ("raw_recursive", "memo_ast", "occurrence_flat", "cse_flat", "cm_common_flat",
        "bare_cm_flat", "cm_recursive", "public_cm", "public_cm_diag", "cse_words", "cm_words")


class Session:
    def __init__(self, case, arm):
        self.case, self.arm = case, arm
        self.names = tuple(f"x{i}" for i in range(case["n"]))
        self.expr = self.node = self.prog = self.prepared = self.env = None
        self.last_diag = None

    def setup(self):
        doc = stage("input_json_parse", json.loads, self.case["payload"])
        self.expr = stage("input_dag_decode_and_validation", serde.expr_from_json, doc)
        arm = self.arm
        if arm.startswith("cm_") or arm in ("bare_cm_flat", "public_cm", "public_cm_diag", "dense_cm"):
            self.node = ir.compile_expr_to_cm_ir(self.expr, reuse_cache=False, persistent_cache=False)
        if arm in ("raw_recursive", "memo_ast"):
            self.env = bb.build_bitset_env(self.names)
        elif arm == "occurrence_flat":
            self.prog = bb.get_expr_flat_program(self.expr)
        elif arm in ("cse_flat", "cse_words"):
            self.prog = bb.get_expr_cse_program(self.expr, flatten=True)
        elif arm == "cm_common_flat":
            self.prog = bb.get_flat_program(self.node)
        if arm in ("occurrence_flat", "cse_flat", "cm_common_flat"):
            template, mask = bb._bind_flat_program(self.prog, self.names, {})
            release = len(self.names) >= bb._FLAT_FREE_MIN_VARS and self.prog.n_slots >= bb._FLAT_FREE_MIN_SLOTS
            self.prepared = bb.PreparedFlatEvaluation(self.prog, template, mask, release)

    def execute(self):
        arm = self.arm
        if arm == "raw_recursive":
            return stage("raw_ast_kernel_and_allocation", raw_recursive, self.expr, self.env)
        if arm == "memo_ast": return bb.eval_expr_bitset(self.expr, self.env)
        if arm in ("occurrence_flat", "cse_flat", "cm_common_flat"): return self.prepared.evaluate()
        if arm == "bare_cm_flat": return bb.eval_cm_node_flat(self.node, self.names)
        if arm == "cm_recursive": return bb.eval_cm_node_bitset(self.node, self.names)
        if arm == "cse_words": return bb.eval_expr_words_cse(self.expr, self.names, flatten=True)
        if arm == "cm_words": return bb.eval_cm_node_words(self.node, self.names)
        if arm == "dense_cm":
            split = len(self.names)//2
            return ir.materialize_cm(self.node, self.names[:split], self.names[split:],
                                     materialize_mode="hybrid", hybrid_threshold=18, output_budget=None)
        self.last_diag = {"ir_timing_enabled": 1} if arm == "public_cm_diag" else None
        res = ir.materialize_hybrid_no_reinflate(self.node, self.names,
                diagnostics=self.last_diag, hybrid_threshold=18, flat_eval=True,
                words_eval=False, output_budget=None, max_full_output_vars=18)
        return res.bits

    def deliver(self, value, expected):
        if self.arm == "dense_cm":
            data = stage("dense_array_delivery", lambda: np.asarray(value, dtype=np.uint8).tobytes())
        else:
            data = stage("packed_integer_to_bytes_delivery", int(value).to_bytes,
                         ((1 << len(self.names)) + 7)//8, "little")
        def check():
            if data != expected: raise AssertionError("complete output mismatch")
        stage("common_complete_output_correctness_guard", check)
        return data

    def run(self, expected, *, setup, q=1):
        if setup: self.setup()
        data = None
        for _ in range(q): data = self.deliver(self.execute(), expected)
        return data


def graph_metrics(session):
    expr = session.expr
    estats = expression_stats(expr, unfolded_limit=100000)
    seen, stack, edges = set(), [expr], 0
    while stack:
        e = stack.pop()
        if id(e) in seen: continue
        seen.add(id(e))
        children = [getattr(e, k) for k in ("a", "b") if hasattr(e, k)]
        edges += len(children)
        stack.extend(children)
    out = {"source": {**estats, "object_dag_edges": edges},
           "basis_width": len(session.names),
           "delivered_bytes": (1 << len(session.names)) if session.arm == "dense_cm" else ((1 << len(session.names)) + 7)//8,
           "actual_input_encoding": session.case["encoding"]}
    if session.node is not None:
        nodes, pending = {}, [session.node]
        while pending:
            n = pending.pop()
            if id(n) in nodes: continue
            nodes[id(n)] = n
            pending.extend(n.args)
        out["cm"] = {**cm_ir_stats(session.node), "support_entries_sum": sum(len(n.vars) for n in nodes.values()),
                     "support_width_max": max(len(n.vars) for n in nodes.values()),
                     "node_shallow_plus_dict_bytes": sum(sys.getsizeof(n)+sys.getsizeof(n.__dict__) for n in nodes.values()),
                     "shallow_bytes_are_not_total_graph_retention": True}
        prog = bb.get_flat_program(session.node)
    elif session.prog is not None: prog = session.prog
    else: prog = None
    if prog is not None:
        out["flat"] = {**flat_program_record(prog), "n_slots": prog.n_slots,
                       "bound_cache_entries": len(prog.bound_cache)}
    out["mask_cache"] = bb.bitset_env_cache_stats()
    out["persistent_cache"] = ir.cm_ir_persistent_cache_stats()
    out["final_dense_materializations"] = 1 if session.arm == "dense_cm" else 0
    out["intermediate_materializations"] = None if session.arm == "dense_cm" else 0
    out["allocation_release_time_separable"] = False
    return out


def profile_record(fn):
    profiler = cProfile.Profile()
    profiler.runcall(fn)
    stats = pstats.Stats(profiler)
    rows = []
    for (file, line, name), (primitive, calls, own, cumulative, _) in stats.stats.items():
        rows.append({"file": file, "line": line, "helper": name, "calls": calls,
                     "primitive_calls": primitive, "self_s": own, "cumulative_s": cumulative,
                     "mean_self_s": own/calls if calls else None})
    return {"clock": "cProfile default elapsed timer; not phase CPU", "total_calls": stats.total_calls,
            "total_tt_s": stats.total_tt, "hot_helpers": sorted(rows, key=lambda x: -x["self_s"])[:40]}


def measure_cell(case, arm, expected, *, repeat=7, timing_samples=None):
    # Rotation/counterbalancing across arms is done by the suite. No profiling
    # libraries enabled during these first two timing treatments.
    cold, warm = timing_samples if timing_samples is not None else ([], [])
    if timing_samples is None:
        for _ in range(repeat):
            clear_caches()
            s = Session(case, arm)
            _, timing = timed_call(s.run, expected, setup=True)
            cold.append(timing)
            s.run(expected, setup=False)
            _, timing = timed_call(s.run, expected, setup=False, q=64)
            warm.append(timing)
    phase = []
    for treatment in ("cold", "resident_q64"):
        for _ in range(3):
            clear_caches()
            s = Session(case, arm)
            if treatment != "cold":
                s.run(expected, setup=True)
            with ExclusiveTracer() as tr:
                _, total = timed_call(s.run, expected, setup=treatment == "cold", q=1 if treatment == "cold" else 64)
            phase.append({"treatment": treatment, **tr.record(total)})
    clear_caches()
    prof_session = Session(case, arm)
    profile = profile_record(lambda: prof_session.run(expected, setup=True))
    clear_caches()
    gc.collect()
    mem_session = Session(case, arm)
    tracemalloc.start()
    before = tracemalloc.get_traced_memory()[0]
    data = mem_session.run(expected, setup=True)
    current, peak = tracemalloc.get_traced_memory()
    snap = tracemalloc.take_snapshot()
    tracemalloc.stop()
    memory = {"traced_current_bytes_delta": current-before, "traced_peak_bytes_delta": peak-before,
              "cumulative_allocated_bytes": None, "native_rss_bytes": None,
              "retention_scope": "result + session Expr/CM/FlatProgram + module caches still alive",
              "top_retained_locations": [{"trace": str(x.traceback), "bytes": x.size, "count": x.count}
                                         for x in snap.statistics("lineno")[:12]]}
    metrics = graph_metrics(mem_session)
    return {"case": case["id"], "arm": arm, "status": "exact_complete_output_match",
            "source": case["source"], "comparison_class": "same packed-byte output" if arm != "dense_cm" else "dense-output contract comparison",
            "uninstrumented": {"cold_q1": cold, "resident_q64": warm}, "phase_passes": phase,
            "cprofile_separate_pass": profile, "memory_separate_pass": memory, "metrics": metrics,
            "output_sha256": hashlib.sha256(data).hexdigest(), "output_bytes": len(data)}


def check_baseline():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if commit != "e334de594262059cc18cf37eaab56b0f79e94843": raise RuntimeError("wrong commit")
    for mod in (bb, ir, serde):
        if not Path(mod.__file__).resolve().is_relative_to(ROOT): raise RuntimeError("wrong import origin")
    return commit


def startup_measurements():
    rows = []
    for _ in range(3):
        start = time.perf_counter()
        p = subprocess.run([sys.executable, "-B", str(Path(__file__)), "--startup"], cwd=ROOT,
                           capture_output=True, text=True, check=True, timeout=60)
        wall = time.perf_counter()-start
        child = json.loads(p.stdout)
        rows.append({"caller_process_delivery_wall_s": wall, **child,
                     "startup_transport_shutdown_and_unmeasured_import_residual_wall_s": wall-child["entry_to_payload_wall_s"]})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--startup", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.startup:
        print(json.dumps({"imports_from_script_entry_wall_s": IMPORT_WALL,
                          "imports_from_script_entry_cpu_s": IMPORT_CPU,
                          "entry_to_payload_wall_s": time.perf_counter()-ENTRY_WALL,
                          "child_process_cpu_s": time.process_time(), "status": "loaded"}))
        return
    commit = check_baseline()
    if args.output is None or args.output.exists(): raise ValueError("new --output path required")
    if not args.output.resolve().is_relative_to(AUDIT): raise ValueError("output must be in this audit")
    start = time.perf_counter()
    selected = cases()[:1] if args.smoke else cases()
    records, cells = [], []
    for index, case in enumerate(selected):
        expr = serde.expr_from_json(json.loads(case["payload"]))
        # Independent vector truth oracle outside all measured scopes.
        truth = eval_expr_tt(expr, case["n"]).astype(np.uint8).reshape(-1)
        expected = np.packbits(truth, bitorder="little").tobytes()
        arms = list(ARMS)
        if case["n"] < 6: arms = [x for x in arms if x not in ("cse_words", "cm_words")]
        if args.smoke: arms = ["memo_ast", "cse_flat", "cm_common_flat", "public_cm"]
        for arm in arms:
            cells.append((case, arm, expected))
        if not args.smoke and case["id"] in ("fixed-structure-output-k4", "fixed-structure-output-k16"):
            cells.append((case, "dense_cm", truth.tobytes()))
    samples = {(c["id"], arm): ([], []) for c, arm, _ in cells}
    schedule = []
    # Complete ALL uninstrumented timings first. Rotate and reverse the entire
    # declared cell order on successive repetitions; store that exact schedule.
    for rep in range(2 if args.smoke else 7):
        offset = rep % len(cells)
        ordered = cells[offset:] + cells[:offset]
        if rep % 2: ordered = list(reversed(ordered))
        for case, arm, expected in ordered:
            if time.perf_counter()-start > 1800: raise TimeoutError("30 minute suite bound")
            clear_caches()
            s = Session(case, arm)
            _, timing = timed_call(s.run, expected, setup=True)
            samples[(case["id"], arm)][0].append(timing)
            s.run(expected, setup=False)
            _, timing = timed_call(s.run, expected, setup=False, q=64)
            samples[(case["id"], arm)][1].append(timing)
            schedule.append({"repeat": rep, "case": case["id"], "arm": arm})
        print(f"finished uninstrumented repetition {rep+1}", flush=True)
    for case, arm, expected in cells:
        if time.perf_counter()-start > 1800: raise TimeoutError("30 minute suite bound")
        before = time.perf_counter()
        records.append(measure_cell(case, arm, expected, timing_samples=samples[(case["id"], arm)]))
        if time.perf_counter()-before > 60: raise TimeoutError("60 second cell bound")
        print(f"finished {case['id']}: {len(records)} cells", flush=True)
    result = {"schema": "cm-time-attribution-ladder/v1", "classification": "diagnostic_only",
              "baseline_commit": commit, "python": sys.version, "executable": sys.executable,
              "platform": platform.platform(), "numpy": np.__version__,
              "cpu_timer_resolution_s": time.get_clock_info("process_time").resolution,
              "cpu_note": "Windows small phase samples may be zero from CPU clock granularity; retain zeros, do not infer free work",
              "plan_sha256": hashlib.sha256((AUDIT/"PLAN.md").read_bytes()).hexdigest(),
              "startup_separate_process_pass": startup_measurements(),
              "ordering": "all uninstrumented cells before any profiling; declared cell order rotates/reverses across repetitions",
              "uninstrumented_schedule": schedule,
              "elapsed_suite_s": time.perf_counter()-start,
              "records": records}
    # Exclusive creation prevents accidental evidence rewrite.
    with args.output.open("x", encoding="utf-8") as f: json.dump(result, f, indent=2)
    if args.output.stat().st_size > 100*1024*1024: raise RuntimeError("artifact bound")
    print(json.dumps({"output": str(args.output), "cells": len(records), "elapsed_s": result["elapsed_suite_s"]}))


if __name__ == "__main__":
    main()
