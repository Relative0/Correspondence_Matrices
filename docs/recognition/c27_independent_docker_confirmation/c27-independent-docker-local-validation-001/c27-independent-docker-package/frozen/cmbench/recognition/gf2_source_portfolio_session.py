"""Bounded resident-session lifecycle for the frozen C22 exact portfolio."""
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

SESSION_SCHEMA = "crse-c25-gf2-source-portfolio-session/v1"
QUERY_SCHEMA = "crse-c25-gf2-source-portfolio-session-query/v1"
MIN_VARS = 3
MAX_VARS = 6
QUERY_TIMING_FIELDS = (
    "input_validation_ns",
    "compile_cache_ns",
    "execution_ns",
    "serialization_verify_ns",
    "wrapper_ns",
)
SETUP_TIMING_FIELDS = ("policy_load_validate_ns", "session_initialize_ns")


class _RefusingResidentPortfolio(CompiledSourcePortfolio):
    def _source_packed(self, document: dict[str, Any]):
        raise ValueError("C25 injected resident source-path refusal")


@dataclass(frozen=True)
class ResidentQueryResult:
    session_id: str
    query_index: int
    case_id: str | None
    n_vars: int | None
    status: str
    reason: str
    advice_enabled: bool
    shadow: bool
    force_source_refusal: bool
    policy_sha256: str
    compile_cache_hit: bool | None
    requested_arm: str | None
    selected_arm: str | None
    fallback_used: bool | None
    exact_check_passed: bool
    best_artifact: dict[str, Any] | None
    artifact_sha256: str | None
    timings_ns: dict[str, int]
    execution: dict[str, Any] | None
    schema: str = QUERY_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _finish_timings(timings: dict[str, int], total_started: int,
                    clock: Callable[[], int]) -> dict[str, int]:
    elapsed = max(1, clock() - total_started)
    charged = sum(timings[field] for field in QUERY_TIMING_FIELDS if field != "wrapper_ns")
    timings["wrapper_ns"] = max(0, elapsed - charged)
    return {**timings, "task_total_ns": sum(timings.values())}


class ResidentSourcePortfolioSession:
    """One immutable policy with bounded per-width compiled-state reuse."""

    def __init__(self, session_id: str, policy_path: Path, *, advice_enabled: bool = True,
                 shadow: bool = False, max_queries: int = 32,
                 clock: Callable[[], int] = time.perf_counter_ns):
        if (
            type(session_id) is not str
            or not session_id
            or len(session_id) > 256
            or type(advice_enabled) is not bool
            or type(shadow) is not bool
            or type(max_queries) is not int
            or not 1 <= max_queries <= 256
        ):
            raise ValueError("invalid C25 resident-session configuration")
        setup_started = clock()
        started = clock()
        policy = load_source_portfolio_policy(policy_path)
        policy_load_ns = max(1, clock() - started)
        started = clock()
        self.session_id = session_id
        self.policy = json.loads(json.dumps(policy, allow_nan=False))
        self.advice_enabled = advice_enabled
        self.shadow = shadow
        self.max_queries = max_queries
        self._clock = clock
        self._compiled: dict[int, CompiledSourcePortfolio] = {}
        self._successful_queries = 0
        self._refused_queries = 0
        self._closed = False
        initialize_ns = max(1, clock() - started)
        elapsed = max(1, clock() - setup_started)
        self.setup_timings_ns = {
            "policy_load_validate_ns": policy_load_ns,
            "session_initialize_ns": max(initialize_ns, elapsed - policy_load_ns),
        }
        self.setup_timings_ns["setup_total_ns"] = sum(self.setup_timings_ns.values())

    @property
    def successful_queries(self) -> int:
        return self._successful_queries

    @property
    def refused_queries(self) -> int:
        return self._refused_queries

    @property
    def closed(self) -> bool:
        return self._closed

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": SESSION_SCHEMA,
            "session_id": self.session_id,
            "policy_sha256": self.policy["policy_sha256"],
            "advice_enabled": self.advice_enabled,
            "shadow": self.shadow,
            "max_queries": self.max_queries,
            "successful_queries": self._successful_queries,
            "refused_queries": self._refused_queries,
            "compiled_widths": sorted(self._compiled),
            "closed": self._closed,
            "setup_timings_ns": dict(self.setup_timings_ns),
        }

    def close(self) -> dict[str, Any]:
        self._compiled.clear()
        self._closed = True
        return self.snapshot()

    def _refused(self, *, case_id: str | None, n_vars: int | None, reason: str,
                 force_source_refusal: bool, timings: dict[str, int],
                 total_started: int) -> ResidentQueryResult:
        self._refused_queries += 1
        return ResidentQueryResult(
            session_id=self.session_id,
            query_index=self._successful_queries,
            case_id=case_id,
            n_vars=n_vars,
            status="refused",
            reason=reason,
            advice_enabled=self.advice_enabled,
            shadow=self.shadow,
            force_source_refusal=force_source_refusal,
            policy_sha256=self.policy["policy_sha256"],
            compile_cache_hit=None,
            requested_arm=None,
            selected_arm=None,
            fallback_used=None,
            exact_check_passed=False,
            best_artifact=None,
            artifact_sha256=None,
            timings_ns=_finish_timings(timings, total_started, self._clock),
            execution=None,
        )

    def execute(self, case: Mapping[str, Any], *,
                force_source_refusal: bool = False) -> ResidentQueryResult:
        if type(force_source_refusal) is not bool or force_source_refusal and (
                not self.advice_enabled or self.shadow):
            raise ValueError("invalid C25 query switches")
        total_started = self._clock()
        timings = {field: 0 for field in QUERY_TIMING_FIELDS}
        case_id = case.get("case_id") if isinstance(case, Mapping) else None
        n_vars = case.get("n_vars") if isinstance(case, Mapping) else None
        started = self._clock()
        try:
            if self._closed:
                raise ValueError("closed session")
            if self._successful_queries >= self.max_queries:
                raise ValueError("query limit")
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
                raise ValueError("input envelope")
            expression = expr_from_json(case["expression_v2"])
            frozen_bits = int(case["truth_bits_hex"], 16)
            if frozen_bits < 0 or frozen_bits.bit_length() > (1 << n_vars):
                raise ValueError("frozen truth bound")
            if reference_bits(expression, n_vars) != frozen_bits:
                raise ValueError("expression/truth mismatch")
            task = GF2DecompositionTask(n_vars, tuple(range(n_vars)))
            task.validate()
        except (KeyError, TypeError, ValueError) as exc:
            timings["input_validation_ns"] = max(1, self._clock() - started)
            return self._refused(
                case_id=case_id if type(case_id) is str else None,
                n_vars=n_vars if type(n_vars) is int else None,
                reason="query_refused:" + str(exc),
                force_source_refusal=force_source_refusal,
                timings=timings,
                total_started=total_started,
            )
        timings["input_validation_ns"] = max(1, self._clock() - started)

        started = self._clock()
        cache_hit = n_vars in self._compiled and not force_source_refusal
        if force_source_refusal:
            compiled = _RefusingResidentPortfolio(
                self.policy, task, advice_enabled=self.advice_enabled, shadow=self.shadow)
        elif cache_hit:
            compiled = self._compiled[n_vars]
        else:
            compiled = compile_source_portfolio(
                self.policy, task, advice_enabled=self.advice_enabled, shadow=self.shadow)
            self._compiled[n_vars] = compiled
        timings["compile_cache_ns"] = max(1, self._clock() - started)

        started = self._clock()
        execution = compiled.execute(case["expression_v2"])
        timings["execution_ns"] = max(1, self._clock() - started)

        started = self._clock()
        execution_document = execution.to_dict()
        verify_source_portfolio_execution(
            execution_document,
            case["expression_v2"],
            policy_sha256=self.policy["policy_sha256"],
        )
        json.dumps(execution_document, sort_keys=True, separators=(",", ":"), allow_nan=False)
        artifact_sha256 = canonical_sha256(execution.best_artifact)
        timings["serialization_verify_ns"] = max(1, self._clock() - started)
        query_index = self._successful_queries
        self._successful_queries += 1
        return ResidentQueryResult(
            session_id=self.session_id,
            query_index=query_index,
            case_id=case_id,
            n_vars=n_vars,
            status="ok",
            reason=execution.decision_reason,
            advice_enabled=self.advice_enabled,
            shadow=self.shadow,
            force_source_refusal=force_source_refusal,
            policy_sha256=self.policy["policy_sha256"],
            compile_cache_hit=cache_hit,
            requested_arm=execution.requested_arm,
            selected_arm=execution.selected_arm,
            fallback_used=execution.fallback_used,
            exact_check_passed=execution.exact_check_passed,
            best_artifact=execution.best_artifact,
            artifact_sha256=artifact_sha256,
            timings_ns=_finish_timings(timings, total_started, self._clock),
            execution=execution_document,
        )


def verify_resident_query_result(document: dict[str, Any], case: Mapping[str, Any],
                                 *, policy_sha256: str,
                                 required_best: dict[str, Any] | None | object = ...) -> None:
    expected = {field.name for field in ResidentQueryResult.__dataclass_fields__.values()}
    timings = document.get("timings_ns") if type(document) is dict else None
    if (
        type(document) is not dict
        or set(document) != expected
        or document.get("schema") != QUERY_SCHEMA
        or document.get("status") not in {"ok", "refused"}
        or document.get("policy_sha256") != policy_sha256
        or type(timings) is not dict
        or set(timings) != {*QUERY_TIMING_FIELDS, "task_total_ns"}
        or any(type(value) is not int or value < 0 for value in timings.values())
        or timings["task_total_ns"] != sum(timings[field] for field in QUERY_TIMING_FIELDS)
    ):
        raise ValueError("invalid C25 resident query record")
    if document["status"] == "refused":
        if (
            document.get("exact_check_passed") is not False
            or document.get("execution") is not None
            or document.get("best_artifact") is not None
            or document.get("selected_arm") is not None
            or document.get("compile_cache_hit") is not None
        ):
            raise ValueError("invalid C25 refusal record")
        return
    if (
        document.get("case_id") != case.get("case_id")
        or document.get("n_vars") != case.get("n_vars")
        or type(document.get("compile_cache_hit")) is not bool
        or document.get("exact_check_passed") is not True
        or document.get("artifact_sha256") != canonical_sha256(document.get("best_artifact"))
        or required_best is not ... and document.get("best_artifact") != required_best
        or type(document.get("execution")) is not dict
    ):
        raise ValueError("invalid C25 successful resident query")
    verify_source_portfolio_execution(
        document["execution"], case["expression_v2"], policy_sha256=policy_sha256)
