from __future__ import annotations

import pytest

from cmbench.recognition.gf2_compiled_policy_tail_experiment import (
    C20Config,
    METHODS,
    summarize,
)


def rows(compiled_case_b: int = 95):
    costs = {
        "case-a": {"direct_exhaustive": 100, "direct_screened": 50,
                   "generic_c19": 55, "compiled_c19": 51},
        "case-b": {"direct_exhaustive": 100, "direct_screened": 90,
                   "generic_c19": 98, "compiled_c19": compiled_case_b},
    }
    return [
        {"case_id": case, "method": method, "round": round_index, "total_ns": cost}
        for case, methods in costs.items()
        for method, cost in methods.items()
        for round_index in range(5)
    ]


def test_summary_uses_per_case_medians_and_predeclared_tail_gate():
    summary = summarize(rows(), {"all_exact": True})
    compiled = summary["methods"]["compiled_c19"]
    assert compiled["aggregate_speedup_over_exhaustive"] == pytest.approx(200 / 146)
    assert compiled["minimum_case_speedup_over_exhaustive"] == pytest.approx(100 / 95)
    assert summary["research_gate"] is True


def test_summary_rejects_a_slow_compiled_tail():
    summary = summarize(rows(compiled_case_b=105), {"all_exact": True})
    assert summary["methods"]["compiled_c19"]["minimum_case_speedup_over_exhaustive"] < 0.97
    assert summary["research_gate"] is False


def test_config_and_method_contract_are_bounded():
    C20Config("run").validate()
    assert METHODS == ("direct_exhaustive", "direct_screened", "generic_c19", "compiled_c19")
    with pytest.raises(ValueError):
        C20Config("run", rounds=4).validate()

