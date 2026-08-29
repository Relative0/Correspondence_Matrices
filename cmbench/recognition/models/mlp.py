"""One small, actually trained NumPy MLP; not a general learning framework."""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from ..teacher import INPUT_SCHEMA

SCHEMA = "crse-numpy-motif-mlp/v1"
MAX_BYTES = 2 * 1024 * 1024


def canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def read_json(path: Path, max_bytes: int = MAX_BYTES) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def reject(value):
        raise ValueError("nonfinite JSON")

    with path.open("rb") as handle:
        raw = handle.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("JSON exceeds allocation bound")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("invalid bounded JSON") from exc


def _array_document(array: np.ndarray) -> dict[str, Any]:
    raw = np.asarray(array, dtype="<f4").tobytes()
    return {"shape": list(array.shape), "dtype": "<f4", "sha256": hashlib.sha256(raw).hexdigest(),
            "data_base64": base64.b64encode(raw).decode("ascii")}


def _array(data: Any, shape: tuple[int, ...]) -> np.ndarray:
    size = 4 * int(np.prod(shape))
    if (type(data) is not dict or set(data) != {"shape", "dtype", "sha256", "data_base64"}
            or type(data["shape"]) is not list or any(type(v) is not int for v in data["shape"])
            or data["shape"] != list(shape) or data["dtype"] != "<f4"
            or type(data["data_base64"]) is not str or len(data["data_base64"]) != 4 * ((size + 2) // 3)):
        raise ValueError("invalid tensor dimensions, dtype or encoded size")
    try:
        raw = base64.b64decode(data["data_base64"], validate=True)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid tensor encoding") from exc
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != data["sha256"]:
        raise ValueError("tensor hash mismatch")
    result = np.frombuffer(raw, dtype="<f4").reshape(shape).copy()
    if not np.isfinite(result).all() or np.abs(result).max() > 1e6:
        raise ValueError("nonfinite or oversized tensor values")
    return result


@dataclass
class MotifMLP:
    w1: np.ndarray
    b1: np.ndarray
    w2: np.ndarray
    b2: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    training: dict[str, Any]
    artifact_digest: str | None = None

    @property
    def parameter_count(self) -> int:
        return sum(a.size for a in (self.w1, self.b1, self.w2, self.b2))

    def predict(self, values: np.ndarray) -> np.ndarray:
        if (type(values) is not np.ndarray or values.ndim != 2 or values.shape[1] != 512
                or not 1 <= values.shape[0] <= 1024 or not np.isfinite(values).all()
                or not np.isin(values, [0, 1]).all()):
            raise ValueError("invalid bounded binary model inputs")
        x = (values.astype(np.float32) - self.mean) / self.scale
        hidden = np.maximum(x @ self.w1 + self.b1, 0)
        logits = np.clip(hidden @ self.w2 + self.b2, -30, 30)
        return (1 / (1 + np.exp(-logits))).reshape(-1)

    def score(self, values: np.ndarray) -> float:
        if type(values) is not np.ndarray or values.shape != (512,):
            raise ValueError("invalid single-request input")
        return float(self.predict(values.reshape(1, 512))[0])

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema": SCHEMA, "input_schema": INPUT_SCHEMA,
                   "architecture": {"input": 512, "hidden": self.b1.size, "output": 1,
                                    "activation": "relu", "output_activation": "sigmoid"},
                   "policy": {"threshold": 0.5, "fallback": "cse", "max_candidates": 1,
                              "acceptance": "independent-full-reference-and-strict-node-reduction/v1"},
                   "training": json.loads(canonical(self.training)),
                   "arrays": {name: _array_document(getattr(self, name))
                              for name in ("w1", "b1", "w2", "b2", "mean", "scale")}}
        return {**payload, "payload_sha256": hashlib.sha256(canonical(payload)).hexdigest()}

    def save(self, path: Path) -> None:
        with path.open("xb") as handle:
            handle.write(canonical(self.to_dict()))

    @classmethod
    def load(cls, path: Path) -> MotifMLP:
        data = read_json(path)
        if (type(data) is not dict or set(data) != {"schema", "input_schema", "architecture", "policy", "training", "arrays", "payload_sha256"}
                or data["schema"] != SCHEMA or data["input_schema"] != INPUT_SCHEMA):
            raise ValueError("invalid model schema")
        architecture = data["architecture"]
        if (type(architecture) is not dict or any(type(architecture.get(k)) is not int
                                                for k in ("input", "hidden", "output"))):
            raise ValueError("invalid architecture")
        hidden = architecture["hidden"]
        if (not 1 <= hidden <= 256 or architecture != {"input": 512, "hidden": hidden, "output": 1,
                "activation": "relu", "output_activation": "sigmoid"}):
            raise ValueError("unsupported or oversized architecture")
        if data["policy"] != {"threshold": 0.5, "fallback": "cse", "max_candidates": 1,
                "acceptance": "independent-full-reference-and-strict-node-reduction/v1"}:
            raise ValueError("model policy mismatch")
        if type(data["training"]) is not dict or data["training"].get("status") != "complete":
            raise ValueError("incomplete model")
        training = data["training"]
        bounds = {"seed": (0, 2**32 - 1), "epochs": (1, 100), "batch_size": (1, 128),
                  "rows": (2, 1024), "steps": (1, 102400)}
        if (any(type(training.get(k)) is not int or not low <= training[k] <= high
                for k, (low, high) in bounds.items()) or training.get("parameters_updated") is not True
                or training["steps"] != training["epochs"] * ((training["rows"] + training["batch_size"] - 1) // training["batch_size"])):
            raise ValueError("invalid trained-model provenance")
        digest = data.pop("payload_sha256")
        if hashlib.sha256(canonical(data)).hexdigest() != digest:
            raise ValueError("model hash mismatch")
        shapes = {"w1": (512, hidden), "b1": (hidden,), "w2": (hidden, 1), "b2": (1,), "mean": (512,), "scale": (512,)}
        if type(data["arrays"]) is not dict or set(data["arrays"]) != set(shapes):
            raise ValueError("invalid model tensors")
        arrays = {name: _array(data["arrays"][name], shape) for name, shape in shapes.items()}
        if np.any(arrays["scale"] <= 0) or np.any(arrays["scale"] > 1e6):
            raise ValueError("invalid train-only normalization")
        if hashlib.sha256(arrays["w1"].tobytes() + arrays["w2"].tobytes()).hexdigest() != training.get("final_weights_sha256"):
            raise ValueError("training/weight identity mismatch")
        return cls(**arrays, training=data["training"], artifact_digest=digest)


def train_mlp(x: np.ndarray, y: np.ndarray, *, seed: int, epochs: int = 40,
              batch_size: int = 32, hidden: int = 128, learning_rate: float = 0.03,
              check: Callable[[], None] = lambda: None) -> MotifMLP:
    if (type(x) is not np.ndarray or x.ndim != 2 or x.shape[1] != 512
            or not 2 <= x.shape[0] <= 1024 or not np.isfinite(x).all() or not np.isin(x, [0, 1]).all()
            or type(y) is not np.ndarray or y.shape != (len(x),) or not np.isin(y, [0, 1]).all()
            or type(seed) is not int or not 0 <= seed <= 2**32 - 1
            or type(epochs) is not int or not 1 <= epochs <= 100
            or type(batch_size) is not int or not 1 <= batch_size <= 128
            or type(hidden) is not int or not 1 <= hidden <= 256
            or type(learning_rate) not in (int, float) or not 0 < learning_rate <= 0.1):
        raise ValueError("invalid training data or finite training bounds")
    check()
    rng = np.random.default_rng(seed)
    mean = x.mean(axis=0, dtype=np.float32)
    scale = x.std(axis=0, dtype=np.float32)
    scale[scale < 0.05] = 1.0
    normalized = (x.astype(np.float32) - mean) / scale
    model = MotifMLP((rng.standard_normal((512, hidden)) * np.sqrt(2 / 512)).astype(np.float32),
                     np.zeros(hidden, dtype=np.float32),
                     (rng.standard_normal((hidden, 1)) * np.sqrt(1 / hidden)).astype(np.float32),
                     np.zeros(1, dtype=np.float32), mean, scale, {"status": "incomplete"})
    initial_hash = hashlib.sha256(model.w1.tobytes() + model.w2.tobytes()).hexdigest()
    history = []
    steps = 0
    for epoch in range(epochs):
        indices = rng.permutation(len(x))
        for start in range(0, len(x), batch_size):
            check()
            batch = indices[start:start + batch_size]
            xb, yb = normalized[batch], y[batch, None]
            hidden_values = np.maximum(xb @ model.w1 + model.b1, 0)
            probabilities = 1 / (1 + np.exp(-np.clip(hidden_values @ model.w2 + model.b2, -30, 30)))
            delta = (probabilities - yb) / len(batch)
            hidden_delta = (delta @ model.w2.T) * (hidden_values > 0)
            model.w2 -= learning_rate * (hidden_values.T @ delta)
            model.b2 -= learning_rate * delta.sum(axis=0)
            model.w1 -= learning_rate * (xb.T @ hidden_delta)
            model.b1 -= learning_rate * hidden_delta.sum(axis=0)
            steps += 1
        check()
        predictions = np.clip(model.predict(x), 1e-7, 1 - 1e-7)
        loss = float(-np.mean(y * np.log(predictions) + (1 - y) * np.log(1 - predictions)))
        if not np.isfinite(loss):
            raise ValueError("nonfinite training loss")
        history.append({"epoch": epoch + 1, "binary_cross_entropy": loss})
    final_hash = hashlib.sha256(model.w1.tobytes() + model.w2.tobytes()).hexdigest()
    check()
    model.training = {"status": "complete", "seed": seed, "epochs": epochs, "steps": steps,
                      "batch_size": batch_size, "learning_rate": learning_rate, "optimizer": "minibatch-SGD",
                      "rows": len(x), "preprocessing": "training-only-mean-std-small-scale-clamped-to-one",
                      "initial_weights_sha256": initial_hash, "final_weights_sha256": final_hash,
                      "parameters_updated": initial_hash != final_hash, "loss_history": history}
    return model
