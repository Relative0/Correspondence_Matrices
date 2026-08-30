"""Small cost-sensitive policy for exact E2/R10 SAT execution actions."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any, Sequence

from .sat_guidance import SAT_FEATURE_NAMES


ACTIONS = (
    "fresh_default",
    "reused_default",
    "reused_occurrence",
    "reused_component",
)


def _finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _vector(values: Sequence[float]) -> tuple[float, ...]:
    if (not isinstance(values, (list, tuple))
            or len(values) != len(SAT_FEATURE_NAMES)
            or not all(_finite(value) and abs(value) <= 1e12 for value in values)):
        raise ValueError("invalid SAT guidance feature vector")
    return tuple(float(value) for value in values)


@dataclass(frozen=True)
class SatGuidanceDecision:
    action: str
    reason: str


@dataclass(frozen=True)
class SatGuidanceCostTree:
    tree: dict[str, Any]
    ranges: tuple[tuple[float, float], ...]
    fallback: str
    min_gain: float = 0.03

    def select(self, values: Sequence[float], *, advice: bool = True) -> SatGuidanceDecision:
        if not advice:
            return SatGuidanceDecision(self.fallback, "advice_off")
        try:
            vector = _vector(values)
        except (TypeError, ValueError):
            return SatGuidanceDecision(self.fallback, "invalid_features")
        if any(value < low - 1e-9 or value > high + 1e-9
               for value, (low, high) in zip(vector, self.ranges)):
            return SatGuidanceDecision(self.fallback, "outside_training_range")
        node = self.tree
        while "feature" in node:
            node = node["left"] if vector[node["feature"]] <= node["threshold"] else node["right"]
        costs = node["costs"]
        best = min(range(len(ACTIONS)), key=lambda index: (costs[index], index))
        fallback_cost = costs[ACTIONS.index(self.fallback)]
        if costs[best] >= fallback_cost * (1 - self.min_gain):
            return SatGuidanceDecision(self.fallback, "insufficient_predicted_gain")
        return SatGuidanceDecision(ACTIONS[best], "learned_cost_tree")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "crse-sat-guidance-cost-tree/v1",
            "features": list(SAT_FEATURE_NAMES), "actions": list(ACTIONS),
            "fallback": self.fallback, "min_gain": self.min_gain,
            "ranges": [list(pair) for pair in self.ranges], "tree": self.tree,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "SatGuidanceCostTree":
        fields = {"schema", "features", "actions", "fallback", "min_gain",
                  "ranges", "tree"}
        if (type(data) is not dict or set(data) != fields
                or data.get("schema") != "crse-sat-guidance-cost-tree/v1"
                or data.get("features") != list(SAT_FEATURE_NAMES)
                or data.get("actions") != list(ACTIONS)
                or data.get("fallback") not in ACTIONS
                or not _finite(data.get("min_gain"))
                or not 0 <= data["min_gain"] <= 1):
            raise ValueError("invalid SAT guidance model schema")
        ranges = data["ranges"]
        if type(ranges) is not list or len(ranges) != len(SAT_FEATURE_NAMES):
            raise ValueError("invalid SAT guidance feature ranges")
        for pair in ranges:
            if (type(pair) is not list or len(pair) != 2
                    or not all(_finite(value) and abs(value) <= 1e12 for value in pair)
                    or pair[0] > pair[1]):
                raise ValueError("invalid SAT guidance feature range")

        def check(node: Any, depth: int) -> None:
            if type(node) is not dict or depth > 2:
                raise ValueError("invalid or oversized SAT guidance tree")
            if set(node) == {"costs", "samples"}:
                if (type(node["costs"]) is not list
                        or len(node["costs"]) != len(ACTIONS)
                        or not all(_finite(cost) and 0 < cost <= 1e12
                                   for cost in node["costs"])
                        or type(node["samples"]) is not int
                        or not 1 <= node["samples"] <= 1024):
                    raise ValueError("invalid SAT guidance tree leaf")
                return
            if (set(node) != {"feature", "threshold", "left", "right"}
                    or type(node["feature"]) is not int
                    or not 0 <= node["feature"] < len(SAT_FEATURE_NAMES)
                    or not _finite(node["threshold"])
                    or abs(node["threshold"]) > 1e12):
                raise ValueError("invalid SAT guidance tree split")
            check(node["left"], depth + 1)
            check(node["right"], depth + 1)

        check(data["tree"], 0)
        detached = json.loads(json.dumps(data["tree"], allow_nan=False))
        return cls(detached,
                   tuple(tuple(float(value) for value in pair) for pair in ranges),
                   data["fallback"], float(data["min_gain"]))


def fit_sat_guidance_cost_tree(
    features: Sequence[Sequence[float]], costs: Sequence[Sequence[float]], *,
    max_depth: int = 2, min_leaf: int = 4, min_gain: float = 0.03,
) -> SatGuidanceCostTree:
    if (type(max_depth) is not int or not 0 <= max_depth <= 2
            or type(min_leaf) is not int or not 1 <= min_leaf <= 512
            or not _finite(min_gain) or not 0 <= min_gain <= 1
            or not 1 <= len(features) <= 1024 or len(features) != len(costs)):
        raise ValueError("invalid bounded SAT guidance training contract")
    x = [_vector(row) for row in features]
    normalized = []
    for row in costs:
        if (not isinstance(row, (list, tuple)) or len(row) != len(ACTIONS)
                or not all(_finite(cost) and 0 < cost <= 1e12 for cost in row)):
            raise ValueError("SAT guidance training requires finite positive costs")
        minimum = min(row)
        normalized.append([float(cost) / minimum for cost in row])

    def sums(indices: list[int]) -> list[float]:
        return [sum(normalized[index][action] for index in indices)
                for action in range(len(ACTIONS))]

    def build(indices: list[int], depth: int) -> dict[str, Any]:
        totals = sums(indices)
        leaf = {"costs": [total / len(indices) for total in totals],
                "samples": len(indices)}
        if depth == max_depth or len(indices) < 2 * min_leaf:
            return leaf
        best_loss, best = min(totals), None
        for feature in range(len(SAT_FEATURE_NAMES)):
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
                    best_loss, best = loss, (feature, threshold, left, right)
        if best is None:
            return leaf
        feature, threshold, left, right = best
        return {"feature": feature, "threshold": threshold,
                "left": build(left, depth + 1), "right": build(right, depth + 1)}

    indices = list(range(len(x)))
    totals = sums(indices)
    fallback = ACTIONS[min(range(len(ACTIONS)),
                           key=lambda action: (totals[action], action))]
    model = SatGuidanceCostTree(
        build(indices, 0),
        tuple((min(row[index] for row in x), max(row[index] for row in x))
              for index in range(len(SAT_FEATURE_NAMES))),
        fallback, float(min_gain))
    return SatGuidanceCostTree.from_dict(model.to_dict())
