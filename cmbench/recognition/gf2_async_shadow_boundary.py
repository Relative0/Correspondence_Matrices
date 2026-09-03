"""Bounded asynchronous shadowing for the frozen prepared GF(2) policy.

C33 separates serving from observation with an explicit delivery acknowledgement.
``execute`` always returns the exact screened baseline and, when sampled, stages an
immutable hash-bound envelope.  Candidate work cannot begin until the caller invokes
``acknowledge_delivery`` after delivering that baseline.  Queue saturation, candidate
failures, and divergences are observational only and cannot change the served result.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from queue import Empty, Full, Queue
from threading import Lock, Thread
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


ASYNC_BOUNDARY_SCHEMA = "crse-c33-prepared-policy-async-shadow-boundary/v1"
ASYNC_RESULT_SCHEMA = "crse-c33-prepared-policy-async-shadow-result/v1"
ASYNC_OBSERVATION_SCHEMA = "crse-c33-prepared-policy-async-observation/v1"
ASYNC_ENVELOPE_SCHEMA = "crse-c33-prepared-policy-async-envelope/v1"
RESULT_TIMING_FIELDS = (
    "baseline_ns",
    "envelope_copy_ns",
    "stage_ns",
    "wrapper_ns",
)
OBSERVATION_TIMING_FIELDS = (
    "queue_wait_ns",
    "candidate_ns",
    "comparison_ns",
)
CandidateExecutor = Callable[
    [SupportAwareGF2Session, Mapping[str, Any]], SupportAwareQueryResult
]
_STOP = object()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def delivery_sha256(best: dict[str, Any] | None) -> str:
    return _sha256_bytes(_canonical_bytes({
        "schema": "cm-comparative-exact-gf2-delivery/v1",
        "best_artifact": best,
    }))


def _shadow_case_payload(case: Mapping[str, Any]) -> dict[str, Any]:
    """Copy only fields required to replay and verify the exact candidate."""
    return {
        "case_id": case["case_id"],
        "n_vars": case["n_vars"],
        "expression_v2": case["expression_v2"],
        "truth_bits_hex": case["truth_bits_hex"],
    }


def _envelope_body(
    *,
    boundary_id: str,
    request_index: int,
    case_sha256: str,
    served_artifact_sha256: str,
    baseline_context_sha256: str,
    prepared_context_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": ASYNC_ENVELOPE_SCHEMA,
        "boundary_id": boundary_id,
        "request_index": request_index,
        "case_sha256": case_sha256,
        "served_artifact_sha256": served_artifact_sha256,
        "baseline_context_sha256": baseline_context_sha256,
        "prepared_context_sha256": prepared_context_sha256,
    }


@dataclass(frozen=True)
class _AsyncEnvelope:
    boundary_id: str
    request_index: int
    case_id: str
    case_json: bytes
    case_sha256: str
    served_artifact_sha256: str
    baseline_context_sha256: str
    prepared_context_sha256: str
    envelope_sha256: str
    staged_ns: int


@dataclass(frozen=True)
class AsyncShadowServeResult:
    boundary_id: str
    request_index: int
    case_id: str
    n_vars: int
    status: str
    shadow_enabled: bool
    sample_every: int
    sample_eligible: bool
    shadow_disposition: str
    shadow_envelope_sha256: str | None
    queue_depth_after: int
    served_output_source: str
    served_selected_arm: str
    served_best_artifact: dict[str, Any] | None
    served_artifact_sha256: str
    baseline_context_sha256: str
    baseline_exact_check_passed: bool
    candidate_observed_only: bool
    delivery_ack_required_before_candidate: bool
    production_write: bool
    shadow_promotion: bool
    production_promotion: bool
    timings_ns: dict[str, int]
    schema: str = ASYNC_RESULT_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AsyncShadowObservation:
    boundary_id: str
    request_index: int
    case_id: str
    envelope_sha256: str
    case_sha256: str
    baseline_context_sha256: str
    expected_artifact_sha256: str
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
    schema: str = ASYNC_OBSERVATION_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PreparedPolicyAsyncShadowBoundary:
    """Serve exact results and release sampled observations only after delivery ack."""

    def __init__(
        self,
        boundary_id: str,
        prepared_context: PreparedSupportPolicyContext,
        *,
        required_prepared_context_sha256: str,
        shadow_enabled: bool = False,
        sample_every: int = 1,
        queue_capacity: int = 64,
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
            or type(sample_every) is not int
            or not 1 <= sample_every <= 1024
            or type(queue_capacity) is not int
            or not 1 <= queue_capacity <= 4096
            or type(max_queries) is not int
            or not 1 <= max_queries <= 4096
            or type(max_partitions) is not int
            or not 1 <= max_partitions <= 64
            or type(materialize_budget) is not int
            or not 1 <= materialize_budget <= 4
            or candidate_executor is not None and not callable(candidate_executor)
        ):
            raise ValueError("invalid C33 asynchronous shadow configuration")
        verify_prepared_policy_sources(prepared_context)
        self.boundary_id = boundary_id
        self.prepared_context = prepared_context
        self.shadow_enabled = shadow_enabled
        self.sample_every = sample_every
        self.queue_capacity = queue_capacity
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
        self._queue: Queue[object] = Queue(maxsize=queue_capacity)
        self._lock = Lock()
        self._staged: dict[str, _AsyncEnvelope] = {}
        self._observations: list[AsyncShadowObservation] = []
        self._requests = 0
        self._sampled_in = 0
        self._sampled_out = 0
        self._queue_full_drops = 0
        self._acknowledged = 0
        self._active = 0
        self._candidate_observations = 0
        self._candidate_refusals = 0
        self._candidate_errors = 0
        self._divergences = 0
        self._worker: Thread | None = None
        self._worker_started = False
        self._worker_stopped = False
        self._accepting = True
        self._closed = False
        if shadow_enabled:
            self._start_worker()

    def _start_worker(self) -> None:
        with self._lock:
            if self._worker_started:
                return
            self._worker_started = True
            self._worker = Thread(
                target=self._worker_loop,
                name=f"{self.boundary_id}-observer",
                daemon=True,
            )
            worker = self._worker
        worker.start()

    def _capacity_used(self) -> int:
        return len(self._staged) + self._queue.qsize() + self._active

    def _make_envelope(
        self,
        *,
        request_index: int,
        case: Mapping[str, Any],
        served_artifact_sha256: str,
        baseline_context_sha256: str,
    ) -> _AsyncEnvelope:
        case_json = _canonical_bytes(_shadow_case_payload(case))
        case_digest = _sha256_bytes(case_json)
        body = _envelope_body(
            boundary_id=self.boundary_id,
            request_index=request_index,
            case_sha256=case_digest,
            served_artifact_sha256=served_artifact_sha256,
            baseline_context_sha256=baseline_context_sha256,
            prepared_context_sha256=self.prepared_context.context_sha256,
        )
        return _AsyncEnvelope(
            boundary_id=self.boundary_id,
            request_index=request_index,
            case_id=str(case["case_id"]),
            case_json=case_json,
            case_sha256=case_digest,
            served_artifact_sha256=served_artifact_sha256,
            baseline_context_sha256=baseline_context_sha256,
            prepared_context_sha256=self.prepared_context.context_sha256,
            envelope_sha256=_sha256_bytes(_canonical_bytes(body)),
            staged_ns=self._clock(),
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = {
                "schema": ASYNC_BOUNDARY_SCHEMA,
                "boundary_id": self.boundary_id,
                "prepared_context_sha256": self.prepared_context.context_sha256,
                "shadow_enabled": self.shadow_enabled,
                "sample_every": self.sample_every,
                "queue_capacity": self.queue_capacity,
                "max_queries": self.max_queries,
                "requests": self._requests,
                "sampled_in": self._sampled_in,
                "sampled_out": self._sampled_out,
                "queue_full_drops": self._queue_full_drops,
                "acknowledged": self._acknowledged,
                "candidate_observations": self._candidate_observations,
                "candidate_refusals": self._candidate_refusals,
                "candidate_errors": self._candidate_errors,
                "divergences": self._divergences,
                "observations_recorded": len(self._observations),
                "pending_staged": len(self._staged),
                "worker_active": self._active,
                "worker_started": self._worker_started,
                "worker_stopped": self._worker_stopped,
                "accepting": self._accepting,
                "closed": self._closed,
                "served_candidate_results": 0,
                "production_writes": 0,
                "shadow_promotions": 0,
                "production_promotions": 0,
            }
        state["pending_ready"] = self._queue.qsize()
        return state

    def audit_sources(self) -> None:
        verify_prepared_policy_sources(self.prepared_context)

    def observations(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            ordered = sorted(self._observations, key=lambda row: row.request_index)
            return tuple(row.to_dict() for row in ordered)

    def execute(self, case: Mapping[str, Any]) -> AsyncShadowServeResult:
        with self._lock:
            if not self._accepting or self._closed:
                raise ValueError("closed C33 asynchronous shadow boundary")
            if self._requests >= self.max_queries:
                raise ValueError("C33 asynchronous shadow query limit")
            request_index = self._requests
            self._requests += 1
        total_started = self._clock()
        timings = {field: 0 for field in RESULT_TIMING_FIELDS}

        started = self._clock()
        baseline_context = build_verified_gf2_context(case, require_source_packed=False)
        analysis = analyze_screened_exact_gf2(
            baseline_context.truth_bits,
            baseline_context.n_vars,
            max_partitions=self.max_partitions,
            materialize_budget=self.materialize_budget,
        )
        if analysis.source_sha256 != baseline_context.truth_sha256:
            raise RuntimeError("C33 baseline source identity mismatch")
        served_best = analysis.best.to_dict() if analysis.best else None
        if (
            served_best is not None
            and ExactGF2Artifact.from_dict(served_best).reconstruct()
            != baseline_context.truth_bits
        ):
            raise RuntimeError("C33 baseline reconstruction failed")
        served_digest = delivery_sha256(served_best)
        timings["baseline_ns"] = max(1, self._clock() - started)

        eligible = self.shadow_enabled and request_index % self.sample_every == 0
        disposition = "disabled" if not self.shadow_enabled else "sampled_out"
        envelope_digest = None
        queue_depth = 0
        if eligible:
            started = self._clock()
            envelope = self._make_envelope(
                request_index=request_index,
                case=case,
                served_artifact_sha256=served_digest,
                baseline_context_sha256=baseline_context.context_sha256,
            )
            timings["envelope_copy_ns"] = max(1, self._clock() - started)
            envelope_digest = envelope.envelope_sha256
            started = self._clock()
            with self._lock:
                if self._capacity_used() >= self.queue_capacity:
                    self._queue_full_drops += 1
                    disposition = "queue_full"
                else:
                    self._staged[envelope.envelope_sha256] = envelope
                    self._sampled_in += 1
                    disposition = "staged_pending_delivery_ack"
                queue_depth = self._capacity_used()
            timings["stage_ns"] = max(1, self._clock() - started)
        elif self.shadow_enabled:
            with self._lock:
                self._sampled_out += 1
                queue_depth = self._capacity_used()

        elapsed = max(1, self._clock() - total_started)
        charged = sum(
            timings[field] for field in RESULT_TIMING_FIELDS if field != "wrapper_ns")
        timings["wrapper_ns"] = max(0, elapsed - charged)
        timings["request_total_ns"] = sum(timings.values())
        return AsyncShadowServeResult(
            boundary_id=self.boundary_id,
            request_index=request_index,
            case_id=baseline_context.case_id,
            n_vars=baseline_context.n_vars,
            status="served_baseline",
            shadow_enabled=self.shadow_enabled,
            sample_every=self.sample_every,
            sample_eligible=eligible,
            shadow_disposition=disposition,
            shadow_envelope_sha256=envelope_digest,
            queue_depth_after=queue_depth,
            served_output_source="exact_screened_baseline",
            served_selected_arm=SCREENED,
            served_best_artifact=served_best,
            served_artifact_sha256=served_digest,
            baseline_context_sha256=baseline_context.context_sha256,
            baseline_exact_check_passed=True,
            candidate_observed_only=True,
            delivery_ack_required_before_candidate=(
                disposition == "staged_pending_delivery_ack"),
            production_write=False,
            shadow_promotion=False,
            production_promotion=False,
            timings_ns=timings,
        )

    def acknowledge_delivery(self, envelope_sha256: str) -> str:
        if type(envelope_sha256) is not str or len(envelope_sha256) != 64:
            raise ValueError("invalid C33 delivery acknowledgement")
        with self._lock:
            if self._closed:
                raise ValueError("closed C33 asynchronous shadow boundary")
            envelope = self._staged.pop(envelope_sha256, None)
            if envelope is None:
                raise ValueError("unknown or already acknowledged C33 envelope")
        try:
            self._queue.put_nowait(envelope)
        except Full as exc:
            with self._lock:
                self._queue_full_drops += 1
            raise RuntimeError("C33 reserved queue capacity invariant failed") from exc
        with self._lock:
            self._acknowledged += 1
        return "acknowledged_for_observation"

    def acknowledge_all_delivered(self) -> int:
        with self._lock:
            tokens = tuple(self._staged)
        for token in tokens:
            self.acknowledge_delivery(token)
        return len(tokens)

    def _verify_envelope(
        self, envelope: _AsyncEnvelope,
    ) -> dict[str, Any]:
        if (
            envelope.prepared_context_sha256 != self.prepared_context.context_sha256
            or _sha256_bytes(envelope.case_json) != envelope.case_sha256
        ):
            raise ValueError("C33 asynchronous envelope payload changed")
        body = _envelope_body(
            boundary_id=envelope.boundary_id,
            request_index=envelope.request_index,
            case_sha256=envelope.case_sha256,
            served_artifact_sha256=envelope.served_artifact_sha256,
            baseline_context_sha256=envelope.baseline_context_sha256,
            prepared_context_sha256=envelope.prepared_context_sha256,
        )
        if _sha256_bytes(_canonical_bytes(body)) != envelope.envelope_sha256:
            raise ValueError("C33 asynchronous envelope identity changed")
        case = json.loads(envelope.case_json)
        context = build_verified_gf2_context(case, require_source_packed=False)
        if (
            context.case_id != envelope.case_id
            or context.context_sha256 != envelope.baseline_context_sha256
        ):
            raise ValueError("C33 asynchronous envelope semantic binding changed")
        return case

    def _observe(self, envelope: _AsyncEnvelope) -> AsyncShadowObservation:
        timings = {field: 0 for field in OBSERVATION_TIMING_FIELDS}
        timings["queue_wait_ns"] = max(0, self._clock() - envelope.staged_ns)
        candidate_status = "error"
        candidate_selected_arm = None
        candidate_best = None
        candidate_digest = None
        candidate_context_sha256 = None
        candidate_match = None
        error_type = None
        refusal_reason = None
        divergence = False
        contained = False
        started = self._clock()
        try:
            verify_prepared_policy_sources(self.prepared_context)
            case = self._verify_envelope(envelope)
            if self._candidate_session is None:
                raise RuntimeError("C33 candidate session missing")
            candidate = self._candidate_executor(self._candidate_session, case)
            if type(candidate) is not SupportAwareQueryResult:
                raise TypeError("C33 candidate executor returned invalid result")
            document = candidate.to_dict()
            if candidate.status == "refused":
                verify_support_aware_query_result(
                    document,
                    None,
                    c27_policy_sha256=self.prepared_context.c27_policy_sha256,
                    c22_policy_sha256=self.prepared_context.c22_policy_sha256,
                )
                candidate_status = "refused"
                refusal_reason = candidate.reason
                contained = True
            else:
                requested_packed = candidate.requested_arm == SOURCE_PACKED_SCREENED
                candidate_context = build_verified_gf2_context(
                    case, require_source_packed=requested_packed)
                verify_support_aware_query_result(
                    document,
                    candidate_context,
                    c27_policy_sha256=self.prepared_context.c27_policy_sha256,
                    c22_policy_sha256=self.prepared_context.c22_policy_sha256,
                )
                candidate_status = "observed"
                candidate_selected_arm = candidate.selected_arm
                candidate_best = candidate.best_artifact
                candidate_digest = delivery_sha256(candidate_best)
                candidate_context_sha256 = candidate.context_sha256
        except Exception as exc:
            candidate_status = "error"
            error_type = type(exc).__name__
            contained = True
        timings["candidate_ns"] = max(1, self._clock() - started)

        started = self._clock()
        if candidate_status == "observed":
            candidate_match = (
                candidate_digest == envelope.served_artifact_sha256
            )
            divergence = not candidate_match
            contained = divergence
        timings["comparison_ns"] = max(1, self._clock() - started)
        return AsyncShadowObservation(
            boundary_id=self.boundary_id,
            request_index=envelope.request_index,
            case_id=envelope.case_id,
            envelope_sha256=envelope.envelope_sha256,
            case_sha256=envelope.case_sha256,
            baseline_context_sha256=envelope.baseline_context_sha256,
            expected_artifact_sha256=envelope.served_artifact_sha256,
            candidate_status=candidate_status,
            candidate_selected_arm=candidate_selected_arm,
            candidate_best_artifact=candidate_best,
            candidate_artifact_sha256=candidate_digest,
            candidate_context_sha256=candidate_context_sha256,
            candidate_best_identity_match=candidate_match,
            candidate_error_type=error_type,
            candidate_refusal_reason=refusal_reason,
            shadow_divergence_detected=divergence,
            shadow_failure_contained=contained,
            candidate_observed_only=True,
            production_write=False,
            shadow_promotion=False,
            production_promotion=False,
            timings_ns={**timings, "observation_total_ns": sum(timings.values())},
        )

    def _worker_loop(self) -> None:
        while True:
            try:
                item = self._queue.get(timeout=0.1)
            except Empty:
                with self._lock:
                    if self._closed:
                        self._worker_stopped = True
                        return
                continue
            if item is _STOP:
                self._queue.task_done()
                with self._lock:
                    self._worker_stopped = True
                return
            with self._lock:
                self._active += 1
            try:
                observation = self._observe(item)
                with self._lock:
                    self._observations.append(observation)
                    if observation.candidate_status == "observed":
                        self._candidate_observations += 1
                    elif observation.candidate_status == "refused":
                        self._candidate_refusals += 1
                    else:
                        self._candidate_errors += 1
                    if observation.shadow_divergence_detected:
                        self._divergences += 1
            finally:
                with self._lock:
                    self._active -= 1
                self._queue.task_done()

    def drain(self, *, timeout_seconds: float = 30.0) -> bool:
        if (
            type(timeout_seconds) not in (int, float)
            or not 0.01 <= timeout_seconds <= 60.0
        ):
            raise ValueError("invalid C33 drain timeout")
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            with self._lock:
                done = not self._staged and self._active == 0
            if done and self._queue.unfinished_tasks == 0:
                return True
            time.sleep(0.001)
        return False

    def close(
        self, *, drain: bool = True, timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        if type(drain) is not bool:
            raise ValueError("invalid C33 close mode")
        with self._lock:
            already_closed = self._closed
            if not already_closed:
                self._accepting = False
        if already_closed:
            return self.snapshot()
        if drain:
            self.acknowledge_all_delivered()
            if not self.drain(timeout_seconds=timeout_seconds):
                raise TimeoutError("C33 asynchronous observation drain timed out")
        elif self.snapshot()["pending_staged"] or self._queue.unfinished_tasks:
            raise ValueError("C33 refuses lossy close with pending observations")
        if self.shadow_enabled and self._worker is not None:
            self._queue.put_nowait(_STOP)
            self._worker.join(timeout=min(float(timeout_seconds), 60.0))
            if self._worker.is_alive():
                raise TimeoutError("C33 asynchronous worker stop timed out")
        if self._candidate_session is not None:
            self._candidate_session.close()
        with self._lock:
            self._closed = True
        self.audit_sources()
        return self.snapshot()


def verify_async_shadow_serve_result(
    document: dict[str, Any],
    case: Mapping[str, Any],
    *,
    required_best: dict[str, Any] | None,
) -> None:
    expected = {field.name for field in AsyncShadowServeResult.__dataclass_fields__.values()}
    timings = document.get("timings_ns") if type(document) is dict else None
    context = build_verified_gf2_context(case, require_source_packed=False)
    if (
        type(document) is not dict
        or set(document) != expected
        or document.get("schema") != ASYNC_RESULT_SCHEMA
        or document.get("status") != "served_baseline"
        or document.get("case_id") != context.case_id
        or document.get("n_vars") != context.n_vars
        or document.get("served_output_source") != "exact_screened_baseline"
        or document.get("served_selected_arm") != SCREENED
        or document.get("served_best_artifact") != required_best
        or document.get("served_artifact_sha256") != delivery_sha256(required_best)
        or document.get("baseline_context_sha256") != context.context_sha256
        or document.get("baseline_exact_check_passed") is not True
        or document.get("candidate_observed_only") is not True
        or type(document.get("shadow_enabled")) is not bool
        or type(document.get("sample_every")) is not int
        or not 1 <= document.get("sample_every") <= 1024
        or type(document.get("sample_eligible")) is not bool
        or document.get("production_write") is not False
        or document.get("shadow_promotion") is not False
        or document.get("production_promotion") is not False
        or type(document.get("queue_depth_after")) is not int
        or document.get("queue_depth_after") < 0
        or type(timings) is not dict
        or set(timings) != {*RESULT_TIMING_FIELDS, "request_total_ns"}
        or any(type(value) is not int or value < 0 for value in timings.values())
        or timings["baseline_ns"] < 1
        or timings["request_total_ns"]
        != sum(timings[field] for field in RESULT_TIMING_FIELDS)
    ):
        raise ValueError("invalid C33 asynchronous served-baseline result")
    if required_best is not None:
        if ExactGF2Artifact.from_dict(required_best).reconstruct() != context.truth_bits:
            raise ValueError("C33 served artifact does not reconstruct")
    disposition = document["shadow_disposition"]
    eligible = document["sample_eligible"]
    token = document["shadow_envelope_sha256"]
    if not document["shadow_enabled"]:
        valid = (
            not eligible
            and disposition == "disabled"
            and token is None
            and document["delivery_ack_required_before_candidate"] is False
            and timings["envelope_copy_ns"] == 0
            and timings["stage_ns"] == 0
        )
    elif not eligible:
        valid = (
            disposition == "sampled_out"
            and token is None
            and document["delivery_ack_required_before_candidate"] is False
            and timings["envelope_copy_ns"] == 0
            and timings["stage_ns"] == 0
        )
    else:
        valid = type(token) is str and len(token) == 64
        if disposition == "staged_pending_delivery_ack":
            valid = valid and document["delivery_ack_required_before_candidate"] is True
        elif disposition == "queue_full":
            valid = valid and document["delivery_ack_required_before_candidate"] is False
        else:
            valid = False
        valid = (
            valid
            and timings["envelope_copy_ns"] >= 1
            and timings["stage_ns"] >= 1
        )
    if not valid:
        raise ValueError("invalid C33 asynchronous shadow disposition")


def verify_async_shadow_observation(
    document: dict[str, Any],
    case: Mapping[str, Any],
    *,
    required_best: dict[str, Any] | None,
    envelope_sha256: str,
) -> None:
    expected = {field.name for field in AsyncShadowObservation.__dataclass_fields__.values()}
    timings = document.get("timings_ns") if type(document) is dict else None
    context = build_verified_gf2_context(case, require_source_packed=False)
    if (
        type(document) is not dict
        or set(document) != expected
        or document.get("schema") != ASYNC_OBSERVATION_SCHEMA
        or document.get("case_id") != context.case_id
        or document.get("envelope_sha256") != envelope_sha256
        or document.get("case_sha256")
        != _sha256_bytes(_canonical_bytes(_shadow_case_payload(case)))
        or document.get("baseline_context_sha256") != context.context_sha256
        or document.get("expected_artifact_sha256") != delivery_sha256(required_best)
        or document.get("candidate_observed_only") is not True
        or document.get("production_write") is not False
        or document.get("shadow_promotion") is not False
        or document.get("production_promotion") is not False
        or type(timings) is not dict
        or set(timings) != {*OBSERVATION_TIMING_FIELDS, "observation_total_ns"}
        or any(type(value) is not int or value < 0 for value in timings.values())
        or timings["candidate_ns"] < 1
        or timings["comparison_ns"] < 1
        or timings["observation_total_ns"]
        != sum(timings[field] for field in OBSERVATION_TIMING_FIELDS)
    ):
        raise ValueError("invalid C33 asynchronous observation")
    status = document.get("candidate_status")
    if status == "observed":
        candidate_best = document.get("candidate_best_artifact")
        match = candidate_best == required_best
        valid = (
            document.get("candidate_selected_arm") is not None
            and document.get("candidate_artifact_sha256")
            == delivery_sha256(candidate_best)
            and document.get("candidate_context_sha256") is not None
            and document.get("candidate_best_identity_match") is match
            and document.get("shadow_divergence_detected") is (not match)
            and document.get("shadow_failure_contained") is (not match)
            and document.get("candidate_error_type") is None
            and document.get("candidate_refusal_reason") is None
        )
    elif status == "refused":
        valid = (
            document.get("candidate_refusal_reason") is not None
            and document.get("shadow_failure_contained") is True
            and document.get("shadow_divergence_detected") is False
            and all(document.get(field) is None for field in (
                "candidate_selected_arm", "candidate_best_artifact",
                "candidate_artifact_sha256", "candidate_context_sha256",
                "candidate_best_identity_match", "candidate_error_type",
            ))
        )
    elif status == "error":
        valid = (
            document.get("candidate_error_type") is not None
            and document.get("shadow_failure_contained") is True
            and document.get("shadow_divergence_detected") is False
            and all(document.get(field) is None for field in (
                "candidate_selected_arm", "candidate_best_artifact",
                "candidate_artifact_sha256", "candidate_context_sha256",
                "candidate_best_identity_match", "candidate_refusal_reason",
            ))
        )
    else:
        valid = False
    if not valid:
        raise ValueError("invalid C33 candidate observation state")
