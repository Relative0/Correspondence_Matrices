#!/usr/bin/env python3
"""Bounded diagnostic of dense CM temporary-memory admission estimates."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time
import tracemalloc


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_exprlib import And, Not, Or, Var, Xor
from cm_ir import _cm_node_count, compile_expr_to_cm_ir, materialize_cm
from cm_normalize import canonical_layout
from cmbench.output_budget import OutputBudget, OutputBudgetExceeded, estimate_explicit_output
from cmbench.reporting.provenance import sha256_file
from cmbench.tracing.replay import write_json_exclusive


def build_expr(n_vars: int):
    expr = Xor(Var(0), Not(Var(1)))
    for index in range(2, n_vars):
        leaf = Var(index)
        previous = Var(index - 1)
        expr = Xor(And(expr, Or(leaf, previous)), Not(And(leaf, previous)))
    return expr


def _digest_dense(array) -> str:
    return hashlib.sha256(array.reshape(-1).astype("uint8", copy=False).tobytes()).hexdigest()


def measure_case(n_vars: int, repetitions: int) -> dict:
    node = compile_expr_to_cm_ir(build_expr(n_vars), reuse_cache=False, persistent_cache=False)
    variables = [f"x{i}" for i in range(n_vars)]
    rows, columns = canonical_layout(variables, mode="balanced")
    operation_slots = _cm_node_count(node)
    estimate = estimate_explicit_output(n_vars, "dense_bool", operation_slots=operation_slots)
    samples = []
    digests = set()
    for _ in range(repetitions):
        gc.collect()
        tracemalloc.start()
        started = time.perf_counter_ns()
        output = materialize_cm(
            node,
            rows,
            columns,
            materialize_mode="numpy",
            output_budget=None,
        )
        elapsed_ns = time.perf_counter_ns() - started
        _current, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        digests.add(_digest_dense(output))
        samples.append({"elapsed_ns": elapsed_ns, "tracemalloc_peak_bytes": peak_bytes})
        del output
    if len(digests) != 1:
        raise AssertionError("dense output changed between repetitions")

    refusal_budget = OutputBudget(max_temporary_bytes=max(0, estimate.temporary_bytes - 1))
    tracemalloc.start()
    try:
        materialize_cm(
            node,
            rows,
            columns,
            materialize_mode="numpy",
            output_budget=refusal_budget,
        )
    except OutputBudgetExceeded as exc:
        refusal_reason = str(exc)
    else:
        raise AssertionError("temporary budget should have refused before materialization")
    _current, refusal_peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peaks = [sample["tracemalloc_peak_bytes"] for sample in samples]
    elapsed = [sample["elapsed_ns"] for sample in samples]
    return {
        "n_vars": n_vars,
        "operation_slots": operation_slots,
        "estimated_output_bytes": estimate.output_bytes,
        "estimated_temporary_bytes": estimate.temporary_bytes,
        "tracemalloc_peak_bytes_median": int(statistics.median(peaks)),
        "tracemalloc_peak_bytes_min": min(peaks),
        "tracemalloc_peak_bytes_max": max(peaks),
        "peak_over_estimated_temporary_median": statistics.median(peaks) / estimate.temporary_bytes,
        "elapsed_ns_median": int(statistics.median(elapsed)),
        "output_sha256": next(iter(digests)),
        "refusal_before_materialization": True,
        "refusal_tracemalloc_peak_bytes": refusal_peak_bytes,
        "refusal_reason": refusal_reason,
        "samples": samples,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="New result JSON path; existing files are refused.")
    parser.add_argument("--supports", nargs="+", type=int, default=[8, 10, 12, 14])
    parser.add_argument("--repetitions", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.repetitions < 1:
        raise ValueError("repetitions must be >= 1")
    if any(value < 2 or value > 18 for value in args.supports):
        raise ValueError("supports must be between 2 and 18")
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")
    source_paths = (
        "cm_ir.py",
        "cmbench/output_budget.py",
        "cmbench/reporting/provenance.py",
        "scripts/cm_output_budget_policy_probe.py",
    )
    payload = {
        "format": "cm-output-budget-policy-probe-v1",
        "measurement_scope": (
            "Python tracemalloc peak during dense NumPy materialization; diagnostic only, "
            "not an RSS or native-allocator upper bound"
        ),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "executable": sys.executable,
        },
        "arguments": {"supports": args.supports, "repetitions": args.repetitions},
        "source_sha256": {path: sha256_file(ROOT / path) for path in source_paths},
        "cases": [measure_case(value, args.repetitions) for value in args.supports],
    }
    write_json_exclusive(output, payload)
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
