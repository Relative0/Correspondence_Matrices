"""B5 on-pod measurement: matched-cost CM/BitSet vs native CUDD (Linux only).

Runs inside the pod repo checkout. Protocol (V4 section C matched-cost
conventions, refreshed on the frozen corrected-E3 corpus):

- corpus: CM_gap_e3_corrected_corpus_2026_08_02.jsonl (192 formulas,
  k in {8,12,16}), SHA-256 verified against the archived value;
- construction costs measured separately per arm: CM DAG compile
  (compile_expr_to_cm_ir), CSE-flat prep, CUDD build (dd.cudd, fixed natural
  variable order, one build — no order search);
- evaluation costs measured separately: CM words kernel and CSE-flat words
  kernel (complete packed truth function per call); CUDD 256 deterministic
  assignments (seeded, recorded) and CUDD full 2^k extraction;
- correctness: CM/CSE-flat complete packed equality before timing on every
  formula; CUDD full-extraction packed equality vs the CM bits on every
  formula (stronger than the archived 64-sample mode);
- fail closed: `import dd.cudd` must succeed and every BDD must come from
  dd.cudd (robdd_is_cudd analogue); no autoref fallback is permitted.
"""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.setrecursionlimit(200_000)

import numpy as np

import dd.cudd as _cudd  # fail closed: ImportError aborts the campaign

from bitset_backend import _eval_words, compile_expr_cse, get_flat_program
from cm_expr_serde import expr_from_json
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir

CORPUS = ROOT / "deliverables_n22_24" / "CM_gap_e3_corrected_corpus_2026_08_02.jsonl"
CORPUS_SHA = "8a6da87cc8b13f6123cb11adfa77b5d69bcd0a086666abea7df633ef92f6e68a"
OUT = ROOT / "deliverables_n22_24" / "pod_out"
EVAL_SAMPLES = 256
SAMPLE_SEED = 20260803


def timed(fn, repeats=1, blocks=3):
    best = float("inf")
    for _ in range(blocks):
        t0 = time.perf_counter()
        for _ in range(repeats):
            fn()
        best = min(best, (time.perf_counter() - t0) / repeats)
    return best


def expr_to_bdd(expr, bdd, var_of):
    memo = {}

    def rec(e):
        r = memo.get(id(e))
        if r is not None:
            return r
        if isinstance(e, Var):
            r = var_of[int(e.i)]
        elif isinstance(e, Not):
            r = bdd.apply("not", rec(e.a))
        else:
            a, b = rec(e.a), rec(e.b)
            if isinstance(e, And):
                r = bdd.apply("and", a, b)
            elif isinstance(e, Or):
                r = bdd.apply("or", a, b)
            elif isinstance(e, Xor):
                r = bdd.apply("xor", a, b)
            elif isinstance(e, Imp):
                r = bdd.apply("=>", a, b)
            elif isinstance(e, Eqv):
                r = bdd.apply("<=>", a, b)
            else:
                raise TypeError(e)
        memo[id(e)] = r
        return r

    return rec(expr)


def main():
    data = CORPUS.read_bytes()
    if hashlib.sha256(data).hexdigest() != CORPUS_SHA:
        raise SystemExit("corpus SHA mismatch — refusing to measure")
    lines = data.decode().splitlines()
    records = [json.loads(l) for l in lines[1:] if l.strip()]
    assert len(records) == 192
    OUT.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SAMPLE_SEED)
    rows = []
    t_start = time.perf_counter()
    for rec in records:
        k = rec["stratum_live_k"]
        expr = expr_from_json(rec["expression_v2"])
        support = tuple(f"x{i}" for i in range(k))
        node = compile_expr_to_cm_ir(expr)
        prog_cm = get_flat_program(node)
        prog_flat = compile_expr_cse(expr, flatten=True)
        bits_cm = int(_eval_words(prog_cm, support, {}))
        bits_flat = int(_eval_words(prog_flat, support, {}))
        if bits_cm != bits_flat:
            raise AssertionError(f"packed mismatch cm/cse_flat: {rec['id']}")

        bdd = _cudd.BDD()
        bdd.declare(*support)
        var_of = {i: bdd.var(f"x{i}") for i in range(k)}
        u = expr_to_bdd(expr, bdd, var_of)
        if type(bdd).__module__ != "dd.cudd":
            raise AssertionError("BDD manager is not dd.cudd — fail closed")

        # full extraction correctness: axis convention — vars_key[0] is the
        # MSB axis in _eval_words, so assignment for truth-bit m has
        # x0 = (m >> (k-1)) & 1 ... x_{k-1} = m & 1.
        def assignment(m):
            return {f"x{i}": bool((m >> (k - 1 - i)) & 1) for i in range(k)}

        t0 = time.perf_counter()
        bits_cudd = 0
        let = bdd.let
        for m in range(1 << k):
            if bdd.let(assignment(m), u) == bdd.true:
                bits_cudd |= 1 << m
        extract_full_s = time.perf_counter() - t0
        if bits_cudd != bits_cm:
            raise AssertionError(f"CUDD full-extraction mismatch: {rec['id']}")

        row = {
            "id": rec["id"], "stratum_live_k": k,
            "op_family": rec["op_family"], "shape": rec["shape"],
            "structural_hash": rec["structural_hash"],
            "truth_sha256": rec["truth_sha256"],
            "packed_equal_cm_cse_flat": True,
            "cudd_full_extraction_equal": True,
            "robdd_is_cudd": True,
            "cudd_dag_size": int(u.dag_size),
            "cm_prep_us": timed(lambda: compile_expr_to_cm_ir(expr)) * 1e6,
            "cse_flat_prep_us": timed(
                lambda: compile_expr_cse(expr, flatten=True)) * 1e6,
            "cm_kernel_us": timed(
                lambda: _eval_words(prog_cm, support, {}), repeats=20) * 1e6,
            "cse_flat_kernel_us": timed(
                lambda: _eval_words(prog_flat, support, {}), repeats=20) * 1e6,
            "cudd_extract_full_us": extract_full_s * 1e6,
        }

        def build_once():
            b2 = _cudd.BDD()
            b2.declare(*support)
            v2 = {i: b2.var(f"x{i}") for i in range(k)}
            return expr_to_bdd(expr, b2, v2)

        row["cudd_build_us"] = timed(build_once) * 1e6

        samples = [int(x) for x in rng.integers(0, 1 << k, EVAL_SAMPLES)]
        asns = [assignment(m) for m in samples]

        def eval256():
            acc = 0
            for a in asns:
                acc ^= (bdd.let(a, u) == bdd.true)
            return acc

        t0 = time.perf_counter()
        eval256()
        row["cudd_eval256_us"] = (time.perf_counter() - t0) * 1e6
        # sampled correctness re-check vs packed bits
        for m, a in zip(samples, asns):
            if ((bits_cm >> m) & 1) != (bdd.let(a, u) == bdd.true):
                raise AssertionError(f"CUDD sample mismatch: {rec['id']}")
        rows.append(row)
        if len(rows) % 24 == 0:
            print(f"  {len(rows)}/192", flush=True)

    def med(key, sel):
        return statistics.median(r[key] for r in sel)

    summary = []
    for k in (8, 12, 16):
        sel = [r for r in rows if r["stratum_live_k"] == k]
        summary.append({
            "live_k": k, "n": len(sel),
            "cm_prep_us_median": med("cm_prep_us", sel),
            "cse_flat_prep_us_median": med("cse_flat_prep_us", sel),
            "cudd_build_us_median": med("cudd_build_us", sel),
            "cm_kernel_us_median": med("cm_kernel_us", sel),
            "cse_flat_kernel_us_median": med("cse_flat_kernel_us", sel),
            "cudd_eval256_us_median": med("cudd_eval256_us", sel),
            "cudd_extract_full_us_median": med("cudd_extract_full_us", sel),
            "cudd_dag_size_median": med("cudd_dag_size", sel),
        })
    results = {
        "_meta": {
            "driver": Path(__file__).name,
            "corpus_sha256": CORPUS_SHA,
            "python": sys.version, "numpy": np.__version__,
            "dd_cudd": True,
            "platform": platform.platform(),
            "cudd_version": getattr(_cudd, "__version__", "unknown"),
            "eval_samples": EVAL_SAMPLES, "sample_seed": SAMPLE_SEED,
            "wall_time_s": time.perf_counter() - t_start,
            "conventions": "CUDD fixed natural order, single build, no "
                           "reordering; construction and evaluation reported "
                           "separately; full-extraction packed equality on "
                           "every formula",
        },
        "rows": rows,
        "summary": summary,
    }
    (OUT / "cm_b5_cudd_matched_results_2026_08_03.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8")
    import csv
    with (OUT / "CM_b5_cudd_matched_summary_2026_08_03.csv").open(
            "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader(); w.writerows(summary)
    print(f"done: 192 rows, wall {time.perf_counter() - t_start:.1f}s")


if __name__ == "__main__":
    main()
