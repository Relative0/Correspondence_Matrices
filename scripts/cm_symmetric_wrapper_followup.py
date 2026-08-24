#!/usr/bin/env python3
"""Symmetric successor to the legacy B2/B4 wrapper comparisons.

Both sides use the current support-width selector.  The CM arm includes the
public no-reinflate wrapper; the raw-AST arm calls the selected raw evaluator.
Frozen B2 and B4 formula corpora are replayed without regeneration.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bitset_backend import (  # noqa: E402
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_flat_bitset,
    eval_expr_words_bitset,
)
from cm_expr_serde import expr_from_json  # noqa: E402
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate  # noqa: E402
from cmbench.backends.bitset_engine import (  # noqa: E402
    WORDS_AUTO_MIN_VARS,
    select_raw_ast_engine,
)

B2 = ROOT / "deliverables_n22_24/b2_wrapper_2026_08_03/CM_b2_wrapper_corpus_2026_08_03.jsonl"
B4 = ROOT / "deliverables_n22_24/b4_sweep_2026_08_03/CM_b4_headline_corpus_2026_08_03.jsonl"
AMBIENT_N = (16, 20, 24)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _records(path: Path) -> list[dict]:
    return [
        row for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
        if "expression_v2" in row
    ]


def _paired(left, right, *, batch: int, rounds: int) -> tuple[float, float]:
    ls, rs = [], []
    for index in range(rounds):
        order = ((left, ls), (right, rs)) if index % 2 == 0 else ((right, rs), (left, ls))
        for fn, samples in order:
            start = time.perf_counter_ns()
            for _ in range(batch):
                fn()
            samples.append((time.perf_counter_ns() - start) / batch)
    return float(statistics.median(ls)), float(statistics.median(rs))


def _batch(k: int) -> int:
    return 100 if k <= 8 else 25 if k <= 12 else 5


def _measure(corpus: str, record: dict, ambient_n: int, rounds: int) -> dict:
    k = int(record.get("stratum_live_k") or record["live_k"])
    expr = expr_from_json(record["expression_v2"])
    node = compile_expr_to_cm_ir(expr)
    support = tuple(f"x{i}" for i in range(k))
    fixed = {f"x{i}": 0 for i in range(k, ambient_n)}
    raw_selection = select_raw_ast_engine(
        live_k=k, words_requested=True, flat_requested=True
    )

    def cm_current() -> int:
        result = materialize_hybrid_no_reinflate(
            node,
            support,
            fixed=fixed,
            hybrid_threshold=16,
            allow_reduced_output=False,
            max_full_output_vars=16,
            flat_eval=True,
            words_eval=True,
        )
        return int(result.bits)

    def raw_current() -> int:
        return raw_selection.evaluate_expr(expr, support, fixed=fixed)

    values = {
        "cm_current": cm_current(),
        "raw_current": raw_current(),
        "cm_flat": eval_cm_node_flat(node, support, fixed=fixed),
        "cm_words": eval_cm_node_words(node, support, fixed=fixed),
        "raw_flat": eval_expr_flat_bitset(expr, support, fixed=fixed),
        "raw_words": eval_expr_words_bitset(expr, support, fixed=fixed),
    }
    if len(set(values.values())) != 1:
        raise AssertionError(f"packed mismatch: {corpus}/{record['id']}/n={ambient_n}")
    output_bytes = max(1, (1 << k) // 8)
    expected = record.get("truth_sha256")
    actual = hashlib.sha256(values["cm_current"].to_bytes(output_bytes, "little")).hexdigest()
    if expected and actual != expected:
        raise AssertionError(f"truth drift: {corpus}/{record['id']}/n={ambient_n}")

    batch = _batch(k)
    cm_ns, raw_ns = _paired(cm_current, raw_current, batch=batch, rounds=rounds)
    cm_flat_ns, cm_words_ns = _paired(
        lambda: eval_cm_node_flat(node, support, fixed=fixed),
        lambda: eval_cm_node_words(node, support, fixed=fixed),
        batch=batch,
        rounds=rounds,
    )
    raw_flat_ns, raw_words_ns = _paired(
        lambda: eval_expr_flat_bitset(expr, support, fixed=fixed),
        lambda: eval_expr_words_bitset(expr, support, fixed=fixed),
        batch=batch,
        rounds=rounds,
    )
    return {
        "corpus": corpus,
        "id": record["id"],
        "live_k": k,
        "ambient_n": ambient_n,
        "op_family": record.get("op_family"),
        "shape": record.get("shape"),
        "current_engine": raw_selection.kind.removeprefix("raw_ast_"),
        "cm_wrapper_ns_median": cm_ns,
        "raw_current_ns_median": raw_ns,
        "cm_wrapper_over_raw_current": cm_ns / raw_ns,
        "cm_flat_ns_median": cm_flat_ns,
        "cm_words_ns_median": cm_words_ns,
        "raw_flat_ns_median": raw_flat_ns,
        "raw_words_ns_median": raw_words_ns,
        "packed_sha256": actual,
        "packed_equal_all_arms": True,
        "batch": batch,
        "rounds": rounds,
    }


def _summary(rows: list[dict]) -> list[dict]:
    output = []
    groups = sorted({(row["corpus"], row["live_k"], row["ambient_n"]) for row in rows})
    for corpus, k, ambient_n in groups:
        subset = [row for row in rows if (row["corpus"], row["live_k"], row["ambient_n"]) == (corpus, k, ambient_n)]
        ratios = [row["cm_wrapper_over_raw_current"] for row in subset]
        output.append({
            "corpus": corpus,
            "live_k": k,
            "ambient_n": ambient_n,
            "current_engine": subset[0]["current_engine"],
            "n": len(subset),
            "ratio_geomean": math.exp(statistics.mean(math.log(value) for value in ratios)),
            "ratio_median": statistics.median(ratios),
            "ratio_min": min(ratios),
            "ratio_max": max(ratios),
        })
    return output


def _csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-prefix", required=True, type=Path)
    parser.add_argument("--rounds", type=int, default=7)
    args = parser.parse_args()
    if args.rounds < 3:
        parser.error("--rounds must be >= 3")
    paths = {
        "raw": args.output_prefix.with_name(args.output_prefix.name + "_raw.csv"),
        "summary": args.output_prefix.with_name(args.output_prefix.name + "_summary.csv"),
        "audit": args.output_prefix.with_name(args.output_prefix.name + "_audit.json"),
    }
    existing = [str(path) for path in paths.values() if path.exists()]
    if existing:
        parser.error("refusing to overwrite: " + ", ".join(existing))
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for record in _records(B2):
        rows.append(_measure("b2", record, int(record["stratum_live_k"]), args.rounds))
    for record in _records(B4):
        for ambient_n in AMBIENT_N:
            rows.append(_measure("b4", record, ambient_n, args.rounds))
    summary = _summary(rows)
    _csv(paths["raw"], rows)
    _csv(paths["summary"], summary)
    audit = {
        "protocol": "symmetric current-policy CM wrapper vs raw-AST selector; paired alternating medians",
        "words_auto_min_vars": WORDS_AUTO_MIN_VARS,
        "corpus_sha256": {"b2": _sha(B2), "b4": _sha(B4)},
        "environment": {"python": sys.version, "platform": platform.platform()},
        "row_count": len(rows),
        "packed_mismatch_count": 0,
        "acceptance": {"pass": all(row["packed_equal_all_arms"] for row in rows)},
    }
    paths["audit"].write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"paths": {key: str(value) for key, value in paths.items()}, "acceptance": audit["acceptance"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
