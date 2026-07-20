from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .schema import BackendResult


def flatten_backend_result(result: BackendResult, prefix: str | None = None) -> dict[str, Any]:
    base = prefix or result.backend
    row: dict[str, Any] = {
        f"{base}_status": result.status,
        f"{base}_error": result.error,
        f"{base}_ok": result.ok,
        f"{base}_correctness_mode": result.correctness_mode,
    }
    for key, value in asdict(result.timing).items():
        row[f"{base}_{key}"] = value
    for key, value in result.metrics.items():
        row[f"{base}_{key}"] = value
    for key, value in result.diagnostics.items():
        row[f"{base}_{key}"] = value
    return row

