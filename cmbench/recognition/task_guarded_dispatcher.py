"""C14 task-level opt-in and shadow execution for the exact ANF sentinel."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import platform
import sys
import time
from typing import Any

from .adaptive_exact_dispatcher import adaptive_exact_partition_fast
from .source_anf_hybrid import ProductCache
from .source_interaction import MAX_VARS, source_exact_partition


TASK_SCHEMA = "crse-exact-task-contract/v1"
POLICY_SCHEMA = "crse-task-tail-guard-policy/v1"
FROZEN_PRODUCT_PAIR_BUDGET = 4096
SUPPORTED_TASKS = {
    "throughput", "latency_sensitive", "repeated_query", "memory_sensitive",
}


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


def freeze_task_guard_policy(identity: dict[str, str] | None = None) -> dict[str, Any]:
    calibration = dict(current_platform_identity() if identity is None else identity)
    expected_keys = {"system", "machine", "python_implementation", "python_version"}
    if set(calibration) != expected_keys or any(
            type(value) is not str or not value or len(value) > 128
            for value in calibration.values()):
        raise ValueError("invalid C14 platform calibration identity")
    policy = {
        "schema": POLICY_SCHEMA, "status": "frozen",
        "product_pair_budget": FROZEN_PRODUCT_PAIR_BUDGET,
        "task_arms": {
            "throughput": "set_no_sentinel",
            "latency_sensitive": "sentinel_fast",
            "repeated_query": "sentinel_fast",
            "memory_sensitive": "set_no_sentinel",
        },
        "minimum_reuses_for_sentinel": 2,
        "calibration_identity": calibration,
        "unknown_platform_action": "abstain_to_set_no_sentinel",
        "unsupported_task_action": "abstain_to_set_no_sentinel",
        "out_of_range_action": "refuse_advice",
        "training_use": False,
    }
    policy["calibration_sha256"] = canonical_sha256(calibration)
    return policy


def validate_policy(policy: dict[str, Any]) -> None:
    expected = {
        "schema", "status", "product_pair_budget", "task_arms",
        "minimum_reuses_for_sentinel", "calibration_identity", "calibration_sha256",
        "unknown_platform_action", "unsupported_task_action", "out_of_range_action",
        "training_use",
    }
    if (type(policy) is not dict or set(policy) != expected
            or policy.get("schema") != POLICY_SCHEMA or policy.get("status") != "frozen"
            or policy.get("product_pair_budget") != FROZEN_PRODUCT_PAIR_BUDGET
            or policy.get("task_arms") != {
                "throughput": "set_no_sentinel",
                "latency_sensitive": "sentinel_fast",
                "repeated_query": "sentinel_fast",
                "memory_sensitive": "set_no_sentinel",
            }
            or policy.get("minimum_reuses_for_sentinel") != 2
            or policy.get("calibration_sha256") != canonical_sha256(
                policy.get("calibration_identity"))
            or policy.get("unknown_platform_action") != "abstain_to_set_no_sentinel"
            or policy.get("unsupported_task_action") != "abstain_to_set_no_sentinel"
            or policy.get("out_of_range_action") != "refuse_advice"
            or policy.get("training_use") is not False):
        raise ValueError("invalid frozen C14 task policy")


@dataclass(frozen=True)
class ExactTaskContract:
    task_kind: str
    expected_reuses: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {"schema": TASK_SCHEMA, **asdict(self)}

    def validate(self) -> None:
        if (type(self.task_kind) is not str or not 1 <= len(self.task_kind) <= 64
                or type(self.expected_reuses) is not int
                or not 1 <= self.expected_reuses <= 1_000_000):
            raise ValueError("invalid bounded C14 task contract")


@dataclass(frozen=True)
class TaskGuardDecision:
    selected_arm: str
    reason: str
    abstained: bool
    advice_enabled: bool
    admitted: bool


@dataclass(frozen=True)
class TaskGuardExecution:
    partition: tuple[int, ...] | None
    selected_arm: str
    decision_reason: str
    abstained: bool
    policy_ns: int
    production_ns: int
    shadow_ns: int
    total_ns: int
    shadow_selected_arm: str | None
    shadow_partition_match: bool | None


def select_task_arm(
    policy: dict[str, Any],
    task: ExactTaskContract,
    *,
    n_vars: int,
    identity: dict[str, str] | None = None,
    advice_enabled: bool = True,
) -> TaskGuardDecision:
    validate_policy(policy)
    task.validate()
    if type(advice_enabled) is not bool:
        raise ValueError("C14 advice switch must be Boolean")
    if type(n_vars) is not int or not 2 <= n_vars <= MAX_VARS:
        return TaskGuardDecision(
            "set_no_sentinel", "advice_input_out_of_range", True,
            advice_enabled, False)
    if not advice_enabled:
        return TaskGuardDecision(
            "set_no_sentinel", "advice_globally_disabled", False, False, True)
    observed = current_platform_identity() if identity is None else identity
    if observed != policy["calibration_identity"]:
        return TaskGuardDecision(
            "set_no_sentinel", "platform_calibration_mismatch", True, True, True)
    if task.task_kind not in SUPPORTED_TASKS:
        return TaskGuardDecision(
            "set_no_sentinel", "unsupported_task", True, True, True)
    if (task.task_kind == "repeated_query"
            and task.expected_reuses < policy["minimum_reuses_for_sentinel"]):
        return TaskGuardDecision(
            "set_no_sentinel", "insufficient_expected_reuse", True, True, True)
    return TaskGuardDecision(
        policy["task_arms"][task.task_kind], f"task:{task.task_kind}",
        False, True, True)


class CompiledTaskGuard:
    """One decision compiled before a bounded workload; execution stays exact."""

    def __init__(self, decision: TaskGuardDecision, *, n_vars: int,
                 product_pair_budget: int, cache_capacity: int, policy_ns: int,
                 shadow: bool):
        if not decision.admitted:
            raise ValueError("cannot compile out-of-range C14 advice")
        if type(shadow) is not bool:
            raise ValueError("C14 shadow flag must be Boolean")
        self.decision = decision
        self.n_vars = n_vars
        self.product_pair_budget = product_pair_budget
        self.cache = ProductCache(cache_capacity)
        self.shadow_cache = ProductCache(cache_capacity)
        self.policy_ns = policy_ns
        self._policy_charged = False
        self.shadow = shadow

    def _execute_arm(self, arm: str, document: dict[str, Any]):
        if arm == "set_no_sentinel":
            return source_exact_partition(document, self.n_vars), "set_source_anf"
        if arm == "sentinel_fast":
            return adaptive_exact_partition_fast(
                document, self.n_vars,
                product_pair_budget=self.product_pair_budget, cache=self.cache)
        raise ValueError("unknown compiled C14 arm")

    def execute(self, document: dict[str, Any]) -> TaskGuardExecution:
        charged_policy_ns = 0 if self._policy_charged else self.policy_ns
        self._policy_charged = True
        production_started = time.perf_counter_ns()
        partition, selected = self._execute_arm(self.decision.selected_arm, document)
        production_ns = time.perf_counter_ns() - production_started
        shadow_ns, shadow_selected, shadow_match = 0, None, None
        if self.shadow:
            shadow_arm = ("sentinel_fast" if self.decision.selected_arm == "set_no_sentinel"
                          else "set_no_sentinel")
            shadow_started = time.perf_counter_ns()
            if shadow_arm == "set_no_sentinel":
                shadow_partition = source_exact_partition(document, self.n_vars)
                shadow_selected = "set_source_anf"
            else:
                shadow_partition, shadow_selected = adaptive_exact_partition_fast(
                    document, self.n_vars,
                    product_pair_budget=self.product_pair_budget, cache=self.shadow_cache)
            shadow_ns = time.perf_counter_ns() - shadow_started
            shadow_match = shadow_partition == partition
            if not shadow_match:
                raise RuntimeError("C14 shadow arm changed an exact partition")
        return TaskGuardExecution(
            partition, selected, self.decision.reason, self.decision.abstained,
            charged_policy_ns, production_ns, shadow_ns,
            charged_policy_ns + production_ns + shadow_ns,
            shadow_selected, shadow_match)


def compile_task_guard(
    policy: dict[str, Any],
    task: ExactTaskContract,
    *,
    n_vars: int,
    cache_capacity: int = 1024,
    identity: dict[str, str] | None = None,
    advice_enabled: bool = True,
    shadow: bool = False,
) -> CompiledTaskGuard:
    started = time.perf_counter_ns()
    decision = select_task_arm(
        policy, task, n_vars=n_vars, identity=identity,
        advice_enabled=advice_enabled)
    policy_ns = time.perf_counter_ns() - started
    return CompiledTaskGuard(
        decision, n_vars=n_vars,
        product_pair_budget=policy["product_pair_budget"],
        cache_capacity=cache_capacity, policy_ns=policy_ns, shadow=shadow)
