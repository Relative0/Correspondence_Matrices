from __future__ import annotations

import pytest

from cmbench.comparative.gf2_fresh_table_experiment import C23Config, fresh_summary
from cmbench.comparative.gf2_method_table import METHODS, TIMING_FIELDS


def make_rows():
    rows = []
    for case, baseline in (("a", 50), ("b", 100)):
        for index, method in enumerate(METHODS):
            total = baseline + index
            if method == "cm_exhaustive":
                total = 100
            elif method == "cm_screened":
                total = 50
            stages = {field: 0 for field in TIMING_FIELDS}
            stages["completion_ns"] = total
            stages["task_total_ns"] = total
            for round_index in range(3):
                rows.append({"case_id": case, "method": method, "round": round_index,
                             "timings_ns": stages,
                             "proposal": {"status": "not_applicable"},
                             "exact_check_passed": True})
    return rows


def test_c23_config_preserves_c21_exact_bounds():
    config = C23Config("run")
    config.validate()
    oracle = config.oracle_config()
    oracle.validate()
    assert oracle.max_partitions == 64
    assert oracle.materialize_budget == 4
    with pytest.raises(ValueError):
        C23Config("run", rounds=2).validate()


def test_fresh_summary_removes_retrospective_label():
    summary = fresh_summary(make_rows(), [], {"all_exact": True})
    assert summary["timing_is_fresh_and_machine_specific"] is True
    assert "timing_is_retrospective_and_machine_specific" not in summary
