"""Independent review of Audit V3 F5: exact semantic support of the 29 committed
"all-live" seeds, computed with methods independent of V3's script.

Two independent support computations per formula:
  1. Packed-cofactor test (n<=26): variable xi is live iff the packed truth
     tables with xi fixed to 0 and to 1 differ. Uses the words evaluator only
     as a truth-table engine (itself verified bit-exact against a scalar
     oracle elsewhere); no BDD library involved.
  2. Own BDD recursion via dd.autoref using the '=>' and '<=>' operators
     directly (V3 composed not/xor instead), for all 29 rows.

Where both run, they must agree. Dead variables at n>=28 are additionally
spot-checked with 512 random scalar-evaluation pairs.

Also recomputes raw AST node/op counts, CM flat-program op counts, and the
compression-vs-advantage correlations from the committed campaign CSV, plus
per-n and n-controlled (partial) correlations that V3 did not report.
"""
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
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir

OUT = REPO / "deliverables_n22_24"


# --- generator copied verbatim from the committed campaign workers (both the
# --- main and tail workers define it identically; seeds 52_000_000 + n*1000 + trial)
def _balanced_all_vars_once(n, rng):
    mix_ops = (And, Or, Imp, Eqv)
    leaves = [Var(i) for i in range(n)]
    rng.shuffle(leaves)
    nodes = leaves[:]
    while len(nodes) > 1:
        nxt = []
        for i in range(0, len(nodes) - 1, 2):
            a, b = nodes[i], nodes[i + 1]
            if rng.random() < 0.25:
                a = Not(a)
            joined = Xor(a, b)
            if rng.random() < 0.5:
                other = mix_ops[int(rng.integers(0, len(mix_ops)))]
                joined = Xor(joined, other(nodes[i], Not(nodes[i + 1])))
            nxt.append(joined)
        if len(nodes) % 2:
            nxt.append(nodes[-1])
        nodes = nxt
    return nodes[0]


def balanced_all_vars(n, rng):
    for _ in range(40):
        expr = _balanced_all_vars_once(n, rng)
        if len(compile_expr_to_cm_ir(expr).vars) == n:
            return expr
    raise RuntimeError(f"no all-live expr at n={n}")


def my_ast_counts(expr):
    """Iterative counter (V3 used recursion): (nodes, ops)."""
    nodes = 0
    ops = 0
    stack = [expr]
    while stack:
        cur = stack.pop()
        nodes += 1
        if isinstance(cur, Var):
            continue
        ops += 1
        if isinstance(cur, Not):
            stack.append(cur.a)
        else:
            stack.append(cur.a)
            stack.append(cur.b)
    return nodes, ops


def support_bdd(expr, n):
    bdd = BDD()
    bdd.declare(*[f"x{i}" for i in range(n)])

    def rec(cur):
        if isinstance(cur, Var):
            return bdd.var(f"x{cur.i}")
        if isinstance(cur, Not):
            return ~rec(cur.a)
        left = rec(cur.a)
        right = rec(cur.b)
        if isinstance(cur, And):
            return left & right
        if isinstance(cur, Or):
            return left | right
        if isinstance(cur, Xor):
            return bdd.apply("xor", left, right)
        if isinstance(cur, Imp):
            return bdd.apply("=>", left, right)
        if isinstance(cur, Eqv):
            return bdd.apply("<=>", left, right)
        raise TypeError(cur)

    root = rec(expr)
    kind = "nonconst"
    if root == bdd.true:
        kind = "const_true"
    elif root == bdd.false:
        kind = "const_false"
    return set(bdd.support(root)), kind


def support_cofactor(expr, n):
    """Exact support via packed cofactor equality; no BDD involved."""
    names = [f"x{i}" for i in range(n)]
    live = set()
    for i, name in enumerate(names):
        scope = tuple(nm for nm in names if nm != name)
        b0 = bb.eval_expr_words_bitset(expr, scope, fixed={name: 0})
        b1 = bb.eval_expr_words_bitset(expr, scope, fixed={name: 1})
        if b0 != b1:
            live.add(name)
    return live


def scalar_eval(expr, assignment):
    t = type(expr)
    if t is Var:
        return assignment[expr.i]
    if t is Not:
        return 1 - scalar_eval(expr.a, assignment)
    a = scalar_eval(expr.a, assignment)
    b = scalar_eval(expr.b, assignment)
    if t is And:
        return a & b
    if t is Or:
        return a | b
    if t is Xor:
        return a ^ b
    if t is Imp:
        return (1 - a) | b
    return 1 - (a ^ b)


def sampled_dead_check(expr, n, dead_names, seed, samples=512):
    """Consistency check only: flipping a 'dead' var never changes the output."""
    rng = np.random.default_rng(seed)
    dead_idx = [int(nm[1:]) for nm in dead_names]
    for _ in range(samples):
        assignment = {i: int(rng.integers(0, 2)) for i in range(n)}
        base = scalar_eval(expr, assignment)
        for di in dead_idx:
            flipped = dict(assignment)
            flipped[di] ^= 1
            if scalar_eval(expr, flipped) != base:
                return False
    return True


def pearson(xs, ys):
    if len(xs) < 2:
        return math.nan
    return float(np.corrcoef(np.asarray(xs), np.asarray(ys))[0, 1])


def partial_corr(xs, ys, zs):
    """Pearson of residuals after regressing out z from both x and y."""
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    z = np.asarray(zs, dtype=float)
    zm = np.column_stack([np.ones_like(z), z])
    rx = x - zm @ np.linalg.lstsq(zm, x, rcond=None)[0]
    ry = y - zm @ np.linalg.lstsq(zm, y, rcond=None)[0]
    return pearson(rx.tolist(), ry.tolist())


def main():
    with (OUT / "CM_FABLE_comprehensive_fullvars.csv").open(newline="", encoding="utf-8") as fh:
        committed = [r for r in csv.DictReader(fh) if r["status"] == "ok"]
    with (OUT / "CM_V3AUDIT_F5_family_structure_raw.csv").open(newline="", encoding="utf-8") as fh:
        v3rows = {
            (int(r["n"]), int(r["trial"])): r
            for r in csv.DictReader(fh)
            if r["family"] == "fable_claimed_all_live"
        }

    assert len(committed) == 29, f"expected 29 ok rows, got {len(committed)}"

    out_rows = []
    disagreements = []
    for src in committed:
        n = int(src["n"])
        trial = int(src["trial"])
        rng = np.random.default_rng(52_000_000 + n * 1000 + trial)
        expr = balanced_all_vars(n, rng)
        node = compile_expr_to_cm_ir(expr)

        bdd_sup, kind = support_bdd(expr, n)
        cof_sup = None
        if n <= 26:
            cof_sup = support_cofactor(expr, n)
            if cof_sup != bdd_sup:
                disagreements.append((n, trial, "cofactor_vs_bdd"))
        dead = sorted(set(f"x{i}" for i in range(n)) - bdd_sup)
        dead_ok = True
        if n >= 28 and dead:
            dead_ok = sampled_dead_check(expr, n, dead, seed=421_000 + n * 10 + trial)

        nodes_cnt, ops_cnt = my_ast_counts(expr)
        prog = bb.get_flat_program(node)
        v3 = v3rows.get((n, trial))
        my_live = len(bdd_sup)
        row = {
            "n": n,
            "trial": trial,
            "my_semantic_live_k": my_live,
            "v3_semantic_live_k": int(v3["semantic_live_k"]) if v3 else None,
            "methods_agree": (cof_sup is None) or (cof_sup == bdd_sup),
            "const_kind": kind,
            "dead_sample_ok": dead_ok,
            "syntactic_live_k": len(node.vars),
            "my_raw_ast_nodes": nodes_cnt,
            "my_raw_ast_ops": ops_cnt,
            "v3_raw_ast_ops": int(v3["raw_ast_ops"]) if v3 else None,
            "my_cm_ops": len(prog.ops),
            "v3_cm_ops": int(v3["cm_ops"]) if v3 else None,
            "match_v3_live": (int(v3["semantic_live_k"]) == my_live) if v3 else None,
            "match_v3_counts": (
                int(v3["raw_ast_ops"]) == ops_cnt and int(v3["cm_ops"]) == len(prog.ops)
            )
            if v3
            else None,
        }
        out_rows.append(row)
        bb.clear_words_env_cache()
        bb.clear_bitset_env_cache()
        print(
            f"n={n} t={trial}: live={my_live} ({kind}) v3={row['v3_semantic_live_k']} "
            f"agree={row['methods_agree']} dead_ok={dead_ok}",
            flush=True,
        )

    lives = sorted(r["my_semantic_live_k"] for r in out_rows)
    all_live_count = sum(1 for r in out_rows if r["my_semantic_live_k"] == r["n"])
    const_count = sum(1 for r in out_rows if r["const_kind"] != "nonconst")
    n32 = [r for r in out_rows if r["n"] == 32]

    # --- structural correlations from the committed timing CSV + my counts
    comp = []
    adv = []
    ambient = []
    for src in committed:
        n = int(src["n"])
        trial = int(src["trial"])
        mine = next(r for r in out_rows if r["n"] == n and r["trial"] == trial)
        compression = mine["my_raw_ast_ops"] / max(1, mine["my_cm_ops"])
        ratio = float(src["cm_words_us"]) / float(src["bs_words_us"])
        comp.append(compression)
        adv.append(1.0 / ratio)
        ambient.append(n)

    summary = {
        "rows": len(out_rows),
        "all_live_count": all_live_count,
        "const_count": const_count,
        "median_semantic_live_k": statistics.median(lives),
        "n32_semantic_live_k": n32[0]["my_semantic_live_k"] if n32 else None,
        "all_methods_agree": not disagreements,
        "all_match_v3_live": all(r["match_v3_live"] for r in out_rows),
        "all_match_v3_counts": all(r["match_v3_counts"] for r in out_rows),
        "corr_compression_vs_advantage": pearson(comp, adv),
        "corr_log_log": pearson([math.log(c) for c in comp], [math.log(a) for a in adv]),
        "partial_corr_controlling_n": partial_corr(comp, adv, ambient),
        "partial_corr_loglog_controlling_n": partial_corr(
            [math.log(c) for c in comp], [math.log(a) for a in adv], ambient
        ),
        "corr_median_cm_over_bitset": statistics.median(1.0 / a for a in adv),
    }

    with (OUT / "CM_independent_review_f5_support.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    with (OUT / "CM_independent_review_f5_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary))
        w.writeheader()
        w.writerow(summary)
    print(summary)
    if disagreements:
        print("DISAGREEMENTS:", disagreements)


if __name__ == "__main__":
    main()
