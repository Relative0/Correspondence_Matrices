from __future__ import annotations

from typing import Any


def skipped_equiv_result(prefix: str, reason: str | None = None) -> dict[str, Any]:
    status = "skipped"
    error = reason
    if prefix == "bitset_equiv":
        return {
            "bitset_equiv_eval_f_time_s": None,
            "bitset_equiv_eval_g_time_s": None,
            "bitset_equiv_eval_total_time_s": None,
            "bitset_equiv_compare_time_s": None,
            "bitset_equiv_total_time_s": None,
            "bitset_equiv_result": None,
            "bitset_equiv_ok": None,
            "bitset_equiv_status": status,
            "bitset_equiv_error": error,
        }
    if prefix == "cm_equiv":
        return {
            "cm_equiv_compile_f_time_s": None,
            "cm_equiv_compile_g_time_s": None,
            "cm_equiv_compile_total_time_s": None,
            "cm_equiv_eval_f_time_s": None,
            "cm_equiv_eval_g_time_s": None,
            "cm_equiv_eval_total_time_s": None,
            "cm_equiv_compare_time_s": None,
            "cm_equiv_total_time_s": None,
            "cm_equiv_result": None,
            "cm_equiv_ok": None,
            "cm_equiv_status": status,
            "cm_equiv_error": error,
        }
    if prefix == "sympy_equiv":
        return {
            "sympy_equiv_time_s": None,
            "sympy_equiv_result": None,
            "sympy_equiv_ok": None,
            "sympy_equiv_status": status,
            "sympy_equiv_error": error,
        }
    if prefix == "robdd_equiv":
        return {
            "robdd_equiv_build_f_time_s": None,
            "robdd_equiv_build_g_time_s": None,
            "robdd_equiv_build_total_time_s": None,
            "robdd_equiv_compare_per_call_time_s": None,
            "robdd_equiv_total_time_s": None,
            "robdd_equiv_nodes_f": None,
            "robdd_equiv_nodes_g": None,
            "robdd_equiv_nodes_manager": None,
            "robdd_equiv_result": None,
            "robdd_equiv_ok": None,
            "robdd_equiv_status": status,
            "robdd_equiv_error": error,
            "robdd_equiv_backend": None,
            "robdd_equiv_backend_preference": None,
            "robdd_equiv_order_policy": None,
            "robdd_equiv_order_seed": None,
            "robdd_equiv_order_sweeps": None,
            "robdd_equiv_order_used": None,
            "robdd_equiv_compare_repeat": None,
            "robdd_equiv_dynamic_reordering_requested": False,
            "robdd_equiv_dynamic_reordering_used": False,
        }
    raise ValueError(f"unknown equivalence result prefix: {prefix!r}")

