"""Independent verifier for a retained natural revision cache run."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.computation_experiment import sha256_file
from cmbench.recognition.natural_revision_experiment import (
    ARMS, RUN_SCHEMA, SOURCE_IDENTITY_CONTRACT, NaturalRevisionConfig,
    build_cache_snapshot, canonical, cnf_bitset, expected_case_details,
    load_natural_revision_cases, packed_sha, source_fingerprints, summarize,
)


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
    required = {"run_spec.json", "selection.json", "case_identities.json",
                "cache_snapshot.json", "measurements.jsonl", "summary.json", "report.md"}
    manifest = _load_json(run / "manifest.json", 256_000)
    if (manifest.get("schema") != "crse-natural-revision-cache-artifacts/v1"
            or manifest.get("status") != "complete"
            or set(manifest.get("files_sha256", {})) != required):
        raise ValueError("natural revision manifest identity or file set disagreement")
    for name, digest in manifest["files_sha256"].items():
        if type(digest) is not str or sha256_file(run / name) != digest:
            raise ValueError(f"natural revision artifact hash mismatch: {name}")
    spec = _load_json(run / "run_spec.json", 512_000)
    config_data = spec.get("config")
    if type(config_data) is not dict:
        raise ValueError("missing natural revision configuration")
    config = NaturalRevisionConfig(**config_data)
    config.validate()
    if (spec.get("schema") != "crse-natural-revision-cache-run-spec/v1"
            or spec.get("arms") != list(ARMS)
            or spec.get("source_identity_contract") != SOURCE_IDENTITY_CONTRACT
            or spec.get("source_sha256") != source_fingerprints()):
        raise ValueError("natural revision run specification disagreement")
    cases, selection = load_natural_revision_cases(config.case_limit)
    if _load_json(run / "selection.json", 1_000_000) != selection:
        raise ValueError("natural revision selection does not reproduce")
    expected = expected_case_details(cases)
    identities = _load_json(run / "case_identities.json", 2_000_000)
    if identities != {"schema": "crse-natural-revision-identities/v1",
                       "identity_contract": SOURCE_IDENTITY_CONTRACT, "cases": expected}:
        raise ValueError("natural revision identities do not reproduce")
    expected_by_id = {case.case_id: case for case in cases}
    rows = _load_jsonl(run / "measurements.jsonl", 32_000_000)
    if len(rows) != len(ARMS) * config.rounds:
        raise ValueError("natural revision measurement row count disagreement")
    seen = set()
    exact_hits = sum(item["exact_source_equal"] for item in expected)
    for row in rows:
        key = (row.get("round"), row.get("arm"))
        if key in seen:
            raise ValueError("duplicate natural revision measurement cell")
        seen.add(key)
        if (row.get("schema") != "crse-natural-revision-cache-measurement/v1"
                or row.get("status") != "ok" or row.get("arm") not in ARMS
                or type(row.get("round")) is not int or not 0 <= row["round"] < config.rounds
                or row.get("case_count") != len(cases) or row.get("mismatches") != 0
                or row.get("total_ns") != sum(row[name] for name in
                    ("identity_ns", "lower_ns", "compile_ns", "extract_ns", "direct_ns"))
                or len(row.get("cases", [])) != len(cases)):
            raise ValueError("invalid natural revision measurement accounting")
        if row["arm"] == "exact_revision_cache":
            if (row.get("later_cache_hits") != exact_hits
                    or row.get("later_invalidations") != len(cases) - exact_hits
                    or row.get("earlier_cold_misses") != len(cases)):
                raise ValueError("natural revision cache accounting disagreement")
        elif any(row.get(name) for name in
                 ("later_cache_hits", "later_invalidations", "earlier_cold_misses")):
            raise ValueError("non-cache arm reported cache activity")
        for detail, case in zip(row["cases"], cases):
            if detail.get("case_id") != case.case_id:
                raise ValueError("natural revision case order disagreement")
            earlier = packed_sha(cnf_bitset(case.earlier_residual, case.k), case.k)
            later = packed_sha(cnf_bitset(case.later_residual, case.k), case.k)
            if (earlier != case.earlier_packed_sha256 or later != case.later_packed_sha256
                    or detail.get("earlier_relation_sha256") != earlier
                    or detail.get("later_relation_sha256") != later):
                raise ValueError("natural revision exact relation disagreement")
    if _load_json(run / "cache_snapshot.json", 2_000_000) != build_cache_snapshot(cases):
        raise ValueError("natural revision cache snapshot does not reproduce")
    summary = _load_json(run / "summary.json", 8_000_000)
    recomputed = summarize(rows, cases, config.rounds)
    if (summary.get("schema") != RUN_SCHEMA or summary.get("status") != "complete"
            or summary.get("source_unchanged") is not True or summary.get("row_count") != len(rows)
            or summary.get("semantic_mismatches") != 0 or summary.get("failed_rows") != 0
            or summary.get("summaries") != recomputed
            or summary.get("criteria", {}).get("safety_met") is not True
            or summary.get("criteria", {}).get("exact_invalidation_met") is not True
            or summary.get("criteria", {}).get("actual_related_revisions_met") is not True
            or summary.get("criteria", {}).get("production_promotion") is not False):
        raise ValueError("natural revision summary or criteria disagreement")
    return {"schema": "crse-natural-revision-cache-verification/v1", "status": "pass",
        "artifacts_verified": len(required), "source_cases_verified": len(cases),
        "transition_ids_verified": len(selection["transition_ids"]),
        "measurement_rows_verified": len(rows), "exact_cache_hits_verified": exact_hits,
        "required_invalidations_verified": len(cases) - exact_hits,
        "semantic_mismatches": 0}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.run)
    except Exception as exc:
        result = {"schema": "crse-natural-revision-cache-verification/v1", "status": "fail",
                  "error_type": type(exc).__name__, "error": str(exc)}
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
