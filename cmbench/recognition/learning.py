"""A small cost-sensitive decision tree learned from measured training costs.

This stores thresholds and average relative costs, never expressions, truth
tables, or a nearest-neighbour lookup table. Models are inert bounded JSON.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .features import FEATURE_NAMES, FEATURE_VERSION
from .portfolio import BACKENDS


def _finite(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _vector(values: Sequence[float]) -> tuple[float, ...]:
    if len(values) != len(FEATURE_NAMES) or not all(_finite(v) and abs(v) <= 1e12 for v in values):
        raise ValueError("invalid feature vector")
    return tuple(float(v) for v in values)


@dataclass(frozen=True)
class Decision:
    backend: str
    reason: str


@dataclass(frozen=True)
class CostTree:
    tree: dict[str, Any]
    ranges: tuple[tuple[float, float], ...]
    fallback: str
    min_gain: float = 0.05

    def select(self, values: Sequence[float]) -> Decision:
        try:
            vector = _vector(values)
        except (TypeError, ValueError):
            return Decision(self.fallback, "invalid_features")
        if any(v < low - 1e-9 or v > high + 1e-9
               for v, (low, high) in zip(vector, self.ranges)):
            return Decision(self.fallback, "outside_training_range")
        node = self.tree
        while "feature" in node:
            node = node["left"] if vector[node["feature"]] <= node["threshold"] else node["right"]
        costs = node["costs"]
        best = min(range(len(BACKENDS)), key=lambda i: (costs[i], i))
        fallback_cost = costs[BACKENDS.index(self.fallback)]
        if costs[best] >= fallback_cost * (1 - self.min_gain):
            return Decision(self.fallback, "insufficient_predicted_gain")
        return Decision(BACKENDS[best], "learned")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "crse-cost-tree/v1", "feature_version": FEATURE_VERSION,
            "features": list(FEATURE_NAMES), "backends": list(BACKENDS),
            "fallback": self.fallback, "min_gain": self.min_gain,
            "ranges": [list(pair) for pair in self.ranges], "tree": self.tree,
        }

    @classmethod
    def from_dict(cls, data: Any) -> CostTree:
        keys = {"schema", "feature_version", "features", "backends", "fallback",
                "min_gain", "ranges", "tree"}
        if type(data) is not dict or set(data) != keys:
            raise ValueError("invalid model fields")
        if (data["schema"] != "crse-cost-tree/v1"
                or type(data["feature_version"]) is not int
                or data["feature_version"] != FEATURE_VERSION
                or data["features"] != list(FEATURE_NAMES)
                or data["backends"] != list(BACKENDS)
                or data["fallback"] not in BACKENDS):
            raise ValueError("model schema or portfolio mismatch")
        if not _finite(data["min_gain"]) or not 0 <= data["min_gain"] <= 1:
            raise ValueError("invalid gain threshold")
        ranges = data["ranges"]
        if type(ranges) is not list or len(ranges) != len(FEATURE_NAMES):
            raise ValueError("invalid feature ranges")
        for pair in ranges:
            if (type(pair) is not list or len(pair) != 2
                    or not all(_finite(v) and abs(v) <= 1e12 for v in pair) or pair[0] > pair[1]):
                raise ValueError("invalid feature range")

        def check(node: Any, depth: int) -> None:
            if depth > 3 or type(node) is not dict:
                raise ValueError("invalid or oversized tree")
            if set(node) == {"costs", "samples"}:
                costs = node["costs"]
                if (type(costs) is not list or len(costs) != len(BACKENDS)
                        or not all(_finite(c) and 0 < c <= 1e12 for c in costs)
                        or type(node["samples"]) is not int or not 1 <= node["samples"] <= 512):
                    raise ValueError("invalid leaf")
                return
            if set(node) != {"feature", "threshold", "left", "right"}:
                raise ValueError("invalid tree node fields")
            if (type(node["feature"]) is not int or not 0 <= node["feature"] < len(FEATURE_NAMES)
                    or not _finite(node["threshold"]) or abs(node["threshold"]) > 1e12):
                raise ValueError("invalid split")
            check(node["left"], depth + 1)
            check(node["right"], depth + 1)

        check(data["tree"], 0)
        # Detach validated containers so callers cannot mutate the source document.
        tree = json.loads(json.dumps(data["tree"], allow_nan=False))
        return cls(tree, tuple(tuple(float(v) for v in p) for p in ranges),
                   data["fallback"], float(data["min_gain"]))


def fit_cost_tree(
    features: Sequence[Sequence[float]], costs: Sequence[Sequence[float]],
    *, max_depth: int = 3, min_leaf: int = 4,
) -> CostTree:
    if (type(max_depth) is not int or not 0 <= max_depth <= 3
            or type(min_leaf) is not int or not 1 <= min_leaf <= 512):
        raise ValueError("invalid tree bounds")
    if not 1 <= len(features) <= 512 or len(features) != len(costs):
        raise ValueError("invalid training row count")
    x = [_vector(row) for row in features]
    y = []
    for row in costs:
        if len(row) != len(BACKENDS) or not all(_finite(c) and 0 < c <= 1e12 for c in row):
            raise ValueError("training requires positive finite costs for every backend")
        best = min(row)
        normalized = [float(c / best) for c in row]
        if max(normalized) > 1e12:
            raise ValueError("training cost ratio exceeds bounds")
        y.append(normalized)

    def sums(indices: list[int]) -> list[float]:
        return [sum(y[i][b] for i in indices) for b in range(len(BACKENDS))]

    def build(indices: list[int], depth: int) -> dict[str, Any]:
        totals = sums(indices)
        leaf = {"costs": [s / len(indices) for s in totals], "samples": len(indices)}
        if depth == max_depth or len(indices) < 2 * min_leaf:
            return leaf
        best_loss = min(totals)
        best_split = None
        for feature in range(len(FEATURE_NAMES)):
            unique = sorted({x[i][feature] for i in indices})
            thresholds = [(a + b) / 2 for a, b in zip(unique, unique[1:])]
            # Bounded deterministic threshold search; never consult validation/test.
            if len(thresholds) > 32:
                thresholds = [thresholds[(j * (len(thresholds) - 1)) // 31] for j in range(32)]
            for threshold in thresholds:
                left = [i for i in indices if x[i][feature] <= threshold]
                right = [i for i in indices if x[i][feature] > threshold]
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

    all_indices = list(range(len(x)))
    totals = sums(all_indices)
    fallback = BACKENDS[min(range(len(BACKENDS)), key=lambda b: (totals[b], b))]
    model = CostTree(
        build(all_indices, 0),
        tuple((min(row[j] for row in x), max(row[j] for row in x)) for j in range(len(FEATURE_NAMES))),
        fallback,
    )
    return CostTree.from_dict(model.to_dict())


def load_model(path: Path) -> CostTree:
    with path.open("rb") as handle:
        raw = handle.read(65_537)
    if len(raw) > 65_536:
        raise ValueError("model exceeds 64 KiB")

    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError("nonfinite JSON")

    try:
        data = json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("invalid model JSON") from exc
    return CostTree.from_dict(data)
