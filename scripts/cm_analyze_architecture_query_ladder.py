"""Analyze the independently verified query-ladder run without fitting a selector."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
DEFAULT_RUN = (
    EXECUTION / "runpod-architecture-query-ladder-execute-002/evidence/run-output"
    / "architecture-query-ladder-linux-gcc-20260904-002"
)
DEFAULT_FREEZE = (
    ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904/FREEZE.json"
)
DEFAULT_PARENT_FREEZE = ROOT / "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json"
DEFAULT_CONTROLLER = EXECUTION / "runpod-architecture-query-ladder-execute-002/RUN.json"
DEFAULT_POST_INVENTORY = EXECUTION / "POST_RUN_INVENTORY.json"
DEFAULT_ATTEMPT_001 = (
    ROOT / "docs/recognition/architecture_query_ladder_followup_execution_20260903/ATTEMPT_001_STATUS.json"
)
DEFAULT_OUTPUT = EXECUTION / "ANALYSIS.json"
DEFAULT_MARKDOWN = EXECUTION / "VERIFIED_INTERPRETATION.md"
SCHEMA = "cm-architecture-query-ladder-analysis/v1"
BOOTSTRAP_REPETITIONS = 2_000
QUERY_COUNTS = (1, 4, 16, 64)
PHASES = (
    "parse_normalization_ns",
    "representation_construction_ns",
    "compilation_ns",
    "binding_ns",
    "evaluation_ns",
    "delivery_ns",
    "serialization_ns_when_applicable",
    "cleanup_ns",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _geomean(values: Iterable[float]) -> float:
    materialized = list(values)
    _require(bool(materialized) and all(value > 0 for value in materialized), "positive values required")
    return math.exp(statistics.fmean(math.log(value) for value in materialized))


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    _require(bool(ordered) and 0.0 <= probability <= 1.0, "valid percentile input required")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _bootstrap_case_geomean(case_values: Mapping[str, float], *, label: str) -> tuple[float, float]:
    case_ids = sorted(case_values)
    _require(bool(case_ids), "case clusters required")
    rng = random.Random(int(hashlib.sha256(label.encode()).hexdigest()[:16], 16))
    logs = {case_id: math.log(case_values[case_id]) for case_id in case_ids}
    draws = [
        math.exp(statistics.fmean(logs[rng.choice(case_ids)] for _ in case_ids))
        for _ in range(BOOTSTRAP_REPETITIONS)
    ]
    return _percentile(draws, 0.025), _percentile(draws, 0.975)


def _cohort(case_speedups: Mapping[str, float], selected: set[str], *, label: str) -> dict[str, Any]:
    values = {case_id: speedup for case_id, speedup in case_speedups.items() if case_id in selected}
    if not values:
        return {"cases": 0}
    low, high = _bootstrap_case_geomean(values, label=label)
    return {
        "cases": len(values),
        "case_cluster_geomean_speedup": _geomean(values.values()),
        "case_cluster_bootstrap_ci95_low": low,
        "case_cluster_bootstrap_ci95_high": high,
        "minimum_case_speedup": min(values.values()),
        "maximum_case_speedup": max(values.values()),
        "candidate_case_wins": sum(value > 1.0 for value in values.values()),
    }


def paired_speedup(
    rows: Sequence[Mapping[str, Any]], *, query_count: int, baseline: str, candidate: str,
    observed_case_ids: set[str],
) -> dict[str, Any]:
    cells: dict[tuple[str, int], dict[str, int]] = defaultdict(dict)
    for row in rows:
        if row["query_count"] != query_count or row["arm"] not in {baseline, candidate}:
            continue
        cells[(row["case_id"], row["block"])][row["arm"]] = row["timings_ns"]["accounted_total_ns"]
    _require(len(cells) == 54 * 16, "incomplete paired query cells")
    _require(all(set(cell) == {baseline, candidate} for cell in cells.values()), "unpaired query cell")
    by_case: dict[str, list[float]] = defaultdict(list)
    for (case_id, _), cell in cells.items():
        by_case[case_id].append(cell[baseline] / cell[candidate])
    case_speedups = {case_id: _geomean(values) for case_id, values in by_case.items()}
    label = f"q{query_count}:{baseline}:{candidate}"
    low, high = _bootstrap_case_geomean(case_speedups, label=label)
    return {
        "baseline": baseline,
        "candidate": candidate,
        "interpretation": "values above 1 mean candidate is faster",
        "paired_cells": len(cells),
        "case_clusters": len(case_speedups),
        "case_cluster_geomean_speedup": _geomean(case_speedups.values()),
        "case_cluster_bootstrap_ci95_low": low,
        "case_cluster_bootstrap_ci95_high": high,
        "minimum_case_speedup": min(case_speedups.values()),
        "minimum_case_id": min(case_speedups, key=case_speedups.get),
        "maximum_case_speedup": max(case_speedups.values()),
        "maximum_case_id": max(case_speedups, key=case_speedups.get),
        "candidate_case_wins": sum(value > 1.0 for value in case_speedups.values()),
        "observed_regression": _cohort(
            case_speedups, observed_case_ids, label=f"{label}:observed",
        ),
        "fresh": _cohort(
            case_speedups, set(case_speedups) - observed_case_ids, label=f"{label}:fresh",
        ),
        "case_speedups": dict(sorted(case_speedups.items())),
    }


def arm_summary(rows: Sequence[Mapping[str, Any]], *, query_count: int, arm: str) -> dict[str, Any]:
    selected = [row for row in rows if row["query_count"] == query_count and row["arm"] == arm]
    _require(len(selected) == 54 * 16, "incomplete arm/query summary")
    memory = [row["memory_measurement"] for row in selected]
    lifecycle = [item["isolation_lifecycle_ns"] for item in memory]
    totals = [row["timings_ns"]["accounted_total_ns"] for row in selected]
    return {
        "rows": len(selected),
        "median_accounted_total_ns": statistics.median(totals),
        "median_isolation_lifecycle_ns": statistics.median(lifecycle),
        "median_isolation_overhead_ns": statistics.median(
            current_lifecycle - current_total
            for current_lifecycle, current_total in zip(lifecycle, totals, strict=True)
        ),
        "median_phase_ns": {
            phase: statistics.median(row["timings_ns"][phase] for row in selected)
            for phase in PHASES
        },
        "memory": {
            "median_peak_rss_bytes": statistics.median(item["peak_rss_bytes"] for item in memory),
            "median_inherited_baseline_rss_bytes": statistics.median(
                item["inherited_baseline_rss_bytes"] for item in memory
            ),
            "median_incremental_peak_rss_bytes": statistics.median(
                item["incremental_peak_rss_bytes"] for item in memory
            ),
            "incremental_peak_nonzero_rows": sum(
                item["incremental_peak_rss_bytes"] > 0 for item in memory
            ),
        },
    }


def fixed_arm(rows: Sequence[Mapping[str, Any]], *, query_count: int, arms: Sequence[str]) -> dict[str, Any]:
    case_arm: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in rows:
        if row["query_count"] == query_count:
            case_arm[(row["case_id"], row["arm"])].append(row["timings_ns"]["accounted_total_ns"])
    case_medians = {
        key: statistics.median(values) for key, values in case_arm.items()
    }
    cases = sorted({case_id for case_id, _ in case_medians})
    _require(len(cases) == 54 and all(len(case_arm[(case_id, arm)]) == 16 for case_id in cases for arm in arms),
             "incomplete fixed-arm cells")
    regrets = {}
    for arm in arms:
        regrets[arm] = _geomean(
            case_medians[(case_id, arm)]
            / min(case_medians[(case_id, candidate)] for candidate in arms)
            for case_id in cases
        )
    winner = min(regrets, key=regrets.get)
    return {
        "best_fixed_arm": winner,
        "case_median_geomean_slowdown_to_per_case_oracle": regrets,
    }


def _write_new(path: Path, value: Any) -> None:
    if path.exists() or not path.resolve().is_relative_to(ROOT):
        raise ValueError("analysis output must be a new in-project file")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        if isinstance(value, str):
            stream.write(value)
        else:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")


def _first_sampled_advantage(by_query: Mapping[str, Mapping[str, Any]], field: str) -> int | None:
    for query_count in QUERY_COUNTS:
        if by_query[str(query_count)][field] > 1.0:
            return query_count
    return None


def render_markdown(analysis: Mapping[str, Any]) -> str:
    memory_nonzero_rows = sum(
        analysis["query_counts"][str(query_count)]["arms"][arm]["memory"][
            "incremental_peak_nonzero_rows"
        ]
        for query_count in QUERY_COUNTS
        for arm in analysis["arms"]
    )
    lines = [
        "# Verified architecture query-ladder interpretation",
        "",
        "Date: 2026-09-04",
        "Status: verified one-host result; cross-machine replication still required",
        "",
        "Retry 002 completed all 27,648 scheduled cells and the independent verifier found zero",
        "semantic, schedule, source/artifact, or memory-field mismatches. Every q1/q4/q16/q64",
        "cell returned the exact explicit residual-relation artifact.",
        "",
        "## Task-time results",
        "",
        "Values above 1.0 mean the candidate is faster than Python R2. Intervals are case-cluster",
        "bootstrap intervals conditional on this one Linux/GCC host.",
        "",
        "| q | arm | median task ms | speedup over R2 (95% CI) | case wins | minimum case |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for query_count in QUERY_COUNTS:
        lane = analysis["query_counts"][str(query_count)]
        for arm in analysis["arms"]:
            summary = lane["arms"][arm]
            if arm == "r2_topological_liveness":
                speedup, interval, wins, minimum = 1.0, "reference", "—", 1.0
            else:
                comparison = lane["speedup_over_r2"][arm]
                speedup = comparison["case_cluster_geomean_speedup"]
                interval = (
                    f"{comparison['case_cluster_bootstrap_ci95_low']:.3f}–"
                    f"{comparison['case_cluster_bootstrap_ci95_high']:.3f}"
                )
                wins = str(comparison["candidate_case_wins"])
                minimum = comparison["minimum_case_speedup"]
            lines.append(
                f"| {query_count} | `{arm}` | {summary['median_accounted_total_ns'] / 1e6:.3f} | "
                f"{speedup:.3f} ({interval}) | {wins} | {minimum:.3f} |"
            )
    native = analysis["sampled_advantage"]["native_fused_slots"]
    lines.extend([
        "",
        "The first sampled native point above R2 is "
        f"q{native['first_q_with_point_speedup']} by point estimate. "
        + (
            f"The first point whose case-bootstrap lower bound exceeds 1.0 is q{native['first_q_with_ci_low_above_one']}."
            if native["first_q_with_ci_low_above_one"] is not None
            else "No sampled point has a case-bootstrap lower bound above 1.0."
        ),
        "This is an observed four-point ladder, not an interpolated universal break-even threshold.",
        "",
        "## Memory and isolation",
        "",
        f"All {analysis['verification']['rows_checked']:,} rows have verified isolated-child RSS and lifecycle fields.",
        f"All had zero nonnegative incremental RSS ({memory_nonzero_rows:,} nonzero rows) because child peak RSS",
        "was below the inherited parent baseline. Absolute peak RSS is descriptive for this host, but these",
        "incremental measurements are not suitable for fitting a memory router.",
        "",
        f"Explicit cache cleanup consumed {analysis['cleanup']['retry_cleanup_share_of_accounted_time']:.2%}",
        "of retry task time, versus 83.05% for the invalid inherited-heap collection in attempt 001.",
        "Full fork/IPC/exit lifecycle time is retained separately and is not used to rank backend task time.",
        "",
        "## Decision boundary",
        "",
        "This run permits a one-host q-ladder interpretation and descriptive host-memory reporting. It does not",
        "permit selector fitting, neural claims, default routing changes, a website update, or a cross-machine claim.",
        "The frozen native minimum-case 0.95 floor and all unfavorable cells remain visible. A separate physical-"
        "machine/compiler replication is still required before preparing public task-labelled sections.",
        "",
        "## Execution",
        "",
        f"The retry Pod ran for {analysis['execution']['elapsed_since_create_s']:.3f} seconds at",
        f"${analysis['execution']['quoted_rate_usd_per_hour']:.2f}/hour, with estimated compute cost",
        f"${analysis['execution']['estimated_compute_cost_usd']:.6f}. Combined estimated compute cost for",
        f"attempt 001 and retry 002 is ${analysis['execution']['combined_estimated_compute_cost_usd']:.6f}.",
        "Controller cleanup and an independent post-run query both found empty v1/v2 inventories.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--parent-freeze", type=Path, default=DEFAULT_PARENT_FREEZE)
    parser.add_argument("--controller", type=Path, default=DEFAULT_CONTROLLER)
    parser.add_argument("--post-inventory", type=Path, default=DEFAULT_POST_INVENTORY)
    parser.add_argument("--attempt-001", type=Path, default=DEFAULT_ATTEMPT_001)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    freeze_path = args.freeze.resolve()
    results_path = run / "results.json"
    raw_path = run / "raw_measurements.jsonl"
    verification_path = run / "independent_verification.json"
    results = _load(results_path)
    verification = _load(verification_path)
    freeze = _load(freeze_path)
    parent_freeze = _load(args.parent_freeze.resolve())
    controller = _load(args.controller.resolve())
    post_inventory = _load(args.post_inventory.resolve())
    attempt = _load(args.attempt_001.resolve())
    _require(results.get("status") == "complete", "query-ladder result is incomplete")
    _require(verification.get("status") == "verified_complete", "query-ladder verification is incomplete")
    _require(verification.get("rows_checked") == 27_648, "query-ladder row count")
    _require(verification.get("results_sha256") == _sha256(results_path), "result binding")
    _require(verification.get("raw_measurements_sha256") == _sha256(raw_path), "raw binding")
    _require(all(verification.get(key) == 0 for key in (
        "semantic_mismatches", "schedule_mismatches", "source_or_artifact_mismatches",
        "memory_measurement_mismatches",
    )), "verified mismatch count")
    _require(
        controller.get("status") == "complete"
        and controller.get("cleanup", {}).get("owned_pod_absent") is True
        and controller.get("cleanup", {}).get("inventories") == {"v1": [], "v2": []}
        and post_inventory.get("owned_pod_absent") is True
        and post_inventory.get("inventories") == {"v1": [], "v2": []},
        "query-ladder cleanup or inventory",
    )
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
    _require(len(rows) == 27_648 and all(row["exact_check_passed"] for row in rows), "raw rows")
    _require(all(
        row.get("cleanup_method") == "cache_clear_then_isolated_child_exit"
        and row["memory_measurement"].get("isolation_lifecycle_in_accounted_timing") is False
        for row in rows
    ), "cleanup/lifecycle contract")
    arms = list(freeze["schedule"]["arms"])
    observed = set(
        parent_freeze["observed_regression_bindings"]["repeated_restriction_regression"]["case_ids"]
    )
    query_analysis = {}
    comparisons_by_arm: dict[str, dict[str, Any]] = {arm: {} for arm in arms if arm != arms[0]}
    for query_count in QUERY_COUNTS:
        comparisons = {
            arm: paired_speedup(
                rows, query_count=query_count, baseline="r2_topological_liveness",
                candidate=arm, observed_case_ids=observed,
            )
            for arm in arms if arm != "r2_topological_liveness"
        }
        for arm, comparison in comparisons.items():
            comparisons_by_arm[arm][str(query_count)] = comparison
        query_analysis[str(query_count)] = {
            "rows": 6_912,
            "arms": {
                arm: arm_summary(rows, query_count=query_count, arm=arm) for arm in arms
            },
            "speedup_over_r2": comparisons,
            "fixed_arm": fixed_arm(rows, query_count=query_count, arms=arms),
            "native_minimum_case_floor": 0.95,
            "native_minimum_case_gate_passed": (
                comparisons["native_fused_slots"]["minimum_case_speedup"] >= 0.95
            ),
        }
    sampled_advantage = {}
    for arm, by_query in comparisons_by_arm.items():
        first_point = _first_sampled_advantage(by_query, "case_cluster_geomean_speedup")
        first_ci = _first_sampled_advantage(by_query, "case_cluster_bootstrap_ci95_low")
        sampled_advantage[arm] = {
            "first_q_with_point_speedup": first_point,
            "first_q_with_ci_low_above_one": first_ci,
            "interpretation": "first observed sample only; no interpolation beyond q1/q4/q16/q64",
            "point_advantage_at_all_later_sampled_q": bool(
                first_point is not None and all(
                    by_query[str(query_count)]["case_cluster_geomean_speedup"] > 1.0
                    for query_count in QUERY_COUNTS if query_count >= first_point
                )
            ),
        }
    retry_cleanup = sum(row["timings_ns"]["cleanup_ns"] for row in rows)
    retry_total = sum(row["timings_ns"]["accounted_total_ns"] for row in rows)
    analysis = {
        "schema": SCHEMA,
        "status": "verified_interpretation_complete",
        "generated_date": "2026-09-04",
        "inputs": {
            "run_dir": run.relative_to(ROOT).as_posix(),
            "results_sha256": _sha256(results_path),
            "independent_verification_sha256": _sha256(verification_path),
            "raw_measurements_sha256": _sha256(raw_path),
            "freeze_sha256": _sha256(freeze_path),
            "controller_sha256": _sha256(args.controller.resolve()),
            "post_run_inventory_sha256": _sha256(args.post_inventory.resolve()),
            "attempt_001_status_sha256": _sha256(args.attempt_001.resolve()),
        },
        "verification": {
            "status": verification["status"],
            "rows_checked": verification["rows_checked"],
            "query_rows": verification["query_rows"],
            "counts": verification["counts"],
            "semantic_mismatches": 0,
            "schedule_mismatches": 0,
            "source_or_artifact_mismatches": 0,
            "memory_measurement_mismatches": 0,
        },
        "execution": {
            "pod_id": controller["pod_id"],
            "quoted_rate_usd_per_hour": controller["quoted_rate_usd_per_hour"],
            "elapsed_since_create_s": controller["elapsed_since_create_s"],
            "estimated_compute_cost_usd": controller["estimated_compute_cost_usd"],
            "attempt_001_estimated_compute_cost_usd": attempt["cost"]["estimated_compute_cost_usd"],
            "combined_estimated_compute_cost_usd": (
                controller["estimated_compute_cost_usd"] + attempt["cost"]["estimated_compute_cost_usd"]
            ),
            "owned_pod_absent": True,
            "controller_final_inventories": {"v1": [], "v2": []},
            "independent_post_run_inventories": {"v1": [], "v2": []},
        },
        "statistics": {
            "primary_metric": "paired accounted_total_ns speedup within query_count/case/block",
            "bootstrap_unit": "frozen case_id",
            "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
            "confidence_scope": "case heterogeneity conditional on one execution host",
            "selector_fitted": False,
        },
        "arms": arms,
        "query_counts": query_analysis,
        "sampled_advantage": sampled_advantage,
        "cleanup": {
            "retry_method": "cache_clear_then_isolated_child_exit",
            "retry_cleanup_share_of_accounted_time": retry_cleanup / retry_total,
            "retry_cleanup_seconds": retry_cleanup / 1e9,
            "retry_accounted_seconds": retry_total / 1e9,
            "attempt_001_invalid_gc_collect_share": attempt["profile_for_retry_sizing_only"][
                "cleanup_share_of_accounted_time"
            ],
        },
        "claim_boundary": {
            "four_point_query_ladder_interpretation_permitted": True,
            "descriptive_host_memory_interpretation_permitted": True,
            "interpolated_universal_break_even_claim_permitted": False,
            "memory_router_fitting_permitted": False,
            "selector_or_neural_claim_permitted": False,
            "production_routing_change_permitted": False,
            "cross_machine_claim_permitted": False,
            "website_update_permitted": False,
        },
        "publication_gates": {
            "exact_and_schedule_verification_passed": True,
            "all_query_counts_separately_timed": True,
            "all_cells_have_isolated_memory_and_lifecycle_fields": True,
            "native_minimum_case_floor_passed_at_every_query_count": all(
                query_analysis[str(query_count)]["native_minimum_case_gate_passed"]
                for query_count in QUERY_COUNTS
            ),
            "cross_machine_replication_passed": False,
            "public_update_permitted": False,
        },
    }
    _write_new(args.output.resolve(), analysis)
    _write_new(args.markdown.resolve(), render_markdown(analysis))
    print(json.dumps({
        "status": analysis["status"],
        "analysis_sha256": _sha256(args.output.resolve()),
        "markdown_sha256": _sha256(args.markdown.resolve()),
        "retry_cleanup_share": analysis["cleanup"]["retry_cleanup_share_of_accounted_time"],
        "native_first_point_advantage_q": sampled_advantage["native_fused_slots"]["first_q_with_point_speedup"],
        "native_floor_passed_at_every_q": analysis["publication_gates"][
            "native_minimum_case_floor_passed_at_every_query_count"
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
