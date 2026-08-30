"""Independent verifier for a retained CRSE rule-profitability run."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bitset_backend import build_bitset_env, compile_expr_cse, eval_expr_bitset
from cmbench.recognition.computation_experiment import (
    ComputationTask, Workload, reference_task, sha256_file,
)
from cmbench.recognition.features import structural_digest
from cmbench.recognition.profitability_rule_experiment import (
    ARMS, RUN_SCHEMA, VERSIONS, DeterministicProfitabilityGate,
    ProfitabilityRuleConfig, canonical, make_versions, source_fingerprints,
    summarize, versions_document,
)
from cmbench.recognition.rule_pack import (
    RULE_PRIORITY_V2, ProvedRulePack, StructuralConeCache, compile_rule_pack,
    prove_rule_pack_v2,
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


def _digest_values(values: list[int]) -> str:
    return hashlib.sha256(canonical(values)).hexdigest()


def _verify_cell(row: dict[str, Any], cones, arm: str, gate,
                 matcher, cache_state: dict[str, tuple[str, Any]]) -> None:
    details = row.get("cones")
    if type(details) is not list or len(details) != len(cones):
        raise ValueError("per-cone measurement count disagreement")
    totals = Counter()
    rule_counts = Counter()
    outputs, result_digests = [], []
    active = set()
    for detail, cone in zip(details, cones):
        if detail.get("cone_id") != cone.cone_id:
            raise ValueError("cone measurement order disagreement")
        decision = gate.decide("complete_vector", cone.expected_reuses, cone.estimated_nodes)
        selected = arm in ("fresh_pack", "cached_pack") or (arm == "gated_cached" and decision.apply_rules)
        rewrite = matcher.rewrite(cone.expr, cone.n_vars) if selected else None
        source_digest = structural_digest(cone.expr)
        cache_hit = invalidated = False
        cache_reason = "not_applicable"
        if arm == "fresh_pack":
            cache_reason = "fresh_match"
        elif arm in ("cached_pack", "gated_cached") and selected:
            active.add(cone.cone_id)
            prior = cache_state.get(cone.cone_id)
            if prior is None:
                cache_reason = "cold_miss"
            elif prior[0] == source_digest:
                cache_hit, cache_reason = True, "unchanged_structural_identity"
                rewrite = prior[1]
            else:
                invalidated, cache_reason = True, "source_changed"
            cache_state[cone.cone_id] = (source_digest, rewrite)
        elif arm == "gated_cached":
            cache_reason = decision.reason
        result = rewrite.result if rewrite is not None else cone.expr
        expected = (reference_task(cone.expr, ComputationTask("complete_vector", 1),
                                   Workload(), cone.n_vars)[0] if cone.n_vars <= 8 else
                    eval_expr_bitset(cone.expr,
                        build_bitset_env(tuple(f"x{i}" for i in range(cone.n_vars)))))
        expected_detail = {
            "cone_id": cone.cone_id, "motif_family": cone.motif_family,
            "change_kind": cone.change_kind, "expected_reuses": cone.expected_reuses,
            "estimated_nodes": cone.estimated_nodes, "n_vars": cone.n_vars,
            "gate_apply": arm == "gated_cached" and decision.apply_rules,
            "gate_reason": decision.reason if arm == "gated_cached" else "not_gated",
            "cache_hit": cache_hit, "invalidated": invalidated, "cache_reason": cache_reason,
            "mismatches": 0,
            "applications": rewrite.applications if rewrite is not None else 0,
            "proposals": rewrite.proposals if rewrite is not None else 0,
            "conflicts": rewrite.conflicts if rewrite is not None else 0,
            "applications_by_rule": rewrite.applications_by_rule if rewrite is not None else
                                    {rule_id: 0 for rule_id in RULE_PRIORITY_V2},
            "cse_ops_before": len(compile_expr_cse(cone.expr, flatten=True).ops),
            "cse_ops_after": len(compile_expr_cse(result, flatten=True).ops),
            "output_sha256": _digest_values([expected]),
            "result_sha256": structural_digest(result),
        }
        for key, value in expected_detail.items():
            if detail.get(key) != value:
                raise ValueError(f"cone accounting disagreement: {key}")
        for timing in ("identity_ns", "rewrite_ns", "cse_build_ns", "cse_kernel_ns", "total_ns"):
            if type(detail.get(timing)) is not int or detail[timing] < 0:
                raise ValueError("invalid cone timing")
        if (arm in ("cached_pack", "gated_cached") and selected) != (detail["identity_ns"] > 0):
            raise ValueError("cone identity timing boundary disagreement")
        if (selected and not cache_hit) != (detail["rewrite_ns"] > 0):
            raise ValueError("cone rewrite timing boundary disagreement")
        totals.update({"cache_hits": int(cache_hit),
            "cache_misses": int(arm in ("cached_pack", "gated_cached") and selected and not cache_hit),
            "source_invalidations": int(invalidated),
            "computed_applications": 0 if cache_hit or rewrite is None else rewrite.applications,
            "reused_applications": rewrite.applications if cache_hit else 0,
            "proposals_computed": 0 if cache_hit or rewrite is None else rewrite.proposals,
            "conflicts_computed": 0 if cache_hit or rewrite is None else rewrite.conflicts,
            "gate_applies": int(arm == "gated_cached" and decision.apply_rules),
            "gate_skips": int(arm == "gated_cached" and not decision.apply_rules)})
        if rewrite is not None and not cache_hit:
            rule_counts.update(rewrite.applications_by_rule)
        outputs.append(expected)
        result_digests.append(structural_digest(result))
    removed = [cone_id for cone_id in cache_state if cone_id not in active]
    if arm in ("cached_pack", "gated_cached"):
        for cone_id in removed:
            del cache_state[cone_id]
    else:
        removed = []
    expected_aggregate = {
        "cache_hits": totals["cache_hits"], "cache_misses": totals["cache_misses"],
        "source_invalidations": totals["source_invalidations"],
        "removed_invalidations": len(removed),
        "invalidations": totals["source_invalidations"] + len(removed),
        "computed_applications": totals["computed_applications"],
        "reused_applications": totals["reused_applications"],
        "proposals_computed": totals["proposals_computed"],
        "conflicts_computed": totals["conflicts_computed"],
        "gate_applies": totals["gate_applies"], "gate_skips": totals["gate_skips"],
        "computed_applications_by_rule": {rule_id: rule_counts[rule_id] for rule_id in RULE_PRIORITY_V2},
        "output_sha256": _digest_values(outputs),
        "result_digests_sha256": hashlib.sha256(canonical(result_digests)).hexdigest(),
    }
    for key, value in expected_aggregate.items():
        if row.get(key) != value:
            raise ValueError(f"version accounting disagreement: {key}")
    if row.get("total_ns") != sum(detail["total_ns"] for detail in details) + row.get("maintenance_ns", -1):
        raise ValueError("version total timing identity disagreement")


def verify(run: Path) -> dict[str, Any]:
    run = run.resolve()
    required = {"run_spec.json", "proved_rule_pack.json", "versioned_cones.json",
                "cache_snapshot.json", "measurements.jsonl", "summary.json", "report.md"}
    manifest = _load_json(run / "manifest.json", 256_000)
    if (manifest.get("schema") != "crse-rule-profitability-artifacts/v1"
            or manifest.get("status") != "complete"
            or set(manifest.get("files_sha256", {})) != required):
        raise ValueError("artifact manifest identity or file set disagreement")
    for name, digest in manifest["files_sha256"].items():
        if type(digest) is not str or sha256_file(run / name) != digest:
            raise ValueError(f"artifact hash mismatch: {name}")
    spec = _load_json(run / "run_spec.json", 512_000)
    config_data = spec.get("config")
    if type(config_data) is not dict:
        raise ValueError("missing profitability configuration")
    config = ProfitabilityRuleConfig(**config_data)
    config.validate()
    if (spec.get("schema") != "crse-rule-profitability-run-spec/v1"
            or spec.get("arms") != list(ARMS) or spec.get("versions") != list(VERSIONS)
            or spec.get("rules") != list(RULE_PRIORITY_V2)
            or spec.get("source_sha256") != source_fingerprints()):
        raise ValueError("run specification or source identity disagreement")
    pack = ProvedRulePack.load(run / "proved_rule_pack.json")
    if pack.to_dict() != prove_rule_pack_v2().to_dict():
        raise ValueError("three-rule pack does not reproduce")
    matcher = compile_rule_pack(pack)
    StructuralConeCache.load(run / "cache_snapshot.json", matcher)
    versions, version_manifest = make_versions(config)
    recorded = _load_json(run / "versioned_cones.json", 16_000_000)
    if recorded != versions_document(versions, version_manifest):
        raise ValueError("profitability corpus does not reproduce")
    rows = _load_jsonl(run / "measurements.jsonl", 32_000_000)
    if len(rows) != len(VERSIONS) * len(ARMS) * config.rounds:
        raise ValueError("measurement row count disagreement")
    by_cell = {}
    for row in rows:
        key = (row.get("round"), row.get("arm"), row.get("version_id"))
        if key in by_cell:
            raise ValueError("duplicate measurement cell")
        if (row.get("schema") != "crse-rule-profitability-measurement/v1"
                or row.get("arm") not in ARMS or row.get("version_id") not in VERSIONS
                or row.get("status") != "ok" or row.get("mismatches") != 0):
            raise ValueError("invalid measurement identity or status")
        by_cell[key] = row
    gate = DeterministicProfitabilityGate(config.min_reuses, config.min_estimated_nodes)
    for round_index in range(config.rounds):
        for arm in ARMS:
            cache_state = {}
            for version_id in VERSIONS:
                row = by_cell[(round_index, arm, version_id)]
                if (row.get("cone_count") != config.cone_count
                        or row.get("declared_changed_cones") != version_manifest["versions"][version_id]["changed_count"]):
                    raise ValueError("version size or declared change disagreement")
                _verify_cell(row, versions[version_id], arm, gate, matcher, cache_state)
    summary = _load_json(run / "summary.json", 8_000_000)
    recomputed = summarize(rows, config.rounds)
    hardening = summary.get("hardening", {})
    if (summary.get("schema") != RUN_SCHEMA or summary.get("status") != "complete"
            or summary.get("source_unchanged") is not True
            or summary.get("row_count") != len(rows) or summary.get("semantic_mismatches") != 0
            or summary.get("failed_rows") != 0 or summary.get("summaries") != recomputed
            or summary.get("criteria", {}).get("safety_met") is not True
            or summary.get("criteria", {}).get("hardening_met") is not True
            or summary.get("criteria", {}).get("production_promotion") is not False
            or hardening.get("snapshot_sha256") != sha256_file(run / "cache_snapshot.json")):
        raise ValueError("summary recomputation or criteria disagreement")
    return {"schema": "crse-rule-profitability-verification/v1", "status": "pass",
            "artifacts_verified": len(required), "proof_rows_reproduced": 16,
            "versions_verified": len(VERSIONS), "cones_per_version": config.cone_count,
            "measurement_rows_verified": len(rows), "semantic_mismatches": 0,
            "cache_hardening_checks": 5}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.run)
    except Exception as exc:
        result = {"schema": "crse-rule-profitability-verification/v1", "status": "fail",
                  "error_type": type(exc).__name__, "error": str(exc)}
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
