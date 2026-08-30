"""Small inert cost tree for ranking exact ROBDD order strategies."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any, Sequence

from .features import FEATURE_NAMES, FEATURE_VERSION


ORDER_POLICIES = ("fixed", "expr", "interaction", "best-of-k")


def _finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _vector(values: Sequence[float]) -> tuple[float, ...]:
    if (len(values) != len(FEATURE_NAMES)
            or not all(_finite(value) and abs(value) <= 1e12 for value in values)):
        raise ValueError("invalid BDD order feature vector")
    return tuple(float(value) for value in values)


@dataclass(frozen=True)
class BddOrderDecision:
    policy: str
    reason: str


@dataclass(frozen=True)
class BddOrderCostTree:
    tree: dict[str, Any]
    ranges: tuple[tuple[float, float], ...]
    fallback: str
    min_gain: float = 0.03

    def select(self, values: Sequence[float]) -> BddOrderDecision:
        try:
            vector = _vector(values)
        except (TypeError, ValueError):
            return BddOrderDecision(self.fallback, "invalid_features")
        if any(value < low - 1e-9 or value > high + 1e-9
               for value, (low, high) in zip(vector, self.ranges)):
            return BddOrderDecision(self.fallback, "outside_training_range")
        node = self.tree
        while "feature" in node:
            node = node["left"] if vector[node["feature"]] <= node["threshold"] else node["right"]
        costs = node["costs"]
        best = min(range(len(ORDER_POLICIES)), key=lambda index: (costs[index], index))
        fallback_cost = costs[ORDER_POLICIES.index(self.fallback)]
        if costs[best] >= fallback_cost * (1 - self.min_gain):
            return BddOrderDecision(self.fallback, "insufficient_predicted_gain")
        return BddOrderDecision(ORDER_POLICIES[best], "learned_cost_tree")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "crse-bdd-order-cost-tree/v1",
            "feature_version": FEATURE_VERSION, "features": list(FEATURE_NAMES),
            "order_policies": list(ORDER_POLICIES), "fallback": self.fallback,
            "min_gain": self.min_gain, "ranges": [list(pair) for pair in self.ranges],
            "tree": self.tree,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "BddOrderCostTree":
        fields = {"schema", "feature_version", "features", "order_policies",
                  "fallback", "min_gain", "ranges", "tree"}
        if (type(data) is not dict or set(data) != fields
                or data.get("schema") != "crse-bdd-order-cost-tree/v1"
                or data.get("feature_version") != FEATURE_VERSION
                or data.get("features") != list(FEATURE_NAMES)
                or data.get("order_policies") != list(ORDER_POLICIES)
                or data.get("fallback") not in ORDER_POLICIES
                or not _finite(data.get("min_gain"))
                or not 0 <= data["min_gain"] <= 1):
            raise ValueError("invalid BDD order model schema")
        ranges = data["ranges"]
        if type(ranges) is not list or len(ranges) != len(FEATURE_NAMES):
            raise ValueError("invalid BDD order feature ranges")
        for pair in ranges:
            if (type(pair) is not list or len(pair) != 2
                    or not all(_finite(value) and abs(value) <= 1e12 for value in pair)
                    or pair[0] > pair[1]):
                raise ValueError("invalid BDD order feature range")

        def check(node: Any, depth: int) -> None:
            if type(node) is not dict or depth > 2:
                raise ValueError("invalid or oversized BDD order tree")
            if set(node) == {"costs", "samples"}:
                if (type(node["costs"]) is not list
                        or len(node["costs"]) != len(ORDER_POLICIES)
                        or not all(_finite(cost) and 0 < cost <= 1e12
                                   for cost in node["costs"])
                        or type(node["samples"]) is not int
                        or not 1 <= node["samples"] <= 512):
                    raise ValueError("invalid BDD order tree leaf")
                return
            if (set(node) != {"feature", "threshold", "left", "right"}
                    or type(node["feature"]) is not int
                    or not 0 <= node["feature"] < len(FEATURE_NAMES)
                    or not _finite(node["threshold"]) or abs(node["threshold"]) > 1e12):
                raise ValueError("invalid BDD order tree split")
            check(node["left"], depth + 1)
            check(node["right"], depth + 1)

        check(data["tree"], 0)
        detached = json.loads(json.dumps(data["tree"], allow_nan=False))
        return cls(detached, tuple(tuple(float(value) for value in pair)
                                   for pair in ranges), data["fallback"],
                   float(data["min_gain"]))


def fit_bdd_order_cost_tree(
    features: Sequence[Sequence[float]], costs: Sequence[Sequence[float]],
    *, max_depth: int = 2, min_leaf: int = 4, min_gain: float = 0.03,
) -> BddOrderCostTree:
    if (type(max_depth) is not int or not 0 <= max_depth <= 2
            or type(min_leaf) is not int or not 1 <= min_leaf <= 512
            or not _finite(min_gain) or not 0 <= min_gain <= 1
            or not 1 <= len(features) <= 512 or len(features) != len(costs)):
        raise ValueError("invalid bounded BDD order training contract")
    x = [_vector(row) for row in features]
    normalized_costs = []
    for row in costs:
        if (len(row) != len(ORDER_POLICIES)
                or not all(_finite(cost) and 0 < cost <= 1e12 for cost in row)):
            raise ValueError("BDD order training requires finite positive costs")
        minimum = min(row)
        normalized_costs.append([float(cost / minimum) for cost in row])

    def sums(indices: list[int]) -> list[float]:
        return [sum(normalized_costs[index][policy] for index in indices)
                for policy in range(len(ORDER_POLICIES))]

    def build(indices: list[int], depth: int) -> dict[str, Any]:
        totals = sums(indices)
        leaf = {"costs": [total / len(indices) for total in totals],
                "samples": len(indices)}
        if depth == max_depth or len(indices) < 2 * min_leaf:
            return leaf
        best_loss, best_split = min(totals), None
        for feature in range(len(FEATURE_NAMES)):
            unique = sorted({x[index][feature] for index in indices})
            thresholds = [(left + right) / 2 for left, right in zip(unique, unique[1:])]
            if len(thresholds) > 32:
                thresholds = [thresholds[(index * (len(thresholds) - 1)) // 31]
                              for index in range(32)]
            for threshold in thresholds:
                left = [index for index in indices if x[index][feature] <= threshold]
                right = [index for index in indices if x[index][feature] > threshold]
                if min(len(left), len(right)) < min_leaf:
                    continue
                loss = min(sums(left)) + min(sums(right))
                if loss < best_loss - 1e-9:
                    best_loss, best_split = loss, (feature, threshold, left, right)
        if best_split is None:
            return leaf
        feature, threshold, left, right = best_split
        return {"feature": feature, "threshold": threshold,
                "left": build(left, depth + 1), "right": build(right, depth + 1)}

    indices = list(range(len(x)))
    totals = sums(indices)
    fallback = ORDER_POLICIES[min(range(len(ORDER_POLICIES)),
                                  key=lambda policy: (totals[policy], policy))]
    model = BddOrderCostTree(
        build(indices, 0),
        tuple((min(row[index] for row in x), max(row[index] for row in x))
              for index in range(len(FEATURE_NAMES))), fallback, float(min_gain))
    return BddOrderCostTree.from_dict(model.to_dict())

