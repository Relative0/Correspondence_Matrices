"""Audit V3 n=24 sampling-luck spot check with two fresh seed populations."""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bitset_backend import eval_expr_flat_bitset
from cm_exprlib import random_expr
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate

N = 24
TRIALS = 300
ROUNDS = 5
THRESHOLD = 16
GUARD = 16
SEEDS = (13_700_000, 28_900_000)


def timed(fn, reps: int) -> float:
    start = perf_counter()
    for _ in range(reps):
        fn()
    return (perf_counter() - start) / reps


def main() -> None:
    vars_all = tuple(f"x{i}" for i in range(N))
    rows: list[dict[str, object]] = []
    for seed_base in SEEDS:
        for trial in range(TRIALS):
            expr = random_expr(
                N,
                np.random.default_rng(seed_base + trial),
                max_depth=4,
                p_unary=0.25,
            )
            node = compile_expr_to_cm_ir(expr)
            live_k = len(node.vars)

            def run_cm():
                return materialize_hybrid_no_reinflate(
                    node,
                    vars_all,
                    fixed={},
                    hybrid_threshold=THRESHOLD,
                    allow_reduced_output=True,
                    max_full_output_vars=GUARD,
                    flat_eval=True,
                )

            initial = run_cm()
            output_vars = tuple(initial.output_vars)
            fixed = {name: 0 for name in vars_all if name not in output_vars}

            def run_bs() -> int:
                return eval_expr_flat_bitset(expr, output_vars, fixed=fixed)

            bs_bits = run_bs()
            if initial.bits is None or int(initial.bits) != bs_bits:
                raise AssertionError(f"packed mismatch seed={seed_base} trial={trial}")
            run_cm()
            run_bs()
            estimate = timed(run_cm, 3) * 1e6
            reps = 150 if estimate < 50 else (30 if estimate < 500 else 7)
            cm_rounds: list[float] = []
            bs_rounds: list[float] = []
            for round_index in range(ROUNDS):
                if (trial + round_index) & 1:
                    cm_rounds.append(timed(run_cm, reps) * 1e6)
                    bs_rounds.append(timed(run_bs, reps) * 1e6)
                else:
                    bs_rounds.append(timed(run_bs, reps) * 1e6)
                    cm_rounds.append(timed(run_cm, reps) * 1e6)
            cm_us = statistics.median(cm_rounds)
            bs_us = statistics.median(bs_rounds)
            rows.append(
                {
                    "seed_base": seed_base,
                    "trial": trial,
                    "n": N,
                    "live_k": live_k,
                    "output_k": len(output_vars),
                    "repr": initial.final_output_representation_code,
                    "reps": reps,
                    "rounds": ROUNDS,
                    "ok": True,
                    "cm_us": cm_us,
                    "bitset_us": bs_us,
                    "ratio": cm_us / bs_us,
                }
            )
        print(f"seed={seed_base}: {TRIALS} formulas complete", flush=True)

    summaries: list[dict[str, object]] = []
    for seed_base in SEEDS:
        selected = [row for row in rows if row["seed_base"] == seed_base]
        ratios = [float(row["ratio"]) for row in selected]
        live = [int(row["live_k"]) for row in selected]
        summaries.append(
            {
                "seed_base": seed_base,
                "n": N,
                "trials": len(selected),
                "all_correct": all(bool(row["ok"]) for row in selected),
                "ratio_median": statistics.median(ratios),
                "ratio_p10": float(np.percentile(ratios, 10)),
                "ratio_p90": float(np.percentile(ratios, 90)),
                "live_k_median": statistics.median(live),
                "live_k_p90": float(np.percentile(live, 90)),
                "live_k_max": max(live),
                "count_live_k_ge8": sum(value >= 8 for value in live),
            }
        )

    out = REPO / "deliverables_n22_24"
    with (out / "CM_V3AUDIT_F3_n24_seeds_raw.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (out / "CM_V3AUDIT_F3_n24_seeds_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    print(summaries)


if __name__ == "__main__":
    main()
