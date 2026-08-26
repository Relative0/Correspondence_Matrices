from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.cm_combine_memo_ablation import combine


FIELDS = [
    "corpus",
    "role",
    "id",
    "cluster",
    "live_k",
    "repetitions",
    "baseline_ns_median",
    "candidate_ns_median",
    "ratio",
    "baseline_ns_p10",
    "baseline_ns_p90",
    "candidate_ns_p10",
    "candidate_ns_p90",
    "baseline_peak_bytes",
    "candidate_peak_bytes",
    "peak_bytes_ratio",
    "canonical_key_equal",
    "packed_output_equal",
    "packed_sha256",
]


def _write(path: Path, identifier: str, ratio: float) -> None:
    row = {
        "corpus": "epfl",
        "role": "validation_reused",
        "id": identifier,
        "cluster": f"epfl:circuit:{identifier}",
        "live_k": 8,
        "repetitions": 5,
        "baseline_ns_median": 100,
        "candidate_ns_median": 100 * ratio,
        "ratio": ratio,
        "baseline_ns_p10": 90,
        "baseline_ns_p90": 110,
        "candidate_ns_p10": 90 * ratio,
        "candidate_ns_p90": 110 * ratio,
        "baseline_peak_bytes": "",
        "candidate_peak_bytes": "",
        "peak_bytes_ratio": "",
        "canonical_key_equal": True,
        "packed_output_equal": True,
        "packed_sha256": "0" * 64,
    }
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(row)


def test_combine_disjoint_rows(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    _write(first, "a", 0.8)
    _write(second, "b", 1.0)

    result = combine([first, second], expected_rows=2)

    assert result["aggregation"]["rows"] == 2
    assert result["summaries"][0]["candidate_over_baseline_geomean"] == pytest.approx(
        0.8**0.5
    )
    assert result["summaries"][0]["canonical_mismatches"] == 0


def test_combine_rejects_duplicate_record_ids(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    _write(first, "same", 0.8)
    _write(second, "same", 0.9)

    with pytest.raises(ValueError, match="duplicate record ids"):
        combine([first, second])
