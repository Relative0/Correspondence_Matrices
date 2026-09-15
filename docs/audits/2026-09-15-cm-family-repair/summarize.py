"""Recompute successor tables from immutable local diagnostic records."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent


def read(name):
    return json.loads((HERE/name).read_text(encoding="utf-8"))


def write(name,text):
    with (HERE/name).open("x",encoding="utf-8") as f:
        f.write(text)


suffix = "-v2" if "--v2" in sys.argv else ""
a,b=read(f"final-resident-a{suffix}.json"),read(f"final-resident-b{suffix}.json")
paired=[]
for x,y in zip(a["cells"],b["cells"],strict=True):
    assert x["id"]==y["id"] and x["exact"] and y["exact"]
    values=[x,y]
    margin=50000 if x["id"].startswith("family/") else 2000
    changes=[v["candidate_median_ns"]-v["baseline_median_ns"] for v in values]
    row={"id":x["id"],"runs":[{k:v[k] for k in
         ("baseline_median_ns","candidate_median_ns","candidate_over_baseline")} for v in values],
        "material_slowdown_both_runs":all(delta>margin and v["candidate_over_baseline"]>1.05
             for delta,v in zip(changes,values)),
        "direction_consistent":all(d<0 for d in changes) or all(d>=0 for d in changes)}
    paired.append(row)

mechanism_name="MECHANISMS-final-v3.json" if suffix else "MECHANISMS-final-v2.json"
mechanisms=read(mechanism_name)
phase_summaries={}
for name,case in mechanisms["family"].items():
    records=case["phases"]
    for axis in ("wall","cpu"):
        assert sum(r[f"exclusive_{axis}_ns"] for r in records)==records[0][f"{axis}_ns"]
    phases=defaultdict(lambda:{"calls":0,"exclusive_wall_ns":0,"exclusive_cpu_ns":0})
    for r in records:
        item=phases[r["phase"]]
        item["calls"]+=1
        item["exclusive_wall_ns"]+=r["exclusive_wall_ns"]
        item["exclusive_cpu_ns"]+=r["exclusive_cpu_ns"]
    for item in phases.values():
        item["pct_capture_wall"]=100*item["exclusive_wall_ns"]/records[0]["wall_ns"]
    phase_summaries[name]=dict(phases)

fresh=[read(f"final-fresh-a{suffix}.json"),read(f"final-fresh-b{suffix}.json")]
for record in fresh:
    assert len(record["cells"])==41 and all(c["exact"] for c in record["cells"])
    assert record["separate_call_counts"]=={"shared_miss_prepasses":1,"shared_hit_prepasses":1}
assert read("baseline-a.json")["separate_call_counts"]["shared_miss_prepasses"]==2
assert fresh[0]["family_shapes"]==read("baseline-a.json")["family_shapes"]

interactions=[]
for record in (a,b):
    cells={c["id"]:c for c in record["cells"]}
    for name in ("packed4","words16","fallback8","reduced20"):
        fast,generic=(cells[f"{name}/fast{x}"] for x in (True,False))
        interactions.append({"case":name,"run":1 if record is a else 2,
            "difference_in_differences_ns":
                (fast["candidate_median_ns"]-fast["baseline_median_ns"])
                -(generic["candidate_median_ns"]-generic["baseline_median_ns"]),
            "meaning":"fast branch change minus generic branch change; no additive causal phase claim"})

known_worker_seconds=sum(read(p.name).get("suite_wall_s",0)
    for p in HERE.glob("*.json") if p.name.startswith(("baseline-","candidate-","final-fresh-")))
profile={"schema":"cm-family-repair-results-v1","scientific_disposition_changed":False,
    "resident_comparisons":paired,"wrapper_interactions":interactions,
    "exclusive_family_phase_summaries":phase_summaries,
    "mechanism_measurements":mechanisms,
    "fresh_timing_profile_memory_records":[f"final-fresh-a{suffix}.json",f"final-fresh-b{suffix}.json"],
    "known_fresh_worker_wall_s_including_imports_and_separate_profile_memory":known_worker_seconds,
    "budget":"under five minutes of local measurement execution including resident/trace passes; two-hour limit",
    "limitations":["fresh-worker drift prevents broad causal speed claims",
        "process CPU resolution is coarse on this host; zero samples are not free work",
        "cProfile default elapsed clock is not process CPU; inclusive entries overlap",
        "native/RSS/allocation counts unavailable; Python retained and peak bytes are separate passes",
        "initial worker mislabeled cProfile fields as CPU; retained unchanged",
        "fallback8 output_bytes in worker metadata is packed-equivalent (32), actual TT delivery is 256 bytes",
        "words16 bare/CSE controls are bigint; public words-vs-bare-flat is an engine comparison",
        "family benchmark comparison includes newly delivered provenance, so its total change is a harness-contract increment"],
    "source_hashes":mechanisms["source_hashes"]}
write(f"PROFILE_RESULTS{suffix}.json",json.dumps(profile,indent=2,sort_keys=True)+"\n")

lines=["# Time ledger","","All measurements are local development diagnostics. Negative differences mean less wall time.",
"Resident pairs alternate independent baseline/candidate CM modules and caches within one process. Each run uses 21 blocks.",
"The baseline and candidate have identical inputs, requested outputs and engine settings. Family rows additionally deliver new provenance.",
"","## Resident caller observations","",
"| Case | Baseline A, us | Candidate A, us | Candidate/baseline A | B | Material slowdown in both? |",
"|---|---:|---:|---:|---:|---|"]
for r in paired:
    x,y=r["runs"]
    lines.append(f'| {r["id"]} | {x["baseline_median_ns"]/1000:.2f} | {x["candidate_median_ns"]/1000:.2f} | {x["candidate_over_baseline"]:.3f} | {y["candidate_over_baseline"]:.3f} | {r["material_slowdown_both_runs"]} |')
lines += ["","## Independent fresh-worker absolute times","",
"These describe final source behavior; do not interpret their difference from earlier worker medians as an exclusive phase.",
"CPU uses the sum of block process-CPU samples divided by total calls. Raw samples, profile counts and memory are in the two worker records.",
"","| Case | Wall A, us | Wall B, us | CPU A, us/call | Wall block min–max A, us/call |","|---|---:|---:|---:|---:|"]
for x,y in zip(fresh[0]["cells"],fresh[1]["cells"],strict=True):
    repeat=x["repetitions_per_block"]
    cpu=sum(x["block_cpu_s"])/len(x["block_cpu_s"])/repeat*1e6
    lo,hi=(v/repeat*1e6 for v in (min(x["block_wall_s"]),max(x["block_wall_s"])))
    lines.append(f'| {x["id"]} | {x["median_wall_s"]*1e6:.2f} | {y["median_wall_s"]*1e6:.2f} | {cpu:.2f} | {lo:.2f}–{hi:.2f} |')
lines += ["","## Exclusive phase passes","",
"One instrumented capture per family; these percentages use that capture alone. Compile residual includes building/adoption/support plus unobserved control. Parent exclusive time includes harness work and observer overhead."]
for name,phases in phase_summaries.items():
    case=mechanisms["family"][name]
    lines += ["",f"### {name}","",
        f'Outer caller: {case["caller_wall_ns"]/1e6:.4f} ms wall, {case["caller_cpu_ns"]/1e6:.4f} ms CPU. Outside nested capture: {case["outside_capture_wall_ns"]/1e6:.4f} ms wall.',
        "","| Phase (exclusive) | Calls | Wall, ms | CPU, ms | Capture wall % |","|---|---:|---:|---:|---:|"]
    for name,item in sorted(phases.items(),key=lambda p:-p[1]["exclusive_wall_ns"]):
        lines.append(f'| {name} | {item["calls"]} | {item["exclusive_wall_ns"]/1e6:.4f} | {item["exclusive_cpu_ns"]/1e6:.4f} | {item["pct_capture_wall"]:.2f} |')
write(f"TIME_LEDGER{suffix}.md","\n".join(lines)+"\n")
print(json.dumps({"resident_cells":len(paired),"fresh_cells_per_run":41,
    "material_resident_slowdowns":[r["id"] for r in paired if r["material_slowdown_both_runs"]],
    "known_fresh_worker_seconds":known_worker_seconds}))
