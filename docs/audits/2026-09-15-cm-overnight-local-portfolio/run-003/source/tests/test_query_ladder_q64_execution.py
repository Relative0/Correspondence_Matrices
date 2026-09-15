from __future__ import annotations

import copy
import json

from cmbench.recognition import query_ladder_q64_execution as q64


def test_counterbalanced_schedule_has_exact_frozen_cardinality():
    frozen = q64.load_verified_parent(q64.ROOT)
    orders = q64.arm_orders()
    assert len(orders) == 16
    assert len({tuple(row) for row in orders}) == 16
    for arm in frozen["exact_task_contract"]["arms"]:
        assert [sum(row[position] == arm for row in orders) for position in range(8)] == [2] * 8
    assert sum(1 for _ in q64.expected_schedule(frozen)) == 9216


def test_standard_library_oracle_handles_all_boolean_operators():
    document = {
        "version": 2,
        "nodes": [
            {"op": "var", "i": 0}, {"op": "var", "i": 1},
            {"op": "not", "a": 0}, {"op": "and", "a": 0, "b": 1},
            {"op": "or", "a": 2, "b": 3}, {"op": "xor", "a": 0, "b": 1},
            {"op": "imp", "a": 4, "b": 5}, {"op": "eqv", "a": 6, "b": 1},
        ],
        "root": 7,
    }
    bits = q64._eval_full_truth(document, 2)
    expected = 0
    for assignment in range(4):
        x0, x1 = (assignment >> 1) & 1, assignment & 1
        value = int((((not x0) or (x0 and x1)) <= bool(x0 ^ x1)) == bool(x1))
        expected |= value << assignment
    assert bits == expected


def test_raw_verifier_fails_closed_on_a_zero_or_missing_row():
    frozen = q64.load_verified_parent(q64.ROOT)
    oracles = q64.build_oracles(frozen)
    planned = next(q64.expected_schedule(frozen))
    timings = {stage: 1 for stage in q64.campaign.STAGES}
    timings["accounted_total_ns"] = len(q64.campaign.STAGES)
    row = {
        **planned, "schema": q64.RAW_SCHEMA, "status": "ok",
        "exact_check_passed": True,
        "output_sha256": oracles["cases"][planned["case_id"]]["q64_output_sha256"],
        "timings_ns": timings,
    }
    result = q64.verify_raw_rows(frozen, oracles, [row])
    assert result["status"] == "incomplete"
    changed = copy.deepcopy(row)
    changed["timings_ns"]["accounted_total_ns"] = 0
    assert q64.verify_raw_rows(frozen, oracles, [changed])["timing_mismatches"] == 1
