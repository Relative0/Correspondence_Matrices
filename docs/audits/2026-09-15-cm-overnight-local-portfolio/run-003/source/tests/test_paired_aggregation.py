import math

from cmbench.results.paired import PairedComparisonSpec, aggregate_paired_comparison


def test_complete_paired_aggregation_reports_both_ratio_definitions():
    rows = [
        {"a": 1.0, "b": 1.0},
        {"a": 100.0, "b": 10.0},
        {"a": 101.0, "b": 100.0},
    ]
    result = aggregate_paired_comparison(rows, PairedComparisonSpec("a", "b"))
    assert result["attempted"] == 3
    assert result["paired_success"] == 3
    assert result["pairing_complete"] is True
    assert result["ratio_of_medians"] == 10.0
    assert result["median_of_paired_ratios"] == 1.01
    assert result["headline_ratio_available"] is True


def test_asymmetric_failures_never_create_independent_survivor_headline():
    rows = [
        {"a": 1.0, "b": 1.0, "as": "success", "bs": "success"},
        {"a": 2.0, "b": None, "as": "success", "bs": "timeout"},
        {"a": None, "b": 3.0, "as": "oom", "bs": "success"},
        {"a": None, "b": 4.0, "as": "refused", "bs": "success"},
        {"a": 5.0, "b": None, "as": "success", "bs": "error"},
        {"a": None, "b": 6.0, "as": "declined", "bs": "success"},
    ]
    spec = PairedComparisonSpec("a", "b", "as", "bs")
    result = aggregate_paired_comparison(rows, spec)
    assert result["paired_success"] == 1
    assert result["left_oom"] == 1
    assert result["left_refused"] == 1
    assert result["left_declined"] == 1
    assert result["right_timeout"] == 1
    assert result["right_error"] == 1
    assert result["pairing_complete"] is False
    assert result["headline_ratio"] is None


def test_zero_nan_and_missing_denominators_are_not_successes():
    rows = [
        {"a": 1.0, "b": 0.0},
        {"a": 1.0, "b": math.nan},
        {"a": None, "b": 1.0},
    ]
    result = aggregate_paired_comparison(rows, PairedComparisonSpec("a", "b"))
    assert result["paired_success"] == 0
    assert result["right_missing"] == 2
    assert result["left_missing"] == 1
    assert result["ratio_of_medians"] is None


def test_artifact_or_timing_mismatch_is_rejected():
    rows = [
        {"a": 1.0, "b": 2.0, "aa": "packed", "ba": "symbolic", "at": "execute", "bt": "build"},
        {"a": 2.0, "b": 4.0, "aa": "packed", "ba": "packed", "at": "execute", "bt": "execute"},
    ]
    spec = PairedComparisonSpec(
        "a", "b", left_artifact="aa", right_artifact="ba", left_timing="at", right_timing="bt"
    )
    result = aggregate_paired_comparison(rows, spec)
    assert result["incompatible_pairs"] == 1
    assert result["paired_success"] == 1
    assert result["pairing_complete"] is False
    assert result["headline_ratio"] is None


def test_explicit_override_labels_incomplete_headline():
    rows = [{"a": 2.0, "b": 1.0}, {"a": None, "b": 1.0}]
    result = aggregate_paired_comparison(
        rows, PairedComparisonSpec("a", "b", allow_incomplete_headline=True)
    )
    assert result["pairing_complete"] is False
    assert result["headline_ratio_available"] is True
    assert result["headline_ratio"] == 2.0
