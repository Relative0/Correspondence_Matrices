"""Run only the frozen proof/static activation gate for bounded cut fusion."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from bitset_backend import build_bitset_env, compile_expr_cse, compile_flat, eval_expr_bitset, program_metrics
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir
from cmbench.recognition.cut_fusion import optimize_cut_fusion, template_document
from cmbench.biology_session_supervisor import run_worker
from cmbench.recognition.d10_rule_engine import compile_d10_rule_pack, prove_d10_rule_pack
from cmbench.recognition.features import postorder
from cmbench.recognition.rule_pack import compile_rule_pack, prove_rule_pack_v2

HERE = Path(__file__).resolve().parent
PACK = compile_rule_pack(prove_rule_pack_v2())
D10 = compile_d10_rule_pack(prove_d10_rule_pack())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def balanced_or(items):
    if len(items) == 1:
        return items[0]
    middle = len(items) // 2
    return Or(balanced_or(items[:middle]), balanced_or(items[middle:]))


def permutation(family, k, t):
    return sorted(range(k), key=lambda i: (
        sha(f"cm-cut-v1|{family}|{k}|{t}|{i}".encode("utf-8")), i))


def synthetic_case(family, k, t):
    p = [Var(i) for i in permutation(family, k, t)]
    shells, shared = [], []
    if family == "F6":
        level = list(p)
        operator_index = 0
        while len(level) > 1:
            next_level = []
            for index in range(0, len(level), 2):
                if index + 1 == len(level):
                    next_level.append(level[index])
                    continue
                ctor = (And, Or, Xor)[operator_index % 3]
                operator_index += 1
                next_level.append(ctor(level[index], level[index + 1]))
            level = next_level
        return level[0]
    for j in range(k // 2):
        a = Xor(p[(2 * j) % k], p[(2 * j + 1) % k])
        b = And(p[(2 * j + 1) % k], p[(2 * j + 2) % k])
        ab = And(a, b)
        if family == "F1" or family == "F5":
            shell = Xor(ab, Or(a, b))
        elif family == "F2":
            shell = And(Imp(a, b), Imp(b, a))
        elif family == "F3":
            shell = Or(ab, And(a, Not(b)))
        elif family == "F4":
            shell = Xor(a, b)
        else:
            raise ValueError(family)
        shells.append(shell)
        shared.append(ab)
    return balanced_or(shells + shared if family == "F5" else shells)


def make_synthetic_manifest():
    rows = []
    for split, ks, ts in (("development", (8, 12), (0, 1)),
                          ("locked_confirmation", (8, 12, 16), (2, 3))):
        for family in ("F1", "F2", "F3", "F4", "F5", "F6"):
            for k in ks:
                for t in ts:
                    expr = synthetic_case(family, k, t)
                    document = expr_to_json_dag(expr)
                    rows.append({"id": f"{split}-{family}-k{k}-t{t}", "split": split,
                                 "family": family, "n_vars": k,
                                 "permutation": permutation(family, k, t),
                                 "expression_sha256": sha(canonical(document)),
                                 "expression_v2": document})
    payload = {"schema": "cm-cut-fusion-synthetic-manifest/v1", "rows": rows}
    return {**payload, "payload_sha256": sha(canonical(payload))}


def natural_cases():
    epfl_path = ROOT / "deliverables_n22_24/CM_gap_epfl_corpus_2026_08_03.jsonl"
    c36_path = ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json"
    cases = []
    for line in epfl_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if ("expression_v2" in row and row["synt_support_size"] == row["sem_support_size"]
                and 11 <= row["synt_support_size"] <= 16):
            expr = expr_from_json(row["expression_v2"])
            cases.append(("exposed_epfl", row["id"], row["circuit"], row["synt_support_size"], expr))
    for row in json.loads(c36_path.read_text(encoding="utf-8"))["cases"]:
        cases.append(("exposed_c36", row["case_id"], row["cluster_id"], row["n_vars"],
                      expr_from_json(row["expression_v2"])))
    assert sum(case[0] == "exposed_epfl" for case in cases) == 64
    assert sum(case[0] == "exposed_c36" for case in cases) == 18
    return cases


def stage_cases(synthetic):
    development = []
    for row in synthetic["rows"]:
        if row["split"] == "development":
            development.append(("synthetic_development", row["id"], row["family"], row["n_vars"],
                                expr_from_json(row["expression_v2"])))
    return development + natural_cases()


def metrics(expr):
    return {
        "cse": program_metrics(compile_expr_cse(expr, flatten=True)),
        "cm": program_metrics(compile_flat(compile_expr_to_cm_ir(expr))),
    }


def controls(expr, n_vars, baseline):
    result = {"plain": {"metrics": baseline}}
    for label, operation in (
        ("one_pass_pack", lambda: PACK.rewrite(expr, n_vars).result),
        ("d10_indexed", lambda: D10.rewrite(expr, n_vars, index_mode="indexed").result),
    ):
        try:
            rewritten = operation()
            result[label] = {"metrics": metrics(rewritten),
                             "expression_sha256": sha(canonical(expr_to_json_dag(rewritten)))}
        except Exception as exc:
            result[label] = {"refusal": type(exc).__name__, "reason": str(exc)}
    return result


def best_ops(control_document):
    values = []
    for row in control_document.values():
        for backend in row.get("metrics", {}).values():
            values.append(backend["executed_bigint_ops"])
    return min(values) if values else None


def evaluate(case):
    cohort, ident, group, n_vars, expr = case
    variables = tuple(f"x{i}" for i in range(n_vars))
    source_bits = eval_expr_bitset(expr, build_bitset_env(variables))
    try:
        fused = optimize_cut_fusion(expr, n_vars)
    except Exception as exc:
        try:
            baseline = metrics(expr)
            control = controls(expr, n_vars, baseline)
        except Exception as control_exc:
            control = {"plain": {"refusal": type(control_exc).__name__, "reason": str(control_exc)}}
        return {"cohort": cohort, "id": ident, "group": group, "n_vars": n_vars,
                "expression_sha256": sha(canonical(expr_to_json_dag(expr))),
                "source_identity_nodes": len(postorder(expr)),
                "fusion_refusal": {"kind": type(exc).__name__, "reason": str(exc)},
                "controls": control, "best_control_bigint_ops": best_ops(control),
                "best_candidate_bigint_ops": None, "accepted_beyond_controls": False,
                "semantic_match": None,
                "truth_sha256": sha(source_bits.to_bytes((1 << n_vars) // 8, "little"))}
    proposed_bits = eval_expr_bitset(fused.proposed_result, build_bitset_env(variables))
    if source_bits != proposed_bits:
        raise RuntimeError(f"semantic mismatch: {ident}")
    control = controls(expr, n_vars, {"cse": fused.baseline_cse_metrics, "cm": fused.baseline_cm_metrics})
    incumbent = best_ops(control)
    candidate = min(fused.proposed_cse_metrics["executed_bigint_ops"],
                    fused.proposed_cm_metrics["executed_bigint_ops"])
    return {"cohort": cohort, "id": ident, "group": group, "n_vars": n_vars,
            "expression_sha256": sha(canonical(expr_to_json_dag(expr))),
            "source_identity_nodes": len(postorder(expr)), "fusion": fused.to_document(),
            "controls": control, "best_control_bigint_ops": incumbent,
            "best_candidate_bigint_ops": candidate,
            "accepted_beyond_controls": bool(fused.accepted and candidate < incumbent),
            "semantic_match": True, "truth_sha256": sha(source_bits.to_bytes((1 << n_vars) // 8, "little"))}


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def write_or_verify(path, value):
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise RuntimeError(f"frozen artifact changed: {path.name}")
        return
    write_json(path, value)


def main():
    started = time.perf_counter()
    template = template_document()
    synthetic = make_synthetic_manifest()
    cases = stage_cases(synthetic)
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        index = int(sys.argv[2])
        if not 0 <= index < len(cases):
            raise ValueError("worker case index outside frozen schedule")
        print(json.dumps(evaluate(cases[index]), sort_keys=True, allow_nan=False), flush=True)
        return
    write_or_verify(HERE / "template-table.json", template)
    write_or_verify(HERE / "synthetic-manifest.json", synthetic)
    rows = []
    receipts = []
    for case_index, case in enumerate(cases):
        receipt = run_worker([sys.executable, "-B", str(Path(__file__).resolve()),
                              "--worker", str(case_index)], timeout_seconds=60,
                             memory_limit_bytes=512 << 20, max_output_bytes=2 << 20, cwd=ROOT)
        compact_receipt = {key: value for key, value in receipt.items() if key not in ("stdout", "stderr")}
        receipts.append({"case_index": case_index, "id": case[1], **compact_receipt})
        if receipt["status"] == "ok":
            row = json.loads(receipt["stdout"])
            row["containment"] = compact_receipt
        else:
            row = {"cohort": case[0], "id": case[1], "group": case[2], "n_vars": case[3],
                   "expression_sha256": sha(canonical(expr_to_json_dag(case[4]))),
                   "fusion_refusal": {"kind": receipt["status"], "reason": receipt["reason"]},
                   "controls": {}, "best_control_bigint_ops": None,
                   "best_candidate_bigint_ops": None, "accepted_beyond_controls": False,
                   "semantic_match": None, "containment": compact_receipt}
        rows.append(row)
        completed = case_index + 1
        if completed % 10 == 0 or receipt["status"] != "ok":
            print(json.dumps({"completed": completed, "total": len(cases),
                              "last_status": receipt["status"],
                              "elapsed_seconds": time.perf_counter() - started}), flush=True)
        if time.perf_counter() - started > 1800:
            raise RuntimeError("frozen Stage-A campaign wall limit exceeded")

    f1 = [row for row in rows if row["cohort"] == "synthetic_development" and row["group"] == "F1"]
    f2 = [row for row in rows if row["cohort"] == "synthetic_development" and row["group"] == "F2"]
    epfl = [row for row in rows if row["cohort"] == "exposed_epfl"]
    c36 = [row for row in rows if row["cohort"] == "exposed_c36"]
    gates = {
        "semantic_and_boundary_checks": "pending_test_command",
        "f1_activation": any(row["accepted_beyond_controls"] for row in f1),
        "f2_activation": any(row["accepted_beyond_controls"] for row in f2),
        "epfl_activation_count": sum(row["accepted_beyond_controls"] for row in epfl),
        "epfl_activation_required": 8,
        "all_c36_retained": len(c36) == 18,
    }
    gates["static_activation_pass"] = bool(gates["f1_activation"] and gates["f2_activation"]
                                            and gates["epfl_activation_count"] >= 8
                                            and gates["all_c36_retained"])
    input_paths = [
        "deliverables_n22_24/CM_gap_epfl_corpus_2026_08_03.jsonl",
        "docs/recognition/c36_wide_repeated_query_dataset.json", "cmbench/recognition/cut_fusion.py",
        "cm_ir.py", "bitset_backend.py", "cm_exprlib.py", "cm_expr_serde.py", "cm_token.py",
        "cmbench/recognition/rule_pack.py", "cmbench/recognition/d10_rule_engine.py",
        "cmbench/biology_session_supervisor.py",
    ]
    source_manifest = {"schema": "cm-cut-fusion-stage-a-source-manifest/v1",
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": sys.version, "platform": platform.platform(),
        "files_sha256": {path: sha((ROOT / path).read_bytes()) for path in input_paths},
        "synthetic_manifest_sha256": synthetic["payload_sha256"],
        "template_table_sha256": template["payload_sha256"]}
    write_json(HERE / "source-manifest.json", source_manifest)
    output = {"schema": "cm-cut-fusion-stage-a-results/v1", "status": "pass" if gates["static_activation_pass"] else "stop",
              "scope": "proof and static activation only; no performance timings",
              "elapsed_seconds": time.perf_counter() - started, "gates": gates,
              "containment": {"kind": "windows_job", "memory_limit_bytes": 512 << 20,
                              "case_timeout_seconds": 60, "max_output_bytes": 2 << 20,
                              "campaign_wall_limit_seconds": 1800},
              "receipts": receipts, "cases": rows}
    write_json(HERE / "stage-a-results.json", output)
    print(json.dumps({"status": output["status"], "gates": gates, "elapsed_seconds": output["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
