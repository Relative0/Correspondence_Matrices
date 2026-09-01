"""C17 task contract and conservative dispatcher for exact CM/GF(2) artifacts."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any

from .gf2_decomposition import (
    MAX_VARS,
    ExactGF2Analysis,
    ExactGF2Artifact,
    analyze_exact_gf2,
    analyze_screened_exact_gf2,
    truth_sha256,
)


TASK_SCHEMA = "crse-gf2-decomposition-task/v1"
POLICY_SCHEMA = "crse-gf2-decomposition-dispatch-policy/v1"
EXECUTION_SCHEMA = "crse-gf2-decomposition-execution/v1"
EXHAUSTIVE = "explicit_cm_exhaustive"
SCREENED = "explicit_cm_screened"
ARMS = (EXHAUSTIVE, SCREENED)
FROZEN_TINY_CASE_MAX_VARS = 3
FROZEN_MAX_PARTITIONS = 64
FROZEN_MATERIALIZE_BUDGET = 4


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("utf-8")).hexdigest()


def current_platform_identity() -> dict[str, str]:
    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "python_implementation": platform.python_implementation(),
        "python_version": ".".join(map(str, sys.version_info[:3])),
    }


def _policy_body(identity: dict[str, str]) -> dict[str, Any]:
    return {
        "schema": POLICY_SCHEMA,
        "status": "frozen",
        "objective": "best_exact_gf2_artifact",
        "screened_arm": SCREENED,
        "advice_off_arm": EXHAUSTIVE,
        "tiny_case_arm": EXHAUSTIVE,
        "tiny_case_max_n_vars": FROZEN_TINY_CASE_MAX_VARS,
        "max_partitions": FROZEN_MAX_PARTITIONS,
        "materialize_budget": FROZEN_MATERIALIZE_BUDGET,
        "calibration_identity": identity,
        "calibration_sha256": canonical_sha256(identity),
        "unknown_platform_action": "abstain_to_exhaustive",
        "out_of_range_action": "refuse",
        "training_use": False,
        "calibration_basis": {
            "milestone": "C16",
            "minimum_case_speedup": 0.8927963215258855,
            "remediation": "conservative analytical tiny-support bypass; requires C18 transfer",
        },
        "production_promotion": False,
    }


def freeze_gf2_dispatch_policy(
    identity: dict[str, str] | None = None,
) -> dict[str, Any]:
    calibration = dict(current_platform_identity() if identity is None else identity)
    expected_keys = {"system", "machine", "python_implementation", "python_version"}
    if set(calibration) != expected_keys or any(
        type(value) is not str or not value or len(value) > 128
        for value in calibration.values()
    ):
        raise ValueError("invalid C17 platform calibration identity")
    body = _policy_body(calibration)
    return {**body, "policy_sha256": canonical_sha256(body)}


def validate_gf2_dispatch_policy(policy: dict[str, Any]) -> None:
    if type(policy) is not dict or set(policy) != set(_policy_body({
        "system": "x", "machine": "x", "python_implementation": "x", "python_version": "x",
    })) | {"policy_sha256"}:
        raise ValueError("invalid C17 policy fields")
    identity = policy.get("calibration_identity")
    if type(identity) is not dict:
        raise ValueError("invalid C17 policy identity")
    expected = _policy_body(identity)
    if policy != {**expected, "policy_sha256": canonical_sha256(expected)}:
        raise ValueError("invalid frozen C17 policy")


def save_gf2_dispatch_policy(policy: dict[str, Any], path: Path) -> None:
    validate_gf2_dispatch_policy(policy)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(policy, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def load_gf2_dispatch_policy(path: Path, *, max_bytes: int = 64_000) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise ValueError("C17 policy exceeds size bound")

    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate C17 policy key")
            value[key] = item
        return value

    policy = json.loads(
        raw,
        object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError("nonfinite C17 policy value")
        ),
    )
    validate_gf2_dispatch_policy(policy)
    return policy


@dataclass(frozen=True)
class GF2DecompositionTask:
    n_vars: int
    variable_order: tuple[int, ...]
    max_partitions: int = FROZEN_MAX_PARTITIONS
    materialize_budget: int = FROZEN_MATERIALIZE_BUDGET
    objective: str = "best_exact_gf2_artifact"
    schema: str = TASK_SCHEMA

    def validate(self) -> None:
        if (
            self.schema != TASK_SCHEMA
            or self.objective != "best_exact_gf2_artifact"
            or type(self.n_vars) is not int
            or not 2 <= self.n_vars <= MAX_VARS
            or type(self.variable_order) is not tuple
            or self.variable_order != tuple(range(self.n_vars))
            or type(self.max_partitions) is not int
            or not 1 <= self.max_partitions <= FROZEN_MAX_PARTITIONS
            or type(self.materialize_budget) is not int
            or not 1 <= self.materialize_budget <= FROZEN_MATERIALIZE_BUDGET
        ):
            raise ValueError("invalid bounded C17 decomposition task")

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "variable_order": list(self.variable_order)}


@dataclass(frozen=True)
class GF2DispatchDecision:
    selected_arm: str
    reason: str
    abstained: bool
    advice_enabled: bool
    admitted: bool


@dataclass(frozen=True)
class GF2DecompositionExecution:
    n_vars: int
    source_sha256: str
    policy_sha256: str
    selected_arm: str
    decision_reason: str
    abstained: bool
    advice_enabled: bool
    best_artifact: dict[str, Any] | None
    exact_check_passed: bool
    partitions_tested: int
    descriptors_screened: int
    artifacts_materialized: int
    policy_ns: int
    analysis_ns: int
    exact_check_ns: int
    shadow_ns: int
    total_ns: int
    shadow_arm: str | None
    shadow_best_identity_match: bool | None
    schema: str = EXECUTION_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def select_gf2_arm(
    policy: dict[str, Any],
    task: GF2DecompositionTask,
    *,
    identity: dict[str, str] | None = None,
    advice_enabled: bool = True,
) -> GF2DispatchDecision:
    validate_gf2_dispatch_policy(policy)
    if type(advice_enabled) is not bool:
        raise ValueError("C17 advice switch must be Boolean")
    try:
        task.validate()
    except ValueError:
        return GF2DispatchDecision(EXHAUSTIVE, "task_out_of_range", True,
                                   advice_enabled, False)
    if not advice_enabled:
        return GF2DispatchDecision(EXHAUSTIVE, "advice_globally_disabled", False,
                                   False, True)
    observed = current_platform_identity() if identity is None else identity
    if observed != policy["calibration_identity"]:
        return GF2DispatchDecision(EXHAUSTIVE, "platform_calibration_mismatch", True,
                                   True, True)
    if task.n_vars <= policy["tiny_case_max_n_vars"]:
        return GF2DispatchDecision(EXHAUSTIVE, "tiny_case_bypass", False, True, True)
    return GF2DispatchDecision(SCREENED, "c16_screened_tail", False, True, True)


def _best_document(analysis: ExactGF2Analysis) -> dict[str, Any] | None:
    return analysis.best.to_dict() if analysis.best is not None else None


class CompiledGF2Dispatcher:
    """A task/platform decision compiled once; every execution remains exact."""

    def __init__(self, policy: dict[str, Any], task: GF2DecompositionTask,
                 decision: GF2DispatchDecision, *, policy_ns: int, shadow: bool):
        if not decision.admitted:
            raise ValueError("cannot compile refused C17 task")
        if type(shadow) is not bool:
            raise ValueError("C17 shadow flag must be Boolean")
        self.policy = json.loads(json.dumps(policy, allow_nan=False))
        self.task = task
        self.decision = decision
        self.policy_ns = policy_ns
        self._policy_charged = False
        self.shadow = shadow

    def _analyze(self, arm: str, bits: int) -> ExactGF2Analysis:
        if arm == EXHAUSTIVE:
            return analyze_exact_gf2(
                bits, self.task.n_vars, max_partitions=self.task.max_partitions
            )
        if arm == SCREENED:
            return analyze_screened_exact_gf2(
                bits,
                self.task.n_vars,
                max_partitions=self.task.max_partitions,
                materialize_budget=self.task.materialize_budget,
            )
        raise ValueError("unknown C17 exact arm")

    def execute(self, bits: int) -> GF2DecompositionExecution:
        source_sha = truth_sha256(bits, self.task.n_vars)
        charged_policy_ns = 0 if self._policy_charged else self.policy_ns
        self._policy_charged = True
        started = time.perf_counter_ns()
        analysis = self._analyze(self.decision.selected_arm, bits)
        analysis_ns = max(1, time.perf_counter_ns() - started)
        check_started = time.perf_counter_ns()
        best = _best_document(analysis)
        exact = analysis.source_sha256 == source_sha and all(
            candidate.reconstruct() == bits for candidate in analysis.candidates
        )
        exact_check_ns = max(1, time.perf_counter_ns() - check_started)
        if not exact:
            raise RuntimeError("C17 selected arm failed exact reconstruction")

        shadow_ns, shadow_arm, shadow_match = 0, None, None
        if self.shadow:
            shadow_arm = SCREENED if self.decision.selected_arm == EXHAUSTIVE else EXHAUSTIVE
            shadow_started = time.perf_counter_ns()
            shadow_analysis = self._analyze(shadow_arm, bits)
            shadow_ns = max(1, time.perf_counter_ns() - shadow_started)
            shadow_match = _best_document(shadow_analysis) == best
            if not shadow_match or any(
                candidate.reconstruct() != bits for candidate in shadow_analysis.candidates
            ):
                raise RuntimeError("C17 shadow arm changed the exact best artifact")

        return GF2DecompositionExecution(
            n_vars=self.task.n_vars,
            source_sha256=source_sha,
            policy_sha256=self.policy["policy_sha256"],
            selected_arm=self.decision.selected_arm,
            decision_reason=self.decision.reason,
            abstained=self.decision.abstained,
            advice_enabled=self.decision.advice_enabled,
            best_artifact=best,
            exact_check_passed=True,
            partitions_tested=analysis.partitions_tested,
            descriptors_screened=analysis.descriptors_screened,
            artifacts_materialized=analysis.artifacts_materialized,
            policy_ns=charged_policy_ns,
            analysis_ns=analysis_ns,
            exact_check_ns=exact_check_ns,
            shadow_ns=shadow_ns,
            total_ns=charged_policy_ns + analysis_ns + exact_check_ns + shadow_ns,
            shadow_arm=shadow_arm,
            shadow_best_identity_match=shadow_match,
        )


def compile_gf2_dispatcher(
    policy: dict[str, Any],
    task: GF2DecompositionTask,
    *,
    identity: dict[str, str] | None = None,
    advice_enabled: bool = True,
    shadow: bool = False,
) -> CompiledGF2Dispatcher:
    started = time.perf_counter_ns()
    decision = select_gf2_arm(
        policy, task, identity=identity, advice_enabled=advice_enabled
    )
    policy_ns = max(1, time.perf_counter_ns() - started)
    return CompiledGF2Dispatcher(
        policy, task, decision, policy_ns=policy_ns, shadow=shadow
    )


def verify_gf2_execution(
    document: dict[str, Any], bits: int, *, policy_sha256: str | None = None
) -> None:
    expected = {field.name for field in GF2DecompositionExecution.__dataclass_fields__.values()}
    if type(document) is not dict or set(document) != expected:
        raise ValueError("invalid C17 execution fields")
    n_vars = document.get("n_vars")
    if (
        document.get("schema") != EXECUTION_SCHEMA
        or document.get("selected_arm") not in ARMS
        or document.get("source_sha256") != truth_sha256(bits, n_vars)
        or policy_sha256 is not None
        and document.get("policy_sha256") != policy_sha256
        or document.get("exact_check_passed") is not True
        or document.get("shadow_best_identity_match") is False
        or any(
            type(document.get(field)) is not int or document[field] < 0
            for field in (
                "policy_ns", "analysis_ns", "exact_check_ns", "shadow_ns", "total_ns",
                "partitions_tested", "descriptors_screened", "artifacts_materialized",
            )
        )
        or document["total_ns"] != (
            document["policy_ns"] + document["analysis_ns"]
            + document["exact_check_ns"] + document["shadow_ns"]
        )
    ):
        raise ValueError("invalid C17 exact execution")
    artifact = document.get("best_artifact")
    if artifact is not None and ExactGF2Artifact.from_dict(artifact).reconstruct() != bits:
        raise ValueError("C17 execution artifact failed reconstruction")

