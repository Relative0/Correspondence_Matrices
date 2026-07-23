"""Audit V3 corrected sharing-rich, semantically all-live campaign through n=26.

The Fable generator's EQV mixer can cancel an entire subtree. This corrected
variant uses only AND/OR/IMP mixers; by induction over disjoint variable
subtrees, every outer operation is essential in both inputs. Exact BDD support
is checked independently before any timing.
"""
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
from cm_exprlib import And, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir
from deliverables_n22_24.v3audit_f5_family_structure_2026_07_23 import (
    exact_bdd_support,
    raw_counts,
)

TRIALS = {16: 10, 18: 10, 20: 8, 22: 6, 24: 5, 26: 3}


def corrected_all_live(n: int, rng: np.random.Generator):
    mix_ops = (And, Or, Imp)
    leaves = [Var(i) for i in range(n)]
    rng.shuffle(leaves)
    nodes = leaves
    while len(nodes) > 1:
        next_nodes = []
        for index in range(0, len(nodes) - 1, 2):
            left, right = nodes[index], nodes[index + 1]
            if rng.random() < 0.25:
                left = Not(left)
            joined = Xor(left, right)
            if rng.random() < 0.5:
                other = mix_ops[int(rng.integers(0, len(mix_ops)))]
                joined = Xor(joined, other(nodes[index], Not(nodes[index + 1])))
            next_nodes.append(joined)
        if len(nodes) & 1:
            next_nodes.append(nodes[-1])
        nodes = next_nodes
    return nodes[0]


def timed(fn, reps: int) -> float:
    start = perf_counter()
    for _ in range(reps):
        fn()
    return (perf_counter() - start) / reps * 1e6


def main() -> None:
    raw: list[dict[str, object]] = []
    for n, trials in TRIALS.items():
        vars_all = tuple(f"x{i}" for i in range(n))
        for trial in range(trials):
            expr = corrected_all_live(
                n, np.random.default_rng(73_000_000 + n * 1000 + trial)
            )
            support = exact_bdd_support(expr, n)
            if support != set(vars_all):
                raise AssertionError(
                    f"corrected generator lost variables at n={n}, trial={trial}: "
                    f"{sorted(set(vars_all) - support)}"
                )
            node = compile_expr_to_cm_ir(expr)
            if len(node.vars) != n:
                raise AssertionError("CM syntactic support unexpectedly shrank")
            cm_bits = bb.eval_cm_node_words(node, vars_all)
            raw_bits = bb.eval_expr_words_bitset(expr, vars_all)
            if cm_bits != raw_bits:
                raise AssertionError(f"packed mismatch n={n} trial={trial}")

            def run_cm():
                return bb.eval_cm_node_words(node, vars_all)

            def run_raw():
                return bb.eval_expr_words_bitset(expr, vars_all)

            run_cm()
            run_raw()
            reps = 20 if n <= 18 else (7 if n <= 22 else 1)
            rounds = 7 if n <= 22 else 5
            samples = {"cm": [], "raw": []}
            for round_index in range(rounds):
                order = ("cm", "raw") if (trial + round_index) & 1 else ("raw", "cm")
                for name in order:
                    samples[name].append(timed(run_cm if name == "cm" else run_raw, reps))
            cm_us = statistics.median(samples["cm"])
            raw_us = statistics.median(samples["raw"])
            raw_nodes, raw_ops = raw_counts(expr)
            cm_prog = bb.get_flat_program(node)
            raw.append(
                {
                    "n": n,
                    "trial": trial,
                    "semantic_live_k": len(support),
                    "all_live": True,
                    "raw_ast_nodes": raw_nodes,
                    "raw_ast_ops": raw_ops,
                    "cm_slots": cm_prog.n_slots,
                    "cm_ops": len(cm_prog.ops),
                    "raw_ops_over_cm_ops": raw_ops / max(1, len(cm_prog.ops)),
                    "rounds": rounds,
                    "reps": reps,
                    "cm_words_us": cm_us,
                    "bitset_words_us": raw_us,
                    "cm_over_bitset": cm_us / raw_us,
                    "all_agree": True,
                }
            )
            del expr, node, cm_bits, raw_bits
            bb.clear_words_env_cache()
            bb.clear_bitset_env_cache()
            gc.collect()
        print(f"n={n}: {trials} corrected all-live formulas", flush=True)

    summary: list[dict[str, object]] = []
    for n in TRIALS:
        selected = [row for row in raw if row["n"] == n]
        summary.append(
            {
                "n": n,
                "trials": len(selected),
                "all_live_all": all(int(row["semantic_live_k"]) == n for row in selected),
                "all_agree": all(bool(row["all_agree"]) for row in selected),
                "raw_ops_over_cm_ops_median": statistics.median(
                    float(row["raw_ops_over_cm_ops"]) for row in selected
                ),
                "cm_words_us_median": statistics.median(
                    float(row["cm_words_us"]) for row in selected
                ),
                "bitset_words_us_median": statistics.median(
                    float(row["bitset_words_us"]) for row in selected
                ),
                "cm_over_bitset_median": statistics.median(
                    float(row["cm_over_bitset"]) for row in selected
                ),
            }
        )

    out = REPO / "deliverables_n22_24"
    with (out / "CM_V3AUDIT_F5_corrected_all_live_raw.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(raw[0]))
        writer.writeheader()
        writer.writerows(raw)
    with (out / "CM_V3AUDIT_F5_corrected_all_live_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print(summary)


if __name__ == "__main__":
    main()
