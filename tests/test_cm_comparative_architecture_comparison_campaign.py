from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cmbench.comparative import architecture_comparison_campaign as campaign
from cmbench.comparative.architecture_refresh_harness import find_native_library
from scripts.crse_verify_architecture_comparison_campaign import _expected_rows


ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json"


@pytest.fixture(scope="module")
def frozen():
    return json.loads(FREEZE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def oracles(frozen):
    return campaign.build_oracles(ROOT, frozen)


def test_postfreeze_oracles_are_deterministic_and_retain_bounded_refusals(frozen, oracles):
    campaign.validate_oracles(oracles, ROOT, frozen)
    assert sum(row["status"] == "runnable" for row in oracles["lanes"]["A"].values()) == 78
    assert sum(row["status"] == "refused" for row in oracles["lanes"]["A"].values()) == 7
    assert sum(row["status"] == "runnable" for row in oracles["lanes"]["D"].values()) == 3
    assert sum(row["status"] == "refused" for row in oracles["lanes"]["D"].values()) == 4
    assert oracles["policy"]["oracle_selection_influence"] is False
    assert oracles["timing_evidence_produced"] is False


def test_extended_restriction_trace_is_stable_and_supports_k8():
    trace = campaign.build_query_trace("fresh-k8-control", 8)
    assert len(trace) == 64
    assert all(1 <= len(row["fixed"]) < 8 for row in trace)
    assert trace == campaign.build_query_trace("fresh-k8-control", 8)


def test_direct_expression_arm_handles_sparse_dead_variables(frozen, oracles):
    catalog = campaign.resolve_catalog(ROOT, frozen)
    case_id = next(
        case_id for case_id, case in catalog["A"].items()
        if case["fixed"] and case["n_vars"] <= campaign.MAX_COMPLETE_LIVE_VARS
    )
    row = campaign.execute_lane_a(
        catalog["A"][case_id], "direct_expression_bitset", oracles["lanes"]["A"][case_id],
        clock=campaign._DeterministicClock(),
    )
    assert row["status"] == "ok"
    assert row["exact_check_passed"] is True


def test_functional_smoke_exercises_every_admitted_arm_without_timing(frozen, oracles):
    native = find_native_library(ROOT)
    if native is None:
        pytest.skip("retained native library unavailable")
    result = campaign.functional_smoke(ROOT, frozen, oracles, native)
    assert result["status"] == "pass"
    assert result["rows_by_lane"] == {"A": 8, "B": 8, "C": 4, "D": 51}
    assert result["timing_evidence_produced"] is False
    assert result["synthetic_clock_used"] is True


def test_frozen_schedule_expands_to_documented_19646_cells(frozen):
    assert sum(1 for _ in _expected_rows(frozen)) == 19_646


def test_tampered_oracle_fails_closed(frozen, oracles):
    changed = copy.deepcopy(oracles)
    first = next(iter(changed["lanes"]["B"].values()))
    first["checkpoints"]["64"] = "0" * 64
    with pytest.raises(ValueError):
        campaign.validate_oracles(changed, ROOT, frozen)
