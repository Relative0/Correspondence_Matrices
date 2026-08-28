"""Independent exact-relation, timing-sample, provenance, and aggregate audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from functools import lru_cache
from pathlib import Path


WIDTHS = (8, 12, 16)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksums(run: Path) -> int:
    lines = (run / "CHECKSUMS.sha256").read_text(encoding="ascii").splitlines()
    for line in lines:
        expected, relative = line.split("  ", 1)
        path = run / relative
        require(path.is_file(), f"missing checksummed file: {relative}")
        require(sha256_file(path) == expected, f"checksum mismatch: {relative}")
    return len(lines)


@lru_cache(maxsize=None)
def patterns(k: int) -> tuple[int, ...]:
    return tuple(sum(1 << assignment for assignment in range(1 << k) if (assignment >> variable) & 1)
                 for variable in range(k))


def cnf_bitset(clauses: tuple[tuple[int, ...], ...], k: int) -> int:
    mask = (1 << (1 << k)) - 1
    value = mask
    pats = patterns(k)
    for clause in clauses:
        clause_value = 0
        for literal in clause:
            require(1 <= abs(literal) <= k, f"literal outside bounded relation: {literal}")
            pattern = pats[abs(literal) - 1]
            clause_value |= pattern if literal > 0 else (~pattern) & mask
        value &= clause_value
    return value


def packed_sha(value: int, k: int) -> str:
    return hashlib.sha256(value.to_bytes(1 << max(0, k - 3), "little")).hexdigest()


def first_set(value: int) -> int:
    return -1 if value == 0 else (value & -value).bit_length() - 1


def geomean(values) -> float:
    vals = [float(value) for value in values]
    return math.exp(statistics.fmean(math.log(value) for value in vals))


def close(actual: float, expected: float, label: str) -> None:
    require(math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12),
            f"{label}: {actual} != {expected}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    checksum_count = verify_checksums(run)
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((run / "version-delta.csv").open(encoding="utf-8", newline="")))
    admissions = list(csv.DictReader((run / "admissions.csv").open(encoding="utf-8", newline="")))
    cases = {row["case_id"]: row for row in
             (json.loads(line) for line in (run / "cases.jsonl").read_text(encoding="utf-8").splitlines())}
    inputs = [json.loads(line) for line in (run / "inputs.jsonl").read_text(encoding="utf-8").splitlines()]
    require(summary["status"] == "completed", "refusing to audit diagnostic version-delta run as complete")
    require(len(rows) == len(cases) == summary["case_count"] == 120, "case count mismatch")
    require(len(admissions) == summary["transition_count"] == 21, "transition count mismatch")
    admitted = [row for row in admissions if row["admitted"] == "True"]
    refused = [row for row in admissions if row["admitted"] == "False"]
    require(len(admitted) == 20 and len(refused) == 1, "unexpected transition admission/refusal count")
    require(refused[0]["transition_id"] == "Linux@2013-11-06T06_39_45+01_00->2013-12-11T15_52_34+01_00",
            "unexpected refused transition")
    require(refused[0]["reason"] == "adjacent versions have no joint satisfying assignment over shared feature names",
            "unexpected refusal reason")
    require(summary["admitted_transitions"] == 20 and summary["correctness_mismatches"] == 0,
            "published admission/correctness mismatch")
    require(len(inputs) == 40, "input cardinality mismatch")
    for item in inputs:
        path = Path(item["path"])
        require(path.is_file(), f"missing source input during audit: {path}")
        require(path.stat().st_size == item["bytes"] and sha256_file(path) == item["sha256"],
                f"source input changed: {item['model_id']}")

    relation_reconstructions = 0
    sample_medians = 0
    for row in rows:
        case = cases[row["case_id"]]
        k = int(row["k"])
        require(k == int(case["k"]), f"case width mismatch: {row['case_id']}")
        earlier = tuple(tuple(int(literal) for literal in clause) for clause in case["earlier_residual"])
        later = tuple(tuple(int(literal) for literal in clause) for clause in case["later_residual"])
        earlier_value = cnf_bitset(earlier, k)
        later_value = cnf_bitset(later, k)
        changed = earlier_value ^ later_value
        require(row["relations_equal_all_arms"] == "True", f"published equality flag false: {row['case_id']}")
        require(packed_sha(earlier_value, k) == row["earlier_packed_sha256"] == case["earlier_packed_sha256"],
                f"earlier digest mismatch: {row['case_id']}")
        require(packed_sha(later_value, k) == row["later_packed_sha256"] == case["later_packed_sha256"],
                f"later digest mismatch: {row['case_id']}")
        require(packed_sha(changed, k) == row["changed_packed_sha256"] == case["changed_packed_sha256"],
                f"delta digest mismatch: {row['case_id']}")
        require(earlier_value.bit_count() == int(row["earlier_count"]), f"earlier count mismatch: {row['case_id']}")
        require(later_value.bit_count() == int(row["later_count"]), f"later count mismatch: {row['case_id']}")
        require(changed.bit_count() == int(row["changed_assignments"]), f"delta count mismatch: {row['case_id']}")
        require(first_set(earlier_value) == int(row["earlier_witness_assignment"]), f"earlier witness mismatch: {row['case_id']}")
        require(first_set(later_value) == int(row["later_witness_assignment"]), f"later witness mismatch: {row['case_id']}")
        require((later_value & ~earlier_value).bit_count() == int(row["added_assignments"]), f"added count mismatch: {row['case_id']}")
        require((earlier_value & ~later_value).bit_count() == int(row["removed_assignments"]), f"removed count mismatch: {row['case_id']}")
        close(row["changed_fraction"], changed.bit_count() / (1 << k), "changed fraction")
        close(row["relation_jaccard"], (earlier_value & later_value).bit_count() / max(1, (earlier_value | later_value).bit_count()),
              "relation Jaccard")
        cm_samples = json.loads(row["cm_samples_json"])
        cudd_samples = json.loads(row["cudd_samples_json"])
        require(len(cm_samples) == len(cudd_samples) == int(manifest["rounds"]), f"sample count mismatch: {row['case_id']}")
        close(row["cm_earlier_compile_ns_median"], statistics.median(item["earlier_compile_ns"] for item in cm_samples), "CM earlier median")
        close(row["cm_later_reuse_compile_ns_median"], statistics.median(item["later_reuse_compile_ns"] for item in cm_samples), "CM later median")
        close(row["cm_extract_pair_ns_median"], statistics.median(item["extract_pair_ns"] for item in cm_samples), "CM extraction median")
        close(row["cudd_extract_pair_ns_median"], statistics.median(item["extract_pair_ns"] for item in cudd_samples), "CUDD extraction median")
        require(int(row["cadical_selector_queries"]) == 2 * (1 << k), f"SAT query count mismatch: {row['case_id']}")
        relation_reconstructions += 3
        sample_medians += 4

    for k in WIDTHS:
        selected = [row for row in rows if int(row["k"]) == k]
        published = summary["by_k"][str(k)]
        require(len(selected) == published["n"] == 40, f"stratum size mismatch k={k}")
        require(sum(int(row["changed_assignments"]) > 0 for row in selected) == published["nonzero_delta_cases"],
                f"nonzero delta aggregate mismatch k={k}")
        require(sum(int(row["changed_assignments"]) == 0 for row in selected) == published["identical_relation_cases"],
                f"identical aggregate mismatch k={k}")
        close(published["changed_fraction_median"], statistics.median(float(row["changed_fraction"]) for row in selected),
              f"changed median k={k}")
        close(published["relation_jaccard_median"], statistics.median(float(row["relation_jaccard"]) for row in selected),
              f"Jaccard median k={k}")
        close(published["cm_over_cudd_pair_extraction_geomean"],
              geomean(float(row["cm_extract_pair_ns_median"]) / float(row["cudd_extract_pair_ns_median"]) for row in selected),
              f"CM/CUDD k={k}")
        close(published["cadical_over_cm_pair_extraction_geomean"],
              geomean(float(row["cadical_selector_enumerate_pair_ns"]) / float(row["cm_extract_pair_ns_median"]) for row in selected),
              f"SAT/CM k={k}")

    audit = {
        "schema_version": "cm-fm-version-delta-audit/v1",
        "status": "passed",
        "checksum_files_verified_before_audit_output": checksum_count,
        "source_inputs_rehashed": len(inputs),
        "transition_admissions_rechecked": len(admissions),
        "transition_refusals_rechecked": len(refused),
        "bounded_relations_reconstructed": relation_reconstructions,
        "timing_sample_medians_recomputed": sample_medians,
        "aggregate_width_strata_recomputed": len(WIDTHS),
    }
    audit_path = run / "independent-audit.json"
    require(not audit_path.exists(), f"refusing to overwrite audit: {audit_path}")
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files = sorted(path for path in run.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
    (run / "CHECKSUMS.sha256").write_text(
        "".join(f"{sha256_file(path)}  {path.relative_to(run).as_posix()}\n" for path in files), encoding="ascii"
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
