"""Independent structural verifier for a retained Milestone D9 run."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bitset_backend import build_bitset_env, compile_expr_cse, eval_expr_bitset
from cm_expr_serde import expr_from_json

from cmbench.recognition.blif import parse_blif
from cmbench.recognition.computation_experiment import sha256_file
from cmbench.recognition.features import structural_digest
from cmbench.recognition.natural_profitability_policy_experiment import (
    ACTIONS, ARMS, MEASUREMENT_SCHEMA, REUSES, RUN_SCHEMA, SPLITS,
    NaturalProfitabilityConfig, source_fingerprints, summarize_split,
)
from cmbench.recognition.profitability_policy import (
    EnvironmentCalibration, ProfitabilityMetadata, ProfitabilityTree, sha256_document,
)
from cmbench.recognition.rule_pack import ProvedRulePack, compile_rule_pack, prove_rule_pack_v2


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _load_json(path: Path, maximum: int) -> Any:
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError(f"{path.name} exceeds verifier size bound")
    return json.loads(raw, object_pairs_hook=_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def _load_jsonl(path: Path, maximum: int) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError(f"{path.name} exceeds verifier size bound")
    result = []
    for line in raw.splitlines():
        if line:
            value = json.loads(line, object_pairs_hook=_pairs,
                parse_constant=lambda item: (_ for _ in ()).throw(ValueError("nonfinite JSONL")))
            if type(value) is not dict:
                raise ValueError("measurement row must be an object")
            result.append(value)
    return result


def _verify_cases(document: dict[str, Any], split: str) -> dict[str, dict[str, Any]]:
    variant, circuits = SPLITS[split]
    if (document.get("schema") != "crse-natural-profitability-selection/v1"
            or document.get("split") != split or document.get("variant") != variant
            or document.get("circuits") != list(circuits)
            or document.get("training_use") is not (split == "training")):
        raise ValueError(f"{split} case-manifest identity disagreement")
    cases = document.get("cases")
    if type(cases) is not list or not cases:
        raise ValueError(f"empty {split} case set")
    netlists = {}
    result = {}
    for item in cases:
        if (type(item) is not dict or item.get("split") != split
                or item.get("variant") != variant or item.get("circuit") not in circuits
                or item.get("case_id") in result):
            raise ValueError(f"invalid or duplicate {split} case")
        source = ROOT / item["source_path"]
        if sha256_file(source) != item["source_sha256"]:
            raise ValueError("BLIF source hash mismatch")
        netlist = netlists.get(str(source))
        if netlist is None:
            netlist = parse_blif(source)
            netlists[str(source)] = netlist
        oracle, support = netlist.packed_value(item["root"])
        expr = expr_from_json(item["expression_v2"])
        metadata = ProfitabilityMetadata(**item["metadata"])
        metadata.validate()
        actual = eval_expr_bitset(expr, build_bitset_env(tuple(f"x{i}" for i in range(metadata.support))))
        if (len(support) != metadata.support or actual != oracle
                or structural_digest(expr) != item["structural_sha256"]
                or structural_digest(expr, alpha_rename=True) != item["alpha_sha256"]):
            raise ValueError("case expression, oracle, or identity mismatch")
        result[item["case_id"]] = {"item": item, "expr": expr, "oracle": oracle,
                                   "metadata": metadata}
    return result


def _verify_rows(rows: list[dict[str, Any]], split: str, cases, matcher,
                 policy, calibration, allowed_arms: tuple[str, ...]) -> None:
    rewrite_cache = {}
    seen = set()
    for row in rows:
        key = (row.get("round"), row.get("case_id"), row.get("expected_reuses"), row.get("arm"))
        if key in seen:
            raise ValueError("duplicate measurement cell")
        seen.add(key)
        case = cases.get(row.get("case_id"))
        if (case is None or row.get("schema") != MEASUREMENT_SCHEMA or row.get("split") != split
                or row.get("arm") not in allowed_arms or row.get("expected_reuses") not in REUSES
                or row.get("status") != "ok" or row.get("mismatches") != 0
                or row.get("output_sha256") != row.get("oracle_sha256")):
            raise ValueError("measurement identity, status, or output mismatch")
        if row.get("total_ns") != sum(row.get(key, -1) for key in (
                "decision_ns", "rewrite_ns", "cse_build_ns", "cse_kernel_ns")):
            raise ValueError("timing stage sum disagreement")
        base = case["metadata"]
        expected_metadata = ProfitabilityMetadata(base.support, row["expected_reuses"],
            base.source_nodes, base.source_edges, base.depth, base.local_cubes, base.local_literals)
        if row.get("metadata") != expected_metadata.__dict__:
            raise ValueError("measurement metadata disagreement")
        if row["arm"] == "frozen_gate":
            decision = policy.decide(expected_metadata, calibration)
            if (row.get("selected_action") != decision.action
                    or row.get("decision_reason") != decision.reason):
                raise ValueError("frozen policy decision does not reproduce")
        elif row.get("selected_action") != row["arm"] or row.get("decision_reason") != "fixed_arm":
            raise ValueError("fixed-arm decision disagreement")
        action = row["selected_action"]
        if action == "no_rewrite":
            if (row.get("applications") != 0 or row.get("rewrite_ns") != 0
                    or row.get("result_sha256") != row.get("source_sha256")):
                raise ValueError("no-rewrite structural accounting disagreement")
        else:
            cached = rewrite_cache.get(row["case_id"])
            if cached is None:
                cached = matcher.rewrite(case["expr"], expected_metadata.support)
                rewrite_cache[row["case_id"]] = cached
            if (row.get("applications") != cached.applications
                    or row.get("proposals") != cached.proposals
                    or row.get("conflicts") != cached.conflicts
                    or row.get("applications_by_rule") != cached.applications_by_rule
                    or row.get("result_sha256") != structural_digest(cached.result)):
                raise ValueError("one-pass rewrite accounting disagreement")
        result_expr = case["expr"] if action == "no_rewrite" else rewrite_cache[row["case_id"]].result
        if (row.get("cse_ops_before") != len(compile_expr_cse(case["expr"], flatten=True).ops)
                or row.get("cse_ops_after") != len(compile_expr_cse(result_expr, flatten=True).ops)):
            raise ValueError("CSE operation accounting disagreement")


def verify(run: Path) -> dict[str, Any]:
    run = run.resolve()
    required = {"run_spec.json", "proved_rule_pack.json", "calibration.json",
        "training_cases.json", "training_measurements.jsonl", "training_manifest.json",
        "policy.json", "policy_freeze.json", "training_policy_measurements.jsonl",
        "validation_cases.json", "validation_measurements.jsonl", "evaluation_cases.json",
        "evaluation_measurements.jsonl", "summary.json", "report.md"}
    manifest = _load_json(run / "manifest.json", 256_000)
    if (manifest.get("schema") != "crse-natural-profitability-policy-artifacts/v1"
            or manifest.get("status") != "complete"
            or set(manifest.get("files_sha256", {})) != required):
        raise ValueError("artifact manifest identity or file set disagreement")
    for name, digest in manifest["files_sha256"].items():
        if sha256_file(run / name) != digest:
            raise ValueError(f"artifact hash mismatch: {name}")
    spec = _load_json(run / "run_spec.json", 512_000)
    config = NaturalProfitabilityConfig(**spec["config"])
    config.validate()
    if (spec.get("schema") != "crse-natural-profitability-policy-run-spec/v1"
            or spec.get("arms") != list(ARMS) or spec.get("reuses") != list(REUSES)
            or spec.get("source_sha256") != source_fingerprints()):
        raise ValueError("run specification or source identity disagreement")
    pack = ProvedRulePack.load(run / "proved_rule_pack.json")
    if pack.to_dict() != prove_rule_pack_v2().to_dict():
        raise ValueError("proved rule pack does not reproduce")
    matcher = compile_rule_pack(pack)
    calibration_document = _load_json(run / "calibration.json", 256_000)
    calibration = EnvironmentCalibration.from_dict(calibration_document)
    training_manifest = _load_json(run / "training_manifest.json", 256_000)
    policy = ProfitabilityTree.load(run / "policy.json")
    freeze = _load_json(run / "policy_freeze.json", 256_000)
    if (freeze.get("frozen") is not True
            or freeze.get("frozen_before_validation_or_evaluation_load") is not True
            or freeze.get("calibration_document_sha256") != calibration.digest
            or freeze.get("training_manifest_document_sha256") != sha256_document(training_manifest)
            or freeze.get("policy_file_sha256") != sha256_file(run / "policy.json")
            or policy.calibration_sha256 != calibration.digest
            or policy.training_manifest_sha256 != sha256_document(training_manifest)):
        raise ValueError("policy freeze or binding disagreement")
    cases = {split: _verify_cases(_load_json(run / f"{split}_cases.json", 32_000_000), split)
             for split in SPLITS}
    circuit_sets = {split: {case["item"]["circuit"] for case in values.values()}
                    for split, values in cases.items()}
    if any(circuit_sets[left] & circuit_sets[right] for left, right in (
            ("training", "validation"), ("training", "evaluation"), ("validation", "evaluation"))):
        raise ValueError("split circuits overlap")
    training_rows = _load_jsonl(run / "training_measurements.jsonl", 64_000_000)
    training_policy_rows = _load_jsonl(run / "training_policy_measurements.jsonl", 32_000_000)
    validation_rows = _load_jsonl(run / "validation_measurements.jsonl", 64_000_000)
    evaluation_rows = _load_jsonl(run / "evaluation_measurements.jsonl", 64_000_000)
    _verify_rows(training_rows, "training", cases["training"], matcher, policy, calibration, ACTIONS)
    _verify_rows(training_policy_rows, "training", cases["training"], matcher, policy,
                 calibration, ("frozen_gate",))
    _verify_rows(validation_rows, "validation", cases["validation"], matcher, policy,
                 calibration, ARMS)
    _verify_rows(evaluation_rows, "evaluation", cases["evaluation"], matcher, policy,
                 calibration, ARMS)
    summary = _load_json(run / "summary.json", 16_000_000)
    recomputed = {"training": summarize_split(training_rows + training_policy_rows),
        "validation": summarize_split(validation_rows), "evaluation": summarize_split(evaluation_rows)}
    all_rows = training_rows + training_policy_rows + validation_rows + evaluation_rows
    if (summary.get("schema") != RUN_SCHEMA or summary.get("status") != "complete"
            or summary.get("semantic_mismatches") != 0 or summary.get("summaries") != recomputed
            or summary.get("semantic_checks") != sum(row["expected_reuses"] for row in all_rows)
            or summary.get("criteria", {}).get("safety_met") is not True
            or summary.get("criteria", {}).get("leakage_control_met") is not True
            or summary.get("criteria", {}).get("production_promotion") is not False):
        raise ValueError("summary recomputation or criteria disagreement")
    return {"schema": "crse-natural-profitability-policy-verification/v1", "status": "pass",
        "artifacts_verified": len(required), "cases_verified": sum(map(len, cases.values())),
        "measurement_rows_verified": len(all_rows), "semantic_mismatches": 0,
        "policy_sha256": sha256_file(run / "policy.json"),
        "evaluation_speedup": recomputed["evaluation"]["frozen_gate_speedup_over_no_rewrite"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.run)
    except Exception as exc:
        result = {"schema": "crse-natural-profitability-policy-verification/v1",
                  "status": "fail", "error_type": type(exc).__name__, "error": str(exc)}
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
