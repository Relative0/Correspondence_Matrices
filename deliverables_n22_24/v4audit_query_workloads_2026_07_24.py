"""Already-built representation query controls on a subset of the V4 corpus.

This is a local autoref control and correctness exercise, not a CUDD timing
claim.  The same serialized formulas and deterministic assignments can be used
unchanged by the blocked Linux/CUDD rerun.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
from dd.autoref import BDD

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from cm_expr_serde import expr_from_json
from cmbench.backends.robdd_dd import bdd_function_value, expr_to_dd_bdd
from cmbench.expr.eval import eval_expr_assignment

BASE = Path(__file__).resolve().parent
CORPUS = BASE / "v4audit_corpus_2026_07_24.jsonl"
RAW = BASE / "CM_v4audit_query_workloads_raw.csv"


def main():
    items = [json.loads(s) for s in CORPUS.read_text(encoding="utf-8").splitlines()]
    items = [x for x in items if x["family"] in {"sparse_depth4", "controlled_live_12"}]
    rows = []
    for item in items:
        expr = expr_from_json(item["expression"])
        n = item["nominal_n"]
        names = [f"x{i}" for i in range(n)]
        bdd = BDD(); bdd.declare(*names)
        root = expr_to_dd_bdd(expr, bdd, {name: name for name in names})
        rng = np.random.default_rng(73_000_000 + n)
        assignments = [
            {name: int(v) for name, v in zip(names, rng.integers(0, 2, size=n))}
            for _ in range(256)
        ]
        expected = [eval_expr_assignment(expr, a) for a in assignments]
        t0 = time.perf_counter()
        actual = [bdd_function_value(bdd, root, a) for a in assignments]
        elapsed = time.perf_counter() - t0
        rows.append({
            "id": item["id"], "nominal_n": n, "family": item["family"],
            "live_k": item["semantic_live_k"], "backend": "dd.autoref",
            "query": "256_assignment_batch", "queries": 256,
            "query_total_us": elapsed * 1e6, "query_per_item_us": elapsed * 1e6 / 256,
            "mismatches": sum(a != b for a, b in zip(actual, expected)),
            "seed": 73_000_000 + n,
        })
        fixed = {name: bool(assignments[0][name]) for name in names[: min(4, n)]}
        t1 = time.perf_counter()
        restricted = bdd.let(fixed, root)
        restrict_us = (time.perf_counter() - t1) * 1e6
        rows.append({
            "id": item["id"], "nominal_n": n, "family": item["family"],
            "live_k": item["semantic_live_k"], "backend": "dd.autoref",
            "query": "cofactor_4_fixed", "queries": 1,
            "query_total_us": restrict_us, "query_per_item_us": restrict_us,
            "mismatches": 0, "seed": 73_000_000 + n,
        })
        t2 = time.perf_counter()
        equiv = bdd.apply("xor", root, root) == bdd.false
        equiv_us = (time.perf_counter() - t2) * 1e6
        rows.append({
            "id": item["id"], "nominal_n": n, "family": item["family"],
            "live_k": item["semantic_live_k"], "backend": "dd.autoref",
            "query": "self_xor_false", "queries": 1,
            "query_total_us": equiv_us, "query_per_item_us": equiv_us,
            "mismatches": 0 if equiv else 1, "seed": 73_000_000 + n,
        })
        del restricted
    with RAW.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} query rows; mismatches={sum(r['mismatches'] for r in rows)}")


if __name__ == "__main__":
    main()
