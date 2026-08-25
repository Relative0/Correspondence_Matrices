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
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

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
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cmbench/backends/bitset_engine.py",
    "cmbench/output_budget.py",
    "scripts/cm_benchmark_provenance.py",
    "scripts/cm_symmetric_wrapper_followup.py",
)
RATIO_FIELDS = (
    "cm_current_over_cse_flat_current",
    "cm_wrapper_over_cse_flat_current",
    "cm_current_over_raw_current",
    "cm_wrapper_over_raw_current",
    "cse_flat_current_over_raw_current",
)
PRIMARY_RATIO_FIELD = "cm_current_over_cse_flat_current"
BOOTSTRAP_REPETITIONS = 10_000
# The current-policy timing block has four arms and the explicit block has six.
# Rotate + reverse needs 2*n rounds per block, so 24 balances both schedules.
BALANCED_ROUNDS_MULTIPLE = math.lcm(2 * 4, 2 * 6)


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


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    index = fraction * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _formula_log_ratios(
    rows: Sequence[Mapping[str, Any]], field: str
) -> dict[tuple[str, str], float]:
    """Collapse paired timing ratios to one log-ratio per frozen formula."""
    by_formula: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        ratio = float(row[field])
        if not math.isfinite(ratio) or ratio <= 0:
            raise ValueError(f"{field} must contain finite positive ratios")
        key = (str(row["corpus"]), str(row["id"]))
        by_formula.setdefault(key, []).append(math.log(ratio))
    return {
        key: statistics.fmean(log_ratios)
        for key, log_ratios in by_formula.items()
    }


def _paired_formula_cluster_stats(
    rows: Sequence[Mapping[str, Any]],
    field: str,
    *,
    seed_label: str,
    repetitions: int = BOOTSTRAP_REPETITIONS,
) -> dict[str, Any]:
    """Estimate a paired geomean and percentile CI by frozen formula.

    Each row is already a paired numerator/denominator timing ratio. Repeated
    ambient-width observations for one formula remain together: their mean log
    ratio is one cluster contribution, and formulas are resampled uniformly.
    """
    if repetitions < 1:
        raise ValueError("bootstrap repetitions must be positive")
    formula_logs = _formula_log_ratios(rows, field)
    if not formula_logs:
        return {
            "row_count": 0,
            "formula_cluster_count": 0,
            "row_weighted_geomean": float("nan"),
            "paired_formula_cluster_geomean": float("nan"),
            "paired_formula_cluster_bootstrap_ci95_low": float("nan"),
            "paired_formula_cluster_bootstrap_ci95_high": float("nan"),
            "bootstrap_repetitions": repetitions,
        }
    cluster_values = [formula_logs[key] for key in sorted(formula_logs)]
    point = math.exp(statistics.fmean(cluster_values))
    seed = int.from_bytes(
        hashlib.sha256(seed_label.encode("utf-8")).digest()[:8], "big"
    )
    rng = random.Random(seed)
    cluster_count = len(cluster_values)
    estimates = [
        math.exp(
            math.fsum(rng.choices(cluster_values, k=cluster_count)) / cluster_count
        )
        for _ in range(repetitions)
    ]
    row_logs = [math.log(float(row[field])) for row in rows]
    return {
        "row_count": len(rows),
        "formula_cluster_count": len(cluster_values),
        "row_weighted_geomean": math.exp(statistics.fmean(row_logs)),
        "paired_formula_cluster_geomean": point,
        "paired_formula_cluster_bootstrap_ci95_low": _percentile(
            estimates, 0.025
        ),
        "paired_formula_cluster_bootstrap_ci95_high": _percentile(
            estimates, 0.975
        ),
        "bootstrap_repetitions": repetitions,
    }


def _inference(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build headline and stratified paired formula-cluster inference rows."""
    scopes: list[tuple[str, str, str, list[Mapping[str, Any]]]] = [
        ("overall", "all", "all", list(rows))
    ]
    for corpus in sorted({str(row["corpus"]) for row in rows}):
        scopes.append(
            (
                "corpus",
                corpus,
                "all",
                [row for row in rows if str(row["corpus"]) == corpus],
            )
        )
    for live_k in sorted({int(row["live_k"]) for row in rows}):
        scopes.append(
            (
                "live_k",
                "all",
                str(live_k),
                [row for row in rows if int(row["live_k"]) == live_k],
            )
        )
    for corpus, live_k in sorted(
        {(str(row["corpus"]), int(row["live_k"])) for row in rows}
    ):
        scopes.append(
            (
                "corpus_live_k",
                corpus,
                str(live_k),
                [
                    row
                    for row in rows
                    if str(row["corpus"]) == corpus
                    and int(row["live_k"]) == live_k
                ],
            )
        )

    output = []
    for scope, corpus, live_k, subset in scopes:
        # The primary CM/CSE comparison is stratified throughout. Secondary
        # wrapper/raw ablations receive an overall interval without multiplying
        # bootstrap work or implying they are co-primary hypotheses.
        fields = RATIO_FIELDS if scope == "overall" else (PRIMARY_RATIO_FIELD,)
        for field in fields:
            stats = _paired_formula_cluster_stats(
                subset,
                field,
                seed_label=f"symmetric:{scope}:{corpus}:{live_k}:{field}",
            )
            output.append(
                {
                    "scope": scope,
                    "corpus": corpus,
                    "live_k": live_k,
                    "metric": field,
                    **stats,
                }
            )
    return output


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
        for field in RATIO_FIELDS:
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
    parser.add_argument("--rounds", type=int, default=BALANCED_ROUNDS_MULTIPLE)
    args = parser.parse_args()
    if args.rounds < BALANCED_ROUNDS_MULTIPLE or args.rounds % BALANCED_ROUNDS_MULTIPLE:
        parser.error(
            f"--rounds must be a positive multiple of {BALANCED_ROUNDS_MULTIPLE} "
            "to exactly balance both timing schedules"
        )
    paths = {
        "raw": args.output_prefix.with_name(args.output_prefix.name + "_raw.csv"),
        "summary": args.output_prefix.with_name(args.output_prefix.name + "_summary.csv"),
        "inference": args.output_prefix.with_name(
            args.output_prefix.name + "_inference.csv"
        ),
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
    inference = _inference(rows)
    headline = next(
        row
        for row in inference
        if row["scope"] == "overall"
        and row["metric"] == PRIMARY_RATIO_FIELD
    )
    source_snapshot = capture_source_snapshot(ROOT, snapshot_dir, SOURCE_PATHS)
    audit = {
        "protocol": (
            "exactly counterbalanced current-policy bare CM vs sharing-aware "
            "CSE-flat primary; raw-AST ablation and CM wrapper reported separately"
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
        "formula_count": len({(row["corpus"], row["id"]) for row in rows}),
        "packed_mismatch_count": 0,
        "statistical_inference": {
            "method": (
                "paired nonparametric percentile bootstrap of formula-level "
                "mean log timing ratios"
            ),
            "cluster_key": ["corpus", "id"],
            "within_formula_aggregation": "arithmetic mean of row log ratios",
            "formula_weighting": "one equal-weight contribution per formula",
            "confidence_level": 0.95,
            "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
            "deterministic_seed": "SHA-256 of scope and metric label",
            "uncertainty_target": (
                "formula-to-formula variation conditional on this machine and run"
            ),
            "does_not_model": [
                "between-run timing variation",
                "between-machine timing variation",
            ],
            "headline": headline,
        },
        "acceptance": {"pass": all(row["packed_equal_all_arms"] for row in rows)},
    }
    _csv(paths["raw"], rows)
    _csv(paths["summary"], summary)
    _csv(paths["inference"], inference)
    paths["audit"].write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"paths": {key: str(value) for key, value in paths.items()}, "acceptance": audit["acceptance"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
