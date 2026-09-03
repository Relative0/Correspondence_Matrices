"""Independently verify a trace-specialized restriction development run."""
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
    "r2_per_query", "cse_bigint", "trace_specialized", "full_projection")
CONTROL_METHODS = tuple(method for method in METHODS if method != "trace_specialized")
QUERY_COUNTS = (1, 4, 16, 64)
REQUIRED_SOURCES = {
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cmbench/comparative/gf2_restricted_evaluators.py",
    "cmbench/comparative/gf2_restricted_evaluator_experiment.py",
    "cmbench/comparative/gf2_trace_specialized.py",
    "cmbench/comparative/gf2_trace_specialized_experiment.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "scripts/cm_comparative_trace_specialized_development.py",
    "scripts/crse_trace_specialized_development_verify.py",
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
        raise ValueError("trace verifier input escaped or is missing")
    return path


def _medians(rows: list[dict[str, Any]]) -> tuple[dict[tuple[str, str, int], int], list[str]]:
    values: dict[tuple[str, str, int], list[int]] = {}
    cases = sorted({row["case_id"] for row in rows if row["role"] == "performance"})
    for row in rows:
        if row["role"] == "performance":
            values.setdefault((row["case_id"], row["method"], row["query_count"]), []).append(
                row["timings_ns"]["accounted_total_ns"])
    medians = {key: int(statistics.median(samples)) for key, samples in values.items()}
    if len(medians) != len(cases) * len(METHODS) * len(QUERY_COUNTS):
        raise ValueError("trace verifier incomplete medians")
    return medians, cases


def independent_summary(rows: list[dict[str, Any]], speedup_gate: float) -> dict[str, Any]:
    medians, cases = _medians(rows)
    metadata = {row["case_id"]: row["n_vars"]
                for row in rows if row["role"] == "performance"}
    checkpoints = {}
    for query_count in QUERY_COUNTS:
        totals = {method: sum(medians[(case, method, query_count)] for case in cases)
                  for method in METHODS}
        best = min(METHODS, key=lambda method: (totals[method], method))
        control = min(CONTROL_METHODS, key=lambda method: (totals[method], method))
        winners = {case: min(
            METHODS, key=lambda method: (medians[(case, method, query_count)], method))
            for case in cases}
        oracle = sum(medians[(case, winners[case], query_count)] for case in cases)
        checkpoints[str(query_count)] = {
            "method_total_ns": totals,
            "best_fixed_method": best,
            "best_control_method": control,
            "trace_speedup_over_best_control": totals[control] / totals["trace_specialized"],
            "per_case_winners": winners,
            "per_case_oracle_total_ns": oracle,
            "oracle_speedup_over_best_fixed": totals[best] / oracle,
        }
    by_width = {}
    for width in sorted(set(metadata.values())):
        selected = [case for case in cases if metadata[case] == width]
        totals = {method: sum(medians[(case, method, 64)] for case in selected)
                  for method in METHODS}
        by_width[str(width)] = {
            "cases": len(selected),
            "method_total_ns": totals,
            "best_fixed_method": min(
                METHODS, key=lambda method: (totals[method], method)),
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
        "performance_sessions": len([row for row in rows if row["role"] == "performance"]),
        "memory_profile_sessions": len(memory_rows),
        "checkpoints": checkpoints,
        "by_width_at_q64": by_width,
        "memory_profiles": memory,
        "decision": {
            "development_speedup_gate": speedup_gate,
            "trace_speedup_over_best_control_at_q64": (
                final["trace_speedup_over_best_control"]),
            "trace_continuation_gate_passed": (
                final["trace_speedup_over_best_control"] >= speedup_gate),
            "best_fixed_at_q64": final["best_fixed_method"],
            "formal_confirmation_or_production_promotion_permitted": False,
        },
        "timing_is_local_and_machine_specific": True,
        "memory_timing_excluded_from_performance_summary": True,
    }


def verify(run: Path) -> dict[str, Any]:
    run = run.resolve()
    if not run.is_relative_to(ROOT.resolve()) or not run.is_dir():
        raise ValueError("trace run must be an existing project directory")
    destination = run / "independent_verification.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    expected_files = {
        "protocol.md", "results.json", "raw_measurements.jsonl",
        "environment.json", "manifest.json", "report.md",
    }
    if {path.name for path in run.iterdir() if path.is_file()} != expected_files:
        raise ValueError("unexpected trace pre-verification layout")
    results = load(run / "results.json")
    manifest = load(run / "manifest.json")
    environment = load(run / "environment.json")
    if (
        results.get("schema") != "crse-trace-specialized-development/v1"
        or results.get("status") != "complete"
        or manifest.get("schema") != "crse-restricted-evaluator-manifest/v1"
    ):
        raise ValueError("trace schema/status")
    local_sources = manifest.get("local_sources", {})
    if not REQUIRED_SOURCES.issubset(local_sources):
        raise ValueError("trace manifest is not source-closed")
    for relative, expected in local_sources.items():
        if sha256(bound_project_path(relative)) != expected:
            raise ValueError(f"trace local source changed: {relative}")
    for module, record in manifest.get("native_modules", {}).items():
        path = Path(record["path"])
        if not path.is_file() or sha256(path) != record["sha256"]:
            raise ValueError(f"trace native module changed: {module}")
    interpreter = manifest.get("interpreter", {})
    executable = Path(interpreter.get("path", ""))
    if not executable.is_file() or sha256(executable) != interpreter.get("sha256"):
        raise ValueError("trace interpreter changed")
    for relative, expected in manifest.get("artifacts", {}).items():
        path = run / relative
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"trace artifact changed: {relative}")

    dataset_path = bound_project_path(results["dataset"]["path"])
    verification_path = bound_project_path(results["dataset"]["verification_path"])
    if (
        sha256(dataset_path) != results["dataset"]["sha256"]
        or sha256(verification_path) != results["dataset"]["verification_sha256"]
        or environment["dataset"]["sha256"] != results["dataset"]["sha256"]
        or load(verification_path).get("status") != "verified"
    ):
        raise ValueError("trace dataset binding")
    dataset = load(dataset_path)
    cases = dataset["cases"]
    case_map = {case["case_id"]: case for case in cases}
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
    performance_counts = Counter(
        (row.get("case_id"), row.get("method"), row.get("query_count"))
        for row in performance)
    if set(performance_counts.values()) != {blocks}:
        measurement_mismatches += 1
    memory_counts = Counter((row.get("case_id"), row.get("method")) for row in memory)
    if set(memory_counts.values()) != {1}:
        measurement_mismatches += 1

    schedule_mismatches = stage_mismatches = output_mismatches = 0
    for row in rows:
        if (
            row.get("schema") != "crse-trace-specialized-raw-session/v1"
            or row.get("method") not in METHODS
            or row.get("query_count") not in QUERY_COUNTS
            or row.get("case_id") not in case_map
            or row.get("status") != "ok"
            or row.get("exact_check_passed") is not True
        ):
            measurement_mismatches += 1
            continue
        timings = row.get("timings_ns", {})
        stage_keys = (
            "input_decode_ns", "representation_ns", "restriction_setup_ns",
            "evaluation_ns", "delivery_ns", "cleanup_ns")
        if (
            any(type(timings.get(key)) is not int or timings[key] <= 0 for key in stage_keys)
            or timings.get("accounted_total_ns") != sum(timings[key] for key in stage_keys)
        ):
            stage_mismatches += 1
        expected_digest, expected_rows = expected_outputs[
            (row["case_id"], row["query_count"])]
        if row.get("artifact_sha256") != expected_digest \
                or row.get("query_output_sha256") != expected_rows:
            output_mismatches += 1
        order = row.get("method_order")
        if not isinstance(order, list) or set(order) != set(METHODS) \
                or row.get("method_position") != order.index(row["method"]):
            schedule_mismatches += 1
        if row["role"] == "performance":
            core = {key: row[key] for key in (
                "block", "cell_position", "case_id", "family", "n_vars",
                "query_count", "method_order")}
            if row.get("order_sha256") != digest(core):
                schedule_mismatches += 1
        elif "tracemalloc_peak_bytes" not in row.get("resources", {}):
            measurement_mismatches += 1

    expected_summary = independent_summary(
        rows, results["config"]["development_speedup_gate"])
    summary_mismatches = int(expected_summary != results.get("summary"))
    mismatches = {
        "trace": trace_mismatches,
        "oracle": oracle_mismatches,
        "measurement": measurement_mismatches,
        "schedule": schedule_mismatches,
        "stage": stage_mismatches,
        "output": output_mismatches,
        "summary": summary_mismatches,
    }
    if any(mismatches.values()):
        raise ValueError(f"trace verification mismatches: {mismatches}")
    verification = {
        "schema": "crse-trace-specialized-independent-verification/v1",
        "status": "verified",
        "run_id": results["run_id"],
        "results_sha256": sha256(run / "results.json"),
        "manifest_sha256": sha256(run / "manifest.json"),
        "raw_measurements_sha256": sha256(run / "raw_measurements.jsonl"),
        "checked_performance_sessions": len(performance),
        "checked_memory_profile_sessions": len(memory),
        "checked_local_sources": len(local_sources),
        "checked_native_modules": len(manifest.get("native_modules", {})),
        "mismatches": mismatches,
        "production_promotion": False,
    }
    write_new(destination, verification)
    return verification


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.run), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
