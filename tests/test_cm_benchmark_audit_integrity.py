"""Regression tests for the corrected CM benchmark audit boundaries."""

from __future__ import annotations

import hashlib
import json
import math

import pytest

from bitset_backend import eval_expr_words_bitset
from cm_expr_serde import expr_from_json
from scripts import cm_deep_performance_audit as audit
from scripts import cm_symmetric_wrapper_followup as symmetric
from cmbench.reporting.provenance import sha256_file as shared_sha256_file
from scripts import cm_benchmark_provenance
from scripts.cm_benchmark_provenance import capture_source_snapshot, sha256_file


def test_sha256_file_is_streaming_shared_provenance_helper(tmp_path) -> None:
    payload = (b"cm-provenance\x00" * 100_000) + b"tail"
    path = tmp_path / "multi-chunk.bin"
    path.write_bytes(payload)

    assert shared_sha256_file(path) == hashlib.sha256(payload).hexdigest()
    assert cm_benchmark_provenance.sha256_file is shared_sha256_file
    with pytest.raises(ValueError, match="positive integer"):
        shared_sha256_file(path, chunk_size=0)


def test_epfl_context_matches_frozen_truth_digest() -> None:
    record = next(iter(audit._records("epfl")))
    expr = expr_from_json(record["expression_v2"])
    live_k = int(record["sem_support_size"])
    variables, fixed = audit._evaluation_context("epfl", record, expr, live_k)

    assert variables == tuple(f"x{i}" for i in range(live_k - 1, -1, -1))
    packed = eval_expr_words_bitset(expr, variables, fixed=fixed)
    assert (
        audit._verify_frozen_truth("epfl", record, expr, packed, live_k)
        == record["truth_sha256"]
    )


def test_epfl_dead_syntactic_input_still_verifies_frozen_width() -> None:
    record = min(
        (
            row
            for row in audit._records("epfl")
            if int(row["synt_support_size"]) > int(row["sem_support_size"])
        ),
        key=lambda row: len(row["expression_v2"]["nodes"]),
    )
    expr = expr_from_json(record["expression_v2"])
    live_k = int(record["sem_support_size"])
    variables, fixed = audit._evaluation_context("epfl", record, expr, live_k)
    packed = eval_expr_words_bitset(expr, variables, fixed=fixed)
    assert (
        audit._verify_frozen_truth("epfl", record, expr, packed, live_k)
        == record["truth_sha256"]
    )


def test_truth_digest_mismatch_is_fail_closed() -> None:
    record = {"id": "tampered", "truth_sha256": "0" * 64}
    with pytest.raises(AssertionError, match="truth drift"):
        audit._require_truth_digest(record, 1, 3)


def test_symmetric_primary_includes_strong_cse_flat_arm() -> None:
    record = symmetric._records(symmetric.B2)[0]
    row = symmetric._measure(
        "b2", record, int(record["stratum_live_k"]), rounds=3
    )
    assert row["packed_equal_all_arms"] is True
    assert row["packed_sha256"] == row["truth_sha256_expected"]
    assert row["truth_sha256_expected"] == record["truth_sha256"]
    assert row["cm_current_over_cse_flat_current"] > 0
    assert row["cse_flat_current_ns_median"] > 0
    assert row["cm_instructions"] > 0
    assert row["cse_flat_instructions"] > 0


def test_source_snapshot_is_exact_and_refuses_overwrite(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "driver.py").write_text("print('exact')\n", encoding="utf-8")
    destination = tmp_path / "snapshot"

    result = capture_source_snapshot(root, destination, ("driver.py",))
    manifest = json.loads((destination / "source_manifest.json").read_text())
    assert (destination / "driver.py").read_bytes() == (root / "driver.py").read_bytes()
    assert manifest["files"][0]["sha256"] == sha256_file(root / "driver.py")
    assert result["manifest_sha256"] == sha256_file(
        destination / "source_manifest.json"
    )
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        capture_source_snapshot(root, destination, ("driver.py",))


def test_source_snapshot_missing_input_leaves_no_partial_destination(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "present.py").write_text("present = True\n", encoding="utf-8")
    destination = tmp_path / "snapshot"

    with pytest.raises(FileNotFoundError):
        capture_source_snapshot(root, destination, ("present.py", "missing.py"))

    assert not destination.exists()


def test_paired_formula_cluster_bootstrap_is_deterministic_and_formula_weighted() -> None:
    rows = [
        {"corpus": "b4", "id": "formula-a", "ratio": 0.5},
        {"corpus": "b4", "id": "formula-a", "ratio": 2.0},
        {"corpus": "b4", "id": "formula-b", "ratio": 4.0},
    ]

    first = symmetric._paired_formula_cluster_stats(
        rows, "ratio", seed_label="unit-test", repetitions=2_000
    )
    second = symmetric._paired_formula_cluster_stats(
        rows, "ratio", seed_label="unit-test", repetitions=2_000
    )

    assert first == second
    assert first["row_count"] == 3
    assert first["formula_cluster_count"] == 2
    assert first["row_weighted_geomean"] == pytest.approx(4.0 ** (1.0 / 3.0))
    assert first["paired_formula_cluster_geomean"] == pytest.approx(2.0)
    assert first["paired_formula_cluster_bootstrap_ci95_low"] == pytest.approx(1.0)
    assert first["paired_formula_cluster_bootstrap_ci95_high"] == pytest.approx(4.0)


def test_paired_formula_cluster_bootstrap_rejects_invalid_ratios() -> None:
    rows = [{"corpus": "b2", "id": "bad", "ratio": math.inf}]
    with pytest.raises(ValueError, match="finite positive ratios"):
        symmetric._paired_formula_cluster_stats(
            rows, "ratio", seed_label="unit-test", repetitions=10
        )


def test_balanced_schedule_places_every_arm_equally_in_every_position() -> None:
    assert symmetric.BALANCED_ROUNDS_MULTIPLE == 24
    for arm_count in (4, 6):
        calls: list[str] = []
        functions = {
            f"arm-{index}": (lambda name=f"arm-{index}": calls.append(name) or 0)
            for index in range(arm_count)
        }
        rounds = 2 * arm_count

        symmetric._balanced(functions, batch=1, rounds=rounds)

        orders = [calls[start : start + arm_count] for start in range(0, len(calls), arm_count)]
        for name in functions:
            positions = [order.index(name) for order in orders]
            assert positions.count(0) == 2
            assert sorted(positions) == sorted(list(range(arm_count)) * 2)
