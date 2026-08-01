"""Corrected CM-vs-BitSet benchmark driver (2026-08-02 gap repair).

Replaces the boundary-confused historical comparison with one that reports
every stage separately and never presents the admission wrapper
(`materialize_hybrid_no_reinflate`) against a bare kernel as a kernel
comparison. Historical CSVs are not modified.

Arms per formula (exact packed-bigint equality asserted across all arms
before any timing):

  cm_old     legacy CM compile (share_aware_flatten=False, build_memo=False)
  cm_new     repaired CM compile (defaults)
  raw        no-CSE raw flat program           (labeled ablation)
  cse        structural-CSE baseline           (production baseline)
  cse_flat   CSE + sharing-aware flattening    (production baseline variant)

Timing boundaries reported separately per formula:

  parse_us          v2 defs/ref JSON -> Expr
  prep_us           compile/lowering per arm
  kernel_us         steady-state packed evaluation per arm (words kernel,
                    identical call shape for every arm)
  wrapper_us        admission/budget wrapper on top of the CM kernel
                    (cm_new only; live_k <= 16)
  cold_total_us     fresh compile + first evaluation (cm_new, cse)
  repeated_total_us kernel_us * REPEAT (steady-state workload)
  breakeven_evals   evaluations for cm_new's total cost to cross below the
                    cse baseline's total cost (None if it never does)

Operation accounting uses bitset_backend.program_metrics — flat instruction
counts and executed primitive operations are separate columns; instruction
counts are never labeled as executed operations.

Usage (benchmark interpreter):
  .venv/Scripts/python.exe deliverables_n22_24/cm_gap_repair_benchmark_2026_08_02.py
Options: --skip-slow  (drop the two slowest legacy-compile cases)

Outputs:
  cm_gap_repair_results_2026_08_02.json
  CM_gap_repair_before_after_2026_08_02.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.setrecursionlimit(200_000)

import numpy as np

from bitset_backend import (
    _eval_words,
    bitset_env_cache_stats,
    compile_expr_cse,
    compile_expr_flat,
    compile_flat,
    eval_cm_node_words,
    eval_expr_words_bitset,
    eval_expr_words_cse,
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir, expr_structural_hash, materialize_hybrid_no_reinflate

OUT_JSON = ROOT / "deliverables_n22_24" / "cm_gap_repair_results_2026_08_02.json"
OUT_CSV = ROOT / "deliverables_n22_24" / "CM_gap_repair_before_after_2026_08_02.csv"

REPEAT = 100          # steady-state repeat count per timing block
BLOCKS = 3            # min-of-blocks
SCHEDULE = "blocked_warm_cache"  # one formula at a time, warm env caches


def timed(fn, repeats: int = 1, blocks: int = BLOCKS) -> float:
    samples = []
    for _ in range(blocks):
        t0 = time.perf_counter()
        for _ in range(repeats):
            fn()
        samples.append((time.perf_counter() - t0) / repeats)
    return min(samples)


# --------------------------------------------------------------------------
# corpus (formula identity is the inferential unit; live_k <= 16 everywhere)
# --------------------------------------------------------------------------

OPS = {"and": And, "or": Or, "xor": Xor, "imp": Imp, "eqv": Eqv}


def chain(op_name: str, k: int):
    op = OPS[op_name]
    cur = Var(0)
    for i in range(1, k):
        cur = op(cur, Var(i))
    return cur


def random_tree(rng: random.Random, n_vars: int, depth: int):
    if depth == 0 or (depth < 3 and rng.random() < 0.3):
        return Var(rng.randrange(n_vars))
    if rng.random() < 0.15:
        return Not(random_tree(rng, n_vars, depth - 1))
    op = OPS[rng.choice(list(OPS))]
    return op(random_tree(rng, n_vars, depth - 1), random_tree(rng, n_vars, depth - 1))


def shared_ladder(depth: int):
    cur = Xor(Var(0), Var(1))
    for level in range(depth):
        a = Var(2 + (2 * level) % 14)
        b = Var(2 + (2 * level + 1) % 14)
        cur = Or(And(cur, a), And(cur, b))
    return cur


def mixed_shared_dag(n_vars: int, steps: int, seed: int):
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


def multiplier_bit(nb: int, topology: str, bit: int):
    rows = []
    for j in range(nb):
        rows.append([None] * j + [And(Var(i), Var(nb + j)) for i in range(nb)])
    if topology == "sequential":
        acc = rows[0]
        for row in rows[1:]:
            acc = add_words(acc, row)
        return acc[bit]
    while len(rows) > 1:
        nxt = []
        for i in range(0, len(rows), 2):
            nxt.append(add_words(rows[i], rows[i + 1]) if i + 1 < len(rows) else rows[i])
        rows = nxt
    return rows[0][bit]


def expr_support(expr):
    seen, out, stack = set(), set(), [expr]
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if isinstance(cur, Var):
            out.add(int(cur.i))
        elif isinstance(cur, Not):
            stack.append(cur.a)
        else:
            stack.extend((cur.a, cur.b))
    return tuple(f"x{i}" for i in sorted(out))


def operator_mix(expr):
    counts: Counter = Counter()
    seen, stack = set(), [expr]
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if isinstance(cur, Var):
            continue
        counts[type(cur).__name__] += 1
        if isinstance(cur, Not):
            stack.append(cur.a)
        else:
            stack.extend((cur.a, cur.b))
    return dict(counts)


def tree_occurrences(expr):
    memo = {}

    def rec(e):
        c = memo.get(id(e))
        if c is not None:
            return c
        if isinstance(e, Var):
            c = 1
        elif isinstance(e, Not):
            c = 1 + rec(e.a)
        else:
            c = 1 + rec(e.a) + rec(e.b)
        memo[id(e)] = c
        return c

    return rec(expr)


def build_corpus(skip_slow: bool):
    corpus = []
    # low-sharing operator chains, every operator family, k in {8, 12, 16}
    for op_name in ("xor", "and", "or", "imp", "eqv"):
        for k in (8, 12, 16):
            corpus.append((f"chain_{op_name}_k{k}", "chains_low_sharing", chain(op_name, k)))
    # random depth-4 trees: 24 distinct formulas (summarizable stratum)
    made = 0
    seed = 0
    seen_hash = set()
    while made < 24:
        seed += 1
        rng = random.Random(seed)
        e = random_tree(rng, 12, 4)
        if isinstance(e, Var) or len(expr_support(e)) < 2:
            continue
        h = expr_structural_hash(e)
        if h in seen_hash:
            continue
        seen_hash.add(h)
        made += 1
        corpus.append((f"tree_d4_s{seed}", "random_trees_depth4", e))
    # high-sharing DAGs: reconvergent ladders + mixed-operator shared DAGs (20 distinct)
    for depth in (4, 6, 8, 10):
        corpus.append((f"ladder_d{depth}", "high_sharing_dags", shared_ladder(depth)))
    for i in range(16):
        corpus.append((f"mixed_dag_s{40 + i}", "high_sharing_dags",
                       mixed_shared_dag(12, 30 + 3 * i, 40 + i)))
    # multipliers, sequential and balanced (live_k <= 16)
    for topology in ("sequential", "balanced"):
        for nb, bits in ((4, (3, 4)), (6, (5, 6)), (8, (7, 8))):
            for bit in bits:
                if skip_slow and topology == "sequential" and nb == 8:
                    continue
                corpus.append((f"mult_{topology}_nb{nb}_bit{bit}", f"multiplier_{topology}",
                               multiplier_bit(nb, topology, bit)))
    return corpus


# --------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------

def measure_formula(name: str, family: str, expr) -> dict:
    support = expr_support(expr)
    live_k = len(support)
    assert live_k <= 16, name
    eff_support = support if live_k >= 6 else tuple(
        sorted(set(support) | {f"x{i}" for i in range(6)}, key=lambda s: int(s[1:])))
    fixed: dict = {}

    # ---- parse boundary (v2 defs/ref document)
    doc = json.loads(json.dumps(expr_to_json_dag(expr)))
    parse_us = timed(lambda: expr_from_json(doc), blocks=BLOCKS) * 1e6
    tree = tree_occurrences(expr)
    raw_feasible = tree <= 90_000

    # ---- compile all arms once for programs/metrics/equality
    node_new = compile_expr_to_cm_ir(expr)
    node_old = compile_expr_to_cm_ir(expr, share_aware_flatten=False, build_memo=False)
    progs = {
        "cm_new": get_flat_program(node_new),
        "cm_old": get_flat_program(node_old),
        "cse": compile_expr_cse(expr),
        "cse_flat": compile_expr_cse(expr, flatten=True),
    }
    if raw_feasible:
        progs["raw"] = compile_expr_flat(expr)

    # ---- exact packed equality across every arm BEFORE timing
    values = {arm: _eval_words(p, eff_support, fixed) for arm, p in progs.items()}
    ref = values["cm_new"]
    equal = all(v == ref for v in values.values())
    if not equal:
        raise AssertionError(f"packed mismatch in {name}")

    row = {
        "id": f"{family}-{name}-{expr_structural_hash(expr)[:12]}",
        "family": family,
        "formula_hash": expr_structural_hash(expr),
        "live_k": live_k,
        "support": list(support),
        "operator_mix": operator_mix(expr),
        "tree_occurrences": tree,
        "schedule": SCHEDULE,
        "repeat": REPEAT,
        "blocks": BLOCKS,
        "parse_us": parse_us,
        "packed_equal_all_arms": True,
        "raw_arm_included": raw_feasible,
    }

    # ---- deterministic program metrics per arm
    for arm, prog in progs.items():
        m = program_metrics(prog)
        row[f"{arm}_flat_instructions"] = m["flat_instructions"]
        row[f"{arm}_executed_word_ops"] = m["executed_word_ops"]
        row[f"{arm}_executed_bigint_ops"] = m["executed_bigint_ops"]
        row[f"{arm}_peak_live_word_buffers"] = m["peak_live_word_buffers"]
        row[f"{arm}_argument_edges"] = m["argument_edges"]

    # ---- preparation time per arm (fresh compile each call)
    prep_calls = {
        "cm_new": lambda: compile_expr_to_cm_ir(expr),
        "cm_old": lambda: compile_expr_to_cm_ir(expr, share_aware_flatten=False, build_memo=False),
        "cse": lambda: compile_expr_cse(expr),
        "cse_flat": lambda: compile_expr_cse(expr, flatten=True),
    }
    if raw_feasible:
        prep_calls["raw"] = lambda: compile_expr_flat(expr)
    slow = tree > 20_000
    for arm, fn in prep_calls.items():
        blocks = 1 if (slow and arm in ("cm_old", "raw")) else BLOCKS
        row[f"{arm}_prep_us"] = timed(fn, blocks=blocks) * 1e6
    # cm_new preparation includes lowering to a FlatProgram for kernel use
    row["cm_new_lower_us"] = timed(lambda: compile_flat(node_new), blocks=BLOCKS) * 1e6

    # ---- steady-state kernel time per arm (identical call shape)
    for arm, prog in progs.items():
        if arm == "raw" and len(prog.ops) > 40_000:
            continue
        reps = max(3, min(REPEAT, 20_000 // max(1, len(prog.ops))))
        row[f"{arm}_kernel_us"] = timed(lambda p=prog: _eval_words(p, eff_support, fixed),
                                        repeats=reps) * 1e6
        row[f"{arm}_kernel_repeats"] = reps

    # ---- admission/budget wrapper boundary (cm_new only; NOT a kernel number)
    def wrapper_call():
        return materialize_hybrid_no_reinflate(
            node_new, eff_support, fixed=fixed, hybrid_threshold=16,
            allow_reduced_output=False, max_full_output_vars=16,
            flat_eval=True, words_eval=True)

    wrapped = wrapper_call()
    row["wrapper_matches_kernel"] = int(wrapped.bits) == ref
    row["cm_new_wrapper_total_us"] = timed(wrapper_call, repeats=min(REPEAT, 50)) * 1e6
    row["cm_new_wrapper_overhead_us"] = row["cm_new_wrapper_total_us"] - row["cm_new_kernel_us"]

    # ---- cold totals (fresh compile + first evaluation on a fresh program)
    def cold_cm():
        n = compile_expr_to_cm_ir(expr)
        return _eval_words(compile_flat(n), eff_support, fixed)

    def cold_cse():
        return _eval_words(compile_expr_cse(expr), eff_support, fixed)

    row["cm_new_cold_total_us"] = timed(cold_cm, blocks=BLOCKS) * 1e6
    row["cse_cold_total_us"] = timed(cold_cse, blocks=BLOCKS) * 1e6

    # ---- repeated workload + break-even vs the cse production baseline
    row["cm_new_repeated_total_us"] = row["cm_new_prep_us"] + REPEAT * row["cm_new_kernel_us"]
    row["cse_repeated_total_us"] = row["cse_prep_us"] + REPEAT * row["cse_kernel_us"]
    prep_gap = row["cm_new_prep_us"] - row["cse_prep_us"]
    eval_gain = row["cse_kernel_us"] - row["cm_new_kernel_us"]
    if eval_gain > 0:
        row["breakeven_evals_vs_cse"] = math.ceil(prep_gap / eval_gain) if prep_gap > 0 else 0
    else:
        row["breakeven_evals_vs_cse"] = None
    return row


def compact_key_residual():
    """Phase 4: residual compile cost after memo+guard, vs the scratch
    compact-key prototype from the 2026-08-02 deep-followup driver."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "dfu", str(ROOT / "deliverables_n22_24" / "cm_gap_deep_followup_2026_08_02.py"))
    dfu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dfu)
    rows = []
    for name, expr in (("mult_sequential_nb8_bit8", multiplier_bit(8, "sequential", 8)),
                       ("mult_balanced_nb8_bit8", multiplier_bit(8, "balanced", 8)),
                       ("ladder_d10", shared_ladder(10)),
                       ("mixed_dag_s60", mixed_shared_dag(12, 60, 2))):
        support = expr_support(expr)
        ref = _eval_words(get_flat_program(compile_expr_to_cm_ir(expr)), support, {})
        assert _eval_words(dfu.compile_compact(expr), support, {}) == ref
        rows.append({
            "case": name,
            "cm_legacy_us": timed(lambda: compile_expr_to_cm_ir(
                expr, share_aware_flatten=False, build_memo=False), blocks=1) * 1e6,
            "cm_repaired_us": timed(lambda: compile_expr_to_cm_ir(expr), blocks=BLOCKS) * 1e6,
            "compact_prototype_us": timed(lambda: dfu.compile_compact(expr), blocks=BLOCKS) * 1e6,
            "note": "compact prototype is scratch-only (deep-followup driver); not merged",
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-slow", action="store_true")
    args = parser.parse_args()

    try:
        git_rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.strip()
    except Exception:
        git_rev = "unknown"

    corpus = build_corpus(args.skip_slow)
    rows = []
    for name, family, expr in corpus:
        print(f"[{time.strftime('%H:%M:%S')}] {family}/{name}", flush=True)
        rows.append(measure_formula(name, family, expr))

    # per-family summaries only where the stratum has >= 20 distinct formulas
    families = defaultdict(list)
    for r in rows:
        families[r["family"]].append(r)
    summaries = []
    for family, sel in sorted(families.items()):
        entry = {"family": family, "distinct_formulas": len(sel),
                 "summarizable": len(sel) >= 20}
        if len(sel) >= 20:
            for num, den, label in (("cm_new_kernel_us", "cse_kernel_us", "cm_new_over_cse_kernel"),
                                    ("cm_new_kernel_us", "cm_old_kernel_us", "cm_new_over_cm_old_kernel"),
                                    ("cm_new_prep_us", "cse_prep_us", "cm_new_over_cse_prep"),
                                    ("cm_new_prep_us", "cm_old_prep_us", "cm_new_over_cm_old_prep")):
                logs = [math.log(r[num] / r[den]) for r in sel]
                entry[f"{label}_geomean"] = math.exp(statistics.mean(logs))
                entry[f"{label}_min"] = math.exp(min(logs))
                entry[f"{label}_max"] = math.exp(max(logs))
        summaries.append(entry)

    out = {
        "_meta": {
            "python": sys.version,
            "numpy": np.__version__,
            "cpu": platform.processor(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "git_revision": git_rev,
            "schedule": SCHEDULE,
            "repeat": REPEAT,
            "blocks": BLOCKS,
            "bitset_env_cache": bitset_env_cache_stats(),
            "note": ("cm_old = legacy compile (always-splice flattening, no build memo); "
                     "cm_new = 2026-08-02 repaired compile. flat_instructions is an "
                     "instruction count; executed_*_ops are the authoritative "
                     "executed-operation counts."),
        },
        "formulas": rows,
        "family_summaries": summaries,
        "compact_key_residual": compact_key_residual(),
    }
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")

    csv_fields = ["id", "family", "live_k", "tree_occurrences",
                  "cm_old_flat_instructions", "cm_new_flat_instructions",
                  "cm_old_executed_word_ops", "cm_new_executed_word_ops",
                  "cse_executed_word_ops",
                  "cm_old_prep_us", "cm_new_prep_us", "cse_prep_us",
                  "cm_old_kernel_us", "cm_new_kernel_us", "cse_kernel_us",
                  "cm_old_peak_live_word_buffers", "cm_new_peak_live_word_buffers",
                  "cm_new_wrapper_overhead_us", "breakeven_evals_vs_cse",
                  "packed_equal_all_arms"]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT_JSON}\nwrote {OUT_CSV}")


if __name__ == "__main__":
    main()
