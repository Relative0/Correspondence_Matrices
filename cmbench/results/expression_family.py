from __future__ import annotations

from typing import Any


def skipped_family_backend(prefix: str, reason: str = "skipped") -> dict[str, Any]:
    if prefix == "family_robdd":
        return {
            "family_robdd_backend": "auto",
            "family_robdd_build_total_time_s": None,
            "family_robdd_build_wall_time_s": None,
            "family_robdd_build_per_variant_median_s": None,
            "family_robdd_nodes_median": None,
            "family_robdd_nodes_total_or_manager_if_shared": None,
            "family_robdd_ok_rate": None,
            "family_robdd_status": reason,
        }
    if prefix == "family_cm_cache":
        return {
            "family_cm_cache_total_time_s": None,
            "family_cm_cache_per_variant_median_s": None,
            "family_cm_cache_compile_total_s": None,
            "family_cm_cache_eval_total_s": None,
            "family_cm_cache_ok_rate": None,
            "family_cm_cache_persistent_hits_total": None,
            "family_cm_cache_persistent_misses_total": None,
            "family_cm_cache_cache_size_final": None,
            "family_cm_cache_materializations_total": None,
            "family_cm_cache_live_vars_max_median": None,
        }
    raise ValueError(f"unknown expression-family backend prefix: {prefix!r}")


def error_result_from_exception(prefix: str, exc: Exception) -> dict[str, Any]:
    out = skipped_family_backend(prefix, reason="error")
    out[f"{prefix}_error"] = repr(exc)
    return out
