"""Same-corpus benchmark for bind-per-call versus prepared flat evaluation."""
from __future__ import annotations

import csv
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bitset_backend import eval_expr_flat_bitset, prepare_expr_flat_evaluation
from cmbench.corpus import load_expression_corpus

BASE = Path(__file__).resolve().parent
CORPUS = BASE / "v4audit_corpus_2026_07_24.jsonl"
RAW = BASE / "CM_v4fix_cached_eval_raw.csv"
SUMMARY = BASE / "CM_v4fix_cached_eval_summary.csv"
ROUNDS = 9


def per_call(fn, repeat: int):
    started = time.perf_counter()
    value = None
    for _ in range(repeat):
        value = fn()
    return (time.perf_counter() - started) / repeat, value


def main() -> None:
    corpus = load_expression_corpus(CORPUS)
    selected = [
        item for item in corpus.formulas
        if item.metadata.get("explicit_packed_policy") == "run"
    ]
    raw = []
    for item in selected:
        expr = item.to_expr()
        support = tuple(item.metadata["semantic_support"])
        fixed = {
            f"x{i}": (i & 1)
            for i in range(item.nominal_n)
            if f"x{i}" not in support
        }
        prep_started = time.perf_counter()
        prepared = prepare_expr_flat_evaluation(expr, support, fixed=fixed)
        prepare_s = time.perf_counter() - prep_started
        expected = eval_expr_flat_bitset(expr, support, fixed=fixed)
        assert prepared.evaluate() == expected
        estimate, _ = per_call(prepared.evaluate, 5)
        repeat = 1000 if estimate < 25e-6 else 250 if estimate < 250e-6 else 40
        for round_index in range(ROUNDS):
            if round_index % 2:
                prepared_s, prepared_value = per_call(prepared.evaluate, repeat)
                legacy_s, legacy_value = per_call(
                    lambda: eval_expr_flat_bitset(expr, support, fixed=fixed), repeat
                )
            else:
                legacy_s, legacy_value = per_call(
                    lambda: eval_expr_flat_bitset(expr, support, fixed=fixed), repeat
                )
                prepared_s, prepared_value = per_call(prepared.evaluate, repeat)
            assert legacy_value == prepared_value == expected
            raw.append({
                "corpus_sha256": corpus.sha256,
                "formula_id": item.formula_id,
                "formula_sha256": item.formula_sha256,
                "family": item.metadata["family"],
                "nominal_n": item.nominal_n,
                "live_k": len(support),
                "round": round_index,
                "repeat": repeat,
                "prepare_us": prepare_s * 1e6,
                "legacy_bind_each_call_us": legacy_s * 1e6,
                "prepared_eval_us": prepared_s * 1e6,
                "legacy_over_prepared": legacy_s / prepared_s,
                "equal": True,
            })
    with RAW.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(raw[0]))
        writer.writeheader()
        writer.writerows(raw)
    summary = []
    for live_k in sorted({row["live_k"] for row in raw}):
        rows = [row for row in raw if row["live_k"] == live_k]
        summary.append({
            "corpus_sha256": corpus.sha256,
            "live_k": live_k,
            "formulas": len({row["formula_id"] for row in rows}),
            "paired_observations": len(rows),
            "all_equal": all(row["equal"] for row in rows),
            "prepare_us_median": statistics.median(row["prepare_us"] for row in rows),
            "legacy_bind_each_call_us_median": statistics.median(
                row["legacy_bind_each_call_us"] for row in rows
            ),
            "prepared_eval_us_median": statistics.median(
                row["prepared_eval_us"] for row in rows
            ),
            "legacy_over_prepared_median": statistics.median(
                row["legacy_over_prepared"] for row in rows
            ),
        })
    with SUMMARY.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print(f"wrote {len(raw)} raw rows and {len(summary)} summary rows; mismatches=0")


if __name__ == "__main__":
    main()
