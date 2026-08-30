import json
from pathlib import Path

import pytest

from scripts.cm_memory_boundary_analysis import analyze, classify, load_rows, write_outputs


def _row(*, peak=100, legacy=80, candidate=120, repetition=0):
    return {
        "status": "ok",
        "comparison_eligible": True,
        "case_id": "case-a",
        "role": "heldout",
        "family": "fixture",
        "schedule": "cold",
        "representation": "dense",
        "repetition": repetition,
        "window": "evaluation",
        "tracemalloc_peak_bytes": peak,
        "legacy_estimate": legacy,
        "candidate": {"temporary_bytes": candidate},
    }


def test_inclusive_boundary_semantics():
    assert classify(100, 100, 99) == {
        "status": "refused", "observed_fits": False,
        "false_admission": False, "false_refusal": False,
    }
    assert classify(100, 100, 100) == {
        "status": "admitted", "observed_fits": True,
        "false_admission": False, "false_refusal": False,
    }
    assert classify(100, 101, 100)["false_admission"] is True
    assert classify(101, 100, 100)["false_refusal"] is True


def test_analysis_records_error_intervals_and_limit_neighbors():
    summary, boundaries, fixed = analyze([_row()], "a" * 64)
    assert summary["eligible_comparable_rows"] == 1
    by_model = {row["model"]: row for row in boundaries}
    assert by_model["candidate"]["error_limit_interval_inclusive"] == [100, 119]
    assert by_model["candidate"]["checks"]["estimate-1"]["false_refusal"] is True
    assert by_model["candidate"]["checks"]["estimate+0"]["false_admission"] is False
    assert by_model["legacy"]["error_limit_interval_inclusive"] == [80, 99]
    assert by_model["legacy"]["checks"]["estimate-1"]["false_refusal"] is False
    assert by_model["legacy"]["checks"]["estimate+0"]["false_admission"] is True
    assert len(fixed) == 6


def test_analysis_ignores_noncomparable_rows_and_rejects_duplicate_identity():
    ignored = {**_row(), "comparison_eligible": False}
    summary, _, _ = analyze([ignored, _row()], "b" * 64)
    assert summary["eligible_comparable_rows"] == 1
    with pytest.raises(ValueError, match="duplicate comparable"):
        analyze([_row(), _row()], "c" * 64)


@pytest.mark.parametrize("field,value", [
    ("tracemalloc_peak_bytes", True),
    ("legacy_estimate", -1),
])
def test_analysis_rejects_invalid_measurements(field, value):
    row = _row()
    row[field] = value
    with pytest.raises(ValueError, match="non-negative integer"):
        analyze([row], "d" * 64)


def test_load_rows_hashes_exact_bytes_and_rejects_bad_json(tmp_path: Path):
    source = tmp_path / "raw.jsonl"
    source.write_text(json.dumps(_row()) + "\n", encoding="utf-8", newline="\n")
    rows, digest = load_rows(source)
    assert rows == [_row()]
    assert len(digest) == 64
    source.write_text("{\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_rows(source)


def test_write_outputs_refuses_existing_directory(tmp_path: Path):
    summary, boundaries, fixed = analyze([_row()], "e" * 64)
    output = tmp_path / "result"
    write_outputs(output, summary, boundaries, fixed)
    assert json.loads((output / "summary.json").read_text())["production_estimator_accepted"] is False
    with pytest.raises(FileExistsError):
        write_outputs(output, summary, boundaries, fixed)
