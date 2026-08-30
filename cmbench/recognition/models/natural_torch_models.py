"""Natural-source structural and graph models for decomposition proposals."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from .mlp import _array, _array_document, canonical, read_json
from .variable_torch_models import GraphBatch, GraphEncoder

SCHEMA = "crse-pytorch-natural-decomposition-model/v1"
MAX_MODEL_BYTES = 8 * 1024 * 1024
STRUCTURAL_FEATURES = 17
INTERACTION_TARGETS = 45


class StructuralLinear(nn.Module):
    def __init__(self):
        super().__init__()
        self.head = nn.Linear(STRUCTURAL_FEATURES, 1)

    def forward(self, structural: torch.Tensor | None = None, graph: GraphBatch | None = None):
        if structural is None or structural.ndim != 2 or structural.shape[1] != STRUCTURAL_FEATURES:
            raise ValueError("bounded structural features required")
        return self.head(structural).squeeze(1), None, structural


class NaturalGraphClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = GraphEncoder(64, 4, 64)
        self.class_head = nn.Linear(64, 1)

    def forward(self, structural: torch.Tensor | None = None, graph: GraphBatch | None = None):
        if graph is None:
            raise ValueError("graph input required")
        embedding = self.encoder(graph)
        return self.class_head(embedding).squeeze(1), None, embedding


class NaturalMultiTaskGNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = GraphEncoder(64, 4, 64)
        self.class_head = nn.Linear(64, 1)
        self.interaction_head = nn.Linear(64, INTERACTION_TARGETS)

    def forward(self, structural: torch.Tensor | None = None, graph: GraphBatch | None = None):
        if graph is None:
            raise ValueError("graph input required")
        embedding = self.encoder(graph)
        return self.class_head(embedding).squeeze(1), self.interaction_head(embedding), embedding


ARCHITECTURES: dict[str, dict[str, Any]] = {
    "structural_linear": {"name": "structural_linear", "task": "natural-xor-decomposition",
        "role": "cheap source-structure control", "input_features": STRUCTURAL_FEATURES,
        "outputs": {"membership": 1}},
    "natural_graph_gnn": {"name": "natural_graph_gnn", "task": "natural-xor-decomposition",
        "role": "source-DAG binary classifier", "hidden": 64, "message_layers": 4,
        "outputs": {"membership": 1}},
    "natural_multitask_gnn": {"name": "natural_multitask_gnn", "task": "natural-xor-decomposition",
        "role": "source-DAG classifier plus ANF interaction prediction", "hidden": 64,
        "message_layers": 4, "outputs": {"membership": 1, "interaction_edges": INTERACTION_TARGETS}},
}


def build_model(name: str):
    builders = {"structural_linear": StructuralLinear, "natural_graph_gnn": NaturalGraphClassifier,
                "natural_multitask_gnn": NaturalMultiTaskGNN}
    if name not in builders:
        raise ValueError("unsupported natural decomposition architecture")
    model = builders[name]()
    count = parameter_count(model)
    if name == "structural_linear":
        if count != STRUCTURAL_FEATURES + 1:
            raise ValueError("structural linear parameter contract changed")
    elif not 50_000 <= count <= 150_000:
        raise ValueError("natural graph model outside parameter bound")
    return model


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def state_sha256(model: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(tensor.detach().cpu().contiguous().numpy().astype("<f4", copy=False).tobytes())
    return digest.hexdigest()


def save_model(model: nn.Module, name: str, training: dict[str, Any], metadata: dict[str, Any], path: Path):
    if name not in ARCHITECTURES or training.get("status") != "complete":
        raise ValueError("invalid natural trained model")
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
                "learning_rate", "loss", "auxiliary_weight", "loss_history", "auxiliary_loss_history",
                "initial_state_sha256", "final_state_sha256", "parameters_updated", "fit_ns",
                "dataset_sha256", "training_ids_sha256"}
    if type(training) is not dict or set(training) != required or training.get("status") != "complete" or training.get("task") != "natural-xor-decomposition":
        raise ValueError("invalid natural training provenance")
    integer_bounds = {"seed": (0, 2**32 - 1), "epochs": (1, 100), "batch_size": (1, 128),
                      "steps": (1, 100_000), "rows": (2, 512), "fit_ns": (1, 10**15)}
    if any(type(training.get(key)) is not int or not low <= training[key] <= high
           for key, (low, high) in integer_bounds.items()):
        raise ValueError("invalid natural training integer provenance")
    histories = (training["loss_history"], training["auxiliary_loss_history"])
    hashes = [training[key] for key in ("initial_state_sha256", "final_state_sha256",
                                       "dataset_sha256", "training_ids_sha256")]
    if (training["steps"] != training["epochs"] * math.ceil(training["rows"] / training["batch_size"])
            or training["optimizer"] != "Adam" or training["loss"] != "binary-cross-entropy-with-logits"
            or type(training["learning_rate"]) not in (int, float) or not 0 < training["learning_rate"] <= .01
            or type(training["auxiliary_weight"]) not in (int, float) or not 0 <= training["auxiliary_weight"] <= 1
            or any(type(history) is not list or len(history) != training["epochs"] for history in histories)
            or any(type(value) not in (int, float) or not math.isfinite(value)
                   for history in histories for value in history)
            or training["parameters_updated"] is not True or hashes[0] == hashes[1]
            or any(type(value) is not str or len(value) != 64
                   or any(character not in "0123456789abcdef" for character in value) for value in hashes)):
        raise ValueError("invalid natural optimization provenance")


def load_model(path: Path):
    data = read_json(path, MAX_MODEL_BYTES)
    required = {"schema", "architecture", "parameter_count", "training", "metadata", "state", "payload_sha256"}
    if type(data) is not dict or set(data) != required or data["schema"] != SCHEMA:
        raise ValueError("invalid natural model schema")
    name = data["architecture"].get("name") if type(data["architecture"]) is dict else None
    if name not in ARCHITECTURES or data["architecture"] != ARCHITECTURES[name]:
        raise ValueError("unsupported or changed natural model architecture")
    _validate_training(data["training"])
    if data["metadata"] != {"torch": torch.__version__, "device": "cpu", "dtype": "float32"}:
        raise ValueError("natural model runtime metadata mismatch")
    payload = {key: data[key] for key in ("schema", "architecture", "parameter_count", "training", "metadata", "state")}
    if hashlib.sha256(canonical(payload)).hexdigest() != data["payload_sha256"]:
        raise ValueError("natural model artifact hash mismatch")
    model = build_model(name)
    expected = model.state_dict()
    if type(data["state"]) is not dict or set(data["state"]) != set(expected) or data["parameter_count"] != parameter_count(model):
        raise ValueError("natural model tensor set mismatch")
    restored = {key: torch.from_numpy(_array(data["state"][key], tuple(value.shape))) for key, value in expected.items()}
    model.load_state_dict(restored, strict=True)
    model.eval()
    if state_sha256(model) != data["training"]["final_state_sha256"]:
        raise ValueError("natural training/model state mismatch")
    return name, model, data["training"], data["metadata"], data["payload_sha256"]
