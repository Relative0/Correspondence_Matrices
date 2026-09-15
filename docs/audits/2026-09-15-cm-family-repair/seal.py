"""Seal/verify new repair artifacts without changing predecessor evidence."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=ROOT.parent/"cm-time-attribution-20260915"
sys.path.insert(0,str(HERE))
import preservation

HEAD="4d9b869fb7b22eb6263ef613b5a9d41fcbbb78dd"
TRACKED=["cm_bench.py","cm_ir.py","cmbench/config.py","cmbench/results/expression_family.py"]
NEW=["cmbench/phase_timing.py","tests/test_cm_family_repairs.py"]
MANIFEST=HERE/"AUDIT_MANIFEST.json"
SEAL=HERE/"AUDIT_MANIFEST.sha256"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args,root=ROOT):
    return subprocess.check_output(["git","-c",f"safe.directory={root.as_posix()}",*args],
                                   cwd=root,stderr=subprocess.DEVNULL).decode("utf-8")


def artifacts():
    return {p.relative_to(HERE).as_posix():{"sha256":sha(p),"bytes":p.stat().st_size}
        for p in sorted(HERE.rglob("*")) if p.is_file() and p not in (MANIFEST,SEAL)
        and "__pycache__" not in p.parts}


def write(name,data):
    with (HERE/name).open("x",encoding="utf-8") as f:
        f.write(data)


def verify_preserved():
    assert preservation.snapshot()==json.loads((HERE/"PRESERVATION.json").read_text())
    assert git("rev-parse","HEAD").strip()==HEAD
    assert not git("diff","--cached","--name-only").strip()
    assert set(git("diff","--name-only").splitlines())==set(TRACKED)
    assert not git("diff","--check").strip()


def predecessor_bindings():
    paths=[BASE/"docs/audits/2026-09-15-cm-time-attribution-deep-dive/AUDIT_MANIFEST.json",
        BASE/"docs/audits/2026-09-15-cm-family-lifecycle-code-dive/AUDIT_MANIFEST.json",
        BASE/"docs/research/CM_FAMILY_REPAIR_AND_SPEEDUP_PLAN_2026_09_15.md"]
    return [{"path":str(p),"sha256":sha(p)} for p in paths]


def create():
    assert not MANIFEST.exists() and not SEAL.exists()
    verify_preserved()
    status=git("status","--porcelain","--untracked-files=all").splitlines()
    prefix=HERE.relative_to(ROOT).as_posix()+"/"
    for line in status:
        name=line[3:]
        assert name in TRACKED+NEW or name.startswith(prefix),line
    patch=git("diff","HEAD","--",*TRACKED)
    for name in NEW:
        patch+="".join(difflib.unified_diff([], (ROOT/name).read_text(encoding="utf-8").splitlines(True),
                                          fromfile="/dev/null",tofile="b/"+name))
    write("PATCH.diff",patch)
    write("GIT_REVIEW.json",json.dumps({"head":HEAD,"branch":git("branch","--show-current").strip(),
        "tracked_changes":TRACKED,"new_source_and_tests":NEW,"audit_directory":prefix,
        "staged":False,"committed":False,"pushed":False,"diff_check":"passed",
        "protected_checkpoint_verified":True,"status_before_seal":status,
        "diff_stat":git("diff","--stat")},indent=2)+"\n")
    # Bind the complete research check report within the new audit.
    report=ROOT/"tmp/repair-research-check-final.json"
    assert json.loads(report.read_text())["status"]=="passed"
    write("research-check-final.json",report.read_text(encoding="utf-8"))
    diagnostics={}
    for name,source in [("2026-09-12-cm-application-evidence","scripts/cm_application_oracle.py"),
                        ("2026-09-12-cm-count-closures","cmbench/comparative/component_counts.py")]:
        expected=json.loads((ROOT/f"docs/audits/{name}/FINAL-MANIFEST.json").read_text())["current_sources"][source]
        data=(ROOT/source).read_bytes()
        diagnostics[source]={"expected":expected,"candidate":sha(ROOT/source),
            "baseline":sha(BASE/source),"LF_normalized":hashlib.sha256(data.replace(b"\r\n",b"\n")).hexdigest()}
        assert diagnostics[source]["candidate"]==diagnostics[source]["baseline"]
    write("SOURCE_IDENTITY_DIAGNOSTIC.json",json.dumps(diagnostics,indent=2)+"\n")
    current={name:sha(ROOT/name) for name in TRACKED+NEW}
    manifest={"schema":"cm-family-repair-audit/v1","head":HEAD,
        "implementation_base":"e334de594262059cc18cf37eaab56b0f79e94843",
        "worktree":str(ROOT),"sources":current,"predecessors":predecessor_bindings(),
        "evidence":"development diagnostics only","scientific_disposition_changed":False,
        "primary_records":["PROFILE_RESULTS-v2.json","final-fresh-a-v2.json","final-fresh-b-v2.json",
                           "final-resident-a-v2.json","final-resident-b-v2.json","MECHANISMS-final-v3.json"],
        "held_out_inputs_consumed":False,"optional_dependencies_installed":False,
        "cloud_started":False,"external_spending":False,"committed":False,"pushed":False,
        "source_and_input_note":"source roots/DAG/key/program hashes are in timing records; generated family metadata retained",
        "environment_at_seal":{k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")},
        "exclusions":["manifest and detached seal avoid circular hashing","Python bytecode is not evidence"],
        "artifacts":artifacts()}
    write(MANIFEST.name,json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    write(SEAL.name,sha(MANIFEST)+"  AUDIT_MANIFEST.json\n")


def verify():
    verify_preserved()
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert sha(MANIFEST)==SEAL.read_text().split()[0]
    assert manifest["artifacts"]==artifacts()
    assert manifest["predecessors"]==predecessor_bindings()
    for name,digest in manifest["sources"].items():assert sha(ROOT/name)==digest,name
    for name in manifest["primary_records"]:
        record=json.loads((HERE/name).read_text())
        if "source_hashes" in record:
            sources=record["source_hashes"]
            if "candidate" in sources:sources=sources["candidate"]
            for path,digest in sources.items():assert sha(ROOT/path)==digest,(name,path)
    print(json.dumps({"verified_artifacts":len(manifest["artifacts"]),
        "bytes":sum(r["bytes"] for r in manifest["artifacts"].values()),
        "sources":len(manifest["sources"]),"predecessors":len(manifest["predecessors"]),
        "protected_worktrees":"unchanged","scientific_disposition_changed":False,
        "uncommitted":True,"unpushed":True}))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    if not args.verify:create()
    verify()
