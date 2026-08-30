"""Sharing-preserving Boolean DAG tensors for universes through ten variables."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from cm_expr_serde import expr_from_json, expr_to_json_dag

from .decomposition_data import MAX_VARS, canonical
from .portfolio import admit

OPS = ("var", "not", "and", "or", "xor", "imp", "eqv")
EDGE_ROLES = ("unary", "left", "right")
MAX_GRAPH_NODES = 4096
NODE_FEATURES = len(OPS) + MAX_VARS + MAX_VARS


@dataclass(frozen=True)
class VariableGraphInput:
    node_features: np.ndarray
    edge_index: np.ndarray
    edge_roles: np.ndarray
    root: int
    n_vars: int
    document_sha256: str

    def __post_init__(self):
        nodes, edges = len(self.node_features), len(self.edge_roles)
        if (type(self.node_features) is not np.ndarray or self.node_features.dtype != np.float32
                or self.node_features.shape != (nodes, NODE_FEATURES) or not 1 <= nodes <= MAX_GRAPH_NODES
                or type(self.edge_index) is not np.ndarray or self.edge_index.dtype != np.int64
                or self.edge_index.shape != (2, edges) or type(self.edge_roles) is not np.ndarray
                or self.edge_roles.dtype != np.int64 or self.edge_roles.shape != (edges,)
                or type(self.root) is not int or not 0 <= self.root < nodes
                or type(self.n_vars) is not int or not 2 <= self.n_vars <= MAX_VARS
                or type(self.document_sha256) is not str or len(self.document_sha256) != 64):
            raise ValueError("invalid bounded variable graph tensors")
        if (not np.isin(self.node_features, (0.0, 1.0)).all()
                or np.any(self.node_features[:, :len(OPS)].sum(axis=1) != 1)
                or np.any(self.node_features[:, len(OPS) + MAX_VARS:].sum(axis=1) != 1)
                or (edges and (self.edge_index.min() < 0 or self.edge_index.max() >= nodes))
                or (edges and (self.edge_roles.min() < 0 or self.edge_roles.max() >= len(EDGE_ROLES)))):
            raise ValueError("invalid variable graph feature values")

    @property
    def memory_bytes(self) -> int:
        return self.node_features.nbytes + self.edge_index.nbytes + self.edge_roles.nbytes


def graph_from_document(document: dict[str, Any], n_vars: int) -> VariableGraphInput:
    if type(n_vars) is not int or not 2 <= n_vars <= MAX_VARS:
        raise ValueError("graph variable universe outside 2..10")
    expr = expr_from_json(document)
    admit(expr, n_vars, 1)
    if expr_to_json_dag(expr) != document or len(document["nodes"]) > MAX_GRAPH_NODES:
        raise ValueError("noncanonical or oversized Boolean DAG")
    nodes = document["nodes"]
    features = np.zeros((len(nodes), NODE_FEATURES), dtype=np.float32)
    sources: list[int] = []
    destinations: list[int] = []
    roles: list[int] = []
    for index, node in enumerate(nodes):
        op = node["op"]
        if op not in OPS:
            raise ValueError("unsupported Boolean DAG operation")
        features[index, OPS.index(op)] = 1.0
        features[index, len(OPS) + MAX_VARS + n_vars - 1] = 1.0
        if op == "var":
            variable = node["i"]
            if type(variable) is not int or not 0 <= variable < n_vars:
                raise ValueError("variable outside declared universe")
            features[index, len(OPS) + variable] = 1.0
        elif op == "not":
            references = ((node["a"], "unary"),)
            for source, role in references:
                if type(source) is not int or not 0 <= source < index:
                    raise ValueError("non-topological graph reference")
                sources.append(source); destinations.append(index); roles.append(EDGE_ROLES.index(role))
        else:
            references = ((node["a"], "left"), (node["b"], "right"))
            for source, role in references:
                if type(source) is not int or not 0 <= source < index:
                    raise ValueError("non-topological graph reference")
                sources.append(source); destinations.append(index); roles.append(EDGE_ROLES.index(role))
    edge_index = (np.asarray((sources, destinations), dtype=np.int64) if sources
                  else np.empty((2, 0), dtype=np.int64))
    return VariableGraphInput(features, edge_index, np.asarray(roles, dtype=np.int64), document["root"],
                              n_vars, hashlib.sha256(canonical(document)).hexdigest())


def graph_schema_document() -> dict[str, Any]:
    return {
        "schema": "crse-variable-bool-dag-graph/v1",
        "node_features": {"operator_one_hot": list(OPS), "variable_identity_one_hot": list(range(MAX_VARS)),
                          "ambient_size_one_hot": list(range(1, MAX_VARS + 1))},
        "edge_direction": "child-to-parent", "edge_roles": list(EDGE_ROLES),
        "root": "explicit-node-index", "sharing": "one encoded node per canonical v2 DAG node",
        "bounds": {"variables": MAX_VARS, "nodes": MAX_GRAPH_NODES},
    }
