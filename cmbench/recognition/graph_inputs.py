"""Bounded, sharing-preserving graph inputs for optional neural experiments."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np

from .motif_data import decode_bounded_dag

GRAPH_SCHEMA = "crse-bool-dag-graph/v1"
OPS = ("var", "not", "and", "or", "xor", "imp", "eqv")
EDGE_ROLES = ("unary", "left", "right")
MAX_GRAPH_NODES = 4096
NODE_FEATURES = len(OPS) + 8


def _canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class GraphInput:
    """One admitted Boolean DAG with explicit operator, variable and edge roles."""

    node_features: np.ndarray
    edge_index: np.ndarray
    edge_roles: np.ndarray
    root: int
    n_vars: int
    document_sha256: str

    def __post_init__(self) -> None:
        n = len(self.node_features)
        e = len(self.edge_roles)
        if (type(self.node_features) is not np.ndarray or self.node_features.dtype != np.float32
                or self.node_features.shape != (n, NODE_FEATURES) or not 1 <= n <= MAX_GRAPH_NODES
                or type(self.edge_index) is not np.ndarray or self.edge_index.dtype != np.int64
                or self.edge_index.shape != (2, e) or type(self.edge_roles) is not np.ndarray
                or self.edge_roles.dtype != np.int64 or self.edge_roles.shape != (e,)
                or type(self.root) is not int or not 0 <= self.root < n
                or type(self.n_vars) is not int or not 1 <= self.n_vars <= 8
                or type(self.document_sha256) is not str or len(self.document_sha256) != 64):
            raise ValueError("invalid bounded graph tensors")
        if (not np.isin(self.node_features, [0.0, 1.0]).all()
                or np.any(self.node_features[:, :len(OPS)].sum(axis=1) != 1)
                or (e and (self.edge_index.min() < 0 or self.edge_index.max() >= n))
                or (e and (self.edge_roles.min() < 0 or self.edge_roles.max() >= len(EDGE_ROLES)))):
            raise ValueError("invalid graph feature values or references")

    @property
    def memory_bytes(self) -> int:
        return self.node_features.nbytes + self.edge_index.nbytes + self.edge_roles.nbytes


def graph_from_document(document: dict[str, Any], n_vars: int = 8,
                        max_nodes: int = MAX_GRAPH_NODES) -> GraphInput:
    """Validate and encode a v2 expression DAG without unfolding shared nodes."""
    decode_bounded_dag(document, n_vars=n_vars, max_nodes=max_nodes)
    nodes = document["nodes"]
    features = np.zeros((len(nodes), NODE_FEATURES), dtype=np.float32)
    sources: list[int] = []
    destinations: list[int] = []
    roles: list[int] = []
    for index, node in enumerate(nodes):
        op = node["op"]
        features[index, OPS.index(op)] = 1.0
        if op == "var":
            features[index, len(OPS) + node["i"]] = 1.0
        elif op == "not":
            sources.append(node["a"])
            destinations.append(index)
            roles.append(EDGE_ROLES.index("unary"))
        else:
            sources.extend((node["a"], node["b"]))
            destinations.extend((index, index))
            roles.extend((EDGE_ROLES.index("left"), EDGE_ROLES.index("right")))
    edge_index = np.asarray((sources, destinations), dtype=np.int64)
    if not sources:
        edge_index = np.empty((2, 0), dtype=np.int64)
    return GraphInput(features, edge_index, np.asarray(roles, dtype=np.int64),
                      document["root"], n_vars, hashlib.sha256(_canonical(document)).hexdigest())


def graph_schema_document() -> dict[str, Any]:
    return {
        "schema": GRAPH_SCHEMA,
        "node_features": {"operator_one_hot": list(OPS), "variable_identity_one_hot": list(range(8))},
        "edge_direction": "child-to-parent",
        "edge_roles": list(EDGE_ROLES),
        "root": "explicit-node-index",
        "sharing": "one encoded node per v2 DAG node; repeated references remain shared",
        "negation": "explicit not operator node",
        "bounds": {"variables": 8, "nodes": MAX_GRAPH_NODES},
    }
