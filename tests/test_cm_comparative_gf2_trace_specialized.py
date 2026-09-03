from __future__ import annotations

import json
from pathlib import Path

import pytest

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cmbench.comparative.gf2_restricted_evaluators import (
    compile_restricted_arena,
    eval_restricted_r2,
    prepare_restriction,
)
from cmbench.comparative.gf2_trace_specialized import (
    compile_trace_specialized,
    evaluate_trace_specialized,
    trace_plan_metrics,
)
from cmbench.comparative.gf2_trace_specialized_experiment import (
    METHODS,
    TraceSpecializedConfig,
    build_schedule,
    execute_session,
    summarize,
    validate_schedule,
)


ROOT = Path(__file__).resolve().parents[1]


def _query(index: int, fixed: dict[str, int], remaining: tuple[str, ...]) -> dict:
    return {
        "query": index,
        "fixed": [
            {"variable": name, "value": value}
            for name, value in sorted(fixed.items(), key=lambda item: int(item[0][1:]))
        ],
        "remaining_order": list(remaining),
    }


def _independent(document: dict, trace: list[dict]) -> tuple[int, ...]:
    arena = compile_restricted_arena(document)
    output = []
    for query in trace:
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        output.append(eval_restricted_r2(
            arena, prepare_restriction(fixed, query["remaining_order"])))
    return tuple(output)


def test_trace_specialization_matches_independent_all_gate_expression():
    shared = Xor(Var(0), Not(Var(1)))
    expression = Eqv(
        Imp(And(shared, Var(2)), Or(shared, Var(3))),
        Xor(Not(shared), Var(4)),
    )
    document = expr_to_json_dag(expression)
    trace = [
        _query(0, {"x1": 1, "x3": 0}, ("x0", "x2", "x4")),
        _query(1, {"x1": 0, "x3": 1}, ("x0", "x2", "x4")),
        _query(2, {"x0": 1, "x4": 0}, ("x1", "x2", "x3")),
    ]
    plan = compile_trace_specialized(document, trace, 5)
    assert evaluate_trace_specialized(plan) == _independent(document, trace)
    assert trace_plan_metrics(plan)["residual_order_groups"] == 2


def test_irrelevant_fixed_values_reuse_the_same_specialized_root():
    document = expr_to_json_dag(Imp(Var(0), Var(1)))
    trace = [
        _query(0, {"x2": 0}, ("x0", "x1")),
        _query(1, {"x2": 1}, ("x0", "x1")),
    ]
    plan = compile_trace_specialized(document, trace, 3)
    metrics = trace_plan_metrics(plan)
    assert metrics["specialized_roots"] == 2
    assert metrics["unique_specialized_roots"] == 1
    assert evaluate_trace_specialized(plan) == _independent(document, trace)


def test_duplicate_and_reordered_queries_preserve_canonical_outputs():
    document = expr_to_json_dag(Xor(And(Var(0), Var(1)), Var(2)))
    first = _query(0, {"x0": 1}, ("x1", "x2"))
    second = _query(1, {"x2": 0}, ("x0", "x1"))
    trace = [first, second, dict(first)]
    forward = evaluate_trace_specialized(compile_trace_specialized(document, trace, 3))
    reversed_trace = list(reversed(trace))
    reverse = evaluate_trace_specialized(
        compile_trace_specialized(document, reversed_trace, 3))
    assert forward == _independent(document, trace)
    assert reverse == tuple(reversed(forward))
    assert forward[0] == forward[2]


def test_full_c36_trace_matches_repaired_r2_for_every_case():
    dataset = json.loads((
        ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json"
    ).read_text(encoding="utf-8"))
    for case in dataset["cases"]:
        document = case["expression_v2"]
        trace = case["c36_trace"]
        plan = compile_trace_specialized(document, trace, case["n_vars"])
        assert evaluate_trace_specialized(plan) == _independent(document, trace)
        assert trace_plan_metrics(plan)["queries"] == 64


def test_trace_experiment_session_and_schedule_are_exact_and_balanced():
    dataset = json.loads((
        ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json"
    ).read_text(encoding="utf-8"))
    cases = dataset["cases"][:2]
    config = TraceSpecializedConfig(run_id="test")
    config.validate()
    schedule = build_schedule(cases, config.blocks, config.seed)
    validate_schedule(schedule, cases, config.blocks)
    changed = json.loads(json.dumps(schedule))
    changed[0]["order_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        validate_schedule(changed, cases, config.blocks)

    sessions = [execute_session(
        case=cases[0], method=method, query_count=4, role="performance")
        for method in METHODS]
    assert len({session["artifact_sha256"] for session in sessions}) == 1
    for session in sessions:
        timings = session["timings_ns"]
        assert timings["accounted_total_ns"] == sum(
            value for key, value in timings.items() if key != "accounted_total_ns")


def test_trace_summary_applies_continuation_gate_without_promoting():
    rows = []
    for case_index, case_id in enumerate(("a", "b")):
        for query_count in (1, 4, 16, 64):
            for block in range(4):
                for method in METHODS:
                    total = 80 if method == "trace_specialized" else 100
                    rows.append({
                        "role": "performance", "case_id": case_id,
                        "family": "test", "n_vars": 11 + case_index,
                        "query_count": query_count, "method": method,
                        "timings_ns": {"accounted_total_ns": total},
                    })
    for case_index, case_id in enumerate(("a", "b")):
        for method in METHODS:
            rows.append({
                "role": "memory_profile", "case_id": case_id,
                "family": "test", "n_vars": 11 + case_index,
                "query_count": 64, "method": method,
                "resources": {
                    "session_sampled_peak_rss_delta_bytes": 1,
                    "tracemalloc_peak_bytes": 2,
                },
            })
    summary = summarize(rows, 1.10)
    assert summary["decision"]["trace_continuation_gate_passed"] is True
    assert summary["decision"][
        "formal_confirmation_or_production_promotion_permitted"] is False
