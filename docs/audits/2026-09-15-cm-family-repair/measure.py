"""Bounded successor diagnostic worker. Each invocation imports one checkout."""
import time
ENTRY = time.perf_counter()
import argparse
import cProfile
import gc
import hashlib
import inspect
import json
from pathlib import Path
import pstats
import statistics
import sys
import tracemalloc
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument("--repo", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--blocks", type=int, default=7)
args = parser.parse_args()
assert 1 <= args.blocks <= 21
assert not args.output.exists()
sys.path.insert(0, str(args.repo.resolve()))
import numpy as np
import bitset_backend as bb
import cm_ir as ir
import cm_bench as bench
from cm_exprlib import Var, And, Or, Imp, Xor, random_expr
from cm_expr_serde import expr_to_json_dag
from cmbench.expr.eval import eval_expr_assignment
from cmbench.config import BenchmarkConfig
from cmbench.output_budget import OutputBudget

IMPORTED = time.perf_counter() - ENTRY
common = Imp(And(Var(0), Var(1)), Or(Var(2), Var(3)))
h = Xor(Xor(Xor(Var(0), Var(1)), Var(2)), Var(3))
shared = And(Xor(h, Var(4)), Xor(h, Var(5)))
families = {}
for name, seed, size in [("shared_block_mix", 2, 8), ("composition_mix", 3, 5)]:
    families[name] = bench.generate_expression_family(
        4, np.random.default_rng(seed), 3, "mixed_no_constants",
        family_size=size, variant_style=name, shared_blocks=3 if seed == 2 else 4,
        force_shared_substructure=True)
simple = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))
families["identical"] = {"base_expr": simple, "variants": [simple]*8, "shared_blocks": []}
config = BenchmarkConfig(sizes=(4,), trials=1, seed=0, max_depth=3,
                         cm_flat_eval=True, cm_use_persistent_cache=True,
                         family_no_robdd=True, no_dd=True, no_robdd_dd=True)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def reference(expr, names, fixed=None):
    """Independent scalar oracle, at most 64 KiB of explicit uint8 output."""
    assert (1 << len(names)) <= 65536
    fixed = fixed or {}
    result = 0
    for row in range(1 << len(names)):
        assignment = {v: (row >> (len(names)-1-i)) & 1 for i, v in enumerate(names)}
        assignment.update(fixed)
        result |= int(bool(eval_expr_assignment(expr, assignment))) << row
    return result


def check_result(result, want):
    if result.bits is not None:
        assert int(result.bits) == want
    else:
        actual = sum(int(v) << i for i, v in enumerate(result.tt))
        assert actual == want
    return True


def run_cell(name, fn, check, repeat=64, reset=None, metadata=None):
    if reset: reset()
    value = fn()
    check(value)
    for _ in range(2):
        if reset: reset()
        for _ in range(repeat):
            fn()
    wall, cpu = [], []
    enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(args.blocks):
            if reset: reset()
            w, c = time.perf_counter(), time.process_time()
            for _ in range(repeat):
                value = fn()
            dt, dc = time.perf_counter()-w, time.process_time()-c
            assert dt <= 10 * repeat
            wall.append(dt)
            cpu.append(dc)
            check(value)
    finally:
        if enabled: gc.enable()
    if reset: reset()
    profile = cProfile.Profile()
    value = profile.runcall(fn)
    check(value)
    stats = pstats.Stats(profile).stats
    hot = sorted([{"file": Path(k[0]).name, "line": k[1], "helper": k[2],
                   "primitive_calls": v[0], "calls": v[1], "self_profile_s": v[2],
                   "inclusive_profile_s": v[3]} for k,v in stats.items()],
                 key=lambda x: -x["self_profile_s"])[:15]
    del value
    if reset: reset()
    gc.collect()
    tracemalloc.start()
    start = tracemalloc.get_traced_memory()[0]
    value = fn()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    check(value)
    assert peak-start < (1 << 30)
    return {"id": name, "repetitions_per_block": repeat, "block_wall_s": wall,
            "block_cpu_s": cpu, "median_wall_s": statistics.median(wall)/repeat,
            "median_cpu_s": statistics.median(cpu)/repeat, "exact": True,
            "profile_separate": hot, "python_memory_separate": {
                "current_bytes": current-start, "peak_bytes": peak-start,
                "scope": "retained result and caches after one call; no observer nodes retained"},
            "metadata": metadata or {}}


def shape(expr):
    node = ir.compile_expr_to_cm_ir(expr)
    prog = bb.get_flat_program(node)
    nodes, edges, support, pending = set(), 0, 0, [node]
    while pending:
        n = pending.pop()
        if id(n) in nodes: continue
        nodes.add(id(n)); edges += len(n.args); support += len(n.vars)
        pending.extend(n.args)
    return {"input_hash": digest(expr_to_json_dag(expr)), "cm_nodes": len(nodes),
            "cm_edges": edges, "support_entries": support, "live_width": len(node.vars),
            "flat_slots": prog.n_slots, "flat_instructions": len(prog.ops),
            "key_hash": digest(node.key), "program_hash": digest([prog.ops, prog.loads])}


def main():
    cells = []
    with ir.evaluation_defaults_scope(flat_eval=True, words_eval=False):
        cases = [("packed4", common, 4, 16, False, False),
                 ("words16", common, 16, 16, True, False),
                 ("fallback8", random_expr(8, np.random.default_rng(2026), max_depth=5,
                                           p_unary=.25), 8, 4, False, False),
                 ("reduced20", Or(Var(0), Var(19)), 20, 16, False, True)]
        for label, expr, n, threshold, words, reduced in cases:
            node = ir.compile_expr_to_cm_ir(expr)
            names = tuple(f"x{i}" for i in range(n))
            out = node.vars if reduced else names
            want = reference(expr, out)
            budget = OutputBudget(max_output_bytes=65536, max_output_vars=16,
                                  allow_reduced_output=reduced)
            for mode in ("fast", "generic", "counts", "timing", "profile"):
                diag = None if mode in ("fast","generic") else (
                    {} if mode == "counts" else {"ir_timing_enabled":1})
                if mode == "profile": diag["cached_exec_profile_enabled"] = 1
                def invoke(diag=diag, mode=mode):
                    return ir.materialize_hybrid_no_reinflate(
                        node, names, fixed={}, diagnostics=diag,
                        hybrid_threshold=threshold, flat_eval=not words, words_eval=words,
                        flat_fast_path=mode != "generic", allow_reduced_output=reduced,
                        max_full_output_vars=16, output_budget=budget)
                cells.append(run_cell(label+"/"+mode, invoke,
                                      lambda r: check_result(r, want),
                                      metadata=shape(expr) | {"output_bytes": ((1<<len(out))+7)//8,
                                                             "contract": "explicit API only"}))
            if not reduced:
                env = bb.build_bitset_env(names)
                for mode, fn in [
                    ("direct_bitset", lambda: bb.eval_expr_bitset(expr, env)),
                    ("cse_flat", lambda: bb.eval_expr_flat_cse(expr, names, flatten=True)),
                    ("bare_cm", lambda: bb.eval_cm_node_flat(node, names))]:
                    cells.append(run_cell(label+"/"+mode, fn,
                                          lambda r: r == want or (_ for _ in ()).throw(AssertionError()),
                                          metadata={"contract":"complete packed output"}))
        for label, expr in [("shared", shared), ("simple",simple)]:
            canonical = ir.compile_expr_to_cm_ir(expr).key
            for persistent in (False, True):
                def compile_one():
                    return ir.compile_expr_to_cm_ir(expr, persistent_cache=persistent)
                cells.append(run_cell(f"compile/{label}/persistent{persistent}", compile_one,
                    lambda n: n.key == canonical or (_ for _ in ()).throw(AssertionError()),
                    repeat=1, reset=ir.clear_cm_ir_persistent_cache, metadata=shape(expr)))
            ir.clear_cm_ir_persistent_cache()
            ir.compile_expr_to_cm_ir(expr, persistent_cache=True)
            cells.append(run_cell(f"compile/{label}/root_hit",
                lambda: ir.compile_expr_to_cm_ir(expr, persistent_cache=True),
                lambda n: n.key == canonical or (_ for _ in ()).throw(AssertionError()),
                metadata=shape(expr)))
        for label, family in families.items():
            refs = [bb.bitset_to_bool_array(reference(e, ("x0","x1","x2","x3")),4)
                    for e in family["variants"]]
            for persistent in (False,True):
                prefix = "family_cm_cache" if persistent else "family_cm_no_cache"
                rng = np.random.default_rng(4)
                def invoke_family():
                    return bench._cm_family_workload(family["variants"],4,
                        persistent_cache=persistent,tt_refs=refs,sample_rng=rng,config=config)
                cells.append(run_cell(f"family/{label}/persistent{persistent}", invoke_family,
                    lambda r: r[prefix+"_ok_rate"] == 1 or (_ for _ in ()).throw(AssertionError()),
                    repeat=4, metadata={"input_hashes":[shape(e)["input_hash"] for e in family["variants"]],
                                       "contract":"legacy instrumented family, references supplied"}))
        # Separate call-count pass: no profiling timings added to whole-call data.
        prepass = ir.CMIRBuilder._shared_assoc_uids
        with patch.object(ir.CMIRBuilder,"_shared_assoc_uids",side_effect=prepass) as observed:
            ir.clear_cm_ir_persistent_cache()
            ir.compile_expr_to_cm_ir(shared,persistent_cache=True)
            cold = observed.call_count
            ir.compile_expr_to_cm_ir(shared,persistent_cache=True)
            warm = observed.call_count-cold
        frozen_shapes = {name:[shape(e) for e in f["variants"]] for name,f in families.items()}
        return {"cells":cells,"separate_call_counts":{"shared_miss_prepasses":cold,
                 "shared_hit_prepasses":warm},"family_shapes":frozen_shapes}


try:
    result = main()
except BaseException as exc:
    with args.output.open("x",encoding="utf-8") as f:
        json.dump({"error":repr(exc),"elapsed_s":time.perf_counter()-ENTRY},f)
    raise
result.update({"python":sys.version,"numpy":np.__version__,"repo":str(args.repo),
               "imports_and_startup_from_python_entry_s":IMPORTED,
               "suite_wall_s":time.perf_counter()-ENTRY,
               "source_hashes":{name:hashlib.sha256((args.repo/name).read_bytes()).hexdigest()
                                for name in ["cm_ir.py","cm_bench.py","bitset_backend.py"]},
               "notice":"development diagnostic; separate timings/profile/memory; GC off in timed blocks"})
with args.output.open("x",encoding="utf-8") as f:
    json.dump(result,f,indent=2,sort_keys=True); f.write("\n")
print(json.dumps({"cells":len(result["cells"]),"suite_s":result["suite_wall_s"],
                  "output":str(args.output)}))
