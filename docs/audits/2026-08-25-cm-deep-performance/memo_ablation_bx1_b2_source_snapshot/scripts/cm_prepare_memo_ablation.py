#!/usr/bin/env python3
"""Paired CM preparation ablation for the redundant identity memo hypothesis.

The sharing-aware builder constructs a structural UID map before lowering and
uses ``memo_by_uid`` while it builds the CM IR.  The current production path
also maintains an id-keyed memo.  This harness compares production compilation
with an otherwise identical build whose id-keyed memo is disabled only after
the UID prepass exists.  It changes no production state and refuses overwrite.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bitset_backend import eval_cm_node_flat  # noqa: E402
from cm_expr_serde import expr_from_json  # noqa: E402
from cm_ir import CMIRBuilder, _BuildState, compile_expr_to_cm_ir  # noqa: E402
from scripts.cm_benchmark_provenance import (  # noqa: E402
    capture_source_snapshot,
    source_hashes,
)
from scripts.cm_deep_performance_audit import (  # noqa: E402
    CORPORA,
    _evaluation_context,
    _sample_records,
)


SOURCE_PATHS = (
    "cm_ir.py",
    "bitset_backend.py",
    "cm_expr_serde.py",
    "scripts/cm_benchmark_provenance.py",
    "scripts/cm_deep_performance_audit.py",
    "scripts/cm_prepare_memo_ablation.py",
)


def _candidate_compile(expr: Any) -> Any:
    """Compile with the structural UID memo but no redundant identity memo."""
    builder = CMIRBuilder(share_aware_flatten=True, build_memo=True)
    uid_by_id, shared_uids = builder._shared_assoc_uids(expr)
    state = _BuildState(None, set(), uid_by_id, shared_uids)
    builder._build_state = state
    try:
        return builder._build_rec(expr, state)
    finally:
        builder._build_state = None


def _paired_samples(
    baseline: Callable[[], Any],
    candidate: Callable[[], Any],
    repetitions: int,
) -> tuple[list[int], list[int], Any, Any]:
    baseline_samples: list[int] = []
    candidate_samples: list[int] = []
    baseline_node = candidate_node = None
    baseline()
    candidate()
    for index in range(repetitions):
        order = ((baseline, baseline_samples), (candidate, candidate_samples))
        if index % 2:
            order = tuple(reversed(order))
        for fn, samples in order:
            started = time.perf_counter_ns()
            node = fn()
            samples.append(time.perf_counter_ns() - started)
            if fn is baseline:
                baseline_node = node
            else:
                candidate_node = node
    return baseline_samples, candidate_samples, baseline_node, candidate_node


def _peak_bytes(fn: Callable[[], Any]) -> tuple[int, Any]:
    tracemalloc.start()
    try:
        node = fn()
        _, peak = tracemalloc.get_traced_memory()
        return int(peak), node
    finally:
        tracemalloc.stop()


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty percentile input")
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def _geomean(values: Sequence[float]) -> float:
    return float(math.exp(statistics.fmean(math.log(value) for value in values)))


def _cluster_key(corpus: str, record: Mapping[str, Any]) -> str:
    circuit = record.get("circuit") or record.get("source_circuit")
    if circuit:
        return f"{corpus}:circuit:{circuit}"
    family = record.get("family") or record.get("operator_family") or "unknown"
    shape = record.get("shape") or record.get("tree_shape") or "unknown"
    return f"{corpus}:family:{family}:{shape}"


def _cluster_interval(rows: Sequence[Mapping[str, Any]], seed: int) -> tuple[float, float]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row["cluster"]), []).append(float(row["ratio"]))
    keys = sorted(grouped)
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(2000):
        sample: list[float] = []
        for _ in keys:
            sample.extend(grouped[rng.choice(keys)])
        draws.append(_geomean(sample))
    return _percentile(draws, 0.025), _percentile(draws, 0.975)


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
    baseline = lambda: compile_expr_to_cm_ir(expr)
    candidate = lambda: _candidate_compile(expr)
    before, after, before_node, after_node = _paired_samples(
        baseline, candidate, repetitions
    )
    if before_node.key != after_node.key:
        raise AssertionError(f"{record.get('id')}: canonical key mismatch")
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
        if peak_before_node.key != peak_after_node.key:
            raise AssertionError(f"{record.get('id')}: allocation-pass key mismatch")
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


def _summaries(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    groups = [("all", list(rows))]
    groups.extend(
        (corpus, [row for row in rows if row["corpus"] == corpus])
        for corpus in sorted({str(row["corpus"]) for row in rows})
    )
    for name, group in groups:
        ratios = [float(row["ratio"]) for row in group]
        memory = [
            float(row["peak_bytes_ratio"])
            for row in group
            if row["peak_bytes_ratio"] is not None
        ]
        low, high = _cluster_interval(group, 20260825)
        output.append(
            {
                "group": name,
                "rows": len(group),
                "candidate_over_baseline_geomean": _geomean(ratios),
                "cluster_interval_95_low": low,
                "cluster_interval_95_high": high,
                "ratio_median": float(statistics.median(ratios)),
                "ratio_p10": _percentile(ratios, 0.10),
                "ratio_p90": _percentile(ratios, 0.90),
                "candidate_faster_rows": sum(value < 1.0 for value in ratios),
                "candidate_slower_rows": sum(value > 1.0 for value in ratios),
                "allocation_rows": len(memory),
                "peak_bytes_ratio_geomean": _geomean(memory) if memory else None,
                "canonical_mismatches": sum(not row["canonical_key_equal"] for row in group),
                "packed_mismatches": sum(not row["packed_output_equal"] for row in group),
            }
        )
    return output


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("smoke", "representative"), default="smoke")
    parser.add_argument("--corpora", default="bx1,b2,epfl")
    parser.add_argument("--repetitions", type=int, default=11)
    parser.add_argument(
        "--skip-allocation",
        action="store_true",
        help="skip per-row tracemalloc; useful for large representative EPFL cones",
    )
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    if args.repetitions < 5 or args.repetitions % 2 == 0:
        parser.error("--repetitions must be an odd integer >= 5")
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
                )
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
        "hypothesis": (
            "The structural UID memo makes the simultaneous id-keyed build memo "
            "redundant in the default sharing-aware compiler."
        ),
        "timing_schedule": "per-formula paired alternating order; one warmup per arm",
        "allocation_window": (
            "skipped"
            if args.skip_allocation
            else "one cold compile per arm under tracemalloc"
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
