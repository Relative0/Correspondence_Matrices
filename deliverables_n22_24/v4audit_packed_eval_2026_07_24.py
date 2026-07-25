"""Paired/interleaved CM-vs-Bitset restricted packed-output comparison."""
from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bitset_backend import eval_expr_words_bitset
from cm_expr_serde import expr_from_json
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate

BASE = Path(__file__).resolve().parent
CORPUS = BASE / "v4audit_corpus_2026_07_24.jsonl"
RAW = BASE / "CM_v4audit_packed_eval_raw.csv"
SUMMARY = BASE / "CM_v4audit_packed_eval_summary.csv"
ROUNDS = 7


def timed(fn, repeat: int):
    t0 = time.perf_counter()
    value = None
    for _ in range(repeat):
        value = fn()
    return (time.perf_counter() - t0) / repeat, value


def percentile(values, q):
    return float(np.percentile(np.asarray(values, dtype=float), q))


def main():
    corpus = [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines()]
    raw = []
    for item in corpus:
        if item["explicit_packed_policy"] != "run":
            raw.append({
                "id": item["id"], "nominal_n": item["nominal_n"], "family": item["family"],
                "live_k": item["semantic_live_k"], "scope": "semantic_support",
                "round": "", "repeat": "", "cm_us": "", "bitset_us": "", "paired_ratio": "",
                "packed_equal": "", "status": "skipped_guard_gt16",
            })
            continue
        expr = expr_from_json(item["expression"])
        support = tuple(item["semantic_support"])
        dead_fixed = {f"x{i}": 0 for i in range(item["nominal_n"]) if f"x{i}" not in support}
        t0 = time.perf_counter()
        node = compile_expr_to_cm_ir(expr)
        compile_us = (time.perf_counter() - t0) * 1e6

        def cm_run():
            return materialize_hybrid_no_reinflate(
                node, support, fixed=dead_fixed, hybrid_threshold=16,
                allow_reduced_output=False, max_full_output_vars=16,
                flat_eval=True, words_eval=True,
            )

        def bitset_run():
            return eval_expr_words_bitset(expr, support, fixed=dead_fixed)

        cm0 = cm_run()
        bs0 = bitset_run()
        cm_bits = int(cm0.bits) if cm0.bits is not None else None
        equal = cm_bits == int(bs0)
        if not equal:
            raise AssertionError(f"packed mismatch: {item['id']}")
        estimate, _ = timed(cm_run, 3)
        repeat = 200 if estimate < 50e-6 else 50 if estimate < 500e-6 else 10
        for rnd in range(ROUNDS):
            if rnd % 2:
                cm_s, cm_val = timed(cm_run, repeat)
                bs_s, bs_val = timed(bitset_run, repeat)
            else:
                bs_s, bs_val = timed(bitset_run, repeat)
                cm_s, cm_val = timed(cm_run, repeat)
            ok = int(cm_val.bits) == int(bs_val)
            raw.append({
                "id": item["id"], "nominal_n": item["nominal_n"], "family": item["family"],
                "live_k": item["semantic_live_k"], "scope": "semantic_support",
                "round": rnd, "repeat": repeat, "compile_us": compile_us,
                "cm_us": cm_s * 1e6, "bitset_us": bs_s * 1e6,
                "paired_ratio": cm_s / bs_s, "packed_equal": ok, "status": "ok",
            })
    fields = sorted({key for row in raw for key in row})
    with RAW.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(raw)

    summary = []
    ok_rows = [r for r in raw if r["status"] == "ok"]
    for (family, live_k) in sorted({(r["family"], r["live_k"]) for r in ok_rows}):
        sel = [r for r in ok_rows if r["family"] == family and r["live_k"] == live_k]
        ratios = [float(r["paired_ratio"]) for r in sel]
        summary.append({
            "family": family, "live_k": live_k,
            "formulas": len({r["id"] for r in sel}), "paired_observations": len(sel),
            "all_packed_equal": all(r["packed_equal"] for r in sel),
            "cm_us_median": statistics.median(float(r["cm_us"]) for r in sel),
            "bitset_us_median": statistics.median(float(r["bitset_us"]) for r in sel),
            "paired_ratio_median": statistics.median(ratios),
            "paired_ratio_p10": percentile(ratios, 10),
            "paired_ratio_p90": percentile(ratios, 90),
        })
    with SUMMARY.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader(); w.writerows(summary)
    print(f"wrote {len(raw)} raw rows and {len(summary)} summary rows; mismatches=0")


if __name__ == "__main__":
    main()
