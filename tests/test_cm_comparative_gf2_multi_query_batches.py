from __future__ import annotations

import json
from pathlib import Path

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Not, Or, Var, Xor
from cmbench.comparative.gf2_multi_query_batches import (
    batch_plan_metrics,
    build_multi_query_batch_plan,
    evaluate_multi_query_batch,
)
from cmbench.comparative.gf2_multi_query_batch_experiment import (
    METHODS,
    MultiQueryBatchConfig,
    build_schedule,
    execute_session,
    validate_schedule,
)
from cmbench.comparative.gf2_restricted_evaluators import compile_restricted_arena
from cmbench.comparative.gf2_wide_repeated_queries import restrict_full_truth


ROOT = Path(__file__).resolve().parents[1]


def _query(query: int, fixed: dict[str, int], n_vars: int) -> dict:
    remaining = [f"x{i}" for i in range(n_vars) if f"x{i}" not in fixed]
    return {
        "query": query,
        "fixed": [{"variable": name, "value": value}
                  for name, value in sorted(fixed.items())],
        "remaining_order": remaining,
    }


def test_concatenated_and_union_care_batches_match_exact_restrictions():
    expression = Or(And(Var(0), Not(Var(1))), Xor(Var(2), Var(3)))
    arena = compile_restricted_arena(expr_to_json_dag(expression))
    trace = [
        _query(0, {"x0": 0, "x3": 1}, 4),
        _query(1, {"x0": 1, "x3": 1}, 4),
        _query(2, {"x1": 0, "x3": 1}, 4),
    ]
    full_bits = 0
    from bitset_backend import build_bitset_env, eval_expr_bitset
    full_bits = eval_expr_bitset(expression, build_bitset_env(("x0", "x1", "x2", "x3")))
    expected = []
    for query in trace:
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        _remaining, reduced = restrict_full_truth(full_bits, 4, fixed)
        expected.append(reduced)
    for mode in ("concatenated", "union_care"):
        plan = build_multi_query_batch_plan(trace, 4, mode)
        assert evaluate_multi_query_batch(arena, plan) == tuple(expected)
    concat = build_multi_query_batch_plan(trace, 4, "concatenated")
    care = build_multi_query_batch_plan(trace, 4, "union_care")
    assert concat.lane_count == concat.requested_lane_count
    assert care.lane_count < care.requested_lane_count
    assert care.lane_count <= min(care.requested_lane_count, 1 << 4)


def test_duplicate_queries_deduplicate_lanes_but_preserve_duplicate_outputs():
    expression = Xor(Var(0), Var(1))
    arena = compile_restricted_arena(expr_to_json_dag(expression))
    query = _query(0, {"x0": 1}, 2)
    plan = build_multi_query_batch_plan([query, query], 2, "union_care")
    outputs = evaluate_multi_query_batch(arena, plan)
    metrics = batch_plan_metrics(plan)
    assert outputs[0] == outputs[1]
    assert metrics["requested_lane_count"] == 4
    assert metrics["evaluated_lane_count"] == 2
    assert metrics["deduplicated_lane_count"] == 2


def test_c36_full_trace_batches_match_frozen_truth_projection():
    dataset = json.loads((
        ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json"
    ).read_text(encoding="utf-8"))
    case = dataset["cases"][0]
    arena = compile_restricted_arena(case["expression_v2"])
    expected = []
    for query in case["c36_trace"]:
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        _remaining, reduced = restrict_full_truth(
            int(case["truth_bits_hex"], 16), case["n_vars"], fixed)
        expected.append(reduced)
    for mode in ("concatenated", "union_care"):
        plan = build_multi_query_batch_plan(case["c36_trace"], case["n_vars"], mode)
        assert evaluate_multi_query_batch(arena, plan) == tuple(expected)


def test_multi_query_all_experiment_arms_match_exact_prefix_and_charge_stages():
    dataset = json.loads((
        ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json"
    ).read_text(encoding="utf-8"))
    case = dataset["cases"][0]
    sessions = [execute_session(
        case=case, method=method, query_count=4, role="performance")
        for method in METHODS]
    assert len({session["artifact_sha256"] for session in sessions}) == 1
    for session in sessions:
        timings = session["timings_ns"]
        assert session["exact_check_passed"]
        assert len(session["query_output_sha256"]) == 4
        assert timings["accounted_total_ns"] == sum(
            timings[key] for key in (
                "input_decode_ns", "representation_ns", "restriction_setup_ns",
                "evaluation_ns", "delivery_ns", "cleanup_ns"))
        assert session["resources"]["rss_sampling_points"] > 0


def test_multi_query_schedule_is_deterministic_and_counterbalanced():
    cases = json.loads((
        ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json"
    ).read_text(encoding="utf-8"))["cases"][:2]
    config = MultiQueryBatchConfig(run_id="test")
    config.validate()
    rows = build_schedule(cases, config.blocks, config.seed)
    assert rows == build_schedule(cases, config.blocks, config.seed)
    validate_schedule(rows, cases, config.blocks)
    assert len(rows) == len(cases) * len(config.query_counts) * config.blocks
