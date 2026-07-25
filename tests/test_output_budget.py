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
