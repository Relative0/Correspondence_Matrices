from __future__ import annotations

import json
from pathlib import Path
import sys

from cmbench.comparative import architecture_comparison_campaign as parent
from cmbench.comparative import h6_fresh_process_memory_gate as gate
from cmbench.comparative.gf2_native_slots import load_native_slot_library
from scripts.crse_verify_h6_fresh_process_memory_gate import verify


ROOT = Path(__file__).resolve().parents[1]
FROZEN = gate.build_freeze(ROOT)


def _write(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_h6_freeze_is_deterministic_and_has_the_declared_fresh_process_schedule():
    frozen = FROZEN
    assert frozen == gate.build_freeze(ROOT)
    assert gate.validate_freeze(frozen, ROOT) == frozen
    assert frozen["expected_rows"] == 708
    assert len(frozen["workload"]["A"]["case_ids"]) == 9
    assert len(frozen["workload"]["B"]["case_ids"]) == 11
    assert len(frozen["workload"]["C"]["case_ids"]) == 6
    rows = list(gate.expected_schedule_rows(frozen))
    assert len(rows) == len({row["row_id"] for row in rows}) == 708
    assert frozen["continuation"]["production_routing_change_authorized"] is False
    assert frozen["continuation"]["runpod_authorized"] is False


def test_all_selected_unchanged_operations_match_the_stored_oracle():
    frozen = FROZEN
    parent_freeze = gate._load(ROOT / gate.PARENT_FREEZE)
    oracles = gate._load(ROOT / gate.PARENT_ORACLES)
    gate._validate_stored_oracles(oracles, parent_freeze)
    catalog = parent.resolve_catalog(ROOT, parent_freeze)
    native = load_native_slot_library(ROOT / gate.NATIVE_LIBRARY)
    selected = []
    for lane, arm in (
        ("A", gate.A_ARMS[0]), ("A", gate.A_ARMS[1]),
        ("B", gate.B_ARMS[0]), ("B", gate.B_ARMS[1]),
        ("B", gate.B_ARMS[2]), ("B", gate.B_ARMS[3]),
        ("C", gate.C_ARMS[0]), ("C", gate.C_ARMS[1]),
    ):
        planned = next(
            row for row in gate.expected_schedule_rows(frozen)
            if row["lane"] == lane and row["arm"] == arm and row["lifecycle"] == "cold"
        )
        result = gate._execute_operation(planned, catalog, oracles, native, None)
        assert len(result["output_sha256"]) == 64
        assert result["output_bytes"] > 0
        assert result["anchor"]
        selected.append(result["output_sha256"])
    assert len(selected) == 8


def test_real_worker_handshake_covers_every_arm_and_lifecycle(tmp_path):
    frozen = FROZEN
    freeze_path = tmp_path / "FREEZE.json"
    _write(freeze_path, frozen)
    pids = set()
    for lane, arms in (("A", gate.A_ARMS), ("B", gate.B_ARMS), ("C", gate.C_ARMS)):
        for arm in arms:
            for lifecycle in gate.LIFECYCLES:
                planned = next(
                    row for row in gate.expected_schedule_rows(frozen)
                    if row["lane"] == lane
                    and row["arm"] == arm
                    and row["query_count"] == (1 if lane in {"A", "B"} else 64)
                    and row["lifecycle"] == lifecycle
                )
                row = gate.run_child_cell(
                    project_root=ROOT,
                    freeze_path=freeze_path,
                    planned=planned,
                    python_executable=Path(sys.executable),
                    worker_script=ROOT / "scripts/cm_h6_fresh_process_memory_gate.py",
                    phase_timeout_seconds=60.0,
                )
                assert row["status"] == "ok"
                assert row["exact_oracle_agreement"] is True
                assert row["child_pid"] not in pids
                pids.add(row["child_pid"])
                assert row["child_exit_code"] == 0
                assert row["memory"]["samplers_stopped"] is True
                assert row["memory"]["execution_sample_count"] >= 1
                assert row["memory"]["common_baseline"]["working_set_bytes"] > 0
                assert row["memory"]["common_baseline"]["private_usage_bytes"] > 0


def _synthetic_rows(frozen):
    arm_rank = {
        arm: index + 1
        for index, arm in enumerate((*gate.A_ARMS, *gate.B_ARMS, *gate.C_ARMS))
    }
    rows = []
    for index, planned in enumerate(gate.expected_schedule_rows(frozen), 1):
        baseline = 100_000_000
        delta = 131_072 * arm_rank[planned["arm"]]
        prepared = 131_072 if planned["lifecycle"] == "reused" else 0
        endpoint = {
            "working_set_bytes": baseline + prepared,
            "private_usage_bytes": baseline + prepared,
            "process_peak_working_set_bytes": baseline + delta,
            "process_peak_pagefile_bytes": baseline + delta,
        }
        memory = {
            "samplers_stopped": True,
            "execution_sample_count": 2,
            "common_baseline": {**endpoint, "working_set_bytes": baseline, "private_usage_bytes": baseline},
            "prepared_endpoint": endpoint,
            "retained_endpoint": endpoint,
            "post_release_endpoint": {**endpoint, "working_set_bytes": baseline, "private_usage_bytes": baseline},
            "working_set_task_peak_bytes": baseline + delta,
            "working_set_task_peak_delta_bytes": delta,
            "private_task_peak_delta_bytes": delta,
            "working_set_prepared_retained_delta_bytes": prepared,
            "private_prepared_retained_delta_bytes": prepared,
        }
        rows.append({
            "schema": gate.RAW_SCHEMA,
            **planned,
            "status": "ok",
            "child_pid": index,
            "child_exit_code": 0,
            "exact_oracle_agreement": True,
            "output_sha256": "a" * 64,
            "ordering_sha256": "b" * 64,
            "structure_sha256": "c" * 64,
            "memory": memory,
        })
    return rows


def test_summary_gate_and_independent_replay_are_deterministic(tmp_path):
    frozen = FROZEN
    freeze_path = tmp_path / "FREEZE.json"
    raw_path = tmp_path / "RAW.jsonl"
    summary_path = tmp_path / "SUMMARY.json"
    _write(freeze_path, frozen)
    rows = _synthetic_rows(frozen)
    raw_path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    summary = gate.summarize(raw_path, frozen)
    assert summary["decision"] == "go_memory_calibration_only_requires_separate_candidate_freeze"
    assert all(summary["conditions"].values())
    _write(summary_path, summary)
    replay = verify(ROOT, freeze_path, raw_path, summary_path)
    assert replay["status"] == "verified"
    assert replay["summary_replay_mismatches"] == 0


def test_zero_os_signal_closes_h6_without_authorizing_a_candidate(tmp_path):
    frozen = FROZEN
    rows = _synthetic_rows(frozen)
    for row in rows:
        row["memory"]["working_set_task_peak_delta_bytes"] = 0
        row["memory"]["private_task_peak_delta_bytes"] = 0
        row["memory"]["working_set_prepared_retained_delta_bytes"] = 0
        row["memory"]["private_prepared_retained_delta_bytes"] = 0
    raw_path = tmp_path / "RAW.jsonl"
    raw_path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    summary = gate.summarize(raw_path, frozen)
    assert summary["decision"] == "no_go_h6_routing_still_deferred"
    assert summary["conditions"]["validity"] is True
    assert summary["conditions"]["per_arm_lifecycle_positive_os_peak"] is False
    assert summary["candidate_implemented"] is False
    assert summary["runpod_authorization_request_permitted"] is False
