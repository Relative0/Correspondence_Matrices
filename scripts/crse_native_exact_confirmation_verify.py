"""Independently verify one frozen C37 prospective native confirmation run."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_multi_root import prospective_sibling_output_workloads
from cmbench.comparative.gf2_native_confirmation import (
    MULTI_METHODS,
    RAW_SCHEMA,
    SINGLE_METHODS,
    STAGES,
)
from scripts.crse_verify_c36_wide_repeated_query_dataset import independent_output
from cmbench.comparative.contracts import canonical_bytes


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def medians(rows, key, identities, methods):
    grouped = defaultdict(list)
    for row in rows:
        if row["role"] == "performance":
            grouped[(row[key], row["method"])].append(row)
    return {
        (identity, method): {
            stage: int(statistics.median_low(
                row["timings_ns"][stage] for row in grouped[(identity, method)]
            ))
            for stage in STAGES
        }
        for identity in identities for method in methods
    }


def independent_single_summary(rows, cases):
    identities = [case["case_id"] for case in cases]
    values = medians(rows, "case_id", identities, SINGLE_METHODS)
    totals = {method: {stage: sum(values[(identity, method)][stage]
                                       for identity in identities)
                       for stage in STAGES} for method in SINGLE_METHODS}
    r2, native = "restricted_r2_reference", "native_fused_slots"
    cases_speed = {identity: values[(identity, r2)]["accounted_total_ns"]
                   / values[(identity, native)]["accounted_total_ns"]
                   for identity in identities}
    widths = {}
    for width in range(11, 17):
        chosen = [case["case_id"] for case in cases if case["n_vars"] == width]
        widths[str(width)] = (
            sum(values[(identity, r2)]["accounted_total_ns"] for identity in chosen)
            / sum(values[(identity, native)]["accounted_total_ns"] for identity in chosen)
        )
    performance = [row for row in rows if row["role"] == "performance"]
    p95 = {method: percentile([row["timings_ns"]["accounted_total_ns"]
                              for row in performance if row["method"] == method], 0.95)
           for method in SINGLE_METHODS}
    max_workspace = max(row["resources"]["max_workspace_bytes"] for row in rows
                        if row["method"] == native)
    gates = {
        "aggregate_speedup_at_least_1_10": totals[r2]["accounted_total_ns"]
        / totals[native]["accounted_total_ns"] >= 1.10,
        "minimum_case_speedup_at_least_0_95": min(cases_speed.values()) >= 0.95,
        "minimum_width_speedup_at_least_1_00": min(widths.values()) >= 1.00,
        "p95_session_speedup_at_least_0_95": p95[r2] / p95[native] >= 0.95,
        "max_workspace_at_most_64_mib": max_workspace <= 64 * 1024 * 1024,
    }
    return {
        "cases": len(cases), "performance_sessions": len(performance),
        "memory_profile_sessions": sum(row["role"] == "memory_profile" for row in rows),
        "timed_queries": len(performance) * 64,
        "aggregate_case_median_stage_ns": totals,
        "native_speedup_over_python_r2": totals[r2]["accounted_total_ns"]
        / totals[native]["accounted_total_ns"],
        "native_speedup_over_projection_u16": totals["projection_u16_tuple"]["accounted_total_ns"]
        / totals[native]["accounted_total_ns"],
        "case_median_speedups_over_python_r2": cases_speed,
        "width_aggregate_speedups_over_python_r2": widths,
        "minimum_case_speedup_over_python_r2": min(cases_speed.values()),
        "minimum_width_speedup_over_python_r2": min(widths.values()),
        "p95_session_ns": p95,
        "p95_session_speedup_over_python_r2": p95[r2] / p95[native],
        "max_native_workspace_bytes": max_workspace,
        "gates": gates, "all_gates_passed": all(gates.values()),
    }


def independent_multi_summary(rows, workloads):
    identities = [workload.workload_id for workload in workloads]
    values = medians(rows, "workload_id", identities, MULTI_METHODS)
    totals = {method: {stage: sum(values[(identity, method)][stage]
                                       for identity in identities)
                       for stage in STAGES} for method in MULTI_METHODS}
    separate, union = "native_separate_roots", "native_union_roots"
    speedups = {identity: values[(identity, separate)]["accounted_total_ns"]
                / values[(identity, union)]["accounted_total_ns"]
                for identity in identities}
    performance = [row for row in rows if row["role"] == "performance"]
    p95 = {method: percentile([row["timings_ns"]["accounted_total_ns"]
                              for row in performance if row["method"] == method], 0.95)
           for method in MULTI_METHODS}
    memory = {identity: {row["method"]: row["resources"] for row in rows
                         if row["role"] == "memory_profile"
                         and row["workload_id"] == identity}
              for identity in identities}
    node_reduction = all(value[union]["union_nodes"]
                         < value[separate]["sum_separate_nodes"]
                         for value in memory.values())
    workspace = all(value[union]["max_workspace_bytes"]
                    <= value[separate]["max_workspace_bytes"]
                    for value in memory.values())
    gates = {
        "aggregate_speedup_at_least_1_10": totals[separate]["accounted_total_ns"]
        / totals[union]["accounted_total_ns"] >= 1.10,
        "minimum_workload_speedup_at_least_1_00": min(speedups.values()) >= 1.00,
        "p95_session_speedup_at_least_0_95": p95[separate] / p95[union] >= 0.95,
        "all_workloads_reduce_nodes": node_reduction,
        "all_workloads_union_workspace_no_larger": workspace,
    }
    return {
        "workloads": len(workloads), "roots_per_workload": 3,
        "performance_sessions": len(performance),
        "memory_profile_sessions": sum(row["role"] == "memory_profile" for row in rows),
        "timed_output_query_rows": len(performance) * 64 * 3,
        "aggregate_workload_median_stage_ns": totals,
        "union_speedup_over_separate": totals[separate]["accounted_total_ns"]
        / totals[union]["accounted_total_ns"],
        "workload_median_speedups": speedups,
        "minimum_workload_speedup": min(speedups.values()),
        "p95_session_ns": p95,
        "p95_session_speedup": p95[separate] / p95[union],
        "gates": gates, "all_gates_passed": all(gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    if not run_dir.is_relative_to(ROOT) or not run_dir.is_dir():
        raise ValueError("C37 run directory escaped the project")
    manifest = load(run_dir / "manifest.json")
    results = load(run_dir / "results.json")
    dataset_path = ROOT.joinpath(*Path(results["dataset"]["path"]).parts)
    dataset = load(dataset_path)
    freeze_path = ROOT.joinpath(*Path(results["freeze"]["path"]).parts)
    freeze = load(freeze_path)
    artifact_mismatches = sum(
        not (run_dir / name).is_file()
        or (run_dir / name).stat().st_size != identity["bytes"]
        or sha256(run_dir / name) != identity["sha256"]
        for name, identity in manifest["artifacts"].items()
    )
    source_mismatches = sum(
        not ROOT.joinpath(*Path(relative).parts).is_file()
        or ROOT.joinpath(*Path(relative).parts).stat().st_size != identity["bytes"]
        or sha256(ROOT.joinpath(*Path(relative).parts)) != identity["sha256"]
        for relative, identity in manifest["sources"].items()
    )
    binding_mismatches = int(
        manifest["freeze_sha256"] != sha256(freeze_path)
        or manifest["dataset_sha256"] != sha256(dataset_path)
        or results["freeze"]["sha256"] != sha256(freeze_path)
        or results["dataset"]["sha256"] != sha256(dataset_path)
        or manifest["sources"] != freeze["sources"]
    )
    native_path = run_dir / "native" / Path(results["native_library"]["path"]).name
    native_mismatches = int(
        not native_path.is_file()
        or sha256(native_path) != freeze["native_library"]["sha256"]
        or results["native_library"]["sha256"] != freeze["native_library"]["sha256"]
        or results["native_library"]["abi_version"] != 1
        or results["native_library"]["supports_multi_root"] is not True
    )
    expected_single = {
        case["case_id"]: digest(independent_output(case, case["c36_trace"]))
        for case in dataset["cases"]
    }
    expected_multi = {row["workload_id"]: row["required_output_sha256"]
                      for row in dataset["multi_root"]["workloads"]}
    rows = [json.loads(line) for line in
            (run_dir / "raw_measurements.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    single = [row for row in rows if row.get("track") == "single_root"]
    multi = [row for row in rows if row.get("track") == "multi_root"]
    structure_mismatches = int(
        len(single) != 12 * 18 * 3 + 18 * 3
        or len(multi) != 20 * 6 * 2 + 6 * 2
    )
    correctness_mismatches = 0
    identity_mismatches = 0
    for row in rows:
        expected = (expected_single.get(row.get("case_id"))
                    if row.get("track") == "single_root"
                    else expected_multi.get(row.get("workload_id")))
        correctness_mismatches += int(
            row.get("schema") != RAW_SCHEMA or row.get("status") != "ok"
            or row.get("role") not in ("performance", "memory_profile")
            or row.get("exact_check_passed") is not True
            or row.get("output_sha256") != expected
            or len(row.get("query_measurements", [])) != 64
        )
        if row.get("method", "").startswith("native_"):
            identity_mismatches += int(
                row["resources"].get("native_library_sha256") != sha256(native_path)
                or row["resources"].get("native_abi_version") != 1
            )
    balance_mismatches = 0
    for case in dataset["cases"]:
        for method in SINGLE_METHODS:
            selected = [row for row in single if row["role"] == "performance"
                        and row["case_id"] == case["case_id"] and row["method"] == method]
            balance_mismatches += int(
                len(selected) != 12
                or Counter(row["method_position"] for row in selected)
                != Counter({0: 4, 1: 4, 2: 4})
            )
    workloads = prospective_sibling_output_workloads()
    for workload in workloads:
        for method in MULTI_METHODS:
            selected = [row for row in multi if row["role"] == "performance"
                        and row["workload_id"] == workload.workload_id
                        and row["method"] == method]
            balance_mismatches += int(
                len(selected) != 20
                or Counter(row["method_position"] for row in selected)
                != Counter({0: 10, 1: 10})
            )
    summary_mismatches = int(
        independent_single_summary(single, dataset["cases"]) != results["single_root"]
    ) + int(independent_multi_summary(multi, workloads) != results["multi_root"])
    decision_mismatches = int(
        results["decision"]["all_predeclared_gates_passed"]
        != (results["single_root"]["all_gates_passed"]
            and results["multi_root"]["all_gates_passed"])
        or results["decision"]["eligible_for_guarded_integration"]
        != results["decision"]["all_predeclared_gates_passed"]
        or results["decision"]["training"] is not False
        or results["decision"]["policy_refit"] is not False
        or results["decision"]["gate_refit"] is not False
        or results["decision"]["production_promotion"] is not False
    )
    failures = {
        "artifact_mismatches": artifact_mismatches,
        "source_mismatches": source_mismatches,
        "binding_mismatches": binding_mismatches,
        "native_mismatches": native_mismatches,
        "structure_mismatches": structure_mismatches,
        "correctness_mismatches": correctness_mismatches,
        "native_identity_mismatches": identity_mismatches,
        "balance_mismatches": balance_mismatches,
        "summary_mismatches": summary_mismatches,
        "decision_mismatches": decision_mismatches,
    }
    if any(failures.values()):
        raise RuntimeError(f"C37 run verification failed: {failures}")
    result = {
        "schema": "crse-c37-native-exact-confirmation-independent-verification/v1",
        "status": "verified", "run_id": results["run_id"],
        "raw_sessions_checked": len(rows),
        "single_root_queries_checked": len(single) * 64,
        "multi_root_output_queries_checked": len(multi) * 64 * 3,
        "results_sha256": sha256(run_dir / "results.json"),
        "manifest_sha256": sha256(run_dir / "manifest.json"),
        "native_library_sha256": sha256(native_path),
        "all_predeclared_gates_passed": results["decision"]["all_predeclared_gates_passed"],
        **failures,
    }
    write_new(run_dir / "independent_verification.json", result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

