"""Independent verifier for a retained bounded natural normalization run."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bitset_backend import build_bitset_env, eval_expr_bitset
from cmbench.recognition.computation_experiment import sha256_file
from cmbench.recognition.features import structural_digest
from cmbench.recognition.normalization import normalize_to_fixpoint
from cmbench.recognition.normalization_experiment import (
    ARMS, RUN_SCHEMA, NormalizationConfig, load_cases, packed_sha,
    source_fingerprints, summarize,
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
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON value")))


def _load_jsonl(path: Path, maximum: int) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError(f"{path.name} exceeds verifier size bound")
    rows = []
    for line in raw.splitlines():
        if line:
            value = json.loads(line, object_pairs_hook=_pairs,
                parse_constant=lambda item: (_ for _ in ()).throw(ValueError("nonfinite JSONL value")))
            if type(value) is not dict:
                raise ValueError("measurement row must be an object")
            rows.append(value)
    return rows


def verify(run: Path) -> dict[str, Any]:
    run = run.resolve()
    required = {"run_spec.json", "natural_cases.json", "proved_rule_pack.json",
                "measurements.jsonl", "summary.json", "report.md"}
    manifest = _load_json(run / "manifest.json", 256_000)
    if (manifest.get("schema") != "crse-natural-normalization-artifacts/v1"
            or manifest.get("status") != "complete"
            or set(manifest.get("files_sha256", {})) != required):
        raise ValueError("normalization manifest identity or file set disagreement")
    for name, digest in manifest["files_sha256"].items():
        if type(digest) is not str or sha256_file(run / name) != digest:
            raise ValueError(f"normalization artifact hash mismatch: {name}")
    spec = _load_json(run / "run_spec.json", 512_000)
    config_data = spec.get("config")
    if type(config_data) is not dict:
        raise ValueError("missing normalization configuration")
    config = NormalizationConfig(**config_data)
    config.validate()
    if (spec.get("schema") != "crse-natural-normalization-run-spec/v1"
            or spec.get("arms") != list(ARMS) or spec.get("source_sha256") != source_fingerprints()):
        raise ValueError("normalization run specification disagreement")
    pack = ProvedRulePack.load(run / "proved_rule_pack.json")
    if pack.to_dict() != prove_rule_pack_v2().to_dict():
        raise ValueError("normalization proved pack does not reproduce")
    matcher = compile_rule_pack(pack)
    cases, selection, case_document = load_cases(config)
    if _load_json(run / "natural_cases.json", 16_000_000) != case_document:
        raise ValueError("normalization natural selection does not reproduce")
    expected = {case.cone_id: eval_expr_bitset(case.expr,
        build_bitset_env(tuple(f"x{i}" for i in range(case.n_vars)))) for case in cases}
    rows = _load_jsonl(run / "measurements.jsonl", 32_000_000)
    if len(rows) != len(ARMS) * config.rounds:
        raise ValueError("normalization measurement row count disagreement")
    seen = set()
    for row in rows:
        key = (row.get("round"), row.get("arm"))
        if key in seen:
            raise ValueError("duplicate normalization measurement cell")
        seen.add(key)
        if (row.get("schema") != "crse-natural-normalization-measurement/v1"
                or row.get("status") != "ok" or row.get("arm") not in ARMS
                or row.get("case_count") != len(cases) or row.get("kernel_repeats") != 128
                or row.get("mismatches") != 0
                or row.get("total_ns") != row.get("normalization_ns")
                    + row.get("cse_build_ns") + row.get("kernel_ns")
                or len(row.get("cases", [])) != len(cases)):
            raise ValueError("normalization measurement accounting disagreement")
        for detail, case in zip(row["cases"], cases):
            if detail.get("case_id") != case.cone_id or detail.get("source_sha256") != structural_digest(case.expr):
                raise ValueError("normalization case identity disagreement")
            if row["arm"] == "no_rewrite":
                result = case.expr
                applications = conflicts = productive = convergence = 0
                by_rule = {rule_id: 0 for rule_id in matcher.rule_ids}
            elif row["arm"] == "one_pass":
                rewrite = matcher.rewrite(case.expr, case.n_vars)
                result = rewrite.result
                applications, conflicts = rewrite.applications, rewrite.conflicts
                productive, convergence = int(applications > 0), 1
                by_rule = rewrite.applications_by_rule
            else:
                normalized = normalize_to_fixpoint(matcher, case.expr, case.n_vars,
                                                    max_passes=config.max_passes)
                result = normalized.result
                applications, conflicts = normalized.total_applications, normalized.total_conflicts
                productive, convergence = normalized.productive_passes, normalized.convergence_passes
                by_rule = normalized.applications_by_rule
            if (detail.get("result_sha256") != structural_digest(result)
                    or detail.get("applications") != applications
                    or detail.get("conflicts") != conflicts
                    or detail.get("productive_passes") != productive
                    or detail.get("convergence_passes") != convergence
                    or detail.get("applications_by_rule") != by_rule
                    or detail.get("value_sha256") != packed_sha(expected[case.cone_id], case.n_vars)):
                raise ValueError("normalization structural reproduction disagreement")
    summary = _load_json(run / "summary.json", 8_000_000)
    recomputed = summarize(rows, config.rounds)
    if (summary.get("schema") != RUN_SCHEMA or summary.get("status") != "complete"
            or summary.get("source_unchanged") is not True or summary.get("row_count") != len(rows)
            or summary.get("semantic_mismatches") != 0 or summary.get("failed_rows") != 0
            or summary.get("summaries") != recomputed
            or summary.get("criteria", {}).get("safety_met") is not True
            or summary.get("criteria", {}).get("fixpoint_met") is not True
            or summary.get("criteria", {}).get("independent_confirmation") is not False
            or summary.get("criteria", {}).get("production_promotion") is not False):
        raise ValueError("normalization summary or criteria disagreement")
    return {"schema": "crse-natural-normalization-verification/v1", "status": "pass",
        "artifacts_verified": len(required), "natural_cases_verified": len(cases),
        "measurement_rows_verified": len(rows), "proof_rows_reproduced": 16,
        "fixpoint_applications_verified": sum(summary["summaries"]["incidence"]["fixpoint"]
            ["applications_by_rule"].values()), "semantic_mismatches": 0}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.run)
    except Exception as exc:
        result = {"schema": "crse-natural-normalization-verification/v1", "status": "fail",
                  "error_type": type(exc).__name__, "error": str(exc)}
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
