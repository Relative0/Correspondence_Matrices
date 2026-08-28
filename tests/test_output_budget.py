from __future__ import annotations

import pytest

import cm_bench
from cm_exprlib import Or, Var
from cm_ir import (
    compile_expr,
    compile_expr_to_cm_ir,
    evaluate_compiled,
    materialize_cm,
    materialize_hybrid_no_reinflate,
)
from cm_normalize import canonical_layout
from cm_remote_executor import LocalMockCMRemoteExecutor, build_remote_request
from cm_runpod_protocol import CMRemoteRequest, CMRemoteResponse
from cmbench.output_budget import (
    DEFAULT_OUTPUT_BUDGET,
    OutputBudget,
    OutputBudgetExceeded,
    OutputStatus,
    decide_output_budget,
    estimate_explicit_output,
)


@pytest.mark.parametrize(
    ("variable_count", "expected"),
    [
        (15, OutputStatus.OK),
        (16, OutputStatus.OK),
        (17, OutputStatus.OK),
        (18, OutputStatus.OK),
        (20, OutputStatus.REFUSED),
        (24, OutputStatus.REFUSED),
        (32, OutputStatus.REFUSED),
    ],
)
def test_default_dense_output_boundaries(
    variable_count: int,
    expected: OutputStatus,
) -> None:
    decision = decide_output_budget(
        DEFAULT_OUTPUT_BUDGET,
        estimate_explicit_output(variable_count, "dense_bool"),
        artifact_name="full dense CM output",
    )
    assert decision.status is expected


def test_default_budget_is_representation_aware() -> None:
    packed_21 = decide_output_budget(
        DEFAULT_OUTPUT_BUDGET,
        estimate_explicit_output(21, "packed_bitset"),
    )
    packed_22 = decide_output_budget(
        DEFAULT_OUTPUT_BUDGET,
        estimate_explicit_output(22, "packed_bitset"),
    )
    assert packed_21.status is OutputStatus.OK
    assert packed_21.estimate.output_bytes == 1 << 18
    assert packed_22.status is OutputStatus.REFUSED


def test_dense_materialization_refuses_before_large_allocation() -> None:
    node = compile_expr_to_cm_ir(Var(0))
    variables = [f"x{i}" for i in range(19)]
    rows, columns = canonical_layout(variables, mode="balanced")

    with pytest.raises(OutputBudgetExceeded) as caught:
        materialize_cm(node, rows, columns)

    assert caught.value.status is OutputStatus.REFUSED
    assert caught.value.decision.estimate.output_bytes == 1 << 19


def test_no_reinflate_returns_typed_reduced_status() -> None:
    node = compile_expr_to_cm_ir(Or(Var(0), Var(1)))
    budget = OutputBudget(
        max_output_bytes=1 << 16,
        max_output_vars=16,
        allow_reduced_output=True,
    )
    result = materialize_hybrid_no_reinflate(
        node,
        [f"x{i}" for i in range(32)],
        output_budget=budget,
        allow_reduced_output=True,
    )

    assert result.status is OutputStatus.REDUCED
    assert result.output_vars == ("x0", "x1")
    assert result.budget_decision is not None
    assert result.budget_decision.full_estimate is not None
    assert result.budget_decision.full_estimate.variable_count == 32


def test_temporary_budget_can_refuse_small_output() -> None:
    compiled = compile_expr(Or(Var(0), Var(1)))
    budget = OutputBudget(max_output_bytes=1 << 16, max_temporary_bytes=1)

    with pytest.raises(OutputBudgetExceeded) as caught:
        evaluate_compiled(
            compiled,
            vars_all=["x0", "x1"],
            output_budget=budget,
        )

    assert "temporary bytes" in str(caught.value)


def test_equivalence_reports_refused_not_algorithm_error() -> None:
    result = cm_bench.cm_equivalence_check(Var(0), Var(0), 17, expected=True)
    assert result["cm_equiv_status"] == OutputStatus.REFUSED.value
    assert result["cm_equiv_result"] is None
    assert "OutputBudgetExceeded" in str(result["cm_equiv_error"])


def test_remote_budget_round_trip_and_refusal_status() -> None:
    request = build_remote_request(
        Var(0),
        20,
        max_full_output_vars=None,
        max_output_bytes=1 << 16,
    )
    round_tripped = CMRemoteRequest.from_dict(request.to_dict())
    assert round_tripped.max_output_bytes == 1 << 16
    assert round_tripped.max_temporary_bytes is None

    execution = LocalMockCMRemoteExecutor().execute(round_tripped)
    assert not execution.response.ok
    assert execution.status == OutputStatus.REFUSED.value
    assert execution.response.status == OutputStatus.REFUSED.value

    response_round_trip = CMRemoteResponse.from_dict(execution.response.to_dict())
    assert response_round_trip.status == OutputStatus.REFUSED.value


def test_remote_reduced_output_has_reduced_status() -> None:
    request = build_remote_request(
        Var(0),
        20,
        large_n_safe=True,
        max_full_output_vars=16,
        max_output_bytes=1 << 16,
    )
    execution = LocalMockCMRemoteExecutor().execute(request)
    assert execution.response.ok
    assert execution.status == OutputStatus.REDUCED.value
    assert execution.response.result is not None
    assert execution.response.result["output_vars"] == ["x0"]


@pytest.mark.parametrize("name", ["max_output_bytes", "max_temporary_bytes", "max_output_vars"])
@pytest.mark.parametrize("value", [-1, -0.5, 1.5, True, "16", float("nan"), float("inf")])
def test_budget_rejects_malformed_limits(name, value) -> None:
    with pytest.raises(ValueError):
        OutputBudget(**{name: value})


@pytest.mark.parametrize("representation", ["dense_bool", "truth_table_uint8", "packed_bitset"])
@pytest.mark.parametrize("field", ["max_output_bytes", "max_temporary_bytes"])
def test_budget_exact_limit_neighbors(representation, field) -> None:
    estimate = estimate_explicit_output(6, representation, operation_slots=7)
    limit = estimate.output_bytes if field == "max_output_bytes" else estimate.temporary_bytes
    for delta, allowed in [(-1, False), (0, True), (1, True)]:
        assert decide_output_budget(OutputBudget(**{field: limit + delta}), estimate).allowed is allowed


@pytest.mark.parametrize("value", [-1, -0.5, 1.5, True, "6"])
def test_estimator_rejects_malformed_counts(value) -> None:
    with pytest.raises(ValueError):
        estimate_explicit_output(value, "dense_bool")
    with pytest.raises(ValueError):
        estimate_explicit_output(1, "packed_bitset", operation_slots=value)


def test_estimator_rejects_unbounded_arithmetic() -> None:
    from cmbench.output_budget import MAX_ESTIMATE_VARIABLES

    for count in [MAX_ESTIMATE_VARIABLES + 1, 10**30]:
        with pytest.raises(ValueError, match="bounded"):
            estimate_explicit_output(count, "dense_bool")
    with pytest.raises(ValueError, match="bounded"):
        OutputBudget(max_output_bytes=1 << 5000)


@pytest.mark.parametrize("dense", [False, True])
def test_refusal_clears_prior_output_diagnostics(dense, monkeypatch) -> None:
    import cm_ir

    node = compile_expr_to_cm_ir(Var(0), reuse_cache=False, persistent_cache=False)
    diagnostics = {}

    def call(budget):
        if dense:
            return materialize_cm(node, ["x0"], [], diagnostics=diagnostics, output_budget=budget)
        return materialize_hybrid_no_reinflate(
            node, ["x0"], diagnostics=diagnostics, output_budget=budget, flat_eval=True
        )

    call(None)
    assert diagnostics["output_budget_status"] == "ok"

    def forbidden(*args, **kwargs):
        pytest.fail("refused call reached material allocation")

    monkeypatch.setattr(cm_ir, "_materialize_ir_tagged", forbidden)
    from cmbench.backends.bitset_engine import CMNodeEngineSelection
    monkeypatch.setattr(CMNodeEngineSelection, "evaluate_node", forbidden)
    with pytest.raises(OutputBudgetExceeded):
        call(OutputBudget(max_output_bytes=0))
    assert diagnostics["output_budget_status"] == "refused"
    assert diagnostics["final_output_elements"] == 0
    assert diagnostics["final_bitset_returned"] == 0
    assert diagnostics["final_cm_materialization_performed"] == 0
    assert diagnostics["final_output_representation_code"] == -1


@pytest.mark.parametrize("fast", [False, True])
def test_packed_refusal_precedes_binding_and_cache_fill(fast, monkeypatch) -> None:
    from bitset_backend import bitset_env_cache_stats, clear_bitset_env_cache, get_flat_program
    from cmbench.backends.bitset_engine import CMNodeEngineSelection

    node = compile_expr_to_cm_ir(Or(Var(0), Var(1)), reuse_cache=False, persistent_cache=False)
    program = get_flat_program(node)
    clear_bitset_env_cache()
    before = bitset_env_cache_stats()

    def forbidden(*args, **kwargs):
        pytest.fail("refused call reached packed evaluation")

    monkeypatch.setattr(CMNodeEngineSelection, "evaluate_node", forbidden)
    with pytest.raises(OutputBudgetExceeded):
        materialize_hybrid_no_reinflate(
            node, ["x0", "x1"], output_budget=OutputBudget(max_output_bytes=0),
            flat_eval=True, flat_fast_path=fast,
        )
    assert bitset_env_cache_stats() == before
    assert not program.bound_cache
    assert program.word_plan is None
    assert not hasattr(program.word_scratch_local, "by_width")


def test_pair_refusal_precedes_internal_fallback(monkeypatch) -> None:
    import cm_build_pair

    def forbidden(*args, **kwargs):
        pytest.fail("refused pair call entered recursive allocation")

    monkeypatch.setattr(cm_build_pair, "_compile_pair", forbidden)
    with pytest.raises(OutputBudgetExceeded):
        cm_build_pair.compile_expr_to_cm_pair(
            Or(Var(0), Var(1)), ["x0"], ["x1"], {},
            output_budget=OutputBudget(max_output_bytes=0),
        )


def test_parallel_refusal_precedes_pool_creation(monkeypatch) -> None:
    import cm_ir
    import cm_parallel

    def forbidden(*args, **kwargs):
        pytest.fail("refused parallel call reached allocation or worker pool")

    monkeypatch.setattr(cm_parallel, "_get_process_pool", forbidden)
    monkeypatch.setattr(cm_ir, "_materialize_ir_tagged", forbidden)
    with pytest.raises(OutputBudgetExceeded):
        cm_parallel.compile_expr_to_cm_parallel(
            Var(0), [f"x{i}" for i in range(19)], [], workers=2, min_n=0, min_nodes=0
        )


@pytest.mark.parametrize("field", ["max_output_bytes", "max_temporary_bytes", "max_full_output_vars"])
def test_remote_limits_preserve_null_and_reject_fraction(field) -> None:
    payload = CMRemoteRequest.from_expr(Var(0), ["x0"]).to_dict()
    payload[field] = None
    assert getattr(CMRemoteRequest.from_dict(payload), field) is None
    payload[field] = -0.5
    with pytest.raises(ValueError):
        CMRemoteRequest.from_dict(payload)


def test_legacy_remote_missing_limits_and_refusal_has_no_payload(monkeypatch) -> None:
    import cm_remote_worker

    payload = {"request_id": "legacy", "expr": CMRemoteRequest.from_expr(Var(0), ["x0"]).expr,
               "vars_all": ["x0"]}
    legacy = CMRemoteRequest.from_dict(payload)
    assert legacy.max_output_bytes == 1 << 16
    assert legacy.max_temporary_bytes is None
    assert legacy.max_full_output_vars is None

    def forbidden(*args, **kwargs):
        pytest.fail("refusal reached serialization")

    monkeypatch.setattr(cm_remote_worker, "result_payload", forbidden)
    payload["max_output_bytes"] = 0
    response = cm_remote_worker.execute_cm_request(CMRemoteRequest.from_dict(payload))
    assert response.status == "refused"
    assert response.result is None
    assert response.diagnostics["output_budget_status"] == "refused"


@pytest.mark.parametrize("fixed", [{}, {"x0": 1}, {"x0": 0, "x1": 1}])
def test_small_exact_context_output_order_and_serialization(fixed) -> None:
    import numpy as np
    from bitset_backend import bitset_to_bool_array, eval_cm_node_flat, eval_cm_node_words
    from cm_exprlib import Xor
    from cm_runpod_protocol import result_payload

    node = compile_expr_to_cm_ir(Xor(Var(0), Var(1)), reuse_cache=False, persistent_cache=False)
    variables = [v for v in ["x1", "x0"] if v not in fixed]
    expected = []
    for row in range(1 << len(variables)):
        assignment = dict(fixed)
        assignment.update({v: (row >> (len(variables) - 1 - i)) & 1 for i, v in enumerate(variables)})
        expected.append(assignment["x0"] ^ assignment["x1"])
    bits = eval_cm_node_flat(node, variables, fixed=fixed)
    assert bits == eval_cm_node_words(node, variables, fixed=fixed)
    assert np.array_equal(bitset_to_bool_array(bits, len(variables)), expected)
    result = materialize_hybrid_no_reinflate(node, variables, fixed=fixed, flat_eval=True)
    _, payload = result_payload(result)
    assert int(payload["bits_hex"], 16) == bits
    assert payload["output_vars"] == variables


def test_numpy_integer_budgets_and_override_validation() -> None:
    import numpy as np

    assert OutputBudget(max_output_bytes=np.int64(16)).max_output_bytes == 16
    with pytest.raises(ValueError):
        OutputBudget().with_overrides(max_output_vars=-0.5)


def test_memory_candidate_is_monotone_and_bounded() -> None:
    from scripts.cm_memory_estimator_study import candidate_estimate

    for representation in ("dense", "bigint", "words"):
        args = dict(k=6, representation=representation, nodes=10, slots=10, edges=12, buffers=3)
        baseline = candidate_estimate(**args)["temporary_bytes"]
        for field in ("k", "nodes", "slots", "edges", "buffers"):
            changed = {**args, field: args[field] + 1}
            assert candidate_estimate(**changed)["temporary_bytes"] >= baseline
        with pytest.raises(ValueError):
            candidate_estimate(**{**args, "k": 10**20})


def test_memory_study_local_gate_and_partial_failure_rows() -> None:
    from scripts.cm_memory_estimator_study import incomplete_rows, parse_child_rows, validate_job_execution

    job = dict(k=8, repetitions=3, family="mixed-chain", context="none", schedule="cold",
               case_id="tiny", role="calibration", representation="bigint")
    with pytest.raises(ValueError, match="local"):
        validate_job_execution(job)
    previous = parse_child_rows('{"repetition": 0, "status": "ok"}\n{"repetition":')
    rows = incomplete_rows(job, previous, "timeout", "deadline")
    assert [row["repetition"] for row in rows] == [1, 2]
    assert [row["status"] for row in rows] == ["timeout", "skipped"]


def test_memory_study_profiles_do_not_impute_unmeasured_memory() -> None:
    from scripts.cm_memory_estimator_study import profile_decisions

    decisions = profile_decisions(6, 64, 1 << 30)
    assert all(row["false_admission"] is None and row["false_refusal"] is None for row in decisions)
    assert next(row for row in decisions if row["profile"] == "legacy-direct")["status"] == "ok"
    assert next(row for row in decisions if row["profile"] == "production-balanced-v1-direct")["status"] == "refused"


def test_worker_rejects_malformed_limit_before_compile(monkeypatch) -> None:
    import cm_remote_worker

    def forbidden(*args, **kwargs):
        pytest.fail("malformed request reached compilation/cache insertion")

    monkeypatch.setattr(cm_remote_worker, "compile_expr", forbidden)
    request = CMRemoteRequest.from_expr(Var(0), ["x0"], max_output_bytes=-0.5)
    response = cm_remote_worker.execute_cm_request(request)
    assert not response.ok
    assert response.status == "error"
    assert response.result is None


def test_estimator_formulas_and_none_remain_legacy() -> None:
    for k in range(0, 33):
        dense = estimate_explicit_output(k, "dense_bool", operation_slots=11)
        packed = estimate_explicit_output(k, "packed_bitset", operation_slots=11)
        assert dense.temporary_bytes == 2 * (1 << k)
        assert packed.temporary_bytes == ((1 << k) + 7) // 8 * (11 + k + 2)
        assert decide_output_budget(None, dense).status is OutputStatus.OK
        assert decide_output_budget(None, packed).status is OutputStatus.OK


@pytest.mark.parametrize("builder", ["eager", "lazy"])
def test_build_wrapper_refusal_before_material_allocation(builder, monkeypatch) -> None:
    import cm_ir
    from cm_build import compile_expr_to_cm
    from cm_build_lazy import compile_expr_to_cm_lazy

    def forbidden(*args, **kwargs):
        pytest.fail("wrapper refusal reached material allocation")

    monkeypatch.setattr(cm_ir, "_materialize_ir_tagged", forbidden)
    compile_cm = compile_expr_to_cm if builder == "eager" else compile_expr_to_cm_lazy
    with pytest.raises(OutputBudgetExceeded):
        compile_cm(Var(0), ["x0"], [], {}, output_budget=OutputBudget(max_output_bytes=0))


def test_refusal_estimate_matches_the_attempted_artifact() -> None:
    full = estimate_explicit_output(4, "dense_bool")
    reduced = estimate_explicit_output(0, "dense_bool")
    refused = decide_output_budget(OutputBudget(max_output_bytes=0), full, reduced_estimate=reduced)
    assert refused.status is OutputStatus.REFUSED
    assert refused.estimate is full
    reduced_refused = decide_output_budget(
        OutputBudget(max_output_bytes=0, allow_reduced_output=True), full, reduced_estimate=reduced
    )
    assert reduced_refused.status is OutputStatus.REFUSED
    assert reduced_refused.estimate is reduced


def test_worker_still_charges_early_budget_validation_to_execution(monkeypatch) -> None:
    from types import SimpleNamespace
    import cm_remote_worker
    from cm_ir import FinalNoReinflateResult

    ticks = iter([0.0, 1.0, 3.0, 4.0, 7.0, 8.0, 13.0, 14.0])
    monkeypatch.setattr(cm_remote_worker, "time", SimpleNamespace(perf_counter=lambda: next(ticks)))
    monkeypatch.setattr(cm_remote_worker, "compile_expr", lambda *args, **kwargs: object())
    monkeypatch.setattr(cm_remote_worker, "evaluate_compiled", lambda *args, **kwargs:
                        FinalNoReinflateResult(2, bits=2, output_vars=("x0",)))
    response = cm_remote_worker.execute_cm_request(CMRemoteRequest.from_expr(Var(0), ["x0"]))
    assert response.ok
    assert response.timing == {"remote_total_time_s": 14.0, "remote_compile_time_s": 3.0,
                               "remote_exec_time_s": 7.0}
