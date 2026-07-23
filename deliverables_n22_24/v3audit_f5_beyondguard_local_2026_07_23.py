"""Audit V3 local reproduction of one high-live_k row per Regime-B cell."""
from __future__ import annotations

import csv
import gc
import statistics
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import bitset_backend as bb
from cm_exprlib import random_expr
from cm_ir import compile_expr_to_cm_ir
from deliverables_n22_24.fable_comprehensive_tail_worker_2026_07_22 import (
    sampled_oracle_ok,
)


def timed(fn) -> float:
    start = perf_counter()
    fn()
    return (perf_counter() - start) * 1e6


def main() -> None:
    out_dir = REPO / "deliverables_n22_24"
    with (out_dir / "CM_FABLE_comprehensive_beyondguard.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        sources = list(csv.DictReader(handle))
    selected = []
    for n in (24, 28, 32):
        for depth in (6, 8):
            cell = [
                row
                for row in sources
                if int(row["n"]) == n and int(row["depth"]) == depth
            ]
            selected.append(max(cell, key=lambda row: int(row["live_k"])))

    output_rows: list[dict[str, object]] = []
    for source in selected:
        n = int(source["n"])
        depth = int(source["depth"])
        trial = int(source["trial"])
        vars_all = tuple(f"x{i}" for i in range(n))
        expr = random_expr(
            n,
            np.random.default_rng(
                63_000_000 + n * 100_000 + depth * 10_000 + trial
            ),
            max_depth=depth,
            p_unary=0.25,
        )
        node = compile_expr_to_cm_ir(expr)
        live_set = set(node.vars)
        live = tuple(name for name in vars_all if name in live_set)
        dropped = {name: 0 for name in vars_all if name not in live_set}
        if len(live) != int(source["live_k"]):
            raise AssertionError("regenerated live_k differs from committed row")
        cm_bits = bb.eval_cm_node_words(node, live)
        raw_bits = bb.eval_expr_words_bitset(expr, live, fixed=dropped)
        if cm_bits != raw_bits:
            raise AssertionError("complete packed output mismatch")
        oracle = sampled_oracle_ok(
            expr,
            cm_bits,
            live,
            dropped,
            2000,
            seed=96_000 + n * 100 + trial,
        )
        if not oracle:
            raise AssertionError("sampled scalar oracle mismatch")

        def run_cm():
            return bb.eval_cm_node_words(node, live)

        def run_raw():
            return bb.eval_expr_words_bitset(expr, live, fixed=dropped)

        cm_samples: list[float] = []
        raw_samples: list[float] = []
        for round_index in range(5):
            if round_index & 1:
                cm_samples.append(timed(run_cm))
                raw_samples.append(timed(run_raw))
            else:
                raw_samples.append(timed(run_raw))
                cm_samples.append(timed(run_cm))
        cm_us = statistics.median(cm_samples)
        raw_us = statistics.median(raw_samples)
        output_rows.append(
            {
                "n": n,
                "depth": depth,
                "trial": trial,
                "live_k": len(live),
                "rows_exhaustively_compared": 1 << len(live),
                "committed_cm_words_us": source["cm_words_us"],
                "committed_bitset_words_us": source["bs_words_us"],
                "committed_ratio": source["ratio_words"],
                "local_cm_words_us": cm_us,
                "local_bitset_words_us": raw_us,
                "local_ratio": cm_us / raw_us,
                "complete_packed_equal": True,
                "scalar_oracle_2000": oracle,
            }
        )
        print(
            f"n={n} depth={depth} live_k={len(live)} ratio={cm_us / raw_us:.3f}",
            flush=True,
        )
        del expr, node, cm_bits, raw_bits
        bb.clear_words_env_cache()
        bb.clear_bitset_env_cache()
        gc.collect()

    with (out_dir / "CM_V3AUDIT_F5_beyondguard_local.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)


if __name__ == "__main__":
    main()
