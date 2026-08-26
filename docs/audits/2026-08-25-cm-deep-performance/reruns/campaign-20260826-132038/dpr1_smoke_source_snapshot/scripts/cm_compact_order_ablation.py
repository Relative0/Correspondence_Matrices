#!/usr/bin/env python3
"""Paired DP-R1 ablation for builder-local compact canonical ordering."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bitset_backend import eval_cm_node_flat  # noqa: E402
from cm_expr_serde import expr_from_json  # noqa: E402
from cm_ir import CMIRBuilder  # noqa: E402
from scripts.cm_benchmark_provenance import (  # noqa: E402
    capture_source_snapshot,
    source_hashes,
)
from scripts.cm_deep_performance_audit import (  # noqa: E402
    CORPORA,
    _evaluation_context,
    _sample_records,
)
from scripts.cm_prepare_memo_ablation import (  # noqa: E402
    _cluster_key,
    _dag_signature,
    _paired_samples,
    _peak_bytes,
    _percentile,
    _summaries,
    _write_csv,
)


SOURCE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "scripts/cm_benchmark_provenance.py",
    "scripts/cm_compact_order_ablation.py",
    "scripts/cm_deep_performance_audit.py",
    "scripts/cm_prepare_memo_ablation.py",
)


def _compile(expr: Any, compact: bool) -> Any:
    return CMIRBuilder(
        share_aware_flatten=True,
        build_memo=True,
        compact_canonical_order=compact,
    ).build(expr)


def _measure_record(
    corpus: str,
    record: Mapping[str, Any],
    repetitions: int,
    measure_allocation: bool,
) -> dict[str, Any]:
    expr = expr_from_json(record["expression_v2"])
    live_k = int(
        record.get("live_k")
        or record.get("stratum_live_k")
        or record.get("sem_support_size")
    )
    baseline = lambda: _compile(expr, False)
    candidate = lambda: _compile(expr, True)
    before, after, before_node, after_node = _paired_samples(
        baseline, candidate, repetitions
    )
    if _dag_signature(before_node) != _dag_signature(after_node):
        raise AssertionError(f"{record.get('id')}: ordered canonical DAG mismatch")
    if before_node.vars != after_node.vars:
        raise AssertionError(f"{record.get('id')}: live-variable mismatch")
    variables, fixed = _evaluation_context(corpus, record, expr, live_k)
    before_bits = eval_cm_node_flat(before_node, variables, fixed=fixed)
    after_bits = eval_cm_node_flat(after_node, variables, fixed=fixed)
    if before_bits != after_bits:
        raise AssertionError(f"{record.get('id')}: exact packed output mismatch")

    before_peak = after_peak = None
    if measure_allocation:
        before_peak, peak_before_node = _peak_bytes(baseline)
        after_peak, peak_after_node = _peak_bytes(candidate)
        if _dag_signature(peak_before_node) != _dag_signature(peak_after_node):
            raise AssertionError(f"{record.get('id')}: allocation-pass DAG mismatch")

    import statistics

    before_median = float(statistics.median(before))
    after_median = float(statistics.median(after))
    return {
        "corpus": corpus,
        "role": "tuning" if corpus == "bx1" else "validation_reused",
        "id": record.get("id"),
        "cluster": _cluster_key(corpus, record),
        "live_k": live_k,
        "repetitions": repetitions,
        "baseline_ns_median": before_median,
        "candidate_ns_median": after_median,
        "ratio": after_median / before_median,
        "baseline_ns_p10": _percentile(before, 0.10),
        "baseline_ns_p90": _percentile(before, 0.90),
        "candidate_ns_p10": _percentile(after, 0.10),
        "candidate_ns_p90": _percentile(after, 0.90),
        "baseline_peak_bytes": before_peak,
        "candidate_peak_bytes": after_peak,
        "peak_bytes_ratio": after_peak / before_peak if before_peak else None,
        "canonical_key_equal": True,
        "packed_output_equal": True,
        "packed_sha256": hashlib.sha256(
            int(after_bits).to_bytes(max(1, (1 << live_k) // 8), "little")
        ).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("smoke", "representative"), default="smoke")
    parser.add_argument("--corpora", default="bx1,b2,epfl")
    parser.add_argument("--repetitions", type=int, default=11)
    parser.add_argument("--skip-allocation", action="store_true")
    parser.add_argument("--record-start", type=int, default=0)
    parser.add_argument("--record-limit", type=int)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    if args.repetitions < 5 or args.repetitions % 2 == 0:
        parser.error("--repetitions must be an odd integer >= 5")
    if args.record_start < 0 or (args.record_limit is not None and args.record_limit < 1):
        parser.error("record range must have start >= 0 and limit >= 1")
    corpora = tuple(item.strip() for item in args.corpora.split(",") if item.strip())
    unknown = set(corpora) - set(CORPORA)
    if unknown:
        parser.error(f"unknown corpora: {sorted(unknown)}")

    prefix = args.output_prefix
    raw_path = prefix.with_name(prefix.name + "_raw.csv")
    summary_path = prefix.with_name(prefix.name + "_summary.json")
    environment_path = prefix.with_name(prefix.name + "_environment.json")
    snapshot_path = prefix.with_name(prefix.name + "_source_snapshot")
    existing = [
        str(path)
        for path in (raw_path, summary_path, environment_path, snapshot_path)
        if path.exists()
    ]
    if existing:
        parser.error("refusing to overwrite existing outputs: " + ", ".join(existing))
    prefix.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for corpus in corpora:
        records = _sample_records(corpus, args.suite)
        stop = None if args.record_limit is None else args.record_start + args.record_limit
        records = records[args.record_start:stop]
        for index, record in enumerate(records, 1):
            row = _measure_record(
                corpus, record, args.repetitions, not args.skip_allocation
            )
            rows.append(row)
            print(
                f"{corpus} {index}/{len(records)} {row['id']}: "
                f"candidate/baseline={row['ratio']:.3f}, "
                + (
                    f"peak={row['peak_bytes_ratio']:.3f}"
                    if row["peak_bytes_ratio"] is not None
                    else "peak=skipped"
                ),
                flush=True,
            )

    summaries = _summaries(rows)
    environment = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "suite": args.suite,
        "corpora": corpora,
        "repetitions": args.repetitions,
        "record_start": args.record_start,
        "record_limit": args.record_limit,
        "hypothesis": (
            "Exact immutable builder-local order labels make canonical child "
            "ordering cheaper than repeated deep CMNode.key comparison."
        ),
        "timing_schedule": "per-formula paired alternating order; one warmup per arm",
        "allocation_window": (
            "skipped" if args.skip_allocation else "one cold compile per arm under tracemalloc"
        ),
        "source_sha256": source_hashes(REPO_ROOT, SOURCE_PATHS),
        "corpus_sha256": {
            name: hashlib.sha256(CORPORA[name].read_bytes()).hexdigest()
            for name in corpora
        },
    }
    environment["source_snapshot"] = capture_source_snapshot(
        REPO_ROOT, snapshot_path, SOURCE_PATHS
    )
    _write_csv(raw_path, rows)
    summary_path.write_text(
        json.dumps({"environment": environment, "summaries": summaries}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    environment_path.write_text(
        json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summaries, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
