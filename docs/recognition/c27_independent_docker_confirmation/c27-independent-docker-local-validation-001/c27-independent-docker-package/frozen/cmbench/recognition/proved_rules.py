"""Bounded proved Boolean rules and non-executable compiled structural matchers."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cmbench.expr.eval import eval_expr_assignment

from .features import postorder, structural_digest
from .portfolio import admit

RULE_SCHEMA = "crse-proved-metavariable-rule/v1"
RULE_ID = "aig-xor-dnf/v1"
PATTERN = {
    "op": "not",
    "a": {"op": "and",
          "a": {"op": "not", "a": {"op": "and", "a": "$A", "b": {"op": "not", "a": "$B"}}},
          "b": {"op": "not", "a": {"op": "and", "a": {"op": "not", "a": "$A"}, "b": "$B"}}},
}
REPLACEMENT = {"op": "xor", "a": "$A", "b": "$B"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def aig_xor_expr(a: Expr, b: Expr) -> Expr:
    return Not(And(Not(And(a, Not(b))), Not(And(Not(a), b))))


@dataclass(frozen=True)
class ProvedRule:
    document: dict[str, Any]

    @property
    def digest(self) -> str:
        return self.document["payload_sha256"]

    def to_dict(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.document, allow_nan=False))

    @classmethod
    def from_dict(cls, data: Any) -> "ProvedRule":
        keys = {"schema", "rule_id", "metavariables", "domain", "pattern", "replacement",
                "commutative_operators", "side_conditions", "proof_method", "proof_rows",
                "proof_rows_sha256", "payload_sha256"}
        if type(data) is not dict or set(data) != keys:
            raise ValueError("invalid proved-rule fields")
        payload = {key: data[key] for key in keys - {"payload_sha256"}}
        if (data["schema"] != RULE_SCHEMA or data["rule_id"] != RULE_ID
                or data["metavariables"] != ["A", "B"]
                or data["domain"] != "pure total Boolean values {0,1}"
                or data["pattern"] != PATTERN or data["replacement"] != REPLACEMENT
                or data["commutative_operators"] != ["and", "xor"]
                or data["side_conditions"] != [
                    "A and B bind to structurally identical pure Boolean subexpressions at every repeated occurrence",
                    "the source AST contains only admitted Boolean operators",
                ]
                or data["proof_method"] != "exhaustive truth evaluation over both Boolean metavariables"
                or type(data["proof_rows"]) is not list or len(data["proof_rows"]) != 4
                or hashlib.sha256(canonical(data["proof_rows"])).hexdigest() != data["proof_rows_sha256"]
                or hashlib.sha256(canonical(payload)).hexdigest() != data["payload_sha256"]):
            raise ValueError("invalid proved-rule identity or evidence")
        expected_assignments = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for row, (a, b) in zip(data["proof_rows"], expected_assignments):
            if (type(row) is not dict or type(row.get("assignment")) is not dict
                    or any(type(value) is not int for value in
                           (row["assignment"].get("A"), row["assignment"].get("B"),
                            row.get("lhs"), row.get("rhs")))
                    or row != {"assignment": {"A": a, "B": b}, "lhs": a ^ b, "rhs": a ^ b}
                    or row["lhs"] != row["rhs"]):
                raise ValueError("metavariable proof row disagreement")
        return cls(json.loads(json.dumps(data, allow_nan=False)))

    def save(self, path: Path) -> None:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(self.document, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")

    @classmethod
    def load(cls, path: Path) -> "ProvedRule":
        raw = path.read_bytes()
        if len(raw) > 32_768:
            raise ValueError("proved-rule artifact exceeds 32 KiB")
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate proved-rule JSON key")
                result[key] = value
            return result
        return cls.from_dict(json.loads(raw, object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite proved rule"))))


def prove_aig_xor_rule() -> ProvedRule:
    a, b = Var(0), Var(1)
    lhs, rhs = aig_xor_expr(a, b), Xor(a, b)
    rows = []
    for av in (0, 1):
        for bv in (0, 1):
            assignment = {"x0": av, "x1": bv}
            left = eval_expr_assignment(lhs, assignment)
            right = eval_expr_assignment(rhs, assignment)
            if left != right:
                raise RuntimeError("AIG XOR metavariable proof failed")
            rows.append({"assignment": {"A": av, "B": bv}, "lhs": left, "rhs": right})
    payload = {"schema": RULE_SCHEMA, "rule_id": RULE_ID, "metavariables": ["A", "B"],
        "domain": "pure total Boolean values {0,1}", "pattern": PATTERN, "replacement": REPLACEMENT,
        "commutative_operators": ["and", "xor"],
        "side_conditions": [
            "A and B bind to structurally identical pure Boolean subexpressions at every repeated occurrence",
            "the source AST contains only admitted Boolean operators",
        ],
        "proof_method": "exhaustive truth evaluation over both Boolean metavariables",
        "proof_rows": rows, "proof_rows_sha256": hashlib.sha256(canonical(rows)).hexdigest()}
    return ProvedRule.from_dict({**payload, "payload_sha256": hashlib.sha256(canonical(payload)).hexdigest()})


@dataclass(frozen=True)
class RuleRewrite:
    result: Expr
    source_sha256: str
    result_sha256: str
    proof_sha256: str
    visited_nodes: int
    proposals: int
    applications: int
    rejected: int
    match_ns: int
    candidate_ns: int


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


class CompiledAigXorRule:
    """Fixed matcher implementation selected only by a validated proved-rule ID."""

    def __init__(self, proof_sha256: str):
        if type(proof_sha256) is not str or len(proof_sha256) != 64:
            raise ValueError("invalid compiled-rule proof identity")
        try:
            bytes.fromhex(proof_sha256)
        except ValueError as exc:
            raise ValueError("invalid compiled-rule proof identity") from exc
        self.proof_sha256 = proof_sha256

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

    def match_root(self, node: Expr, uid_by_id: dict[int, int]) -> tuple[Expr, Expr] | None:
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

    def rewrite(self, expr: Expr, n_vars: int, *, max_nodes: int = 4096, max_applications: int = 256,
                verify: Callable[[Expr, Expr], bool] | None = None) -> RuleRewrite:
        admit(expr, n_vars, 1)
        nodes = postorder(expr)
        if (type(max_nodes) is not int or not 1 <= max_nodes <= 4096 or len(nodes) > max_nodes
                or type(max_applications) is not int or not 1 <= max_applications <= 256):
            raise ValueError("compiled-rule rewrite bounds exceeded")
        memo: dict[int, Expr] = {}
        uid_by_id: dict[int, int] = {}
        intern: dict[tuple[Any, ...], int] = {}
        proposals = applications = rejected = match_ns = candidate_ns = 0
        source_sha = structural_digest(expr)
        for original in nodes:
            children = tuple(memo[id(child)] for child in _children(original))
            rebuilt = _with_children(original, children)
            for child in children:
                if id(child) not in uid_by_id:
                    raise RuntimeError("rewrite UID ordering disagreement")
            _uid(rebuilt, uid_by_id, intern)
            started = time.perf_counter_ns()
            bindings = self.match_root(rebuilt, uid_by_id)
            match_ns += time.perf_counter_ns() - started
            if bindings is not None:
                proposals += 1
                started = time.perf_counter_ns()
                candidate = Xor(*bindings)
                _uid(candidate, uid_by_id, intern)
                candidate_ns += time.perf_counter_ns() - started
                accepted = verify(rebuilt, candidate) if verify is not None else True
                if accepted:
                    if applications == max_applications:
                        raise ValueError("compiled-rule application bound exceeded")
                    applications += 1
                    rebuilt = candidate
                else:
                    rejected += 1
            memo[id(original)] = rebuilt
        result = memo[id(expr)]
        return RuleRewrite(result, source_sha, structural_digest(result), self.proof_sha256,
                           len(nodes), proposals, applications, rejected, match_ns, candidate_ns)


def compile_rule(rule: ProvedRule) -> CompiledAigXorRule:
    validated = ProvedRule.from_dict(rule.to_dict())
    if validated.document["rule_id"] != RULE_ID:
        raise ValueError("no compiled matcher for proved rule")
    return CompiledAigXorRule(validated.digest)
