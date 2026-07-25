"""Recalculate Independent Review statistics and add a third support oracle."""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
BASE = Path(__file__).resolve().parent

from deliverables_n22_24.independent_review_f5_support_2026_07_23 import (
    balanced_all_vars, support_bdd, support_cofactor,
)
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor

OUT = BASE / "CM_v4audit_independent_claims.csv"


def vector_oracle(expr, n):
    idx = np.arange(1 << n, dtype=np.uint32)
    env = {i: ((idx >> (n - 1 - i)) & 1).astype(bool) for i in range(n)}
    def rec(e):
        if isinstance(e, Var): return env[e.i]
        if isinstance(e, Not): return ~rec(e.a)
        a, b = rec(e.a), rec(e.b)
        if isinstance(e, And): return a & b
        if isinstance(e, Or): return a | b
        if isinstance(e, Xor): return a ^ b
        if isinstance(e, Imp): return (~a) | b
        if isinstance(e, Eqv): return ~(a ^ b)
        raise TypeError(e)
    values = rec(expr)
    support = set()
    for i in range(n):
        stride = 1 << (n - 1 - i)
        shaped = values.reshape(-1, 2, stride)
        if np.any(shaped[:, 0, :] != shaped[:, 1, :]):
            support.add(f"x{i}")
    return support


def bootstrap(values, seed=7, iterations=10_000):
    arr = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    meds = np.median(arr[rng.integers(0, len(arr), size=(iterations, len(arr)))], axis=1)
    return statistics.median(values), float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def main():
    rows = []
    with (BASE / "CM_FABLE_comprehensive_fullvars.csv").open(newline="", encoding="utf-8") as fh:
        committed = [r for r in csv.DictReader(fh) if r["status"] == "ok"]
    disagreements = 0
    third_method_cases = 0
    supports = []
    constants = []
    for src in committed:
        n, trial = int(src["n"]), int(src["trial"])
        expr = balanced_all_vars(n, np.random.default_rng(52_000_000 + n * 1000 + trial))
        bdd_support, kind = support_bdd(expr, n)
        cofactor = support_cofactor(expr, n) if n <= 26 else None
        vector = vector_oracle(expr, n) if n <= 18 else None
        agrees = (cofactor is None or cofactor == bdd_support) and (vector is None or vector == bdd_support)
        disagreements += 0 if agrees else 1
        third_method_cases += vector is not None
        supports.append(len(bdd_support))
        if kind != "nonconst": constants.append((n, trial, kind))
    rows.append({"check": "F5_support_three_methods", "ok": disagreements == 0,
                 "detail": f"29 BDD; 24 cofactor; {third_method_cases} vector; disagreements={disagreements}"})
    rows.append({"check": "F5_summary", "ok": sum(
        1 for src, live in zip(committed, supports) if int(src["n"]) == live) == 4
        and statistics.median(supports) == 16,
        "detail": f"all_live={sum(1 for src,live in zip(committed,supports) if int(src['n'])==live)};"
                  f" median={statistics.median(supports)}; constants={constants}"})

    with (BASE / "CM_V3AUDIT_F3_n24_seeds_raw.csv").open(newline="", encoding="utf-8") as fh:
        f3 = list(csv.DictReader(fh))
    for seed in sorted({int(r["seed_base"]) for r in f3}):
        vals = [float(r["ratio"]) for r in f3 if int(r["seed_base"]) == seed]
        med, lo, hi = bootstrap(vals)
        rows.append({"check": f"F3_bootstrap_{seed}", "ok": True,
                     "detail": f"n={len(vals)} median={med:.4f} ci95=[{lo:.4f},{hi:.4f}]"})

    with (BASE / "CM_FABLE_wrapper_stats300_t16_raw.csv").open(newline="", encoding="utf-8") as fh:
        wrap = [r for r in csv.DictReader(fh) if int(r["n"]) == 24]
    med, lo, hi = bootstrap([float(r["ratio"]) for r in wrap])
    rows.append({"check": "F3_bootstrap_wrapper_n24", "ok": True,
                 "detail": f"n={len(wrap)} median={med:.4f} ci95=[{lo:.4f},{hi:.4f}]"})

    with (BASE / "CM_independent_review_f2_depth6.csv").open(newline="", encoding="utf-8") as fh:
        depth = list(csv.DictReader(fh))
    for label, pred in (("le7", lambda k: k <= 7), ("8to11", lambda k: 8 <= k <= 11),
                        ("12to16", lambda k: 12 <= k <= 16)):
        vals = [float(r["t16_over_t7"]) for r in depth if pred(int(r["live_k"]))]
        rows.append({"check": f"F2_depth6_{label}", "ok": bool(vals),
                     "detail": f"n={len(vals)} median={statistics.median(vals):.4f}"})

    with (BASE / "CM_V3AUDIT_F4_binding_profile_raw.csv").open(newline="", encoding="utf-8") as fh:
        profile = list(csv.DictReader(fh))
    for ambient in sorted({int(r["ambient_n"]) for r in profile}):
        sel = [r for r in profile if int(r["ambient_n"]) == ambient]
        rows.append({"check": f"F4_profile_n{ambient}", "ok": True,
                     "detail": "full/prebound/key_us="
                     f"{statistics.median(float(r['full_raw_us']) for r in sel):.3f}/"
                     f"{statistics.median(float(r['prebound_eval_us']) for r in sel):.3f}/"
                     f"{statistics.median(float(r['key_sort_hash_us']) for r in sel):.3f}"})
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(json.dumps(rows, indent=2))
    raise SystemExit(1 if any(not r["ok"] for r in rows) else 0)


if __name__ == "__main__":
    main()
