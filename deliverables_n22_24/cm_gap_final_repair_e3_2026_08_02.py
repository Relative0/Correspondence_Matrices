"""Corrected local E3 replication (2026-08-02, post-repair).

Formula-clustered, operator-crossed replication of the packed-evaluation
comparison with the repaired CM compiler against the structural-CSE
production baseline, on exact-support strata 8/12/16.

Design (per the final-repair brief):
- >= 30 distinct formulas per stratum: 4 operator families (xor-dominant,
  and/or-dominant, imp/eqv-dominant, mixed) x 2 shapes (low-sharing tree,
  shared DAG) x 4 formulas = 32. Formula identity (structural hash) is the
  inferential unit; no ambient-n rebinding; timing rounds are never counted
  as formulas.
- Primary arms: repaired CM kernel vs structural-CSE BitSet kernel, both as
  bare ``_eval_words`` on prebuilt programs (identical call shape).
- Secondary, reported separately: raw ablation, CSE+sharing-aware flatten,
  admission wrapper, cold totals, repeated-workload totals, break-even.
- Blocked and round-robin schedules measured and reported separately (never
  pooled). Even paired rounds with alternating order.
- Exact packed equality asserted across every arm before timing.
- Statistics: per-formula paired log ratios; per-stratum geomean/median;
  cluster bootstrap CI (formula = resampling unit, 2000 draws, seeded);
  residual sigma with df = n-1; operator-family and shape subgroups. No
  significance claims from timing rounds.

Outputs:
  CM_gap_e3_corpus_2026_08_02.jsonl
  cm_gap_final_repair_e3_results_2026_08_02.json
  CM_gap_final_repair_e3_summary_2026_08_02.csv

Run: .venv/Scripts/python.exe deliverables_n22_24/cm_gap_final_repair_e3_2026_08_02.py
"""
from __future__ import annotations

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
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir, expr_structural_hash, materialize_hybrid_no_reinflate

DELIV = ROOT / "deliverables_n22_24"
CORPUS_OUT = DELIV / "CM_gap_e3_corpus_2026_08_02.jsonl"
RESULTS_OUT = DELIV / "cm_gap_final_repair_e3_results_2026_08_02.json"
SUMMARY_OUT = DELIV / "CM_gap_final_repair_e3_summary_2026_08_02.csv"

STRATA = (8, 12, 16)
PER_CELL = 4                      # formulas per (stratum, family, shape)
ROUNDS = 4                        # even, alternating order
RR_PASSES = 60                    # round-robin passes per stratum
BOOTSTRAP = 2000

OPS = {"and": And, "or": Or, "xor": Xor, "imp": Imp, "eqv": Eqv}
FAMILIES = {
    "xor_dom": {"xor": 0.75, "and": 0.08, "or": 0.07, "imp": 0.05, "eqv": 0.05},
    "andor_dom": {"and": 0.40, "or": 0.40, "xor": 0.10, "imp": 0.05, "eqv": 0.05},
    "impeqv_dom": {"imp": 0.40, "eqv": 0.40, "and": 0.07, "or": 0.07, "xor": 0.06},
    "mixed": {"and": 0.2, "or": 0.2, "xor": 0.2, "imp": 0.2, "eqv": 0.2},
}


def pick_op(rng, weights):
    r = rng.random()
    acc = 0.0
    for name, w in weights.items():
        acc += w
        if r <= acc:
            return name
    return "xor"


def tree_formula(rng, k, weights):
    """Low-sharing random tree with exact support k (every var appears)."""
    extra = rng.randrange(0, max(1, k // 2) + 1)
    leaves = list(range(k)) + [rng.randrange(k) for _ in range(extra)]
    rng.shuffle(leaves)
    nodes = [Var(i) for i in leaves]
    while len(nodes) > 1:
        i = rng.randrange(len(nodes) - 1)
        a = nodes.pop(i)
        b = nodes.pop(rng.randrange(len(nodes)))
        combined = OPS[pick_op(rng, weights)](a, b)
        if rng.random() < 0.12:
            combined = Not(combined)
        nodes.insert(rng.randrange(len(nodes) + 1), combined)
    return nodes[0]


def shared_formula(rng, k, weights):
    """Controlled shared DAG with exact support k."""
    pool = [Var(i) for i in range(k)]
    for _ in range(k + rng.randrange(k, 2 * k)):
        name = pick_op(rng, weights)
        e = OPS[name](rng.choice(pool), rng.choice(pool))
        if rng.random() < 0.10:
            e = Not(e)
        pool.append(e)
    root = pool[-1]
    for e in pool[-5:-1]:
        root = OPS[max(weights, key=weights.get)](root, e)
    # guarantee exact support: fold in any variable the walk missed
    missing = set(range(k)) - {int(s[1:]) for s in expr_support(root)}
    dom = max(weights, key=weights.get)
    for m in sorted(missing):
        root = OPS[dom](root, Var(m))
    return root


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


def operator_mix(expr):
    counts, seen, stack = Counter(), set(), [expr]
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


def build_corpus():
    records = []
    seen_hashes = set()
    for k in STRATA:
        for family, weights in FAMILIES.items():
            for shape in ("tree", "shared"):
                made = 0
                attempt = 0
                while made < PER_CELL:
                    attempt += 1
                    seed = k * 1_000_000 + hash(family) % 9973 * 1000 + \
                        (0 if shape == "tree" else 500_000) + attempt
                    rng = random.Random(seed)
                    expr = (tree_formula if shape == "tree" else shared_formula)(rng, k, weights)
                    if len(expr_support(expr)) != k:
                        continue
                    if tree_occurrences(expr) > 60_000:
                        continue
                    h = expr_structural_hash(expr)
                    if h in seen_hashes:
                        continue
                    seen_hashes.add(h)
                    made += 1
                    records.append({
                        "id": f"e3-k{k}-{family}-{shape}-{made}-{h[:12]}",
                        "stratum_live_k": k,
                        "op_family": family,
                        "shape": shape,
                        "seed": seed,
                        "structural_hash": h,
                        "operator_mix": operator_mix(expr),
                        "tree_occurrences": tree_occurrences(expr),
                        "expression_v2": expr_to_json_dag(expr),
                    })
    return records


def timed(fn, repeats=1, blocks=3):
    best = float("inf")
    for _ in range(blocks):
        t0 = time.perf_counter()
        for _ in range(repeats):
            fn()
        best = min(best, (time.perf_counter() - t0) / repeats)
    return best


def prepare(record):
    expr = expr_from_json(record["expression_v2"])
    support = expr_support(expr)
    node = compile_expr_to_cm_ir(expr)
    progs = {
        "cm": get_flat_program(node),
        "cse": compile_expr_cse(expr),
        "cse_flat": compile_expr_cse(expr, flatten=True),
    }
    raw_ok = record["tree_occurrences"] <= 60_000
    if raw_ok:
        progs["raw"] = compile_expr_flat(expr)
    vals = {arm: _eval_words(p, support, {}) for arm, p in progs.items()}
    ref = vals["cm"]
    if any(v != ref for v in vals.values()):
        raise AssertionError(f"packed mismatch: {record['id']}")
    wrapped = materialize_hybrid_no_reinflate(
        node, support, fixed={}, hybrid_threshold=16, allow_reduced_output=False,
        max_full_output_vars=16, flat_eval=True, words_eval=True)
    if int(wrapped.bits) != ref:
        raise AssertionError(f"wrapper mismatch: {record['id']}")
    return expr, node, support, progs


def measure_blocked(record, expr, node, support, progs):
    row = {
        "id": record["id"], "stratum_live_k": record["stratum_live_k"],
        "op_family": record["op_family"], "shape": record["shape"],
        "structural_hash": record["structural_hash"],
        "operator_mix": record["operator_mix"],
        "tree_occurrences": record["tree_occurrences"],
        "schedule": "blocked_warm", "rounds": ROUNDS,
        "packed_equal_all_arms": True,
    }
    row["parse_us"] = timed(lambda: expr_from_json(record["expression_v2"])) * 1e6

    for arm, prog in progs.items():
        m = program_metrics(prog)
        row[f"{arm}_flat_instructions"] = m["flat_instructions"]
        row[f"{arm}_executed_word_ops"] = m["executed_word_ops"]
        row[f"{arm}_peak_live_word_buffers"] = m["peak_live_word_buffers"]

    row["cm_prep_us"] = timed(lambda: compile_expr_to_cm_ir(expr)) * 1e6
    row["cm_lower_us"] = timed(lambda: compile_flat(node)) * 1e6
    row["cse_prep_us"] = timed(lambda: compile_expr_cse(expr)) * 1e6
    row["cse_flat_prep_us"] = timed(lambda: compile_expr_cse(expr, flatten=True)) * 1e6
    if "raw" in progs:
        row["raw_prep_us"] = timed(lambda: compile_expr_flat(expr), blocks=1) * 1e6

    repeats = max(20, min(200, 20_000 // max(1, len(progs["cm"].ops))))
    row["kernel_repeats"] = repeats
    ratios = []
    cm_times, cse_times = [], []
    for rnd in range(ROUNDS):
        if rnd % 2:
            cm_s = timed(lambda: _eval_words(progs["cm"], support, {}), repeats, blocks=1)
            bs_s = timed(lambda: _eval_words(progs["cse"], support, {}), repeats, blocks=1)
        else:
            bs_s = timed(lambda: _eval_words(progs["cse"], support, {}), repeats, blocks=1)
            cm_s = timed(lambda: _eval_words(progs["cm"], support, {}), repeats, blocks=1)
        ratios.append(cm_s / bs_s)
        cm_times.append(cm_s)
        cse_times.append(bs_s)
    row["cm_kernel_us"] = statistics.median(cm_times) * 1e6
    row["cse_kernel_us"] = statistics.median(cse_times) * 1e6
    row["blocked_ratio_median"] = statistics.median(ratios)
    row["blocked_ratios"] = ratios

    for arm in ("cse_flat", "raw"):
        if arm in progs and len(progs[arm].ops) <= 20_000:
            reps = max(3, min(repeats, 20_000 // max(1, len(progs[arm].ops))))
            row[f"{arm}_kernel_us"] = timed(
                lambda a=arm: _eval_words(progs[a], support, {}), reps) * 1e6

    def wrapper_call():
        return materialize_hybrid_no_reinflate(
            node, support, fixed={}, hybrid_threshold=16, allow_reduced_output=False,
            max_full_output_vars=16, flat_eval=True, words_eval=True)

    row["cm_wrapper_total_us"] = timed(wrapper_call, repeats=30) * 1e6
    row["cm_wrapper_overhead_us"] = row["cm_wrapper_total_us"] - row["cm_kernel_us"]

    def cold_cm():
        n = compile_expr_to_cm_ir(expr)
        return _eval_words(compile_flat(n), support, {})

    row["cm_cold_total_us"] = timed(cold_cm) * 1e6
    row["cse_cold_total_us"] = timed(
        lambda: _eval_words(compile_expr_cse(expr), support, {})) * 1e6
    row["cm_repeated100_total_us"] = row["cm_prep_us"] + 100 * row["cm_kernel_us"]
    row["cse_repeated100_total_us"] = row["cse_prep_us"] + 100 * row["cse_kernel_us"]
    prep_gap = row["cm_prep_us"] - row["cse_prep_us"]
    eval_gain = row["cse_kernel_us"] - row["cm_kernel_us"]
    row["breakeven_evals_vs_cse"] = (
        (0 if prep_gap <= 0 else math.ceil(prep_gap / eval_gain)) if eval_gain > 0 else None)
    return row


def measure_round_robin(prepared):
    """Round-robin across all formulas of one stratum; even alternation."""
    tot_cm = defaultdict(float)
    tot_bs = defaultdict(float)
    for p in range(RR_PASSES):
        for rec_id, support, progs in prepared:
            if p % 2:
                t0 = time.perf_counter(); _eval_words(progs["cm"], support, {})
                t1 = time.perf_counter(); _eval_words(progs["cse"], support, {})
                t2 = time.perf_counter()
                tot_cm[rec_id] += t1 - t0; tot_bs[rec_id] += t2 - t1
            else:
                t0 = time.perf_counter(); _eval_words(progs["cse"], support, {})
                t1 = time.perf_counter(); _eval_words(progs["cm"], support, {})
                t2 = time.perf_counter()
                tot_bs[rec_id] += t1 - t0; tot_cm[rec_id] += t2 - t1
    return {rid: tot_cm[rid] / tot_bs[rid] for rid, _, _ in prepared}


def bootstrap_ci(logs, rng, draws=BOOTSTRAP):
    n = len(logs)
    means = []
    for _ in range(draws):
        sample = [logs[rng.randrange(n)] for _ in range(n)]
        means.append(statistics.mean(sample))
    means.sort()
    return (math.exp(means[int(0.025 * draws)]), math.exp(means[int(0.975 * draws)]))


def summarize(rows, ratio_key, label):
    out = []
    rng = random.Random(20260802)

    def stat_block(sel, group):
        logs = [math.log(r[ratio_key]) for r in sel]
        n = len(logs)
        entry = {
            "schedule": label, "group": group, "n_formulas": n,
            "geomean": math.exp(statistics.mean(logs)),
            "median": math.exp(statistics.median(logs)),
            "sigma_log": statistics.stdev(logs) if n > 1 else None,
            "df": n - 1,
        }
        if n > 3:
            lo, hi = bootstrap_ci(logs, rng)
            entry["ci95_lo"], entry["ci95_hi"] = lo, hi
        return entry

    by_stratum = defaultdict(list)
    for r in rows:
        by_stratum[r["stratum_live_k"]].append(r)
    for k, sel in sorted(by_stratum.items()):
        out.append(stat_block(sel, f"live_k={k}"))
        for family in FAMILIES:
            sub = [r for r in sel if r["op_family"] == family]
            if sub:
                out.append(stat_block(sub, f"live_k={k}/family={family}"))
        for shape in ("tree", "shared"):
            sub = [r for r in sel if r["shape"] == shape]
            if sub:
                out.append(stat_block(sub, f"live_k={k}/shape={shape}"))
    out.append(stat_block(rows, "all"))
    return out


def main():
    try:
        git_rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.strip()
    except Exception:
        git_rev = "unknown"

    print("generating corpus ...", flush=True)
    corpus = build_corpus()
    with CORPUS_OUT.open("w", encoding="utf-8") as fh:
        for rec in corpus:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    counts = Counter((r["stratum_live_k"], r["op_family"], r["shape"]) for r in corpus)
    assert all(v == PER_CELL for v in counts.values())
    print(f"  {len(corpus)} distinct formulas "
          f"({len(set(r['structural_hash'] for r in corpus))} distinct hashes)")

    rows = []
    by_stratum_prepared = defaultdict(list)
    for rec in corpus:
        expr, node, support, progs = prepare(rec)
        rows.append(measure_blocked(rec, expr, node, support, progs))
        by_stratum_prepared[rec["stratum_live_k"]].append((rec["id"], support, progs))
        if len(rows) % 24 == 0:
            print(f"  [{time.strftime('%H:%M:%S')}] measured {len(rows)}/{len(corpus)}", flush=True)

    print("round-robin schedules ...", flush=True)
    rr_ratio_by_id = {}
    for k, prepared in sorted(by_stratum_prepared.items()):
        rr_ratio_by_id.update(measure_round_robin(prepared))
    for r in rows:
        r["rr_ratio"] = rr_ratio_by_id[r["id"]]

    blocked_summary = summarize(rows, "blocked_ratio_median", "blocked")
    rr_summary = summarize(rows, "rr_ratio", "round_robin")

    results = {
        "_meta": {
            "python": sys.version, "numpy": np.__version__,
            "cpu": platform.processor(), "platform": platform.platform(),
            "git_revision": git_rev,
            "rounds": ROUNDS, "rr_passes": RR_PASSES, "bootstrap_draws": BOOTSTRAP,
            "cache_state": "warm within formula (blocked); cycling supports (round-robin)",
            "bitset_env_cache": bitset_env_cache_stats(),
            "primary_arms": "repaired CM kernel vs structural-CSE kernel, bare _eval_words",
            "note": "blocked and round-robin summaries are reported separately, never pooled",
        },
        "formulas": rows,
        "summary_blocked": blocked_summary,
        "summary_round_robin": rr_summary,
    }
    RESULTS_OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")

    with SUMMARY_OUT.open("w", newline="", encoding="utf-8") as fh:
        fields = ["schedule", "group", "n_formulas", "geomean", "median",
                  "ci95_lo", "ci95_hi", "sigma_log", "df"]
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(blocked_summary + rr_summary)
    print(f"wrote {CORPUS_OUT}\nwrote {RESULTS_OUT}\nwrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
