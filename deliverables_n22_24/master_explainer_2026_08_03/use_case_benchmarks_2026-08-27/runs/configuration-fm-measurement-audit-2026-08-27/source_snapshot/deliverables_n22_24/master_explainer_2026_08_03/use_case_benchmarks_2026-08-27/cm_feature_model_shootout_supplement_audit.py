"""Independent checksum, exact-count, artifact, sample, and aggregate audit."""

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


def read_dimacs(path: Path) -> tuple[int, tuple[tuple[int, ...], ...]]:
    lines = path.read_text(encoding="ascii").splitlines()
    header = lines[0].split()
    require(header[:2] == ["p", "cnf"], f"invalid DIMACS header: {path}")
    k, declared = int(header[2]), int(header[3])
    clauses = tuple(tuple(map(int, line.split()[:-1])) for line in lines[1:] if line.strip())
    require(len(clauses) == declared, f"DIMACS clause mismatch: {path}")
    return k, clauses


def cnf_bitset(clauses: tuple[tuple[int, ...], ...], k: int) -> int:
    mask = (1 << (1 << k)) - 1
    value = mask
    pats = patterns(k)
    for clause in clauses:
        clause_value = 0
        for literal in clause:
            pattern = pats[abs(literal) - 1]
            clause_value |= pattern if literal > 0 else (~pattern) & mask
        value &= clause_value
    return value


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
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((run / "supplement.csv").open(encoding="utf-8", newline="")))
    rss_rows = list(csv.DictReader((run / "native-rss.csv").open(encoding="utf-8", newline="")))
    core = Path(manifest["core_run"])
    require(core.is_dir(), f"core run unavailable: {core}")
    require(sha256_file(core / "CHECKSUMS.sha256") == manifest["core_checksums_sha256"],
            "core checksum manifest changed")
    require(len(rows) == summary["case_count"] == 240, "supplement case count mismatch")
    require(len(rss_rows) == summary["rss_case_count"] == 160, "RSS row count mismatch")
    require(all(value == 0 for value in summary["correctness"].values()), "published mismatch counter is nonzero")

    relation_counts = 0
    ddnnf_artifacts = 0
    for row in rows:
        case_hash = hashlib.sha256(row["case_id"].encode()).hexdigest()[:16]
        k, clauses = read_dimacs(core / "serialized" / case_hash / "residual.dimacs")
        require(k == int(row["k"]), f"width mismatch: {row['case_id']}")
        packed = cnf_bitset(clauses, k)
        require(packed.bit_count() == int(row["expected_count"]) == int(row["d4_count"]),
                f"exact count mismatch: {row['case_id']}")
        require(row["cudd_sifting_relation_equal"] == "True", f"CUDD equality flag false: {row['case_id']}")
        require(row["d4_count_equal"] == "True" and row["d4_compile_count_equal"] == "True",
                f"d4 equality flag false: {row['case_id']}")
        sifting = json.loads(row["cudd_sifting_samples_json"])
        d4_samples = json.loads(row["d4_count_samples_json"])
        require(len(sifting) == len(d4_samples) == int(manifest["rounds"]), f"sample count mismatch: {row['case_id']}")
        close(float(row["cudd_reorder_ns_median"]), statistics.median(item["reorder_ns"] for item in sifting), "reorder median")
        close(float(row["cudd_sifted_over_fixed_nodes"]),
              statistics.median(item["sifted_nodes"] / item["fixed_nodes"] for item in sifting), "node ratio")
        close(float(row["d4_count_wall_ns_median"]), statistics.median(item["wall_ns"] for item in d4_samples), "d4 wall median")
        close(float(row["d4_count_peak_rss_bytes_median"]),
              statistics.median(item["peak_rss_bytes"] for item in d4_samples), "d4 RSS median")
        nnf = run / "ddnnf" / f"{case_hash}.nnf"
        require(nnf.is_file() and nnf.stat().st_size == int(row["ddnnf_bytes"]), f"d-DNNF size mismatch: {row['case_id']}")
        require(sha256_file(nnf) == row["ddnnf_sha256"], f"d-DNNF hash mismatch: {row['case_id']}")
        require(int(row["ddnnf_nodes"]) >= 0 and int(row["ddnnf_edges"]) >= 0, f"invalid d-DNNF metrics: {row['case_id']}")
        relation_counts += 1
        ddnnf_artifacts += 1

    for k in WIDTHS:
        selected = [row for row in rows if int(row["k"]) == k]
        published = summary["by_k"][str(k)]
        require(len(selected) == published["n"] == 80, f"stratum size mismatch k={k}")
        close(published["sifted_over_fixed_nodes_geomean"],
              geomean(row["cudd_sifted_over_fixed_nodes"] for row in selected), f"sifting k={k}")
        close(published["d4_count_over_packed_count_geomean"],
              geomean(float(row["d4_count_wall_ns_median"]) / float(row["core_packed_count_ns"]) for row in selected), f"count k={k}")
        close(published["ddnnf_over_robdd_bytes_geomean"],
              geomean(float(row["ddnnf_bytes"]) / float(row["core_robdd_serialized_bytes"]) for row in selected), f"d-DNNF/BDD k={k}")
        close(published["ddnnf_over_cm_bytes_geomean"],
              geomean(float(row["ddnnf_bytes"]) / float(row["core_cm_serialized_bytes"]) for row in selected), f"d-DNNF/CM k={k}")

    arms = sorted({row["arm"] for row in rss_rows})
    require(arms == ["cm", "cnf", "cudd", "d4_count"], "unexpected RSS arms")
    for arm in arms:
        selected = [row for row in rss_rows if row["arm"] == arm]
        require(len(selected) == summary["rss"][arm]["n"] == 40, f"RSS stratum mismatch: {arm}")
        require(all(row["relation_equal"] == "True" for row in selected), f"RSS equality flag false: {arm}")
        close(summary["rss"][arm]["peak_rss_bytes_median"],
              statistics.median(int(float(row["peak_rss_bytes"])) for row in selected), f"RSS median {arm}")

    audit = {
        "schema_version": "cm-fm-shootout-supplement-audit/v1",
        "status": "passed",
        "checksum_files_verified_before_audit_output": checksum_count,
        "relation_counts_reconstructed": relation_counts,
        "ddnnf_artifacts_rehashed": ddnnf_artifacts,
        "timing_sample_medians_recomputed": len(rows) * 4,
        "aggregate_width_strata_recomputed": len(WIDTHS),
        "rss_rows_rechecked": len(rss_rows),
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
