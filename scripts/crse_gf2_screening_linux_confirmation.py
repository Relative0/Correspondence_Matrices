"""Frozen second-machine timing for the C16 exact-screened GF(2) tail."""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import statistics
import sys
import time
from pathlib import Path

from cm_expr_serde import expr_from_json
from cmbench.recognition.gf2_decomposition import (
    analyze_exact_gf2,
    analyze_screened_exact_gf2,
    truth_sha256,
)
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.source_anf_hybrid import packed_truth_bits, source_anf_packed

METHODS = ("explicit_cm_exhaustive", "explicit_cm_screened", "packed_source_anf_screened")


def best_document(analysis):
    return analysis.best.to_dict() if analysis.best else None


def method_bits(method, case, expression):
    if method in {"explicit_cm_exhaustive", "explicit_cm_screened"}:
        return reference_bits(expression, case["n_vars"])
    polynomial, _stats = source_anf_packed(case["expression_v2"], case["n_vars"])
    return packed_truth_bits(polynomial, case["n_vars"])


def analyze(method, bits, n_vars):
    if method == "explicit_cm_exhaustive":
        return analyze_exact_gf2(bits, n_vars, max_partitions=64)
    return analyze_screened_exact_gf2(
        bits, n_vars, max_partitions=64, materialize_budget=4
    )


def p95(values):
    return statistics.quantiles(values, n=20, method="inclusive")[18]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if not 3 <= args.repetitions <= 5:
        raise SystemExit("repetitions outside frozen bound")
    data = json.loads(args.dataset.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if data.get("schema") != "crse-c16-gf2-screened-tail-dataset/v1" or len(cases) != 40:
        raise SystemExit("invalid frozen C16 dataset")
    args.output.mkdir(parents=True, exist_ok=False)
    expressions, expected_bits, expected_best = {}, {}, {}
    functional_rows = []
    for case in cases:
        expression = expr_from_json(case["expression_v2"])
        bits = reference_bits(expression, case["n_vars"])
        exhaustive = analyze_exact_gf2(bits, case["n_vars"], max_partitions=64)
        screened = analyze_screened_exact_gf2(
            bits, case["n_vars"], max_partitions=64, materialize_budget=4
        )
        match = best_document(screened) == best_document(exhaustive)
        exact = all(candidate.reconstruct() == bits for candidate in screened.candidates)
        if not match or not exact:
            raise RuntimeError("C16 Linux functional replay mismatch")
        expressions[case["case_id"]] = expression
        expected_bits[case["case_id"]] = bits
        expected_best[case["case_id"]] = best_document(exhaustive)
        functional_rows.append({
            "case_id": case["case_id"],
            "split": case["split"],
            "n_vars": case["n_vars"],
            "exact_best_identity_match": match,
            "exact_reconstruction": exact,
            "best_artifact_sha256": screened.best.digest if screened.best else None,
            "screened_descriptors": screened.descriptors_screened,
            "screened_artifacts_materialized": screened.artifacts_materialized,
        })

    measurements = []
    rng = random.Random("20260830:c16-linux-balanced-method-order/v1")
    wall_started = time.perf_counter()
    for repetition in range(args.repetitions):
        order = [(case, method) for case in cases for method in METHODS]
        rng.shuffle(order)
        for case, method in order:
            case_id = case["case_id"]
            started = time.perf_counter_ns()
            bits = method_bits(method, case, expressions[case_id])
            representation_ns = max(1, time.perf_counter_ns() - started)
            started = time.perf_counter_ns()
            result = analyze(method, bits, case["n_vars"])
            analysis_ns = max(1, time.perf_counter_ns() - started)
            best = best_document(result)
            semantic_mismatch = int(bits != expected_bits[case_id])
            artifact_mismatch = int(best != expected_best[case_id])
            measurements.append({
                "case_id": case_id,
                "split": case["split"],
                "method": method,
                "repetition": repetition,
                "n_vars": case["n_vars"],
                "semantic_mismatches": semantic_mismatch,
                "artifact_mismatches": artifact_mismatch,
                "representation_ns": representation_ns,
                "analysis_ns": analysis_ns,
                "total_ns": representation_ns + analysis_ns,
                "output_sha256": truth_sha256(bits, case["n_vars"]),
                "best_artifact_sha256": best["payload_sha256"] if best else None,
                "partitions_screened": result.partitions_tested,
                "descriptors_screened": result.descriptors_screened,
                "artifacts_materialized": result.artifacts_materialized,
            })

    by_case_method = {}
    for row in measurements:
        by_case_method.setdefault((row["case_id"], row["method"]), []).append(row)
    case_ids = sorted(expressions)
    medians = {
        key: {field: statistics.median(row[field] for row in rows)
              for field in ("representation_ns", "analysis_ns", "total_ns")}
        for key, rows in by_case_method.items()
    }
    totals = {
        method: {field: sum(medians[(case_id, method)][field] for case_id in case_ids)
                 for field in ("representation_ns", "analysis_ns", "total_ns")}
        for method in METHODS
    }
    exhaustive, screened = "explicit_cm_exhaustive", "explicit_cm_screened"
    speeds = {
        "screened_analysis_over_exhaustive":
            totals[exhaustive]["analysis_ns"] / totals[screened]["analysis_ns"],
        "screened_whole_path_over_exhaustive":
            totals[exhaustive]["total_ns"] / totals[screened]["total_ns"],
        "screened_whole_path_p95":
            p95([medians[(case_id, exhaustive)]["total_ns"] for case_id in case_ids])
            / p95([medians[(case_id, screened)]["total_ns"] for case_id in case_ids]),
        "packed_source_anf_over_explicit_cm_screened":
            totals[screened]["total_ns"] / totals["packed_source_anf_screened"]["total_ns"],
    }
    mismatches = sum(row["semantic_mismatches"] + row["artifact_mismatches"]
                     for row in measurements)
    criteria = {
        "exact": mismatches == 0 and all(row["exact_best_identity_match"]
                                         and row["exact_reconstruction"]
                                         for row in functional_rows),
        "screened_analysis_speedup_at_least_1_50x":
            speeds["screened_analysis_over_exhaustive"] >= 1.50,
        "whole_path_speedup_at_least_1_25x":
            speeds["screened_whole_path_over_exhaustive"] >= 1.25,
        "whole_path_p95_speedup_at_least_1_20x": speeds["screened_whole_path_p95"] >= 1.20,
    }
    summary = {
        "schema": "crse-c16-gf2-screened-tail-linux-confirmation/v1",
        "status": "complete" if criteria["exact"] else "failed",
        "scientific_scope": "second-machine timing of the frozen C16 exact-screened GF(2) tail",
        "semantic_mismatches": mismatches,
        "config": {"cases": len(cases), "repetitions": args.repetitions,
                   "methods": list(METHODS), "max_partitions": 64, "materialize_budget": 4},
        "criteria": criteria,
        "second_machine_gate": all(criteria.values()),
        "speedup": speeds,
        "median_case_sum_ns": {
            method: {field: int(value) for field, value in fields.items()}
            for method, fields in totals.items()
        },
        "functional_rows": functional_rows,
        "measurement_rows": len(measurements),
        "wall_seconds": time.perf_counter() - wall_started,
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "cpu_count": os.cpu_count()},
        "production_promotion": False,
    }
    with (args.output / "measurements.jsonl").open("x", encoding="utf-8", newline="\n") as handle:
        for row in measurements:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    with (args.output / "summary.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": summary["status"], "second_machine_gate": summary["second_machine_gate"],
                      "speedup": speeds, "mismatches": mismatches}, sort_keys=True))
    return 0 if summary["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
