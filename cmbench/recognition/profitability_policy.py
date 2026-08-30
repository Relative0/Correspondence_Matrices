"""Small inert cost tree for choosing no rewrite or one proved-rule pass."""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


POLICY_SCHEMA = "crse-profitability-policy/v1"
CALIBRATION_SCHEMA = "crse-profitability-environment-calibration/v1"
FEATURE_NAMES = (
    "support",
    "log2_reuses",
    "log2_source_nodes",
    "source_depth",
    "log2_source_edges",
    "log2_local_cubes",
    "calibrated_rewrite_pressure",
)
ACTIONS = ("no_rewrite", "one_pass")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_document(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _is_finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


@dataclass(frozen=True)
class ProfitabilityMetadata:
    support: int
    expected_reuses: int
    source_nodes: int
    source_edges: int
    depth: int
    local_cubes: int
    local_literals: int

    def validate(self) -> None:
        if (type(self.support) is not int or not 1 <= self.support <= 16
                or type(self.expected_reuses) is not int or not 1 <= self.expected_reuses <= 256
                or type(self.source_nodes) is not int or not 1 <= self.source_nodes <= 4096
                or type(self.source_edges) is not int or not 0 <= self.source_edges <= 24_576
                or type(self.depth) is not int or not 1 <= self.depth <= 4096
                or type(self.local_cubes) is not int or not 1 <= self.local_cubes <= 64
                or type(self.local_literals) is not int or not 0 <= self.local_literals <= 384):
            raise ValueError("invalid profitability metadata")


@dataclass(frozen=True)
class EnvironmentCalibration:
    document: dict[str, Any]

    @classmethod
    def from_dict(cls, value: Any) -> "EnvironmentCalibration":
        required = {"schema", "environment", "probe", "matcher_node_ns",
                    "kernel_node_execution_ns", "semantic_mismatches"}
        if type(value) is not dict or set(value) != required:
            raise ValueError("invalid calibration fields")
        if (value["schema"] != CALIBRATION_SCHEMA or type(value["environment"]) is not dict
                or type(value["probe"]) is not dict
                or not _is_finite(value["matcher_node_ns"]) or value["matcher_node_ns"] <= 0
                or not _is_finite(value["kernel_node_execution_ns"])
                or value["kernel_node_execution_ns"] <= 0
                or value["semantic_mismatches"] != 0):
            raise ValueError("invalid calibration values")
        detached = json.loads(json.dumps(value, allow_nan=False))
        return cls(detached)

    @property
    def digest(self) -> str:
        return sha256_document(self.document)

    @property
    def matcher_node_ns(self) -> float:
        return float(self.document["matcher_node_ns"])

    @property
    def kernel_node_execution_ns(self) -> float:
        return float(self.document["kernel_node_execution_ns"])


def feature_vector(metadata: ProfitabilityMetadata,
                   calibration: EnvironmentCalibration) -> tuple[float, ...]:
    metadata.validate()
    predicted_rewrite = calibration.matcher_node_ns * (
        metadata.source_nodes + metadata.local_literals / 2)
    predicted_execution = calibration.kernel_node_execution_ns * max(
        1, metadata.source_nodes + metadata.source_edges) * metadata.expected_reuses
    return (
        float(metadata.support),
        math.log2(metadata.expected_reuses),
        math.log2(metadata.source_nodes),
        float(metadata.depth),
        math.log2(metadata.source_edges + 1),
        math.log2(metadata.local_cubes + 1),
        math.log2((predicted_rewrite + 1) / (predicted_execution + 1)),
    )


@dataclass(frozen=True)
class PolicyDecision:
    action: str
    reason: str
    decision_ns: int


@dataclass(frozen=True)
class ProfitabilityTree:
    tree: dict[str, Any]
    ranges: tuple[tuple[float, float], ...]
    calibration_sha256: str
    training_manifest_sha256: str
    min_gain: float = 0.05

    def decide(self, metadata: ProfitabilityMetadata,
               calibration: EnvironmentCalibration) -> PolicyDecision:
        started = time.perf_counter_ns()
        if calibration.digest != self.calibration_sha256:
            return PolicyDecision("no_rewrite", "calibration_identity_mismatch",
                                  max(1, time.perf_counter_ns() - started))
        try:
            vector = feature_vector(metadata, calibration)
        except (TypeError, ValueError, OverflowError):
            return PolicyDecision("no_rewrite", "invalid_metadata",
                                  max(1, time.perf_counter_ns() - started))
        if any(value < low - 1e-12 or value > high + 1e-12
               for value, (low, high) in zip(vector, self.ranges)):
            return PolicyDecision("no_rewrite", "outside_training_range",
                                  max(1, time.perf_counter_ns() - started))
        node = self.tree
        while "feature" in node:
            node = node["left"] if vector[node["feature"]] <= node["threshold"] else node["right"]
        costs = node["costs"]
        best = min(range(len(ACTIONS)), key=lambda index: (costs[index], index))
        if best == 0 or costs[best] >= costs[0] * (1 - self.min_gain):
            action, reason = "no_rewrite", "insufficient_predicted_gain"
        else:
            action, reason = "one_pass", "learned_profitable"
        return PolicyDecision(action, reason, max(1, time.perf_counter_ns() - started))

    def to_dict(self) -> dict[str, Any]:
        return {"schema": POLICY_SCHEMA, "features": list(FEATURE_NAMES),
            "actions": list(ACTIONS), "fallback": "no_rewrite", "min_gain": self.min_gain,
            "ranges": [list(pair) for pair in self.ranges], "tree": self.tree,
            "calibration_sha256": self.calibration_sha256,
            "training_manifest_sha256": self.training_manifest_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "ProfitabilityTree":
        required = {"schema", "features", "actions", "fallback", "min_gain", "ranges",
                    "tree", "calibration_sha256", "training_manifest_sha256"}
        if type(value) is not dict or set(value) != required:
            raise ValueError("invalid profitability policy fields")
        if (value["schema"] != POLICY_SCHEMA or value["features"] != list(FEATURE_NAMES)
                or value["actions"] != list(ACTIONS) or value["fallback"] != "no_rewrite"
                or not _is_finite(value["min_gain"]) or not 0 <= value["min_gain"] <= 1
                or not _hash(value["calibration_sha256"])
                or not _hash(value["training_manifest_sha256"])):
            raise ValueError("invalid profitability policy identity")
        ranges = value["ranges"]
        if type(ranges) is not list or len(ranges) != len(FEATURE_NAMES):
            raise ValueError("invalid profitability policy ranges")
        for pair in ranges:
            if (type(pair) is not list or len(pair) != 2
                    or not all(_is_finite(item) and abs(item) <= 1e12 for item in pair)
                    or pair[0] > pair[1]):
                raise ValueError("invalid profitability policy range")

        def validate_node(node: Any, depth: int) -> None:
            if type(node) is not dict or depth > 3:
                raise ValueError("invalid profitability tree")
            if set(node) == {"costs", "samples"}:
                if (type(node["costs"]) is not list or len(node["costs"]) != len(ACTIONS)
                        or not all(_is_finite(cost) and 0 < cost <= 1e12 for cost in node["costs"])
                        or type(node["samples"]) is not int or not 1 <= node["samples"] <= 512):
                    raise ValueError("invalid profitability leaf")
                return
            if (set(node) != {"feature", "threshold", "left", "right"}
                    or type(node["feature"]) is not int
                    or not 0 <= node["feature"] < len(FEATURE_NAMES)
                    or not _is_finite(node["threshold"]) or abs(node["threshold"]) > 1e12):
                raise ValueError("invalid profitability split")
            validate_node(node["left"], depth + 1)
            validate_node(node["right"], depth + 1)

        validate_node(value["tree"], 0)
        return cls(json.loads(json.dumps(value["tree"], allow_nan=False)),
                   tuple(tuple(float(item) for item in pair) for pair in ranges),
                   value["calibration_sha256"], value["training_manifest_sha256"],
                   float(value["min_gain"]))

    def save(self, path: Path) -> None:
        with Path(path).open("xb") as handle:
            handle.write(json.dumps(self.to_dict(), indent=2, sort_keys=True,
                                    allow_nan=False).encode("utf-8") + b"\n")

    @classmethod
    def load(cls, path: Path) -> "ProfitabilityTree":
        raw = Path(path).read_bytes()
        if len(raw) > 65_536:
            raise ValueError("profitability policy exceeds 64 KiB")
        return cls.from_dict(json.loads(raw))


def fit_profitability_tree(features: Sequence[Sequence[float]],
                           costs: Sequence[Sequence[float]], *,
                           calibration_sha256: str,
                           training_manifest_sha256: str,
                           max_depth: int = 3, min_leaf: int = 3,
                           min_gain: float = 0.05) -> ProfitabilityTree:
    if (not 1 <= len(features) <= 512 or len(features) != len(costs)
            or type(max_depth) is not int or not 0 <= max_depth <= 3
            or type(min_leaf) is not int or not 1 <= min_leaf <= 512
            or not _is_finite(min_gain) or not 0 <= min_gain <= 1
            or not _hash(calibration_sha256) or not _hash(training_manifest_sha256)):
        raise ValueError("invalid profitability training contract")
    vectors = []
    normalized_costs = []
    for vector, row in zip(features, costs):
        if (len(vector) != len(FEATURE_NAMES)
                or not all(_is_finite(value) and abs(value) <= 1e12 for value in vector)
                or len(row) != len(ACTIONS)
                or not all(_is_finite(cost) and 0 < cost <= 1e12 for cost in row)):
            raise ValueError("invalid profitability training row")
        vectors.append(tuple(float(value) for value in vector))
        best = min(row)
        normalized_costs.append(tuple(float(cost / best) for cost in row))

    def sums(indices: list[int]) -> list[float]:
        return [sum(normalized_costs[index][action] for index in indices)
                for action in range(len(ACTIONS))]

    def build(indices: list[int], depth: int) -> dict[str, Any]:
        totals = sums(indices)
        leaf = {"costs": [total / len(indices) for total in totals], "samples": len(indices)}
        if depth == max_depth or len(indices) < 2 * min_leaf:
            return leaf
        best_loss = min(totals)
        best_split = None
        for feature_index in range(len(FEATURE_NAMES)):
            unique = sorted({vectors[index][feature_index] for index in indices})
            thresholds = [(left + right) / 2 for left, right in zip(unique, unique[1:])]
            if len(thresholds) > 32:
                thresholds = [thresholds[(index * (len(thresholds) - 1)) // 31]
                              for index in range(32)]
            for threshold in thresholds:
                left = [index for index in indices if vectors[index][feature_index] <= threshold]
                right = [index for index in indices if vectors[index][feature_index] > threshold]
                if min(len(left), len(right)) < min_leaf:
                    continue
                loss = min(sums(left)) + min(sums(right))
                if loss < best_loss - 1e-12:
                    best_loss, best_split = loss, (feature_index, threshold, left, right)
        if best_split is None:
            return leaf
        feature_index, threshold, left, right = best_split
        return {"feature": feature_index, "threshold": threshold,
                "left": build(left, depth + 1), "right": build(right, depth + 1)}

    all_indices = list(range(len(vectors)))
    model = ProfitabilityTree(build(all_indices, 0),
        tuple((min(row[index] for row in vectors), max(row[index] for row in vectors))
              for index in range(len(FEATURE_NAMES))),
        calibration_sha256, training_manifest_sha256, min_gain)
    return ProfitabilityTree.from_dict(model.to_dict())
