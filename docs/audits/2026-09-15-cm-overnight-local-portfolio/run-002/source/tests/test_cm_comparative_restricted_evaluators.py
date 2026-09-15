from __future__ import annotations

import json
from pathlib import Path

import pytest

import cmbench.comparative.gf2_restricted_evaluators as restricted_evaluators
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cmbench.comparative.gf2_restricted_evaluator_experiment import (
    METHODS,
    REQUIRED_SOURCE_PATHS,
    RestrictedEvaluatorConfig,
    build_schedule,
    execute_session,
    source_fingerprints,
    validate_schedule,
)
from cmbench.comparative.gf2_restricted_evaluators import (
    RESTRICTED_METHODS,
    arena_structural_profile,
    compile_restricted_arena,
    eval_restricted_r0,
    eval_restricted_r1,
    eval_restricted_r2,
    method_work_counters,
    prepare_restriction,
)
from cmbench.comparative.gf2_wide_repeated_queries import _eval_ast_restricted


ROOT = Path(__file__).resolve().parents[1]


def _dataset() -> dict:
    return json.loads((
        ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json"
    ).read_text(encoding="utf-8"))


def test_restricted_r0_r1_r2_match_frozen_control_for_all_gate_types():
    shared = Xor(Var(0), Not(Var(1)))
    expression = Eqv(
        Imp(And(shared, Var(2)), Or(shared, Var(3))),
        Xor(Not(shared), Var(4)),
    )
    document = expr_to_json_dag(expression)
    parsed = expr_from_json(document)
    arena = compile_restricted_arena(document)
    fixed = {"x1": 1, "x3": 0}
    remaining = ("x0", "x2", "x4")
    prepared = prepare_restriction(fixed, remaining)
    expected = _eval_ast_restricted(parsed, fixed, remaining)
    assert eval_restricted_r0(parsed, prepared) == expected
    assert eval_restricted_r1(parsed, prepared) == expected
    assert eval_restricted_r2(arena, prepared) == expected


def test_sharing_counters_prove_occurrence_to_unique_node_reduction_and_liveness():
    expression = Var(0)
    for _ in range(12):
        expression = Or(expression, expression)
    arena = compile_restricted_arena(expr_to_json_dag(expression))
    profile = arena_structural_profile(arena)
    assert profile["unique_nodes"] == 13
    assert profile["unfolded_visits"] == (1 << 13) - 1
    assert method_work_counters(RESTRICTED_METHODS[0], profile)["node_evaluations"] \
        == profile["unfolded_visits"]
    assert method_work_counters(RESTRICTED_METHODS[1], profile)["node_evaluations"] \
        == profile["unique_nodes"]
    assert method_work_counters(RESTRICTED_METHODS[2], profile)["node_evaluations"] \
        == profile["unique_nodes"]
    assert 0 < profile["r2_peak_live_result_slots"] < profile["unique_nodes"]


def test_r2_repeated_child_release_is_safe():
    shared = Xor(Var(0), Var(1))
    expression = And(shared, shared)
    document = expr_to_json_dag(expression)
    arena = compile_restricted_arena(document)
    prepared = prepare_restriction({"x1": 0}, ("x0",))
    assert eval_restricted_r2(arena, prepared) == eval_restricted_r1(
        expr_from_json(document), prepared)


def test_r1_memoizes_shared_zero_results(monkeypatch: pytest.MonkeyPatch):
    shared = Var(0)
    expression = Or(shared, shared)
    prepared = prepare_restriction({"x0": 0}, ("x1",))
    calls = 0
    original = restricted_evaluators._variable_value

    def counting_variable_value(name, current):
        nonlocal calls
        calls += 1
        return original(name, current)

    monkeypatch.setattr(
        restricted_evaluators, "_variable_value", counting_variable_value)
    assert eval_restricted_r1(expression, prepared) == 0
    assert calls == 1


def test_development_session_delivers_exact_canonical_output_and_stage_counters():
    case = _dataset()["cases"][0]
    profile = arena_structural_profile(compile_restricted_arena(case["expression_v2"]))
    results = [execute_session(
        case=case, method=method, structural_profile=profile, role="performance")
        for method in RESTRICTED_METHODS]
    assert len({result["artifact_sha256"] for result in results}) == 1
    assert all(result["exact_check_passed"] for result in results)
    for result in results:
        timings = result["timings_ns"]
        assert timings["accounted_total_ns"] == (
            timings["input_decode_ns"] + timings["representation_ns"]
            + timings["query_total_ns"] + timings["cleanup_ns"])
        assert result["checkpoint_query_ns"]["64"] == timings["query_total_ns"]
        assert len(result["query_measurements"]) == 64
    assert results[1]["resources"]["node_evaluations"] <= profile["unique_nodes"]
    assert results[2]["resources"]["node_evaluations"] == profile["unique_nodes"]
    assert results[2]["resources"]["peak_live_result_slots"] <= profile["unique_nodes"]


def test_development_schedule_is_complete_and_counterbalanced():
    cases = _dataset()["cases"][:2]
    config = RestrictedEvaluatorConfig(run_id="test")
    config.validate()
    rows = build_schedule(cases, config.blocks, config.seed)
    validate_schedule(rows, cases, config.blocks)
    assert len(rows) == len(cases) * 2 * len(METHODS)
    changed = json.loads(json.dumps(rows))
    changed[0]["order_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        validate_schedule(changed, cases, config.blocks)


def test_manifest_source_hash_changes_when_bitset_backend_changes(tmp_path: Path):
    path = tmp_path / "bitset_backend.py"
    path.write_text("version = 1\n", encoding="utf-8")
    before = source_fingerprints(tmp_path, ("bitset_backend.py",))
    path.write_text("version = 2\n", encoding="utf-8")
    after = source_fingerprints(tmp_path, ("bitset_backend.py",))
    assert before["bitset_backend.py"] != after["bitset_backend.py"]
    assert "bitset_backend.py" in REQUIRED_SOURCE_PATHS


def test_arena_rejects_non_dag_v2_input():
    with pytest.raises(ValueError):
        compile_restricted_arena({"op": "var", "i": 0})
