"""Independently verify and reaggregate an EPFL context-pilot run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def geomean(values) -> float:
    values = [float(value) for value in values]
    if not values or any(value <= 0 or not math.isfinite(value) for value in values):
        raise ValueError("invalid geomean input")
    return math.exp(statistics.fmean(math.log(value) for value in values))


def close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
        raise AssertionError(f"{label}: {actual} != {expected}")


def audit(run_dir: Path) -> dict:
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    checksums = {}
    for line in (run_dir / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        checksums[name] = digest
    for name, expected in checksums.items():
        actual = sha256_file(run_dir / name)
        if actual != expected:
            raise AssertionError(f"checksum mismatch for {name}")

    with (run_dir / "raw.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != int(summary["correctness"]["context_rows"]):
        raise AssertionError("raw row count mismatch")
    if any(row["packed_equal"].lower() != "true" for row in rows):
        raise AssertionError("packed mismatch row present")
    if len({row["id"] for row in rows}) != int(summary["corpus"]["admitted_records_used"]):
        raise AssertionError("formula count mismatch")

    ratios = [float(row["cm_over_cse_flat"]) for row in rows]
    close(geomean(ratios), float(summary["row_weighted"]["geomean"]), "row geomean")
    close(statistics.median(ratios), float(summary["row_weighted"]["median"]), "row median")

    def circuit_geomean(subset):
        grouped = defaultdict(list)
        for row in subset:
            grouped[row["circuit"]].append(float(row["cm_over_cse_flat"]))
        return geomean(geomean(values) for values in grouped.values()), len(grouped)

    primary, circuit_count = circuit_geomean(rows)
    close(primary, float(summary["primary_circuit_clustered"]["geomean"]), "primary circuit geomean")
    if circuit_count != int(summary["primary_circuit_clustered"]["circuit_count"]):
        raise AssertionError("circuit count mismatch")
    for fraction, expected in summary["by_fixed_fraction_circuit_clustered"].items():
        subset = [row for row in rows if math.isclose(float(row["fixed_fraction"]), float(fraction))]
        actual, count = circuit_geomean(subset)
        close(actual, float(expected["geomean"]), f"fraction {fraction}")
        if count != int(expected["circuit_count"]):
            raise AssertionError(f"fraction circuit count mismatch: {fraction}")

    construction_rows = summary["family_compile_rows"]
    if construction_rows and "cm_fresh_compile_ns" in construction_rows[0]:
        construction = summary["construction_descriptive"]
        close(geomean(row["compile_ns"] for row in construction_rows), float(construction["cm_family_compile_ns_geomean"]), "family compile geomean")
        close(geomean(row["cm_fresh_compile_ns"] for row in construction_rows), float(construction["cm_fresh_compile_ns_geomean"]), "fresh CM compile geomean")
        close(geomean(row["cse_flat_compile_ns"] for row in construction_rows), float(construction["cse_flat_compile_ns_geomean"]), "CSE compile geomean")

    return {
        "status": "pass",
        "run_dir": str(run_dir.resolve()),
        "raw_rows": len(rows),
        "formulas": len({row["id"] for row in rows}),
        "circuits": circuit_count,
        "packed_mismatches": 0,
        "primary_geomean": primary,
        "checksums_verified": sorted(checksums),
        "construction_raw_reaggregated": bool(construction_rows and "cm_fresh_compile_ns" in construction_rows[0]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.run_dir), indent=2))


if __name__ == "__main__":
    main()
