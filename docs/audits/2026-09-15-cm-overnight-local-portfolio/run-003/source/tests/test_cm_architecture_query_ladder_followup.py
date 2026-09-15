from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from cmbench.comparative import architecture_comparison_campaign as parent
from cmbench.comparative import architecture_query_ladder_followup as followup
from cmbench.comparative.architecture_query_ladder_freeze import build_followup_freeze
from cmbench.comparative.architecture_refresh_harness import find_native_library


ROOT = Path(__file__).resolve().parents[1]
PARENT_FREEZE = ROOT / "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json"
ORACLES = ROOT / "docs/recognition/architecture_comparison_execution_retry_20260903/ORACLES.json"


@pytest.fixture(scope="module")
def parent_inputs():
    freeze = json.loads(PARENT_FREEZE.read_text(encoding="utf-8"))
    oracles = json.loads(ORACLES.read_text(encoding="utf-8"))
    catalog = parent.resolve_catalog(ROOT, freeze)["B"]
    return freeze, oracles, catalog


def test_every_query_count_is_an_exact_distinct_cell(parent_inputs) -> None:
    freeze, oracles, catalog = parent_inputs
    native_path = find_native_library(ROOT)
    if native_path is None:
        pytest.skip("retained native library unavailable")
    native = followup.load_native_slot_library(native_path)
    case_id = next(case for case in freeze["schedules"]["B"]["case_order"] if case.startswith("fresh-tree-"))
    clock = parent._DeterministicClock()

    rows = [
        followup.execute_query_count_cell(
            catalog[case_id], arm, oracles["lanes"]["B"][case_id], native,
            query_count, clock=clock,
        )
        for query_count in followup.QUERY_COUNTS
        for arm in freeze["schedules"]["B"]["arms"]
    ]

    assert len(rows) == 32
    assert {row["query_count"] for row in rows} == {1, 4, 16, 64}
    assert all(row["resources"]["queries"] == row["query_count"] for row in rows)
    assert all(row["exact_check_passed"] for row in rows)
    assert all(row["cleanup_method"] == "gc_collect_in_process" for row in rows)
    assert all(
        row["output_sha256"] == oracles["lanes"]["B"][case_id]["checkpoints"][str(row["query_count"])]
        for row in rows
    )
    assert all(row["memory_measurement"]["interpretation_permitted"] is False for row in rows)


def test_isolated_process_cleanup_does_not_collect_the_inherited_heap(
    parent_inputs, monkeypatch: pytest.MonkeyPatch,
) -> None:
    freeze, oracles, catalog = parent_inputs
    native_path = find_native_library(ROOT)
    if native_path is None:
        pytest.skip("retained native library unavailable")
    native = followup.load_native_slot_library(native_path)
    case_id = next(
        case for case in freeze["schedules"]["B"]["case_order"]
        if case.startswith("fresh-tree-")
    )

    def refuse_collect() -> None:
        raise AssertionError("isolated child cleanup must not scan the inherited heap")

    monkeypatch.setattr(followup.gc, "collect", refuse_collect)
    row = followup.execute_query_count_cell(
        catalog[case_id], "r2_topological_liveness", oracles["lanes"]["B"][case_id],
        native, 1, clock=parent._DeterministicClock(), isolated_process_cleanup=True,
    )

    assert row["cleanup_method"] == "cache_clear_then_isolated_child_exit"
    assert row["timings_ns"]["cleanup_ns"] > 0


def test_followup_freeze_preserves_parent_cases_and_counterbalance() -> None:
    freeze = build_followup_freeze(
        project_root=ROOT,
        source_checkpoint="0" * 40,
        parent_freeze_path=PARENT_FREEZE.relative_to(ROOT).as_posix(),
        parent_analysis_path=(
            ROOT / "docs/recognition/architecture_comparison_execution_retry_20260903/ANALYSIS.json"
        ).relative_to(ROOT).as_posix(),
        oracles_path=ORACLES.relative_to(ROOT).as_posix(),
    )
    parent_freeze = json.loads(PARENT_FREEZE.read_text(encoding="utf-8"))

    assert freeze["schedule"]["case_order"] == parent_freeze["schedules"]["B"]["case_order"]
    assert freeze["schedule"]["arm_orders"] == parent_freeze["schedules"]["B"]["arm_orders"]
    assert freeze["schedule"]["query_counts"] == [1, 4, 16, 64]
    assert freeze["schedule"]["planned_cells"] == 27_648
    assert sum(1 for _ in followup.expected_schedule_rows(freeze)) == 27_648
    assert followup.validate_followup_freeze(freeze) is freeze


def test_isolated_memory_path_fails_closed_off_linux() -> None:
    if sys.platform == "linux":
        pytest.skip("off-Linux fail-closed behavior")
    with pytest.raises(ValueError, match="Linux fork/wait4 required"):
        followup.execute_isolated_linux_cell(lambda: {})
