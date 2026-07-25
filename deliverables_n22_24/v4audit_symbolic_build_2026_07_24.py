"""Representation-build audit on the immutable V4 corpus.

Local Windows has dd.autoref but not dd.cudd.  Each row therefore records the
explicit CUDD refusal alongside CM/FlatProgram/autoref measurements; it never
substitutes autoref for a requested CUDD run.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bitset_backend import get_expr_flat_program
from cm_expr_serde import expr_from_json
from cm_ir import clear_cm_ir_compile_cache, compile_expr_to_cm_ir
from cmbench.backends.robdd_dd import run_robdd_dd_backend

BASE = Path(__file__).resolve().parent
CORPUS = BASE / "v4audit_corpus_2026_07_24.jsonl"
RAW = BASE / "CM_v4audit_symbolic_build_raw.csv"
SUMMARY = BASE / "CM_v4audit_symbolic_build_summary.csv"


def micros(fn):
    t0 = time.perf_counter()
    value = fn()
    return (time.perf_counter() - t0) * 1e6, value


def main():
    rows = []
    for item in map(json.loads, CORPUS.read_text(encoding="utf-8").splitlines()):
        expr = expr_from_json(item["expression"])
        clear_cm_ir_compile_cache()
        cm_us, node = micros(lambda: compile_expr_to_cm_ir(expr))
        flat_us, prog = micros(lambda: get_expr_flat_program(expr))
        fixed = run_robdd_dd_backend(
            expr, item["nominal_n"], backend_preference="autoref",
            order_policy="fixed", correctness_samples=64,
        )
        best10 = run_robdd_dd_backend(
            expr, item["nominal_n"], backend_preference="autoref",
            order_policy="best-of-k", order_sweeps=10, order_seed=20260724,
            correctness_samples=64,
        )
        cudd = run_robdd_dd_backend(
            expr, item["nominal_n"], backend_preference="cudd",
            order_policy="fixed", correctness_samples=64,
        )
        cudd_best10 = run_robdd_dd_backend(
            expr, item["nominal_n"], backend_preference="cudd",
            order_policy="best-of-k", order_sweeps=10, order_seed=20260724,
            correctness_samples=64,
        )
        cudd_dynamic = run_robdd_dd_backend(
            expr, item["nominal_n"], backend_preference="cudd",
            order_policy="fixed", dynamic_reordering=True, correctness_samples=64,
        )
        if cudd["robdd_status"] == "unavailable":
            if cudd["robdd_backend"] is not None:
                raise AssertionError("explicit CUDD request silently fell back")
        elif not (cudd["robdd_backend"] == "dd.cudd" and cudd["robdd_is_cudd"]):
            raise AssertionError("explicit CUDD request did not identify dd.cudd")
        rows.append({
            "id": item["id"], "nominal_n": item["nominal_n"], "family": item["family"],
            "live_k": item["semantic_live_k"], "cm_compile_us": cm_us,
            "cm_dag_nodes": len(prog.loads) + len(prog.ops),
            "flat_prepare_us": flat_us, "flat_slots": prog.n_slots, "flat_ops": len(prog.ops),
            "autoref_fixed_build_us": float(fixed["robdd_build_time_s"]) * 1e6,
            "autoref_fixed_nodes": fixed["robdd_node_count"],
            "autoref_fixed_ok": fixed["robdd_ok"],
            "autoref_best10_selected_build_us": float(best10["robdd_build_time_s"]) * 1e6,
            "autoref_best10_min_build_us": float(best10["robdd_best_time_s"]) * 1e6,
            "autoref_best10_median_build_us": float(best10["robdd_median_time_s"]) * 1e6,
            "autoref_best10_nodes": best10["robdd_node_count"],
            "autoref_best10_ok": best10["robdd_ok"],
            "order_search_trials": 10,
            "order_search_wall_lower_bound_us": float(best10["robdd_median_time_s"]) * 10e6,
            "cudd_status": cudd["robdd_status"], "cudd_backend": cudd["robdd_backend"],
            "cudd_is_cudd": cudd["robdd_is_cudd"],
            "cudd_fixed_build_us": (
                float(cudd["robdd_build_time_s"]) * 1e6
                if cudd["robdd_build_time_s"] is not None else None
            ),
            "cudd_best10_selected_build_us": (
                float(cudd_best10["robdd_build_time_s"]) * 1e6
                if cudd_best10["robdd_build_time_s"] is not None else None
            ),
            "cudd_best10_median_build_us": (
                float(cudd_best10["robdd_median_time_s"]) * 1e6
                if cudd_best10["robdd_median_time_s"] is not None else None
            ),
            "cudd_best10_fastest_build_us": (
                float(cudd_best10["robdd_fastest_build_time_s"]) * 1e6
                if cudd_best10["robdd_fastest_build_time_s"] is not None else None
            ),
            "cudd_best10_smallest_node_build_us": (
                float(cudd_best10["robdd_smallest_node_build_time_s"]) * 1e6
                if cudd_best10["robdd_smallest_node_build_time_s"] is not None else None
            ),
            "cudd_best10_selected_trial_index": cudd_best10["robdd_selected_trial_index"],
            "cudd_best10_selection_objective": cudd_best10["robdd_selection_objective"],
            "cudd_best10_selection_tiebreak": cudd_best10["robdd_selection_tiebreak"],
            "cudd_best10_order_generation_us": (
                float(cudd_best10["robdd_order_generation_time_s"]) * 1e6
            ),
            "cudd_best10_order_search_us": (
                float(cudd_best10["robdd_order_search_time_s"]) * 1e6
            ),
            "cudd_best10_all_in_search_us": (
                float(cudd_best10["robdd_all_in_search_time_s"]) * 1e6
            ),
            "cudd_best10_trials_json": cudd_best10["robdd_order_trials_json"],
            "cudd_dynamic_build_us": (
                float(cudd_dynamic["robdd_build_time_s"]) * 1e6
                if cudd_dynamic["robdd_build_time_s"] is not None else None
            ),
            "cudd_dynamic_reorder_us": (
                float(cudd_dynamic["robdd_reorder_time_s"]) * 1e6
                if cudd_dynamic["robdd_reorder_time_s"] is not None else None
            ),
        })
    with RAW.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    summary = []
    for family in sorted({r["family"] for r in rows}):
        sel = [r for r in rows if r["family"] == family]
        summary.append({
            "family": family, "formulas": len(sel),
            "live_k_median": statistics.median(r["live_k"] for r in sel),
            "cm_compile_us_median": statistics.median(r["cm_compile_us"] for r in sel),
            "flat_prepare_us_median": statistics.median(r["flat_prepare_us"] for r in sel),
            "autoref_fixed_build_us_median": statistics.median(r["autoref_fixed_build_us"] for r in sel),
            "autoref_best10_selected_build_us_median": statistics.median(r["autoref_best10_selected_build_us"] for r in sel),
            "all_autoref_correct": all(r["autoref_fixed_ok"] and r["autoref_best10_ok"] for r in sel),
            "cudd_mode": (
                "available_verified" if all(r["cudd_backend"] == "dd.cudd" and r["cudd_is_cudd"] for r in sel)
                else "unavailable_fail_closed" if all(r["cudd_status"] == "unavailable" and not r["cudd_backend"] for r in sel)
                else "mixed_or_error"
            ),
        })
    with SUMMARY.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
    modes = sorted({row["cudd_mode"] for row in summary})
    print(f"wrote {len(rows)} build rows; CUDD modes={modes}")


if __name__ == "__main__":
    main()
