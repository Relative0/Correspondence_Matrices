from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from numbers import Integral
from typing import Literal


class OutputStatus(str, Enum):
    """Stable outcome vocabulary for explicit CM artifact production."""

    OK = "ok"
    REDUCED = "reduced"
    REFUSED = "refused"
    TIMEOUT = "timeout"
    OOM = "oom"
    UNVALIDATED = "unvalidated"


OutputRepresentation = Literal["packed_bitset", "truth_table_uint8", "dense_bool"]

# Arithmetic capacity, not an admission profile. Even an unbounded caller must
# not make the estimator allocate an arbitrarily large integer before checking
# its budget. 4096 variables already describe an unrealizable explicit output.
MAX_ESTIMATE_VARIABLES = 4096
_MAX_INPUT_INTEGER_BITS = 4096


def _nonnegative_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    normalized = int(value)
    if normalized.bit_length() > _MAX_INPUT_INTEGER_BITS:
        raise ValueError(f"{name} exceeds bounded estimator integer capacity")
    return normalized


@dataclass(frozen=True)
class OutputBudget:
    """Limits for one explicit CM output and its estimated working memory.

    ``max_output_vars`` retains the legacy variable-count guard while callers
    migrate to byte limits. Byte limits are representation-aware.
    """

    max_output_bytes: int | None = None
    max_temporary_bytes: int | None = None
    max_output_vars: int | None = None
    allow_reduced_output: bool = False

    def __post_init__(self) -> None:
        for name in ("max_output_bytes", "max_temporary_bytes", "max_output_vars"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _nonnegative_integer(value, name))

    def with_overrides(
        self,
        *,
        max_output_vars: int | None = None,
        allow_reduced_output: bool | None = None,
    ) -> "OutputBudget":
        effective_max_vars = self.max_output_vars
        if max_output_vars is not None:
            max_output_vars = _nonnegative_integer(max_output_vars, "max_output_vars")
            effective_max_vars = (
                int(max_output_vars)
                if effective_max_vars is None
                else min(int(effective_max_vars), int(max_output_vars))
            )
        return replace(
            self,
            max_output_vars=effective_max_vars,
            allow_reduced_output=(
                self.allow_reduced_output
                if allow_reduced_output is None
                else bool(allow_reduced_output)
            ),
        )


# Direct APIs historically exercise dense n=18 in the parallel path. Keep that
# supported while bounding accidental larger artifacts. Benchmark and remote
# configuration retain their stricter 64 KiB / n=16 defaults.
DEFAULT_OUTPUT_BUDGET = OutputBudget(max_output_bytes=1 << 18)


@dataclass(frozen=True)
class OutputEstimate:
    representation: OutputRepresentation
    variable_count: int
    elements: int
    output_bytes: int
    temporary_bytes: int


@dataclass(frozen=True)
class OutputBudgetDecision:
    status: OutputStatus
    estimate: OutputEstimate
    reason: str | None = None
    full_estimate: OutputEstimate | None = None

    @property
    def allowed(self) -> bool:
        return self.status in {OutputStatus.OK, OutputStatus.REDUCED}


class OutputBudgetExceeded(ValueError):
    """Typed, backward-compatible refusal raised before explicit allocation."""

    status = OutputStatus.REFUSED

    def __init__(self, decision: OutputBudgetDecision):
        self.decision = decision
        super().__init__(decision.reason or "explicit output refused by output budget")


def estimate_explicit_output(
    variable_count: int,
    representation: OutputRepresentation,
    *,
    operation_slots: int = 1,
) -> OutputEstimate:
    """Return the legacy deterministic admission estimate.

    The temporary estimate covers the final construction plus evaluator-sized
    packed operands. The dense two-buffer heuristic is known to underestimate
    traced allocations; neither representation is a Python heap or RSS bound.
    """

    k = _nonnegative_integer(variable_count, "variable_count")
    if k > MAX_ESTIMATE_VARIABLES:
        raise ValueError("variable_count exceeds bounded estimator capacity (4096)")
    slots = max(1, _nonnegative_integer(operation_slots, "operation_slots"))
    elements = 1 << k
    if representation == "packed_bitset":
        output_bytes = (elements + 7) // 8
        temporary_bytes = output_bytes * (slots + k + 2)
    elif representation in {"truth_table_uint8", "dense_bool"}:
        output_bytes = elements
        temporary_bytes = output_bytes * 2
    else:
        raise ValueError(f"unsupported output representation: {representation!r}")
    return OutputEstimate(
        representation=representation,
        variable_count=k,
        elements=elements,
        output_bytes=output_bytes,
        temporary_bytes=temporary_bytes,
    )


def decide_output_budget(
    budget: OutputBudget | None,
    full_estimate: OutputEstimate,
    *,
    reduced_estimate: OutputEstimate | None = None,
    artifact_name: str = "explicit output",
    reduced_artifact_name: str = "reduced explicit output",
) -> OutputBudgetDecision:
    """Choose full, reduced, or refused output before materialization."""

    if budget is None:
        return OutputBudgetDecision(OutputStatus.OK, full_estimate)

    full_reason = _limit_reason(budget, full_estimate, artifact_name)
    if full_reason is None:
        return OutputBudgetDecision(OutputStatus.OK, full_estimate)

    if budget.allow_reduced_output and reduced_estimate is not None:
        reduced_reason = _limit_reason(budget, reduced_estimate, reduced_artifact_name)
        if reduced_reason is None:
            return OutputBudgetDecision(
                OutputStatus.REDUCED,
                reduced_estimate,
                reason=full_reason,
                full_estimate=full_estimate,
            )
        reason = reduced_reason
    else:
        reason = full_reason
    return OutputBudgetDecision(
        OutputStatus.REFUSED,
        reduced_estimate or full_estimate,
        reason=reason,
        full_estimate=full_estimate,
    )


def require_output_budget(decision: OutputBudgetDecision) -> OutputBudgetDecision:
    if not decision.allowed:
        raise OutputBudgetExceeded(decision)
    return decision


def _limit_reason(
    budget: OutputBudget,
    estimate: OutputEstimate,
    artifact_name: str,
) -> str | None:
    if (
        budget.max_output_vars is not None
        and estimate.variable_count > int(budget.max_output_vars)
    ):
        return (
            f"refusing to materialize {artifact_name} for {estimate.variable_count} variables; "
            f"max_output_vars={int(budget.max_output_vars)}"
        )
    if (
        budget.max_output_bytes is not None
        and estimate.output_bytes > int(budget.max_output_bytes)
    ):
        return (
            f"refusing to materialize {artifact_name} requiring an estimated "
            f"{estimate.output_bytes} output bytes; "
            f"max_output_bytes={int(budget.max_output_bytes)}"
        )
    if (
        budget.max_temporary_bytes is not None
        and estimate.temporary_bytes > int(budget.max_temporary_bytes)
    ):
        return (
            f"refusing to materialize {artifact_name} requiring an estimated "
            f"{estimate.temporary_bytes} temporary bytes; "
            f"max_temporary_bytes={int(budget.max_temporary_bytes)}"
        )
    return None
