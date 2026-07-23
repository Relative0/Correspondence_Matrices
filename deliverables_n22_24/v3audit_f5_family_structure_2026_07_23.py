"""Audit V3 structural and semantic audit of the comprehensive families."""
from __future__ import annotations

import csv
import math
import statistics
import sys
from pathlib import Path

import numpy as np
from dd.autoref import BDD

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import bitset_backend as bb
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, random_expr
from cm_ir import compile_expr_to_cm_ir
from deliverables_n22_24.fable_comprehensive_tail_worker_2026_07_22 import (
    balanced_all_vars,
)


def raw_counts(expr) -> tuple[int, int]:
    if isinstance(expr, Var):
        return 1, 0
    if isinstance(expr, Not):
        nodes, ops = raw_counts(expr.a)
        return nodes + 1, ops + 1
    left_nodes, left_ops = raw_counts(expr.a)
    right_nodes, right_ops = raw_counts(expr.b)
    return left_nodes + right_nodes + 1, left_ops + right_ops + 1


def exact_bdd_support(expr, n: int) -> set[str]:
    bdd = BDD()
    names = tuple(f"x{i}" for i in range(n))
    bdd.declare(*names)

    def rec(cur):
        if isinstance(cur, Var):
            return bdd.var(f"x{cur.i}")
        if isinstance(cur, Not):
            return bdd.apply("not", rec(cur.a))
        left = rec(cur.a)
        right = rec(cur.b)
        if isinstance(cur, And):
            return bdd.apply("and", left, right)
        if isinstance(cur, Or):
            return bdd.apply("or", left, right)
        if isinstance(cur, Xor):
            return bdd.apply("xor", left, right)
        if isinstance(cur, Imp):
            return bdd.apply("or", bdd.apply("not", left), right)
        if isinstance(cur, Eqv):
            return bdd.apply("not", bdd.apply("xor", left, right))
        raise TypeError(cur)

    root = rec(expr)
    return set(bdd.support(root))


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return math.nan
    return float(np.corrcoef(np.asarray(xs), np.asarray(ys))[0, 1])


def main() -> None:
    out_dir = REPO / "deliverables_n22_24"
    rows: list[dict[str, object]] = []

    with (out_dir / "CM_FABLE_comprehensive_fullvars.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        full_rows = [row for row in csv.DictReader(handle) if row["status"] == "ok"]
    for source in full_rows:
        n = int(source["n"])
        trial = int(source["trial"])
        expr = balanced_all_vars(
            n, np.random.default_rng(52_000_000 + n * 1000 + trial)
        )
        node = compile_expr_to_cm_ir(expr)
        raw_nodes, raw_ops = raw_counts(expr)
        cm_prog = bb.get_flat_program(node)
        support = exact_bdd_support(expr, n)
        ratio = float(source["cm_words_us"]) / float(source["bs_words_us"])
        rows.append(
            {
                "family": "fable_claimed_all_live",
                "n": n,
                "trial": trial,
                "semantic_live_k": len(support),
                "syntactic_live_k": len(node.vars),
                "actually_all_live": len(support) == n,
                "raw_ast_nodes": raw_nodes,
                "raw_ast_ops": raw_ops,
                "cm_slots": cm_prog.n_slots,
                "cm_ops": len(cm_prog.ops),
                "raw_ops_over_cm_ops": raw_ops / max(1, len(cm_prog.ops)),
                "cm_over_bitset_ratio": ratio,
                "bitset_advantage": 1.0 / ratio,
            }
        )

    with (out_dir / "CM_FABLE_wrapper_stats300_t16_raw.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        sparse_sources = list(csv.DictReader(handle))
    for source in sparse_sources:
        n = int(source["n"])
        trial = int(source["trial"])
        expr = random_expr(
            n,
            np.random.default_rng(9_100_000 + 10_000 * n + trial),
            max_depth=4,
            p_unary=0.25,
        )
        node = compile_expr_to_cm_ir(expr)
        raw_nodes, raw_ops = raw_counts(expr)
        cm_prog = bb.get_flat_program(node)
        ratio = float(source["ratio"])
        rows.append(
            {
                "family": "sparse_depth4",
                "n": n,
                "trial": trial,
                "semantic_live_k": "",
                "syntactic_live_k": len(node.vars),
                "actually_all_live": "",
                "raw_ast_nodes": raw_nodes,
                "raw_ast_ops": raw_ops,
                "cm_slots": cm_prog.n_slots,
                "cm_ops": len(cm_prog.ops),
                "raw_ops_over_cm_ops": raw_ops / max(1, len(cm_prog.ops)),
                "cm_over_bitset_ratio": ratio,
                "bitset_advantage": 1.0 / ratio,
            }
        )

    summaries: list[dict[str, object]] = []
    for family in ("fable_claimed_all_live", "sparse_depth4"):
        selected = [row for row in rows if row["family"] == family]
        compression = [float(row["raw_ops_over_cm_ops"]) for row in selected]
        advantage = [float(row["bitset_advantage"]) for row in selected]
        summaries.append(
            {
                "family": family,
                "rows": len(selected),
                "actually_all_live_count": (
                    sum(bool(row["actually_all_live"]) for row in selected)
                    if family == "fable_claimed_all_live"
                    else ""
                ),
                "semantic_live_k_median": (
                    statistics.median(int(row["semantic_live_k"]) for row in selected)
                    if family == "fable_claimed_all_live"
                    else ""
                ),
                "raw_ops_over_cm_ops_median": statistics.median(compression),
                "cm_over_bitset_ratio_median": statistics.median(
                    float(row["cm_over_bitset_ratio"]) for row in selected
                ),
                "corr_compression_vs_bitset_advantage": pearson(compression, advantage),
                "corr_log_compression_vs_log_advantage": pearson(
                    [math.log(value) for value in compression],
                    [math.log(value) for value in advantage],
                ),
            }
        )

    with (out_dir / "CM_V3AUDIT_F5_family_structure_raw.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (out_dir / "CM_V3AUDIT_F5_family_structure_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    print(summaries)


if __name__ == "__main__":
    main()
