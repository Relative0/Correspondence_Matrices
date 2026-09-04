"""Verify a completed incremental-revision local gate from saved artifacts."""

from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import incremental_revision as experiment  # noqa: E402


DEFAULT_RUN = ROOT / "docs" / "research" / "verification" / "incremental-revision-local-gate-retry-003-2026-09-04"


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strict_json(raw: str) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ValueError(f"non-finite JSON value: {value}")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def verify_checksums(run: Path) -> int:
    checksum_path = run / "CHECKSUMS.sha256"
    records = {}
    for line in checksum_path.read_text(encoding="ascii").splitlines():
        digest, name = line.split("  ", 1)
        if name in records or "/" in name or "\\" in name:
            raise ValueError("invalid or duplicate checksum entry")
        records[name] = digest
    actual = {path.name for path in run.iterdir() if path.is_file() and path.name != checksum_path.name}
    if set(records) != actual:
        raise ValueError("checksum inventory does not match run files")
    for name, expected in records.items():
        if file_sha(run / name) != expected:
            raise ValueError(f"checksum mismatch: {name}")
    return len(records)


@lru_cache(maxsize=3)
def _patterns(k: int) -> tuple[int, ...]:
    width = 1 << k
    return tuple(
        sum(1 << assignment for assignment in range(width) if (assignment >> index) & 1)
        for index in range(k)
    )


def raw_cnf_bits(clauses: Iterable[Iterable[int]], k: int) -> int:
    """Packed evaluator over the unnormalized stored CNF."""
    width = 1 << k
    full = (1 << width) - 1
    result = full
    for source_clause in clauses:
        clause_bits = 0
        for source_literal in source_clause:
            literal = int(source_literal)
            if literal == 0 or abs(literal) > k:
                raise ValueError("invalid stored literal")
            value = _patterns(k)[abs(literal) - 1]
            clause_bits |= value if literal > 0 else full ^ value
        result &= clause_bits
    return result


def _normalize(clauses: Iterable[Iterable[int]], k: int) -> tuple[tuple[int, ...], ...]:
    result = set()
    for source_clause in clauses:
        literals = {int(literal) for literal in source_clause}
        if 0 in literals or any(abs(literal) > k for literal in literals):
            raise ValueError("invalid stored literal")
        if any(-literal in literals for literal in literals):
            continue
        clause = tuple(sorted(literals, key=lambda literal: (abs(literal), literal < 0)))
        if not clause:
            return ((),)
        result.add(clause)
    return tuple(sorted(result, key=lambda clause: (len(clause), clause)))


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def refresh_inventory(run: Path) -> None:
    artifacts = sorted(
        path for path in run.iterdir()
        if path.is_file() and path.name not in {"INVENTORY.json", "CHECKSUMS.sha256"}
    )
    _write_json(
        run / "INVENTORY.json",
        {
            "schema": "cm-incremental-revision-local-gate-inventory/v1",
            "files": [
                {"path": path.name, "bytes": path.stat().st_size, "sha256": file_sha(path)}
                for path in artifacts
            ],
        },
    )
    checksummed = sorted(path for path in run.iterdir() if path.is_file() and path.name != "CHECKSUMS.sha256")
    (run / "CHECKSUMS.sha256").write_text(
        "".join(f"{file_sha(path)}  {path.name}\n" for path in checksummed),
        encoding="ascii",
        newline="\n",
    )


def verify(run: Path) -> dict[str, Any]:
    checksum_files = verify_checksums(run)
    manifest = strict_json((run / "MANIFEST.json").read_text(encoding="utf-8"))
    plan = strict_json((run / "PLAN.json").read_text(encoding="utf-8"))
    saved_summary = strict_json((run / "SUMMARY.json").read_text(encoding="utf-8"))
    if manifest["status"] != "completed" or not manifest["full_frozen_matrix"]:
        raise ValueError("run manifest is not a completed frozen matrix")
    if manifest["cases_sha256"] != experiment.CASES_SHA256 or manifest["admissions_sha256"] != experiment.ADMISSIONS_SHA256:
        raise ValueError("run manifest input identity changed")

    cases = experiment.load_cases()
    case_by_id = {case["case_id"]: case for case in cases}
    if plan["case_ids"] != [case["case_id"] for case in cases] or plan["output_selected"]:
        raise ValueError("saved plan is not the frozen non-output-selected case order")

    rows = [strict_json(line) for line in (run / "RAW.jsonl").read_text(encoding="utf-8").splitlines()]
    expected_count = len(cases) * len(experiment.ARMS) * int(manifest["rounds"])
    if len(rows) != expected_count:
        raise ValueError("raw row count is incomplete")
    keys = {(row["case_id"], row["arm"], int(row["round"])) for row in rows}
    if len(keys) != expected_count:
        raise ValueError("duplicate case/arm/round row")

    oracle_by_case = {}
    normalized_change_by_case = {}
    for case in cases:
        k = int(case["k"])
        earlier = raw_cnf_bits(case["earlier_residual"], k)
        later = raw_cnf_bits(case["later_residual"], k)
        oracle = (
            experiment.packed_sha(earlier, k),
            experiment.packed_sha(later, k),
            experiment.packed_sha(earlier ^ later, k),
            (earlier ^ later).bit_count(),
        )
        saved = (
            case["earlier_packed_sha256"],
            case["later_packed_sha256"],
            case["changed_packed_sha256"],
        )
        if oracle[:3] != saved:
            raise AssertionError(f"raw-CNF oracle mismatch: {case['case_id']}")
        oracle_by_case[case["case_id"]] = oracle
        normalized_change_by_case[case["case_id"]] = _normalize(case["earlier_residual"], k) != _normalize(case["later_residual"], k)

    for row in rows:
        case_id = row["case_id"]
        if case_id not in case_by_id or row["arm"] not in experiment.ARMS or not row["exact"]:
            raise ValueError("raw row identity or exactness is invalid")
        expected = oracle_by_case[case_id]
        actual = (
            row["earlier_packed_sha256"],
            row["later_packed_sha256"],
            row["changed_packed_sha256"],
            int(row["changed_assignments"]),
        )
        if actual != expected:
            raise AssertionError(f"saved row artifact mismatch: {case_id} {row['arm']}")
        if bool(row["invalidation_identity_changed"]) != normalized_change_by_case[case_id]:
            raise AssertionError(f"invalidation identity mismatch: {case_id} {row['arm']}")
        if normalized_change_by_case[case_id] and not bool(row["program_identity_changed"]):
            raise AssertionError(f"stale program identity: {case_id} {row['arm']}")
        for name in (
            "earlier_construction_ns",
            "update_construction_ns",
            "resident_pair_construction_ns",
            "evaluation_batch_ns",
            "retained_python_bytes",
        ):
            if float(row[name]) <= 0:
                raise ValueError(f"nonpositive measurement: {case_id} {row['arm']} {name}")

    recomputed_summary = experiment.summarize(rows)
    if recomputed_summary != saved_summary:
        raise AssertionError("summary does not reproduce from strict raw rows")
    gates = saved_summary["gates"]
    if gates["promotion"] or not gates["correctness"] or not gates["update_construction_advantage"]:
        raise AssertionError("saved gate decision is inconsistent with the retained result")
    return {
        "schema": "cm-incremental-revision-independent-verification/v1",
        "status": "passed",
        "checksum_files_verified": checksum_files,
        "raw_rows_verified": len(rows),
        "unique_cells_verified": len(keys),
        "cases_replayed_from_unnormalized_cnf": len(oracle_by_case),
        "saved_artifact_hashes_checked_per_case": 3,
        "summary_reproduced": True,
        "promotion_gate_reproduced": False,
        "correctness_mismatches": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    run = args.run.resolve()
    report_path = run / "INDEPENDENT_VERIFICATION.json"
    if args.write and report_path.exists():
        raise SystemExit(f"refusing to overwrite existing verification: {report_path}")
    report = verify(run)
    if args.write:
        _write_json(report_path, report)
        refresh_inventory(run)
        report = verify(run)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
