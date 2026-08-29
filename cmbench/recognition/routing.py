"""Versioned feature ablations without changing the original tree contract."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from cm_exprlib import Expr, Not, Var

from .features import FEATURE_NAMES, extract_features, postorder
from .learning import CostTree, Decision, fit_cost_tree

SCHEMAS = ("full/v1", "queries/v1", "queries-depth/v1")


def project_features(values: tuple[float, ...], schema: str) -> tuple[float, ...]:
    if schema not in SCHEMAS or len(values) != len(FEATURE_NAMES):
        raise ValueError("unknown or mismatched feature schema")
    if schema == "full/v1":
        return values
    return tuple(v if j == 1 or (schema == "queries-depth/v1" and j == 3) else 0.0
                 for j, v in enumerate(values))


def routing_features(expr: Expr, n_vars: int, queries: int, schema: str) -> tuple[float, ...]:
    """Input admission is common to all arms, before their timers."""
    if schema not in SCHEMAS or type(queries) is not int or not 1 <= queries <= 256:
        raise ValueError("invalid routing feature request")
    if schema == "full/v1":
        return extract_features(expr, n_vars, queries).values
    values = [0.0] * len(FEATURE_NAMES)
    values[1] = math.log2(queries)
    if schema == "queries-depth/v1":
        depths = {}
        for node in postorder(expr):
            children = () if type(node) is Var else (node.a,) if type(node) is Not else (node.a, node.b)
            depths[id(node)] = 1 + max((depths[id(c)] for c in children), default=0)
        values[3] = float(depths[id(expr)])
    return tuple(values)


def query_rule(queries: int) -> str:
    if type(queries) is not int or not 1 <= queries <= 256:
        raise ValueError("invalid query count")
    # Predeclared compile-amortization control, not a fitted universal crossover.
    return "direct" if queries <= 2 else "cse"


@dataclass(frozen=True)
class FeatureRouter:
    feature_schema: str
    model: CostTree

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "crse-feature-router/v1", "feature_schema": self.feature_schema,
                "projection": "unused-original-dimensions-zero/v1", "model": self.model.to_dict()}

    @classmethod
    def from_dict(cls, data: Any) -> FeatureRouter:
        if (type(data) is not dict or set(data) != {"schema", "feature_schema", "projection", "model"}
                or data["schema"] != "crse-feature-router/v1" or data["feature_schema"] not in SCHEMAS
                or data["projection"] != "unused-original-dimensions-zero/v1"):
            raise ValueError("invalid feature router")
        model = CostTree.from_dict(data["model"])
        active = project_features(tuple(1.0 for _ in FEATURE_NAMES), data["feature_schema"])
        if any(not enabled and pair != (0.0, 0.0) for enabled, pair in zip(active, model.ranges)):
            raise ValueError("model ranges do not match feature projection")
        return cls(data["feature_schema"], model)

    def select(self, values: tuple[float, ...]) -> Decision:
        return self.model.select(values)


def fit_router(features, costs, schema: str) -> FeatureRouter:
    model = fit_cost_tree([project_features(tuple(v), schema) for v in features], costs)
    return FeatureRouter.from_dict(FeatureRouter(schema, model).to_dict())
