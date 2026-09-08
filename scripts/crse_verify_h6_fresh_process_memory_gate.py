"""Independent standard-library replay of the H6 memory calibration summary."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence


REPLICATES = 3


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _schedule(freeze: Mapping[str, Any]):
    for lane in ("A", "B", "C"):
        lane_spec = freeze["workload"][lane]
        for case_id in lane_spec["case_ids"]:
            for query_count in lane_spec["query_counts"]:
                for arm in lane_spec["arms"]:
                    for lifecycle in freeze["workload"]["lifecycles"]:
                        for replicate in range(freeze["workload"]["replicates"]):
                            yield {
                                "row_id": f"{lane}:{case_id}:q{query_count}:{arm}:{lifecycle}:r{replicate}",
                                "logical_id": f"{lane}:{case_id}:q{query_count}:{arm}:{lifecycle}",
                                "lane": lane,
                                "case_id": case_id,
                                "query_count": query_count,
                                "arm": arm,
                                "lifecycle": lifecycle,
                                "replicate": replicate,
                                "cohort": "fresh" if case_id.startswith("fresh-") else "observed",
                            }


def _median(values: Sequence[int]) -> float:
    return float(statistics.median(values))


def verify(root: Path, freeze_path: Path, raw_path: Path, summary_path: Path) -> dict[str, Any]:
    freeze, summary = _load(freeze_path), _load(summary_path)
    core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    _require(freeze["freeze_sha256"] == _digest(core), "freeze digest")
    _require(freeze["source_closure_sha256"] == _digest(freeze["source_closure"]), "closure digest")
    closure_mismatches = []
    for record in freeze["source_closure"]:
        path = (root / record["path"]).resolve()
        if (
            not path.is_relative_to(root)
            or not path.is_file()
            or path.stat().st_size != record["bytes"]
            or _sha256(path) != record["sha256"]
        ):
            closure_mismatches.append(record["path"])
    _require(not closure_mismatches, f"source closure mismatches: {closure_mismatches}")
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line]
    expected = list(_schedule(freeze))
    _require(len(rows) == len(expected) == freeze["expected_rows"], "raw cardinality")
    _require([row["row_id"] for row in rows] == [row["row_id"] for row in expected], "raw schedule")
    exact_failures = [row["row_id"] for row in rows if row["status"] != "ok" or not row["exact_oracle_agreement"]]
    lifecycle_failures = [
        row["row_id"] for row in rows
        if row["child_exit_code"] != 0
        or not row["memory"]["samplers_stopped"]
        or row["memory"]["execution_sample_count"] < 1
    ]
    memory_failures = []
    for row in rows:
        memory = row["memory"]
        for name in ("working_set_bytes", "private_usage_bytes"):
            if any(int(memory[endpoint][name]) < 0 for endpoint in (
                "common_baseline", "prepared_endpoint", "retained_endpoint", "post_release_endpoint"
            )):
                memory_failures.append(row["row_id"])
                break
        if int(memory["working_set_task_peak_bytes"]) < int(memory["common_baseline"]["working_set_bytes"]):
            memory_failures.append(row["row_id"])
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["logical_id"]].append(row)
    logical = []
    stability_failures = []
    for logical_id, selected in sorted(grouped.items()):
        _require(len(selected) == REPLICATES, f"replicate count: {logical_id}")
        identities = {
            (row["output_sha256"], row["ordering_sha256"], row["structure_sha256"])
            for row in selected
        }
        if len(identities) != 1 or len({row["child_pid"] for row in selected}) != REPLICATES:
            stability_failures.append(logical_id)
        first = selected[0]
        os_peaks = [
            max(
                int(row["memory"]["working_set_task_peak_delta_bytes"]),
                int(row["memory"]["private_task_peak_delta_bytes"]),
            )
            for row in selected
        ]
        prepared = [
            max(
                0,
                int(row["memory"]["working_set_prepared_retained_delta_bytes"]),
                int(row["memory"]["private_prepared_retained_delta_bytes"]),
            )
            for row in selected
        ]
        median_peak = _median(os_peaks)
        logical.append({
            "logical_id": logical_id,
            "lane": first["lane"], "case_id": first["case_id"],
            "query_count": first["query_count"], "arm": first["arm"],
            "lifecycle": first["lifecycle"], "cohort": first["cohort"],
            "median_os_task_peak_delta_bytes": median_peak,
            "median_prepared_retained_delta_bytes": _median(prepared),
            "replicate_range_over_median": (
                (max(os_peaks) - min(os_peaks)) / median_peak if median_peak > 0 else None
            ),
        })
    gate = freeze["calibration_gate"]
    group_prevalence = {}
    for arm, lifecycle in sorted({(row["arm"], row["lifecycle"]) for row in logical}):
        selected = [row for row in logical if row["arm"] == arm and row["lifecycle"] == lifecycle]
        group_prevalence[f"{arm}/{lifecycle}"] = sum(
            row["median_os_task_peak_delta_bytes"] > 0 for row in selected
        ) / len(selected)
    cohort_prevalence = {}
    for cohort in ("observed", "fresh"):
        selected = [row for row in logical if row["cohort"] == cohort]
        cohort_prevalence[cohort] = sum(
            row["median_os_task_peak_delta_bytes"] > 0 for row in selected
        ) / len(selected)
    reused = [row for row in logical if row["lifecycle"] == "reused"]
    reused_prepared_prevalence = sum(
        row["median_prepared_retained_delta_bytes"] >= gate["reused_prepared_retained_floor_bytes"]
        for row in reused
    ) / len(reused)
    stable_signal = [
        row for row in logical
        if row["median_os_task_peak_delta_bytes"] >= gate["stable_signal_floor_bytes"]
    ]
    stable_signal_prevalence = (
        sum(
            row["replicate_range_over_median"] is not None
            and row["replicate_range_over_median"] <= gate["replicate_range_over_median_max"]
            for row in stable_signal
        ) / len(stable_signal)
        if stable_signal else 0.0
    )
    matched: dict[tuple[str, str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in logical:
        matched[(row["lane"], row["case_id"], row["query_count"], row["lifecycle"])].append(row)
    discriminating = 0
    for selected in matched.values():
        values = [row["median_os_task_peak_delta_bytes"] for row in selected]
        low, high = min(values), max(values)
        relative_floor = low * gate["arm_discrimination_relative_floor"] if low > 0 else 0
        if high - low >= max(gate["arm_discrimination_absolute_floor_bytes"], relative_floor):
            discriminating += 1
    discrimination_prevalence = discriminating / len(matched)
    conditions = {
        "validity": not exact_failures and not stability_failures and not lifecycle_failures and not memory_failures,
        "per_arm_lifecycle_positive_os_peak": all(
            value >= gate["per_arm_lifecycle_positive_os_peak_prevalence_min"]
            for value in group_prevalence.values()
        ),
        "per_cohort_positive_os_peak": all(
            value >= gate["per_cohort_positive_os_peak_prevalence_min"]
            for value in cohort_prevalence.values()
        ),
        "reused_prepared_retained": reused_prepared_prevalence >= gate["reused_prepared_retained_prevalence_min"],
        "minimum_stable_signal_cells": len(stable_signal) >= gate["minimum_stable_signal_logical_cells"],
        "stable_replicates": stable_signal_prevalence >= gate["stable_signal_prevalence_min"],
        "representation_discrimination": discrimination_prevalence >= gate["arm_discrimination_prevalence_min"],
    }
    decision = (
        "stop_local_validity_failure" if not conditions["validity"]
        else "go_memory_calibration_only_requires_separate_candidate_freeze" if all(conditions.values())
        else "no_go_h6_routing_still_deferred"
    )
    recomputed = {
        "schema": "cm-h6-fresh-process-memory-summary/v1",
        "freeze_sha256": freeze["freeze_sha256"],
        "raw_sha256": _sha256(raw_path),
        "rows": len(rows), "logical_cells": len(logical),
        "rows_by_lane": {lane: sum(row["lane"] == lane for row in rows) for lane in ("A", "B", "C")},
        "exact_failures": exact_failures, "stability_failures": stability_failures,
        "lifecycle_failures": lifecycle_failures,
        "memory_accounting_failures": sorted(set(memory_failures)),
        "group_positive_os_peak_prevalence": group_prevalence,
        "cohort_positive_os_peak_prevalence": cohort_prevalence,
        "reused_prepared_retained_prevalence": reused_prepared_prevalence,
        "stable_signal_logical_cells": len(stable_signal),
        "stable_signal_prevalence": stable_signal_prevalence,
        "matched_arm_groups": len(matched), "discriminating_arm_groups": discriminating,
        "arm_discrimination_prevalence": discrimination_prevalence,
        "conditions": conditions, "decision": decision,
        "candidate_implemented": False, "production_routing_changed": False,
        "runpod_authorization_request_permitted": False,
        "environment": summary["environment"],
    }
    recomputed = {**recomputed, "summary_sha256": _digest(recomputed)}
    _require(_canonical(recomputed) == _canonical(summary), "summary replay mismatch")
    return {
        "schema": "cm-h6-fresh-process-memory-independent-verification/v1",
        "status": "verified",
        "decision": decision,
        "freeze_sha256": freeze["freeze_sha256"],
        "raw_sha256": _sha256(raw_path),
        "summary_sha256": _sha256(summary_path),
        "source_closure_mismatches": closure_mismatches,
        "rows_replayed": len(rows),
        "logical_cells_replayed": len(logical),
        "exact_mismatches": len(exact_failures),
        "stability_mismatches": len(stability_failures),
        "lifecycle_mismatches": len(lifecycle_failures),
        "memory_accounting_mismatches": len(set(memory_failures)),
        "summary_replay_mismatches": 0,
        "production_routing_changed": False,
        "runpod_request_permitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(
        args.project_root.resolve(), args.freeze.resolve(), args.raw.resolve(), args.summary.resolve()
    )
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

