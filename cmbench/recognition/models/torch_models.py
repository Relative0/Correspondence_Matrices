"""Optional PyTorch models and inert, hash-checked JSON state artifacts.

Importing :mod:`cmbench.recognition` does not import this module.  The optional
dependency is reached only by the explicit neural experiment entry point.
"""
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

from ..graph_inputs import EDGE_ROLES, NODE_FEATURES, GraphInput, graph_schema_document
from .mlp import _array, _array_document, canonical, read_json

SCHEMA = "crse-pytorch-neural-model/v1"
MAX_MODEL_BYTES = 8 * 1024 * 1024
MAX_PARAMETERS = 250_000


@dataclass(frozen=True)
class GraphBatch:
    node_features: torch.Tensor
    edge_index: torch.Tensor
    edge_roles: torch.Tensor
    graph_index: torch.Tensor
    roots: torch.Tensor
    ptr: torch.Tensor


def batch_graphs(graphs: Sequence[GraphInput]) -> GraphBatch:
    if not 1 <= len(graphs) <= 512 or any(type(graph) is not GraphInput for graph in graphs):
        raise ValueError("invalid bounded graph batch")
    features, edge_indices, edge_roles, graph_indices, roots, ptr = [], [], [], [], [], [0]
    offset = 0
    for graph_number, graph in enumerate(graphs):
        features.append(graph.node_features)
        if graph.edge_index.shape[1]:
            edge_indices.append(graph.edge_index + offset)
            edge_roles.append(graph.edge_roles)
        graph_indices.append(np.full(len(graph.node_features), graph_number, dtype=np.int64))
        roots.append(graph.root + offset)
        offset += len(graph.node_features)
        ptr.append(offset)
    edge_index = np.concatenate(edge_indices, axis=1) if edge_indices else np.empty((2, 0), dtype=np.int64)
    roles = np.concatenate(edge_roles) if edge_roles else np.empty(0, dtype=np.int64)
    return GraphBatch(
        torch.from_numpy(np.concatenate(features)),
        torch.from_numpy(edge_index),
        torch.from_numpy(roles),
        torch.from_numpy(np.concatenate(graph_indices)),
        torch.tensor(roots, dtype=torch.int64),
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


class MatrixMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = nn.Sequential(nn.Linear(512, 128), nn.ReLU(), nn.Linear(128, 64), nn.ReLU())
        self.head = nn.Linear(64, 1)

    def forward(self, matrix: torch.Tensor | None, graph: GraphBatch | None = None):
        if matrix is None:
            raise ValueError("matrix input required")
        embedding = self.backbone(matrix)
        return self.head(embedding).squeeze(1), embedding


class MatrixCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.convolution = nn.Sequential(
            nn.Conv2d(2, 32, 3, padding=1), nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1), nn.ReLU(),
            nn.AvgPool2d(4),
        )
        self.backbone = nn.Sequential(nn.Linear(32 * 4 * 4, 128), nn.ReLU(), nn.Linear(128, 64), nn.ReLU())
        self.head = nn.Linear(64, 1)

    def forward(self, matrix: torch.Tensor | None, graph: GraphBatch | None = None):
        if matrix is None:
            raise ValueError("matrix input required")
        image = matrix.reshape(-1, 2, 16, 16)
        embedding = self.backbone(self.convolution(image).flatten(1))
        return self.head(embedding).squeeze(1), embedding


class GraphClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = GraphEncoder(64, 4, 64)
        self.head = nn.Linear(64, 1)

    def forward(self, matrix: torch.Tensor | None, graph: GraphBatch | None = None):
        if graph is None:
            raise ValueError("graph input required")
        embedding = self.encoder(graph)
        return self.head(embedding).squeeze(1), embedding


class FusedClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.matrix = nn.Sequential(nn.Linear(512, 64), nn.ReLU(), nn.Linear(64, 32), nn.ReLU())
        self.graph = GraphEncoder(48, 3, 32)
        self.fusion = nn.Sequential(nn.Linear(64, 64), nn.ReLU())
        self.head = nn.Linear(64, 1)

    def forward(self, matrix: torch.Tensor | None, graph: GraphBatch | None = None):
        if matrix is None or graph is None:
            raise ValueError("matrix and graph inputs required")
        embedding = self.fusion(torch.cat((self.matrix(matrix), self.graph(graph)), dim=1))
        return self.head(embedding).squeeze(1), embedding


class GraphRetrieval(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = GraphEncoder(64, 4, 32)

    def forward(self, matrix: torch.Tensor | None, graph: GraphBatch | None = None):
        if graph is None:
            raise ValueError("graph input required")
        embedding = F.normalize(self.encoder(graph), dim=1)
        return None, embedding


ARCHITECTURES: dict[str, dict[str, Any]] = {
    "matrix_mlp": {"name": "matrix_mlp", "task": "affine-classification", "layers": [512, 128, 64, 1],
                   "activations": ["relu", "relu", "sigmoid"], "matrix_layout": "values256+valid-mask256"},
    "matrix_cnn": {"name": "matrix_cnn", "task": "affine-classification", "convolutions": [[2, 32, 3], [32, 32, 3]],
                   "layers": [512, 128, 64, 1], "activations": ["relu", "relu", "avg-pool4", "relu", "relu", "sigmoid"],
                   "matrix_layout": "channels(values,valid-mask)-16x16"},
    "graph_gnn": {"name": "graph_gnn", "task": "affine-classification", "node_features": NODE_FEATURES,
                  "message_layers": 4, "hidden": 64, "embedding": 64, "activations": ["relu", "sigmoid"],
                  "graph_schema": graph_schema_document()},
    "fused": {"name": "fused", "task": "affine-classification", "matrix_layers": [512, 64, 32],
              "graph_hidden": 48, "message_layers": 3, "graph_embedding": 32,
              "fusion_layers": [64, 64, 1], "activations": ["relu", "sigmoid"],
              "graph_schema": graph_schema_document()},
    "graph_retrieval": {"name": "graph_retrieval", "task": "contrastive-functional-retrieval",
                        "node_features": NODE_FEATURES, "message_layers": 4, "hidden": 64,
                        "embedding": 32, "activation": "relu+l2-normalize",
                        "graph_schema": graph_schema_document()},
}


def build_model(name: str) -> nn.Module:
    builders = {"matrix_mlp": MatrixMLP, "matrix_cnn": MatrixCNN, "graph_gnn": GraphClassifier,
                "fused": FusedClassifier, "graph_retrieval": GraphRetrieval}
    if name not in builders:
        raise ValueError("unsupported neural architecture")
    model = builders[name]()
    count = parameter_count(model)
    if not 50_000 <= count <= MAX_PARAMETERS:
        raise ValueError("architecture outside approved parameter band")
    return model


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def state_sha256(model: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(tensor.detach().cpu().contiguous().numpy().astype("<f4", copy=False).tobytes())
    return digest.hexdigest()


def save_model(model: nn.Module, name: str, training: dict[str, Any], metadata: dict[str, Any],
               path: Path) -> str:
    if ARCHITECTURES.get(name) is None or type(training) is not dict or training.get("status") != "complete":
        raise ValueError("invalid complete model provenance")
    state = {key: _array_document(value.detach().cpu().numpy())
             for key, value in sorted(model.state_dict().items())}
    payload = {"schema": SCHEMA, "architecture": ARCHITECTURES[name],
               "parameter_count": parameter_count(model), "training": training,
               "metadata": metadata, "state": state}
    digest = hashlib.sha256(canonical(payload)).hexdigest()
    with path.open("xb") as handle:
        handle.write(canonical({**payload, "payload_sha256": digest}))
    return digest


def _validate_training(training: Any, task: str) -> None:
    common = {"status", "task", "seed", "epochs", "batch_size", "steps", "rows", "optimizer",
              "learning_rate", "loss", "loss_history", "initial_state_sha256", "final_state_sha256",
              "parameters_updated", "fit_ns", "dataset_sha256", "training_ids_sha256"}
    expected = common | ({"temperature", "positive_pairs"} if task == "contrastive-functional-retrieval" else set())
    if type(training) is not dict or set(training) != expected or training.get("status") != "complete" or training.get("task") != task:
        raise ValueError("invalid trained model provenance fields")
    integer_bounds = {"seed": (0, 2**32 - 1), "epochs": (1, 100), "batch_size": (1, 128),
                      "steps": (1, 100_000), "rows": (2, 512), "fit_ns": (1, 10**15)}
    if any(type(training.get(key)) is not int or not low <= training[key] <= high
           for key, (low, high) in integer_bounds.items()):
        raise ValueError("invalid trained model integer provenance")
    expected_steps = training["epochs"] * math.ceil(training["rows"] / training["batch_size"])
    histories = training.get("loss_history")
    hashes = (training.get("initial_state_sha256"), training.get("final_state_sha256"),
              training.get("dataset_sha256"), training.get("training_ids_sha256"))
    if (training["steps"] != expected_steps or training.get("optimizer") != "Adam"
            or type(training.get("learning_rate")) not in (int, float)
            or not math.isfinite(training["learning_rate"]) or not 0 < training["learning_rate"] <= 0.01
            or type(histories) is not list or len(histories) != training["epochs"]
            or any(type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1e6
                   for value in histories)
            or training.get("parameters_updated") is not True
            or any(type(value) is not str or len(value) != 64
                   or any(character not in "0123456789abcdef" for character in value) for value in hashes)
            or hashes[0] == hashes[1]):
        raise ValueError("invalid trained model optimization provenance")
    if task == "affine-classification":
        if training.get("loss") != "binary-cross-entropy-with-logits":
            raise ValueError("classification loss mismatch")
    elif (training.get("loss") != "symmetric-in-batch-NT-Xent"
          or training.get("positive_pairs") != "exact-checked absorption-equivalent graph views"
          or type(training.get("temperature")) not in (int, float)
          or not math.isfinite(training["temperature"]) or not 0 < training["temperature"] <= 1):
        raise ValueError("retrieval loss provenance mismatch")


def _validate_metadata(metadata: Any) -> None:
    if (type(metadata) is not dict or set(metadata) != {"torch", "device", "dtype", "graph_memory_bytes"}
            or type(metadata["torch"]) is not str or not 1 <= len(metadata["torch"]) <= 64
            or metadata["device"] != "cpu" or metadata["dtype"] != "float32"
            or (metadata["graph_memory_bytes"] is not None
                and (type(metadata["graph_memory_bytes"]) is not int
                     or not 0 <= metadata["graph_memory_bytes"] <= 1024**3))):
        raise ValueError("invalid model runtime metadata")


def load_model(path: Path) -> tuple[str, nn.Module, dict[str, Any], dict[str, Any], str]:
    data = read_json(path, MAX_MODEL_BYTES)
    if type(data) is not dict or set(data) != {"schema", "architecture", "parameter_count", "training",
                                               "metadata", "state", "payload_sha256"} or data["schema"] != SCHEMA:
        raise ValueError("invalid PyTorch model artifact schema")
    name = data["architecture"].get("name") if type(data["architecture"]) is dict else None
    if name not in ARCHITECTURES or data["architecture"] != ARCHITECTURES[name]:
        raise ValueError("unsupported or changed architecture document")
    _validate_training(data["training"], data["architecture"]["task"])
    _validate_metadata(data["metadata"])
    if type(data["payload_sha256"]) is not str or len(data["payload_sha256"]) != 64:
        raise ValueError("invalid model artifact digest")
    payload = {key: data[key] for key in ("schema", "architecture", "parameter_count", "training", "metadata", "state")}
    if hashlib.sha256(canonical(payload)).hexdigest() != data["payload_sha256"]:
        raise ValueError("PyTorch model artifact hash mismatch")
    model = build_model(name)
    expected = model.state_dict()
    if (type(data["state"]) is not dict or set(data["state"]) != set(expected)
            or type(data["parameter_count"]) is not int or data["parameter_count"] != parameter_count(model)
            or data["parameter_count"] > MAX_PARAMETERS):
        raise ValueError("model tensor set or parameter count mismatch")
    restored = {key: torch.from_numpy(_array(data["state"][key], tuple(value.shape)))
                for key, value in expected.items()}
    model.load_state_dict(restored, strict=True)
    model.eval()
    if state_sha256(model) != data["training"].get("final_state_sha256"):
        raise ValueError("training and model state identity mismatch")
    return name, model, data["training"], data["metadata"], data["payload_sha256"]
