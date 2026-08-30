"""Permutation-equivariant per-variable cut models with safe JSON artifacts."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from ..variable_graph_inputs import EDGE_ROLES, MAX_VARS, OPS
from .mlp import _array, _array_document, canonical, read_json
from .variable_torch_models import GraphBatch

SCHEMA = "crse-pytorch-natural-variable-cut-model/v1"
MAX_MODEL_BYTES = 8 * 1024 * 1024
HIDDEN = 64
INPUT_FEATURES = len(OPS) + MAX_VARS + 1


class BidirectionalGraphLayer(nn.Module):
    def __init__(self, hidden: int):
        super().__init__()
        self.self_linear = nn.Linear(hidden, hidden)
        self.forward_roles = nn.ModuleList(nn.Linear(hidden, hidden, bias=False) for _ in EDGE_ROLES)
        self.reverse_roles = nn.ModuleList(nn.Linear(hidden, hidden, bias=False) for _ in EDGE_ROLES)

    def forward(self, values: torch.Tensor, graph: GraphBatch):
        aggregate = torch.zeros_like(values)
        degree = torch.zeros((len(values), 1), dtype=values.dtype, device=values.device)
        source, destination = graph.edge_index
        for role, (forward, reverse) in enumerate(zip(self.forward_roles, self.reverse_roles)):
            mask = graph.edge_roles == role
            if bool(mask.any()):
                role_source, role_destination = source[mask], destination[mask]
                aggregate.index_add_(0, role_destination, forward(values[role_source]))
                aggregate.index_add_(0, role_source, reverse(values[role_destination]))
                ones = torch.ones((len(role_source), 1), dtype=values.dtype, device=values.device)
                degree.index_add_(0, role_destination, ones)
                degree.index_add_(0, role_source, ones)
        return F.relu(self.self_linear(values) + aggregate / degree.clamp_min(1.0))


class VariableConditionedCutGNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.node_input = nn.Linear(INPUT_FEATURES, HIDDEN)
        self.layers = nn.ModuleList(BidirectionalGraphLayer(HIDDEN) for _ in range(4))
        self.global_readout = nn.Linear(HIDDEN * 3, HIDDEN)
        self.class_head = nn.Linear(HIDDEN, 1)
        self.variable_head = nn.Sequential(nn.Linear(HIDDEN * 2 + 1, HIDDEN), nn.ReLU(), nn.Linear(HIDDEN, 1))

    def forward(self, structural: torch.Tensor | None = None, graph: GraphBatch | None = None):
        if graph is None:
            raise ValueError("graph input required")
        operator = graph.node_features[:, :len(OPS)]
        identity = graph.node_features[:, len(OPS):len(OPS) + MAX_VARS]
        ambient = graph.node_features[:, len(OPS) + MAX_VARS:]
        anchor = identity[:, :1]
        values = F.relu(self.node_input(torch.cat((operator, ambient, anchor), dim=1)))
        for layer in self.layers:
            values = layer(values, graph)

        count = len(graph.roots)
        sums = torch.zeros((count, HIDDEN), dtype=values.dtype, device=values.device)
        sums.index_add_(0, graph.graph_index, values)
        sizes = (graph.ptr[1:] - graph.ptr[:-1]).to(values.dtype).unsqueeze(1)
        means = sums / sizes
        maxima = torch.stack([
            values[int(graph.ptr[index]):int(graph.ptr[index + 1])].max(dim=0).values
            for index in range(count)
        ])
        roots = values[graph.roots]
        context = F.relu(self.global_readout(torch.cat((roots, means, maxima), dim=1)))

        is_variable = identity.sum(dim=1) == 1
        variable_index = identity.argmax(dim=1)
        flat_index = graph.graph_index[is_variable] * MAX_VARS + variable_index[is_variable]
        variable_sums = torch.zeros((count * MAX_VARS, HIDDEN), dtype=values.dtype, device=values.device)
        variable_counts = torch.zeros((count * MAX_VARS, 1), dtype=values.dtype, device=values.device)
        variable_sums.index_add_(0, flat_index, values[is_variable])
        variable_counts.index_add_(
            0, flat_index, torch.ones((int(is_variable.sum()), 1), dtype=values.dtype, device=values.device)
        )
        variable_values = (variable_sums / variable_counts.clamp_min(1.0)).reshape(count, MAX_VARS, HIDDEN)
        expanded_context = context.unsqueeze(1).expand(-1, MAX_VARS, -1)
        anchor_slots = torch.zeros((count, MAX_VARS, 1), dtype=values.dtype, device=values.device)
        anchor_slots[:, 0, 0] = 1.0
        cut_logits = self.variable_head(
            torch.cat((variable_values, expanded_context, anchor_slots), dim=2)
        ).squeeze(2)
        return self.class_head(context).squeeze(1), cut_logits, context


ARCHITECTURES: dict[str, dict[str, Any]] = {
    "variable_cut_gnn": {
        "name": "variable_cut_gnn",
        "task": "natural-variable-cut-ranking",
        "role": "bidirectional per-variable direct-cut proposal",
        "hidden": HIDDEN,
        "message_layers": 4,
        "absolute_variable_identity_in_learned_features": False,
        "orientation_anchor": "x0",
        "outputs": {"membership": 1, "shared_variable_membership": MAX_VARS},
    },
    "variable_cut_rank_gnn": {
        "name": "variable_cut_rank_gnn",
        "task": "natural-variable-cut-ranking",
        "role": "bidirectional per-variable cut plus same-pair ranking",
        "hidden": HIDDEN,
        "message_layers": 4,
        "absolute_variable_identity_in_learned_features": False,
        "orientation_anchor": "x0",
        "outputs": {"membership": 1, "shared_variable_membership": MAX_VARS},
    },
}


def build_model(name: str):
    if name not in ARCHITECTURES:
        raise ValueError("unsupported natural variable-cut architecture")
    model = VariableConditionedCutGNN()
    if not 50_000 <= parameter_count(model) <= 200_000:
        raise ValueError("natural variable-cut model outside parameter bound")
    return model


def parameter_count(model: nn.Module):
    return sum(parameter.numel() for parameter in model.parameters())


def state_sha256(model: nn.Module):
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(tensor.detach().cpu().contiguous().numpy().astype("<f4", copy=False).tobytes())
    return digest.hexdigest()


def save_model(model: nn.Module, name: str, training: dict[str, Any], metadata: dict[str, Any], path: Path):
    if name not in ARCHITECTURES or training.get("status") != "complete":
        raise ValueError("invalid complete natural variable-cut model")
    state = {key: _array_document(value.detach().cpu().numpy()) for key, value in sorted(model.state_dict().items())}
    payload = {"schema": SCHEMA, "architecture": ARCHITECTURES[name],
        "parameter_count": parameter_count(model), "training": training, "metadata": metadata, "state": state}
    digest = hashlib.sha256(canonical(payload)).hexdigest()
    with path.open("xb") as handle:
        handle.write(canonical({**payload, "payload_sha256": digest}))
    return digest


def _validate_training(training: Any):
    required = {"status", "task", "seed", "epochs", "batch_pairs", "steps", "pairs", "rows",
        "optimizer", "learning_rate", "loss", "weights", "loss_history", "cut_loss_history",
        "ranking_loss_history", "initial_state_sha256", "final_state_sha256", "parameters_updated",
        "fit_ns", "dataset_sha256", "training_pair_ids_sha256"}
    if (type(training) is not dict or set(training) != required or training.get("status") != "complete"
            or training.get("task") != "natural-variable-cut-ranking"):
        raise ValueError("invalid natural variable-cut training provenance")
    integers = {"seed": (0, 2**32 - 1), "epochs": (1, 100), "batch_pairs": (1, 64),
        "steps": (1, 100_000), "pairs": (1, 256), "rows": (2, 512), "fit_ns": (1, 10**15)}
    if any(type(training.get(key)) is not int or not low <= training[key] <= high
           for key, (low, high) in integers.items()):
        raise ValueError("invalid natural variable-cut integer provenance")
    histories = (training["loss_history"], training["cut_loss_history"], training["ranking_loss_history"])
    hashes = [training[key] for key in ("initial_state_sha256", "final_state_sha256",
        "dataset_sha256", "training_pair_ids_sha256")]
    weights = training["weights"]
    if (training["rows"] != 2 * training["pairs"]
            or training["steps"] != training["epochs"] * math.ceil(training["pairs"] / training["batch_pairs"])
            or training["optimizer"] != "Adam"
            or training["loss"] != "classification + equivariant-variable-cut + same-pair-margin"
            or type(training["learning_rate"]) not in (int, float) or not 0 < training["learning_rate"] <= .01
            or type(weights) is not dict or set(weights) != {"classification", "cut", "ranking", "ranking_margin"}
            or any(type(value) not in (int, float) or not 0 <= value <= 2 for value in weights.values())
            or any(type(history) is not list or len(history) != training["epochs"] for history in histories)
            or any(type(value) not in (int, float) or not math.isfinite(value)
                   for history in histories for value in history)
            or training["parameters_updated"] is not True or hashes[0] == hashes[1]
            or any(type(value) is not str or len(value) != 64
                   or any(character not in "0123456789abcdef" for character in value) for value in hashes)):
        raise ValueError("invalid natural variable-cut optimization provenance")


def load_model(path: Path):
    data = read_json(path, MAX_MODEL_BYTES)
    required = {"schema", "architecture", "parameter_count", "training", "metadata", "state", "payload_sha256"}
    if type(data) is not dict or set(data) != required or data["schema"] != SCHEMA:
        raise ValueError("invalid natural variable-cut model schema")
    name = data["architecture"].get("name") if type(data["architecture"]) is dict else None
    if name not in ARCHITECTURES or data["architecture"] != ARCHITECTURES[name]:
        raise ValueError("unsupported or changed natural variable-cut architecture")
    _validate_training(data["training"])
    if data["metadata"] != {"torch": torch.__version__, "device": "cpu", "dtype": "float32"}:
        raise ValueError("natural variable-cut runtime metadata mismatch")
    payload = {key: data[key] for key in ("schema", "architecture", "parameter_count", "training", "metadata", "state")}
    if hashlib.sha256(canonical(payload)).hexdigest() != data["payload_sha256"]:
        raise ValueError("natural variable-cut model artifact hash mismatch")
    model = build_model(name)
    expected = model.state_dict()
    if type(data["state"]) is not dict or set(data["state"]) != set(expected) or data["parameter_count"] != parameter_count(model):
        raise ValueError("natural variable-cut model tensor set mismatch")
    restored = {key: torch.from_numpy(_array(data["state"][key], tuple(value.shape))) for key, value in expected.items()}
    model.load_state_dict(restored, strict=True)
    model.eval()
    if state_sha256(model) != data["training"]["final_state_sha256"]:
        raise ValueError("natural variable-cut state mismatch")
    return name, model, data["training"], data["metadata"], data["payload_sha256"]
