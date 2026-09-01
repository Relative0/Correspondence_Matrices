"""Baseline-serving shadow boundary for the frozen C30 prepared policy.

The boundary is deliberately one-way: the exact screened baseline is the only
servable result.  An opt-in prepared-policy candidate may be observed, timed,
and compared, but it cannot affect the delivered artifact or write/promote any
state.  Candidate refusals, exceptions, and exact-artifact divergences are
contained as shadow evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import time
from typing import Any, Callable, Mapping

from .gf2_decomposition import ExactGF2Artifact, analyze_screened_exact_gf2
from .gf2_prepared_support_context import (
    PreparedSupportPolicyContext,
    verify_prepared_policy_sources,
)
from .gf2_source_portfolio import SOURCE_PACKED_SCREENED
from .gf2_support_aware_session import (
    SupportAwareGF2Session,
    SupportAwareQueryResult,
    verify_support_aware_query_result,
)
from .gf2_task_dispatcher import SCREENED
from .gf2_verified_context import build_verified_gf2_context


SHADOW_BOUNDARY_SCHEMA = "crse-c32-prepared-policy-shadow-boundary/v1"
SHADOW_RESULT_SCHEMA = "crse-c32-prepared-policy-shadow-result/v1"
TIMING_FIELDS = (
    "baseline_ns",
    "shadow_candidate_ns",
    "comparison_ns",
    "wrapper_ns",
)
CandidateExecutor = Callable[
    [SupportAwareGF2Session, Mapping[str, Any]], SupportAwareQueryResult
]


def _delivery_sha256(best: dict[str, Any] | None) -> str:
    document = {
        "schema": "cm-comparative-exact-gf2-delivery/v1",
        "best_artifact": best,
    }
    raw = json.dumps(
        document, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class PreparedPolicyShadowResult:
    boundary_id: str
    request_index: int
    case_id: str
    n_vars: int
    status: str
    shadow_enabled: bool
    served_output_source: str
    served_selected_arm: str
    served_best_artifact: dict[str, Any] | None
    served_artifact_sha256: str
    baseline_context_sha256: str
    baseline_exact_check_passed: bool
    candidate_status: str
    candidate_selected_arm: str | None
    candidate_best_artifact: dict[str, Any] | None
    candidate_artifact_sha256: str | None
    candidate_context_sha256: str | None
    candidate_best_identity_match: bool | None
    candidate_error_type: str | None
    candidate_refusal_reason: str | None
    shadow_divergence_detected: bool
    shadow_failure_contained: bool
    candidate_observed_only: bool
    production_write: bool
    shadow_promotion: bool
    production_promotion: bool
    timings_ns: dict[str, int]
    schema: str = SHADOW_RESULT_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PreparedPolicyShadowBoundary:
    """Serve exact screened output while optionally observing C30 candidate work."""

    def __init__(
        self,
        boundary_id: str,
        prepared_context: PreparedSupportPolicyContext,
        *,
        required_prepared_context_sha256: str,
        shadow_enabled: bool = False,
        max_queries: int = 256,
        max_partitions: int = 64,
        materialize_budget: int = 4,
        candidate_executor: CandidateExecutor | None = None,
        clock: Callable[[], int] = time.perf_counter_ns,
    ):
        if (
            type(boundary_id) is not str
            or not boundary_id
            or len(boundary_id) > 256
            or type(prepared_context) is not PreparedSupportPolicyContext
            or required_prepared_context_sha256 != prepared_context.context_sha256
            or type(shadow_enabled) is not bool
            or type(max_queries) is not int
            or not 1 <= max_queries <= 4096
            or type(max_partitions) is not int
            or not 1 <= max_partitions <= 64
            or type(materialize_budget) is not int
            or not 1 <= materialize_budget <= 4
            or candidate_executor is not None and not callable(candidate_executor)
        ):
            raise ValueError("invalid C32 shadow boundary configuration")
        verify_prepared_policy_sources(prepared_context)
        self.boundary_id = boundary_id
        self.prepared_context = prepared_context
        self.shadow_enabled = shadow_enabled
        self.max_queries = max_queries
        self.max_partitions = max_partitions
        self.materialize_budget = materialize_budget
        self._clock = clock
        self._candidate_executor = candidate_executor or (
            lambda session, case: session.execute(case)
        )
        self._candidate_session = (
            SupportAwareGF2Session.from_prepared_context(
                boundary_id + "-candidate",
                prepared_context,
                max_queries=max_queries,
                clock=clock,
            )
            if shadow_enabled else None
        )
        self._requests = 0
        self._candidate_observations = 0
        self._candidate_refusals = 0
        self._candidate_errors = 0
        self._divergences = 0
        self._closed = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": SHADOW_BOUNDARY_SCHEMA,
            "boundary_id": self.boundary_id,
            "prepared_context_sha256": self.prepared_context.context_sha256,
            "shadow_enabled": self.shadow_enabled,
            "max_queries": self.max_queries,
            "max_partitions": self.max_partitions,
            "materialize_budget": self.materialize_budget,
            "requests": self._requests,
            "candidate_observations": self._candidate_observations,
            "candidate_refusals": self._candidate_refusals,
            "candidate_errors": self._candidate_errors,
            "divergences": self._divergences,
            "served_candidate_results": 0,
            "production_writes": 0,
            "shadow_promotions": 0,
            "production_promotions": 0,
            "closed": self._closed,
        }

    def audit_sources(self) -> None:
        verify_prepared_policy_sources(self.prepared_context)

    def close(self) -> dict[str, Any]:
        if not self._closed:
            if self._candidate_session is not None:
                self._candidate_session.close()
            self.audit_sources()
            self._closed = True
        return self.snapshot()

    def execute(self, case: Mapping[str, Any]) -> PreparedPolicyShadowResult:
        if self._closed:
            raise ValueError("closed C32 shadow boundary")
        if self._requests >= self.max_queries:
            raise ValueError("C32 shadow boundary query limit")
        total_started = self._clock()
        timings = {field: 0 for field in TIMING_FIELDS}

        started = self._clock()
        baseline_context = build_verified_gf2_context(case, require_source_packed=False)
        analysis = analyze_screened_exact_gf2(
            baseline_context.truth_bits,
            baseline_context.n_vars,
            max_partitions=self.max_partitions,
            materialize_budget=self.materialize_budget,
        )
        if analysis.source_sha256 != baseline_context.truth_sha256:
            raise RuntimeError("C32 baseline source identity mismatch")
        served_best = analysis.best.to_dict() if analysis.best else None
        if (
            served_best is not None
            and ExactGF2Artifact.from_dict(served_best).reconstruct()
            != baseline_context.truth_bits
        ):
            raise RuntimeError("C32 baseline reconstruction failed")
        served_digest = _delivery_sha256(served_best)
        timings["baseline_ns"] = max(1, self._clock() - started)

        candidate_status = "disabled"
        candidate_selected_arm = None
        candidate_best = None
        candidate_digest = None
        candidate_context_sha256 = None
        candidate_match = None
        candidate_error_type = None
        candidate_refusal_reason = None
        divergence = False
        contained = False

        if self.shadow_enabled:
            started = self._clock()
            try:
                if self._candidate_session is None:
                    raise RuntimeError("C32 candidate session missing")
                candidate = self._candidate_executor(self._candidate_session, case)
                if type(candidate) is not SupportAwareQueryResult:
                    raise TypeError("C32 candidate executor returned invalid result")
                candidate_document = candidate.to_dict()
                if candidate.status == "refused":
                    verify_support_aware_query_result(
                        candidate_document,
                        None,
                        c27_policy_sha256=self.prepared_context.c27_policy_sha256,
                        c22_policy_sha256=self.prepared_context.c22_policy_sha256,
                    )
                    candidate_status = "refused"
                    candidate_refusal_reason = candidate.reason
                    contained = True
                    self._candidate_refusals += 1
                else:
                    requested_packed = candidate.requested_arm == SOURCE_PACKED_SCREENED
                    candidate_context = build_verified_gf2_context(
                        case, require_source_packed=requested_packed)
                    verify_support_aware_query_result(
                        candidate_document,
                        candidate_context,
                        c27_policy_sha256=self.prepared_context.c27_policy_sha256,
                        c22_policy_sha256=self.prepared_context.c22_policy_sha256,
                    )
                    candidate_status = "observed"
                    candidate_selected_arm = candidate.selected_arm
                    candidate_best = candidate.best_artifact
                    candidate_digest = _delivery_sha256(candidate_best)
                    candidate_context_sha256 = candidate.context_sha256
                    self._candidate_observations += 1
            except Exception as exc:
                candidate_status = "error"
                candidate_error_type = type(exc).__name__
                contained = True
                self._candidate_errors += 1
            timings["shadow_candidate_ns"] = max(1, self._clock() - started)

            started = self._clock()
            if candidate_status == "observed":
                candidate_match = (
                    candidate_best == served_best and candidate_digest == served_digest
                )
                divergence = not candidate_match
                if divergence:
                    contained = True
                    self._divergences += 1
            timings["comparison_ns"] = max(1, self._clock() - started)

        request_index = self._requests
        self._requests += 1
        elapsed = max(1, self._clock() - total_started)
        charged = sum(timings[field] for field in TIMING_FIELDS if field != "wrapper_ns")
        timings["wrapper_ns"] = max(0, elapsed - charged)
        timings["task_total_ns"] = sum(timings.values())
        return PreparedPolicyShadowResult(
            boundary_id=self.boundary_id,
            request_index=request_index,
            case_id=baseline_context.case_id,
            n_vars=baseline_context.n_vars,
            status="served_baseline",
            shadow_enabled=self.shadow_enabled,
            served_output_source="exact_screened_baseline",
            served_selected_arm=SCREENED,
            served_best_artifact=served_best,
            served_artifact_sha256=served_digest,
            baseline_context_sha256=baseline_context.context_sha256,
            baseline_exact_check_passed=True,
            candidate_status=candidate_status,
            candidate_selected_arm=candidate_selected_arm,
            candidate_best_artifact=candidate_best,
            candidate_artifact_sha256=candidate_digest,
            candidate_context_sha256=candidate_context_sha256,
            candidate_best_identity_match=candidate_match,
            candidate_error_type=candidate_error_type,
            candidate_refusal_reason=candidate_refusal_reason,
            shadow_divergence_detected=divergence,
            shadow_failure_contained=contained,
            candidate_observed_only=True,
            production_write=False,
            shadow_promotion=False,
            production_promotion=False,
            timings_ns=timings,
        )


def verify_prepared_policy_shadow_result(
    document: dict[str, Any],
    case: Mapping[str, Any],
    *,
    required_best: dict[str, Any] | None,
) -> None:
    fields = {field.name for field in PreparedPolicyShadowResult.__dataclass_fields__.values()}
    timings = document.get("timings_ns") if type(document) is dict else None
    context = build_verified_gf2_context(case, require_source_packed=False)
    if (
        type(document) is not dict
        or set(document) != fields
        or document.get("schema") != SHADOW_RESULT_SCHEMA
        or document.get("status") != "served_baseline"
        or document.get("case_id") != context.case_id
        or document.get("n_vars") != context.n_vars
        or document.get("served_output_source") != "exact_screened_baseline"
        or document.get("served_selected_arm") != SCREENED
        or document.get("served_best_artifact") != required_best
        or document.get("served_artifact_sha256") != _delivery_sha256(required_best)
        or document.get("baseline_context_sha256") != context.context_sha256
        or document.get("baseline_exact_check_passed") is not True
        or document.get("candidate_observed_only") is not True
        or document.get("production_write") is not False
        or document.get("shadow_promotion") is not False
        or document.get("production_promotion") is not False
        or type(timings) is not dict
        or set(timings) != {*TIMING_FIELDS, "task_total_ns"}
        or any(type(value) is not int or value < 0 for value in timings.values())
        or timings["baseline_ns"] < 1
        or timings["task_total_ns"] != sum(timings[field] for field in TIMING_FIELDS)
    ):
        raise ValueError("invalid C32 served-baseline shadow result")
    if required_best is not None:
        if ExactGF2Artifact.from_dict(required_best).reconstruct() != context.truth_bits:
            raise ValueError("C32 served artifact does not reconstruct")

    shadow_enabled = document["shadow_enabled"]
    status = document["candidate_status"]
    if not shadow_enabled:
        if (
            status != "disabled"
            or timings["shadow_candidate_ns"] != 0
            or timings["comparison_ns"] != 0
            or any(document.get(field) is not None for field in (
                "candidate_selected_arm", "candidate_best_artifact",
                "candidate_artifact_sha256", "candidate_context_sha256",
                "candidate_best_identity_match", "candidate_error_type",
                "candidate_refusal_reason",
            ))
            or document.get("shadow_divergence_detected") is not False
            or document.get("shadow_failure_contained") is not False
        ):
            raise ValueError("invalid C32 shadow-disabled result")
        return

    if timings["shadow_candidate_ns"] < 1 or timings["comparison_ns"] < 1:
        raise ValueError("invalid C32 shadow timing")
    if status == "observed":
        candidate_best = document.get("candidate_best_artifact")
        match = candidate_best == required_best
        if (
            document.get("candidate_selected_arm") is None
            or document.get("candidate_artifact_sha256") != _delivery_sha256(candidate_best)
            or document.get("candidate_context_sha256") is None
            or document.get("candidate_best_identity_match") is not match
            or document.get("shadow_divergence_detected") is match
            or document.get("shadow_failure_contained") is match
            or document.get("candidate_error_type") is not None
            or document.get("candidate_refusal_reason") is not None
        ):
            raise ValueError("invalid C32 observed candidate result")
    elif status == "error":
        if (
            document.get("candidate_error_type") is None
            or document.get("shadow_failure_contained") is not True
            or document.get("shadow_divergence_detected") is not False
            or any(document.get(field) is not None for field in (
                "candidate_selected_arm", "candidate_best_artifact",
                "candidate_artifact_sha256", "candidate_context_sha256",
                "candidate_best_identity_match", "candidate_refusal_reason",
            ))
        ):
            raise ValueError("invalid C32 contained candidate error")
    elif status == "refused":
        if (
            document.get("candidate_refusal_reason") is None
            or document.get("shadow_failure_contained") is not True
            or document.get("shadow_divergence_detected") is not False
            or any(document.get(field) is not None for field in (
                "candidate_selected_arm", "candidate_best_artifact",
                "candidate_artifact_sha256", "candidate_context_sha256",
                "candidate_best_identity_match", "candidate_error_type",
            ))
        ):
            raise ValueError("invalid C32 contained candidate refusal")
    else:
        raise ValueError("invalid C32 candidate status")
