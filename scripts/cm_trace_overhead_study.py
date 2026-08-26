#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import time
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_exprlib import And, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate
from cmbench.output_budget import OutputBudget
from cmbench.reporting.provenance import sha256_file
from cmbench.tracing.integration import trace_single_expression_result
from cmbench.tracing.replay import summarize_trace_files, write_json_exclusive
from cmbench.tracing.sink import JsonlTraceSink, NullTraceSink


class SamplingContext:
    def __init__(self, trace_sink: JsonlTraceSink, sample_every: int) -> None:
        self.trace_sink = trace_sink
        self.config = SimpleNamespace(cm_trace_sample_every=sample_every)
        self._counter_by_stream: dict[str, int] = {}

    def should_trace(self, stream: str) -> bool:
        count = self._counter_by_stream.get(stream, 0)
        self._counter_by_stream[stream] = count + 1
        return count % self.config.cm_trace_sample_every == 0


def build_expr(n_vars: int):
    expr = Xor(Var(0), Not(Var(1)))
    for index in range(2, n_vars):
        leaf = Var(index)
        previous = Var(index - 1)
        expr = Xor(And(expr, Or(leaf, previous)), Not(And(leaf, previous)))
    return expr


def run_workload(expr: Any, n_vars: int) -> tuple[int, float, float, float]:
    compile_started = time.perf_counter()
    node = compile_expr_to_cm_ir(expr, reuse_cache=False, persistent_cache=False)
    compile_s = time.perf_counter() - compile_started
    evaluate_started = time.perf_counter()
    result = materialize_hybrid_no_reinflate(
        node,
        [f"x{i}" for i in range(n_vars)],
        fixed={},
        hybrid_threshold=16,
        words_eval=(n_vars >= 16),
        allow_reduced_output=False,
        max_full_output_vars=16,
        output_budget=OutputBudget(
            max_output_vars=16,
            max_output_bytes=1 << 16,
            max_temporary_bytes=1 << 24,
            allow_reduced_output=False,
        ),
    )
    evaluate_s = time.perf_counter() - evaluate_started
    if result.bits is None:
        raise AssertionError("overhead study expected packed output")
    return int(result.bits), compile_s, evaluate_s, compile_s + evaluate_s


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    position = fraction * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def write_csv_exclusive(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Paired metrics-trace overhead study.")
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--supports", default="8,12,16")
    parser.add_argument("--rounds", type=int, default=101)
    parser.add_argument("--sample-every", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    supports = [int(part) for part in args.supports.split(",") if part]
    if args.rounds < 3:
        raise ValueError("rounds must be >= 3")
    if args.sample_every < 1:
        raise ValueError("sample-every must be >= 1")
    prefix = Path(args.output_prefix)
    raw_path = prefix.with_name(prefix.name + "_raw.csv")
    summary_path = prefix.with_name(prefix.name + "_summary.json")
    trace_path = prefix.with_name(prefix.name + "_events.jsonl")
    audit_path = prefix.with_name(prefix.name + "_trace_audit.json")
    for path in (raw_path, summary_path, trace_path, audit_path):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite: {path}")
    trace_sink = JsonlTraceSink(trace_path, max_bytes=1 << 25, max_files=1, flush_every=64)
    trace_ctx = SamplingContext(trace_sink, args.sample_every)
    null_ctx = SimpleNamespace(trace_sink=NullTraceSink())
    rows: list[dict[str, Any]] = []
    exact_mismatches = 0
    emitted_events_before = trace_sink.stats()["events_written"]
    for n_vars in supports:
        expr = build_expr(n_vars)
        structural_identity = hashlib.sha256(repr(expr).encode("utf-8")).hexdigest()
        warm_a = run_workload(expr, n_vars)[0]
        warm_b = run_workload(expr, n_vars)[0]
        if warm_a != warm_b:
            raise AssertionError("warmup output mismatch")
        for round_index in range(args.rounds):
            order = ("null", "trace") if round_index % 2 == 0 else ("trace", "null")
            results: dict[str, tuple[int, float, float, float, float]] = {}
            for arm in order:
                started = time.perf_counter()
                bits, compile_s, evaluate_s, backend_total_s = run_workload(expr, n_vars)
                row = {
                    "n_vars": n_vars,
                    "trial": round_index,
                    "expr_unique_var_count": n_vars,
                    "expr_structural_hash_if_available": structural_identity,
                    "cm_hybrid_no_reinflate_time_s": backend_total_s,
                    "cm_hybrid_no_reinflate_exec_only_time_s": evaluate_s,
                    "cm_hybrid_no_reinflate_ir_compile_time_s": compile_s,
                    "cm_hybrid_no_reinflate_ok": True,
                }
                ctx = trace_ctx if arm == "trace" else null_ctx
                trace_single_expression_result(ctx, expr, row, workload_id=f"overhead:{n_vars}:{round_index}")
                wrapper_total_s = time.perf_counter() - started
                results[arm] = (bits, compile_s, evaluate_s, backend_total_s, wrapper_total_s)
            if results["null"][0] != results["trace"][0]:
                exact_mismatches += 1
            null_total = results["null"][4]
            trace_total = results["trace"][4]
            rows.append(
                {
                    "n_vars": n_vars,
                    "round": round_index,
                    "order": "null-trace" if order[0] == "null" else "trace-null",
                    "null_backend_total_s": results["null"][3],
                    "trace_backend_total_s": results["trace"][3],
                    "null_wrapper_total_s": null_total,
                    "trace_wrapper_total_s": trace_total,
                    "trace_over_null_ratio": trace_total / null_total,
                    "trace_minus_null_s": trace_total - null_total,
                    "exact_match": results["null"][0] == results["trace"][0],
                }
            )
    close_started = time.perf_counter()
    trace_sink.close()
    close_s = time.perf_counter() - close_started
    stats = trace_sink.stats()
    emitted_events = int(stats["events_written"]) - int(emitted_events_before)
    trace_audit = summarize_trace_files([trace_path])
    write_csv_exclusive(raw_path, rows)
    ratios = [float(row["trace_over_null_ratio"]) for row in rows]
    deltas = [float(row["trace_minus_null_s"]) for row in rows]
    per_event_s = (sum(deltas) + close_s) / emitted_events if emitted_events else None
    case_summaries = []
    for n_vars in supports:
        case_rows = [row for row in rows if row["n_vars"] == n_vars]
        case_ratios = [float(row["trace_over_null_ratio"]) for row in case_rows]
        case_deltas = [float(row["trace_minus_null_s"]) for row in case_rows]
        case_summaries.append(
            {
                "n_vars": n_vars,
                "rows": len(case_rows),
                "ratio_median": statistics.median(case_ratios),
                "ratio_p25": percentile(case_ratios, 0.25),
                "ratio_p75": percentile(case_ratios, 0.75),
                "delta_median_s": statistics.median(case_deltas),
            }
        )
    summary = {
        "protocol": "paired_round_robin",
        "supports": supports,
        "rounds_per_case": args.rounds,
        "sample_every": args.sample_every,
        "rows": len(rows),
        "exact_mismatches": exact_mismatches,
        "trace_events_charged": emitted_events,
        "trace_bytes": int(stats["bytes_written"]),
        "trace_close_s": close_s,
        "trace_io_errors": int(stats["io_error_count"]),
        "trace_dropped_events": int(stats["dropped_events"]),
        "ratio_median": statistics.median(ratios),
        "ratio_p25": percentile(ratios, 0.25),
        "ratio_p75": percentile(ratios, 0.75),
        "delta_median_s": statistics.median(deltas),
        "amortized_overhead_per_event_s": per_event_s,
        "target_ratio_max": 1.02,
        "target_overhead_per_event_s_max": 5e-6,
        "ratio_gate_pass": statistics.median(ratios) <= 1.02,
        "event_overhead_gate_pass": per_event_s is not None and per_event_s <= 5e-6,
        "exactness_gate_pass": exact_mismatches == 0,
        "case_summaries": case_summaries,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "command": [sys.executable, str(Path(__file__).resolve()), *(argv if argv is not None else sys.argv[1:])],
            "script_sha256": sha256_file(Path(__file__).resolve()),
        },
        "artifacts": {
            "raw_csv": str(raw_path),
            "trace_jsonl": str(trace_path),
            "trace_sha256": sha256_file(trace_path),
        },
    }
    write_json_exclusive(summary_path, summary)
    write_json_exclusive(audit_path, trace_audit)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["exactness_gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
