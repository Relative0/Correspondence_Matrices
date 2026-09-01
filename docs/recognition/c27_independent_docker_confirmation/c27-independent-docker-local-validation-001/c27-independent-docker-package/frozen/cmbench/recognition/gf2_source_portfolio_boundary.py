"""Fail-closed, fully charged C24 boundary around the frozen C22 portfolio."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping

from cm_expr_serde import expr_from_json

from .gf2_source_portfolio import (
    CompiledSourcePortfolio,
    compile_source_portfolio,
    load_source_portfolio_policy,
    verify_source_portfolio_execution,
)
from .gf2_task_dispatcher import GF2DecompositionTask, canonical_sha256
from .portfolio import reference_bits


BOUNDARY_SCHEMA = "crse-c24-gf2-source-portfolio-boundary/v1"
TIMING_FIELDS = (
    "input_validation_ns",
    "policy_load_ns",
    "compile_ns",
    "execution_ns",
    "serialization_verify_ns",
    "boundary_overhead_ns",
)
MIN_VARS = 3
MAX_VARS = 6


@dataclass(frozen=True)
class SourcePortfolioBoundaryResult:
    case_id: str | None
    n_vars: int | None
    status: str
    reason: str
    advice_enabled: bool
    shadow: bool
    force_source_refusal: bool
    policy_sha256: str | None
    requested_arm: str | None
    selected_arm: str | None
    fallback_used: bool | None
    exact_check_passed: bool
    best_artifact: dict[str, Any] | None
    artifact_sha256: str | None
    timings_ns: dict[str, int]
    execution: dict[str, Any] | None
    schema: str = BOUNDARY_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _RefusingSourcePortfolio(CompiledSourcePortfolio):
    """Deterministic fault injection for the exact fallback control."""

    def _source_packed(self, document: dict[str, Any]):
        raise ValueError("C24 injected source-path refusal")


def _finish_timings(timings: dict[str, int], total_started: int,
                    clock: Callable[[], int]) -> dict[str, int]:
    elapsed = max(1, clock() - total_started)
    charged = sum(timings[field] for field in TIMING_FIELDS if field != "boundary_overhead_ns")
    timings["boundary_overhead_ns"] = max(0, elapsed - charged)
    return {**timings, "task_total_ns": sum(timings.values())}


def _refused(*, case_id: str | None, n_vars: int | None, reason: str,
             advice_enabled: bool, shadow: bool, force_source_refusal: bool,
             timings: dict[str, int], total_started: int,
             clock: Callable[[], int]) -> SourcePortfolioBoundaryResult:
    return SourcePortfolioBoundaryResult(
        case_id=case_id,
        n_vars=n_vars,
        status="refused",
        reason=reason,
        advice_enabled=advice_enabled,
        shadow=shadow,
        force_source_refusal=force_source_refusal,
        policy_sha256=None,
        requested_arm=None,
        selected_arm=None,
        fallback_used=None,
        exact_check_passed=False,
        best_artifact=None,
        artifact_sha256=None,
        timings_ns=_finish_timings(timings, total_started, clock),
        execution=None,
    )


def execute_source_portfolio_boundary(
    case: Mapping[str, Any],
    policy_path: Path,
    *,
    advice_enabled: bool = True,
    shadow: bool = False,
    force_source_refusal: bool = False,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> SourcePortfolioBoundaryResult:
    """Execute one fresh single-query C22 request with all boundary costs charged."""
    if (type(advice_enabled) is not bool or type(shadow) is not bool
            or type(force_source_refusal) is not bool
            or force_source_refusal and (not advice_enabled or shadow)):
        raise ValueError("invalid C24 boundary switches")
    total_started = clock()
    timings = {field: 0 for field in TIMING_FIELDS}
    case_id = case.get("case_id") if isinstance(case, Mapping) else None
    n_vars = case.get("n_vars") if isinstance(case, Mapping) else None

    started = clock()
    try:
        if (
            not isinstance(case, Mapping)
            or type(case_id) is not str
            or not case_id
            or len(case_id) > 256
            or type(n_vars) is not int
            or not MIN_VARS <= n_vars <= MAX_VARS
            or type(case.get("expression_v2")) is not dict
            or type(case.get("truth_bits_hex")) is not str
        ):
            raise ValueError("C24 input envelope")
        expression = expr_from_json(case["expression_v2"])
        frozen_bits = int(case["truth_bits_hex"], 16)
        if frozen_bits < 0 or frozen_bits.bit_length() > (1 << n_vars):
            raise ValueError("C24 frozen truth bound")
        if reference_bits(expression, n_vars) != frozen_bits:
            raise ValueError("C24 expression/truth mismatch")
        task = GF2DecompositionTask(n_vars, tuple(range(n_vars)))
        task.validate()
    except (KeyError, TypeError, ValueError) as exc:
        timings["input_validation_ns"] = max(1, clock() - started)
        return _refused(
            case_id=case_id if type(case_id) is str else None,
            n_vars=n_vars if type(n_vars) is int else None,
            reason="input_refused:" + type(exc).__name__,
            advice_enabled=advice_enabled,
            shadow=shadow,
            force_source_refusal=force_source_refusal,
            timings=timings,
            total_started=total_started,
            clock=clock,
        )
    timings["input_validation_ns"] = max(1, clock() - started)

    started = clock()
    try:
        policy = load_source_portfolio_policy(policy_path)
    except (OSError, TypeError, ValueError) as exc:
        timings["policy_load_ns"] = max(1, clock() - started)
        return _refused(
            case_id=case_id,
            n_vars=n_vars,
            reason="policy_refused:" + type(exc).__name__,
            advice_enabled=advice_enabled,
            shadow=shadow,
            force_source_refusal=force_source_refusal,
            timings=timings,
            total_started=total_started,
            clock=clock,
        )
    timings["policy_load_ns"] = max(1, clock() - started)

    started = clock()
    try:
        if force_source_refusal:
            compiled = _RefusingSourcePortfolio(
                policy, task, advice_enabled=advice_enabled, shadow=shadow)
        else:
            compiled = compile_source_portfolio(
                policy, task, advice_enabled=advice_enabled, shadow=shadow)
    except (TypeError, ValueError) as exc:
        timings["compile_ns"] = max(1, clock() - started)
        return _refused(
            case_id=case_id,
            n_vars=n_vars,
            reason="compile_refused:" + type(exc).__name__,
            advice_enabled=advice_enabled,
            shadow=shadow,
            force_source_refusal=force_source_refusal,
            timings=timings,
            total_started=total_started,
            clock=clock,
        )
    timings["compile_ns"] = max(1, clock() - started)

    started = clock()
    try:
        execution = compiled.execute(case["expression_v2"])
    except (KeyError, TypeError, ValueError) as exc:
        timings["execution_ns"] = max(1, clock() - started)
        return _refused(
            case_id=case_id,
            n_vars=n_vars,
            reason="execution_refused:" + type(exc).__name__,
            advice_enabled=advice_enabled,
            shadow=shadow,
            force_source_refusal=force_source_refusal,
            timings=timings,
            total_started=total_started,
            clock=clock,
        )
    timings["execution_ns"] = max(1, clock() - started)

    started = clock()
    execution_document = execution.to_dict()
    verify_source_portfolio_execution(
        execution_document, case["expression_v2"], policy_sha256=policy["policy_sha256"])
    json.dumps(execution_document, sort_keys=True, separators=(",", ":"), allow_nan=False)
    artifact_sha256 = canonical_sha256(execution.best_artifact)
    timings["serialization_verify_ns"] = max(1, clock() - started)
    return SourcePortfolioBoundaryResult(
        case_id=case_id,
        n_vars=n_vars,
        status="ok",
        reason=execution.decision_reason,
        advice_enabled=advice_enabled,
        shadow=shadow,
        force_source_refusal=force_source_refusal,
        policy_sha256=policy["policy_sha256"],
        requested_arm=execution.requested_arm,
        selected_arm=execution.selected_arm,
        fallback_used=execution.fallback_used,
        exact_check_passed=execution.exact_check_passed,
        best_artifact=execution.best_artifact,
        artifact_sha256=artifact_sha256,
        timings_ns=_finish_timings(timings, total_started, clock),
        execution=execution_document,
    )


def verify_source_portfolio_boundary_result(
    document: dict[str, Any],
    case: Mapping[str, Any],
    *,
    required_best: dict[str, Any] | None | object = ...,
) -> None:
    expected = {field.name for field in SourcePortfolioBoundaryResult.__dataclass_fields__.values()}
    if type(document) is not dict or set(document) != expected:
        raise ValueError("invalid C24 boundary fields")
    timings = document.get("timings_ns")
    if (
        document.get("schema") != BOUNDARY_SCHEMA
        or document.get("status") not in {"ok", "refused"}
        or type(timings) is not dict
        or set(timings) != {*TIMING_FIELDS, "task_total_ns"}
        or any(type(value) is not int or value < 0 for value in timings.values())
        or timings["task_total_ns"] != sum(
            timings[field] for field in TIMING_FIELDS)
        or type(document.get("advice_enabled")) is not bool
        or type(document.get("shadow")) is not bool
        or type(document.get("force_source_refusal")) is not bool
    ):
        raise ValueError("invalid C24 boundary record")
    if document["status"] == "refused":
        if (
            document.get("exact_check_passed") is not False
            or document.get("execution") is not None
            or document.get("best_artifact") is not None
            or document.get("artifact_sha256") is not None
            or document.get("selected_arm") is not None
        ):
            raise ValueError("invalid C24 refusal")
        return
    if (
        document.get("case_id") != case.get("case_id")
        or document.get("n_vars") != case.get("n_vars")
        or document.get("exact_check_passed") is not True
        or type(document.get("execution")) is not dict
        or document.get("artifact_sha256") != canonical_sha256(document.get("best_artifact"))
        or required_best is not ... and document.get("best_artifact") != required_best
    ):
        raise ValueError("invalid C24 successful boundary result")
    verify_source_portfolio_execution(
        document["execution"], case["expression_v2"], policy_sha256=document["policy_sha256"])

