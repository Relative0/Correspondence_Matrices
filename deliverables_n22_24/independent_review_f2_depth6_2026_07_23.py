"""Independent review of F2 on a family V3 did not test: depth-6, n=20.

Paired thresholds 7 and 16 on 120 deeper formulas (higher live_k mass than the
depth-4 family), interleaved order, same rep count both sides, complete packed
equality against the raw-AST flat Bitset control.
"""
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

N = 20
DEPTH = 6
TRIALS = 120
ROUNDS = 5
GUARD = 16


def timed(fn, reps):
    start = perf_counter()
    for _ in range(reps):
        fn()
    return (perf_counter() - start) / reps


def result_bits(result):
    if result.bits is not None:
        return int(result.bits)
    flat = np.asarray(result.tt, dtype=np.uint8).reshape(-1)
    return int.from_bytes(np.packbits(flat, bitorder="little").tobytes(), "little")


def main():
    vars_all = tuple(f"x{i}" for i in range(N))
    rows = []
    for trial in range(TRIALS):
        expr = random_expr(
            N, np.random.default_rng(37_500_000 + trial), max_depth=DEPTH, p_unary=0.25
        )
        node = compile_expr_to_cm_ir(expr)
        live_k = len(node.vars)

        def run_cm(threshold):
            return materialize_hybrid_no_reinflate(
                node,
                vars_all,
                fixed={},
                hybrid_threshold=threshold,
                allow_reduced_output=True,
                max_full_output_vars=GUARD,
                flat_eval=True,
            )

        try:
            first7 = run_cm(7)
            first16 = run_cm(16)
        except ValueError:
            continue  # guard-declined (live_k beyond GUARD): thresholds irrelevant
        output_vars = tuple(first16.output_vars)
        if tuple(first7.output_vars) != output_vars:
            raise AssertionError("threshold changed output scope")
        fixed = {name: 0 for name in vars_all if name not in output_vars}
        bs = eval_expr_flat_bitset(expr, output_vars, fixed=fixed)
        if result_bits(first7) != bs or result_bits(first16) != bs:
            raise AssertionError(f"packed mismatch trial={trial}")

        estimate = max(timed(lambda: run_cm(7), 3), timed(lambda: run_cm(16), 3)) * 1e6
        reps = 100 if estimate < 50 else (30 if estimate < 500 else 7)
        samples = {"t7": [], "t16": []}
        for round_index in range(ROUNDS):
            order = ("t7", "t16") if (trial + round_index) & 1 else ("t16", "t7")
            for name in order:
                fn = (lambda: run_cm(7)) if name == "t7" else (lambda: run_cm(16))
                samples[name].append(timed(fn, reps) * 1e6)
        rows.append(
            {
                "trial": trial,
                "live_k": live_k,
                "output_k": len(output_vars),
                "reps": reps,
                "t7_us": statistics.median(samples["t7"]),
                "t16_us": statistics.median(samples["t16"]),
                "t16_over_t7": statistics.median(samples["t16"]) / statistics.median(samples["t7"]),
            }
        )

    strata = (("le7", 0, 7), ("8_11", 8, 11), ("12_16", 12, 16))
    summary = []
    for label, low, high in strata:
        sel = [r for r in rows if low <= r["live_k"] <= high]
        if not sel:
            continue
        ratios = [r["t16_over_t7"] for r in sel]
        summary.append(
            {
                "family": f"depth{DEPTH}_n{N}",
                "stratum": label,
                "count": len(sel),
                "t16_over_t7_median": round(statistics.median(ratios), 4),
                "t16_over_t7_p10": round(float(np.percentile(ratios, 10)), 4),
                "t16_over_t7_p90": round(float(np.percentile(ratios, 90)), 4),
            }
        )
    with (REPO / "deliverables_n22_24" / "CM_independent_review_f2_depth6.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in summary:
        print(row)
    print(f"{len(rows)} timed formulas (declines excluded), all bit-exact")


if __name__ == "__main__":
    main()
