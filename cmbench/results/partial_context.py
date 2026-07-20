from __future__ import annotations

from typing import Any


def skipped_partial_backend(prefix: str, reason: str = "skipped") -> dict[str, Any]:
    if prefix != "partial_robdd":
        raise ValueError(f"unknown partial-context backend prefix: {prefix!r}")
    return {
        "partial_robdd_backend": "auto",
        "partial_robdd_build_once_s": None,
        "partial_robdd_restrict_contexts_total_s": None,
        "partial_robdd_total_s": None,
        "partial_robdd_restrict_per_context_median_s": None,
        "partial_robdd_nodes_base": None,
        "partial_robdd_restricted_nodes_median": None,
        "partial_robdd_ok_rate": None,
        "partial_robdd_status": reason,
        "partial_robdd_error": None,
        "partial_robdd_extract_total_s": None,
        "partial_robdd_build_restrict_extract_total_s": None,
    }


def error_result_from_exception(prefix: str, exc: Exception) -> dict[str, Any]:
    out = skipped_partial_backend(prefix, reason="error")
    out[f"{prefix}_error"] = repr(exc)
    return out
