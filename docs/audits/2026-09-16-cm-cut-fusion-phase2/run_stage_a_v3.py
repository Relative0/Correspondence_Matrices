"""Stage-A v3: isolated arms with non-recursive diagnostics serialization."""
from __future__ import annotations

import importlib.util
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_to_json_dag
from cmbench.biology_session_supervisor import run_worker

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cm_cut_stage_a_v2_live", HERE / "run_stage_a_v2.py")
v2 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(v2)
stage = v2.stage


def bounded(arguments):
    return run_worker([sys.executable, "-B", str(Path(__file__).resolve()), *arguments],
                      timeout_seconds=60, memory_limit_bytes=512 << 20,
                      max_output_bytes=2 << 20, cwd=ROOT)


def compact(receipt):
    return {key: value for key, value in receipt.items() if key not in ("stdout", "stderr")}


def main():
    synthetic = stage.make_synthetic_manifest()
    cases = stage.stage_cases(synthetic)
    if len(sys.argv) >= 4 and sys.argv[1] == "--worker":
        index = int(sys.argv[2])
        if sys.argv[3] == "candidate":
            value = v2.candidate(cases[index])
        elif sys.argv[3] == "control" and len(sys.argv) == 5:
            value = v2.control(cases[index], sys.argv[4])
        else:
            raise ValueError("invalid worker mode")
        print(json.dumps(value, sort_keys=True, allow_nan=False), flush=True)
        return

    started = time.perf_counter()
    rows, receipts = [], []
    for index, case in enumerate(cases):
        candidate_receipt = bounded(["--worker", str(index), "candidate"])
        receipts.append({"case_index": index, "arm": "candidate", **compact(candidate_receipt)})
        candidate_row = (json.loads(candidate_receipt["stdout"])
                         if candidate_receipt["status"] == "ok" else None)
        controls = {}
        for label in ("plain", "one_pass_pack", "d10_indexed"):
            receipt = bounded(["--worker", str(index), "control", label])
            receipts.append({"case_index": index, "arm": label, **compact(receipt)})
            controls[label] = (json.loads(receipt["stdout"]) if receipt["status"] == "ok" else
                {"label": label, "refusal": receipt["status"], "reason": receipt["reason"]})
        if candidate_row is None:
            candidate_row = {"cohort": case[0], "id": case[1], "group": case[2], "n_vars": case[3],
                "expression_sha256": stage.sha(stage.canonical(expr_to_json_dag(case[4]))),
                "fusion_refusal": {"kind": candidate_receipt["status"],
                                   "reason": candidate_receipt["reason"]},
                "best_candidate_bigint_ops": None, "semantic_match": None}
        candidate_row["controls"] = controls
        incumbent = stage.best_ops(controls)
        proposed = candidate_row.get("best_candidate_bigint_ops")
        candidate_row["best_control_bigint_ops"] = incumbent
        candidate_row["accepted_beyond_controls"] = bool(
            candidate_row.get("fusion", {}).get("accepted", False)
            and incumbent is not None and proposed is not None and proposed < incumbent)
        rows.append(candidate_row)
        completed = index + 1
        if completed % 10 == 0 or candidate_receipt["status"] != "ok":
            print(json.dumps({"completed": completed, "total": len(cases),
                              "candidate_status": candidate_receipt["status"],
                              "elapsed_seconds": time.perf_counter() - started}), flush=True)
        if time.perf_counter() - started > 1800:
            raise RuntimeError("frozen Stage-A campaign wall limit exceeded")

    f1 = [row for row in rows if row["cohort"] == "synthetic_development" and row["group"] == "F1"]
    f2 = [row for row in rows if row["cohort"] == "synthetic_development" and row["group"] == "F2"]
    epfl = [row for row in rows if row["cohort"] == "exposed_epfl"]
    c36 = [row for row in rows if row["cohort"] == "exposed_c36"]
    resource_failures = [row for row in receipts if row["status"] in ("resource_limit", "timeout")]
    gates = {"semantic_and_boundary_checks": "pending_test_command",
        "f1_activation": any(row["accepted_beyond_controls"] for row in f1),
        "f2_activation": any(row["accepted_beyond_controls"] for row in f2),
        "epfl_activation_count": sum(row["accepted_beyond_controls"] for row in epfl),
        "epfl_activation_required": 8, "all_c36_retained": len(c36) == 18,
        "resource_failure_count": len(resource_failures), "resource_failure_required": 0}
    gates["static_activation_pass"] = bool(gates["f1_activation"] and gates["f2_activation"]
        and gates["epfl_activation_count"] >= 8 and gates["all_c36_retained"]
        and gates["resource_failure_count"] == 0)
    paths = ["cmbench/recognition/cut_fusion.py", "cmbench/biology_session_supervisor.py",
        "docs/audits/2026-09-16-cm-cut-fusion-phase2/run_stage_a.py",
        "docs/audits/2026-09-16-cm-cut-fusion-phase2/run_stage_a_v2.py",
        "docs/audits/2026-09-16-cm-cut-fusion-phase2/run_stage_a_v3.py"]
    manifest = {"schema": "cm-cut-fusion-stage-a-source-manifest/v3",
        "supersedes": "source-manifest-v2.json", "head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": sys.version, "platform": platform.platform(),
        "files_sha256": {path: stage.sha((ROOT / path).read_bytes()) for path in paths},
        "synthetic_manifest_sha256": synthetic["payload_sha256"],
        "template_table_sha256": stage.template_document()["payload_sha256"]}
    stage.write_json(HERE / "source-manifest-v3.json", manifest)
    output = {"schema": "cm-cut-fusion-stage-a-results/v3",
        "supersedes": "stage-a-results-v2.json",
        "status": "pass" if gates["static_activation_pass"] else "stop",
        "scope": "proof and static activation only; isolated bounded arms; no performance timings",
        "elapsed_seconds": time.perf_counter() - started, "gates": gates,
        "containment": {"kind": "windows_job", "memory_limit_bytes": 512 << 20,
                        "case_timeout_seconds": 60, "max_output_bytes": 2 << 20,
                        "campaign_wall_limit_seconds": 1800},
        "receipts": receipts, "cases": rows}
    stage.write_json(HERE / "stage-a-results-v3.json", output)
    print(json.dumps({"status": output["status"], "gates": gates,
                      "elapsed_seconds": output["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
