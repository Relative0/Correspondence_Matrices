"""Host-drift follow-up: alternating independent module/cache instances.

This is a resident diagnostic, separate from the fresh-process worker series.
Only unchanged helper modules are shared; baseline/candidate CM caches and
module defaults are independent. No package/source files are rewritten.
"""
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time
import gc
import hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT.parent / "cm-time-attribution-20260915"
sys.path.insert(0,str(ROOT))
import numpy as np
import cm_ir as candidate_ir
import cm_bench as candidate_bench
from cm_exprlib import And, Or, Imp, Xor, Var, random_expr
from cmbench.config import BenchmarkConfig
from cmbench.output_budget import OutputBudget


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


baseline_ir=load("repair_baseline_ir",BASE/"cm_ir.py")
# Bind the baseline harness's from-imports to its own IR, then restore the
# ordinary import immediately. Both harnesses share unchanged evaluator helpers.
sys.modules["cm_ir"]=baseline_ir
try:
    baseline_bench=load("repair_baseline_bench",BASE/"cm_bench.py")
finally:
    sys.modules["cm_ir"]=candidate_ir
for module in (baseline_ir,candidate_ir):
    module.set_flat_eval_default(True)
    module.set_words_eval_default(False)

rows=[]
cfg=BenchmarkConfig(sizes=(4,),trials=1,seed=2,max_depth=3,cm_flat_eval=True,
    cm_use_persistent_cache=True,no_dd=True,no_robdd_dd=True,family_no_robdd=True)


def measure(label,functions,check,repeat=64,resets=None):
    resets=resets or [lambda:None,lambda:None]
    for f,reset in zip(functions,resets):
        for _ in range(2):
            reset()
            for _ in range(repeat):
                value=f()
            check(value)
    samples=[[],[]]
    enabled=gc.isenabled()
    gc.disable()
    try:
        for block in range(21):
            for index in ([0,1] if block%2==0 else [1,0]):
                resets[index]()
                w,c=time.perf_counter_ns(),time.process_time_ns()
                for _ in range(repeat):
                    value=functions[index]()
                cpu,wall=time.process_time_ns()-c,time.perf_counter_ns()-w
                check(value)
                samples[index].append({"block":block,"wall_ns":wall,"cpu_ns":cpu})
    finally:
        if enabled:gc.enable()
    medians=[statistics.median(s["wall_ns"] for s in treatment)/repeat for treatment in samples]
    rows.append({"id":label,"repetitions":repeat,"baseline":samples[0],"candidate":samples[1],
        "baseline_median_ns":medians[0],"candidate_median_ns":medians[1],
        "candidate_over_baseline":medians[1]/medians[0],"exact":True})


common=Imp(And(Var(0),Var(1)),Or(Var(2),Var(3)))
for label,expr,width,threshold,words,reduced in [
    ("packed4",common,4,7,False,False),
    ("words16",common,16,7,True,False),
    ("fallback8",random_expr(8,np.random.default_rng(2026),max_depth=5,p_unary=.25),8,4,False,False),
    ("reduced20",Or(Var(0),Var(19)),20,7,False,True)]:
    names=tuple(f"x{i}" for i in range(width))
    nodes=[m.compile_expr_to_cm_ir(expr) for m in (baseline_ir,candidate_ir)]
    for mode in (True,False):
        functions=[lambda m=m,n=n: m.materialize_hybrid_no_reinflate(n,names,
            hybrid_threshold=threshold,flat_eval=not words,words_eval=words,
            flat_fast_path=mode,allow_reduced_output=reduced,max_full_output_vars=16,
            output_budget=budget) for m,n in zip((baseline_ir,candidate_ir),nodes)]
        budget=OutputBudget(max_output_bytes=65536,max_output_vars=16,allow_reduced_output=reduced)
        expected=functions[0]()
        def check(v):
            assert tuple(v.output_vars)==tuple(expected.output_vars)
            assert v.status.value==expected.status.value
            if expected.bits is not None: assert v.bits==expected.bits
            else: assert np.array_equal(v.tt,expected.tt)
        measure(f"{label}/fast{mode}",functions,check)

h=Xor(Xor(Xor(Var(0),Var(1)),Var(2)),Var(3))
shared=And(Xor(h,Var(4)),Xor(h,Var(5)))
for persistent in (False,True):
    functions=[lambda m=m:m.compile_expr_to_cm_ir(shared,persistent_cache=persistent)
               for m in (baseline_ir,candidate_ir)]
    key=functions[0]().key
    def check(n):assert n.key==key
    measure(f"compile/shared/persistent{persistent}",functions,check,repeat=1,
        resets=[m.clear_cm_ir_persistent_cache for m in (baseline_ir,candidate_ir)])

families={style:candidate_bench.generate_expression_family(4,np.random.default_rng(seed),3,
    "mixed_no_constants",family_size=size,variant_style=style,shared_blocks=blocks,
    force_shared_substructure=True) for style,seed,size,blocks in
    [("shared_block_mix",2,8,3),("composition_mix",3,5,4)]}
simple=Or(And(Var(0),Var(1)),Xor(Var(2),Var(3)))
families["identical"]={"variants":[simple]*8}
for name,family in families.items():
    refs=[candidate_bench.eval_expr_tt(e,4).astype(np.uint8).reshape(-1) for e in family["variants"]]
    for persistent in (False,True):
        rngs=[np.random.default_rng(4),np.random.default_rng(4)]
        functions=[lambda m=m,r=r:m._cm_family_workload(family["variants"],4,
            persistent_cache=persistent,tt_refs=refs,sample_rng=r,config=cfg)
            for m,r in zip((baseline_bench,candidate_bench),rngs)]
        prefix="family_cm_cache" if persistent else "family_cm_no_cache"
        def check(v):assert v[prefix+"_ok_rate"]==1
        measure(f"family/{name}/persistent{persistent}",functions,check,repeat=4)

dest=HERE/sys.argv[1]
with dest.open("x",encoding="utf-8") as f:
    json.dump({"schema":"cm-repair-resident-pairs-v1","cells":rows,
        "treatment":"two independent CM modules/caches; alternating within resident process",
        "scope":"diagnostic host-drift follow-up; no profile/tracemalloc in measured cells",
        "source_hashes":{label:{name:hashlib.sha256((root/name).read_bytes()).hexdigest()
            for name in ["cm_ir.py","cm_bench.py","bitset_backend.py"]}
            for label,root in [("baseline",BASE),("candidate",ROOT)]}},f,indent=2)
    f.write("\n")
print(json.dumps({"cells":len(rows),"output":str(dest)}))
