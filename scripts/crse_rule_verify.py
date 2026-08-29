"""Independent structural and exactness verifier for a retained proved-rule run."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.computation_experiment import load_epfl_d_cases, sha256_file
from cmbench.recognition.features import structural_digest
from cmbench.recognition.proved_rules import ProvedRule, compile_rule, prove_aig_xor_rule
from cmbench.recognition.rule_experiment import (
    ARMS, RUN_SCHEMA, RuleExperimentConfig, canonical, source_fingerprints, summarize,
)
from cmbench.recognition.teacher import teach


def _load_json(path: Path, maximum: int) -> Any:
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError(f"{path.name} exceeds verifier size bound")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path.name}")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON value")))


def _load_jsonl(path: Path, maximum: int) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError(f"{path.name} exceeds verifier size bound")
    rows = []
    for line in raw.splitlines():
        if line:
            value = json.loads(line,
                parse_constant=lambda item: (_ for _ in ()).throw(ValueError("nonfinite JSONL value")))
            if type(value) is not dict:
                raise ValueError("measurement row must be an object")
            rows.append(value)
    return rows


def verify(run: Path) -> dict[str, Any]:
    run = run.resolve()
    required = {"run_spec.json", "proved_rule.json", "generated_regions.json",
                "epfl_evaluation_manifest.json", "measurements.jsonl", "summary.json", "report.md"}
    manifest = _load_json(run / "manifest.json", 128_000)
    if (manifest.get("schema") != "crse-proved-rule-artifacts/v1"
            or manifest.get("status") != "complete"
            or set(manifest.get("files_sha256", {})) != required):
        raise ValueError("artifact manifest identity or file set disagreement")
    for name, digest in manifest["files_sha256"].items():
        if type(digest) is not str or sha256_file(run / name) != digest:
            raise ValueError(f"artifact hash mismatch: {name}")
    spec = _load_json(run / "run_spec.json", 256_000)
    config_data = spec.get("config")
    if type(config_data) is not dict:
        raise ValueError("missing run configuration")
    config = RuleExperimentConfig(
        data_seed=config_data["data_seed"], batch_sizes=tuple(config_data["batch_sizes"]),
        rounds=config_data["rounds"], epfl_limit=config_data["epfl_limit"],
        negative_controls=config_data["negative_controls"], max_seconds=config_data["max_seconds"])
    config.validate()
    if spec.get("schema") != "crse-proved-rule-run-spec/v1" or spec.get("arms") != list(ARMS):
        raise ValueError("run specification identity disagreement")
    if spec.get("source_sha256") != source_fingerprints():
        raise ValueError("retained run does not match current source fingerprints")
    proof = ProvedRule.load(run / "proved_rule.json")
    if proof.to_dict() != prove_aig_xor_rule().to_dict():
        raise ValueError("retained metavariable proof does not reproduce")
    matcher = compile_rule(proof)
    regions = _load_json(run / "generated_regions.json", 4_000_000)
    if (regions.get("schema") != "crse-proved-rule-regions/v1"
            or regions.get("seed") != config.data_seed
            or len(regions.get("positive", [])) != max(config.batch_sizes)
            or len(regions.get("negative", [])) != config.negative_controls):
        raise ValueError("generated-region manifest disagreement")
    positives = []
    for expected_split, expected_matches, documents in (
            ("generated_positive", 1, regions["positive"]),
            ("generated_negative", 0, regions["negative"])):
        for document in documents:
            expr = expr_from_json(document["expression_v2"])
            rewrite = matcher.rewrite(expr, 8)
            if (document.get("split") != expected_split
                    or document.get("expected_root_matches") != expected_matches
                    or structural_digest(expr) != document.get("structural_sha256")
                    or rewrite.applications != expected_matches
                    or teach(expr, 8).bits != teach(rewrite.result, 8).bits):
                raise ValueError("generated region proof or match disagreement")
            if expected_split == "generated_positive":
                positives.append((document["region_id"], expr, rewrite.result))
    epfl_cases, expected_epfl_manifest = load_epfl_d_cases(config.epfl_limit)
    recorded_epfl = _load_json(run / "epfl_evaluation_manifest.json", 512_000)
    if recorded_epfl != expected_epfl_manifest:
        raise ValueError("EPFL evaluation selection disagreement")
    epfl = [(case.case_id, case.expr, matcher.rewrite(case.expr, 8).result) for case in epfl_cases]
    rows = _load_jsonl(run / "measurements.jsonl", 8_000_000)
    expected_rows = (len(config.batch_sizes) + 1) * config.rounds * len(ARMS)
    if len(rows) != expected_rows:
        raise ValueError("measurement row count disagreement")
    seen = set()
    for row in rows:
        key = (row.get("batch_id"), row.get("arm"), row.get("round"))
        if key in seen:
            raise ValueError("duplicate measurement cell")
        seen.add(key)
        if (row.get("schema") != "crse-proved-rule-measurement/v1"
                or row.get("arm") not in ARMS or row.get("status") != "ok"
                or row.get("mismatches") != 0 or row.get("rejected") != 0):
            raise ValueError("invalid measurement status")
        if row["split"] == "generated_positive":
            size = row["batch_size"]
            selected = positives[:size]
            expected_applications = 0 if row["arm"] == "no_rewrite" else size
        elif row["split"] == "epfl_d":
            selected = epfl
            expected_applications = 0 if row["arm"] == "no_rewrite" else sum(
                matcher.rewrite(case.expr, 8).applications for case in epfl_cases)
        else:
            raise ValueError("unexpected timed split")
        outputs = [teach(expr, 8).bits for _case_id, expr, _rewritten in selected]
        result_digests = [structural_digest(expr if row["arm"] == "no_rewrite" else rewritten)
                          for _case_id, expr, rewritten in selected]
        if (row["applications"] != expected_applications
                or row["proposals"] != expected_applications
                or row["proof_calls"] != (expected_applications if row["arm"] == "instance_cm_proof" else 0)
                or row["output_sha256"] != hashlib.sha256(canonical(outputs)).hexdigest()
                or row["result_digests_sha256"] != hashlib.sha256(canonical(result_digests)).hexdigest()):
            raise ValueError("measurement semantic or matcher accounting disagreement")
        if ((row["arm"] == "compiled_cold") != (row["load_compile_ns"] > 0)
                or (row["proof_calls"] > 0) != (row["proof_ns"] > 0)):
            raise ValueError("measurement cost-accounting disagreement")
    summary = _load_json(run / "summary.json", 2_000_000)
    recomputed = summarize(rows, config.rounds, summary["proof"]["one_time_proof_and_compile_ns"])
    if (summary.get("schema") != RUN_SCHEMA or summary.get("status") != "complete"
            or summary.get("source_unchanged") is not True or summary.get("semantic_mismatches") != 0
            or summary.get("failed_rows") != 0 or summary.get("row_count") != len(rows)
            or summary.get("summaries") != recomputed
            or summary.get("negative_controls") != {"cases": config.negative_controls, "false_matches": 0}
            or summary.get("criteria", {}).get("safety_met") is not True
            or summary.get("criteria", {}).get("production_promotion") is not False):
        raise ValueError("summary recomputation disagreement")
    return {"schema": "crse-proved-rule-verification/v1", "status": "pass",
            "artifacts_verified": len(required), "measurement_rows_verified": len(rows),
            "proof_rows_reproduced": 4, "generated_regions_verified": len(positives) + config.negative_controls,
            "epfl_cases_verified": len(epfl_cases), "semantic_mismatches": 0}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.run)
    except Exception as exc:
        result = {"schema": "crse-proved-rule-verification/v1", "status": "fail",
                  "error_type": type(exc).__name__, "error": str(exc)}
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
