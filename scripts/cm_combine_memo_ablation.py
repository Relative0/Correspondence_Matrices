#!/usr/bin/env python3
"""Combine disjoint outputs from ``cm_prepare_memo_ablation.py`` safely."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.cm_prepare_memo_ablation import _summaries


NUMERIC_FIELDS = {
    "live_k": int,
    "repetitions": int,
    "baseline_ns_median": float,
    "candidate_ns_median": float,
    "ratio": float,
    "baseline_ns_p10": float,
    "baseline_ns_p90": float,
    "candidate_ns_p10": float,
    "candidate_ns_p90": float,
    "baseline_peak_bytes": float,
    "candidate_peak_bytes": float,
    "peak_bytes_ratio": float,
}
BOOLEAN_FIELDS = ("canonical_key_equal", "packed_output_equal")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _optional_number(value: str, convert: type[int] | type[float]) -> int | float | None:
    return None if value == "" else convert(value)


def _boolean(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"invalid Boolean CSV value: {value!r}")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty input: {path}")
    for row in rows:
        for field, convert in NUMERIC_FIELDS.items():
            if field not in row:
                raise ValueError(f"{path}: missing field {field!r}")
            row[field] = _optional_number(row[field], convert)
        for field in BOOLEAN_FIELDS:
            if field not in row:
                raise ValueError(f"{path}: missing field {field!r}")
            row[field] = _boolean(row[field])
    return rows


def combine(inputs: list[Path], expected_rows: int | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    sources = []
    for path in inputs:
        chunk = _read_rows(path)
        rows.extend(chunk)
        sources.append({"path": str(path), "rows": len(chunk), "sha256": _sha256(path)})

    ids = [str(row["id"]) for row in rows]
    duplicates = sorted({identifier for identifier in ids if ids.count(identifier) > 1})
    if duplicates:
        raise ValueError(f"duplicate record ids: {duplicates[:10]}")
    if expected_rows is not None and len(rows) != expected_rows:
        raise ValueError(f"expected {expected_rows} rows, found {len(rows)}")

    repetitions = sorted({int(row["repetitions"]) for row in rows})
    if len(repetitions) != 1:
        raise ValueError(f"mixed repetition counts: {repetitions}")
    return {
        "aggregation": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "method": (
                "geometric mean of per-record candidate/baseline median ratios; "
                "95% percentile interval from the benchmark's deterministic "
                "cluster bootstrap"
            ),
            "rows": len(rows),
            "repetitions_per_record": repetitions[0],
            "inputs": sources,
        },
        "summaries": _summaries(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--expected-rows", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"refusing to overwrite existing output: {args.output}")
    if len({path.resolve() for path in args.input}) != len(args.input):
        parser.error("duplicate input path")
    missing = [str(path) for path in args.input if not path.is_file()]
    if missing:
        parser.error("missing inputs: " + ", ".join(missing))

    result = combine(args.input, args.expected_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["summaries"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
