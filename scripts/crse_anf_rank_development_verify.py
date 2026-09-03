"""Verify an ANF-basis GF(2)-rank development artifact."""
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

from cmbench.comparative.gf2_anf_rank_experiment import (
    exhaustive_four_variable_validation,
    prepare_c16_cases,
)
from cmbench.comparative.contracts import canonical_bytes


METHODS = (
    "truth_rank_screen", "anf_rank_screen_from_truth",
    "anf_rank_factor_from_truth", "anf_rank_screen_precomputed")
REQUIRED_SOURCES = {
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cmbench/recognition/gf2_anf_rank.py",
    "cmbench/recognition/gf2_decomposition.py",
    "cmbench/recognition/natural_decomposition.py",
    "cmbench/recognition/source_anf_hybrid.py",
    "cmbench/comparative/gf2_anf_rank_experiment.py",
    "scripts/cm_comparative_anf_rank_development.py",
    "scripts/crse_anf_rank_development_verify.py",
    "docs/recognition/c16_linux_confirmation/c16_dataset.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        raise ValueError("ANF-rank verifier input escaped or is missing")
    return path


def independent_summary(rows: list[dict[str, Any]], speedup_gate: float) -> dict[str, Any]:
    performance = [row for row in rows if row["role"] == "performance"]
    cases = sorted({row["case_id"] for row in performance})
    samples: dict[tuple[str, str], list[int]] = {}
    for row in performance:
        samples.setdefault((row["case_id"], row["method"]), []).append(
            row["timings_ns"]["accounted_total_ns"])
    medians = {key: int(statistics.median(values)) for key, values in samples.items()}
    totals = {method: sum(medians[(case, method)] for case in cases) for method in METHODS}
    speedups = {method: totals["truth_rank_screen"] / total
                for method, total in totals.items()}
    metadata = {row["case_id"]: row["n_vars"] for row in performance}
    by_width = {}
    for width in sorted(set(metadata.values())):
        selected = [case for case in cases if metadata[case] == width]
        width_totals = {method: sum(medians[(case, method)] for case in selected)
                        for method in METHODS}
        by_width[str(width)] = {
            "cases": len(selected), "method_total_ns": width_totals,
            "best_method": min(METHODS,
                               key=lambda method: (width_totals[method], method)),
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
    complete = speedups["anf_rank_screen_from_truth"]
    precomputed = speedups["anf_rank_screen_precomputed"]
    return {
        "cases": len(cases), "performance_sessions": len(performance),
        "memory_profile_sessions": len(memory_rows), "method_total_ns": totals,
        "speedup_over_truth_rank_screen": speedups,
        "best_method": min(METHODS, key=lambda method: (totals[method], method)),
        "by_width": by_width, "memory_profiles": memory,
        "decision": {
            "development_speedup_gate": speedup_gate,
            "complete_from_truth_speedup": complete,
            "precomputed_anf_speedup": precomputed,
            "complete_from_truth_gate_passed": complete >= speedup_gate,
            "precomputed_anf_gate_passed": precomputed >= speedup_gate,
            "production_integration_permitted": False,
        },
        "timing_is_local_and_machine_specific": True,
        "memory_timing_excluded_from_performance_summary": True,
    }


def verify(run: Path) -> dict[str, Any]:
    run = run.resolve()
    if not run.is_relative_to(ROOT.resolve()) or not run.is_dir():
        raise ValueError("ANF-rank run must be an existing project directory")
    destination = run / "independent_verification.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    expected_files = {"protocol.md", "results.json", "raw_measurements.jsonl",
                      "environment.json", "manifest.json", "report.md"}
    if {path.name for path in run.iterdir() if path.is_file()} != expected_files:
        raise ValueError("unexpected ANF-rank pre-verification layout")
    results = load(run / "results.json")
    manifest = load(run / "manifest.json")
    if results.get("schema") != "crse-anf-rank-development/v1" \
            or results.get("status") != "complete" \
            or manifest.get("schema") != "crse-restricted-evaluator-manifest/v1":
        raise ValueError("ANF-rank schema/status")
    local_sources = manifest.get("local_sources", {})
    if not REQUIRED_SOURCES.issubset(local_sources):
        raise ValueError("ANF-rank manifest is not source-closed")
    for relative, expected in local_sources.items():
        if sha256(bound_project_path(relative)) != expected:
            raise ValueError(f"ANF-rank local source changed: {relative}")
    for module, record in manifest.get("native_modules", {}).items():
        path = Path(record["path"])
        if not path.is_file() or sha256(path) != record["sha256"]:
            raise ValueError(f"ANF-rank native module changed: {module}")
    interpreter = manifest.get("interpreter", {})
    executable = Path(interpreter.get("path", ""))
    if not executable.is_file() or sha256(executable) != interpreter.get("sha256"):
        raise ValueError("ANF-rank interpreter changed")
    for relative, expected in manifest.get("artifacts", {}).items():
        if sha256(run / relative) != expected:
            raise ValueError(f"ANF-rank artifact changed: {relative}")

    dataset_path = bound_project_path(results["dataset"]["path"])
    if sha256(dataset_path) != results["dataset"]["sha256"]:
        raise ValueError("ANF-rank dataset binding")
    cases = prepare_c16_cases(load(dataset_path))
    case_map = {case["case_id"]: case for case in cases}
    exhaustive = exhaustive_four_variable_validation()
    exhaustive_mismatches = int(exhaustive != results.get("exhaustive_validation"))
    source_mismatches = int(results.get("source_anf_validation") != {
        "cases": len(cases), "mismatches": 0})

    rows = load_jsonl(run / "raw_measurements.jsonl")
    performance = [row for row in rows if row.get("role") == "performance"]
    memory = [row for row in rows if row.get("role") == "memory_profile"]
    blocks = results["config"]["blocks"]
    measurement_mismatches = 0
    if len(performance) != len(cases) * blocks * len(METHODS) \
            or len(memory) != len(cases) * len(METHODS):
        measurement_mismatches += 1
    if set(Counter((row.get("case_id"), row.get("method"))
                   for row in performance).values()) != {blocks}:
        measurement_mismatches += 1
    if set(Counter((row.get("case_id"), row.get("method"))
                   for row in memory).values()) != {1}:
        measurement_mismatches += 1

    stage_mismatches = output_mismatches = schedule_mismatches = 0
    for row in rows:
        if row.get("schema") != "crse-anf-rank-raw-session/v1" \
                or row.get("method") not in METHODS \
                or row.get("case_id") not in case_map \
                or row.get("status") != "ok" \
                or row.get("exact_check_passed") is not True:
            measurement_mismatches += 1
            continue
        timings = row["timings_ns"]
        stages = ("anf_construction_ns", "rank_or_factor_ns", "delivery_ns")
        if any(type(timings.get(key)) is not int or timings[key] <= 0 for key in stages) \
                or timings.get("accounted_total_ns") != sum(timings[key] for key in stages):
            stage_mismatches += 1
        if row.get("artifact_sha256") != case_map[row["case_id"]]["expected_sha256"]:
            output_mismatches += 1
        order = row.get("method_order")
        if not isinstance(order, list) or set(order) != set(METHODS) \
                or row.get("method_position") != order.index(row["method"]):
            schedule_mismatches += 1
        if row["role"] == "performance":
            core = {key: row[key] for key in (
                "block", "cell_position", "case_id", "family", "n_vars", "method_order")}
            digest = hashlib.sha256(canonical_bytes(core)).hexdigest()
            if row.get("order_sha256") != digest:
                schedule_mismatches += 1
        elif "tracemalloc_peak_bytes" not in row.get("resources", {}):
            measurement_mismatches += 1
    summary = independent_summary(rows, results["config"]["development_speedup_gate"])
    summary_mismatches = int(summary != results.get("summary"))
    mismatches = {
        "exhaustive": exhaustive_mismatches,
        "source_anf": source_mismatches,
        "measurement": measurement_mismatches,
        "stage": stage_mismatches,
        "output": output_mismatches,
        "schedule": schedule_mismatches,
        "summary": summary_mismatches,
    }
    if any(mismatches.values()):
        raise ValueError(f"ANF-rank verification mismatches: {mismatches}")
    verification = {
        "schema": "crse-anf-rank-independent-verification/v1",
        "status": "verified", "run_id": results["run_id"],
        "results_sha256": sha256(run / "results.json"),
        "manifest_sha256": sha256(run / "manifest.json"),
        "raw_measurements_sha256": sha256(run / "raw_measurements.jsonl"),
        "checked_exhaustive_function_partitions": exhaustive["function_partition_checks"],
        "checked_performance_sessions": len(performance),
        "checked_memory_profile_sessions": len(memory),
        "checked_local_sources": len(local_sources),
        "checked_native_modules": len(manifest.get("native_modules", {})),
        "mismatches": mismatches, "production_promotion": False,
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
