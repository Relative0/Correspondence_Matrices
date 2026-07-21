"""Measure traced peak allocations for retained versus last-use-free flat slots."""

from __future__ import annotations

import argparse
import csv
import gc
from pathlib import Path
import statistics
import sys
import tracemalloc

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from bitset_backend import eval_cm_node_flat, eval_expr_flat_bitset  # noqa: E402
from cm_ir import compile_expr_to_cm_ir  # noqa: E402
from cmbench.expr.generators import random_expr_balanced_all_vars  # noqa: E402


def peak_delta(fn) -> int:
    gc.collect()
    tracemalloc.start()
    before, _ = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    fn()
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return max(0, peak - before)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default="18,20,22")
    parser.add_argument("--trials", type=int, default=5)
    args = parser.parse_args()
    if args.trials < 5:
        raise SystemExit("use at least five trials")
    raw = []
    for n in [int(x) for x in args.sizes.split(",")]:
        vars_all = tuple(f"x{i}" for i in range(n))
        for trial in range(args.trials):
            expr = random_expr_balanced_all_vars(
                n, np.random.default_rng(20260721 + n * 100 + trial), max_depth=8
            )
            node = compile_expr_to_cm_ir(expr)
            methods = {
                "raw_flat_retained": lambda: eval_expr_flat_bitset(
                    expr, vars_all, free_dead_slots=False
                ),
                "raw_flat_liveness": lambda: eval_expr_flat_bitset(
                    expr, vars_all, free_dead_slots=True
                ),
                "cm_flat_retained": lambda: eval_cm_node_flat(
                    node, vars_all, free_dead_slots=False
                ),
                "cm_flat_liveness": lambda: eval_cm_node_flat(
                    node, vars_all, free_dead_slots=True
                ),
            }
            for method, fn in methods.items():
                fn()  # lower/bind before tracing
                raw.append(
                    {
                        "n": n,
                        "trial": trial,
                        "method": method,
                        "traced_peak_bytes": peak_delta(fn),
                    }
                )
    summary = []
    for n in sorted({int(r["n"]) for r in raw}):
        selected = [r for r in raw if r["n"] == n]
        medians = {
            method: statistics.median(
                int(r["traced_peak_bytes"]) for r in selected if r["method"] == method
            )
            for method in (
                "raw_flat_retained",
                "raw_flat_liveness",
                "cm_flat_retained",
                "cm_flat_liveness",
            )
        }
        summary.append(
            {
                "n": n,
                **{f"{method}_peak_bytes_median": value for method, value in medians.items()},
                "raw_peak_reduction": medians["raw_flat_retained"] / medians["raw_flat_liveness"],
                "cm_peak_reduction": medians["cm_flat_retained"] / medians["cm_flat_liveness"],
            }
        )
    for name, rows in (("raw", raw), ("summary", summary)):
        with (HERE / f"CM_flat_liveness_memory_{name}.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    for row in summary:
        print(row)


if __name__ == "__main__":
    main()
