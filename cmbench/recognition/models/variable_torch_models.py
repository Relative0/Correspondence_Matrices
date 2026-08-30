"""Variable-size CM/GNN models with inert, hash-checked JSON artifacts."""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from ..variable_graph_inputs import EDGE_ROLES, NODE_FEATURES, VariableGraphInput, graph_schema_document
from .mlp import _array, _array_document, canonical, read_json

SCHEMA = "crse-pytorch-variable-decomposition-model/v1"
MAX_MODEL_BYTES = 8 * 1024 * 1024
MAX_PARAMETERS = 200_000
MIN_PARAMETERS = 25_000


@dataclass(frozen=True)
class GraphBatch:
    node_features: torch.Tensor
    edge_index: torch.Tensor
    edge_roles: torch.Tensor
    graph_index: torch.Tensor
    roots: torch.Tensor
    ptr: torch.Tensor


def batch_graphs(graphs: Sequence[VariableGraphInput]) -> GraphBatch:
    if not 1 <= len(graphs) <= 512 or any(type(graph) is not VariableGraphInput for graph in graphs):
        raise ValueError("invalid bounded graph batch")
    features, edges, roles, graph_indices, roots, ptr = [], [], [], [], [], [0]
    offset = 0
    for graph_number, graph in enumerate(graphs):
        features.append(graph.node_features)
        if graph.edge_index.shape[1]:
            edges.append(graph.edge_index + offset)
            roles.append(graph.edge_roles)
        graph_indices.append(np.full(len(graph.node_features), graph_number, dtype=np.int64))
        roots.append(graph.root + offset)
        offset += len(graph.node_features)
        ptr.append(offset)
    return GraphBatch(
        torch.from_numpy(np.concatenate(features)),
        torch.from_numpy(np.concatenate(edges, axis=1) if edges else np.empty((2, 0), dtype=np.int64)),
        torch.from_numpy(np.concatenate(roles) if roles else np.empty(0, dtype=np.int64)),
        torch.from_numpy(np.concatenate(graph_indices)), torch.tensor(roots, dtype=torch.int64),
        torch.tensor(ptr, dtype=torch.int64),
    )


class GraphLayer(nn.Module):
    def __init__(self, hidden: int):
        super().__init__()
        self.self_linear = nn.Linear(hidden, hidden)
        self.role_linears = nn.ModuleList(nn.Linear(hidden, hidden, bias=False) for _ in EDGE_ROLES)

    def forward(self, values: torch.Tensor, graph: GraphBatch) -> torch.Tensor:
        aggregate = torch.zeros_like(values)
        source, destination = graph.edge_index
        for role, linear in enumerate(self.role_linears):
            mask = graph.edge_roles == role
            if bool(mask.any()):
                aggregate.index_add_(0, destination[mask], linear(values[source[mask]]))
        degree = torch.zeros((len(values), 1), dtype=values.dtype, device=values.device)
        if len(destination):
            degree.index_add_(0, destination, torch.ones((len(destination), 1), dtype=values.dtype,
                                                          device=values.device))
        return F.relu(self.self_linear(values) + aggregate / degree.clamp_min(1.0))


class GraphEncoder(nn.Module):
    def __init__(self, hidden: int, layers: int, output: int):
        super().__init__()
        self.node_input = nn.Linear(NODE_FEATURES, hidden)
        self.layers = nn.ModuleList(GraphLayer(hidden) for _ in range(layers))
        self.readout = nn.Linear(hidden * 3, output)

    def forward(self, graph: GraphBatch) -> torch.Tensor:
        values = F.relu(self.node_input(graph.node_features))
        for layer in self.layers:
            values = layer(values, graph)
        count = len(graph.roots)
        sums = torch.zeros((count, values.shape[1]), dtype=values.dtype, device=values.device)
        sums.index_add_(0, graph.graph_index, values)
        sizes = (graph.ptr[1:] - graph.ptr[:-1]).to(values.dtype).unsqueeze(1)
        means = sums / sizes
        maxima = torch.stack([values[int(graph.ptr[i]):int(graph.ptr[i + 1])].max(dim=0).values
                              for i in range(count)])
        roots = values[graph.roots]
        return F.relu(self.readout(torch.cat((roots, means, maxima), dim=1)))


def multiscale_features(matrix: torch.Tensor) -> torch.Tensor:
    if matrix.ndim != 4 or matrix.shape[1:] != (2, 32, 32):
        raise ValueError("expected two-channel 32x32 CM images")
    return torch.cat([F.adaptive_avg_pool2d(matrix, size).flatten(1) for size in (1, 2, 4, 8)], dim=1)


class VariableMatrixMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = nn.Sequential(nn.Flatten(), nn.Linear(2048, 48), nn.ReLU(), nn.Linear(48, 32), nn.ReLU())
        self.head = nn.Linear(32, 1)

    def forward(self, matrix=None, graph=None):
        if matrix is None:
            raise ValueError("matrix input required")
        embedding = self.backbone(matrix)
        return self.head(embedding).squeeze(1), embedding


class MultiScaleCM(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = nn.Sequential(nn.Linear(170, 256), nn.ReLU(), nn.Linear(256, 64), nn.ReLU())
        self.head = nn.Linear(64, 1)

    def forward(self, matrix=None, graph=None):
        if matrix is None:
            raise ValueError("matrix input required")
        embedding = self.backbone(multiscale_features(matrix))
        return self.head(embedding).squeeze(1), embedding


class VariableGraphGNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = GraphEncoder(64, 4, 64)
        self.head = nn.Linear(64, 1)

    def forward(self, matrix=None, graph=None):
        if graph is None:
            raise ValueError("graph input required")
        embedding = self.encoder(graph)
        return self.head(embedding).squeeze(1), embedding


class VariableFused(nn.Module):
    def __init__(self):
        super().__init__()
        self.matrix = nn.Sequential(nn.Linear(170, 128), nn.ReLU(), nn.Linear(128, 32), nn.ReLU())
        self.graph = GraphEncoder(48, 3, 32)
        self.fusion = nn.Sequential(nn.Linear(64, 64), nn.ReLU())
        self.head = nn.Linear(64, 1)

    def forward(self, matrix=None, graph=None):
        if matrix is None or graph is None:
            raise ValueError("matrix and graph inputs required")
        embedding = self.fusion(torch.cat((self.matrix(multiscale_features(matrix)), self.graph(graph)), dim=1))
        return self.head(embedding).squeeze(1), embedding


ARCHITECTURES: dict[str, dict[str, Any]] = {
    "variable_matrix_mlp": {"name": "variable_matrix_mlp", "task": "balanced-xor-decomposition",
        "layers": [2048, 48, 32, 1], "matrix_layout": "channels(values,valid-mask)-32x32"},
    "multiscale_cm": {"name": "multiscale_cm", "task": "balanced-xor-decomposition",
        "pool_sizes": [1, 2, 4, 8], "layers": [170, 256, 64, 1],
        "matrix_layout": "shared adaptive blocks over channels(values,valid-mask)-32x32"},
    "variable_graph_gnn": {"name": "variable_graph_gnn", "task": "balanced-xor-decomposition",
        "node_features": NODE_FEATURES, "hidden": 64, "message_layers": 4, "embedding": 64,
        "graph_schema": graph_schema_document()},
    "variable_fused": {"name": "variable_fused", "task": "balanced-xor-decomposition",
        "matrix_pool_sizes": [1, 2, 4, 8], "graph_hidden": 48, "message_layers": 3,
        "embedding": 64, "graph_schema": graph_schema_document()},
}


def build_model(name: str) -> nn.Module:
    builders = {"variable_matrix_mlp": VariableMatrixMLP, "multiscale_cm": MultiScaleCM,
                "variable_graph_gnn": VariableGraphGNN, "variable_fused": VariableFused}
    if name not in builders:
        raise ValueError("unsupported variable-size architecture")
    model = builders[name]()
    if not MIN_PARAMETERS <= parameter_count(model) <= MAX_PARAMETERS:
        raise ValueError("variable-size architecture outside approved parameter band")
    return model


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def state_sha256(model: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(tensor.detach().cpu().contiguous().numpy().astype("<f4", copy=False).tobytes())
    return digest.hexdigest()


def save_model(model: nn.Module, name: str, training: dict[str, Any], metadata: dict[str, Any], path: Path) -> str:
    if name not in ARCHITECTURES or training.get("status") != "complete":
        raise ValueError("invalid complete model provenance")
    state = {key: _array_document(value.detach().cpu().numpy()) for key, value in sorted(model.state_dict().items())}
    payload = {"schema": SCHEMA, "architecture": ARCHITECTURES[name],
               "parameter_count": parameter_count(model), "training": training,
               "metadata": metadata, "state": state}
    digest = hashlib.sha256(canonical(payload)).hexdigest()
    with path.open("xb") as handle:
        handle.write(canonical({**payload, "payload_sha256": digest}))
    return digest


def _validate_training(training: Any):
    required = {"status", "task", "seed", "epochs", "batch_size", "steps", "rows", "optimizer",
                "learning_rate", "loss", "loss_history", "initial_state_sha256", "final_state_sha256",
                "parameters_updated", "fit_ns", "dataset_sha256", "training_ids_sha256"}
    if type(training) is not dict or set(training) != required or training.get("status") != "complete" or training.get("task") != "balanced-xor-decomposition":
        raise ValueError("invalid variable-size training provenance")
    integers = {"seed": (0, 2**32 - 1), "epochs": (1, 100), "batch_size": (1, 128),
                "steps": (1, 100_000), "rows": (2, 512), "fit_ns": (1, 10**15)}
    if any(type(training.get(key)) is not int or not low <= training[key] <= high
           for key, (low, high) in integers.items()):
        raise ValueError("invalid training integer provenance")
    expected_steps = training["epochs"] * math.ceil(training["rows"] / training["batch_size"])
    hashes = [training[key] for key in ("initial_state_sha256", "final_state_sha256",
                                       "dataset_sha256", "training_ids_sha256")]
    if (training["steps"] != expected_steps or training["optimizer"] != "Adam"
            or training["loss"] != "binary-cross-entropy-with-logits"
            or type(training["learning_rate"]) not in (int, float) or not 0 < training["learning_rate"] <= .01
            or type(training["loss_history"]) is not list or len(training["loss_history"]) != training["epochs"]
            or any(type(value) not in (int, float) or not math.isfinite(value) for value in training["loss_history"])
            or training["parameters_updated"] is not True or hashes[0] == hashes[1]
            or any(type(value) is not str or len(value) != 64
                   or any(character not in "0123456789abcdef" for character in value) for value in hashes)):
        raise ValueError("invalid training optimization provenance")


def load_model(path: Path):
    data = read_json(path, MAX_MODEL_BYTES)
    required = {"schema", "architecture", "parameter_count", "training", "metadata", "state", "payload_sha256"}
    if type(data) is not dict or set(data) != required or data["schema"] != SCHEMA:
        raise ValueError("invalid variable-size model schema")
    name = data["architecture"].get("name") if type(data["architecture"]) is dict else None
    if name not in ARCHITECTURES or data["architecture"] != ARCHITECTURES[name]:
        raise ValueError("unsupported or changed variable-size architecture")
    _validate_training(data["training"])
    if data["metadata"] != {"torch": torch.__version__, "device": "cpu", "dtype": "float32"}:
        raise ValueError("variable-size model runtime metadata mismatch")
    payload = {key: data[key] for key in ("schema", "architecture", "parameter_count", "training", "metadata", "state")}
    if hashlib.sha256(canonical(payload)).hexdigest() != data["payload_sha256"]:
        raise ValueError("variable-size model artifact hash mismatch")
    model = build_model(name)
    expected = model.state_dict()
    if type(data["state"]) is not dict or set(data["state"]) != set(expected) or data["parameter_count"] != parameter_count(model):
        raise ValueError("variable-size model tensor set mismatch")
    restored = {key: torch.from_numpy(_array(data["state"][key], tuple(value.shape))) for key, value in expected.items()}
    model.load_state_dict(restored, strict=True)
    model.eval()
    if state_sha256(model) != data["training"]["final_state_sha256"]:
        raise ValueError("training/model state identity mismatch")
    return name, model, data["training"], data["metadata"], data["payload_sha256"]
