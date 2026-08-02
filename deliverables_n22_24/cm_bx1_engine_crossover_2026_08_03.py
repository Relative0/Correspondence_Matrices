"""BX1 — dedicated words/flat/bigint engine crossover sweep (2026-08-03).

Optional-gap follow-up to the refresh campaign: the deck's engine-crossover
claim ("bigint/flat below six variables, words at six and above") was only
touched in passing (B2 measured the k=4 fallback). This sweep measures the
three BitSet evaluation engines on the same formulas across live_k:

- recursive bigint  (eval_expr_bitset, prebuilt input env)
- flat bigint       (eval_expr_flat_bitset, program cached on the expr)
- numpy words       (_eval_words on the raw-AST program; k >= 6 only —
                     2^k bits must fill at least one uint64 word)

Steady-state kernels: environments/programs prebuilt outside all timed
windows. Exact-semantic-support corpora (blake2b seeds, corrected-E3
generators; the family-balance rule is relaxed below k=6 where dominant-
family membership is often unattainable — shapes still alternate and
admission still requires exact support + distinct structural hash and truth
SHA). Packed equality across all engines before timing (recursive engine is
the reference). 7 paired interleaved rounds; outputs refuse-overwrite.
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
    bitset_to_bool_array,
    build_bitset_env,
    eval_expr_bitset,
    eval_expr_flat_bitset,
    get_expr_flat_program,
)
from cm_expr_serde import expr_to_json_dag
from cm_ir import expr_structural_hash

_spec = importlib.util.spec_from_file_location(
    "e3c_frozen", ROOT / "deliverables_n22_24" / "cm_gap_e3_corrected_2026_08_02.py")
e3c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e3c)

GENERATOR_VERSION = "bx1-crossover-2026-08-03.1"
STRATA = (2, 3, 4, 5, 6, 7, 8, 10, 12, 16)
PER_K = 8
ROUNDS = 7
WORDS_MIN = 6


def stable_seed(k, attempt):
    tag = f"{GENERATOR_VERSION}|k={k}|attempt={attempt}"
    return int.from_bytes(hashlib.blake2b(tag.encode(), digest_size=8).digest(), "big") >> 1


def build_corpus(max_attempts=4000, log=print):
    families = list(e3c.FAMILIES.items())
    records = []
    for k in STRATA:
        hashes, truths = set(), set()
        made, attempt = 0, 0
        while made < PER_K and attempt < max_attempts:
            attempt += 1
            seed = stable_seed(k, attempt)
            rng = random.Random(seed)
            family, weights = families[attempt % len(families)]
            shape = "tree" if attempt % 2 else "shared"
            expr = (e3c.tree_formula if shape == "tree"
                    else e3c.shared_formula)(rng, k, weights)
            if len(e3c.syntactic_support(expr)) != k:
                continue
            struct = e3c.analyze_structure(expr)
            if struct["unfolded_occurrences"] > e3c.MAX_UNFOLDED:
                continue
            # exact semantic support via the recursive bigint reference
            vars_key = tuple(f"x{i}" for i in range(k))
            env = build_bitset_env(vars_key)
            bits = eval_expr_bitset(expr, env)
            arr = bitset_to_bool_array(bits, k).astype(bool).reshape((2,) * k)
            dep = [ax for ax in range(k)
                   if not np.array_equal(np.take(arr, 0, axis=ax),
                                         np.take(arr, 1, axis=ax))]
            if len(dep) != k:
                continue
            h = expr_structural_hash(expr)
            nbytes = max(1, (1 << k) // 8)
            truth_sha = hashlib.sha256(
                int(bits).to_bytes(nbytes, "little")).hexdigest()
            if h in hashes or truth_sha in truths:
                continue
            hashes.add(h); truths.add(truth_sha)
            made += 1
            records.append({
                "id": f"bx1-k{k}-{made}-{h[:12]}",
                "generator_version": GENERATOR_VERSION,
                "live_k": k, "op_family": family, "shape": shape,
                "seed": seed, "attempt": attempt,
                "structural_hash": h, "truth_sha256": truth_sha,
                "structural_dag_nodes": struct["structural_dag_nodes"],
                "expression_v2": expr_to_json_dag(expr),
            })
        if made < PER_K:
            raise SystemExit(f"corpus exhausted at k={k}: {made}/{PER_K}")
        log(f"  k={k}: {made} admitted in {attempt} attempts")
    return records


def timed(fn, repeats, blocks=1):
    best = float("inf")
    for _ in range(blocks):
        t0 = time.perf_counter()
        for _ in range(repeats):
            fn()
        best = min(best, (time.perf_counter() - t0) / repeats)
    return best


def measure(rec, expr):
    k = rec["live_k"]
    vars_key = tuple(f"x{i}" for i in range(k))
    env = build_bitset_env(vars_key)          # prebuilt, outside timing
    prog = get_expr_flat_program(expr)        # cached on expr

    engines = {
        "recursive_bigint": lambda: eval_expr_bitset(expr, env),
        "flat_bigint": lambda: eval_expr_flat_bitset(expr, vars_key),
    }
    if k >= WORDS_MIN:
        engines["words"] = lambda: _eval_words(prog, vars_key, {})

    ref = int(engines["recursive_bigint"]())
    for name, fn in engines.items():
        if int(fn()) != ref:
            raise AssertionError(f"packed mismatch {name}: {rec['id']}")
    nbytes = max(1, (1 << k) // 8)
    if hashlib.sha256(ref.to_bytes(nbytes, "little")).hexdigest() != rec["truth_sha256"]:
        raise AssertionError(f"truth drift: {rec['id']}")

    est = timed(engines["recursive_bigint"], 3)
    repeat = 500 if est < 20e-6 else 100 if est < 200e-6 else 20
    times = {n: [] for n in engines}
    order = sorted(engines)
    for rnd in range(ROUNDS):
        seq = order if rnd % 2 else list(reversed(order))
        for name in seq:
            times[name].append(timed(engines[name], repeat))
    row = {"id": rec["id"], "live_k": k, "op_family": rec["op_family"],
           "shape": rec["shape"], "structural_hash": rec["structural_hash"],
           "truth_sha256": rec["truth_sha256"],
           "structural_dag_nodes": rec["structural_dag_nodes"],
           "repeat": repeat, "packed_equal_all_engines": True}
    for name in engines:
        row[f"{name}_us_median"] = statistics.median(times[name]) * 1e6
    row["flat_vs_recursive_ratio"] = (row["flat_bigint_us_median"]
                                      / row["recursive_bigint_us_median"])
    if "words" in engines:
        row["words_vs_flat_ratio"] = row["words_us_median"] / row["flat_bigint_us_median"]
        row["words_vs_recursive_ratio"] = (row["words_us_median"]
                                           / row["recursive_bigint_us_median"])
    return row


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    targets = {n: out / n for n in ("CM_bx1_crossover_corpus_2026_08_03.jsonl",
                                    "cm_bx1_crossover_results_2026_08_03.json",
                                    "CM_bx1_crossover_summary_2026_08_03.csv")}
    existing = [str(p) for p in targets.values() if p.exists()]
    if existing:
        raise SystemExit("refusing to overwrite:\n  " + "\n  ".join(existing))
    out.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    print("generating BX1 corpus ...", flush=True)
    corpus = build_corpus()
    lines = [json.dumps({"record_type": "bx1_crossover_corpus_meta",
                         "generator_version": GENERATOR_VERSION,
                         "strata": list(STRATA), "per_k": PER_K},
                        sort_keys=True, separators=(",", ":"))]
    lines += [json.dumps(r, sort_keys=True, separators=(",", ":")) for r in corpus]
    corpus_bytes = ("\n".join(lines) + "\n").encode()
    targets["CM_bx1_crossover_corpus_2026_08_03.jsonl"].write_bytes(corpus_bytes)
    corpus_sha = hashlib.sha256(corpus_bytes).hexdigest()
    print(f"corpus sha256 {corpus_sha}")

    from cm_expr_serde import expr_from_json
    rows = []
    for rec in corpus:
        rows.append(measure(rec, expr_from_json(rec["expression_v2"])))
    summary = []
    for k in STRATA:
        sel = [r for r in rows if r["live_k"] == k]
        entry = {"live_k": k, "n_formulas": len(sel)}
        for name in ("recursive_bigint", "flat_bigint", "words"):
            key = f"{name}_us_median"
            vals = [r[key] for r in sel if key in r]
            entry[key] = statistics.median(vals) if vals else None
        for rk in ("flat_vs_recursive_ratio", "words_vs_flat_ratio",
                   "words_vs_recursive_ratio"):
            vals = [r[rk] for r in sel if rk in r]
            entry[f"{rk}_geomean"] = (math.exp(statistics.mean(
                math.log(v) for v in vals)) if vals else None)
        fastest = min(
            (n for n in ("recursive_bigint", "flat_bigint", "words")
             if entry.get(f"{n}_us_median") is not None),
            key=lambda n: entry[f"{n}_us_median"])
        entry["fastest_engine_by_median"] = fastest
        summary.append(entry)

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
            "corpus_sha256": corpus_sha, "rounds": ROUNDS,
            "engines": "recursive bigint / flat bigint / words (k>=6); "
                       "steady-state kernels, envs and programs prebuilt",
            "schedule": "blocked paired interleaved, engine order alternating",
            "note": "family balance relaxed below k=6 (admission: exact "
                    "semantic support + distinct hash/truth only)",
        },
        "formulas": rows,
        "summary": summary,
    }
    targets["cm_bx1_crossover_results_2026_08_03.json"].write_text(
        json.dumps(results, indent=2), encoding="utf-8")
    with targets["CM_bx1_crossover_summary_2026_08_03.csv"].open(
            "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader(); w.writerows(summary)
    print(f"wall {time.perf_counter() - t0:.1f}s; wrote outputs to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
