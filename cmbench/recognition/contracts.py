"""Minimal task/proposal/check boundary for the first verified motif slice."""
from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from cm_exprlib import Expr

from .features import structural_digest
from .portfolio import admit, reference_bits


@dataclass(frozen=True)
class Task:
    n_vars: int
    queries: int = 1
    max_seconds: float = 1.0
    learned_enabled: bool = True
    schema: str = "crse-exact-vector-task/v1"

    def __post_init__(self):
        if (self.schema != "crse-exact-vector-task/v1" or type(self.n_vars) is not int
                or not 1 <= self.n_vars <= 8 or type(self.queries) is not int
                or not 1 <= self.queries <= 256 or type(self.learned_enabled) is not bool
                or type(self.max_seconds) not in (int, float)
                or not math.isfinite(self.max_seconds) or not 0 < self.max_seconds <= 2):
            raise ValueError("invalid bounded task contract")


class Scorer(Protocol):
    """Scores proposals; no semantic authority and no training on import."""
    def score(self, values) -> float: ...


class RequestBudget:
    """Cooperative deadline; half the request reserved for exact fallback.

    Checks surround bounded Python/NumPy operations. This does not preempt native
    code. Exhausting the total deadline refuses a result, never accepts late proof.
    """
    def __init__(self, task: Task):
        self.started = time.perf_counter()
        self.deadline = self.started + task.max_seconds
        self.proposal_deadline = self.started + task.max_seconds / 2

    def check(self, *, proposal: bool = False) -> None:
        if time.perf_counter() >= (self.proposal_deadline if proposal else self.deadline):
            raise TimeoutError("cooperative request budget exhausted")


@dataclass(frozen=True)
class Proposal:
    source_region_sha256: str
    candidate: Expr
    origin: str
    model_version: str
    predicted_probability: float | None
    schema: str = "crse-affine-instance-proposal/v1"


PROPOSAL_SCHEMAS = frozenset({
    "crse-affine-instance-proposal/v1",
    "crse-region-instance-proposal/v1",
})


@dataclass(frozen=True)
class Check:
    accepted: bool
    reason: str
    source_region_sha256: str
    candidate_sha256: str | None
    pre_nodes: int
    post_nodes: int | None
    check_ns: int
    evidence: str | None
    schema: str = "crse-instance-check/v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_proposal(original: Expr, proposal: Proposal, task: Task, budget: RequestBudget,
                   *, visited: frozenset[str] = frozenset()) -> Check:
    started = time.perf_counter_ns()
    source = structural_digest(original)
    before = admit(original, task.n_vars, task.queries)
    after = None
    candidate_hash = None
    evidence = None
    accepted = False
    reason = "invalid_proposal"
    try:
        budget.check(proposal=True)
        if (type(proposal) is not Proposal or proposal.schema not in PROPOSAL_SCHEMAS
                or proposal.origin not in ("learned", "handwritten")
                or not isinstance(proposal.model_version, str) or not 1 <= len(proposal.model_version) <= 128
                or proposal.source_region_sha256 != source):
            reason = "stale_or_malformed_proposal"
        elif proposal.origin == "learned" and not task.learned_enabled:
            reason = "learned_disabled"
        elif proposal.predicted_probability is not None and (
                type(proposal.predicted_probability) not in (float, int)
                or not math.isfinite(proposal.predicted_probability)
                or not 0 <= proposal.predicted_probability <= 1):
            reason = "invalid_probability"
        else:
            after = admit(proposal.candidate, task.n_vars, task.queries)
            candidate_hash = structural_digest(proposal.candidate)
            if candidate_hash == source or candidate_hash in visited:
                reason = "cycle_or_redundant"
            else:
                # Both sides independently interpreted; never trust the model's CM.
                original_bits = reference_bits(original, task.n_vars)
                candidate_bits = reference_bits(proposal.candidate, task.n_vars)
                budget.check(proposal=True)
                if original_bits != candidate_bits:
                    reason = "semantic_mismatch"
                elif after.structural_nodes >= before.structural_nodes:
                    reason = "no_structural_reduction"
                else:
                    accepted, reason = True, "exact_instance_equivalence_and_node_reduction"
                    import hashlib
                    evidence = hashlib.sha256(original_bits.to_bytes((1 << task.n_vars) // 8 + 1, "little")).hexdigest()
    except TimeoutError:
        reason = "verification_timeout"
    except (TypeError, ValueError, AttributeError):
        reason = "invalid_candidate"
    return Check(accepted, reason, source, candidate_hash, before.structural_nodes,
                 after.structural_nodes if after else None, time.perf_counter_ns() - started, evidence)
