"""Independently verify the exact multi-query batching development run."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.contracts import canonical_bytes
from scripts.crse_verify_c36_wide_repeated_query_dataset import (
    independent_output,
    independent_trace,
)


METHODS = (
    "r2_per_query",
    "cse_bigint",
    "cse_words",
    "cm_ir_bigint",
    "cm_ir_words",
    "concatenated_r2",
    "union_care_r2",
    "full_projection",
)
BATCH_METHODS = ("concatenated_r2", "union_care_r2")
BASELINE_METHODS = tuple(method for method in METHODS if method not in BATCH_METHODS)
QUERY_COUNTS = (1, 4, 16, 64)
REQUIRED_SOURCES = {
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cmbench/comparative/gf2_multi_query_batches.py",
    "cmbench/comparative/gf2_multi_query_batch_experiment.py",
    "cmbench/comparative/gf2_restricted_evaluators.py",
    "cmbench/comparative/gf2_restricted_evaluator_experiment.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "scripts/cm_comparative_multi_query_batch_development.py",
    "scripts/crse_multi_query_batch_development_verify.py",
    "scripts/crse_verify_c36_wide_repeated_query_dataset.py",
    "docs/recognition/c36_wide_repeated_query_dataset.json",
    "docs/recognition/c36_wide_repeated_query_dataset_verification.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def bound_project_path(relative: str) -> Path:
    path = ROOT.joinpath(*Path(relative).parts).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError("multi-query verifier input escaped or is missing")
    return path


def complete_assignments(query: dict[str, Any], n_vars: int) -> tuple[int, ...]:
    fixed = {int(row["variable"][1:]): row["value"] for row in query["fixed"]}
    remaining = [int(name[1:]) for name in query["remaining_order"]]
    output = []
    for residual in range(1 << len(remaining)):
        values = dict(fixed)
        for position, variable in enumerate(remaining):
            values[variable] = (residual >> (len(remaining) - 1 - position)) & 1
        complete = 0
        for variable in range(n_vars):
            complete = (complete << 1) | values[variable]
        output.append(complete)
    return tuple(output)


def independent_geometry(cases: list[dict[str, Any]]) -> dict[str, Any]:
    output = {}
    for case in cases:
        case_rows = {}
        for query_count in QUERY_COUNTS:
            per_query = [complete_assignments(query, case["n_vars"])
                         for query in case["c36_trace"][:query_count]]
            requested = sum(len(values) for values in per_query)
            union = len({assignment for values in per_query for assignment in values})
            full = 1 << case["n_vars"]
            case_rows[str(query_count)] = {
                "requested_lane_count": requested,
                "union_lane_count": union,
                "full_truth_lane_count": full,
                "union_coverage": union / full,
                "deduplication_fraction": 1 - union / requested,
            }
        output[case["case_id"]] = case_rows
    return output


def _medians(rows: list[dict[str, Any]]) -> tuple[dict[tuple[str, str, int], int], list[str]]:
    values: dict[tuple[str, str, int], list[int]] = {}
    cases = sorted({row["case_id"] for row in rows if row["role"] == "performance"})
    for row in rows:
        if row["role"] == "performance":
            values.setdefault((row["case_id"], row["method"], row["query_count"]), []).append(
                row["timings_ns"]["accounted_total_ns"])
    medians = {key: int(statistics.median(samples)) for key, samples in values.items()}
    if len(medians) != len(cases) * len(METHODS) * len(QUERY_COUNTS):
        raise ValueError("multi-query verifier incomplete medians")
    return medians, cases


def _totals(
    selected: list[str], medians: dict[tuple[str, str, int], int], query_count: int,
) -> dict[str, int]:
    return {method: sum(medians[(case, method, query_count)] for case in selected)
            for method in METHODS}


def independent_summary(
    rows: list[dict[str, Any]], geometry: dict[str, Any], speedup_gate: float,
) -> dict[str, Any]:
    medians, cases = _medians(rows)
    metadata = {row["case_id"]: (row["family"], row["n_vars"])
                for row in rows if row["role"] == "performance"}
    checkpoints = {}
    for query_count in QUERY_COUNTS:
        totals = _totals(cases, medians, query_count)
        best = min(METHODS, key=lambda method: (totals[method], method))
        baseline = min(BASELINE_METHODS, key=lambda method: (totals[method], method))
        batch = min(BATCH_METHODS, key=lambda method: (totals[method], method))
        winners = {case: min(
            METHODS, key=lambda method: (medians[(case, method, query_count)], method))
            for case in cases}
        oracle = sum(medians[(case, winners[case], query_count)] for case in cases)
        checkpoints[str(query_count)] = {
            "method_total_ns": totals,
            "best_fixed_method": best,
            "best_nonbatch_baseline": baseline,
            "best_batch_method": batch,
            "best_batch_speedup_over_best_nonbatch": totals[baseline] / totals[batch],
            "per_case_winners": winners,
            "per_case_oracle_total_ns": oracle,
            "oracle_speedup_over_best_fixed": totals[best] / oracle,
            "cse_words_speedup_over_bigint": totals["cse_bigint"] / totals["cse_words"],
            "cm_words_speedup_over_bigint": totals["cm_ir_bigint"] / totals["cm_ir_words"],
            "preferred_cse_engine": min(
                ("cse_bigint", "cse_words"), key=lambda method: (totals[method], method)),
            "preferred_cm_engine": min(
                ("cm_ir_bigint", "cm_ir_words"), key=lambda method: (totals[method], method)),
        }
    by_width = {}
    for width in sorted({value[1] for value in metadata.values()}):
        selected = [case for case in cases if metadata[case][1] == width]
        totals = _totals(selected, medians, 64)
        by_width[str(width)] = {
            "cases": len(selected),
            "method_total_ns": totals,
            "best_fixed_method": min(METHODS, key=lambda method: (totals[method], method)),
            "preferred_cse_engine": min(
                ("cse_bigint", "cse_words"), key=lambda method: (totals[method], method)),
            "preferred_cm_engine": min(
                ("cm_ir_bigint", "cm_ir_words"), key=lambda method: (totals[method], method)),
        }
    memory_rows = [row for row in rows if row["role"] == "memory_profile"]
    memory = {}
    for method in METHODS:
        selected = [row for row in memory_rows if row["method"] == method]
        memory[method] = {
            "profile_sessions": len(selected),
            "max_session_sampled_peak_rss_delta_bytes": max(
                (row["resources"]["session_sampled_peak_rss_delta_bytes"] or 0)
                for row in selected),
            "max_tracemalloc_peak_bytes": max(
                row["resources"].get("tracemalloc_peak_bytes", 0) for row in selected),
        }
    final = checkpoints["64"]
    return {
        "cases": len(cases),
        "performance_sessions": sum(row["role"] == "performance" for row in rows),
        "memory_profile_sessions": len(memory_rows),
        "checkpoints": checkpoints,
        "by_width_at_q64": by_width,
        "batch_geometry": geometry,
        "memory_profiles": memory,
        "decision": {
            "development_speedup_gate": speedup_gate,
            "best_batch_at_q64": final["best_batch_method"],
            "best_batch_speedup_over_best_nonbatch_at_q64": (
                final["best_batch_speedup_over_best_nonbatch"]),
            "batch_continuation_gate_passed": (
                final["best_batch_speedup_over_best_nonbatch"] >= speedup_gate),
            "best_fixed_at_q64": final["best_fixed_method"],
            "formal_confirmation_or_production_promotion_permitted": False,
        },
        "timing_is_local_and_machine_specific": True,
        "memory_timing_excluded_from_performance_summary": True,
    }


def verify(run: Path) -> dict[str, Any]:
    run = run.resolve()
    if not run.is_relative_to(ROOT.resolve()) or not run.is_dir():
        raise ValueError("multi-query run must be an existing project directory")
    destination = run / "independent_verification.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    expected_files = {
        "protocol.md", "results.json", "raw_measurements.jsonl",
        "environment.json", "manifest.json", "report.md",
    }
    if {path.name for path in run.iterdir() if path.is_file()} != expected_files:
        raise ValueError("unexpected multi-query pre-verification layout")
    results = load(run / "results.json")
    manifest = load(run / "manifest.json")
    environment = load(run / "environment.json")
    if (
        results.get("schema") != "crse-multi-query-batch-development/v1"
        or results.get("status") != "complete"
        or manifest.get("schema") != "crse-restricted-evaluator-manifest/v1"
    ):
        raise ValueError("multi-query schema/status")
    local_sources = manifest.get("local_sources", {})
    if not REQUIRED_SOURCES.issubset(local_sources):
        raise ValueError("multi-query manifest is not source-closed")
    for relative, expected in local_sources.items():
        if sha256(bound_project_path(relative)) != expected:
            raise ValueError(f"multi-query local source changed: {relative}")
    for module, record in manifest.get("native_modules", {}).items():
        path = Path(record["path"])
        if not path.is_file() or sha256(path) != record["sha256"]:
            raise ValueError(f"multi-query native module changed: {module}")
    interpreter = manifest.get("interpreter", {})
    executable = Path(interpreter.get("path", ""))
    if not executable.is_file() or sha256(executable) != interpreter.get("sha256"):
        raise ValueError("multi-query interpreter changed")
    for relative, expected in manifest.get("artifacts", {}).items():
        path = run / relative
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"multi-query artifact changed: {relative}")

    dataset_path = bound_project_path(results["dataset"]["path"])
    verification_path = bound_project_path(results["dataset"]["verification_path"])
    if (
        sha256(dataset_path) != results["dataset"]["sha256"]
        or sha256(verification_path) != results["dataset"]["verification_sha256"]
        or environment["dataset"]["sha256"] != results["dataset"]["sha256"]
        or load(verification_path).get("status") != "verified"
    ):
        raise ValueError("multi-query dataset binding")
    dataset = load(dataset_path)
    cases = dataset["cases"]
    case_map = {case["case_id"]: case for case in cases}
    geometry = independent_geometry(cases)
    expected_outputs: dict[tuple[str, int], tuple[str, list[str]]] = {}
    trace_mismatches = oracle_mismatches = 0
    for case in cases:
        trace = independent_trace(case["case_id"], case["n_vars"])
        trace_mismatches += int(trace != case["c36_trace"])
        full = independent_output(case, trace)
        for query_count in QUERY_COUNTS:
            prefix = {"schema": full["schema"], "case_id": case["case_id"],
                      "rows": full["rows"][:query_count]}
            expected_outputs[(case["case_id"], query_count)] = (
                digest(prefix), [digest(row) for row in prefix["rows"]])
        oracle_mismatches += int(digest(full) != case["c36_required_output_sha256"])

    rows = load_jsonl(run / "raw_measurements.jsonl")
    performance = [row for row in rows if row.get("role") == "performance"]
    memory = [row for row in rows if row.get("role") == "memory_profile"]
    blocks = results["config"]["blocks"]
    measurement_mismatches = 0
    if (
        len(performance) != len(cases) * len(QUERY_COUNTS) * blocks * len(METHODS)
        or len(memory) != len(cases) * len(METHODS)
    ):
        measurement_mismatches += 1
    expected_counts = Counter(
        (case["case_id"], query_count, method, block)
        for case in cases for query_count in QUERY_COUNTS
        for method in METHODS for block in range(blocks))
    actual_counts = Counter(
        (row["case_id"], row["query_count"], row["method"], row["block"])
        for row in performance)
    measurement_mismatches += int(expected_counts != actual_counts)
    memory_counts = Counter((row["case_id"], row["method"]) for row in memory)
    measurement_mismatches += int(memory_counts != Counter(
        (case["case_id"], method) for case in cases for method in METHODS))

    for row in rows:
        case_id = row.get("case_id")
        method = row.get("method")
        query_count = row.get("query_count")
        if case_id not in case_map or method not in METHODS or query_count not in QUERY_COUNTS:
            measurement_mismatches += 1
            continue
        expected_digest, expected_rows = expected_outputs[(case_id, query_count)]
        timings = row.get("timings_ns", {})
        stage_sum = sum(timings.get(key, 0) for key in (
            "input_decode_ns", "representation_ns", "restriction_setup_ns",
            "evaluation_ns", "delivery_ns", "cleanup_ns"))
        resources = row.get("resources", {})
        measurement_mismatches += int(
            row.get("schema") != "crse-multi-query-batch-raw-session/v1"
            or row.get("status") != "ok"
            or row.get("artifact_sha256") != expected_digest
            or row.get("query_output_sha256") != expected_rows
            or row.get("exact_check_passed") is not True
            or timings.get("accounted_total_ns") != stage_sum
            or resources.get("rss_sampling_points", 0) <= 0
            or (row["role"] == "memory_profile"
                and resources.get("tracemalloc_peak_bytes", 0) <= 0)
        )
        expected_geometry = geometry[case_id][str(query_count)]
        if method == "concatenated_r2":
            measurement_mismatches += int(
                resources.get("requested_lane_count")
                != expected_geometry["requested_lane_count"]
                or resources.get("evaluated_lane_count")
                != expected_geometry["requested_lane_count"])
        elif method == "union_care_r2":
            measurement_mismatches += int(
                resources.get("requested_lane_count")
                != expected_geometry["requested_lane_count"]
                or resources.get("evaluated_lane_count")
                != expected_geometry["union_lane_count"])

    recomputed = independent_summary(
        rows, geometry, results["config"]["development_speedup_gate"])
    summary_mismatches = int(recomputed != results.get("summary"))
    correctness_mismatches = int(results.get("correctness") != {
        "relation_mismatches": 0,
        "count_mismatches": 0,
        "sat_mismatches": 0,
        "witness_mismatches": 0,
        "canonical_delivery_mismatches": 0,
    })
    if any((trace_mismatches, oracle_mismatches, measurement_mismatches,
            summary_mismatches, correctness_mismatches)):
        raise RuntimeError(
            "multi-query independent verification failed: "
            f"trace={trace_mismatches}, oracle={oracle_mismatches}, "
            f"measurement={measurement_mismatches}, summary={summary_mismatches}, "
            f"correctness={correctness_mismatches}")
    verification = {
        "schema": "crse-multi-query-batch-independent-verification/v1",
        "status": "verified",
        "dataset_cases_replayed": len(cases),
        "queries_replayed": len(cases) * 64,
        "performance_sessions_checked": len(performance),
        "memory_profile_sessions_checked": len(memory),
        "trace_mismatches": 0,
        "relation_mismatches": 0,
        "count_mismatches": 0,
        "sat_mismatches": 0,
        "witness_mismatches": 0,
        "canonical_delivery_mismatches": 0,
        "measurement_mismatches": 0,
        "summary_mismatches": 0,
        "summary_recomputed_independently": True,
        "manifest_sources_checked": len(local_sources),
        "native_modules_checked": len(manifest.get("native_modules", {})),
        "interpreter_checked": True,
        "training_performed": False,
        "prospective_data_consumed": False,
        "production_write": False,
        "production_promotion": False,
        "results_sha256": sha256(run / "results.json"),
        "manifest_sha256": sha256(run / "manifest.json"),
    }
    write_new(destination, verification)
    return verification


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    result = verify(args.run)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
