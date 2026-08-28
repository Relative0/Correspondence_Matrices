"""Independent checksum, aggregation, and scalar-semantics audit for the FM pilot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import cm_feature_model_history_pilot as pilot


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def close(actual: float, expected: float, message: str) -> None:
    require(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), f"{message}: {actual} != {expected}")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_checksums(run: Path) -> int:
    lines = (run / "CHECKSUMS.sha256").read_text(encoding="ascii").splitlines()
    checked = 0
    for line in lines:
        digest, filename = line.split("  ", 1)
        path = run / filename
        require(path.is_file(), f"checksummed file missing: {filename}")
        require(pilot.sha256_file(path) == digest, f"checksum mismatch: {filename}")
        checked += 1
    return checked


def decode_witness(record: dict) -> dict[int, bool]:
    raw = bytes.fromhex(record["product_little_endian_hex"])
    require(hashlib.sha256(raw).hexdigest() == record["product_sha256"], f"witness digest mismatch: {record['model_id']}")
    expected_size = (int(record["n_vars"]) + 7) // 8
    require(len(raw) == expected_size, f"witness width mismatch: {record['model_id']}")
    value = int.from_bytes(raw, "little")
    return {variable: bool((value >> (variable - 1)) & 1) for variable in range(1, int(record["n_vars"]) + 1)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--source", type=Path, default=pilot.DEFAULT_SOURCE)
    args = parser.parse_args()
    run = args.run.resolve()
    source = args.source.resolve()

    checksum_count = verify_checksums(run)
    manifest = read_json(run / "manifest.json")
    provenance = read_json(run / "SOURCE-PROVENANCE.json")
    summary = read_json(run / "summary.json")
    admissions = read_json(run / "admissions.json")
    require(manifest["source_commit"] == pilot.SOURCE_COMMIT, "manifest source commit mismatch")
    require(provenance["source_commit"] == pilot.SOURCE_COMMIT, "provenance source commit mismatch")
    require(pilot.root_tree(source), "source tree unavailable")

    with (run / "raw.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    witnesses = {}
    with (run / "witnesses.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            require(record["model_id"] not in witnesses, f"duplicate witness: {record['model_id']}")
            witnesses[record["model_id"]] = record
    payloads = {record["model_id"]: record for record in provenance["selected_payloads"]}
    admitted_ids = {record["model_id"] for record in admissions if record["admitted"]}
    require(len(rows) == int(summary["row_count"]), "raw row count mismatch")
    require(len(admitted_ids) == int(summary["admitted_payload_count"]), "admitted count mismatch")
    require(set(witnesses) == admitted_ids, "witness/admission model set mismatch")
    require(all(row["packed_equal_all_arms"] == "True" for row in rows), "raw correctness flag failure")

    for row in rows:
        close(float(row["cm_over_cnf_bitset"]), float(row["cm_ns_median"]) / float(row["cnf_bitset_ns_median"]), "CM/CNF ratio")
        close(float(row["cm_over_cse_flat"]), float(row["cm_ns_median"]) / float(row["cse_flat_ns_median"]), "CM/CSE ratio")
        close(float(row["cm_over_cadical195"]), float(row["cm_ns_median"]) / float(row["cadical195_ns_median"]), "CM/CaDiCaL ratio")

    aggregations = {
        "primary_cm_over_cnf_bitset": "cm_over_cnf_bitset",
        "secondary_cm_over_cse_flat": "cm_over_cse_flat",
        "secondary_cm_over_cadical195": "cm_over_cadical195",
    }
    recomputed = {}
    for summary_key, ratio_key in aggregations.items():
        aggregate = pilot.clustered_summary(rows, ratio_key)
        recomputed[summary_key] = aggregate
        close(aggregate["geomean"], summary[summary_key]["geomean"], f"{summary_key} geomean")
        close(aggregate["ci95"][0], summary[summary_key]["ci95"][0], f"{summary_key} lower CI")
        close(aggregate["ci95"][1], summary[summary_key]["ci95"][1], f"{summary_key} upper CI")

    family_ratio = sum(float(row["family_cm_compile_ns"]) for row in rows) / sum(float(row["fresh_cm_compile_ns"]) for row in rows)
    close(family_ratio, summary["family_compile"]["total_family_over_fresh"], "family compile ratio")
    hits_by_history = {}
    for row in rows:
        hits_by_history[row["history"]] = hits_by_history.get(row["history"], 0) + int(row["persistent_hits"])
    require(hits_by_history == summary["family_compile"]["persistent_hits_by_history"], "persistent hits aggregation mismatch")
    expected_gates = {
        "correctness": True,
        "specialized_warm_advantage": recomputed["primary_cm_over_cnf_bitset"]["geomean"] <= 0.95
        and recomputed["primary_cm_over_cnf_bitset"]["ci95"][1] < 1.0,
        "incumbent_batch_advantage": recomputed["secondary_cm_over_cadical195"]["geomean"] <= 0.80
        and recomputed["secondary_cm_over_cadical195"]["ci95"][1] < 1.0,
        "family_construction_advantage": family_ratio <= 0.90 and all(value > 0 for value in hits_by_history.values()),
    }
    require(expected_gates == summary["gates"], "gate recomputation mismatch")

    rows_by_model: dict[str, list[dict]] = {}
    for row in rows:
        rows_by_model.setdefault(row["model_id"], []).append(row)
    semantic_checks = 0
    for model_id in sorted(admitted_ids):
        payload = payloads[model_id]
        dimacs_path = source / "selected_payloads" / payload["cache_filename"]
        require(dimacs_path.is_file(), f"cached DIMACS missing: {model_id}")
        require(pilot.sha256_file(dimacs_path) == payload["dimacs_sha256"], f"payload checksum mismatch: {model_id}")
        parsed = pilot.parse_dimacs(dimacs_path)
        witness_record = witnesses[model_id]
        require(parsed.n_vars == int(witness_record["n_vars"]), f"witness/model width mismatch: {model_id}")
        product = decode_witness(witness_record)
        require(pilot.scalar_cnf(parsed.clauses, product), f"stored witness is not satisfying: {model_id}")
        slices = pilot.choose_slices(model_id, parsed)
        require({row["slice_kind"] for row in rows_by_model[model_id]} == set(slices), f"slice set mismatch: {model_id}")
        for row in rows_by_model[model_id]:
            variables = tuple(json.loads(row["slice_variables_json"]))
            require(variables == slices[row["slice_kind"]], f"slice selection mismatch: {model_id} {row['slice_kind']}")
            residual, stats = pilot.condition_cnf(parsed.clauses, product, variables)
            packed = pilot.cnf_bitset(residual)
            digest = hashlib.sha256(packed.to_bytes(pilot.PACKED_WIDTH // 8, "little")).hexdigest()
            require(digest == row["packed_sha256"], f"packed digest mismatch: {model_id} {row['slice_kind']}")
            require(packed.bit_count() == int(row["packed_true_count"]), f"packed count mismatch: {model_id} {row['slice_kind']}")
            require(stats["residual_clauses"] == int(row["residual_clauses"]), f"residual clause mismatch: {model_id}")
            pilot.scalar_spotcheck(parsed, product, variables, packed)
            semantic_checks += 1

    audit = {
        "schema_version": "1.0",
        "status": "passed",
        "checksum_files_verified_before_audit_output": checksum_count,
        "raw_rows_verified": len(rows),
        "models_reparsed": len(admitted_ids),
        "independent_scalar_semantic_checks": semantic_checks,
        "aggregations_recomputed": sorted(aggregations),
        "gates_recomputed": expected_gates,
        "source_commit": pilot.SOURCE_COMMIT,
    }
    pilot.json_dump(run / "independent-audit.json", audit)
    pilot.write_checksums(run)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
