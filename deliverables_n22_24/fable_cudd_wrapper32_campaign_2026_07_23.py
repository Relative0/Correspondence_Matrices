"""CUDD extension of the robust wrapper campaign, n=16-32 (2026-07-23).

Identical expression stream to fable_wrapper_stats300 (t16 variant): 300 depth-4
random expressions per n via seed 9_100_000 + 10_000*n + trial, hybrid threshold 16,
guard 16, 5 interleaved timing rounds. Adds per-formula ROBDD symbolic-build timing
for both dd.cudd and dd.autoref (best-of-k order, 10 sweeps, sampled correctness),
so CUDD can be charted next to the CM/Bitset ratio at every n including 32.
ROBDD build is symbolic only — no truth-table extraction (infeasible at n>16 scale);
it is a different deliverable than the CM/Bitset flat outputs and must not be
collapsed with them.

Runs on the RunPod pod from the repo tarball (cwd = extracted repo root).
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bitset_backend import eval_expr_flat_bitset
from cm_exprlib import random_expr
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate
from cmbench.backends.robdd_dd import run_robdd_dd_backend

import os

SIZES = tuple(int(s) for s in os.environ.get(
    "CUDD_W32_SIZES", "16,18,20,22,24,26,28,30,32").split(","))
TRIALS = int(os.environ.get("CUDD_W32_TRIALS", "300"))
ROUNDS = 5
GUARD = 16
THRESHOLD = 16
ROBDD_SWEEPS = 10
CORRECTNESS_SAMPLES = 64


def timed(fn, reps):
    t0 = perf_counter()
    for _ in range(reps):
        fn()
    return (perf_counter() - t0) / reps


def pct(vals, q):
    return float(np.percentile(np.asarray(vals, dtype=float), q))


raw = []
for n in SIZES:
    vars_all = tuple(f"x{i}" for i in range(n))
    large_n = n > 16
    for trial in range(TRIALS):
        rng = np.random.default_rng(9_100_000 + 10_000 * n + trial)
        expr = random_expr(n, rng, max_depth=4, p_unary=0.25)
        node = compile_expr_to_cm_ir(expr)
        live_k = len(node.vars)

        res = materialize_hybrid_no_reinflate(
            node, vars_all, fixed={},
            hybrid_threshold=THRESHOLD,
            allow_reduced_output=large_n,
            max_full_output_vars=GUARD,
            flat_eval=True,
        )
        output_vars = tuple(res.output_vars)
        raw_fixed = {v: 0 for v in vars_all if v not in output_vars}

        def run_cm():
            return materialize_hybrid_no_reinflate(
                node, vars_all, fixed={},
                hybrid_threshold=THRESHOLD,
                allow_reduced_output=large_n,
                max_full_output_vars=GUARD,
                flat_eval=True,
            )

        def run_bs():
            return eval_expr_flat_bitset(expr, output_vars, fixed=raw_fixed)

        bits_bs = run_bs()
        if res.bits is not None:
            ok = int(res.bits) == int(bits_bs)
        else:
            from bitset_backend import bitset_to_bool_array
            ok = bool(np.array_equal(
                np.asarray(res.tt, dtype=np.uint8).reshape(-1),
                bitset_to_bool_array(int(bits_bs), len(output_vars))))

        run_cm(); run_bs()  # warm caches
        est = timed(run_cm, 3) * 1e6
        reps = 200 if est < 50 else (40 if est < 500 else 10)
        t_cm, t_bs = [], []
        for rnd in range(ROUNDS):
            if (trial + rnd) % 2:
                t_cm.append(timed(run_cm, reps) * 1e6)
                t_bs.append(timed(run_bs, reps) * 1e6)
            else:
                t_bs.append(timed(run_bs, reps) * 1e6)
                t_cm.append(timed(run_cm, reps) * 1e6)
        cm_us = statistics.median(t_cm)
        bs_us = statistics.median(t_bs)

        robdd = {}
        for pref in ("cudd", "autoref"):
            r = run_robdd_dd_backend(
                expr, n,
                backend_preference=pref,
                order_policy="best-of-k",
                order_sweeps=ROBDD_SWEEPS,
                order_seed=trial,
                correctness_rng=np.random.default_rng(7_700_000 + 10_000 * n + trial),
                correctness_samples=CORRECTNESS_SAMPLES,
            )
            robdd[f"{pref}_backend"] = r["robdd_backend"]
            robdd[f"{pref}_is_cudd"] = r["robdd_is_cudd"]
            robdd[f"{pref}_status"] = r["robdd_status"]
            robdd[f"{pref}_ok"] = r["robdd_ok"]
            robdd[f"{pref}_build_best_us"] = (
                r["robdd_best_time_s"] * 1e6 if r["robdd_best_time_s"] is not None else None)
            robdd[f"{pref}_build_median_us"] = (
                r["robdd_median_time_s"] * 1e6 if r["robdd_median_time_s"] is not None else None)
            robdd[f"{pref}_nodes"] = r["robdd_median_nodes"]

        raw.append({
            "n": n, "trial": trial, "live_k": live_k,
            "repr": res.final_output_representation_code,
            "output_k": len(output_vars), "reps": reps, "ok": ok,
            "cm_us": cm_us, "bitset_us": bs_us, "ratio": cm_us / bs_us,
            **robdd,
        })
    done = [r for r in raw if r["n"] == n]
    print(f"n={n}: {len(done)} trials, ok={sum(r['ok'] for r in done)}, "
          f"cudd_ok={sum(1 for r in done if r['cudd_ok'])}", flush=True)

summary = []
for n in SIZES:
    sel = [r for r in raw if r["n"] == n]
    summary.append({
        "n": n, "trials": len(sel),
        "all_correct": all(r["ok"] for r in sel),
        "cudd_all_status_ok": all(r["cudd_status"] == "ok" for r in sel),
        "cudd_all_is_cudd": all(r["cudd_is_cudd"] for r in sel),
        "cudd_sampled_ok_count": sum(1 for r in sel if r["cudd_ok"]),
        "autoref_sampled_ok_count": sum(1 for r in sel if r["autoref_ok"]),
        "live_k_median": statistics.median([r["live_k"] for r in sel]),
        "cm_us_median": round(statistics.median(r["cm_us"] for r in sel), 2),
        "bitset_us_median": round(statistics.median(r["bitset_us"] for r in sel), 2),
        "ratio_cm_bitset_median": round(statistics.median(r["ratio"] for r in sel), 3),
        "ratio_p10": round(pct([r["ratio"] for r in sel], 10), 3),
        "ratio_p90": round(pct([r["ratio"] for r in sel], 90), 3),
        "cudd_build_us_median": round(statistics.median(
            r["cudd_build_median_us"] for r in sel), 2),
        "autoref_build_us_median": round(statistics.median(
            r["autoref_build_median_us"] for r in sel), 2),
        "ratio_cudd_build_bitset_median": round(statistics.median(
            r["cudd_build_median_us"] / r["bitset_us"] for r in sel), 3),
        "ratio_cudd_build_cm_median": round(statistics.median(
            r["cudd_build_median_us"] / r["cm_us"] for r in sel), 3),
        "cudd_nodes_median": statistics.median(r["cudd_nodes"] for r in sel),
    })
    print("summary", summary[-1], flush=True)

for name, rows in (("CM_FABLE_cudd_wrapper32_raw.csv", raw),
                   ("CM_FABLE_cudd_wrapper32_summary.csv", summary)):
    with open(name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", name, flush=True)
