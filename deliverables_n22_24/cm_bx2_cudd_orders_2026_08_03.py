"""BX2 on-pod measurement: CUDD order sensitivity (best-of-10 + dynamic reordering).

Optional-gap extension of B5 (which used fixed natural order only), closing
Audit V4's request for "CUDD fixed-order, best-of-k including search totals,
and dynamic-reorder rows" on the same box. Runs inside the pod repo.

Per formula of the frozen corrected-E3 corpus (192, k in {8,12,16}):

- fixed natural order build (baseline, as B5);
- best-of-10 seeded random orders: 10 fresh managers, each declaring the
  variables in a blake2b-seeded permutation; per-order build time and node
  count recorded; selected BDD = lexicographic (node count, build time) —
  the historical backend policy; reported: selected nodes/time, median and
  min build time across orders, and the TOTAL search cost (all 10 builds);
- dynamic reordering: fresh manager with CUDD reordering enabled
  (bdd.configure(reordering=True)), build time and final node count.

Correctness: 256 seeded assignments per variant checked against the CM
packed truth bits (the fixed-order arm already carries B5's exhaustive
full-extraction equality on this corpus; the sampled mode here is stated
and never promoted). Fail closed on dd.cudd.
"""
from __future__ import annotations

import hashlib
import json
import platform
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.setrecursionlimit(200_000)

import numpy as np

import dd.cudd as _cudd  # fail closed

from bitset_backend import _eval_words, get_flat_program
from cm_expr_serde import expr_from_json
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir

CORPUS = ROOT / "deliverables_n22_24" / "CM_gap_e3_corrected_corpus_2026_08_02.jsonl"
CORPUS_SHA = "8a6da87cc8b13f6123cb11adfa77b5d69bcd0a086666abea7df633ef92f6e68a"
OUT = ROOT / "deliverables_n22_24" / "pod_out"
N_ORDERS = 10
EVAL_SAMPLES = 256
SAMPLE_SEED = 20260803


def expr_to_bdd(expr, bdd, var_of):
    memo = {}

    def rec(e):
        r = memo.get(id(e))
        if r is not None:
            return r
        if isinstance(e, Var):
            r = var_of[int(e.i)]
        elif isinstance(e, Not):
            r = bdd.apply("not", rec(e.a))
        else:
            a, b = rec(e.a), rec(e.b)
            op = {And: "and", Or: "or", Xor: "xor", Imp: "=>",
                  Eqv: "<=>"}[type(e)]
            r = bdd.apply(op, a, b)
        memo[id(e)] = r
        return r

    return rec(expr)


def order_perm(formula_id, order_idx, k):
    seed = int.from_bytes(hashlib.blake2b(
        f"bx2|{formula_id}|order={order_idx}".encode(), digest_size=8).digest(),
        "big") >> 1
    perm = list(range(k))
    random.Random(seed).shuffle(perm)
    return perm


def build_with_order(expr, k, declare_indices, reordering=False):
    bdd = _cudd.BDD()
    if reordering:
        bdd.configure(reordering=True)
    bdd.declare(*[f"x{i}" for i in declare_indices])
    var_of = {i: bdd.var(f"x{i}") for i in declare_indices}
    t0 = time.perf_counter()
    u = expr_to_bdd(expr, bdd, var_of)
    build_s = time.perf_counter() - t0
    if type(bdd).__module__ != "dd.cudd":
        raise AssertionError("not dd.cudd — fail closed")
    return bdd, u, build_s


def sampled_check(bdd, u, k, bits_ref, samples):
    for m in samples:
        asn = {f"x{i}": bool((m >> (k - 1 - i)) & 1) for i in range(k)}
        if ((bits_ref >> m) & 1) != (bdd.let(asn, u) == bdd.true):
            return False
    return True


def main():
    data = CORPUS.read_bytes()
    if hashlib.sha256(data).hexdigest() != CORPUS_SHA:
        raise SystemExit("corpus SHA mismatch — refusing to measure")
    records = [json.loads(l) for l in data.decode().splitlines()[1:] if l.strip()]
    assert len(records) == 192
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SAMPLE_SEED)

    rows = []
    t_start = time.perf_counter()
    for rec in records:
        k = rec["stratum_live_k"]
        expr = expr_from_json(rec["expression_v2"])
        support = tuple(f"x{i}" for i in range(k))
        bits_ref = int(_eval_words(
            get_flat_program(compile_expr_to_cm_ir(expr)), support, {}))
        samples = [int(x) for x in rng.integers(0, 1 << k, EVAL_SAMPLES)]

        row = {"id": rec["id"], "stratum_live_k": k,
               "op_family": rec["op_family"], "shape": rec["shape"],
               "structural_hash": rec["structural_hash"],
               "robdd_is_cudd": True, "sampled_checks_all_ok": True}

        # fixed natural order
        bdd, u, s = build_with_order(expr, k, list(range(k)))
        if not sampled_check(bdd, u, k, bits_ref, samples):
            raise AssertionError(f"fixed-order sample mismatch: {rec['id']}")
        row["fixed_build_us"] = s * 1e6
        row["fixed_nodes"] = int(u.dag_size)

        # best-of-10 random orders
        per_order = []
        t_search0 = time.perf_counter()
        for oi in range(N_ORDERS):
            perm = order_perm(rec["id"], oi, k)
            b2, u2, s2 = build_with_order(expr, k, perm)
            if not sampled_check(b2, u2, k, bits_ref, samples):
                raise AssertionError(f"order {oi} sample mismatch: {rec['id']}")
            per_order.append({"order_idx": oi, "build_us": s2 * 1e6,
                              "nodes": int(u2.dag_size)})
        row["order_search_total_us"] = (time.perf_counter() - t_search0) * 1e6
        sel = min(per_order, key=lambda o: (o["nodes"], o["build_us"]))
        row["best10_selected_nodes"] = sel["nodes"]
        row["best10_selected_build_us"] = sel["build_us"]
        row["best10_median_build_us"] = statistics.median(
            o["build_us"] for o in per_order)
        row["best10_min_build_us"] = min(o["build_us"] for o in per_order)
        row["best10_min_nodes"] = min(o["nodes"] for o in per_order)
        row["best10_max_nodes"] = max(o["nodes"] for o in per_order)
        row["per_order"] = per_order

        # dynamic reordering
        b3, u3, s3 = build_with_order(expr, k, list(range(k)), reordering=True)
        if not sampled_check(b3, u3, k, bits_ref, samples):
            raise AssertionError(f"reorder sample mismatch: {rec['id']}")
        row["reorder_build_us"] = s3 * 1e6
        row["reorder_nodes"] = int(u3.dag_size)
        rows.append(row)
        if len(rows) % 24 == 0:
            print(f"  {len(rows)}/192", flush=True)

    def med(key, sel):
        return statistics.median(r[key] for r in sel)

    summary = []
    for k in (8, 12, 16):
        sel = [r for r in rows if r["stratum_live_k"] == k]
        summary.append({
            "live_k": k, "n": len(sel),
            "fixed_build_us_median": med("fixed_build_us", sel),
            "fixed_nodes_median": med("fixed_nodes", sel),
            "best10_selected_build_us_median": med("best10_selected_build_us", sel),
            "best10_selected_nodes_median": med("best10_selected_nodes", sel),
            "best10_median_build_us_median": med("best10_median_build_us", sel),
            "order_search_total_us_median": med("order_search_total_us", sel),
            "reorder_build_us_median": med("reorder_build_us", sel),
            "reorder_nodes_median": med("reorder_nodes", sel),
            "node_ratio_best10_vs_fixed_median": statistics.median(
                r["best10_selected_nodes"] / r["fixed_nodes"] for r in sel),
            "node_ratio_reorder_vs_fixed_median": statistics.median(
                r["reorder_nodes"] / r["fixed_nodes"] for r in sel),
        })
    results = {
        "_meta": {
            "driver": Path(__file__).name, "corpus_sha256": CORPUS_SHA,
            "python": sys.version, "numpy": np.__version__,
            "platform": platform.platform(), "dd_cudd": True,
            "n_orders": N_ORDERS, "eval_samples": EVAL_SAMPLES,
            "sample_seed": SAMPLE_SEED,
            "wall_time_s": time.perf_counter() - t_start,
            "selection_rule": "lexicographic (node count, build time) — the "
                              "historical backend policy",
            "correctness_mode": "256 seeded assignments per variant vs CM "
                                "packed bits (fixed-order arm has exhaustive "
                                "equality from B5 on this corpus)",
        },
        "rows": rows,
        "summary": summary,
    }
    (OUT / "cm_bx2_cudd_orders_results_2026_08_03.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8")
    import csv
    with (OUT / "CM_bx2_cudd_orders_summary_2026_08_03.csv").open(
            "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader(); w.writerows(summary)
    print(f"done: 192 rows, wall {time.perf_counter() - t_start:.1f}s")


if __name__ == "__main__":
    main()
