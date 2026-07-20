from __future__ import annotations

from typing import Any


def skipped_single_backend(prefix: str, reason: str = "skipped") -> dict[str, Any]:
    return {
        f"{prefix}_time_s": None,
        f"{prefix}_ok": None,
        f"{prefix}_status": reason,
        f"{prefix}_error": None,
    }


def error_result_from_exception(prefix: str, exc: Exception) -> dict[str, Any]:
    out = skipped_single_backend(prefix, reason="error")
    out[f"{prefix}_error"] = repr(exc)
    return out
