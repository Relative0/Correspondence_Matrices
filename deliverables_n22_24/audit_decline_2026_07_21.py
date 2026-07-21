"""Audit live-variable selection and the reduced-output safety guard."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cm_exprlib import random_expr  # noqa: E402
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default="16,20,24,28,32")
    parser.add_argument("--depths", default="4,5,6,8")
    parser.add_argument("--trials", type=int, default=300)
    args = parser.parse_args()
    rows = []
    for n in [int(x) for x in args.sizes.split(",")]:
        for depth in [int(x) for x in args.depths.split(",")]:
            live_counts = []
            declined = 0
            wrong_guard = 0
            oversized_output = 0
            for trial in range(args.trials):
                rng = np.random.default_rng(20260721 + n * 10000 + depth * 100 + trial)
                expr = random_expr(n, rng, max_depth=depth, p_unary=0.25)
                node = compile_expr_to_cm_ir(expr)
                live_k = len(node.vars)
                live_counts.append(live_k)
                try:
                    result = materialize_hybrid_no_reinflate(
                        node,
                        tuple(f"x{i}" for i in range(n)),
                        fixed={},
                        hybrid_threshold=64,
                        allow_reduced_output=n > 16,
                        max_full_output_vars=16,
                        flat_eval=True,
                    )
                    if live_k > 16:
                        wrong_guard += 1
                    if len(result.output_vars) > 16 or (
                        result.bits is not None and int(result.bits).bit_length() > (1 << len(result.output_vars))
                    ):
                        oversized_output += 1
                except ValueError as exc:
                    is_decline = str(exc).startswith("refusing to materialize reduced no-reinflate output")
                    declined += int(is_decline)
                    if live_k <= 16 or not is_decline:
                        wrong_guard += 1
            rows.append(
                {
                    "n": n,
                    "depth": depth,
                    "trials": args.trials,
                    "min_live_k": min(live_counts),
                    "median_live_k": float(np.median(live_counts)),
                    "max_live_k": max(live_counts),
                    "declined_count": declined,
                    "declined_rate": declined / args.trials,
                    "wrong_guard_count": wrong_guard,
                    "oversized_output_count": oversized_output,
                }
            )
            print(rows[-1], flush=True)
    with (HERE / "CM_audit_2026-07-21_decline_distribution.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if any(r["wrong_guard_count"] or r["oversized_output_count"] for r in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
