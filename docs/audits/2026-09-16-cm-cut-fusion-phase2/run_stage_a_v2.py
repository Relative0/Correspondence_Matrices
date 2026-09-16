"""Successor Stage-A runner: isolate every arm in its own bounded process."""
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

from bitset_backend import build_bitset_env, eval_expr_bitset
from cm_expr_serde import expr_to_json_dag
from cmbench.biology_session_supervisor import run_worker
from cmbench.recognition.cut_fusion import optimize_cut_fusion
from cmbench.recognition.features import postorder

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cm_cut_stage_a_v1", HERE / "run_stage_a.py")
stage = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(stage)


def candidate(case):
    cohort, ident, group, n_vars, expr = case
    variables = tuple(f"x{i}" for i in range(n_vars))
    source_bits = eval_expr_bitset(expr, build_bitset_env(variables))
    common = {"cohort": cohort, "id": ident, "group": group, "n_vars": n_vars,
              "expression_sha256": stage.sha(stage.canonical(expr_to_json_dag(expr))),
              "source_identity_nodes": len(postorder(expr)),
              "truth_sha256": stage.sha(source_bits.to_bytes((1 << n_vars) // 8, "little"))}
    try:
        fused = optimize_cut_fusion(expr, n_vars)
    except Exception as exc:
        return {**common, "fusion_refusal": {"kind": type(exc).__name__, "reason": str(exc)},
                "best_candidate_bigint_ops": None, "semantic_match": None}
    proposed_bits = eval_expr_bitset(fused.proposed_result, build_bitset_env(variables))
    if source_bits != proposed_bits:
        raise RuntimeError(f"semantic mismatch: {ident}")
    return {**common, "fusion": fused.to_document(),
            "best_candidate_bigint_ops": min(fused.proposed_cse_metrics["executed_bigint_ops"],
                                              fused.proposed_cm_metrics["executed_bigint_ops"]),
            "semantic_match": True}


def control(case, label):
    _cohort, ident, _group, n_vars, expr = case
    try:
        if label == "plain":
            rewritten = expr
        elif label == "one_pass_pack":
            rewritten = stage.PACK.rewrite(expr, n_vars).result
        elif label == "d10_indexed":
            rewritten = stage.D10.rewrite(expr, n_vars, index_mode="indexed").result
        else:
            raise ValueError(label)
        return {"id": ident, "label": label, "metrics": stage.metrics(rewritten),
                "expression_sha256": stage.sha(stage.canonical(expr_to_json_dag(rewritten)))}
    except Exception as exc:
        return {"id": ident, "label": label, "refusal": type(exc).__name__, "reason": str(exc)}


def bounded(arguments):
    return run_worker([sys.executable, "-B", str(Path(__file__).resolve()), *arguments],
                      timeout_seconds=60, memory_limit_bytes=512 << 20,
                      max_output_bytes=2 << 20, cwd=ROOT)


def compact(receipt):
    return {key: value for key, value in receipt.items() if key not in ("stdout", "stderr")}


def worker_document(receipt):
    return json.loads(receipt["stdout"]) if receipt["status"] == "ok" else None


def main():
    synthetic = stage.make_synthetic_manifest()
    cases = stage.stage_cases(synthetic)
    if len(sys.argv) >= 4 and sys.argv[1] == "--worker":
        index = int(sys.argv[2])
        if sys.argv[3] == "candidate":
            value = candidate(cases[index])
        elif sys.argv[3] == "control" and len(sys.argv) == 5:
            value = control(cases[index], sys.argv[4])
        else:
            raise ValueError("invalid worker mode")
        print(json.dumps(value, sort_keys=True, allow_nan=False), flush=True)
        return

    started = time.perf_counter()
    rows, receipts = [], []
    for index, case in enumerate(cases):
        candidate_receipt = bounded(["--worker", str(index), "candidate"])
        receipts.append({"case_index": index, "arm": "candidate", **compact(candidate_receipt)})
        candidate_row = worker_document(candidate_receipt)
        controls = {}
        for label in ("plain", "one_pass_pack", "d10_indexed"):
            receipt = bounded(["--worker", str(index), "control", label])
            receipts.append({"case_index": index, "arm": label, **compact(receipt)})
            value = worker_document(receipt)
            controls[label] = (value if value is not None else
                {"label": label, "refusal": receipt["status"], "reason": receipt["reason"]})
        if candidate_row is None:
            candidate_row = {"cohort": case[0], "id": case[1], "group": case[2], "n_vars": case[3],
                             "expression_sha256": stage.sha(stage.canonical(expr_to_json_dag(case[4]))),
                             "fusion_refusal": {"kind": candidate_receipt["status"],
                                                "reason": candidate_receipt["reason"]},
                             "best_candidate_bigint_ops": None, "semantic_match": None}
        candidate_row["controls"] = controls
        incumbent = stage.best_ops({label: value for label, value in controls.items()})
        candidate_row["best_control_bigint_ops"] = incumbent
        proposed = candidate_row.get("best_candidate_bigint_ops")
        accepted = candidate_row.get("fusion", {}).get("accepted", False)
        candidate_row["accepted_beyond_controls"] = bool(
            accepted and incumbent is not None and proposed is not None and proposed < incumbent)
        rows.append(candidate_row)
        completed = index + 1
        if completed % 10 == 0 or any(receipt["status"] != "ok" for receipt in (
                candidate_receipt,)):
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
             "docs/audits/2026-09-16-cm-cut-fusion-phase2/run_stage_a_v2.py"]
    manifest = {"schema": "cm-cut-fusion-stage-a-source-manifest/v2",
        "supersedes": "source-manifest.json", "head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": sys.version, "platform": platform.platform(),
        "files_sha256": {path: stage.sha((ROOT / path).read_bytes()) for path in paths},
        "synthetic_manifest_sha256": synthetic["payload_sha256"],
        "template_table_sha256": stage.template_document()["payload_sha256"]}
    stage.write_json(HERE / "source-manifest-v2.json", manifest)
    output = {"schema": "cm-cut-fusion-stage-a-results/v2", "supersedes": "stage-a-results.json",
              "status": "pass" if gates["static_activation_pass"] else "stop",
              "scope": "proof and static activation only; one isolated job per candidate/control arm; no performance timings",
              "elapsed_seconds": time.perf_counter() - started, "gates": gates,
              "containment": {"kind": "windows_job", "memory_limit_bytes": 512 << 20,
                              "case_timeout_seconds": 60, "max_output_bytes": 2 << 20,
                              "campaign_wall_limit_seconds": 1800},
              "receipts": receipts, "cases": rows}
    stage.write_json(HERE / "stage-a-results-v2.json", output)
    print(json.dumps({"status": output["status"], "gates": gates,
                      "elapsed_seconds": output["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
