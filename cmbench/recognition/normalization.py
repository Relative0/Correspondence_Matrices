"""Bounded multi-pass normalization for an inert, proved Boolean rule pack."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

from .features import postorder, structural_digest
from .rule_pack import CompiledRulePack, PackRewrite


class NormalizationRefusal(ValueError):
    """The bounded normalizer refused to promote a partial or ambiguous result."""


def _identity_bytes(expr: Expr) -> bytes:
    return json.dumps(expr_to_json_dag(expr), sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def operator_count(expr: Expr) -> int:
    """Count operator occurrences in the DAG's expanded AST interpretation."""
    counts: dict[int, int] = {}
    for node in postorder(expr):
        if isinstance(node, Var):
            value = 0
        elif isinstance(node, Not):
            value = 1 + counts[id(node.a)]
        elif isinstance(node, (And, Or, Xor, Imp, Eqv)):
            value = 1 + counts[id(node.a)] + counts[id(node.b)]
        else:
            raise TypeError(node)
        counts[id(node)] = value
    return counts[id(expr)]


@dataclass(frozen=True)
class NormalizationPass:
    pass_index: int
    source_sha256: str
    result_sha256: str
    operator_count_before: int
    operator_count_after: int
    applications: int
    proposals: int
    conflicts: int
    applications_by_rule: dict[str, int]
    match_ns: int
    candidate_ns: int


@dataclass(frozen=True)
class PackNormalization:
    result: Expr
    source_sha256: str
    result_sha256: str
    pack_sha256: str
    productive_passes: int
    convergence_passes: int
    total_applications: int
    total_proposals: int
    total_conflicts: int
    applications_by_rule: dict[str, int]
    operator_count_before: int
    operator_count_after: int
    passes: tuple[NormalizationPass, ...]
    termination_reason: str


def normalize_to_fixpoint(
    matcher: CompiledRulePack,
    expr: Expr,
    n_vars: int,
    *,
    max_passes: int = 8,
    max_nodes: int = 4096,
    max_total_applications: int = 1024,
    conflict_policy: str = "declared_priority",
    verify: Callable[[str, Expr, Expr], bool] | None = None,
) -> PackNormalization:
    """Normalize to a proved-rule fixpoint or refuse without returning a partial result.

    Productive passes must strictly reduce the distinct DAG operator count. Exact
    canonical bytes detect cycles even under a deliberately broken matcher. The
    final no-op pass is charged and recorded because it establishes convergence.
    """
    if type(matcher) is not CompiledRulePack:
        raise TypeError("normalization requires a compiled proved-rule pack")
    if type(max_passes) is not int or not 1 <= max_passes <= 8:
        raise ValueError("normalization pass bound must be in [1,8]")
    if type(max_nodes) is not int or not 1 <= max_nodes <= 4096:
        raise ValueError("normalization node bound must be in [1,4096]")
    if (type(max_total_applications) is not int
            or not 1 <= max_total_applications <= 2048):
        raise ValueError("normalization application bound must be in [1,2048]")
    if conflict_policy not in ("declared_priority", "refuse"):
        raise ValueError("invalid normalization conflict policy")

    source_sha = structural_digest(expr)
    initial_count = operator_count(expr)
    current = expr
    seen = {_identity_bytes(expr)}
    pass_rows = []
    total_applications = total_proposals = total_conflicts = 0
    by_rule = {rule_id: 0 for rule_id in matcher.rule_ids}
    productive_passes = 0
    for pass_index in range(max_passes):
        remaining = max_total_applications - total_applications
        if remaining <= 0:
            raise NormalizationRefusal("normalization application budget exhausted before convergence")
        rewrite: PackRewrite = matcher.rewrite(current, n_vars, max_nodes=max_nodes,
            max_applications=min(256, remaining), verify=verify)
        before_count = operator_count(current)
        after_count = operator_count(rewrite.result)
        pass_rows.append(NormalizationPass(pass_index, rewrite.source_sha256,
            rewrite.result_sha256, before_count, after_count, rewrite.applications,
            rewrite.proposals, rewrite.conflicts, dict(rewrite.applications_by_rule),
            rewrite.match_ns, rewrite.candidate_ns))
        total_applications += rewrite.applications
        total_proposals += rewrite.proposals
        total_conflicts += rewrite.conflicts
        for rule_id, count in rewrite.applications_by_rule.items():
            by_rule[rule_id] += count
        if conflict_policy == "refuse" and rewrite.conflicts:
            raise NormalizationRefusal("normalization overlap encountered under refuse policy")
        if rewrite.applications == 0:
            return PackNormalization(current, source_sha, structural_digest(current),
                matcher.pack_sha256, productive_passes, len(pass_rows), total_applications,
                total_proposals, total_conflicts, by_rule, initial_count,
                operator_count(current), tuple(pass_rows), "proved_rule_fixpoint")
        if after_count >= before_count:
            raise NormalizationRefusal("productive normalization pass did not strictly decrease operators")
        identity = _identity_bytes(rewrite.result)
        if identity in seen:
            raise NormalizationRefusal("normalization cycle detected by exact structural identity")
        seen.add(identity)
        productive_passes += 1
        current = rewrite.result
    raise NormalizationRefusal("normalization pass budget exhausted before convergence")
