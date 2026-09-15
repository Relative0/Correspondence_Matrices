"""Separate phase, helper-count and cache-retention passes; no benchmark claims."""
import cProfile
from contextlib import ExitStack
import gc
import hashlib
import json
from pathlib import Path
import pstats
import sys
import time
import tracemalloc
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import bitset_backend as bb
import cm_ir as ir
import cm_bench as bench
import cmbench.backends.bitset_engine as engine
from cm_exprlib import And, Or, Imp, Xor, Var, Not
from cmbench.config import BenchmarkConfig
from cmbench.phase_timing import PhaseRecorder, timed_phase

DEST = HERE / (sys.argv[1] if len(sys.argv) > 1 else "MECHANISMS.json")
assert not DEST.exists()
cfg = BenchmarkConfig(sizes=(4,),trials=1,seed=2,max_depth=3,cm_flat_eval=True,
    cm_use_persistent_cache=True,no_dd=True,no_robdd_dd=True,family_no_robdd=True)
families = {style: bench.generate_expression_family(4,np.random.default_rng(seed),3,
    "mixed_no_constants",family_size=size,variant_style=style,
    shared_blocks=blocks,force_shared_substructure=True)
    for style,seed,size,blocks in [("shared_block_mix",2,8,3),("composition_mix",3,5,4)]}
simple = Or(And(Var(0),Var(1)),Xor(Var(2),Var(3)))
families["identical"] = {"base_expr":simple,"variants":[simple]*8,"shared_blocks":[]}


def snapshot_cache():
    # Called without any observer retaining nodes. All temporary references
    # disappear on return; returned data contains only scalars and dictionaries.
    union, weights = {}, []
    for root in ir._PERSISTENT_IR_CACHE.values():
        seen, stack = {}, [root]
        while stack:
            n = stack.pop()
            if id(n) in seen:
                continue
            seen[id(n)] = n
            stack.extend(n.args)
        weights.append(len(seen))
        union.update(seen)
    return {"entries":len(weights),"entry_reachable_node_weights":weights,
        "unique_reachable_nodes":len(union),
        "support_entries":sum(len(n.vars) for n in union.values()),
        "map_shallow_bytes":sys.getsizeof(ir._PERSISTENT_IR_CACHE),
        "node_shallow_bytes":sum(sys.getsizeof(n) for n in union.values()),
        "scope":"graph counts and shallow sizes; native allocation unknown"}


def source_shape(expr):
    seen, pending, edges = {}, [expr], 0
    while pending:
        node = pending.pop()
        if id(node) in seen:
            continue
        seen[id(node)] = node
        children = () if isinstance(node,Var) else (node.a,) if isinstance(node,Not) else (node.a,node.b)
        pending.extend(children)
        edges += len(children)
    uids, shared = ir.CMIRBuilder._shared_assoc_uids(expr)
    return {"source_dag_nodes":len(seen),"source_dag_edges":edges,
            "structural_classes":len(set(uids.values())),"shared_associative_classes":len(shared)}


def run_family(family, recorder=None):
    return bench.time_expression_family_workload(4,family,family_id="diagnostic",
        trial=0,expr_style="mixed_no_constants",variant_style="existing",
        mutation_rate=.15,bit_env=None,sample_rng=np.random.default_rng(4),
        robdd_order_seed=5,config=cfg,timing=recorder)


result = {"schema":"cm-family-repair-mechanisms-v1","family":{},"wrapper":{},
          "notice":"Instrumented development measurements; do not pool with timing workers."}
for label,family in families.items():
    trace = PhaseRecorder()
    w,c = time.perf_counter_ns(),time.process_time_ns()
    row = run_family(family,trace)
    cpu,wall = time.process_time_ns()-c,time.perf_counter_ns()-w
    assert row["family_cm_cache_correct_variants"] == len(family["variants"])
    records = trace.snapshot()["records"]
    observed = records[0]
    capture = {"caller_wall_ns":wall,"caller_cpu_ns":cpu,
        "source_shapes_separate":[source_shape(e) for e in family["variants"]],
        "outside_capture_wall_ns":wall-observed["wall_ns"],
        "outside_capture_cpu_ns":cpu-observed["cpu_ns"],
        "outside_capture_contents":"argument setup, wrapper activation, trace metadata/serialization, return",
        "phases":records,
        "cache_profiles":json.loads(row["family_cm_cache_cache_profile_json"])}
    for r in records:
        r["exclusive_pct_of_capture_wall"] = 100*r["exclusive_wall_ns"]/observed["wall_ns"]
    # cProfile is a different pass with no active phase recorder.
    profile = cProfile.Profile()
    profile.runcall(run_family,family)
    capture["helper_profile_separate"] = [{"file":Path(k[0]).name,"line":k[1],"helper":k[2],
        "primitive_calls":v[0],"calls":v[1],"self_profile_s":v[2],"inclusive_profile_s":v[3],
        "mean_self_profile_s":v[2]/v[1] if v[1] else None}
        for k,v in pstats.Stats(profile).stats.items()
        if k[2] in {"_persistent_digest","_shared_assoc_uids","_adopt_foreign","_intern",
                    "_cm_node_count","_bind_flat_program","_eval_prepared_flat",
                    "eval_cm_node_flat","cache_get","cache_put"}]
    # Isolated cache-only retained graph and allocation pass (no trace/cProfile).
    ir.clear_cm_ir_persistent_cache()
    gc.collect()
    tracemalloc.start()
    for expr in family["variants"]:
        ir.compile_expr_to_cm_ir_persistent(expr)
    gc.collect()
    current,peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    capture["cache_retention_separate"] = snapshot_cache() | {"traced_current_bytes":current,"traced_peak_bytes":peak}
    ir.clear_cm_ir_persistent_cache()
    del trace, row, records
    result["family"][label] = capture

common = Imp(And(Var(0),Var(1)),Or(Var(2),Var(3)))
for label,expr,width,threshold,words in [("packed4",common,4,7,False),
        ("words16",common,16,7,True),("fallback4",common,4,0,False)]:
    node = ir.compile_expr_to_cm_ir(expr)
    names = tuple(f"x{i}" for i in range(width))
    # Fill source-attached programs/bindings, including both wrapper modes.
    for mode in (True,False):
        ir.materialize_hybrid_no_reinflate(node,names,flat_eval=True,words_eval=words,
            hybrid_threshold=threshold,flat_fast_path=mode)
    for mode in (True,False):
        trace = PhaseRecorder()
        with ExitStack() as stack:
            for module,func,phase in [
                (engine,"select_cm_node_engine","engine_selection"),
                (engine,"eval_cm_node_flat","flat_evaluator_with_allocation"),
                (engine,"eval_cm_node_words","words_evaluator"),
                (ir,"_effective_output_budget","budget_configuration"),
                (ir,"_cm_node_count","node_count_cached"),
                (ir,"estimate_explicit_output","output_estimate"),
                (ir,"decide_output_budget","budget_decision"),
                (ir,"require_output_budget","budget_guard"),
                (bb,"get_flat_program","cm_lowering_cache"),
                (bb,"_bind_flat_program","flat_binding"),
                (bb,"_eval_prepared_flat","flat_kernel"),
                (bb,"_eval_words","words_binding_execution_conversion"),
                (ir,"materialize_ir","numpy_materialization"),
                (ir,"align_to_vars","output_alignment")]:
                stack.enter_context(patch.object(module,func,timed_phase(phase)(getattr(module,func))))
            with trace.activate(), trace.span("wrapper_api"):
                value = ir.materialize_hybrid_no_reinflate(node,names,flat_eval=True,
                    words_eval=words,hybrid_threshold=threshold,flat_fast_path=mode)
        result["wrapper"][f"{label}/fast{mode}"] = trace.snapshot()

# Stable cache extent across a bounded resident session; fixed policy, no eviction
# tuning. Separate from timing and tracing, so observed nodes cannot pin entries.
ir.clear_cm_ir_persistent_cache()
for expr in families["composition_mix"]["variants"]:
    ir.compile_expr_to_cm_ir_persistent(expr)
before = snapshot_cache()
for _ in range(64):
    for expr in families["composition_mix"]["variants"]:
        ir.compile_expr_to_cm_ir_persistent(expr)
after = snapshot_cache()
assert before == after
result["resident_retention"] = {"rounds":64,"before":before,"after":after,"stable":True}
result["source_hashes"] = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    for name in ["cm_ir.py","cm_bench.py","cmbench/phase_timing.py","bitset_backend.py"]}
with DEST.open("x",encoding="utf-8") as f:
    json.dump(result,f,indent=2,sort_keys=True)
    f.write("\n")
print(json.dumps({"families":len(result["family"]),"wrappers":len(result["wrapper"]),"exact":True}))
