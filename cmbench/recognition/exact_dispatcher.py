"""Cheap deterministic selection among exact source decomposition paths."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .source_interaction import MULTIPLICATIVE_OPS, OPS, _validate_document

ARMS = ("set_source_anf", "cached_packed_source_anf", "bitset_truth_vector_anf")
O1_FEATURES = ("n_vars", "nodes")
LINEAR_FEATURES = (
    "n_vars", "nodes", "depth", "multiplicative_nodes", "xor_eqv_nodes",
    "not_nodes", "shared_nodes", "extra_references", "root_term_log2",
    "total_product_log2", "max_product_log2", "root_support",
)
POLICY_SCHEMA = "crse-exact-representation-dispatcher/v1"
MAX_BOUND = (1 << 62) - 1


def _cap(value: int) -> int:
    return min(MAX_BOUND, value)


def _ceil_log2(value: int) -> int:
    return max(0, (max(1, value) - 1).bit_length())


@dataclass(frozen=True)
class DispatchFeatures:
    n_vars: int
    nodes: int
    depth: int
    multiplicative_nodes: int
    xor_eqv_nodes: int
    not_nodes: int
    shared_nodes: int
    extra_references: int
    root_term_log2: int
    total_product_log2: int
    max_product_log2: int
    root_support: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def extract_dispatch_features(document: dict[str, Any], n_vars: int) -> DispatchFeatures:
    """Calculate bounded structural ANF-cost upper bounds without doing ANF."""
    nodes, root = _validate_document(document, n_vars)
    term_bounds: list[int] = []
    supports: list[int] = []
    depths: list[int] = []
    fanout = [0] * len(nodes)
    multiplicative = xor_eqv = not_nodes = 0
    total_products = maximum_product = 0
    for index, node in enumerate(nodes):
        if type(node) is not dict or node.get("op") not in OPS:
            raise ValueError("unsupported dispatcher source node")
        op = node["op"]
        if op == "var":
            variable = node.get("i")
            if type(variable) is not int or not 0 <= variable < n_vars or set(node) != {"op", "i"}:
                raise ValueError("invalid dispatcher source variable")
            term_bounds.append(1)
            supports.append(1 << variable)
            depths.append(0)
            continue
        references = (node.get("a"),) if op == "not" else (node.get("a"), node.get("b"))
        if any(type(reference) is not int or not 0 <= reference < index for reference in references):
            raise ValueError("non-topological dispatcher source reference")
        for reference in references:
            fanout[reference] += 1
        support = 0
        for reference in references:
            support |= supports[reference]
        supports.append(support)
        depths.append(1 + max(depths[reference] for reference in references))
        if op == "not":
            not_nodes += 1
            term_bounds.append(_cap(term_bounds[references[0]] + 1))
            continue
        left, right = (term_bounds[reference] for reference in references)
        if op in MULTIPLICATIVE_OPS:
            multiplicative += 1
            product = _cap(left * right)
            total_products = _cap(total_products + product)
            maximum_product = max(maximum_product, product)
        else:
            product = 0
        if op == "and":
            terms = product
        elif op == "or":
            terms = _cap(left + right + product)
        elif op == "imp":
            terms = _cap(1 + left + product)
        elif op == "xor":
            xor_eqv += 1
            terms = _cap(left + right)
        elif op == "eqv":
            xor_eqv += 1
            terms = _cap(1 + left + right)
        else:  # pragma: no cover - guarded above
            raise ValueError("unreachable dispatcher operation")
        term_bounds.append(terms)
    if supports[root] != (1 << n_vars) - 1:
        raise ValueError("dispatcher root lacks full declared support")
    return DispatchFeatures(
        n_vars=n_vars,
        nodes=len(nodes),
        depth=depths[root],
        multiplicative_nodes=multiplicative,
        xor_eqv_nodes=xor_eqv,
        not_nodes=not_nodes,
        shared_nodes=sum(value > 1 for value in fanout),
        extra_references=sum(max(0, value - 1) for value in fanout),
        root_term_log2=_ceil_log2(term_bounds[root]),
        total_product_log2=_ceil_log2(total_products),
        max_product_log2=_ceil_log2(maximum_product),
        root_support=supports[root].bit_count(),
    )


def cheap_feature_values(document: dict[str, Any], n_vars: int,
                         required: Iterable[str]) -> dict[str, int]:
    """Evaluate only the feature family required by a frozen policy."""
    required = tuple(sorted(set(required)))
    if any(name not in LINEAR_FEATURES for name in required):
        raise ValueError("unknown frozen dispatcher feature")
    if set(required).issubset(O1_FEATURES):
        nodes, _root = _validate_document(document, n_vars)
        return {"n_vars": n_vars, "nodes": len(nodes)} | {
            name: value for name, value in () if name in required
        }
    values = extract_dispatch_features(document, n_vars).to_dict()
    return {name: values[name] for name in required}


def _leaf(rows: list[dict]) -> tuple[dict, int]:
    losses = {arm: sum(int(row["costs"][arm]) for row in rows) for arm in ARMS}
    arm = min(ARMS, key=lambda name: (losses[name], ARMS.index(name)))
    return {"kind": "leaf", "arm": arm, "training_rows": len(rows)}, losses[arm]


def _thresholds(rows: list[dict], feature: str):
    values = sorted({int(row["features"][feature]) for row in rows})
    return [(left + right) / 2 for left, right in zip(values, values[1:])]


def fit_greedy_tree(rows: list[dict], *, features: tuple[str, ...],
                    max_depth: int, min_leaf: int) -> tuple[dict, int]:
    """Fit a small deterministic latency tree; rows and costs are development-only."""
    if (type(rows) is not list or not rows or any(set(row.get("costs", {})) != set(ARMS) for row in rows)
            or any(feature not in LINEAR_FEATURES for feature in features)
            or type(max_depth) is not int or not 0 <= max_depth <= 2
            or type(min_leaf) is not int or not 2 <= min_leaf <= 32):
        raise ValueError("invalid exact dispatcher fitting input")

    def fit(current: list[dict], depth: int):
        leaf, leaf_loss = _leaf(current)
        if depth == 0 or not features:
            return leaf, leaf_loss
        best = None
        for feature in features:
            for threshold in _thresholds(current, feature):
                lower = [row for row in current if row["features"][feature] <= threshold]
                upper = [row for row in current if row["features"][feature] > threshold]
                if len(lower) < min_leaf or len(upper) < min_leaf:
                    continue
                lower_leaf, lower_loss = _leaf(lower)
                upper_leaf, upper_loss = _leaf(upper)
                candidate = (lower_loss + upper_loss, feature, threshold,
                             lower, upper, lower_leaf, upper_leaf)
                if best is None or candidate[:3] < best[:3]:
                    best = candidate
        if best is None or best[0] >= leaf_loss:
            return leaf, leaf_loss
        _immediate, feature, threshold, lower, upper, _lower_leaf, _upper_leaf = best
        lower_tree, lower_loss = fit(lower, depth - 1)
        upper_tree, upper_loss = fit(upper, depth - 1)
        return {"kind": "split", "feature": feature, "threshold": threshold,
                "leq": lower_tree, "gt": upper_tree, "training_rows": len(current)}, lower_loss + upper_loss

    return fit(rows, max_depth)


def tree_stats(tree: dict) -> dict[str, Any]:
    if tree.get("kind") == "leaf":
        return {"leaves": 1, "splits": 0, "depth": 0,
                "arms": [tree["arm"]], "required_features": []}
    left, right = tree_stats(tree["leq"]), tree_stats(tree["gt"])
    return {"leaves": left["leaves"] + right["leaves"],
            "splits": 1 + left["splits"] + right["splits"],
            "depth": 1 + max(left["depth"], right["depth"]),
            "arms": sorted(set(left["arms"] + right["arms"])),
            "required_features": sorted(set([tree["feature"], *left["required_features"],
                                             *right["required_features"]]))}


def select_from_values(tree: dict, values: dict[str, int]) -> str:
    node = tree
    while node.get("kind") == "split":
        feature = node["feature"]
        if feature not in values:
            raise ValueError("missing frozen dispatcher feature")
        node = node["leq"] if values[feature] <= node["threshold"] else node["gt"]
    arm = node.get("arm")
    if node.get("kind") != "leaf" or arm not in ARMS:
        raise ValueError("invalid frozen dispatcher tree")
    return arm


def select_document(policy: dict, document: dict[str, Any], n_vars: int) -> tuple[str, dict[str, int]]:
    return CompiledDispatcher(policy).select(document, n_vars)


class CompiledDispatcher:
    """Validated-once hot selector; compilation performs no scientific fitting."""

    def __init__(self, policy: dict):
        validate_policy(policy)
        self.tree = policy["tree"]
        self.required_features = tuple(policy["tree_stats"]["required_features"])

    def select(self, document: dict[str, Any], n_vars: int) -> tuple[str, dict[str, int]]:
        values = cheap_feature_values(document, n_vars, self.required_features)
        return select_from_values(self.tree, values), values


def validate_policy(policy: dict) -> None:
    if (type(policy) is not dict or policy.get("schema") != POLICY_SCHEMA
            or policy.get("arms") != list(ARMS) or type(policy.get("tree")) is not dict
            or policy.get("tree_stats") != tree_stats(policy["tree"])
            or policy.get("training_use") != {"train": True, "validation": True,
                                               "test": False, "confirmatory": False,
                                               "c7_sealed_a": False, "c7_sealed_b": False}):
        raise ValueError("invalid frozen exact dispatcher policy")


def canonical_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()
