"""Independent verifier for a retained natural EPFL proved-rule run."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.computation_experiment import sha256_file
from cmbench.recognition.natural_rule_experiment import (
    ARMS, RUN_SCHEMA, SESSIONS, NaturalRuleConfig, cases_document,
    load_natural_cases, make_sessions, source_fingerprints, summarize_natural,
)
from cmbench.recognition.profitability_rule_experiment import DeterministicProfitabilityGate
from cmbench.recognition.rule_pack import ProvedRulePack, compile_rule_pack, prove_rule_pack_v2
from scripts.crse_rule_profitability_verify import _verify_cell


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
    if (manifest.get("schema") != "crse-natural-rule-profitability-artifacts/v1"
            or manifest.get("status") != "complete"
            or set(manifest.get("files_sha256", {})) != required):
        raise ValueError("natural artifact manifest identity or file set disagreement")
    for name, digest in manifest["files_sha256"].items():
        if type(digest) is not str or sha256_file(run / name) != digest:
            raise ValueError(f"natural artifact hash mismatch: {name}")
    spec = _load_json(run / "run_spec.json", 512_000)
    config_data = spec.get("config")
    if type(config_data) is not dict:
        raise ValueError("missing natural rule configuration")
    config = NaturalRuleConfig(**config_data)
    config.validate()
    if (spec.get("schema") != "crse-natural-rule-profitability-run-spec/v1"
            or spec.get("arms") != list(ARMS) or spec.get("sessions") != list(SESSIONS)
            or spec.get("source_sha256") != source_fingerprints()):
        raise ValueError("natural run specification or source identity disagreement")
    pack = ProvedRulePack.load(run / "proved_rule_pack.json")
    if pack.to_dict() != prove_rule_pack_v2().to_dict():
        raise ValueError("natural run proved pack does not reproduce")
    matcher = compile_rule_pack(pack)
    cases, selection = load_natural_cases(config)
    if _load_json(run / "natural_cases.json", 16_000_000) != cases_document(cases, selection):
        raise ValueError("sealed natural case selection does not reproduce")
    sessions = make_sessions(cases)
    rows = _load_jsonl(run / "measurements.jsonl", 64_000_000)
    if len(rows) != len(SESSIONS) * len(ARMS) * config.rounds:
        raise ValueError("natural measurement row count disagreement")
    by_cell = {}
    for row in rows:
        key = (row.get("round"), row.get("arm"), row.get("version_id"))
        if key in by_cell:
            raise ValueError("duplicate natural measurement cell")
        if (row.get("schema") != "crse-rule-profitability-measurement/v1"
                or row.get("arm") not in ARMS or row.get("version_id") not in SESSIONS
                or row.get("status") != "ok" or row.get("mismatches") != 0):
            raise ValueError("invalid natural measurement identity or status")
        by_cell[key] = row
    gate = DeterministicProfitabilityGate(config.min_reuses, config.min_estimated_nodes)
    for round_index in range(config.rounds):
        for arm in ARMS:
            cache_state = {}
            for session in SESSIONS:
                row = by_cell[(round_index, arm, session)]
                if row.get("cone_count") != config.case_count or row.get("declared_changed_cones") != 0:
                    raise ValueError("natural session size or change accounting disagreement")
                _verify_cell(row, sessions[session], arm, gate, matcher, cache_state)
    summary = _load_json(run / "summary.json", 8_000_000)
    recomputed = summarize_natural(rows, config.rounds)
    if (summary.get("schema") != RUN_SCHEMA or summary.get("status") != "complete"
            or summary.get("source_unchanged") is not True or summary.get("row_count") != len(rows)
            or summary.get("semantic_mismatches") != 0 or summary.get("failed_rows") != 0
            or summary.get("summaries") != recomputed
            or summary.get("criteria", {}).get("safety_met") is not True
            or summary.get("criteria", {}).get("sealed_natural_source_met") is not True
            or summary.get("criteria", {}).get("production_promotion") is not False):
        raise ValueError("natural summary recomputation or criteria disagreement")
    incidence = recomputed["natural_rule_incidence"]
    return {"schema": "crse-natural-rule-profitability-verification/v1", "status": "pass",
            "artifacts_verified": len(required), "proof_rows_reproduced": 16,
            "natural_cases_verified": config.case_count, "sessions_verified": len(SESSIONS),
            "measurement_rows_verified": len(rows), "semantic_mismatches": 0,
            "natural_rule_applications_verified": sum(value["applications"] for value in incidence.values())}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.run)
    except Exception as exc:
        result = {"schema": "crse-natural-rule-profitability-verification/v1", "status": "fail",
                  "error_type": type(exc).__name__, "error": str(exc)}
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
