"""Direct-cut and pair-ranking models with inert, hash-checked artifacts."""
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

SCHEMA = "crse-pytorch-natural-cut-model/v1"
MAX_MODEL_BYTES = 8 * 1024 * 1024
STRUCTURAL_FEATURES = 17
MAX_VARS = 10


class StructuralPairRanker(nn.Module):
    def __init__(self):
        super().__init__()
        self.class_head = nn.Linear(STRUCTURAL_FEATURES, 1)

    def forward(self, structural: torch.Tensor | None = None, graph: GraphBatch | None = None):
        if structural is None or structural.ndim != 2 or structural.shape[1] != STRUCTURAL_FEATURES:
            raise ValueError("bounded structural features required")
        return self.class_head(structural).squeeze(1), None, structural


class DirectCutGNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = GraphEncoder(64, 4, 64)
        self.class_head = nn.Linear(64, 1)
        self.cut_head = nn.Linear(64, MAX_VARS)

    def forward(self, structural: torch.Tensor | None = None, graph: GraphBatch | None = None):
        if graph is None:
            raise ValueError("graph input required")
        embedding = self.encoder(graph)
        return self.class_head(embedding).squeeze(1), self.cut_head(embedding), embedding


ARCHITECTURES: dict[str, dict[str, Any]] = {
    "structural_pair_ranker": {
        "name": "structural_pair_ranker",
        "task": "natural-xor-cut-ranking",
        "role": "coarse source-structure membership and pair-ranking control",
        "outputs": {"membership": 1},
    },
    "direct_cut_gnn": {
        "name": "direct_cut_gnn",
        "task": "natural-xor-cut-ranking",
        "role": "source-DAG membership plus direct canonical cut",
        "hidden": 64,
        "message_layers": 4,
        "outputs": {"membership": 1, "row_membership": MAX_VARS},
    },
    "cut_rank_gnn": {
        "name": "cut_rank_gnn",
        "task": "natural-xor-cut-ranking",
        "role": "source-DAG direct cut with same-circuit pair ranking",
        "hidden": 64,
        "message_layers": 4,
        "outputs": {"membership": 1, "row_membership": MAX_VARS},
    },
}


def build_model(name: str):
    builders = {
        "structural_pair_ranker": StructuralPairRanker,
        "direct_cut_gnn": DirectCutGNN,
        "cut_rank_gnn": DirectCutGNN,
    }
    if name not in builders:
        raise ValueError("unsupported natural cut architecture")
    model = builders[name]()
    count = parameter_count(model)
    if name == "structural_pair_ranker":
        if count != STRUCTURAL_FEATURES + 1:
            raise ValueError("structural pair-ranker parameter contract changed")
    elif not 50_000 <= count <= 150_000:
        raise ValueError("natural cut GNN outside parameter bound")
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
        raise ValueError("invalid complete natural cut model")
    state = {
        key: _array_document(value.detach().cpu().numpy())
        for key, value in sorted(model.state_dict().items())
    }
    payload = {
        "schema": SCHEMA,
        "architecture": ARCHITECTURES[name],
        "parameter_count": parameter_count(model),
        "training": training,
        "metadata": metadata,
        "state": state,
    }
    digest = hashlib.sha256(canonical(payload)).hexdigest()
    with path.open("xb") as handle:
        handle.write(canonical({**payload, "payload_sha256": digest}))
    return digest


def _validate_training(training: Any):
    required = {
        "status", "task", "seed", "epochs", "batch_pairs", "steps", "pairs", "rows",
        "optimizer", "learning_rate", "loss", "weights", "loss_history", "cut_loss_history",
        "ranking_loss_history", "initial_state_sha256", "final_state_sha256",
        "parameters_updated", "fit_ns", "dataset_sha256", "training_pair_ids_sha256",
    }
    if (
        type(training) is not dict
        or set(training) != required
        or training.get("status") != "complete"
        or training.get("task") != "natural-xor-cut-ranking"
    ):
        raise ValueError("invalid natural cut training provenance")
    integers = {
        "seed": (0, 2**32 - 1),
        "epochs": (1, 100),
        "batch_pairs": (1, 64),
        "steps": (1, 100_000),
        "pairs": (1, 256),
        "rows": (2, 512),
        "fit_ns": (1, 10**15),
    }
    if any(
        type(training.get(key)) is not int or not low <= training[key] <= high
        for key, (low, high) in integers.items()
    ):
        raise ValueError("invalid natural cut integer provenance")
    histories = (
        training["loss_history"], training["cut_loss_history"], training["ranking_loss_history"]
    )
    hashes = [
        training[key]
        for key in (
            "initial_state_sha256", "final_state_sha256", "dataset_sha256",
            "training_pair_ids_sha256",
        )
    ]
    expected_steps = training["epochs"] * math.ceil(training["pairs"] / training["batch_pairs"])
    weights = training["weights"]
    if (
        training["rows"] != 2 * training["pairs"]
        or training["steps"] != expected_steps
        or training["optimizer"] != "Adam"
        or training["loss"] != "classification + direct-cut + same-pair-margin"
        or type(training["learning_rate"]) not in (int, float)
        or not 0 < training["learning_rate"] <= .01
        or type(weights) is not dict
        or set(weights) != {"classification", "cut", "ranking", "ranking_margin"}
        or any(type(value) not in (int, float) or not 0 <= value <= 2 for value in weights.values())
        or any(type(history) is not list or len(history) != training["epochs"] for history in histories)
        or any(
            type(value) not in (int, float) or not math.isfinite(value)
            for history in histories for value in history
        )
        or training["parameters_updated"] is not True
        or hashes[0] == hashes[1]
        or any(
            type(value) is not str or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in hashes
        )
    ):
        raise ValueError("invalid natural cut optimization provenance")


def load_model(path: Path):
    data = read_json(path, MAX_MODEL_BYTES)
    required = {
        "schema", "architecture", "parameter_count", "training", "metadata", "state",
        "payload_sha256",
    }
    if type(data) is not dict or set(data) != required or data["schema"] != SCHEMA:
        raise ValueError("invalid natural cut model schema")
    name = data["architecture"].get("name") if type(data["architecture"]) is dict else None
    if name not in ARCHITECTURES or data["architecture"] != ARCHITECTURES[name]:
        raise ValueError("unsupported or changed natural cut architecture")
    _validate_training(data["training"])
    if data["metadata"] != {"torch": torch.__version__, "device": "cpu", "dtype": "float32"}:
        raise ValueError("natural cut runtime metadata mismatch")
    payload = {
        key: data[key]
        for key in ("schema", "architecture", "parameter_count", "training", "metadata", "state")
    }
    if hashlib.sha256(canonical(payload)).hexdigest() != data["payload_sha256"]:
        raise ValueError("natural cut model artifact hash mismatch")
    model = build_model(name)
    expected = model.state_dict()
    if (
        type(data["state"]) is not dict
        or set(data["state"]) != set(expected)
        or data["parameter_count"] != parameter_count(model)
    ):
        raise ValueError("natural cut model tensor set mismatch")
    restored = {
        key: torch.from_numpy(_array(data["state"][key], tuple(value.shape)))
        for key, value in expected.items()
    }
    model.load_state_dict(restored, strict=True)
    model.eval()
    if state_sha256(model) != data["training"]["final_state_sha256"]:
        raise ValueError("natural cut training/model state mismatch")
    return name, model, data["training"], data["metadata"], data["payload_sha256"]
