"""Independent verifier for a retained versioned proved-rule cache run."""
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
from cmbench.recognition.computation_experiment import sha256_file
from cmbench.recognition.features import structural_digest
from cmbench.recognition.rule_pack import (
    RULE_PRIORITY, ProvedRulePack, compile_rule_pack, prove_rule_pack,
)
from cmbench.recognition.teacher import teach
from cmbench.recognition.versioned_rule_experiment import (
    ARMS, RUN_SCHEMA, VERSIONS, VersionedRuleConfig, canonical, make_versions,
    source_fingerprints, summarize, versions_document,
)


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
        if not line:
            continue
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate measurement JSON key")
                result[key] = value
            return result
        value = json.loads(line, object_pairs_hook=pairs,
            parse_constant=lambda item: (_ for _ in ()).throw(ValueError("nonfinite JSONL value")))
        if type(value) is not dict:
            raise ValueError("measurement row must be an object")
        rows.append(value)
    return rows


def verify(run: Path) -> dict[str, Any]:
    run = run.resolve()
    required = {"run_spec.json", "proved_rule_pack.json", "versioned_cones.json",
                "measurements.jsonl", "summary.json", "report.md"}
    manifest = _load_json(run / "manifest.json", 128_000)
    if (manifest.get("schema") != "crse-versioned-rule-cache-artifacts/v1"
            or manifest.get("status") != "complete"
            or set(manifest.get("files_sha256", {})) != required):
        raise ValueError("artifact manifest identity or file set disagreement")
    for name, digest in manifest["files_sha256"].items():
        if type(digest) is not str or sha256_file(run / name) != digest:
            raise ValueError(f"artifact hash mismatch: {name}")
    spec = _load_json(run / "run_spec.json", 256_000)
    config_data = spec.get("config")
    if type(config_data) is not dict:
        raise ValueError("missing versioned run configuration")
    config = VersionedRuleConfig(data_seed=config_data["data_seed"],
        cone_count=config_data["cone_count"],
        changed_per_transition=config_data["changed_per_transition"],
        rounds=config_data["rounds"], max_seconds=config_data["max_seconds"])
    config.validate()
    if (spec.get("schema") != "crse-versioned-rule-cache-run-spec/v1"
            or spec.get("arms") != list(ARMS) or spec.get("versions") != list(VERSIONS)
            or spec.get("rules") != list(RULE_PRIORITY)
            or spec.get("source_sha256") != source_fingerprints()):
        raise ValueError("run specification or source identity disagreement")
    pack = ProvedRulePack.load(run / "proved_rule_pack.json")
    if pack.to_dict() != prove_rule_pack().to_dict():
        raise ValueError("proved rule pack does not reproduce")
    matcher = compile_rule_pack(pack)
    generated_versions, generated_manifest = make_versions(config)
    recorded_versions = _load_json(run / "versioned_cones.json", 8_000_000)
    if recorded_versions != versions_document(generated_versions, generated_manifest):
        raise ValueError("versioned cone corpus does not reproduce")
    loaded_versions = {}
    for version_id in VERSIONS:
        loaded = []
        for document in recorded_versions["versions"][version_id]:
            expr = expr_from_json(document["expression_v2"])
            if structural_digest(expr) != document["structural_sha256"]:
                raise ValueError("retained cone structural identity disagreement")
            loaded.append((document["cone_id"], expr, matcher.rewrite(expr, 8)))
        loaded_versions[version_id] = loaded
    rows = _load_jsonl(run / "measurements.jsonl", 4_000_000)
    if len(rows) != len(VERSIONS) * len(ARMS) * config.rounds:
        raise ValueError("measurement row count disagreement")
    seen = set()
    for row in rows:
        key = (row.get("version_id"), row.get("arm"), row.get("round"))
        if key in seen:
            raise ValueError("duplicate versioned measurement cell")
        seen.add(key)
        version_id, arm = row.get("version_id"), row.get("arm")
        if (row.get("schema") != "crse-versioned-rule-measurement/v1"
                or version_id not in VERSIONS or arm not in ARMS
                or row.get("status") != "ok" or row.get("mismatches") != 0):
            raise ValueError("invalid versioned measurement status")
        changed = 0 if version_id == "v1" else config.changed_per_transition
        unchanged = config.cone_count - changed
        if arm == "no_rewrite":
            hits = misses = invalidations = computed = reused = proposals = conflicts = 0
            counts = {rule_id: 0 for rule_id in RULE_PRIORITY}
        elif arm == "fresh_pack":
            hits, misses, invalidations = 0, config.cone_count, 0
            computed, reused = 2 * config.cone_count, 0
            proposals, conflicts = 3 * config.cone_count, config.cone_count
            counts = {rule_id: config.cone_count for rule_id in RULE_PRIORITY}
        else:
            hits = 0 if version_id == "v1" else unchanged
            misses = config.cone_count if version_id == "v1" else changed
            invalidations = 0 if version_id == "v1" else changed
            computed, reused = 2 * misses, 2 * hits
            proposals, conflicts = 3 * misses, misses
            counts = {rule_id: misses for rule_id in RULE_PRIORITY}
        selected = loaded_versions[version_id]
        outputs = [teach(expr, 8).bits for _cone_id, expr, _rewrite in selected]
        digests = [structural_digest(expr if arm == "no_rewrite" else rewrite.result)
                   for _cone_id, expr, rewrite in selected]
        if (row["cone_count"] != config.cone_count
                or row["declared_changed_cones"] != changed
                or row["cache_hits"] != hits or row["cache_misses"] != misses
                or row["invalidations"] != invalidations
                or row["computed_applications"] != computed
                or row["reused_applications"] != reused
                or row["effective_applications"] != computed + reused
                or row["proposals_computed"] != proposals
                or row["conflicts_computed"] != conflicts
                or row["computed_applications_by_rule"] != counts
                or row["output_sha256"] != hashlib.sha256(canonical(outputs)).hexdigest()
                or row["result_digests_sha256"] != hashlib.sha256(canonical(digests)).hexdigest()):
            raise ValueError("versioned measurement accounting disagreement")
        if ((arm == "cached_pack") != (row["identity_ns"] > 0)
                or (arm != "no_rewrite") != (row["rewrite_ns"] > 0)):
            raise ValueError("versioned timing component disagreement")
    summary = _load_json(run / "summary.json", 2_000_000)
    recomputed = summarize(rows, config.rounds)
    if (summary.get("schema") != RUN_SCHEMA or summary.get("status") != "complete"
            or summary.get("source_unchanged") is not True
            or summary.get("semantic_mismatches") != 0 or summary.get("failed_rows") != 0
            or summary.get("row_count") != len(rows) or summary.get("summaries") != recomputed
            or summary.get("criteria", {}).get("safety_met") is not True
            or summary.get("criteria", {}).get("exact_invalidation_met") is not True
            or summary.get("criteria", {}).get("production_promotion") is not False):
        raise ValueError("versioned summary recomputation disagreement")
    return {"schema": "crse-versioned-rule-cache-verification/v1", "status": "pass",
            "artifacts_verified": len(required), "proof_rows_reproduced": 8,
            "versions_verified": len(VERSIONS), "cones_per_version": config.cone_count,
            "measurement_rows_verified": len(rows), "semantic_mismatches": 0,
            "changed_cone_invalidations_verified": config.changed_per_transition * 2}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.run)
    except Exception as exc:
        result = {"schema": "crse-versioned-rule-cache-verification/v1", "status": "fail",
                  "error_type": type(exc).__name__, "error": str(exc)}
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
