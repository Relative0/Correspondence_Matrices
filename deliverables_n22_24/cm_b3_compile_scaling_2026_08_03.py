"""B3 — compile/DAG scaling benchmark (2026-08-03 refresh campaign).

Prep-time scaling of the repaired CM pipeline vs structural nodes, depth, and
unfolding factor, on deterministic constructed families (fixed literal seeds,
no timing knowledge in construction):

- shared_ladder(depth)   — the pathological shared-chain class (historical
  pre-repair 403 ms -> 3.0 ms probe headline); unfolded grows exponentially
  while structural stays linear;
- random unshared trees  — the 152 us tree-compile class;
- cyclic n-ary chains    — xor/and chains over 16 variables (n-ary merging);
- mixed shared DAGs      — random DAG pools (seeded);
- multiplier bit cones   — 8x8 sequential multiplier middle output bit.

All constructions use at most 16 variables so the complete packed
truth-function equality gate (cm vs cse vs cse_flat, words kernels) runs
before every timing measurement. The raw no-CSE ablation arm is compiled only
under a 60,000-unfolded cap (skips recorded). Outputs refuse-overwrite.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.setrecursionlimit(200_000)

import numpy as np

from bitset_backend import (
    _eval_words,
    compile_expr_cse,
    compile_expr_flat,
    compile_flat,
    get_flat_program,
    program_metrics,
)
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir, expr_structural_hash

_spec = importlib.util.spec_from_file_location(
    "e3c_frozen", ROOT / "deliverables_n22_24" / "cm_gap_e3_corrected_2026_08_02.py")
e3c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e3c)

OPS = {"and": And, "or": Or, "xor": Xor, "imp": Imp, "eqv": Eqv}
MAX_UNFOLDED_RAW = 60_000


def shared_ladder(depth):
    cur = Xor(Var(0), Var(1))
    for level in range(depth):
        a = Var(2 + (2 * level) % 14)
        b = Var(2 + (2 * level + 1) % 14)
        cur = Or(And(cur, a), And(cur, b))
    return cur


def cyc_chain(op_name, length):
    op = OPS[op_name]
    cur = Var(0)
    for i in range(1, length):
        cur = op(cur, Var(i % 16))
    return cur


def random_tree(rng, n_vars, depth):
    if depth == 0 or (depth < 3 and rng.random() < 0.3):
        return Var(rng.randrange(n_vars))
    if rng.random() < 0.15:
        return Not(random_tree(rng, n_vars, depth - 1))
    op = OPS[rng.choice(sorted(OPS))]
    return op(random_tree(rng, n_vars, depth - 1), random_tree(rng, n_vars, depth - 1))


def mixed_shared_dag(n_vars, steps, seed):
    rng = random.Random(seed)
    pool = [Var(i) for i in range(n_vars)]
    for _ in range(steps):
        name = rng.choice(["and", "or", "xor", "imp", "eqv", "not"])
        if name == "not":
            pool.append(Not(rng.choice(pool)))
        else:
            pool.append(OPS[name](rng.choice(pool), rng.choice(pool)))
    root = pool[-1]
    for e in pool[-6:-1]:
        root = Xor(root, e)
    return root


def add_words(a, b):
    width = max(len(a), len(b))
    out, carry = [], None
    for i in range(width):
        ai = a[i] if i < len(a) else None
        bi = b[i] if i < len(b) else None
        terms = [x for x in (ai, bi, carry) if x is not None]
        if not terms:
            out.append(None); carry = None
        elif len(terms) == 1:
            out.append(terms[0]); carry = None
        elif len(terms) == 2:
            out.append(Xor(terms[0], terms[1])); carry = And(terms[0], terms[1])
        else:
            ab = Xor(ai, bi)
            out.append(Xor(ab, carry))
            carry = Or(And(ai, bi), And(ab, carry))
    if carry is not None:
        out.append(carry)
    return out


def multiplier_bit(nb, bit):
    rows = []
    for j in range(nb):
        rows.append([None] * j + [And(Var(i), Var(nb + j)) for i in range(nb)])
    acc = rows[0]
    for row in rows[1:]:
        acc = add_words(acc, row)
    return acc[bit]


def cases():
    for depth in (4, 6, 8, 10, 12, 16, 20):
        yield f"shared_ladder_d{depth}", "shared_ladder", shared_ladder(depth)
    for op in ("xor", "and"):
        for length in (16, 32, 64, 128, 256):
            yield f"chain_{op}_L{length}", "nary_chain", cyc_chain(op, length)
    for i, (seed, depth) in enumerate([(11, 6), (12, 7), (13, 8), (14, 9),
                                       (15, 10), (16, 11)]):
        yield f"tree_s{seed}_d{depth}", "unshared_tree", random_tree(
            random.Random(seed), 12, depth)
    for steps in (50, 150, 400, 1000, 2500):
        yield f"mixed_dag_s{steps}", "mixed_shared_dag", mixed_shared_dag(16, steps, 20260803)
    for bit in (7, 11, 14):
        yield f"mult8_seq_bit{bit}", "multiplier_bit", multiplier_bit(8, bit)


def timed(fn, repeats=1, blocks=3):
    best = float("inf")
    for _ in range(blocks):
        t0 = time.perf_counter()
        for _ in range(repeats):
            fn()
        best = min(best, (time.perf_counter() - t0) / repeats)
    return best


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    targets = {n: out / n for n in ("cm_b3_scaling_results_2026_08_03.json",
                                    "CM_b3_scaling_summary_2026_08_03.csv")}
    existing = [str(p) for p in targets.values() if p.exists()]
    if existing:
        raise SystemExit("refusing to overwrite:\n  " + "\n  ".join(existing))
    out.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    rows = []
    for cid, family, expr in cases():
        struct = e3c.analyze_structure(expr)
        support = tuple(f"x{i}" for i in sorted(
            {int(v[1:]) for v in _support_names(expr)}))
        k = len(support)
        row = {"id": cid, "case_family": family, "live_vars_syntactic": k,
               "structural_hash": expr_structural_hash(expr),
               **{f: struct[f] for f in (
                   "identity_dag_nodes", "structural_dag_nodes",
                   "unfolded_occurrences", "sharing_factor", "max_depth")}}

        # packed-equality gate before timing (support <= 16 by construction)
        progs = {"cm": get_flat_program(compile_expr_to_cm_ir(expr)),
                 "cse": compile_expr_cse(expr),
                 "cse_flat": compile_expr_cse(expr, flatten=True)}
        vals = {a: _eval_words(p, support, {}) for a, p in progs.items()}
        if len(set(vals.values())) != 1:
            raise AssertionError(f"packed mismatch: {cid}")
        row["packed_equal_all_arms"] = True
        for a, p in progs.items():
            row[f"{a}_flat_instructions"] = program_metrics(p)["flat_instructions"]
            row[f"{a}_executed_word_ops"] = program_metrics(p)["executed_word_ops"]

        node = compile_expr_to_cm_ir(expr)
        row["cm_prep_us"] = timed(lambda: compile_expr_to_cm_ir(expr)) * 1e6
        row["cm_lower_us"] = timed(lambda: compile_flat(node)) * 1e6
        row["cse_prep_us"] = timed(lambda: compile_expr_cse(expr)) * 1e6
        row["cse_flat_prep_us"] = timed(
            lambda: compile_expr_cse(expr, flatten=True)) * 1e6
        row["prep_ratio_cm_vs_cse"] = row["cm_prep_us"] / row["cse_prep_us"]
        if struct["unfolded_occurrences"] <= MAX_UNFOLDED_RAW:
            row["raw_prep_us"] = timed(lambda: compile_expr_flat(expr), blocks=1) * 1e6
            raw_prog = compile_expr_flat(expr)
            if _eval_words(raw_prog, support, {}) != vals["cm"]:
                raise AssertionError(f"raw packed mismatch: {cid}")
            row["raw_arm"] = "ok"
        else:
            row["raw_arm"] = "skipped_unfolded_cap"
        rows.append(row)
        print(f"  {cid}: struct={row['structural_dag_nodes']} "
              f"unfolded={row['unfolded_occurrences']} "
              f"cm_prep={row['cm_prep_us']:.1f}us "
              f"ratio_vs_cse={row['prep_ratio_cm_vs_cse']:.2f}", flush=True)

    try:
        git_rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.strip()
    except Exception:
        git_rev = "unknown"
    results = {
        "_meta": {
            "driver": Path(__file__).name,
            "python": sys.version, "numpy": np.__version__,
            "cpu": platform.processor(), "platform": platform.platform(),
            "git_revision": git_rev,
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "wall_time_s": time.perf_counter() - t0,
            "timing": "best-of-3 blocks per measurement, perf_counter",
            "note": "all cases <= 16 syntactic vars so packed equality gates "
                    "every timing; raw arm capped at 60k unfolded",
        },
        "cases": rows,
    }
    targets["cm_b3_scaling_results_2026_08_03.json"].write_text(
        json.dumps(results, indent=2), encoding="utf-8")
    fields = [f for f in rows[0] if not f.endswith("_hash")]
    with targets["CM_b3_scaling_summary_2026_08_03.csv"].open(
            "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    print(f"wall {time.perf_counter() - t0:.1f}s; wrote outputs to {out}")
    return 0


def _support_names(expr):
    seen, out, stack = set(), set(), [expr]
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if isinstance(cur, Var):
            out.add(f"x{int(cur.i)}")
        elif isinstance(cur, Not):
            stack.append(cur.a)
        else:
            stack.extend((cur.a, cur.b))
    return out


if __name__ == "__main__":
    sys.exit(main())
