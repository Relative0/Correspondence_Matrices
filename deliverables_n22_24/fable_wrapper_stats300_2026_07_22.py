"""Statistically robust CM-wrapper vs fair-Bitset ratios at reduced scope.

300 depth-4 random expressions per n (vs 8 in the first pass), 5 interleaved
timing rounds each, medians + spread, stratified by live_k and repr code.
Correctness: CM output vs corrected Bitset comparator per trial (exact packed
equality over the reduced scope).
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

REPO = Path(r"C:\Users\brian\Documents\CM_Computation")
sys.path.insert(0, str(REPO))

from bitset_backend import eval_expr_flat_bitset
from cm_exprlib import random_expr
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate

SIZES = (16, 18, 20, 22, 24)
TRIALS = 300
ROUNDS = 5
GUARD = 16
THRESHOLD = 7


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

        # correctness (exhaustive over the reduced scope by packed equality)
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
        raw.append({
            "n": n, "trial": trial, "live_k": live_k,
            "repr": res.final_output_representation_code,
            "output_k": len(output_vars), "reps": reps, "ok": ok,
            "cm_us": cm_us, "bitset_us": bs_us, "ratio": cm_us / bs_us,
        })
    done = [r for r in raw if r["n"] == n]
    print(f"n={n}: {len(done)} trials, ok={sum(r['ok'] for r in done)}", flush=True)

summary = []
for n in SIZES:
    sel = [r for r in raw if r["n"] == n]
    ratios = [r["ratio"] for r in sel]
    lks = [r["live_k"] for r in sel]
    def bucket(rs):
        return round(statistics.median(rs), 3) if rs else None
    summary.append({
        "n": n, "trials": len(sel), "all_correct": all(r["ok"] for r in sel),
        "live_k_median": statistics.median(lks),
        "live_k_p90": pct(lks, 90), "live_k_max": max(lks),
        "repr4_count": sum(1 for r in sel if r["repr"] == 4 or (r["live_k"] > THRESHOLD and n > 16)),
        "cm_us_median": round(statistics.median(r["cm_us"] for r in sel), 2),
        "bitset_us_median": round(statistics.median(r["bitset_us"] for r in sel), 2),
        "ratio_median": round(statistics.median(ratios), 3),
        "ratio_p10": round(pct(ratios, 10), 3),
        "ratio_p90": round(pct(ratios, 90), 3),
        "ratio_by_livek_le4": bucket([r["ratio"] for r in sel if r["live_k"] <= 4]),
        "ratio_by_livek_5_7": bucket([r["ratio"] for r in sel if 5 <= r["live_k"] <= 7]),
        "ratio_by_livek_ge8": bucket([r["ratio"] for r in sel if r["live_k"] >= 8]),
        "count_livek_ge8": sum(1 for r in sel if r["live_k"] >= 8),
    })

out = REPO / "deliverables_n22_24"
with (out / "CM_FABLE_wrapper_stats300_raw.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(raw[0])); w.writeheader(); w.writerows(raw)
with (out / "CM_FABLE_wrapper_stats300_summary.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
print(json.dumps(summary, indent=2))
