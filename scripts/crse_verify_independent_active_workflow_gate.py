"""Independent standard-library replay for the active-workflow profile gate."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

COMPONENTS_H2 = ("key_creation", "hashing", "interning")
COMPONENTS_H3 = ("dense_lifting", "allocation", "conversion", "temporary_copies")
LIFECYCLES = ("cold", "reused")
REPETITIONS = 7
MEMORY_REPLICATES = 3


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def scalar_payload(cohort: str, primitive: str) -> dict[str, Any]:
    bits = "".join(
        str(int(bool(a and b) ^ (bool(c) if cohort == "ambient_control" else bool(c or d))))
        for a, b in ((0, 0), (0, 1), (1, 0), (1, 1))
        for c, d in ((0, 0), (0, 1), (1, 0), (1, 1))
    )
    full = {
        "expression": "(A AND B) XOR C" if cohort == "ambient_control" else "(A AND B) XOR (C OR D)",
        "ambient_variables": ["A", "B", "C", "D"],
        "live_variables": ["A", "B", "C"] if cohort == "ambient_control" else ["A", "B", "C", "D"],
        "matrix": {"rows": 4, "columns": 4, "bits": bits,
                   "row_labels": ["AB=00", "AB=01", "AB=10", "AB=11"],
                   "column_labels": ["CD=00", "CD=01", "CD=10", "CD=11"]},
    }
    return full if primitive == "expression_matrix" else full["matrix"]


def materiality(rows: Sequence[Mapping[str, Any]], memory: Sequence[Mapping[str, Any]], freeze: Mapping[str, Any], hypothesis: str, component: str) -> dict[str, Any]:
    applicable = [row for row in rows if hypothesis in row["hypothesis_scope"]]
    gate = freeze["materiality_gate"]
    accounted = sum(row["profile"]["accounted_self_ns"] for row in applicable)
    component_total = sum(row["profile"]["exclusive_self_ns"][component] for row in applicable)
    shares = [row["profile"]["exclusive_share"][component] for row in applicable]
    cohort_shares = {}
    for cohort in ("main", "ambient_control"):
        selected = [row for row in applicable if row["cohort"] == cohort]
        denominator = sum(row["profile"]["accounted_self_ns"] for row in selected)
        cohort_shares[cohort] = sum(row["profile"]["exclusive_self_ns"][component] for row in selected) / denominator if denominator else 0.0
    peak_excess = []
    for row in memory:
        peak = max(row["memory"]["working_set_task_peak_delta_bytes"], row["memory"]["private_task_peak_delta_bytes"], row["memory"]["tracemalloc_task_peak_delta_bytes"])
        required = max(1, row["required_artifact_bytes"])
        peak_excess.append((peak - required) / required)
    conditions = {
        "minimum_cells": len(applicable) >= gate["minimum_cells"],
        "aggregate_share": (component_total / accounted if accounted else 0.0) >= gate["aggregate_share_min"],
        "median_cell_share": statistics.median(shares) >= gate["median_cell_share_min"] if shares else False,
        "median_exclusive_time": statistics.median(row["profile"]["exclusive_self_ns"][component] for row in applicable) >= gate["median_exclusive_ns_min"] if applicable else False,
        "cell_prevalence": sum(value >= gate["cell_prevalence_share_floor"] for value in shares) / len(shares) >= gate["cell_prevalence_min"] if shares else False,
        "both_cohorts": all(value >= gate["per_cohort_aggregate_share_min"] for value in cohort_shares.values()),
        "allocation_copy_peak_excess": component not in {"allocation", "temporary_copies"} or (bool(peak_excess) and statistics.median(peak_excess) >= gate["allocation_copy_peak_excess_over_output_min"]),
    }
    return {"hypothesis": hypothesis, "component": component, "applicable_cells": len(applicable),
            "aggregate_exclusive_share": component_total / accounted if accounted else 0.0,
            "median_cell_share": statistics.median(shares) if shares else 0.0,
            "median_exclusive_ns": statistics.median(row["profile"]["exclusive_self_ns"][component] for row in applicable) if applicable else 0,
            "cell_prevalence": sum(value >= gate["cell_prevalence_share_floor"] for value in shares) / len(shares) if shares else 0.0,
            "cohort_aggregate_shares": cohort_shares, "conditions": conditions, "passed": all(conditions.values())}


def verify(root: Path, freeze_path: Path, profile_path: Path, memory_path: Path, summary_path: Path) -> dict[str, Any]:
    freeze, summary = load(freeze_path), load(summary_path)
    profiles, memory = read_jsonl(profile_path), read_jsonl(memory_path)
    mismatches: dict[str, list[str]] = defaultdict(list)
    freeze_core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    if digest(freeze_core) != freeze.get("freeze_sha256"): mismatches["freeze"].append("canonical_digest")
    for record in freeze["source_closure"]:
        path = root / record["path"]
        if not path.is_file() or path.stat().st_size != record["bytes"] or file_sha(path) != record["sha256"]:
            mismatches["source_closure"].append(record["path"])
    for occurrence in freeze["workload"]["occurrences"]:
        expected = scalar_payload(occurrence["cohort"], occurrence["primitive"])
        if canonical(expected) != canonical(occurrence["artifact"]): mismatches["oracle"].append(occurrence["occurrence_id"])
        if digest(expected) != occurrence["artifact_sha256"]: mismatches["oracle_hash"].append(occurrence["occurrence_id"])
        contract = root / occurrence["contract_path"]
        if not contract.is_file() or file_sha(contract) != occurrence["contract_file_sha256"]:
            mismatches["caller_contract"].append(occurrence["occurrence_id"])
    expected_profiles = [f"{row['occurrence_id']}:{lifecycle}" for row in freeze["workload"]["occurrences"] for lifecycle in LIFECYCLES]
    if [row["row_id"] for row in profiles] != expected_profiles: mismatches["profile_schedule"].append("order_or_cardinality")
    for row in profiles:
        if row["status"] != "ok" or not row["exact_oracle_agreement"] or not row["stable_output_order_and_hashes"]:
            mismatches["profile_exactness"].append(row["row_id"])
        if len(row["raw_timing_trials"]) != REPETITIONS: mismatches["timing_repetitions"].append(row["row_id"])
    groups = sorted(freeze["workload"]["oracle_groups"])
    expected_memory = [f"{key}:{lifecycle}:r{replicate}" for key in groups for lifecycle in LIFECYCLES for replicate in range(MEMORY_REPLICATES)]
    if [row["row_id"] for row in memory] != expected_memory: mismatches["memory_schedule"].append("order_or_cardinality")
    by_logical: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in memory:
        by_logical[row["logical_id"]].append(row)
        fields = row["memory"]
        if row["status"] != "ok" or row["child_exit_code"] != 0 or not row["exact_oracle_agreement"] or not row["stable_output_order_and_hashes"] or not fields["samplers_stopped"] or fields["execution_sample_count"] < 1:
            mismatches["memory_validity"].append(row["row_id"])
        for endpoint in ("common_baseline", "prepared_endpoint", "retained_endpoint", "post_release_endpoint"):
            if min(fields[endpoint]["working_set_bytes"], fields[endpoint]["private_usage_bytes"]) < 0:
                mismatches["memory_endpoint"].append(row["row_id"])
        for signed in ("working_set_prepared_retained_delta_bytes", "private_prepared_retained_delta_bytes", "working_set_retained_delta_bytes", "private_retained_delta_bytes", "working_set_post_release_delta_bytes", "private_post_release_delta_bytes", "tracemalloc_prepared_retained_delta_bytes", "tracemalloc_retained_delta_bytes", "tracemalloc_post_release_delta_bytes"):
            if type(fields[signed]) is not int: mismatches["signed_memory"].append(f"{row['row_id']}:{signed}")
    for logical, selected in by_logical.items():
        if len(selected) != MEMORY_REPLICATES or len({row["child_pid"] for row in selected}) != MEMORY_REPLICATES:
            mismatches["fresh_process"] .append(logical)
    replay_materiality = [*[materiality(profiles, memory, freeze, "H2", item) for item in COMPONENTS_H2],
                          *[materiality(profiles, memory, freeze, "H3", item) for item in COMPONENTS_H3]]
    passing = [f"{row['hypothesis']}:{row['component']}" for row in replay_materiality if row["passed"]]
    valid = not any(mismatches.values())
    decision = "stop_local_measurement_invalid" if not valid else "no_go_no_material_component" if not passing else "no_go_nonunique_material_components" if len(passing) > 1 else "go_one_candidate_eligible_requires_separate_freeze"
    if canonical(replay_materiality) != canonical(summary["materiality"]): mismatches["summary"].append("materiality")
    if passing != summary["passing_components"]: mismatches["summary"].append("passing_components")
    if decision != summary["decision"]: mismatches["summary"].append("decision")
    summary_core = {key: summary[key] for key in summary if key != "summary_sha256"}
    if digest(summary_core) != summary["summary_sha256"]: mismatches["summary"].append("canonical_digest")
    flat = {key: values for key, values in sorted(mismatches.items()) if values}
    return {
        "schema": "cm-independent-active-workflow-independent-verification/v1",
        "status": "verified" if not flat else "failed_closed",
        "method": "independent_standard_library_oracle_and_summary_replay",
        "freeze_sha256": freeze["freeze_sha256"], "profile_raw_sha256": file_sha(profile_path),
        "memory_raw_sha256": file_sha(memory_path), "summary_file_sha256": file_sha(summary_path),
        "profile_rows": len(profiles), "memory_rows": len(memory),
        "oracle_replayed_occurrences": len(freeze["workload"]["occurrences"]),
        "materiality": replay_materiality, "passing_components": passing,
        "decision": decision, "mismatches": flat, "mismatch_count": sum(len(values) for values in flat.values()),
        "production_behavior_changed": False, "runpod_authorization_request_permitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--memory", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = verify(args.project_root.resolve(), args.freeze.resolve(), args.profile.resolve(), args.memory.resolve(), args.summary.resolve())
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False); stream.write("\n")
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
