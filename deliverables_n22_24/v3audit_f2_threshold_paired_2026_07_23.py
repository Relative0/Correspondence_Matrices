"""Audit V3 paired rerun of hybrid thresholds 7 and 16.

Same 300-formula population as the Fable campaign. For each formula, threshold
7, threshold 16, and the fair raw-AST Bitset control are timed in a rotating
interleaved order for five rounds. Complete packed outputs are compared.
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

from bitset_backend import bitset_to_bool_array, eval_expr_flat_bitset
from cm_exprlib import random_expr
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate

SIZES = (16, 18, 20, 22, 24)
TRIALS = 300
ROUNDS = 5
GUARD = 16
THRESHOLDS = (7, 16)


def timed(fn, reps: int) -> float:
    t0 = perf_counter()
    for _ in range(reps):
        fn()
    return (perf_counter() - t0) / reps


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q))


def result_bits(result) -> int:
    if result.bits is not None:
        return int(result.bits)
    flat = np.asarray(result.tt, dtype=np.uint8).reshape(-1)
    return int.from_bytes(np.packbits(flat, bitorder="little").tobytes(), "little")


def main() -> None:
    raw: list[dict[str, object]] = []
    for n in SIZES:
        vars_all = tuple(f"x{i}" for i in range(n))
        allow_reduced = n > GUARD
        for trial in range(TRIALS):
            rng = np.random.default_rng(9_100_000 + 10_000 * n + trial)
            expr = random_expr(n, rng, max_depth=4, p_unary=0.25)
            node = compile_expr_to_cm_ir(expr)
            live_k = len(node.vars)

            def run_cm(threshold: int):
                return materialize_hybrid_no_reinflate(
                    node,
                    vars_all,
                    fixed={},
                    hybrid_threshold=threshold,
                    allow_reduced_output=allow_reduced,
                    max_full_output_vars=GUARD,
                    flat_eval=True,
                )

            initial = {threshold: run_cm(threshold) for threshold in THRESHOLDS}
            output_vars = tuple(initial[16].output_vars)
            if tuple(initial[7].output_vars) != output_vars:
                raise AssertionError("threshold changed output scope")
            raw_fixed = {name: 0 for name in vars_all if name not in output_vars}

            def run_bs() -> int:
                return eval_expr_flat_bitset(expr, output_vars, fixed=raw_fixed)

            bs_bits = run_bs()
            ok7 = result_bits(initial[7]) == bs_bits
            ok16 = result_bits(initial[16]) == bs_bits
            if not (ok7 and ok16):
                raise AssertionError(f"packed mismatch n={n} trial={trial}")

            run_cm(7)
            run_cm(16)
            run_bs()
            estimate = max(timed(lambda: run_cm(7), 3), timed(lambda: run_cm(16), 3)) * 1e6
            reps = 100 if estimate < 50 else (30 if estimate < 500 else 7)
            timings = {"t7": [], "t16": [], "bs": []}
            funcs = {
                "t7": lambda: run_cm(7),
                "t16": lambda: run_cm(16),
                "bs": run_bs,
            }
            base_order = ("t7", "t16", "bs")
            for round_index in range(ROUNDS):
                offset = (trial + round_index) % len(base_order)
                order = base_order[offset:] + base_order[:offset]
                for name in order:
                    timings[name].append(timed(funcs[name], reps) * 1e6)
            med = {name: statistics.median(values) for name, values in timings.items()}
            raw.append(
                {
                    "n": n,
                    "trial": trial,
                    "live_k": live_k,
                    "output_k": len(output_vars),
                    "repr_t7": initial[7].final_output_representation_code,
                    "repr_t16": initial[16].final_output_representation_code,
                    "reps": reps,
                    "rounds": ROUNDS,
                    "ok_t7": ok7,
                    "ok_t16": ok16,
                    "threshold7_us": med["t7"],
                    "threshold16_us": med["t16"],
                    "bitset_us": med["bs"],
                    "t7_over_bitset": med["t7"] / med["bs"],
                    "t16_over_bitset": med["t16"] / med["bs"],
                    "t16_over_t7": med["t16"] / med["t7"],
                }
            )
        print(f"n={n}: {TRIALS} paired formulas complete", flush=True)

    summary: list[dict[str, object]] = []
    strata = (("le4", 0, 4), ("5_7", 5, 7), ("8_11", 8, 11), ("12_16", 12, 16))
    for n in SIZES:
        n_rows = [row for row in raw if row["n"] == n]
        for label, low, high in strata:
            selected = [row for row in n_rows if low <= int(row["live_k"]) <= high]
            if not selected:
                continue
            paired = [float(row["t16_over_t7"]) for row in selected]
            ratios16 = [float(row["t16_over_bitset"]) for row in selected]
            summary.append(
                {
                    "n": n,
                    "live_k_stratum": label,
                    "count": len(selected),
                    "all_correct": all(bool(row["ok_t7"]) and bool(row["ok_t16"]) for row in selected),
                    "threshold16_over_threshold7_median": statistics.median(paired),
                    "threshold16_over_threshold7_p10": percentile(paired, 10),
                    "threshold16_over_threshold7_p90": percentile(paired, 90),
                    "threshold16_over_bitset_median": statistics.median(ratios16),
                    "threshold16_over_bitset_p10": percentile(ratios16, 10),
                    "threshold16_over_bitset_p90": percentile(ratios16, 90),
                }
            )

    out = REPO / "deliverables_n22_24"
    with (out / "CM_V3AUDIT_F2_threshold_paired_raw.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(raw[0]))
        writer.writeheader()
        writer.writerows(raw)
    with (out / "CM_V3AUDIT_F2_threshold_paired_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print(f"{len(raw)} formulas; {len(summary)} summary strata; all bit-exact")


if __name__ == "__main__":
    main()
