"""Bounded, iterative features available before running any Boolean backend."""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

FEATURE_VERSION = 1
FEATURE_NAMES = (
    "n_vars", "log2_queries", "log2_nodes", "depth", "sharing_fraction",
    "not_fraction", "and_or_fraction", "xor_eqv_fraction",
    "same_child_fraction", "complement_child_fraction",
)
BIN_OPS = (And, Or, Xor, Imp, Eqv)


class IneligibleExpression(ValueError):
    """The local research contract cannot evaluate this input within its bounds."""


def postorder(expr: Expr, *, max_nodes: int = 4096) -> list[Expr]:
    """Identity-DAG traversal, with cycle detection and no recursive hashing."""
    state: dict[int, int] = {}
    result: list[Expr] = []
    stack = [(expr, False)]
    while stack:
        node, done = stack.pop()
        key = id(node)
        if done:
            state[key] = 2
            result.append(node)
            continue
        if state.get(key) == 2:
            continue
        if state.get(key) == 1:
            raise IneligibleExpression("cyclic expression")
        if type(node) not in (Var, Not, *BIN_OPS):
            raise IneligibleExpression("unsupported expression node")
        if len(state) >= max_nodes:
            raise IneligibleExpression("identity-node limit exceeded")
        state[key] = 1
        stack.append((node, True))
        if type(node) is Var:
            if type(node.i) is not int or node.i < 0:
                raise IneligibleExpression("invalid variable index")
        else:
            if type(node) in BIN_OPS:
                stack.append((node.b, False))
            stack.append((node.a, False))
    return result


@dataclass(frozen=True)
class Features:
    values: tuple[float, ...]
    identity_nodes: int
    structural_nodes: int
    depth: int
    unfolded_nodes_capped: int


def extract_features(expr: Expr, n_vars: int, queries: int = 1) -> Features:
    if type(n_vars) is not int or not 1 <= n_vars <= 16:
        raise IneligibleExpression("complete truth-vector experiments require 1..16 variables")
    if type(queries) is not int or not 1 <= queries <= 256:
        raise IneligibleExpression("queries must be in 1..256")
    nodes = postorder(expr)
    ids: dict[int, int] = {}
    intern: dict[tuple, int] = {}
    depths: dict[int, int] = {}
    unfolded: dict[int, int] = {}
    counts = {op: 0 for op in (Not, *BIN_OPS)}
    equal = complement = edges = 0
    for node in nodes:
        kind = type(node)
        if kind is Var:
            if node.i >= n_vars:
                raise IneligibleExpression("variable outside the declared output universe")
            signature = ("var", node.i)
            depth = size = 1
        else:
            a = ids[id(node.a)]
            children = (node.a,) if kind is Not else (node.a, node.b)
            signature = (kind.__name__,) + tuple(ids[id(c)] for c in children)
            depth = 1 + max(depths[id(c)] for c in children)
            size = min(1_000_001, 1 + sum(unfolded[id(c)] for c in children))
            edges += len(children)
            counts[kind] += 1
            if kind in BIN_OPS:
                b = ids[id(node.b)]
                equal += int(a == b)
                complement += int(
                    (type(node.a) is Not and ids[id(node.a.a)] == b)
                    or (type(node.b) is Not and ids[id(node.b.a)] == a)
                )
        ids[id(node)] = intern.setdefault(signature, len(intern))
        depths[id(node)] = depth
        unfolded[id(node)] = size
    total = len(nodes)
    values = (
        float(n_vars), math.log2(queries), math.log2(total),
        float(depths[id(expr)]), max(0, edges - total + 1) / max(1, edges),
        counts[Not] / total, (counts[And] + counts[Or]) / total,
        (counts[Xor] + counts[Eqv]) / total, equal / total, complement / total,
    )
    return Features(values, total, len(intern), depths[id(expr)], unfolded[id(expr)])


def structural_digest(expr: Expr, *, alpha_rename: bool = False) -> str:
    """Group identical and variable-renamed DAGs; not a semantic equivalence hash."""
    digests: dict[int, bytes] = {}
    variable_names: dict[int, int] = {}
    for node in postorder(expr):
        if type(node) is Var:
            index = variable_names.setdefault(node.i, len(variable_names)) if alpha_rename else node.i
            payload = f"var:{index}".encode("ascii")
        else:
            payload = type(node).__name__.encode("ascii") + b":" + digests[id(node.a)]
            if type(node) in BIN_OPS:
                payload += digests[id(node.b)]
        digests[id(node)] = hashlib.sha256(payload).digest()
    return digests[id(expr)].hex()
