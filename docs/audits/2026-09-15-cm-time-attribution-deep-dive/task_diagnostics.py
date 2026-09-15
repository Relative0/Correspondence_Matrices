"""Audit-local task attribution; no production changes or default entry-point effects.

Run only after the root audit permits measurement. ``--list`` only lists cells.
Output directories must be new. Historical helper source is loaded by exact hash;
its imports resolve against the pinned worktree, not the dirty source checkout.
"""
from __future__ import annotations

import argparse
import cProfile
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pstats
import statistics
import subprocess
import sys
import time
import tracemalloc
from dataclasses import dataclass
from typing import Any, Callable

AUDIT = Path(__file__).resolve().parent
BASE = AUDIT.parents[2]
SOURCE = Path("C:/Users/brian/Documents/CM_Computation")
HELPER_REL = "cmbench/comparative/sympy_cm_claim_cleanup.py"
INPUT_REL = "docs/audits/2026-09-15-cm-sympy-claim-cleanup/FROZEN_INPUTS.json"
HELPER_HASH = "47ca5daf1d402e7c2c7e30140727699f0a67eb996f30d3688f219e803a666bd5"
sys.path.insert(0, str(BASE))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_runtime():
    if sha(SOURCE / HELPER_REL) != HELPER_HASH:
        raise ValueError("historical helper source changed")
    spec = importlib.util.spec_from_file_location("audit_historical_y02_y05", SOURCE / HELPER_REL)
    assert spec and spec.loader
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    import bitset_backend as bitset
    import cm_ir
    import cm_exprlib
    import cm_bench
    import numpy as np
    import sympy as sp
    for module in (bitset, cm_ir, cm_exprlib, cm_bench):
        if Path(module.__file__).resolve().parent != BASE:
            raise ValueError(f"unexpected baseline import origin: {module.__file__}")
    return helper, bitset, cm_ir, cm_exprlib, cm_bench, np, sp


RUNTIME = None


def runtime():
    global RUNTIME
    if RUNTIME is None:
        RUNTIME = load_runtime()
    return RUNTIME


def inputs():
    doc = json.loads((SOURCE / INPUT_REL).read_text(encoding="utf-8"))
    names = {case["case_id"] for case in doc["cases"]}
    if names != {"absorption-k4", "contradiction-k4", "majority-k6", "balanced-k8"}:
        raise ValueError("unexpected development input membership")
    return doc


class Phases:
    """Sequential stage spans; never mixes nested inclusive values into sums."""
    def __init__(self, enabled=False):
        self.enabled = enabled
        self.rows: dict[str, dict[str, int]] = {}

    def call(self, name: str, fn: Callable[[], Any]):
        if not self.enabled:
            return fn()
        wall = time.perf_counter_ns()
        cpu = time.process_time_ns()
        value = fn()
        cpu = time.process_time_ns() - cpu
        wall = time.perf_counter_ns() - wall
        row = self.rows.setdefault(name, {"wall_ns": 0, "cpu_ns": 0, "calls": 0})
        row["wall_ns"] += wall
        row["cpu_ns"] += cpu
        row["calls"] += 1
        return value


@dataclass(slots=True)
class BatchNode:
    kind: str
    op: str | None = None
    args: tuple = ()
    var_name: str | None = None
    const_value: int | None = None


def batch_adapter(expr, *, structural: bool):
    """Same historical evaluator interface, with no CM metadata or rewrites."""
    _, _, _, ex, *_ = runtime()
    memo, intern = {}, {}
    tags = {ex.And: "AND", ex.Or: "OR", ex.Xor: "XOR", ex.Imp: "IMP", ex.Eqv: "EQV"}

    def build(cur):
        if id(cur) in memo:
            return memo[id(cur)]
        if isinstance(cur, ex.Var):
            key = ("var", cur.i)
            candidate = BatchNode("var", var_name=f"x{cur.i}")
        elif isinstance(cur, ex.Not):
            child = build(cur.a)
            key = ("not", id(child))
            candidate = BatchNode("not", args=(child,))
        else:
            left, right = build(cur.a), build(cur.b)
            tag = tags[type(cur)]
            key = (tag, id(left), id(right))
            candidate = BatchNode("op", op=tag, args=(left, right))
        if structural:
            candidate = intern.setdefault(key, candidate)
        memo[id(cur)] = candidate
        return candidate
    return build(expr)


def reset_caches():
    _, bs, cm, *_ = runtime()
    bs.clear_bitset_env_cache()
    bs.clear_words_env_cache()
    cm.clear_cm_ir_persistent_cache()
    cache = getattr(cm, "_COMPILED_IR_CACHE", None)
    if cache is not None:
        cache.clear()


def primitive_prepare(program, names, fixed):
    _, bs, *_ = runtime()
    template, mask = bs._bind_flat_program(program, tuple(names), fixed)
    return bs.PreparedFlatEvaluation(program, template, mask, False)


def packed_program(expr, arm, phases):
    _, bs, cm, *_ = runtime()
    if arm.startswith("cm"):
        node = phases.call("cm_representation_compile", lambda: cm.compile_expr_to_cm_ir(
            expr, reuse_cache=False, persistent_cache=False, share_aware_flatten=True))
        return phases.call("lowering", lambda: bs.compile_flat(node))
    return phases.call("structural_cse_lowering", lambda: bs.compile_expr_cse(expr, flatten=True))


def scalar_values(expr, n):
    return runtime()[0].scalar_truth_values(expr, n)


def fixture_case(name):
    return next(c for c in inputs()["cases"] if c["case_id"] == name)


def oracle_for(cell):
    helper, _, _, _, _, _, sp = runtime()
    if cell["task"] == "family":
        family = family_for(cell["case"])
        return [scalar_values(e, 4) for e in family["variants"]]
    case = fixture_case(cell["case"])
    expr = helper.parse_expression(case["expression"])
    n = case["n_vars"]
    values = scalar_values(expr, n)
    task = cell["task"]
    if task == "assignment_batch":
        rows = helper.assignment_rows(inputs()["assignment_generator"], n)
        return helper.assignment_output(expr, n, rows)
    if task == "restriction":
        outputs = []
        from cmbench.expr.eval import eval_expr_assignment
        for fixed in contexts(n, cell["q"]):
            remaining = [f"x{i}" for i in range(n) if f"x{i}" not in fixed]
            output = []
            for row in range(1 << len(remaining)):
                assignment = {name: (row >> (len(remaining)-1-j)) & 1 for j, name in enumerate(remaining)}
                assignment.update(fixed)
                output.append(int(eval_expr_assignment(expr, assignment)))
            outputs.append(helper.pack_values(output))
        return outputs
    if task == "exact_count":
        return sum(values)
    if task == "sat_status":
        return any(values)
    if task == "equivalence_status":
        right = helper.parse_expression(case["comparison_expression"])
        return values == scalar_values(right, n)
    if task == "simplified_expression":
        return helper.packed_digest(values)
    raise ValueError(task)


def contexts(n, q):
    # Disclosed expression, restriction treatment. Every cofactor delivered.
    # The four two-variable contexts cycle at q64; this explicitly tests reuse.
    return [{"x0": (j >> 1) & 1, "x1": j & 1} for j in range(q)]


def ensure(condition, message="exact output mismatch"):
    if not condition:
        raise AssertionError(message)


def task_operation(cell, oracle, phases):
    helper, bs, cm, ex, bench, np, sp = runtime()
    document = phases.call("input_document_loading_json_decode", inputs)
    case = next(c for c in document["cases"] if c["case_id"] == cell["case"])
    n = case["n_vars"]
    arm, task = cell["arm"], cell["task"]
    expr = phases.call("input_parse", lambda: helper.parse_expression(case["expression"]))
    names = phases.call("variable_basis_mapping", lambda: tuple(f"x{i}" for i in range(n)))
    metadata = {}
    if task == "assignment_batch":
        raw_rows = phases.call("supplied_assignment_loading", lambda: helper.assignment_rows(document["assignment_generator"], n))
        if arm in {"raw_batch", "cse_batch", "cm_batch"}:
            node = phases.call("cm_representation_compile" if arm == "cm_batch" else "batch_adapter_prepare", lambda:
                cm.compile_expr_to_cm_ir(expr, reuse_cache=False, persistent_cache=False, share_aware_flatten=True)
                if arm == "cm_batch" else batch_adapter(expr, structural=arm == "cse_batch"))
            values = phases.call("assignment_binding_kernel_array_to_list", lambda: helper._cm_batch_values(node, raw_rows, n))
        else:
            converted = phases.call("sympy_conversion", lambda: helper._sympy_expression(expr, n))
            symbols = phases.call("variable_basis_mapping", lambda: [sp.Symbol(name) for name in names])
            function = phases.call("sympy_lambdify", lambda: sp.lambdify(symbols, converted, modules="numpy", cse=arm.endswith("on")))
            assignments = phases.call("assignment_binding", lambda: np.frombuffer(raw_rows, dtype=np.uint8).reshape(-1, n).astype(bool, copy=False))
            native = phases.call("execution_kernel", lambda: function(*[assignments[:, i] for i in range(n)]))
            values = phases.call("array_to_list", lambda: helper._normalize_vector(native, len(raw_rows)//n))
        output = phases.call("packed_conversion", lambda: helper.pack_values(values))
        phases.call("correctness_guard", lambda: ensure(values == oracle))
        metadata["assignment_rows"] = len(values)
    elif task == "restriction":
        program = packed_program(expr, arm, phases)
        query_contexts = phases.call("restriction_context_construction", lambda: contexts(n, cell["q"]))
        output = []
        for fixed in query_contexts:
            remaining = phases.call("variable_basis_mapping", lambda: tuple(name for name in names if name not in fixed))
            prepared = phases.call("mask_context_binding", lambda: primitive_prepare(program, remaining, fixed))
            bits = phases.call("execution_kernel", prepared.evaluate)
            output.append(phases.call("packed_conversion", lambda: bits.to_bytes(max(1, (1 << len(remaining))//8), "little")))
        phases.call("correctness_guard", lambda: ensure(output == oracle))
        metadata["contexts_unique"] = len({tuple(sorted(c.items())) for c in query_contexts})
        metadata["query_count"] = cell["q"]
    elif task in {"exact_count", "sat_status", "equivalence_status", "simplified_expression"}:
        if arm.startswith("sympy"):
            converted = phases.call("sympy_conversion", lambda: helper._sympy_expression(expr, n))
            if task == "sat_status":
                from sympy.logic.inference import satisfiable
                model = phases.call("sat_solver", lambda: satisfiable(converted, algorithm="dpll2"))
                output = model is not False
                if output:
                    witness = [int(bool(model.get(sp.Symbol(name), False))) for name in names]
                    from cmbench.expr.eval import eval_expr_assignment
                    phases.call("witness_guard", lambda: ensure(bool(eval_expr_assignment(expr, dict(zip(names, witness))))))
            elif task == "equivalence_status":
                from sympy.logic.inference import satisfiable
                right = phases.call("input_parse", lambda: helper.parse_expression(case["comparison_expression"]))
                right_sp = phases.call("sympy_conversion", lambda: helper._sympy_expression(right, n))
                output = phases.call("sat_miter_solver", lambda: satisfiable(sp.Xor(converted, right_sp, evaluate=False), algorithm="dpll2") is False)
            elif task == "simplified_expression":
                output = phases.call("sympy_simplify_logic", lambda: sp.simplify_logic(converted, form="dnf", force=arm.endswith("forced")))
            else:
                from sympy.logic.boolalg import truth_table
                symbols = [sp.Symbol(name) for name in names]
                output = phases.call("sympy_exhaustive_count", lambda: sum(int(bool(v)) for v in truth_table(converted, symbols, input=False)))
        else:
            program = packed_program(expr, arm, phases)
            prepared = phases.call("mask_context_binding", lambda: primitive_prepare(program, names, {}))
            bits = phases.call("execution_kernel", prepared.evaluate)
            if task == "exact_count":
                output = phases.call("packed_count", bits.bit_count)
            elif task == "sat_status":
                output = phases.call("packed_status", lambda: bool(bits))
                if output:
                    row = (bits & -bits).bit_length()-1
                    witness = [(row >> (n-1-i)) & 1 for i in range(n)]
                    from cmbench.expr.eval import eval_expr_assignment
                    phases.call("witness_guard", lambda: ensure(bool(eval_expr_assignment(expr, dict(zip(names, witness))))))
            elif task == "equivalence_status":
                right = phases.call("input_parse", lambda: helper.parse_expression(case["comparison_expression"]))
                right_program = packed_program(right, arm, phases)
                right_prepared = phases.call("mask_context_binding", lambda: primitive_prepare(right_program, names, {}))
                right_bits = phases.call("execution_kernel", right_prepared.evaluate)
                output = phases.call("packed_status", lambda: bits == right_bits)
            else:
                def minterm_rows():
                    return [[(row >> (n-1-i)) & 1 for i in range(n)] for row in range(1 << n) if (bits >> row) & 1]
                minterms = phases.call("minterm_materialization", minterm_rows)
                symbols = phases.call("variable_basis_mapping", lambda: [sp.Symbol(name) for name in names])
                output = phases.call("shared_sympy_minimizer", lambda: sp.SOPform(symbols, minterms))
        if task == "simplified_expression":
            text = phases.call("expression_serialization", lambda: sp.srepr(output).encode("utf-8"))
            semantic = phases.call("correctness_guard", lambda: helper.packed_digest(helper._sympy_values(output, n)))
            ensure(semantic == oracle)
            metadata["quality"] = phases.call("expression_quality_guard", lambda: helper.expression_quality(output))
            output = text
        else:
            phases.call("correctness_guard", lambda: ensure(output == oracle))
    else:
        raise ValueError(task)
    if isinstance(output, bytes):
        delivered = output
    elif isinstance(output, list) and all(isinstance(item, bytes) for item in output):
        delivered = phases.call("output_delivery", lambda: b"".join(output))
    else:
        delivered = phases.call("status_serialization", lambda: helper.canonical_bytes({"value": output}))
    digest = phases.call("delivery_digest", lambda: hashlib.sha256(delivered).hexdigest())
    return {"correct": True, "output_bytes": len(delivered), "output_sha256": digest, **metadata}


def family_for(name):
    _, _, _, _, bench, np, _ = runtime()
    common = dict(family_size=8, variant_style="shared_block_mix", shared_blocks=3, force_shared_substructure=True)
    if name == "shared_seed2":
        return bench.generate_expression_family(4, np.random.default_rng(2), 3, "mixed_no_constants", **common)
    if name == "composition_seed3":
        return bench.generate_expression_family(4, np.random.default_rng(3), 3, "mixed_no_constants", family_size=5, variant_style="composition_mix", force_shared_substructure=True)
    if name == "identical_seed2":
        family = family_for("shared_seed2")
        family["variants"] = [family["base_expr"]] * 8
        return family
    if name.startswith("mutation_seed3_"):
        rate = float(name.rsplit("_", 1)[1])
        return bench.generate_expression_family(4, np.random.default_rng(3), 3, "mixed_no_constants", family_size=5, variant_style="subtree_mutation", mutation_rate=rate, force_shared_substructure=False)
    raise ValueError(name)


def family_config():
    from cmbench.config import BenchmarkConfig
    return BenchmarkConfig(sizes=(4,), trials=1, seed=2, max_depth=3,
                           cm_words_eval=True, cm_flat_eval=True, cm_hybrid_threshold=16,
                           cm_use_persistent_cache=True, no_dd=True, no_robdd_dd=True,
                           family_no_robdd=True, sampled_correctness=0)


def family_operation(cell, oracle, phases):
    helper, bs, cm, ex, bench, np, sp = runtime()
    family = phases.call("fixture_ingress_family_generation", lambda: family_for(cell["case"]))
    variants = family["variants"]
    arm = cell["arm"]
    cache = arm.endswith("cache_on")
    refs = phases.call("public_reference_construction", lambda: [ex.eval_expr_tt(e, 4).astype(np.uint8).reshape(-1) for e in variants])
    if arm.startswith("public"):
        phases.call("public_family_structural_diagnostics", lambda: bench.expression_family_diagnostics(
            family, 4, family_id=cell["case"], variant_style="diagnostic_disclosed_treatment", mutation_rate=0.15))
        legacy = phases.call("public_family_inclusive", lambda: bench._cm_family_workload(
            variants, 4, persistent_cache=cache, tt_refs=refs,
            sample_rng=np.random.default_rng(4), config=family_config()))
        prefix = "family_cm_cache" if cache else "family_cm_no_cache"
        phases.call("correctness_guard", lambda: ensure(legacy[prefix+"_ok_rate"] == 1))
        output = helper.pack_values([value for ref in refs for value in ref.tolist()])
        return {"correct": True, "output_bytes": len(output), "output_sha256": hashlib.sha256(output).hexdigest(),
                "legacy_fields": legacy, "delivery_contract": "public family statistics; relation delivery used only for internal guard"}
    outputs = []
    diagnostics = []
    phases.call("persistent_cache_clear", cm.clear_cm_ir_persistent_cache)
    for expr, expected in zip(variants, oracle):
        if arm == "cse_family":
            program = phases.call("structural_cse_lowering", lambda: bs.compile_expr_cse(expr, flatten=True))
        else:
            diag = {} if phases.enabled else None
            node = phases.call("cm_compile_including_reuse_management", lambda: cm.compile_expr_to_cm_ir(expr, diagnostics=diag, reuse_cache=False, persistent_cache=cache))
            if diag is not None:
                diagnostics.append(diag)
            program = phases.call("lowering", lambda: bs.get_flat_program(node))
        prepared = phases.call("mask_context_binding", lambda: primitive_prepare(program, ("x0", "x1", "x2", "x3"), {}))
        bits = phases.call("execution_kernel", prepared.evaluate)
        data = phases.call("packed_conversion", lambda: bits.to_bytes(2, "little"))
        phases.call("correctness_guard", lambda: ensure(data == helper.pack_values(expected)))
        outputs.append(data)
    output = phases.call("output_delivery", lambda: b"".join(outputs))
    return {"correct": True, "output_bytes": len(output), "output_sha256": hashlib.sha256(output).hexdigest(),
            "cache_counts": {"hits": sum(d.get("ir_persistent_cache_hits", 0) for d in diagnostics),
                             "misses": sum(d.get("ir_persistent_cache_misses", 0) for d in diagnostics),
                             "final_entries": len(cm._PERSISTENT_IR_CACHE),
                             "lookup_wall_ns": None, "validation_wall_ns": None, "eviction_wall_ns": None},
            "delivery_contract": "complete packed output for every variant"}


def execute(cell, oracle, phase=False):
    stages = Phases(phase)
    start_wall, start_cpu = time.perf_counter_ns(), time.process_time_ns()
    result = family_operation(cell, oracle, stages) if cell["task"] == "family" else task_operation(cell, oracle, stages)
    elapsed_cpu = time.process_time_ns()-start_cpu
    elapsed_wall = time.perf_counter_ns()-start_wall
    if phase:
        known_wall = sum(r["wall_ns"] for r in stages.rows.values())
        known_cpu = sum(r["cpu_ns"] for r in stages.rows.values())
        ensure(known_wall <= elapsed_wall, "phase wall spans overlap")
        ensure(known_cpu <= elapsed_cpu, "phase CPU spans overlap")
        stages.rows["unresolved_python_bookkeeping"] = {"wall_ns": elapsed_wall-known_wall, "cpu_ns": elapsed_cpu-known_cpu, "calls": 1}
        for row in stages.rows.values():
            row["wall_percent_caller"] = 100*row["wall_ns"]/elapsed_wall
            row["cpu_percent_caller"] = None if not elapsed_cpu else 100*row["cpu_ns"]/elapsed_cpu
    return {"wall_ns": elapsed_wall, "cpu_ns": elapsed_cpu, "phases": stages.rows, "result": result}


def structural_metrics(cell):
    helper, bs, cm, *_ = runtime()
    if cell["task"] == "family":
        expressions = family_for(cell["case"])["variants"]
        n = 4
    else:
        case = fixture_case(cell["case"])
        n = case["n_vars"]
        expressions = [helper.parse_expression(case["expression"])]
    rows = []
    for expr in expressions:
        seen, stack, edges = set(), [expr], 0
        while stack:
            cur = stack.pop()
            if id(cur) in seen:
                continue
            seen.add(id(cur))
            children = (cur.a, cur.b) if hasattr(cur, "b") else (cur.a,) if hasattr(cur, "a") else ()
            edges += len(children)
            stack.extend(children)
        def occurrences(cur):
            return 1+(occurrences(cur.a)+occurrences(cur.b) if hasattr(cur, "b") else occurrences(cur.a) if hasattr(cur, "a") else 0)
        unfolded = occurrences(expr)
        node = cm.compile_expr_to_cm_ir(expr, reuse_cache=False, persistent_cache=False)
        cm_nodes, stack = {}, [node]
        while stack:
            cur = stack.pop()
            if id(cur) in cm_nodes:
                continue
            cm_nodes[id(cur)] = cur
            stack.extend(cur.args)
        cse = bs.compile_expr_cse(expr, flatten=True)
        flat = bs.compile_flat(node)
        rows.append({"source_dag_nodes": len(seen), "source_dag_edges": edges, "source_occurrences": unfolded,
                     "identity_sharing_factor": unfolded/len(seen), "cm_nodes": len(cm_nodes),
                     "cm_support_sizes": [len(cur.vars) for cur in cm_nodes.values()],
                     "cm_support_total": sum(len(cur.vars) for cur in cm_nodes.values()),
                     "live_variables": len(node.vars), "requested_basis": n,
                     "cse_program": bs.program_metrics(cse), "cm_program": bs.program_metrics(flat)})
    return rows


def all_cells():
    rows = []
    for case in ("absorption-k4", "balanced-k8"):
        for arm in ("raw_batch", "cse_batch", "cm_batch", "sympy_cse_off", "sympy_cse_on"):
            rows.append(dict(case=case, task="assignment_batch", arm=arm, q=1))
    for q in (1, 64):
        for arm in ("cse_packed", "cm_packed"):
            rows.append(dict(case="balanced-k8", task="restriction", arm=arm, q=q))
    for task in ("exact_count", "sat_status", "equivalence_status"):
        for case in ("contradiction-k4", "balanced-k8"):
            for arm in ("cse_packed", "cm_packed", "sympy_task"):
                rows.append(dict(case=case, task=task, arm=arm, q=1))
    for case in ("absorption-k4", "balanced-k8"):
        for arm in ("cse_shared_minimizer", "cm_shared_minimizer", "sympy_default", "sympy_forced"):
            rows.append(dict(case=case, task="simplified_expression", arm=arm, q=1))
    for case in ("identical_seed2", "shared_seed2", "composition_seed3", "mutation_seed3_0", "mutation_seed3_0.15", "mutation_seed3_1"):
        for arm in ("cse_family", "cm_cache_off", "cm_cache_on", "public_cache_off", "public_cache_on"):
            rows.append(dict(case=case, task="family", arm=arm, q=1))
    for row in rows:
        row["id"] = f"{row['task']}__{row['case']}__{row['arm']}__q{row['q']}"
        row["treatment"] = "resident_imports_cold_session; q64 compile-once within session" if row["q"] == 64 else "resident_imports_cold_session"
    return rows


def worker(cell, repeats, precomputed=None):
    boot_wall, boot_cpu = time.perf_counter_ns(), time.process_time_ns()
    runtime()
    import_wall, import_cpu = time.perf_counter_ns()-boot_wall, time.process_time_ns()-boot_cpu
    oracle = oracle_for(cell)
    samples, phase_samples = list(precomputed or []), []
    if precomputed is None:
        for _ in range(repeats):
            reset_caches()
            samples.append(execute(cell, oracle))
    for _ in range(3):
        reset_caches()
        phase_samples.append(execute(cell, oracle, phase=True))
    reset_caches()
    profile = cProfile.Profile()
    profile.enable()
    profiled = execute(cell, oracle)
    profile.disable()
    stats = pstats.Stats(profile)
    helpers = []
    for (filename, line, function), (primitive, total, self_s, cumulative_s, callers) in stats.stats.items():
        helpers.append({"file": filename, "line": line, "function": function,
                        "primitive_calls": primitive, "total_calls": total,
                        "self_wall_s": self_s, "cumulative_wall_s": cumulative_s,
                        "mean_self_wall_s": self_s/total if total else None})
    helpers.sort(key=lambda r: r["self_wall_s"], reverse=True)
    reset_caches()
    gc.collect()
    tracemalloc.start()
    before = tracemalloc.take_snapshot()
    memory_result = execute(cell, oracle)
    current, peak = tracemalloc.get_traced_memory()
    after = tracemalloc.take_snapshot()
    growth = after.compare_to(before, "filename")
    tracemalloc.stop()
    memory = {"current_traced_bytes": current, "peak_traced_bytes": peak,
              "net_traced_bytes": sum(row.size_diff for row in growth),
              "cumulative_allocated_bytes": None, "native_rss_bytes": None,
              "semantics": "Python-traced allocations still reachable after result return; cache retention included; native allocations incomplete",
              "top_net_growth": [{"file": str(row.traceback[0].filename), "bytes": row.size_diff, "objects": row.count_diff} for row in growth[:12]]}
    med = statistics.median(row["wall_ns"] for row in samples)
    return {"cell": cell, "status": "ok", "source": {"helper_sha256": HELPER_HASH, "input_sha256": sha(SOURCE / INPUT_REL)},
            "runtime_preload": {"wall_ns": import_wall, "cpu_ns": import_cpu},
            "uninstrumented": samples, "phase_pass": phase_samples,
            "summary": {"wall_median_ns": med, "cpu_median_ns": statistics.median(row["cpu_ns"] for row in samples),
                        "phase_dilation": statistics.median(row["wall_ns"] for row in phase_samples)/med},
            "profile": {"caller_wall_ns": profiled["wall_ns"], "hot_helpers": helpers[:35]},
            "memory_pass": memory, "structure": structural_metrics(cell),
            "inseparable": {"allocation_release_in_kernel_ns": None, "cache_lookup_ns": None, "cache_validation_ns": None,
                            "process_startup_ns": None, "json_source_read_ns": None},
            "correctness": {"every_sample_exact": all(r["result"]["correct"] for r in samples+phase_samples),
                            "oracle": "independent scalar exhaustive outside timed cell"}}


def grouped_cells():
    groups = {}
    for cell in all_cells():
        groups.setdefault((cell["task"], cell["case"], cell["q"]), []).append(cell)
    return list(groups.values())


def group_worker(cells, repeats):
    started_wall, started_cpu = time.perf_counter_ns(), time.process_time_ns()
    runtime()
    preload = {"wall_ns": time.perf_counter_ns()-started_wall, "cpu_ns": time.process_time_ns()-started_cpu}
    oracles = {cell["id"]: oracle_for(cell) for cell in cells}
    sample_map = {cell["id"]: [] for cell in cells}
    orders = []
    # Every uninstrumented arm finishes all repeats before any phase/profile pass.
    for repetition in range(repeats):
        shift = repetition % len(cells)
        order = cells[shift:]+cells[:shift]
        if repetition % 2:
            order = list(reversed(order))
        orders.append([cell["arm"] for cell in order])
        for cell in order:
            reset_caches()
            result = execute(cell, oracles[cell["id"]])
            result["repetition"] = repetition
            sample_map[cell["id"]].append(result)
    results = []
    for cell in cells:
        result = worker(cell, repeats, precomputed=sample_map[cell["id"]])
        result["runtime_preload"] = preload
        result["uninstrumented_arm_orders"] = orders
        result["runtime_preload_scope"] = "once per matched task/case/query group; not additive across group arms"
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--worker", type=int)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-cells", type=int)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 7:
        parser.error("repeats must be 1..7")
    cells = all_cells()
    if args.list:
        print(json.dumps(cells, indent=2))
        return 0
    if args.worker is not None:
        result = group_worker(grouped_cells()[args.worker], args.repeats)
        print(json.dumps(result, separators=(",", ":"), allow_nan=False))
        return 0
    if args.output is None:
        parser.error("--output required; new directory only")
    output = args.output.resolve()
    if AUDIT not in output.parents:
        parser.error("output must be under this audit")
    output.mkdir(exist_ok=False)
    groups = grouped_cells()
    if args.max_cells is not None:
        groups = groups[:args.max_cells]
    start = time.perf_counter()
    records = []
    for index, group in enumerate(groups):
        if time.perf_counter()-start > 1800:
            records.extend({"cell": cell, "status": "not_run", "reason": "suite budget"} for cell in group)
            continue
        wall, cpu = time.perf_counter_ns(), time.process_time_ns()
        try:
            completed = subprocess.run([sys.executable, "-B", str(__file__), "--worker", str(index), "--repeats", str(args.repeats)],
                                       cwd=BASE, capture_output=True, text=True, timeout=60, check=False,
                                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
            if completed.returncode:
                group_records = [{"cell": cell, "status": "error", "error": completed.stderr[-12000:]} for cell in group]
            else:
                group_records = json.loads(completed.stdout)
        except subprocess.TimeoutExpired:
            group_records = [{"cell": cell, "status": "timeout", "reason": "60-second matched-group bound"} for cell in group]
        caller_wall, parent_cpu = time.perf_counter_ns()-wall, time.process_time_ns()-cpu
        for record in group_records:
            record["worker_caller_wall_ns"] = caller_wall
            record["parent_cpu_ns"] = parent_cpu
            record["worker_caller_scope"] = "all matched arms/repeats and phase/profile/memory/structure passes plus process; NOT a one-call latency or additive across arms"
            records.append(record)
        (output / f"{index:03d}.json").write_text(json.dumps(group_records, indent=2, allow_nan=False), encoding="utf-8")
        print(f"{index+1}/{len(groups)} {group_records[0]['status']} {group[0]['task']} {group[0]['case']} q{group[0]['q']}", flush=True)
    document = {"schema": "cm-time-attribution-task-diagnostics/v1", "base_commit": "e334de594262059cc18cf37eaab56b0f79e94843",
                "source_origin": str(SOURCE), "baseline_import_origin": str(BASE), "elapsed_s": time.perf_counter()-start,
                "repeats": args.repeats, "cells": records}
    (output / "TASK_RESULTS.json").write_text(json.dumps(document, indent=2, allow_nan=False), encoding="utf-8")
    return 0 if all(row["status"] == "ok" for row in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
