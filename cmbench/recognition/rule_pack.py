"""A bounded proved Boolean rule pack and exact structural cone cache."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cmbench.expr.eval import eval_expr_assignment

from .features import postorder, structural_digest
from .portfolio import admit
from .proved_rules import PATTERN as XOR_PATTERN
from .proved_rules import REPLACEMENT as XOR_REPLACEMENT
from .proved_rules import RULE_ID as XOR_RULE_ID
from .proved_rules import aig_xor_expr, canonical

PACK_SCHEMA = "crse-proved-rule-pack/v1"
PACK_ID = "boolean-aig-core/v1"
OR_RULE_ID = "aig-demorgan-or/v1"
OR_PATTERN = {
    "op": "not",
    "a": {"op": "and", "a": {"op": "not", "a": "$A"},
          "b": {"op": "not", "a": "$B"}},
}
OR_REPLACEMENT = {"op": "or", "a": "$A", "b": "$B"}
RULE_PRIORITY = (XOR_RULE_ID, OR_RULE_ID)
SIDE_CONDITIONS = [
    "A and B bind to structurally identical pure Boolean subexpressions at every repeated occurrence",
    "the source AST contains only admitted Boolean operators",
]


def aig_or_expr(a: Expr, b: Expr) -> Expr:
    return Not(And(Not(a), Not(b)))


def _proof_rows(rule_id: str) -> list[dict[str, Any]]:
    a, b = Var(0), Var(1)
    if rule_id == XOR_RULE_ID:
        lhs, rhs = aig_xor_expr(a, b), Xor(a, b)
    elif rule_id == OR_RULE_ID:
        lhs, rhs = aig_or_expr(a, b), Or(a, b)
    else:
        raise ValueError("unknown proved pack rule")
    rows = []
    for av in (0, 1):
        for bv in (0, 1):
            assignment = {"x0": av, "x1": bv}
            left = eval_expr_assignment(lhs, assignment)
            right = eval_expr_assignment(rhs, assignment)
            if left != right:
                raise RuntimeError("proved pack rule disagreement")
            rows.append({"assignment": {"A": av, "B": bv}, "lhs": left, "rhs": right})
    return rows


def _metadata(rule_id: str) -> dict[str, Any]:
    if rule_id == XOR_RULE_ID:
        pattern, replacement, label = XOR_PATTERN, XOR_REPLACEMENT, "exclusive-or AIG macro"
    elif rule_id == OR_RULE_ID:
        pattern, replacement, label = OR_PATTERN, OR_REPLACEMENT, "De Morgan AIG-or macro"
    else:
        raise ValueError("unknown proved pack rule")
    return {"rule_id": rule_id, "label": label, "metavariables": ["A", "B"],
            "domain": "pure total Boolean values {0,1}", "pattern": pattern,
            "replacement": replacement, "commutative_operators": ["and", "or", "xor"],
            "side_conditions": SIDE_CONDITIONS,
            "proof_method": "exhaustive truth evaluation over both Boolean metavariables"}


@dataclass(frozen=True)
class ProvedRulePack:
    document: dict[str, Any]

    @property
    def digest(self) -> str:
        return self.document["payload_sha256"]

    def to_dict(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.document, allow_nan=False))

    @classmethod
    def from_dict(cls, data: Any) -> "ProvedRulePack":
        keys = {"schema", "pack_id", "priority", "rules", "payload_sha256"}
        if type(data) is not dict or set(data) != keys:
            raise ValueError("invalid proved-rule-pack fields")
        payload = {key: data[key] for key in keys - {"payload_sha256"}}
        if (data["schema"] != PACK_SCHEMA or data["pack_id"] != PACK_ID
                or data["priority"] != list(RULE_PRIORITY)
                or type(data["rules"]) is not list or len(data["rules"]) != 2
                or hashlib.sha256(canonical(payload)).hexdigest() != data["payload_sha256"]):
            raise ValueError("invalid proved-rule-pack identity")
        for rule, rule_id in zip(data["rules"], RULE_PRIORITY):
            expected_keys = set(_metadata(rule_id)) | {"proof_rows", "proof_rows_sha256"}
            if type(rule) is not dict or set(rule) != expected_keys:
                raise ValueError("invalid proved-rule entry fields")
            metadata = {key: rule[key] for key in _metadata(rule_id)}
            rows = rule["proof_rows"]
            if (metadata != _metadata(rule_id) or type(rows) is not list or len(rows) != 4
                    or hashlib.sha256(canonical(rows)).hexdigest() != rule["proof_rows_sha256"]):
                raise ValueError("invalid proved-rule entry identity")
            operator = (lambda a, b: a ^ b) if rule_id == XOR_RULE_ID else (lambda a, b: a | b)
            for row, (a, b) in zip(rows, ((0, 0), (0, 1), (1, 0), (1, 1))):
                expected = operator(a, b)
                if (type(row) is not dict or type(row.get("assignment")) is not dict
                        or any(type(value) is not int for value in
                               (row["assignment"].get("A"), row["assignment"].get("B"),
                                row.get("lhs"), row.get("rhs")))
                        or row != {"assignment": {"A": a, "B": b},
                                   "lhs": expected, "rhs": expected}):
                    raise ValueError("proved-rule-pack truth row disagreement")
        return cls(json.loads(json.dumps(data, allow_nan=False)))

    def save(self, path: Path) -> None:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(self.document, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")

    @classmethod
    def load(cls, path: Path) -> "ProvedRulePack":
        raw = path.read_bytes()
        if len(raw) > 65_536:
            raise ValueError("proved rule pack exceeds 64 KiB")
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate proved-rule-pack JSON key")
                result[key] = value
            return result
        return cls.from_dict(json.loads(raw, object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite rule pack"))))


def prove_rule_pack() -> ProvedRulePack:
    rules = []
    for rule_id in RULE_PRIORITY:
        rows = _proof_rows(rule_id)
        rules.append({**_metadata(rule_id), "proof_rows": rows,
                      "proof_rows_sha256": hashlib.sha256(canonical(rows)).hexdigest()})
    payload = {"schema": PACK_SCHEMA, "pack_id": PACK_ID,
               "priority": list(RULE_PRIORITY), "rules": rules}
    return ProvedRulePack.from_dict({**payload,
        "payload_sha256": hashlib.sha256(canonical(payload)).hexdigest()})


def _children(node: Expr) -> tuple[Expr, ...]:
    if isinstance(node, Var):
        return ()
    if isinstance(node, Not):
        return (node.a,)
    if isinstance(node, (And, Or, Xor, Imp, Eqv)):
        return (node.a, node.b)
    raise TypeError(node)


def _with_children(node: Expr, children: tuple[Expr, ...]) -> Expr:
    if isinstance(node, Var):
        return node
    if isinstance(node, Not):
        return node if node.a is children[0] else Not(children[0])
    cls = type(node)
    return node if node.a is children[0] and node.b is children[1] else cls(children[0], children[1])


def _uid(node: Expr, uid_by_id: dict[int, int], intern: dict[tuple[Any, ...], int]) -> int:
    if isinstance(node, Var):
        key: tuple[Any, ...] = ("var", int(node.i))
    elif isinstance(node, Not):
        key = ("not", uid_by_id[id(node.a)])
    else:
        key = (type(node).__name__.lower(), uid_by_id[id(node.a)], uid_by_id[id(node.b)])
    value = intern.get(key)
    if value is None:
        value = intern[key] = len(intern)
    uid_by_id[id(node)] = value
    return value


@dataclass(frozen=True)
class PackRewrite:
    result: Expr
    source_sha256: str
    result_sha256: str
    pack_sha256: str
    visited_nodes: int
    proposals: int
    selected_sites: int
    conflicts: int
    applications: int
    rejected: int
    applications_by_rule: dict[str, int]
    match_ns: int
    candidate_ns: int


class CompiledRulePack:
    """Fixed two-rule matcher; the proof artifact cannot supply executable behavior."""

    def __init__(self, pack_sha256: str):
        if type(pack_sha256) is not str or len(pack_sha256) != 64:
            raise ValueError("invalid compiled pack identity")
        try:
            decoded = bytes.fromhex(pack_sha256)
        except ValueError as exc:
            raise ValueError("invalid compiled pack identity") from exc
        if len(decoded) != 32:
            raise ValueError("invalid compiled pack identity")
        self.pack_sha256 = pack_sha256

    @staticmethod
    def _signed_pairs(product: Expr) -> list[tuple[Expr, Expr]]:
        if not isinstance(product, And):
            return []
        pairs = []
        if isinstance(product.b, Not):
            pairs.append((product.a, product.b.a))
        if isinstance(product.a, Not):
            pairs.append((product.b, product.a.a))
        return pairs

    def _xor_match(self, node: Expr, uid_by_id: dict[int, int]) -> tuple[Expr, Expr] | None:
        if (not isinstance(node, Not) or not isinstance(node.a, And)
                or not isinstance(node.a.a, Not) or not isinstance(node.a.b, Not)):
            return None
        products = (node.a.a.a, node.a.b.a)
        for positive_a, negative_b in self._signed_pairs(products[0]):
            for positive_b, negative_a in self._signed_pairs(products[1]):
                if (uid_by_id[id(positive_a)] == uid_by_id[id(negative_a)]
                        and uid_by_id[id(negative_b)] == uid_by_id[id(positive_b)]):
                    return positive_a, negative_b
        return None

    @staticmethod
    def _or_match(node: Expr) -> tuple[Expr, Expr] | None:
        if (isinstance(node, Not) and isinstance(node.a, And)
                and isinstance(node.a.a, Not) and isinstance(node.a.b, Not)):
            return node.a.a.a, node.a.b.a
        return None

    def matches(self, node: Expr, uid_by_id: dict[int, int]) -> list[tuple[str, tuple[Expr, Expr]]]:
        matches = []
        xor = self._xor_match(node, uid_by_id)
        if xor is not None:
            matches.append((XOR_RULE_ID, xor))
        aig_or = self._or_match(node)
        if aig_or is not None:
            matches.append((OR_RULE_ID, aig_or))
        return matches

    def rewrite(self, expr: Expr, n_vars: int, *, max_nodes: int = 4096,
                max_applications: int = 256,
                verify: Callable[[str, Expr, Expr], bool] | None = None) -> PackRewrite:
        admit(expr, n_vars, 1)
        nodes = postorder(expr)
        if (type(max_nodes) is not int or not 1 <= max_nodes <= 4096 or len(nodes) > max_nodes
                or type(max_applications) is not int or not 1 <= max_applications <= 256):
            raise ValueError("compiled pack rewrite bounds exceeded")
        memo: dict[int, Expr] = {}
        uid_by_id: dict[int, int] = {}
        intern: dict[tuple[Any, ...], int] = {}
        proposals = selected_sites = conflicts = applications = rejected = 0
        match_ns = candidate_ns = 0
        counts = {rule_id: 0 for rule_id in RULE_PRIORITY}
        source_sha = structural_digest(expr)
        for original in nodes:
            children = tuple(memo[id(child)] for child in _children(original))
            rebuilt = _with_children(original, children)
            _uid(rebuilt, uid_by_id, intern)
            started = time.perf_counter_ns()
            matches = self.matches(rebuilt, uid_by_id)
            match_ns += time.perf_counter_ns() - started
            proposals += len(matches)
            if matches:
                selected_sites += 1
                conflicts += int(len(matches) > 1)
                rule_id, bindings = matches[0]
                started = time.perf_counter_ns()
                candidate = Xor(*bindings) if rule_id == XOR_RULE_ID else Or(*bindings)
                _uid(candidate, uid_by_id, intern)
                candidate_ns += time.perf_counter_ns() - started
                accepted = verify(rule_id, rebuilt, candidate) if verify is not None else True
                if accepted:
                    if applications == max_applications:
                        raise ValueError("compiled pack application bound exceeded")
                    applications += 1
                    counts[rule_id] += 1
                    rebuilt = candidate
                else:
                    rejected += 1
            memo[id(original)] = rebuilt
        result = memo[id(expr)]
        return PackRewrite(result, source_sha, structural_digest(result), self.pack_sha256,
                           len(nodes), proposals, selected_sites, conflicts, applications,
                           rejected, counts, match_ns, candidate_ns)


def compile_rule_pack(pack: ProvedRulePack) -> CompiledRulePack:
    validated = ProvedRulePack.from_dict(pack.to_dict())
    return CompiledRulePack(validated.digest)


def _identity_bytes(expr: Expr) -> bytes:
    return canonical(expr_to_json_dag(expr))


@dataclass(frozen=True)
class ConeCacheEntry:
    source_bytes: bytes
    source_sha256: str
    pack_sha256: str
    rewrite: PackRewrite


@dataclass(frozen=True)
class CachedConeRewrite:
    cone_id: str
    result: Expr
    cache_hit: bool
    invalidated: bool
    reason: str
    source_identity_sha256: str
    identity_ns: int
    rewrite_ns: int
    rewrite: PackRewrite


class StructuralConeCache:
    """Exact per-cone cache with canonical source equality and explicit invalidation."""

    def __init__(self, max_entries: int = 256):
        if type(max_entries) is not int or not 1 <= max_entries <= 256:
            raise ValueError("invalid structural cone cache bound")
        self.max_entries = max_entries
        self._entries: dict[str, ConeCacheEntry] = {}

    @property
    def size(self) -> int:
        return len(self._entries)

    def rewrite(self, cone_id: str, expr: Expr, matcher: CompiledRulePack,
                n_vars: int = 8) -> CachedConeRewrite:
        if type(cone_id) is not str or not cone_id or len(cone_id) > 128:
            raise ValueError("invalid cone cache identity")
        started = time.perf_counter_ns()
        source_bytes = _identity_bytes(expr)
        source_sha = hashlib.sha256(source_bytes).hexdigest()
        identity_ns = max(1, time.perf_counter_ns() - started)
        prior = self._entries.get(cone_id)
        if (prior is not None and prior.pack_sha256 == matcher.pack_sha256
                and prior.source_sha256 == source_sha and prior.source_bytes == source_bytes):
            return CachedConeRewrite(cone_id, prior.rewrite.result, True, False,
                                     "unchanged_structural_identity", source_sha,
                                     identity_ns, 0, prior.rewrite)
        invalidated = prior is not None
        if prior is None and len(self._entries) == self.max_entries:
            raise ValueError("structural cone cache entry bound exceeded")
        reason = ("cold_miss" if prior is None else
                  "pack_changed" if prior.pack_sha256 != matcher.pack_sha256 else "source_changed")
        started = time.perf_counter_ns()
        rewrite = matcher.rewrite(expr, n_vars)
        rewrite_ns = max(1, time.perf_counter_ns() - started)
        self._entries[cone_id] = ConeCacheEntry(source_bytes, source_sha, matcher.pack_sha256, rewrite)
        return CachedConeRewrite(cone_id, rewrite.result, False, invalidated, reason,
                                 source_sha, identity_ns, rewrite_ns, rewrite)

    def invalidate_missing(self, active_cone_ids: set[str]) -> int:
        if type(active_cone_ids) is not set or any(type(value) is not str for value in active_cone_ids):
            raise ValueError("invalid active cone identity set")
        missing = [cone_id for cone_id in self._entries if cone_id not in active_cone_ids]
        for cone_id in missing:
            del self._entries[cone_id]
        return len(missing)
