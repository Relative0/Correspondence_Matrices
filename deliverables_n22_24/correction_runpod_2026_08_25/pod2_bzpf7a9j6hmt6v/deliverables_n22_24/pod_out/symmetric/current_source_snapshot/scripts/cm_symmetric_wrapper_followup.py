#!/usr/bin/env python3
"""Matched successor to the legacy B2/B4 wrapper comparisons.

CM, sharing-aware CSE-flat, and raw-AST ablation arms use the same current
support-width policy. Bare selected kernels are the primary matched boundary;
the public CM wrapper is reported separately so its admission/result overhead
cannot be mistaken for a kernel difference. Frozen B2 and B4 formula corpora
are replayed without regeneration.
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
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bitset_backend import (  # noqa: E402
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_flat_cse,
    eval_expr_flat_bitset,
    eval_expr_words_cse,
    eval_expr_words_bitset,
    get_expr_cse_program,
    get_expr_flat_program,
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json  # noqa: E402
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate  # noqa: E402
from cmbench.backends.bitset_engine import (  # noqa: E402
    WORDS_AUTO_MIN_VARS,
    select_cm_node_engine,
    select_raw_ast_engine,
)
from scripts.cm_benchmark_provenance import (  # noqa: E402
    capture_source_snapshot,
    source_hashes,
)

B2 = ROOT / "deliverables_n22_24/b2_wrapper_2026_08_03/CM_b2_wrapper_corpus_2026_08_03.jsonl"
B4 = ROOT / "deliverables_n22_24/b4_sweep_2026_08_03/CM_b4_headline_corpus_2026_08_03.jsonl"
AMBIENT_N = (16, 20, 24)
SOURCE_PATHS = (
    "bitset_backend.py",
    "cm_ir.py",
    "cmbench/backends/bitset_engine.py",
    "scripts/cm_benchmark_provenance.py",
    "scripts/cm_symmetric_wrapper_followup.py",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _records(path: Path) -> list[dict]:
    return [
        row for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
        if "expression_v2" in row
    ]


def _balanced(
    functions: dict[str, Callable[[], int]], *, batch: int, rounds: int
) -> dict[str, float]:
    names = tuple(functions)
    samples = {name: [] for name in names}
    for index in range(rounds):
        offset = index % len(names)
        order = names[offset:] + names[:offset]
        if (index // len(names)) % 2:
            order = tuple(reversed(order))
        for name in order:
            fn = functions[name]
            start = time.perf_counter_ns()
            for _ in range(batch):
                fn()
            samples[name].append((time.perf_counter_ns() - start) / batch)
    return {
        name: float(statistics.median(values)) for name, values in samples.items()
    }


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
    cm_selection = select_cm_node_engine(
        live_k=k, words_requested=True, flat_requested=True
    )

    def cm_current() -> int:
        return cm_selection.evaluate_node(node, support, fixed=fixed)

    def cm_wrapper() -> int:
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

    def cse_flat_current() -> int:
        if k >= WORDS_AUTO_MIN_VARS:
            return eval_expr_words_cse(
                expr, support, fixed=fixed, flatten=True
            )
        return eval_expr_flat_cse(expr, support, fixed=fixed, flatten=True)

    values = {
        "cm_current": cm_current(),
        "cm_wrapper": cm_wrapper(),
        "cse_flat_current": cse_flat_current(),
        "raw_current": raw_current(),
        "cm_flat": eval_cm_node_flat(node, support, fixed=fixed),
        "cm_words": eval_cm_node_words(node, support, fixed=fixed),
        "raw_flat": eval_expr_flat_bitset(expr, support, fixed=fixed),
        "raw_words": eval_expr_words_bitset(expr, support, fixed=fixed),
        "cse_flat_flat": eval_expr_flat_cse(
            expr, support, fixed=fixed, flatten=True
        ),
        "cse_flat_words": eval_expr_words_cse(
            expr, support, fixed=fixed, flatten=True
        ),
    }
    if len(set(values.values())) != 1:
        raise AssertionError(f"packed mismatch: {corpus}/{record['id']}/n={ambient_n}")
    output_bytes = max(1, (1 << k) // 8)
    expected = record.get("truth_sha256")
    actual = hashlib.sha256(values["cm_current"].to_bytes(output_bytes, "little")).hexdigest()
    if not isinstance(expected, str) or not expected:
        raise AssertionError(
            f"missing frozen truth digest: {corpus}/{record['id']}/n={ambient_n}"
        )
    if actual != expected:
        raise AssertionError(f"truth drift: {corpus}/{record['id']}/n={ambient_n}")

    cm_metrics = program_metrics(get_flat_program(node))
    cse_flat_metrics = program_metrics(get_expr_cse_program(expr, flatten=True))
    raw_metrics = program_metrics(get_expr_flat_program(expr))

    batch = _batch(k)
    current_ns = _balanced(
        {
            "cm_current": cm_current,
            "cm_wrapper": cm_wrapper,
            "cse_flat_current": cse_flat_current,
            "raw_current": raw_current,
        },
        batch=batch,
        rounds=rounds,
    )
    explicit_ns = _balanced(
        {
            "cm_flat": lambda: eval_cm_node_flat(node, support, fixed=fixed),
            "cm_words": lambda: eval_cm_node_words(node, support, fixed=fixed),
            "cse_flat_flat": lambda: eval_expr_flat_cse(
                expr, support, fixed=fixed, flatten=True
            ),
            "cse_flat_words": lambda: eval_expr_words_cse(
                expr, support, fixed=fixed, flatten=True
            ),
            "raw_flat": lambda: eval_expr_flat_bitset(expr, support, fixed=fixed),
            "raw_words": lambda: eval_expr_words_bitset(expr, support, fixed=fixed),
        },
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
        "cm_instructions": cm_metrics["flat_instructions"],
        "cse_flat_instructions": cse_flat_metrics["flat_instructions"],
        "raw_instructions": raw_metrics["flat_instructions"],
        "cm_executed_bigint_ops": cm_metrics["executed_bigint_ops"],
        "cse_flat_executed_bigint_ops": cse_flat_metrics["executed_bigint_ops"],
        "raw_executed_bigint_ops": raw_metrics["executed_bigint_ops"],
        "cm_executed_word_ops": cm_metrics["executed_word_ops"],
        "cse_flat_executed_word_ops": cse_flat_metrics["executed_word_ops"],
        "raw_executed_word_ops": raw_metrics["executed_word_ops"],
        "cm_current_ns_median": current_ns["cm_current"],
        "cm_wrapper_ns_median": current_ns["cm_wrapper"],
        "cse_flat_current_ns_median": current_ns["cse_flat_current"],
        "raw_current_ns_median": current_ns["raw_current"],
        "cm_current_over_cse_flat_current": (
            current_ns["cm_current"] / current_ns["cse_flat_current"]
        ),
        "cm_wrapper_over_cse_flat_current": (
            current_ns["cm_wrapper"] / current_ns["cse_flat_current"]
        ),
        "cm_current_over_raw_current": (
            current_ns["cm_current"] / current_ns["raw_current"]
        ),
        "cm_wrapper_over_raw_current": (
            current_ns["cm_wrapper"] / current_ns["raw_current"]
        ),
        "cse_flat_current_over_raw_current": (
            current_ns["cse_flat_current"] / current_ns["raw_current"]
        ),
        "cm_flat_ns_median": explicit_ns["cm_flat"],
        "cm_words_ns_median": explicit_ns["cm_words"],
        "cse_flat_flat_ns_median": explicit_ns["cse_flat_flat"],
        "cse_flat_words_ns_median": explicit_ns["cse_flat_words"],
        "raw_flat_ns_median": explicit_ns["raw_flat"],
        "raw_words_ns_median": explicit_ns["raw_words"],
        "truth_sha256_expected": expected,
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
        result = {
            "corpus": corpus,
            "live_k": k,
            "ambient_n": ambient_n,
            "current_engine": subset[0]["current_engine"],
            "n": len(subset),
        }
        for field in (
            "cm_current_over_cse_flat_current",
            "cm_wrapper_over_cse_flat_current",
            "cm_current_over_raw_current",
            "cm_wrapper_over_raw_current",
            "cse_flat_current_over_raw_current",
        ):
            values = [row[field] for row in subset]
            result[f"{field}_geomean"] = math.exp(
                statistics.mean(math.log(value) for value in values)
            )
            result[f"{field}_median"] = statistics.median(values)
            result[f"{field}_min"] = min(values)
            result[f"{field}_max"] = max(values)
        output.append(result)
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
    snapshot_dir = args.output_prefix.with_name(
        args.output_prefix.name + "_source_snapshot"
    )
    existing = [str(path) for path in (*paths.values(), snapshot_dir) if path.exists()]
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
    source_snapshot = capture_source_snapshot(ROOT, snapshot_dir, SOURCE_PATHS)
    audit = {
        "protocol": (
            "balanced current-policy bare CM vs sharing-aware CSE-flat primary; "
            "raw-AST ablation and CM wrapper reported separately"
        ),
        "primary_comparator": "sharing-aware structural CSE with flatten=True",
        "raw_ast_status": "ablation only; not the strongest generic comparator",
        "words_auto_min_vars": WORDS_AUTO_MIN_VARS,
        "corpus_sha256": {"b2": _sha(B2), "b4": _sha(B4)},
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "source_sha256": source_hashes(ROOT, SOURCE_PATHS),
            "source_snapshot": source_snapshot,
        },
        "row_count": len(rows),
        "packed_mismatch_count": 0,
        "acceptance": {"pass": all(row["packed_equal_all_arms"] for row in rows)},
    }
    _csv(paths["raw"], rows)
    _csv(paths["summary"], summary)
    paths["audit"].write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"paths": {key: str(value) for key, value in paths.items()}, "acceptance": audit["acceptance"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
