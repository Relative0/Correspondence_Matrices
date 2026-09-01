"""Immutable, hash-bound prepared C27/C22 policy context for resident reuse."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import time
from typing import Any, Callable

from .gf2_source_portfolio import SOURCE_PACKED_SCREENED, load_source_portfolio_policy
from .gf2_support_aware_policy import load_support_aware_policy
from .gf2_task_dispatcher import canonical_sha256


PREPARED_CONTEXT_SCHEMA = "crse-c30-prepared-support-policy-context/v1"
_CONSTRUCTION_TOKEN = object()


def _policy_items(policy: dict[str, Any]) -> tuple[tuple[str, str | int | bool], ...]:
    if any(type(value) not in (str, int, bool) for value in policy.values()):
        raise ValueError("prepared policy values must be immutable scalars")
    return tuple(sorted(policy.items()))


def _context_body(*, c27_policy_sha256: str, c22_policy_sha256: str,
                  c27_file_sha256: str, c22_file_sha256: str) -> dict[str, str]:
    return {
        "schema": PREPARED_CONTEXT_SCHEMA,
        "c27_policy_sha256": c27_policy_sha256,
        "c22_policy_sha256": c22_policy_sha256,
        "c27_file_sha256": c27_file_sha256,
        "c22_file_sha256": c22_file_sha256,
    }


@dataclass(frozen=True, init=False)
class PreparedSupportPolicyContext:
    """Validated policy snapshot containing only immutable scalar tuples."""

    schema: str
    c27_policy_items: tuple[tuple[str, str | int | bool], ...]
    c22_policy_items: tuple[tuple[str, str | int | bool], ...]
    c27_policy_sha256: str
    c22_policy_sha256: str
    c27_file_sha256: str
    c22_file_sha256: str
    c27_source_path: str
    c22_source_path: str
    context_sha256: str
    preparation_ns: int

    def __init__(self, *, token: object, c27_policy: dict[str, Any],
                 c22_policy: dict[str, Any], c27_file_sha256: str,
                 c22_file_sha256: str, c27_source_path: Path,
                 c22_source_path: Path, preparation_ns: int):
        if token is not _CONSTRUCTION_TOKEN:
            raise ValueError("prepared policy contexts require validated construction")
        body = _context_body(
            c27_policy_sha256=c27_policy["policy_sha256"],
            c22_policy_sha256=c22_policy["policy_sha256"],
            c27_file_sha256=c27_file_sha256,
            c22_file_sha256=c22_file_sha256,
        )
        values = {
            "schema": PREPARED_CONTEXT_SCHEMA,
            "c27_policy_items": _policy_items(c27_policy),
            "c22_policy_items": _policy_items(c22_policy),
            "c27_policy_sha256": c27_policy["policy_sha256"],
            "c22_policy_sha256": c22_policy["policy_sha256"],
            "c27_file_sha256": c27_file_sha256,
            "c22_file_sha256": c22_file_sha256,
            "c27_source_path": str(c27_source_path.resolve()),
            "c22_source_path": str(c22_source_path.resolve()),
            "context_sha256": canonical_sha256(body),
            "preparation_ns": preparation_ns,
        }
        for field, value in values.items():
            object.__setattr__(self, field, value)

    def policies(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return fresh mutable copies while the stored snapshot remains immutable."""
        return dict(self.c27_policy_items), dict(self.c22_policy_items)

    def identity(self) -> dict[str, str | int]:
        return {
            **_context_body(
                c27_policy_sha256=self.c27_policy_sha256,
                c22_policy_sha256=self.c22_policy_sha256,
                c27_file_sha256=self.c27_file_sha256,
                c22_file_sha256=self.c22_file_sha256,
            ),
            "context_sha256": self.context_sha256,
            "preparation_ns": self.preparation_ns,
        }


def prepare_support_policy_context(
    c27_policy_path: Path,
    c22_policy_path: Path,
    *,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> PreparedSupportPolicyContext:
    started = clock()
    c27_policy = load_support_aware_policy(c27_policy_path)
    c22_policy = load_source_portfolio_policy(c22_policy_path)
    if (
        c27_policy["large_support_arm"] != c22_policy["selected_arm"]
        or c27_policy["large_support_arm"] != SOURCE_PACKED_SCREENED
        or c27_policy["max_partitions"] != c22_policy["max_partitions"]
        or c27_policy["materialize_budget"] != c22_policy["materialize_budget"]
    ):
        raise ValueError("prepared C27/C22 frozen policy mismatch")
    c27_raw = c27_policy_path.read_bytes()
    c22_raw = c22_policy_path.read_bytes()
    preparation_ns = max(1, clock() - started)
    return PreparedSupportPolicyContext(
        token=_CONSTRUCTION_TOKEN,
        c27_policy=c27_policy,
        c22_policy=c22_policy,
        c27_file_sha256=hashlib.sha256(c27_raw).hexdigest(),
        c22_file_sha256=hashlib.sha256(c22_raw).hexdigest(),
        c27_source_path=c27_policy_path,
        c22_source_path=c22_policy_path,
        preparation_ns=preparation_ns,
    )


def verify_prepared_policy_sources(context: PreparedSupportPolicyContext) -> None:
    """Fail closed if either source file differs from the validated snapshot."""
    if type(context) is not PreparedSupportPolicyContext:
        raise ValueError("invalid prepared policy context")
    current = (
        hashlib.sha256(Path(context.c27_source_path).read_bytes()).hexdigest(),
        hashlib.sha256(Path(context.c22_source_path).read_bytes()).hexdigest(),
    )
    if current != (context.c27_file_sha256, context.c22_file_sha256):
        raise ValueError("prepared policy source changed after validation")
