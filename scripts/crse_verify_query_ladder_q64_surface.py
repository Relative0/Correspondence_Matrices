"""Independent standard-library replay of the sealed q64 decision surface.

This verifier deliberately imports neither ``cmbench`` nor third-party packages.
It replays the two raw schedules, timing arithmetic, frozen joint-host label rule,
charged-cost summaries, surface summaries, and fail-closed readiness gates.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGES = (
    "parse_normalization_ns",
    "representation_construction_ns",
    "compilation_ns",
    "binding_ns",
    "evaluation_ns",
    "delivery_ns",
    "serialization_ns_when_applicable",
    "cleanup_ns",
)
REQUIRED_COSTS = (
    "feature_extraction_and_control",
    "model_inference",
    "exact_verification",
    "expected_fallback",
)
ABSTAIN = "__abstain__"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside_root(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError("path must be inside the project root")
    return resolved


def _json(path: Path) -> dict[str, Any]:
    resolved = _inside_root(path)
    if not resolved.is_file() or not 0 < resolved.stat().st_size <= 64 * 1024 * 1024:
        raise ValueError(f"missing or oversized JSON input: {resolved}")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {resolved}")
    return value


def _p95(values: list[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("empty p95 sample")
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def _same_number(left: Any, right: Any) -> bool:
    return (
        type(left) in (int, float)
        and type(right) in (int, float)
        and math.isfinite(float(left))
        and math.isfinite(float(right))
        and math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-9)
    )


def _host_case_result(
    arm_blocks: dict[str, list[int]], arms: list[str], policy: dict[str, Any]
) -> dict[str, Any]:
    medians = {
        arm: float(statistics.median(arm_blocks[arm]))
        for arm in arms
    }
    ranked = sorted(arms, key=lambda arm: (medians[arm], arm))
    winner, runner_up = ranked[:2]
    winner_blocks = arm_blocks[winner]
    runner_blocks = arm_blocks[runner_up]
    ratios = [
        float(runner) / float(best)
        for best, runner in zip(winner_blocks, runner_blocks, strict=True)
    ]
    ordered_ratios = sorted(ratios)
    paired_wins = sum(
        float(best) < float(runner)
        for best, runner in zip(winner_blocks, runner_blocks, strict=True)
    )
    median_speedup = medians[runner_up] / medians[winner]
    win_fraction = paired_wins / len(winner_blocks)
    p10 = ordered_ratios[int(0.10 * (len(ordered_ratios) - 1))]
    conditions = {
        "median_runner_up_speedup": median_speedup
        >= policy["minimum_median_runner_up_speedup"],
        "paired_block_win_fraction": win_fraction
        >= policy["minimum_paired_block_win_fraction"],
        "paired_p10_speedup": p10 >= policy["minimum_p10_paired_speedup"],
    }
    return {
        "winner": winner,
        "runner_up": runner_up,
        "medians_ns": medians,
        "median_runner_up_speedup": median_speedup,
        "paired_block_wins": paired_wins,
        "paired_blocks": len(winner_blocks),
        "paired_block_win_fraction": win_fraction,
        "paired_p10_speedup": p10,
        "p10_method": "frozen_lower_order_statistic_floor_0_10_n_minus_1",
        "conditions": conditions,
        "material_label": winner if all(conditions.values()) else ABSTAIN,
    }


def _read_host(
    run_dir: Path,
    host_id: str,
    child: dict[str, Any],
    oracles: dict[str, Any],
    arms: list[str],
    mismatches: list[str],
) -> dict[str, Any]:
    host_dir = run_dir / host_id
    raw_path = host_dir / "RAW.jsonl"
    verification_path = host_dir / "INDEPENDENT_VERIFICATION.json"
    result_path = host_dir / "RESULT.json"
    charged_path = host_dir / "CHARGED_COSTS.json"
    preflight_path = host_dir / "HOST_PREFLIGHT.json"
    verification = _json(verification_path)
    result = _json(result_path)
    charged = _json(charged_path)
    preflight = _json(preflight_path)
    schedule = child["schedule"]
    cases = schedule["case_order"]
    blocks = schedule["blocks"]
    expected_cells = blocks * len(cases) * len(arms)
    tables = {
        case_id: {arm: [None] * blocks for arm in arms}
        for case_id in cases
    }
    status_counts: Counter[str] = Counter()
    schedule_mismatches = 0
    semantic_mismatches = 0
    timing_mismatches = 0
    completed_rows = 0
    with raw_path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if not line.strip():
                continue
            row = json.loads(line)
            completed_rows += 1
            status_counts[str(row.get("status"))] += 1
            block, remainder = divmod(index, len(cases) * len(arms))
            case_position, arm_position = divmod(remainder, len(arms))
            if block >= blocks:
                schedule_mismatches += 1
                continue
            case_id = cases[case_position]
            arm_order = schedule["arm_orders"][block]
            arm = arm_order[arm_position]
            expected = {
                "block": block,
                "case_position": case_position,
                "case_id": case_id,
                "arm_position": arm_position,
                "arm_order": arm_order,
                "arm": arm,
            }
            if any(row.get(key) != value for key, value in expected.items()):
                schedule_mismatches += 1
            oracle = oracles["cases"].get(case_id, {})
            if not (
                row.get("status") == "ok"
                and row.get("reason") == "completed"
                and row.get("exact_check_passed") is True
                and row.get("worker_exit_code") == 0
                and row.get("worker_stderr") == ""
                and row.get("query_count") == schedule["query_count"]
                and row.get("output_sha256") == oracle.get("q64_output_sha256")
            ):
                semantic_mismatches += 1
            timings = row.get("timings_ns")
            valid_timing = (
                isinstance(timings, dict)
                and set(timings) == {*STAGES, "accounted_total_ns"}
                and all(type(timings.get(name)) is int and timings[name] >= 0 for name in STAGES)
                and type(timings.get("accounted_total_ns")) is int
                and timings["accounted_total_ns"] > 0
                and timings["accounted_total_ns"] == sum(timings[name] for name in STAGES)
            )
            if not valid_timing:
                timing_mismatches += 1
            else:
                if tables[case_id][arm][block] is not None:
                    schedule_mismatches += 1
                tables[case_id][arm][block] = timings["accounted_total_ns"]
    schedule_mismatches += abs(expected_cells - completed_rows)
    if any(
        value is None
        for by_arm in tables.values()
        for values in by_arm.values()
        for value in values
    ):
        schedule_mismatches += 1

    raw_sha = _file_sha256(raw_path)
    charged_sha = _file_sha256(charged_path)
    result_sha = _file_sha256(result_path)
    preflight_sha = _file_sha256(preflight_path)
    verification_checks = {
        "status": verification.get("status") == "verified_complete",
        "completed_rows": verification.get("completed_rows") == completed_rows,
        "expected_cells": verification.get("expected_cells") == expected_cells,
        "schedule_mismatches": verification.get("schedule_mismatches") == schedule_mismatches == 0,
        "semantic_mismatches": verification.get("semantic_mismatches") == semantic_mismatches == 0,
        "timing_mismatches": verification.get("timing_mismatches") == timing_mismatches == 0,
        "source_mismatches": verification.get("source_or_artifact_mismatches") == 0,
        "charged_mismatches": verification.get("charged_cost_mismatches") == 0,
        "raw_sha256": verification.get("raw_file_sha256") == raw_sha,
        "charged_sha256": verification.get("charged_cost_file_sha256") == charged_sha,
        "result_sha256": verification.get("result_file_sha256") == result_sha,
        "preflight_sha256": verification.get("host_preflight_file_sha256") == preflight_sha,
        "retention": verification.get("all_failures_refusals_and_zeroes_retained") is True,
        "same_host_costs": verification.get("p95_costs_measured_same_host") is True,
    }
    for name, passed in verification_checks.items():
        if not passed:
            mismatches.append(f"{host_id}:host_verification:{name}")
    expected_counts = {
        "ok": status_counts["ok"],
        "failed": status_counts["failed"],
        "refused": status_counts["refused"],
        "timeout": status_counts["timeout"],
    }
    if not (
        result.get("status") == "complete"
        and result.get("completed_rows") == completed_rows
        and result.get("expected_cells") == expected_cells
        and result.get("counts") == expected_counts
        and result.get("raw_file_sha256") == raw_sha
    ):
        mismatches.append(f"{host_id}:result_summary")
    for name, samples in charged.get("samples_ns_per_case", {}).items():
        if name not in charged.get("p95_ns_per_case", {}) or not _same_number(
            _p95(samples), charged["p95_ns_per_case"][name]
        ):
            mismatches.append(f"{host_id}:charged_p95:{name}")
    return {
        "host_id": host_id,
        "tables": tables,
        "charged": charged,
        "preflight": preflight,
        "verification": verification,
        "verification_sha256": _file_sha256(verification_path),
        "raw_sha256": raw_sha,
        "charged_sha256": charged_sha,
        "result_sha256": result_sha,
        "preflight_sha256": preflight_sha,
        "completed_rows": completed_rows,
        "expected_cells": expected_cells,
        "status_counts": expected_counts,
        "schedule_mismatches": schedule_mismatches,
        "semantic_mismatches": semantic_mismatches,
        "timing_mismatches": timing_mismatches,
    }


def replay(run_dir: Path, freeze_path: Path, host_ids: list[str]) -> dict[str, Any]:
    run_dir = _inside_root(run_dir)
    freeze_path = _inside_root(freeze_path)
    if len(host_ids) != 2 or len(set(host_ids)) != 2:
        raise ValueError("exactly two distinct host IDs are required")
    child = _json(run_dir / "CHILD_FREEZE.json")
    freeze = _json(freeze_path)
    oracles = _json(run_dir / "ORACLES.json")
    evidence = _json(run_dir / "NORMALIZED_EVIDENCE.json")
    surface_verification = _json(run_dir / "SURFACE_INDEPENDENT_VERIFICATION.json")
    assessment = _json(run_dir / "SURFACE_ASSESSMENT.json")
    mismatches: list[str] = []
    freeze_sha = _file_sha256(freeze_path)
    if freeze_sha != child["parent"]["file_sha256"]:
        mismatches.append("parent_freeze_file_sha256")
    if _digest(freeze["exact_task_contract"]) != child["parent"]["task_contract_sha256"]:
        mismatches.append("task_contract_sha256")
    if _digest(freeze["label_policy"]) != child["parent"]["label_policy_sha256"]:
        mismatches.append("label_policy_sha256")
    if _file_sha256(run_dir / "ORACLES.json") != child["oracles"]["file_sha256"]:
        mismatches.append("oracles_file_sha256")
    arms = list(freeze["exact_task_contract"]["arms"])
    hosts = {
        host_id: _read_host(run_dir, host_id, child, oracles, arms, mismatches)
        for host_id in host_ids
    }
    machines = {row["verification"].get("physical_machine_sha256") for row in hosts.values()}
    if len(machines) != 2:
        mismatches.append("physical_machine_identities_not_distinct")

    frozen_by_id = {row["case_id"]: row for row in freeze["cohort"]["cases"]}
    policy = freeze["label_policy"]
    host_results: dict[str, dict[str, dict[str, Any]]] = {}
    for host_id, host in hosts.items():
        host_results[host_id] = {
            case_id: _host_case_result(by_arm, arms, policy)
            for case_id, by_arm in host["tables"].items()
        }
    labels: dict[str, str] = {}
    case_results = []
    threshold_abstentions = []
    disagreements = []
    for case_id in child["schedule"]["case_order"]:
        material = {host_id: host_results[host_id][case_id]["material_label"] for host_id in host_ids}
        non_abstain = {label for label in material.values() if label != ABSTAIN}
        if ABSTAIN in material.values():
            label = ABSTAIN
            reason = "host_threshold_failure"
            threshold_abstentions.append(case_id)
        elif len(non_abstain) != 1:
            label = ABSTAIN
            reason = "cross_host_winner_disagreement"
            disagreements.append(case_id)
        else:
            label = next(iter(non_abstain))
            reason = "stable_material_winner"
        labels[case_id] = label
        frozen_case = frozen_by_id[case_id]
        case_results.append({
            "case_id": case_id,
            "source_group_sha256": frozen_case["source_group_sha256"],
            "split": frozen_case["split"],
            "joint_label": label,
            "joint_label_reason": reason,
            "host_results": {host_id: host_results[host_id][case_id] for host_id in host_ids},
        })
    non_abstain_labels = {case_id: label for case_id, label in labels.items() if label != ABSTAIN}
    label_counts = Counter(non_abstain_labels.values())
    split_sizes = freeze["cohort"]["source_group_counts_by_split"]
    split_counts = Counter(frozen_by_id[case_id]["split"] for case_id in non_abstain_labels)
    coverage = len(non_abstain_labels) / len(labels)
    coverage_by_split = {split: split_counts[split] / size for split, size in split_sizes.items()}
    label_sha = _digest(labels)
    if assessment.get("label_table_sha256") != label_sha:
        mismatches.append("assessment_label_table_sha256")
    if assessment.get("case_results_sha256") != _digest(case_results):
        mismatches.append("assessment_case_results_sha256")
    summary_checks = {
        "source_groups_per_label": assessment.get("source_groups_per_label") == dict(sorted(label_counts.items())),
        "stable_count": assessment.get("source_groups_with_stable_material_winner") == len(non_abstain_labels),
        "coverage": _same_number(assessment.get("non_abstain_coverage"), coverage),
        "coverage_by_split": assessment.get("non_abstain_coverage_by_split") == coverage_by_split,
        "threshold_abstentions": assessment.get("threshold_abstention_cases") == sorted(threshold_abstentions),
        "disagreements": assessment.get("cross_host_winner_disagreement_cases") == sorted(disagreements),
        "winner_arms": assessment.get("material_winner_arms") == sorted(label_counts),
    }
    for name, passed in summary_checks.items():
        if not passed:
            mismatches.append(f"surface_summary:{name}")

    replication_by_id = {row["replication_id"]: row for row in evidence["replications"]}
    economics: dict[str, dict[str, Any]] = {}
    for host_id, host in hosts.items():
        replication = replication_by_id.get(host_id, {})
        if replication.get("block_timings_sha256") != _digest(host["tables"]):
            mismatches.append(f"{host_id}:normalized_block_table")
        expected_identity = {
            "physical_machine_sha256": host["verification"].get("physical_machine_sha256"),
            "compiler_sha256": host["verification"].get("compiler_sha256"),
            "independent_verification_sha256": host["verification_sha256"],
        }
        for name, value in expected_identity.items():
            if replication.get(name) != value:
                mismatches.append(f"{host_id}:normalized_identity:{name}")
        medians = {
            case_id: {arm: float(statistics.median(values)) for arm, values in by_arm.items()}
            for case_id, by_arm in host["tables"].items()
        }
        fixed_sums = {arm: sum(row[arm] for row in medians.values()) for arm in arms}
        best = min(arms, key=lambda arm: (fixed_sums[arm], arms.index(arm)))
        oracle_sum = sum(min(row.values()) for row in medians.values())
        fallback = 0.0
        fallback_dispatch = host["charged"]["p95_ns_per_case"]["fallback_dispatch"]
        for case_id, label in labels.items():
            if label == ABSTAIN:
                row = medians[case_id]
                fallback += max(0.0, row[best] - min(row.values())) + fallback_dispatch
        fallback /= len(labels)
        costs = {
            name: host["charged"]["p95_ns_per_case"][name]
            for name in REQUIRED_COSTS[:-1]
        }
        costs["expected_fallback"] = fallback
        for name, value in costs.items():
            if not _same_number(replication.get("p95_costs_ns_per_case", {}).get(name), value):
                mismatches.append(f"{host_id}:normalized_cost:{name}")
        gross = fixed_sums[best] / oracle_sum
        fully_charged = fixed_sums[best] / (oracle_sum + len(labels) * sum(costs.values()))
        economics[host_id] = {
            "best_fixed_arm": best,
            "best_fixed_sum_ns": fixed_sums[best],
            "oracle_sum_ns": oracle_sum,
            "gross_speedup": gross,
            "fully_charged_speedup": fully_charged,
            "p95_costs_ns_per_case": costs,
        }
        packaged = surface_verification.get("economics_by_host", {}).get(host_id, {})
        for name in ("best_fixed_sum_ns", "oracle_sum_ns", "gross_speedup", "fully_charged_speedup"):
            if not _same_number(packaged.get(name), economics[host_id][name]):
                mismatches.append(f"{host_id}:surface_economics:{name}")
        if packaged.get("best_fixed_arm") != best:
            mismatches.append(f"{host_id}:surface_economics:best_fixed_arm")

    surface_path = run_dir / "SURFACE_INDEPENDENT_VERIFICATION.json"
    if evidence.get("surface_independent_verification_sha256") != _file_sha256(surface_path):
        mismatches.append("surface_verification_file_sha256")
    if surface_verification.get("label_table_sha256") != label_sha:
        mismatches.append("surface_verification_label_table_sha256")
    if not _same_number(surface_verification.get("coverage"), coverage):
        mismatches.append("surface_verification_coverage")

    readiness_blockers = []
    minimum_label_groups = policy["minimum_source_groups_per_non_abstain_label"]
    if len(label_counts) < 2 or any(value < minimum_label_groups for value in label_counts.values()):
        readiness_blockers.append("insufficient_source_groups_per_label")
    if len(label_counts) < 2:
        readiness_blockers.append("fewer_than_two_material_winner_arms")
    if coverage < 0.80:
        readiness_blockers.append("decision_surface_coverage_below_0_80")
    if any(value < 0.80 for value in coverage_by_split.values()):
        readiness_blockers.append("decision_surface_split_coverage_below_0_80")
    for host_id in host_ids:
        if economics[host_id]["gross_speedup"] < freeze["charged_cost_contract"]["gross_and_fully_charged_minimum_speedup"]:
            readiness_blockers.append(f"gross_headroom_below_1_10:{host_id}")
        if economics[host_id]["fully_charged_speedup"] < freeze["charged_cost_contract"]["gross_and_fully_charged_minimum_speedup"]:
            readiness_blockers.append(f"charged_headroom_below_1_10:{host_id}")

    host_summary = {
        host_id: {
            "completed_rows": host["completed_rows"],
            "expected_cells": host["expected_cells"],
            "status_counts": host["status_counts"],
            "raw_file_sha256": host["raw_sha256"],
            "independent_verification_file_sha256": host["verification_sha256"],
            "physical_machine_sha256": host["verification"].get("physical_machine_sha256"),
            "schedule_mismatches": host["schedule_mismatches"],
            "semantic_mismatches": host["semantic_mismatches"],
            "timing_mismatches": host["timing_mismatches"],
        }
        for host_id, host in hosts.items()
    }
    return {
        "schema": "crse-query-ladder-q64-stdlib-surface-replay/v1",
        "status": "verified_complete" if not mismatches else "failed",
        "method": "independent_standard_library_raw_schedule_oracle_timing_label_cost_and_summary_replay",
        "project_imports": [],
        "third_party_imports": [],
        "verifier_source_sha256": _file_sha256(Path(__file__)),
        "inputs": {
            "parent_freeze_file_sha256": freeze_sha,
            "child_freeze_file_sha256": _file_sha256(run_dir / "CHILD_FREEZE.json"),
            "oracles_file_sha256": _file_sha256(run_dir / "ORACLES.json"),
            "normalized_evidence_file_sha256": _file_sha256(run_dir / "NORMALIZED_EVIDENCE.json"),
            "surface_verification_file_sha256": _file_sha256(surface_path),
            "surface_assessment_file_sha256": _file_sha256(run_dir / "SURFACE_ASSESSMENT.json"),
        },
        "hosts": host_summary,
        "surface": {
            "label_table_sha256": label_sha,
            "source_groups": len(labels),
            "source_groups_per_label": dict(sorted(label_counts.items())),
            "abstentions": len(labels) - len(non_abstain_labels),
            "non_abstain_coverage": coverage,
            "non_abstain_coverage_by_split": coverage_by_split,
            "cross_host_winner_disagreements": len(disagreements),
            "economics_by_host": economics,
        },
        "readiness": {
            "status": "eligible_for_development_experiment_design" if not readiness_blockers else "abstained",
            "development_training_eligible": not readiness_blockers,
            "blockers": readiness_blockers,
            "training_performed": False,
            "production_routing_permitted": False,
        },
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "all_failures_refusals_and_zeroes_retained": all(
            host["verification"].get("all_failures_refusals_and_zeroes_retained") is True
            for host in hosts.values()
        ),
        "prospective_cases_consumed": 0,
        "models_trained": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--host", action="append", required=True)
    parser.add_argument("--output", default="STDLIB_SUMMARY_REPLAY.json")
    args = parser.parse_args()
    try:
        result = replay(args.run_dir, args.freeze, args.host)
        output = _inside_root(args.run_dir) / args.output
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "error": type(exc).__name__, "message": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({
        "status": result["status"],
        "mismatch_count": result["mismatch_count"],
        "label_table_sha256": result["surface"]["label_table_sha256"],
        "coverage": result["surface"]["non_abstain_coverage"],
        "readiness": result["readiness"],
        "output": str(output),
    }, sort_keys=True))
    return 0 if result["status"] == "verified_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
