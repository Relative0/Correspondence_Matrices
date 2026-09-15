"""Seal or verify this additive diagnostic audit without touching predecessors."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
MANIFEST=HERE/"AUDIT_MANIFEST.json"
COMMIT="e334de594262059cc18cf37eaab56b0f79e94843"
CODE=["cm_ir.py","bitset_backend.py","cm_bench.py","cm_exprlib.py","cm_expr_serde.py",
      "cmbench/backends/bitset_engine.py","cmbench/output_budget.py","cmbench/config.py",
      "cmbench/expr/families.py","cmbench/expr/partial_contexts.py","cmbench/comparative/ir.py",
      "tests/test_bitset_cse.py","tests/test_prepared_flat_evaluation.py","tests/test_expression_family_bench.py"]


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def artifacts():
    return {p.relative_to(HERE).as_posix():{"sha256":sha(p),"bytes":p.stat().st_size}
            for p in sorted(HERE.rglob("*")) if p.is_file() and p!=MANIFEST
            and "__pycache__" not in p.parts and p.suffix!=".pyc"}


def link_check():
    checked=[]
    for name in ("REPORT.md","TIME_LEDGER.md","ROOT_CAUSE_MATRIX.md","VERIFICATION.md"):
        for target in re.findall(r"\]\(([^)]+)\)",(HERE/name).read_text(encoding="utf-8")):
            target=target.split("#",1)[0].strip("<>")
            if not target or "://" in target: continue
            path=HERE/target
            # The manifest is being created after the report that links to it.
            if path!=MANIFEST and not path.exists(): raise AssertionError((name,target))
            checked.append({"from":name,"target":target})
    return checked


def predecessors():
    sources=json.loads((HERE/"frozen_evidence.json").read_text(encoding="utf-8"))["sources"]
    extra=[
        ("C:/Users/brian/Documents/CM_Computation/cmbench/comparative/sympy_cm_claim_cleanup.py","historical_helper_explicitly_bound_to_baseline_imports"),
        ("C:/Users/brian/Documents/CM_Computation/docs/audits/2026-09-15-cm-sympy-claim-cleanup/FROZEN_INPUTS.json","exposed_development_inputs_only"),
    ]
    known={str(Path(x["path"]).resolve()) for x in sources}
    for path,origin in extra:
        p=Path(path)
        if str(p.resolve()) not in known:
            sources.append({"path":str(p),"origin":origin,"sha256":sha(p),"bytes":p.stat().st_size})
    for row in sources:
        assert sha(Path(row["path"]))==row["sha256"], row["path"]
    return sources


def preservation():
    data=json.loads((HERE/"PRESERVATION_CHECKPOINT.json").read_text())
    count=0
    for row in data["worktrees"]:
        for relative,digest in row["dirty_file_sha256"].items():
            assert sha(Path(row["worktree"])/relative)==digest,relative
            count+=1
    return {"unchanged_dirty_tracked_file_hashes":count,"scope":"synthesis-time checkpoint to final; initial status independently in task tool log"}


def create():
    assert not MANIFEST.exists(),"refusing to overwrite manifest"
    assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==COMMIT
    # Only tracked files: all diagnostic additions are deliberately untracked.
    assert not subprocess.check_output(["git","diff","--name-only"],cwd=ROOT,text=True).strip()
    sources=[]
    for rel in CODE:
        p=ROOT/rel
        blob=subprocess.check_output(["git","rev-parse",f"{COMMIT}:{rel}"],cwd=ROOT,text=True).strip()
        sources.append({"path":rel,"filesystem_sha256":sha(p),"commit_blob_oid":blob,
                        "note":"filesystem hash binds checkout bytes; Git blob may use normalized line endings"})
    result={"schema":"cm-time-attribution-audit-manifest/v1","base_commit":COMMIT,
            "worktree":str(ROOT),"worktree_mode":"detached; initially clean; additions only",
            "scientific_disposition_changed":False,
            "version_control_state":{"sealed_before_commit":True,
                "commit_authorized_after_seal":True,"pushed":False,
                "commit_oid":None,
                "note":"A commit cannot contain its own final object ID; verify it from Git history."},
            "plan_sha256":sha(HERE/"PLAN.md"),
            "primary_measurements":["ladder-run-002.json","task-run-001/TASK_RESULTS.json"],
            "superseded_preserved":["ladder-smoke-001.json","ladder-run-001.json"],
            "exclusions":["AUDIT_MANIFEST.json self hash is circular","Python bytecode/cache files are not evidence"],
            "baseline_code_and_fixture_bindings":sources,
            "predecessor_and_disclosed_input_bindings":predecessors(),
            "protected_worktree_verification":preservation(),"artifact_links_checked":link_check(),
            "tests":{"focused_passes":90,"synthesis_passes":7,"total_passed":97},
            "artifacts":artifacts()}
    with MANIFEST.open("x",encoding="utf-8") as f:json.dump(result,f,indent=2);f.write("\n")


def verify():
    d=json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert artifacts()==d["artifacts"],"artifact content or membership changed"
    assert sha(HERE/"PLAN.md")==d["plan_sha256"]
    for row in d["baseline_code_and_fixture_bindings"]:
        assert sha(ROOT/row["path"])==row["filesystem_sha256"]
    for row in d["predecessor_and_disclosed_input_bindings"]:
        assert sha(Path(row["path"]))==row["sha256"],row["path"]
    assert preservation()==d["protected_worktree_verification"]
    link_check()
    print(json.dumps({"verified_artifacts":len(d["artifacts"]),
                      "verified_predecessor_and_input_bindings":len(d["predecessor_and_disclosed_input_bindings"]),
                      "verified_baseline_bindings":len(d["baseline_code_and_fixture_bindings"]),
                      "artifact_bytes":sum(r["bytes"] for r in d["artifacts"].values()),
                      "scientific_disposition_changed":False,"mode":"read_only"}))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--verify",action="store_true");args=p.parse_args()
    if not args.verify:create()
    verify()
