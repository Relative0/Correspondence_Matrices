"""B4 — guard/decline and n=16-24 family sweep (2026-08-03 refresh campaign).

Replaces the deck's pre-repair n>=18 numbers (marked superseded by the
consolidated audit) with post-repair measurements. Two parts:

Part 1 — guard/decline sweep (protocol of audit_decline_2026_07_21.py, fresh
seeds): random_expr at nominal n in {16,18,20,22,24}, depths {4,6,8}, 200
trials/cell; records live_k distribution, decline rate, wrong-guard and
oversized-output counts. Guard correctness is a hard failure if violated.

Part 2 — live_k-controlled headline refresh (protocol of Audit V4 C1 /
v4audit_packed_eval, fresh corpus): formulas with exact semantic support
k in {8,12,16} (corrected-E3 admission: measured family/shape membership,
balanced 4 families x 2 shapes, one per cell) embedded at ambient
n in {16,20,24} by fixing dead variables to 0. CM wrapper
(materialize_hybrid_no_reinflate, flat+words) vs the symmetric words BitSet
control (eval_expr_words_bitset, same support + fixed map — engine symmetry
per latent fix 1). Packed equality before timing; 7 paired interleaved
rounds; median paired ratios per (live_k, ambient n).

Fresh blake2b seeds (no hash()); outputs refuse-overwrite.
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
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.setrecursionlimit(200_000)

import numpy as np

from bitset_backend import eval_expr_words_bitset, eval_expr_flat_bitset, bitset_to_bool_array
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import random_expr
from cm_ir import compile_expr_to_cm_ir, expr_structural_hash, materialize_hybrid_no_reinflate

_spec = importlib.util.spec_from_file_location(
    "e3c_frozen", ROOT / "deliverables_n22_24" / "cm_gap_e3_corrected_2026_08_02.py")
e3c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e3c)

GENERATOR_VERSION = "b4-sweep-2026-08-03.1"
GUARD_SIZES = (16, 18, 20, 22, 24)
GUARD_DEPTHS = (4, 6, 8)
GUARD_TRIALS = 200
GUARD_SEED_BASE = 20260803
HEADLINE_K = (8, 12, 16)
AMBIENT_N = (16, 20, 24)
ROUNDS = 7


def stable_seed(k, family, shape, attempt):
    tag = (f"{GENERATOR_VERSION}|k={k}|family={e3c.FAMILY_CODES[family]}"
           f"|shape={e3c.SHAPE_CODES[shape]}|attempt={attempt}")
    return int.from_bytes(hashlib.blake2b(tag.encode(), digest_size=8).digest(), "big") >> 1


def timed(fn, repeats=1, blocks=1):
    best = float("inf")
    for _ in range(blocks):
        t0 = time.perf_counter()
        for _ in range(repeats):
            fn()
        best = min(best, (time.perf_counter() - t0) / repeats)
    return best


def guard_sweep(log=print):
    rows = []
    for n in GUARD_SIZES:
        for depth in GUARD_DEPTHS:
            live_counts, declined, wrong_guard, oversized = [], 0, 0, 0
            for trial in range(GUARD_TRIALS):
                rng = np.random.default_rng(GUARD_SEED_BASE + n * 10000 + depth * 100 + trial)
                expr = random_expr(n, rng, max_depth=depth, p_unary=0.25)
                node = compile_expr_to_cm_ir(expr)
                live_k = len(node.vars)
                live_counts.append(live_k)
                try:
                    result = materialize_hybrid_no_reinflate(
                        node, tuple(f"x{i}" for i in range(n)), fixed={},
                        hybrid_threshold=64, allow_reduced_output=n > 16,
                        max_full_output_vars=16, flat_eval=True)
                    if live_k > 16:
                        wrong_guard += 1
                    if len(result.output_vars) > 16 or (
                            result.bits is not None
                            and int(result.bits).bit_length() > (1 << len(result.output_vars))):
                        oversized += 1
                except ValueError as exc:
                    is_decline = str(exc).startswith(
                        "refusing to materialize reduced no-reinflate output")
                    declined += int(is_decline)
                    if live_k <= 16 or not is_decline:
                        wrong_guard += 1
            rows.append({
                "n": n, "depth": depth, "trials": GUARD_TRIALS,
                "seed_base": GUARD_SEED_BASE,
                "min_live_k": min(live_counts),
                "median_live_k": float(np.median(live_counts)),
                "max_live_k": max(live_counts),
                "declined_count": declined,
                "declined_rate": declined / GUARD_TRIALS,
                "wrong_guard_count": wrong_guard,
                "oversized_output_count": oversized,
            })
            log(f"  guard n={n} depth={depth}: median_live_k="
                f"{rows[-1]['median_live_k']} declined={declined} "
                f"wrong={wrong_guard}", flush=True)
    if any(r["wrong_guard_count"] or r["oversized_output_count"] for r in rows):
        raise AssertionError("guard violation detected")
    return rows


def build_headline_corpus(max_attempts=800, log=print):
    records = []
    for k in HEADLINE_K:
        hashes, truths = set(), set()
        for family, weights in e3c.FAMILIES.items():
            for shape in ("tree", "shared"):
                made, attempt = 0, 0
                while made < 1 and attempt < max_attempts:
                    attempt += 1
                    seed = stable_seed(k, family, shape, attempt)
                    rng = random.Random(seed)
                    expr = (e3c.tree_formula if shape == "tree"
                            else e3c.shared_formula)(rng, k, weights)
                    if len(e3c.syntactic_support(expr)) != k:
                        continue
                    struct = e3c.analyze_structure(expr)
                    if struct["unfolded_occurrences"] > e3c.MAX_UNFOLDED:
                        continue
                    if shape == "tree" and struct["n_repeated_nonleaf_structural"] > 0:
                        continue
                    if shape == "shared" and struct["sharing_factor"] < e3c.SHARED_MIN_SHARING:
                        continue
                    fam = e3c.family_admission(struct["operator_mix_structural"])
                    if family not in fam["actual_families"]:
                        continue
                    vars_key = tuple(f"x{i}" for i in range(k))
                    bits = eval_expr_flat_bitset(expr, vars_key)
                    arr = bitset_to_bool_array(bits, k).reshape((2,) * k)
                    dep = [ax for ax in range(k)
                           if not np.array_equal(np.take(arr, 0, axis=ax),
                                                 np.take(arr, 1, axis=ax))]
                    if dep != list(range(k)):
                        continue
                    truth_sha = hashlib.sha256(
                        int(bits).to_bytes((1 << k) // 8, "little")).hexdigest()
                    h = expr_structural_hash(expr)
                    if h in hashes or truth_sha in truths:
                        continue
                    hashes.add(h); truths.add(truth_sha)
                    made += 1
                    records.append({
                        "id": f"b4-k{k}-{family}-{shape}-{h[:12]}",
                        "generator_version": GENERATOR_VERSION,
                        "live_k": k, "op_family": family, "shape": shape,
                        "seed": seed, "attempt": attempt,
                        "structural_hash": h, "truth_sha256": truth_sha,
                        **{f: struct[f] for f in ("structural_dag_nodes",
                                                  "unfolded_occurrences")},
                        "expression_v2": expr_to_json_dag(expr),
                    })
                if made < 1:
                    records.append({"id": f"b4-k{k}-{family}-{shape}-EXHAUSTED",
                                    "status": "cell_exhausted"})
        log(f"  headline corpus: k={k} done", flush=True)
    return records


def headline_measure(records, log=print):
    rows = []
    for rec in records:
        if rec.get("status") == "cell_exhausted":
            continue
        k = rec["live_k"]
        expr = expr_from_json(rec["expression_v2"])
        node = compile_expr_to_cm_ir(expr)
        support = tuple(f"x{i}" for i in range(k))
        for n in AMBIENT_N:
            dead = {f"x{i}": 0 for i in range(k, n)}

            def cm_run():
                return materialize_hybrid_no_reinflate(
                    node, support, fixed=dead, hybrid_threshold=16,
                    allow_reduced_output=False, max_full_output_vars=16,
                    flat_eval=True, words_eval=True)

            def bs_run():
                return eval_expr_words_bitset(expr, support, fixed=dead)

            cm0, bs0 = cm_run(), bs_run()
            if int(cm0.bits) != int(bs0):
                raise AssertionError(f"packed mismatch: {rec['id']} n={n}")
            nb = (1 << k) // 8
            if hashlib.sha256(int(bs0).to_bytes(nb, "little")).hexdigest() != rec["truth_sha256"]:
                raise AssertionError(f"truth drift: {rec['id']}")
            est = timed(cm_run, 3)
            repeat = 200 if est < 50e-6 else 50 if est < 500e-6 else 10
            ratios, cm_t, bs_t = [], [], []
            for rnd in range(ROUNDS):
                if rnd % 2:
                    c = timed(cm_run, repeat); b = timed(bs_run, repeat)
                else:
                    b = timed(bs_run, repeat); c = timed(cm_run, repeat)
                ratios.append(c / b); cm_t.append(c); bs_t.append(b)
            rows.append({
                "id": rec["id"], "live_k": k, "ambient_n": n,
                "op_family": rec["op_family"], "shape": rec["shape"],
                "structural_hash": rec["structural_hash"],
                "truth_sha256": rec["truth_sha256"], "repeat": repeat,
                "packed_equal": True,
                "cm_us_median": statistics.median(cm_t) * 1e6,
                "bitset_us_median": statistics.median(bs_t) * 1e6,
                "paired_ratio_median": statistics.median(ratios),
                "paired_ratios": ratios,
            })
        log(f"  headline measured {rec['id']}", flush=True)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    targets = {n: out / n for n in (
        "CM_b4_headline_corpus_2026_08_03.jsonl",
        "cm_b4_sweep_results_2026_08_03.json",
        "CM_b4_guard_summary_2026_08_03.csv",
        "CM_b4_headline_summary_2026_08_03.csv")}
    existing = [str(p) for p in targets.values() if p.exists()]
    if existing:
        raise SystemExit("refusing to overwrite:\n  " + "\n  ".join(existing))
    out.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    print("Part 1: guard/decline sweep ...", flush=True)
    guard_rows = guard_sweep()
    print("Part 2: headline corpus ...", flush=True)
    corpus = build_headline_corpus()
    lines = [json.dumps({"record_type": "b4_headline_corpus_meta",
                         "generator_version": GENERATOR_VERSION},
                        sort_keys=True, separators=(",", ":"))]
    lines += [json.dumps(r, sort_keys=True, separators=(",", ":")) for r in corpus]
    corpus_bytes = ("\n".join(lines) + "\n").encode()
    targets["CM_b4_headline_corpus_2026_08_03.jsonl"].write_bytes(corpus_bytes)
    corpus_sha = hashlib.sha256(corpus_bytes).hexdigest()
    print(f"  corpus sha256 {corpus_sha}")
    print("Part 2: headline measurement ...", flush=True)
    headline_rows = headline_measure(corpus)

    headline_summary = []
    for k in HEADLINE_K:
        for n in AMBIENT_N:
            sel = [r for r in headline_rows if r["live_k"] == k and r["ambient_n"] == n]
            if not sel:
                continue
            ratios = [r["paired_ratio_median"] for r in sel]
            headline_summary.append({
                "live_k": k, "ambient_n": n, "n_formulas": len(sel),
                "paired_ratio_median": statistics.median(ratios),
                "paired_ratio_geomean": math.exp(
                    statistics.mean(math.log(x) for x in ratios)),
                "paired_ratio_p10": float(np.percentile(ratios, 10)),
                "paired_ratio_p90": float(np.percentile(ratios, 90)),
                "cm_us_median": statistics.median(r["cm_us_median"] for r in sel),
                "bitset_us_median": statistics.median(r["bitset_us_median"] for r in sel),
            })

    try:
        git_rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.strip()
    except Exception:
        git_rev = "unknown"
    results = {
        "_meta": {
            "driver": Path(__file__).name, "generator_version": GENERATOR_VERSION,
            "python": sys.version, "numpy": np.__version__,
            "cpu": platform.processor(), "platform": platform.platform(),
            "git_revision": git_rev,
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "wall_time_s": time.perf_counter() - t0,
            "corpus_sha256": corpus_sha,
            "guard_protocol": "audit_decline_2026_07_21 protocol, fresh seed base "
                              f"{GUARD_SEED_BASE}, {GUARD_TRIALS} trials/cell",
            "headline_protocol": "Audit V4 C1 restricted-scope protocol, symmetric "
                                 "words engines both sides, dead vars fixed to 0, "
                                 "blocked paired interleaved rounds",
            "schedules_note": "single blocked schedule; no pooling",
        },
        "guard_rows": guard_rows,
        "headline_rows": headline_rows,
        "headline_summary": headline_summary,
    }
    targets["cm_b4_sweep_results_2026_08_03.json"].write_text(
        json.dumps(results, indent=2), encoding="utf-8")
    with targets["CM_b4_guard_summary_2026_08_03.csv"].open(
            "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(guard_rows[0]))
        w.writeheader(); w.writerows(guard_rows)
    with targets["CM_b4_headline_summary_2026_08_03.csv"].open(
            "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(headline_summary[0]))
        w.writeheader(); w.writerows(headline_summary)
    print(f"wall {time.perf_counter() - t0:.1f}s; wrote outputs to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
