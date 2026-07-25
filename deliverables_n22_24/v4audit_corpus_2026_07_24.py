"""Build the immutable Audit V4 expression corpus.

The corpus deliberately separates nominal n from exact semantic support.  It
contains the historical shallow/sparse generator, controlled XOR support bands,
and an actual-all-live XOR chain used only for sampled/symbolic work above the
16-variable explicit-output guard.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from dd.autoref import BDD

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from cm_expr_serde import expr_to_json
from cm_exprlib import Var, Xor, random_expr
from cm_ir import compile_expr_to_cm_ir
from cmbench.backends.robdd_dd import expr_to_dd_bdd

OUT = Path(__file__).with_name("v4audit_corpus_2026_07_24.jsonl")
SIZES = (20, 22, 24, 26, 28, 30, 32)


def xor_chain(k: int):
    expr = Var(0)
    for i in range(1, k):
        expr = Xor(expr, Var(i))
    return expr


def counts(expr):
    nodes = leaves = ops = 0
    op_counts: dict[str, int] = {}
    stack = [expr]
    while stack:
        cur = stack.pop()
        nodes += 1
        name = type(cur).__name__.lower()
        if name == "var":
            leaves += 1
        else:
            ops += 1
            op_counts[name] = op_counts.get(name, 0) + 1
            stack.append(cur.a)
            if hasattr(cur, "b"):
                stack.append(cur.b)
    return nodes, leaves, ops, op_counts


def exact_support(expr, n: int):
    bdd = BDD()
    names = [f"x{i}" for i in range(n)]
    bdd.declare(*names)
    root = expr_to_dd_bdd(expr, bdd, {name: name for name in names})
    return sorted(bdd.support(root), key=lambda s: int(s[1:]))


def emit(expr, n: int, family: str, seed: int, index: int):
    payload = expr_to_json(expr)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    support = exact_support(expr, n)
    node = compile_expr_to_cm_ir(expr)
    nodes, leaves, ops, op_counts = counts(expr)
    return {
        "corpus_version": 1,
        "id": f"{family}-n{n}-i{index}-{digest[:12]}",
        "sha256": digest,
        "nominal_n": n,
        "seed": seed,
        "family": family,
        "generator": (
            "cm_exprlib.random_expr(max_depth=4,p_unary=0.25)"
            if family == "sparse_depth4"
            else "left-associated XOR chain"
        ),
        "expression": payload,
        "semantic_support": support,
        "semantic_live_k": len(support),
        "syntactic_support": sorted(node.vars, key=lambda s: int(s[1:])),
        "syntactic_live_k": len(node.vars),
        "ast_nodes": nodes,
        "ast_leaves": leaves,
        "ast_ops": ops,
        "operator_counts": op_counts,
        "explicit_packed_policy": "run" if len(support) <= 16 else "skip_guard_gt16",
    }


def main():
    rows = []
    for n in SIZES:
        for trial in range(3):
            seed = 94_000_000 + 10_000 * n + trial
            expr = random_expr(n, np.random.default_rng(seed), max_depth=4, p_unary=0.25)
            rows.append(emit(expr, n, "sparse_depth4", seed, trial))
        for i, k in enumerate((8, 12, 16)):
            rows.append(emit(xor_chain(k), n, f"controlled_live_{k}", 0, i))
        rows.append(emit(xor_chain(n), n, "actual_all_live_xor", 0, 0))
    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"wrote {len(rows)} formulas to {OUT.name}")


if __name__ == "__main__":
    main()
