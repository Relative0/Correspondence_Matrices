from scripts.cm_corpus_memory_result_analysis import _boundary, distribution


def _row(candidate: int, legacy: int, peak: int, case_id: str = "case") -> dict:
    return {
        "case_id": case_id,
        "k": 6,
        "representation": "dense",
        "schedule": "cold",
        "candidate": {"temporary_bytes": candidate},
        "legacy_estimate": legacy,
        "tracemalloc_peak_bytes": peak,
    }


def test_distribution_uses_declared_nearest_rank_percentile():
    assert distribution([1, 2, 3, 100]) == {
        "count": 4,
        "min": 1,
        "median": 2.5,
        "p95_nearest_rank": 100,
        "max": 100,
    }


def test_boundary_is_inclusive_and_records_false_refusal_identity():
    result = _boundary([
        _row(candidate=10, legacy=4, peak=5, case_id="at-limit"),
        _row(candidate=11, legacy=4, peak=5, case_id="above-limit"),
        _row(candidate=4, legacy=4, peak=11, case_id="unsafe"),
    ], "candidate", 10)

    assert result["correct_admission"] == 1
    assert result["false_refusal"] == 1
    assert result["false_admission"] == 1
    assert result["correct_refusal"] == 0
    assert result["error_groups"]["false_refusal"] == [{
        "case_id": "above-limit",
        "k": 6,
        "representation": "dense",
        "schedule": "cold",
        "rows": 1,
    }]
