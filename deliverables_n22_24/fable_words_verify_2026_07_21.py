"""Fable: verify + benchmark the landed numpy-words backend.

Bit-identity: words == bigint flat == oracle across random fuzz (exhaustive by
construction: packed-output equality covers all 2^k rows), fixed bindings,
repeated calls (scratch buffer recycling), and width switching per program.
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

REPO = Path(r"C:\Users\brian\Documents\CM_Computation")
sys.path.insert(0, str(REPO))

from bitset_backend import (
    bitset_to_bool_array,
    eval_cm_node_bitset,
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_flat_bitset,
    eval_expr_words_bitset,
)
from cm_exprlib import And, Not, Var, Xor, eval_expr_tt, random_expr
from cm_ir import compile_expr_to_cm_ir
from cmbench.expr.generators import random_expr_balanced_all_vars

fails = 0
checks = 0


def check(label, cond):
    global fails, checks
    checks += 1
    if not cond:
        fails += 1
        print("FAIL:", label)


# --- 1. random fuzz incl. oracle, fixed bindings, repeated calls ---
rng = np.random.default_rng(1618)
for trial in range(300):
    n = int(rng.integers(3, 13))  # includes <6 fallback sizes
    expr = random_expr(n, rng, max_depth=int(rng.integers(3, 8)), p_unary=0.3)
    node = compile_expr_to_cm_ir(expr)
    vars_all = tuple(f"x{i}" for i in range(n))
    tt = eval_expr_tt(expr, n).astype(np.uint8, copy=False).reshape(-1)
    exp_full = int.from_bytes(np.packbits(tt, bitorder="little").tobytes(), "little")
    check(f"f{trial}/cm", eval_cm_node_words(node, vars_all) == exp_full)
    check(f"f{trial}/raw", eval_expr_words_bitset(expr, vars_all) == exp_full)
    # repeated call: scratch reuse must not corrupt
    check(f"f{trial}/cm_repeat", eval_cm_node_words(node, vars_all) == exp_full)
    # fixed subset
    k_fix = int(rng.integers(0, n))
    fixed_names = list(rng.choice(n, size=k_fix, replace=False))
    fixed = {f"x{i}": int(rng.integers(0, 2)) for i in fixed_names}
    live = tuple(v for v in vars_all if v not in fixed)
    ref = eval_cm_node_bitset(node, live, fixed=fixed)
    check(f"f{trial}/cm_fixed", eval_cm_node_words(node, live, fixed=fixed) == ref)
    check(f"f{trial}/raw_fixed", eval_expr_words_bitset(expr, live, fixed=fixed) == ref)
    # width switch on the same program: full width again after reduced
    check(f"f{trial}/cm_wswitch", eval_cm_node_words(node, vars_all) == exp_full)

# --- 2. structured edges ---
for n in (6, 8):
    vars_all = tuple(f"x{i}" for i in range(n))
    for label, e in (
        ("single_var", Var(n - 1)),
        ("const_false", And(Var(0), Not(Var(0)))),
        ("xorpair", Xor(Var(0), Var(n - 1))),
    ):
        node = compile_expr_to_cm_ir(e)
        ref = eval_cm_node_bitset(node, vars_all)
        check(f"{label}_n{n}/cm", eval_cm_node_words(node, vars_all) == ref)
        check(f"{label}_n{n}/raw", eval_expr_words_bitset(e, vars_all) == ref)

# --- 3. big balanced exprs 16..24: words == bigint flat (packed equality = exhaustive) ---
for n in (16, 18, 20, 22, 24):
    vars_all = tuple(f"x{i}" for i in range(n))
    expr = random_expr_balanced_all_vars(n, np.random.default_rng(999 + n), max_depth=8)
    node = compile_expr_to_cm_ir(expr)
    ref = eval_cm_node_flat(node, vars_all)
    check(f"big{n}/cm", eval_cm_node_words(node, vars_all) == ref)
    check(f"big{n}/raw", eval_expr_words_bitset(expr, vars_all) == ref)
    check(f"big{n}/cm_repeat", eval_cm_node_words(node, vars_all) == ref)

print(f"verify: {checks} checks, {fails} fails")
if fails:
    sys.exit(1)


# --- 4. timing: crossover + headline (paired, interleaved) ---
def timed(fn, repeats):
    t0 = perf_counter()
    for _ in range(repeats):
        fn()
    return (perf_counter() - t0) / repeats


print(f"{'n':>3} {'bigintCM us':>12} {'wordsCM us':>11} {'CMx':>6} "
      f"{'bigintRAW us':>13} {'wordsRAW us':>12} {'RAWx':>6} {'scratch_bufs':>12}")
for n in (12, 14, 16, 18, 20, 22, 24):
    vars_all = tuple(f"x{i}" for i in range(n))
    t = {"bc": [], "wc": [], "br": [], "wr": []}
    n_bufs = []
    for trial in range(3):
        expr = random_expr_balanced_all_vars(
            n, np.random.default_rng(20260721 + n * 100 + trial), max_depth=8)
        node = compile_expr_to_cm_ir(expr)
        ref = eval_cm_node_flat(node, vars_all)
        assert eval_cm_node_words(node, vars_all) == ref
        assert eval_expr_words_bitset(expr, vars_all) == ref
        from bitset_backend import get_flat_program
        n_bufs.append(get_flat_program(node).word_plan[1])
        reps = 20 if n <= 16 else (5 if n <= 20 else 2)
        for _ in range(5):
            t["bc"].append(timed(lambda: eval_cm_node_flat(node, vars_all), reps) * 1e6)
            t["wc"].append(timed(lambda: eval_cm_node_words(node, vars_all), reps) * 1e6)
            t["br"].append(timed(lambda: eval_expr_flat_bitset(expr, vars_all), reps) * 1e6)
            t["wr"].append(timed(lambda: eval_expr_words_bitset(expr, vars_all), reps) * 1e6)
    m = {k: statistics.median(v) for k, v in t.items()}
    print(f"{n:>3} {m['bc']:>12.1f} {m['wc']:>11.1f} {m['bc']/m['wc']:>6.2f} "
          f"{m['br']:>13.1f} {m['wr']:>12.1f} {m['br']/m['wr']:>6.2f} "
          f"{max(n_bufs):>12}")
