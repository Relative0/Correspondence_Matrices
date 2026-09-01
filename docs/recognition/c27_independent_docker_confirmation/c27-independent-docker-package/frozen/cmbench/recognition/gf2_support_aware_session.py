"""C27 fused resident session with a frozen transparent support rule."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping

from .gf2_decomposition import ExactGF2Artifact, analyze_exact_gf2, analyze_screened_exact_gf2
from .gf2_source_portfolio import SOURCE_PACKED_SCREENED, load_source_portfolio_policy
from .gf2_support_aware_policy import (
    TRUTH_SCREENED, load_support_aware_policy, select_support_arm,
)
from .gf2_task_dispatcher import EXHAUSTIVE, canonical_sha256
from .gf2_verified_context import VerifiedGF2RequestContext, build_verified_gf2_context

SESSION_SCHEMA = "crse-c27-support-aware-gf2-session/v1"
QUERY_SCHEMA = "crse-c27-support-aware-gf2-query/v1"
QUERY_TIMING_FIELDS = (
    "verified_context_ns",
    "plan_cache_ns",
    "exact_completion_ns",
    "final_delivery_verify_ns",
    "wrapper_ns",
)


@dataclass(frozen=True)
class SupportAwareWidthPlan:
    n_vars: int
    max_partitions: int
    materialize_budget: int
    requested_arm: str


@dataclass(frozen=True)
class SupportAwareQueryResult:
    session_id: str
    query_index: int
    case_id: str | None
    n_vars: int | None
    status: str
    reason: str
    advice_enabled: bool
    force_selected_refusal: bool
    c27_policy_sha256: str
    c22_policy_sha256: str
    context_sha256: str | None
    expression_sha256: str | None
    truth_sha256: str | None
    plan_cache_hit: bool | None
    requested_arm: str | None
    selected_arm: str | None
    fallback_used: bool | None
    exact_check_passed: bool
    best_artifact: dict[str, Any] | None
    artifact_sha256: str | None
    partitions_tested: int | None
    descriptors_screened: int | None
    artifacts_materialized: int | None
    timings_ns: dict[str, int]
    schema: str = QUERY_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _finish(timings: dict[str, int], started: int,
            clock: Callable[[], int]) -> dict[str, int]:
    elapsed = max(1, clock() - started)
    charged = sum(timings[field] for field in QUERY_TIMING_FIELDS if field != "wrapper_ns")
    timings["wrapper_ns"] = max(0, elapsed - charged)
    return {**timings, "task_total_ns": sum(timings.values())}


class SupportAwareGF2Session:
    def __init__(self, session_id: str, c27_policy_path: Path, c22_policy_path: Path, *,
                 advice_enabled: bool = True, max_queries: int = 32,
                 clock: Callable[[], int] = time.perf_counter_ns):
        if (
            type(session_id) is not str or not session_id or len(session_id) > 256
            or type(advice_enabled) is not bool
            or type(max_queries) is not int or not 1 <= max_queries <= 256
        ):
            raise ValueError("invalid C27 support-aware session configuration")
        setup_started = clock()
        c27_policy = load_support_aware_policy(c27_policy_path)
        c27_loaded = max(1, clock() - setup_started)
        started = clock()
        c22_policy = load_source_portfolio_policy(c22_policy_path)
        c22_loaded = max(1, clock() - started)
        if (
            c27_policy["large_support_arm"] != c22_policy["selected_arm"]
            or c27_policy["large_support_arm"] != SOURCE_PACKED_SCREENED
            or c27_policy["max_partitions"] != c22_policy["max_partitions"]
            or c27_policy["materialize_budget"] != c22_policy["materialize_budget"]
        ):
            raise ValueError("C27/C22 frozen policy mismatch")
        self.session_id = session_id
        self.c27_policy = json.loads(json.dumps(c27_policy, allow_nan=False))
        self.c22_policy = json.loads(json.dumps(c22_policy, allow_nan=False))
        self.advice_enabled = advice_enabled
        self.max_queries = max_queries
        self._clock = clock
        self._plans: dict[int, SupportAwareWidthPlan] = {}
        self._successful_queries = 0
        self._refused_queries = 0
        self._closed = False
        self.setup_timings_ns = {
            "c27_policy_load_validate_ns": c27_loaded,
            "c22_policy_load_validate_ns": c22_loaded,
            "session_initialize_ns": max(
                1, clock() - setup_started - c27_loaded - c22_loaded),
        }
        self.setup_timings_ns["setup_total_ns"] = sum(self.setup_timings_ns.values())

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": SESSION_SCHEMA,
            "session_id": self.session_id,
            "c27_policy_sha256": self.c27_policy["policy_sha256"],
            "c22_policy_sha256": self.c22_policy["policy_sha256"],
            "advice_enabled": self.advice_enabled,
            "max_queries": self.max_queries,
            "successful_queries": self._successful_queries,
            "refused_queries": self._refused_queries,
            "compiled_widths": sorted(self._plans),
            "compiled_arms": {
                str(width): self._plans[width].requested_arm for width in sorted(self._plans)
            },
            "closed": self._closed,
            "setup_timings_ns": dict(self.setup_timings_ns),
        }

    def close(self) -> dict[str, Any]:
        self._plans.clear()
        self._closed = True
        return self.snapshot()

    def _refused(self, *, case_id: str | None, n_vars: int | None, reason: str,
                 force_selected_refusal: bool, timings: dict[str, int],
                 total_started: int) -> SupportAwareQueryResult:
        self._refused_queries += 1
        return SupportAwareQueryResult(
            session_id=self.session_id,
            query_index=self._successful_queries,
            case_id=case_id,
            n_vars=n_vars,
            status="refused",
            reason=reason,
            advice_enabled=self.advice_enabled,
            force_selected_refusal=force_selected_refusal,
            c27_policy_sha256=self.c27_policy["policy_sha256"],
            c22_policy_sha256=self.c22_policy["policy_sha256"],
            context_sha256=None,
            expression_sha256=None,
            truth_sha256=None,
            plan_cache_hit=None,
            requested_arm=None,
            selected_arm=None,
            fallback_used=None,
            exact_check_passed=False,
            best_artifact=None,
            artifact_sha256=None,
            partitions_tested=None,
            descriptors_screened=None,
            artifacts_materialized=None,
            timings_ns=_finish(timings, total_started, self._clock),
        )

    def execute(self, case: Mapping[str, Any], *,
                force_selected_refusal: bool = False) -> SupportAwareQueryResult:
        if type(force_selected_refusal) is not bool or (
                force_selected_refusal and not self.advice_enabled):
            raise ValueError("invalid C27 query switches")
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
            requested = select_support_arm(
                self.c27_policy, n_vars, advice_enabled=self.advice_enabled)
            context = build_verified_gf2_context(
                case,
                require_source_packed=(
                    requested == SOURCE_PACKED_SCREENED and not force_selected_refusal),
            )
        except (KeyError, TypeError, ValueError) as exc:
            timings["verified_context_ns"] = max(1, self._clock() - started)
            return self._refused(
                case_id=case_id if type(case_id) is str else None,
                n_vars=n_vars if type(n_vars) is int else None,
                reason="query_refused:" + str(exc),
                force_selected_refusal=force_selected_refusal,
                timings=timings,
                total_started=total_started,
            )
        timings["verified_context_ns"] = max(1, self._clock() - started)

        started = self._clock()
        cache_hit = context.n_vars in self._plans
        if cache_hit:
            plan = self._plans[context.n_vars]
        else:
            plan = SupportAwareWidthPlan(
                n_vars=context.n_vars,
                max_partitions=self.c27_policy["max_partitions"],
                materialize_budget=self.c27_policy["materialize_budget"],
                requested_arm=requested,
            )
            self._plans[context.n_vars] = plan
        if plan.requested_arm != requested:
            raise RuntimeError("C27 cached plan arm mismatch")
        timings["plan_cache_ns"] = max(1, self._clock() - started)

        started = self._clock()
        fallback_used = force_selected_refusal
        if force_selected_refusal or requested == EXHAUSTIVE:
            analysis = analyze_exact_gf2(
                context.truth_bits, context.n_vars, max_partitions=plan.max_partitions)
            selected = EXHAUSTIVE
            reason = ("selected_path_refused_exact_fallback" if force_selected_refusal
                      else "advice_globally_disabled")
        elif requested in {TRUTH_SCREENED, SOURCE_PACKED_SCREENED}:
            if requested == SOURCE_PACKED_SCREENED and (
                    not context.source_packed_verified or context.packed_polynomial is None):
                raise RuntimeError("C27 packed selected context is incomplete")
            if requested == TRUTH_SCREENED and context.source_packed_verified:
                raise RuntimeError("C27 tiny truth path unexpectedly built packed source")
            analysis = analyze_screened_exact_gf2(
                context.truth_bits,
                context.n_vars,
                max_partitions=plan.max_partitions,
                materialize_budget=plan.materialize_budget,
            )
            selected = requested
            reason = ("transparent_tiny_support_truth_screened" if requested == TRUTH_SCREENED
                      else "transparent_large_support_source_packed")
        else:
            raise RuntimeError("C27 unknown frozen arm")
        if analysis.source_sha256 != context.truth_sha256:
            raise RuntimeError("C27 exact completion source identity mismatch")
        best = analysis.best.to_dict() if analysis.best else None
        timings["exact_completion_ns"] = max(1, self._clock() - started)

        started = self._clock()
        if best is not None and ExactGF2Artifact.from_dict(best).reconstruct() != context.truth_bits:
            raise RuntimeError("C27 final artifact reconstruction failed")
        artifact_sha256 = canonical_sha256(best)
        json.dumps({
            "context_sha256": context.context_sha256,
            "c27_policy_sha256": self.c27_policy["policy_sha256"],
            "c22_policy_sha256": self.c22_policy["policy_sha256"],
            "selected_arm": selected,
            "artifact_sha256": artifact_sha256,
        }, sort_keys=True, separators=(",", ":"), allow_nan=False)
        timings["final_delivery_verify_ns"] = max(1, self._clock() - started)
        query_index = self._successful_queries
        self._successful_queries += 1
        return SupportAwareQueryResult(
            session_id=self.session_id,
            query_index=query_index,
            case_id=context.case_id,
            n_vars=context.n_vars,
            status="ok",
            reason=reason,
            advice_enabled=self.advice_enabled,
            force_selected_refusal=force_selected_refusal,
            c27_policy_sha256=self.c27_policy["policy_sha256"],
            c22_policy_sha256=self.c22_policy["policy_sha256"],
            context_sha256=context.context_sha256,
            expression_sha256=context.expression_sha256,
            truth_sha256=context.truth_sha256,
            plan_cache_hit=cache_hit,
            requested_arm=requested,
            selected_arm=selected,
            fallback_used=fallback_used,
            exact_check_passed=True,
            best_artifact=best,
            artifact_sha256=artifact_sha256,
            partitions_tested=analysis.partitions_tested,
            descriptors_screened=analysis.descriptors_screened,
            artifacts_materialized=analysis.artifacts_materialized,
            timings_ns=_finish(timings, total_started, self._clock),
        )


def verify_support_aware_query_result(
    document: dict[str, Any], context: VerifiedGF2RequestContext | None, *,
    c27_policy_sha256: str, c22_policy_sha256: str,
    required_best: dict[str, Any] | None | object = ...,
    reconstruct_artifact: bool = True,
) -> None:
    expected = {field.name for field in SupportAwareQueryResult.__dataclass_fields__.values()}
    timings = document.get("timings_ns") if type(document) is dict else None
    if (
        type(document) is not dict or set(document) != expected
        or document.get("schema") != QUERY_SCHEMA
        or document.get("status") not in {"ok", "refused"}
        or document.get("c27_policy_sha256") != c27_policy_sha256
        or document.get("c22_policy_sha256") != c22_policy_sha256
        or type(timings) is not dict
        or set(timings) != {*QUERY_TIMING_FIELDS, "task_total_ns"}
        or any(type(value) is not int or value < 0 for value in timings.values())
        or timings["task_total_ns"] != sum(timings[field] for field in QUERY_TIMING_FIELDS)
    ):
        raise ValueError("invalid C27 support-aware query record")
    if document["status"] == "refused":
        if context is not None or any(document.get(field) is not None for field in (
            "context_sha256", "selected_arm", "best_artifact", "artifact_sha256",
            "plan_cache_hit", "partitions_tested", "descriptors_screened",
            "artifacts_materialized",
        )) or document.get("exact_check_passed") is not False:
            raise ValueError("invalid C27 support-aware refusal")
        return
    if context is None:
        raise ValueError("C27 successful query requires verified context")
    best = document.get("best_artifact")
    if (
        document.get("case_id") != context.case_id
        or document.get("n_vars") != context.n_vars
        or document.get("context_sha256") != context.context_sha256
        or document.get("expression_sha256") != context.expression_sha256
        or document.get("truth_sha256") != context.truth_sha256
        or type(document.get("plan_cache_hit")) is not bool
        or document.get("exact_check_passed") is not True
        or document.get("artifact_sha256") != canonical_sha256(best)
        or required_best is not ... and best != required_best
    ):
        raise ValueError("invalid C27 support-aware query identity")
    if reconstruct_artifact and best is not None:
        if ExactGF2Artifact.from_dict(best).reconstruct() != context.truth_bits:
            raise ValueError("C27 support-aware artifact replay mismatch")
