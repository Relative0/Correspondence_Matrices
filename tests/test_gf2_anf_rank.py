from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest

from cmbench.comparative.gf2_anf_rank_experiment import (
    METHODS,
    ANFRankConfig,
    build_schedule,
    execute_session,
    prepare_c16_cases,
    summarize,
    validate_schedule,
)

from cmbench.recognition.gf2_anf_rank import (
    anf_rank,
    anf_rank_factor_to_truth,
    normalize_source_anf,
    packed_anf_from_truth,
    truth_partition_rows,
)
from cmbench.recognition.gf2_decomposition import gf2_rank_factor
from cmbench.recognition.gf2_decomposition import analyze_screened_exact_gf2
from cmbench.recognition.gf2_anf_screened import analyze_screened_exact_gf2_anf_rank
from cmbench.recognition.gf2_bounded_rank import (
    analyze_screened_exact_gf2_bounded_rank,
    gf2_rank_factor_bounded,
)
from cmbench.recognition.source_anf_hybrid import packed_truth_bits


ROOT = Path(__file__).resolve().parents[1]


def _partitions(n_vars: int):
    return tuple(
        row for size in range(1, n_vars)
        for row in itertools.combinations(range(n_vars), size)
        if 0 in row
    )


def test_anf_rank_and_factor_conversion_for_structured_truths():
    truths = (0, 1, 0x6996, 0x8000, 0xFFFF, 0xA55A, 0xF888)
    for bits in truths:
        polynomial = packed_anf_from_truth(bits, 4)
        for row in _partitions(4):
            factor = anf_rank_factor_to_truth(
                polynomial, 4, row, expected_truth_bits=bits)
            expected = gf2_rank_factor(truth_partition_rows(bits, 4, row),
                                       factor.matrix_shape[1])[0]
            assert factor.rank == expected


def test_source_anf_index_normalization_round_trips_truth():
    # x0*x2 xor x1 xor 1 in source variable-mask indexing.
    source = (1 << 0) | (1 << (1 << 1)) | (1 << ((1 << 0) | (1 << 2)))
    natural = normalize_source_anf(source, 3)
    truth = packed_truth_bits(source, 3)
    assert natural == packed_anf_from_truth(truth, 3)


def test_exhaustive_three_variable_rank_invariant_and_reconstruction():
    for bits in range(1 << (1 << 3)):
        polynomial = packed_anf_from_truth(bits, 3)
        for row in _partitions(3):
            factor = anf_rank_factor_to_truth(
                polynomial, 3, row, expected_truth_bits=bits)
            assert factor.rank == anf_rank(polynomial, 3, row)


def test_anf_rank_experiment_sessions_share_rank_artifact_and_schedule_is_balanced():
    dataset = json.loads((
        ROOT / "docs/recognition/c16_linux_confirmation/c16_dataset.json"
    ).read_text(encoding="utf-8"))
    cases = prepare_c16_cases({**dataset, "cases": dataset["cases"]})[:2]
    config = ANFRankConfig(run_id="test")
    config.validate()
    schedule = build_schedule(cases, config.blocks, config.seed)
    validate_schedule(schedule, cases, config.blocks)
    changed = json.loads(json.dumps(schedule))
    changed[0]["order_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        validate_schedule(changed, cases, config.blocks)
    sessions = [execute_session(case=cases[0], method=method, role="performance")
                for method in METHODS]
    assert len({session["artifact_sha256"] for session in sessions}) == 1


def test_anf_rank_summary_keeps_production_gate_closed():
    rows = []
    for case_index, case_id in enumerate(("a", "b")):
        for block in range(4):
            for method in METHODS:
                rows.append({
                    "role": "performance", "case_id": case_id,
                    "n_vars": 8 + case_index, "method": method,
                    "timings_ns": {"accounted_total_ns": (
                        50 if method == "anf_rank_screen_from_truth" else 100)},
                })
        for method in METHODS:
            rows.append({
                "role": "memory_profile", "case_id": case_id,
                "n_vars": 8 + case_index, "method": method,
                "resources": {"session_sampled_peak_rss_delta_bytes": 1,
                              "tracemalloc_peak_bytes": 2},
            })
    summary = summarize(rows, 1.10)
    assert summary["decision"]["complete_from_truth_gate_passed"] is True
    assert summary["decision"]["production_integration_permitted"] is False


def test_anf_rank_full_screen_is_byte_identical_on_c16():
    dataset = json.loads((
        ROOT / "docs/recognition/c16_linux_confirmation/c16_dataset.json"
    ).read_text(encoding="utf-8"))
    for case in prepare_c16_cases(dataset):
        baseline = analyze_screened_exact_gf2(
            case["bits"], case["n_vars"], max_partitions=64,
            materialize_budget=4)
        candidate = analyze_screened_exact_gf2_anf_rank(
            case["bits"], case["n_vars"], max_partitions=64,
            materialize_budget=4, polynomial=case["polynomial"])
        assert [artifact.to_dict() for artifact in candidate.candidates] == [
            artifact.to_dict() for artifact in baseline.candidates]
        assert (candidate.best.to_dict() if candidate.best else None) == (
            baseline.best.to_dict() if baseline.best else None)


def test_bounded_rank_stops_on_constructed_full_rank_matrix():
    rows = tuple(1 << index for index in range(8))
    result = gf2_rank_factor_bounded(rows, 8, noncompressing_rank=4)
    assert result.pruned is True
    assert result.rows_scanned == 4
    assert result.rank_lower_bound == 4


def test_bounded_rank_full_screen_is_byte_identical_and_prunes_c16_work():
    dataset = json.loads((
        ROOT / "docs/recognition/c16_linux_confirmation/c16_dataset.json"
    ).read_text(encoding="utf-8"))
    total_pruned = 0
    for case in prepare_c16_cases(dataset):
        baseline = analyze_screened_exact_gf2(
            case["bits"], case["n_vars"], max_partitions=64,
            materialize_budget=4)
        candidate, metrics = analyze_screened_exact_gf2_bounded_rank(
            case["bits"], case["n_vars"], max_partitions=64,
            materialize_budget=4)
        assert [artifact.to_dict() for artifact in candidate.candidates] == [
            artifact.to_dict() for artifact in baseline.candidates]
        total_pruned += metrics["rank_rows_pruned"]
    assert total_pruned > 0
