"""Independently verify the published W8 LogikBench confirmation freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = next(
    parent
    for parent in (HERE, *HERE.parents)
    if (parent / "cmbench").is_dir() and (parent / "docs").is_dir()
)
ROOT = (
    PROJECT_ROOT
    / "docs"
    / "research"
    / "verification"
    / "comparative-w8-logikbench-confirmation-v1-2026-08-31"
)


def load(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    failures = []
    freeze = load("freeze.json")
    logical = {key: value for key, value in freeze.items() if key != "freeze_sha256"}
    logical_hash = hashlib.sha256(
        json.dumps(logical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if logical_hash != freeze.get("freeze_sha256"):
        failures.append("logical freeze hash mismatch")

    checksums = load("checksums.json")
    expected_paths = {row["path"] for row in checksums.get("files") or []} | {"checksums.json"}
    actual_paths = {
        path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()
    }
    if actual_paths != expected_paths:
        failures.append("artifact path set mismatch")
    for row in checksums.get("files") or []:
        path = ROOT / Path(row["path"])
        if not path.is_file() or path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            failures.append(f"artifact identity mismatch: {row['path']}")

    selection = load("confirmation-selection.json")
    oracle = load("oracle-package.json")
    source_manifest = load("source-manifest.json")
    exclusions = load("selection-exclusions.json")
    cases = selection.get("cases") or []
    oracle_by_case = {row["case_id"]: row for row in oracle.get("rows") or []}
    sources_by_case = {row["case_id"]: row for row in source_manifest.get("files") or []}
    if len(cases) != len(oracle_by_case) or len(cases) != len(sources_by_case) or len(cases) != 30:
        failures.append("case/oracle/source cardinality mismatch")
    for case in cases:
        source = sources_by_case.get(case["case_id"])
        oracle_row = oracle_by_case.get(case["case_id"])
        if source is None or oracle_row is None:
            failures.append(f"missing bound row: {case['case_id']}")
            continue
        path = ROOT / source["path"]
        expected = case["source"]["sha256"]
        if (
            digest(path) != expected
            or source["sha256"] != expected
            or oracle_row["input_sha256"] != expected
            or oracle_row != case["oracle"]
            or source["cluster_id"] != case["cluster_id"]
        ):
            failures.append(f"case binding mismatch: {case['case_id']}")
    if (
        exclusions.get("terminal_inputs") != 64
        or exclusions.get("selected") != 30
        or exclusions.get("eligible_unselected") != 6
        or exclusions.get("rejected") != 28
    ):
        failures.append("selection ledger count mismatch")
    if (
        freeze.get("case_count") != 30
        or freeze.get("independent_cluster_count") != 30
        or freeze.get("performance_measurement") is not False
        or freeze.get("use_boundary", {}).get("development_timing") != "prohibited"
    ):
        failures.append("freeze boundary mismatch")

    result = {
        "schema": "cm-comparative-w8-logikbench-confirmation-independent-verification/v1",
        "verified": not failures,
        "failures": failures,
        "freeze_sha256": logical_hash,
        "artifact_files": len(actual_paths),
        "cases": len(cases),
        "source_files": len(sources_by_case),
        "oracle_rows": len(oracle_by_case),
        "performance_measurement": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
