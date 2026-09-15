"""Frozen-summary algebra and reproducibility checks; no new timings."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("cm_ladder_summary_tested", HERE / "summarize_ladder.py")
summary_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(summary_module)


def test_exclusive_phase_weighting_uses_total_not_mean_of_percentages():
    passes = [
        {"total": {"wall_s": 10., "cpu_s": 0.}, "exclusive_phases": {
            "a": {"wall_s": 9., "cpu_s": 0., "calls": 1},
            "remainder": {"wall_s": 1., "cpu_s": 0., "calls": None}}, "helpers": []},
        {"total": {"wall_s": 100., "cpu_s": 4.}, "exclusive_phases": {
            "a": {"wall_s": 1., "cpu_s": 1., "calls": 2},
            "remainder": {"wall_s": 99., "cpu_s": 3., "calls": None}}, "helpers": []},
    ]
    value = summary_module.aggregate_phases(passes, queries=64)
    phases = value["exclusive_phases"]
    assert phases["a"]["percent_of_own_phase_pass_wall"] == pytest.approx(1000 / 110)
    assert phases["a"]["mean_wall_s_per_operation"] == 10 / 2 / 64
    assert phases["a"]["calls"] == 3
    assert phases["remainder"]["calls"] is None
    assert sum(v["percent_of_own_phase_pass_wall"] for v in phases.values()) == pytest.approx(100.)
    assert sum(v["cpu_s"] for v in phases.values()) == 4.


def test_distribution_keeps_cpu_zero_observations_and_full_range():
    value = summary_module.distribution([0., .015625, 0., 0., 0., 0., 0.])
    assert value["samples"] == 7
    assert value["median"] == value["min"] == 0.
    assert value["max"] == .015625
    assert value["zero_samples"] == 6


def test_all137_cells_and_render_are_reproducible_from_corrected_run_only():
    raw = (HERE / "ladder-run-002.json").read_bytes()
    recomputed = summary_module.build_summary(json.loads(raw), hashlib.sha256(raw).hexdigest())
    saved = json.loads((HERE / "ladder_summary.json").read_text(encoding="utf-8"))
    assert recomputed == saved
    assert summary_module.render(recomputed) == (HERE / "LADDER_FINDINGS.md").read_text(encoding="utf-8")
    assert len(saved["cells"]) == saved["records"] == 137
    assert len({(v["case"], v["arm"]) for v in saved["cells"]}) == 137
    assert saved["source"]["path"] == "ladder-run-002.json"
    assert saved["score"]["same_executor_cm_cold_lower_median_cases"] == 0
    assert len(saved["comparisons"]) == 13
    for row in saved["cells"]:
        for name, _, q in summary_module.TREATMENTS:
            stats = row["timing"][name]
            assert stats["whole_pass"]["wall_s"]["median"] / q == stats["per_operation"]["wall_s"]["median"]
            assert stats["whole_pass"]["cpu_s"]["median"] / q == stats["per_operation"]["cpu_s"]["median"]
            phase = row["phase"][name]
            assert sum(v["wall_s"] for v in phase["exclusive_phases"].values()) == pytest.approx(phase["sum_caller_wall_s"])
            assert sum(v["percent_of_own_phase_pass_wall"] for v in phase["exclusive_phases"].values()) == pytest.approx(100.)
