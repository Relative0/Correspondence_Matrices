"""Verify bounded GF(2)-rank development artifacts."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cmbench.comparative.gf2_bounded_rank_experiment import METHODS, expected, prepare_c16_cases, summarize
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(run:Path)->dict:
    run=run.resolve(); results=json.loads((run/"results.json").read_text()); manifest=json.loads((run/"manifest.json").read_text())
    sources=manifest["local_sources"]
    required={"cmbench/recognition/gf2_bounded_rank.py","cmbench/comparative/gf2_bounded_rank_experiment.py","scripts/crse_bounded_rank_development_verify.py","docs/recognition/c16_linux_confirmation/c16_dataset.json"}
    if not required.issubset(sources): raise ValueError("bounded-rank manifest closure")
    for rel,digest in sources.items():
        path=(ROOT/rel).resolve()
        if not path.is_file() or sha(path)!=digest: raise ValueError(f"bounded-rank source {rel}")
    for rel,digest in manifest["artifacts"].items():
        if sha(run/rel)!=digest: raise ValueError("bounded-rank artifact")
    dataset=ROOT/results["dataset"]["path"]; cases=prepare_c16_cases(json.loads(dataset.read_text())); expected_hash={c["case_id"]:expected(c)[0] for c in cases}
    rows=[json.loads(line) for line in (run/"raw_measurements.jsonl").read_text().splitlines() if line]
    perf=[r for r in rows if r["role"]=="performance"]; mem=[r for r in rows if r["role"]=="memory_profile"]
    mismatch=sum(r["artifact_sha256"]!=expected_hash[r["case_id"]] or not r["exact_check_passed"] for r in rows)
    summary_mismatch=int(summarize(rows,results["config"]["development_speedup_gate"],results["config"]["pruning_gate"])!=results["summary"])
    if len(perf)!=160 or len(mem)!=18 or mismatch or summary_mismatch: raise ValueError("bounded-rank verification mismatch")
    output={"schema":"crse-bounded-rank-independent-verification/v1","status":"verified","run_id":results["run_id"],"checked_performance_sessions":len(perf),"checked_memory_profile_sessions":len(mem),"checked_local_sources":len(sources),"mismatches":0,"results_sha256":sha(run/"results.json"),"manifest_sha256":sha(run/"manifest.json"),"production_promotion":False}
    with (run/"independent_verification.json").open("x",encoding="utf-8") as h: json.dump(output,h,indent=2,sort_keys=True);h.write("\n")
    return output
def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--run",type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.run),indent=2,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
