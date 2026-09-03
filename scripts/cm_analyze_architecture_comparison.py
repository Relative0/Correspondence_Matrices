"""Analyze a verified architecture-comparison campaign without fitting a selector."""
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
DEFAULT_RUN = (
    ROOT
    / "docs/recognition/architecture_comparison_execution_retry_20260903"
    / "runpod-architecture-comparison-retry-002/evidence/run-output"
    / "architecture-comparison-linux-gcc-20260903-002"
)
DEFAULT_FREEZE = (
    ROOT / "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json"
)
DEFAULT_CONTROLLER = (
    ROOT
    / "docs/recognition/architecture_comparison_execution_retry_20260903"
    / "runpod-architecture-comparison-retry-002/RUN.json"
)
SCHEMA = "cm-architecture-comparison-analysis/v1"
BOOTSTRAP_REPETITIONS = 2_000
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


def _bootstrap_case_geomean(
    case_speedups: Mapping[str, float], *, label: str, repetitions: int = BOOTSTRAP_REPETITIONS,
) -> tuple[float, float]:
    case_ids = sorted(case_speedups)
    _require(bool(case_ids), "case clusters required")
    seed = int(hashlib.sha256(label.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    logs = {case_id: math.log(case_speedups[case_id]) for case_id in case_ids}
    draws = []
    for _ in range(repetitions):
        draws.append(math.exp(statistics.fmean(logs[rng.choice(case_ids)] for _ in case_ids)))
    return _percentile(draws, 0.025), _percentile(draws, 0.975)


def _cohort(case_speedups: Mapping[str, float], case_ids: set[str], *, label: str) -> dict[str, Any]:
    selected = {key: value for key, value in case_speedups.items() if key in case_ids}
    if not selected:
        return {"cases": 0}
    low, high = _bootstrap_case_geomean(selected, label=label)
    return {
        "cases": len(selected),
        "case_cluster_geomean_speedup": _geomean(selected.values()),
        "case_cluster_bootstrap_ci95_low": low,
        "case_cluster_bootstrap_ci95_high": high,
        "minimum_case_speedup": min(selected.values()),
        "maximum_case_speedup": max(selected.values()),
        "candidate_case_wins": sum(value > 1.0 for value in selected.values()),
    }


def paired_speedup(
    rows: Sequence[Mapping[str, Any]], *, lane: str, baseline: str, candidate: str,
    sublane: str | None = None, label: str | None = None,
    observed_case_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Return baseline/candidate speedup, paired within case and block."""
    cells: dict[tuple[str, int], dict[str, int]] = defaultdict(dict)
    for row in rows:
        if row["status"] != "ok" or row["lane"] != lane:
            continue
        if sublane is not None and row.get("sublane") != sublane:
            continue
        arm = str(row["arm"])
        if arm not in {baseline, candidate}:
            continue
        key = (str(row["case_id"]), int(row["block"]))
        _require(arm not in cells[key], "duplicate paired cell")
        cells[key][arm] = int(row["timings_ns"]["accounted_total_ns"])
    _require(bool(cells), f"no paired cells for {lane} {baseline} {candidate}")
    _require(all(set(cell) == {baseline, candidate} for cell in cells.values()), "incomplete paired cells")
    by_case: dict[str, list[float]] = defaultdict(list)
    for (case_id, _), cell in cells.items():
        by_case[case_id].append(cell[baseline] / cell[candidate])
    case_speedups = {case_id: _geomean(values) for case_id, values in by_case.items()}
    comparison_label = label or f"{lane}:{sublane}:{baseline}:{candidate}"
    low, high = _bootstrap_case_geomean(case_speedups, label=comparison_label)
    result: dict[str, Any] = {
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
        "case_speedups": dict(sorted(case_speedups.items())),
    }
    if observed_case_ids is not None:
        result["observed_regression"] = _cohort(
            case_speedups, observed_case_ids, label=f"{comparison_label}:observed"
        )
        result["fresh"] = _cohort(
            case_speedups, set(case_speedups) - observed_case_ids,
            label=f"{comparison_label}:fresh",
        )
    return result


def _arm_summary(rows: Sequence[Mapping[str, Any]], lane: str) -> dict[str, Any]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["lane"] == lane and row["status"] == "ok":
            grouped[str(row["arm"])].append(row)
    result = {}
    for arm, values in sorted(grouped.items()):
        total = [int(row["timings_ns"]["accounted_total_ns"]) for row in values]
        cleanup = [int(row["timings_ns"]["cleanup_ns"]) for row in values]
        result[arm] = {
            "rows": len(values),
            "median_accounted_total_ns": statistics.median(total),
            "median_non_cleanup_work_ns": statistics.median(
                current - current_cleanup for current, current_cleanup in zip(total, cleanup, strict=True)
            ),
            "median_phase_ns": {
                phase: statistics.median(int(row["timings_ns"][phase]) for row in values)
                for phase in PHASES
            },
        }
    return result


def _fixed_winner(
    rows: Sequence[Mapping[str, Any]], *, sublane: str, arms: Sequence[str],
) -> dict[str, Any]:
    cells: dict[tuple[str, int], dict[str, int]] = defaultdict(dict)
    for row in rows:
        if row["lane"] != "D" or row["status"] != "ok" or row.get("sublane") != sublane:
            continue
        arm = str(row["arm"])
        if arm in arms:
            cells[(str(row["case_id"]), int(row["block"]))][arm] = int(
                row["timings_ns"]["accounted_total_ns"]
            )
    _require(bool(cells) and all(set(cell) == set(arms) for cell in cells.values()), "invalid task cells")
    regrets = {
        arm: _geomean(cell[arm] / min(cell.values()) for cell in cells.values()) for arm in arms
    }
    winner = min(regrets, key=regrets.get)
    comparisons = {
        arm: paired_speedup(
            rows, lane="D", baseline=arm, candidate=winner, sublane=sublane,
            label=f"D:{sublane}:{winner}:over:{arm}",
        )
        for arm in arms if arm != winner
    }
    return {
        "fixed_winner": winner,
        "geomean_slowdown_to_cell_oracle": regrets,
        "winner_speedup_over": comparisons,
    }


def _fmt(value: float) -> str:
    return f"{value:.3f}x"


def _ci(value: Mapping[str, Any]) -> str:
    return (
        f"{_fmt(value['case_cluster_geomean_speedup'])} "
        f"[{_fmt(value['case_cluster_bootstrap_ci95_low'])}, "
        f"{_fmt(value['case_cluster_bootstrap_ci95_high'])}]"
    )


def _markdown(analysis: Mapping[str, Any]) -> str:
    a = analysis["lanes"]["A"]
    b = analysis["lanes"]["B"]
    c = analysis["lanes"]["C"]
    lines = [
        "# Architecture comparison retry 002 — verified interpretation",
        "",
        "Date: 2026-09-03  ",
        "Scope: exact non-neural CM-family comparisons on Linux/GCC  ",
        "Status: **verified complete; no routing, selector, training, website, or publication change**",
        "",
        "## Outcome",
        "",
        f"The independent verifier accepted all {analysis['verification']['rows_checked']:,} scheduled rows with "
        "zero semantic, schedule, source, or artifact mismatches. The single RunPod was deleted; both final "
        f"inventories were empty. Estimated compute cost was ${analysis['execution']['estimated_compute_cost_usd']:.6f}.",
        "",
        "Speedups below use paired accounted-total time, cluster by frozen case, and show a deterministic "
        "case-cluster bootstrap 95% interval. They are conditional on this one execution host.",
        "",
        "## Lane A — complete explicit relation",
        "",
        "| Candidate | Speedup over dense CM | Speedup over current direct BitSet | Median total |",
        "|---|---:|---:|---:|",
    ]
    for arm in a["arm_order"]:
        dense = "1.000x" if arm == "cm_dense_full_reinflation" else _fmt(
            a["speedup_over_dense_cm"][arm]["case_cluster_geomean_speedup"]
        )
        bitset = "1.000x" if arm == "direct_expression_bitset" else _fmt(
            a["speedup_over_direct_bitset"][arm]["case_cluster_geomean_speedup"]
        )
        median_ms = a["arms"][arm]["median_accounted_total_ns"] / 1_000_000
        lines.append(f"| `{arm}` | {dense} | {bitset} | {median_ms:.3f} ms |")
    best_cm = a["direct_bitset_over_best_fixed_cm"]
    lines.extend([
        "",
        f"The current direct-expression BitSet was faster than the best fixed CM-family arm "
        f"(`{best_cm['candidate']}`) in all {best_cm['case_clusters']} runnable cases. The CM arm's "
        f"speedup over BitSet was {_ci(best_cm)}; values below 1 mean it remained slower. The same CM arm "
        f"was {_fmt(a['best_fixed_cm_over_dense']['case_cluster_geomean_speedup'])} faster than dense CM, "
        "so the packed/recursive architecture is useful but is not the complete-vector winner.",
        "",
        "## Lane B — repeated restrictions",
        "",
        "| Candidate | Speedup over R2 | Speedup over projection | Median total |",
        "|---|---:|---:|---:|",
    ])
    for arm in b["arm_order"]:
        r2 = "1.000x" if arm == "r2_topological_liveness" else _fmt(
            b["speedup_over_r2"][arm]["case_cluster_geomean_speedup"]
        )
        projection = "1.000x" if arm == "current_projection" else _fmt(
            b["speedup_over_projection"][arm]["case_cluster_geomean_speedup"]
        )
        median_ms = b["arms"][arm]["median_accounted_total_ns"] / 1_000_000
        lines.append(f"| `{arm}` | {r2} | {projection} | {median_ms:.3f} ms |")
    native = b["speedup_over_r2"]["native_fused_slots"]
    lines.extend([
        "",
        f"Native fused slots were {_ci(native)} over R2 overall and "
        f"{_fmt(native['observed_regression']['case_cluster_geomean_speedup'])} on the 18-case observed C36 "
        f"cohort, but only {_fmt(native['fresh']['case_cluster_geomean_speedup'])} on the 36 fresh cases. "
        f"The minimum case was {_fmt(native['minimum_case_speedup'])} (`{native['minimum_case_id']}`), "
        "below the frozen 0.95 floor. Native therefore remains guarded/opt-in.",
        "",
        "This run does **not** establish q1/q4/q16 break-even points. Every timed Lane B row executes q64; "
        "q1/q4/q16 are prefix correctness digests, not separately timed cells. A corrected follow-up freeze "
        "is required before making query-count crossover claims.",
        "",
        "## Lane C — related multi-root outputs",
        "",
        f"- Python sharing-aware union versus separate roots: {_ci(c['python_union_over_separate'])}; "
        f"all {c['python_union_over_separate']['case_clusters']} cases favored union.",
        f"- Native union versus separate arenas: {_ci(c['native_union_over_separate'])}; "
        f"all {c['native_union_over_separate']['case_clusters']} cases favored union.",
        f"- Native union versus Python union: {_ci(c['native_union_over_python_union'])}. The aggregate was "
        "near parity and the fresh width-8 cases regressed, so the supported conclusion is union sharing, "
        "not unconditional native superiority.",
        "",
        "## Lane D — smaller task-specific queries",
        "",
        "| Task / lifecycle | Fastest fixed backend | Speedup over CM |",
        "|---|---|---:|",
    ])
    for key, value in analysis["lanes"]["D"]["tasks"].items():
        winner = value["fixed_winner"]
        cm_arm = next((arm for arm in value["winner_speedup_over"] if arm.split("/")[0] == "cm"), None)
        speedup = (
            _fmt(value["winner_speedup_over"][cm_arm]["case_cluster_geomean_speedup"])
            if cm_arm else "1.000x"
        )
        lines.append(f"| `{key}` | `{winner}` | {speedup} |")
    lines.extend([
        "",
        "The task-matched controls win these bounded smaller-query lanes. CM remains useful as an exact "
        "diagnostic/reference representation, not a universal replacement for CNF/CSE/SAT task paths.",
        "",
        "## Limits and next boundary",
        "",
        "- Per-row RSS is the process-wide `ru_maxrss` high-water mark and is nondecreasing through the run; "
        "it cannot support per-arm memory routing or memory-win claims.",
        "- The result is one verified Linux/GCC host execution. The freeze still requires a separate "
        "cross-machine replication before public cross-machine claims.",
        "- No selector was fitted and no neural conclusion is permitted. The q64 native result itself "
        "contains case-specific regressions, while the previously exposed C36-only portfolio had no useful "
        "selector headroom.",
        "- Before any `expert.html` update, freeze and run separately timed q1/q4/q16/q64 cells and add "
        "per-cell memory measurement if memory comparisons are intended. Retain the historical Windows-only "
        "1.472x result unchanged and label any new section by task, source freeze, platform, and date.",
        "",
    ])
    return "\n".join(lines)


def analyze(run_dir: Path, freeze_path: Path, controller_path: Path) -> dict[str, Any]:
    results_path = run_dir / "results.json"
    verification_path = run_dir / "independent_verification.json"
    raw_path = run_dir / "raw_measurements.jsonl"
    results = _load(results_path)
    verification = _load(verification_path)
    freeze = _load(freeze_path)
    controller = _load(controller_path)
    _require(results["status"] == "complete", "campaign is incomplete")
    _require(verification["status"] == "verified_complete", "campaign is not independently verified")
    _require(verification["performance_interpretation_permitted"] is True, "interpretation is prohibited")
    _require(verification["raw_measurements_sha256"] == _sha256(raw_path), "raw measurement hash mismatch")
    _require(verification["results_sha256"] == _sha256(results_path), "result hash mismatch")
    _require(
        all(verification[key] == 0 for key in (
            "schedule_mismatches", "semantic_mismatches", "source_or_artifact_mismatches"
        )),
        "verified mismatch count is nonzero",
    )
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
    _require(len(rows) == verification["rows_checked"], "row count mismatch")
    _require(all(row["exact_check_passed"] for row in rows if row["status"] == "ok"), "inexact row")

    observed = freeze["observed_regression_bindings"]
    observed_a = set(observed["public_complete_relation_regression"]["case_ids"])
    observed_b = set(observed["repeated_restriction_regression"]["case_ids"])
    observed_c = set(observed["related_root_regression"]["case_ids"])
    arms_a = list(freeze["schedules"]["A"]["arms"])
    arms_b = list(freeze["schedules"]["B"]["arms"])
    arms_c = list(freeze["schedules"]["C"]["arms"])

    speed_a_dense = {
        arm: paired_speedup(
            rows, lane="A", baseline="cm_dense_full_reinflation", candidate=arm,
            observed_case_ids=observed_a,
        )
        for arm in arms_a if arm != "cm_dense_full_reinflation"
    }
    speed_a_bitset = {
        arm: paired_speedup(
            rows, lane="A", baseline="direct_expression_bitset", candidate=arm,
            observed_case_ids=observed_a,
        )
        for arm in arms_a if arm != "direct_expression_bitset"
    }
    cm_arms = [arm for arm in arms_a if arm.startswith("cm_")]
    best_cm = max(
        cm_arms,
        key=lambda arm: 1.0 if arm == "cm_dense_full_reinflation"
        else speed_a_dense[arm]["case_cluster_geomean_speedup"],
    )

    speed_b_r2 = {
        arm: paired_speedup(
            rows, lane="B", baseline="r2_topological_liveness", candidate=arm,
            observed_case_ids=observed_b,
        )
        for arm in arms_b if arm != "r2_topological_liveness"
    }
    speed_b_projection = {
        arm: paired_speedup(
            rows, lane="B", baseline="current_projection", candidate=arm,
            observed_case_ids=observed_b,
        )
        for arm in arms_b if arm != "current_projection"
    }
    lane_b_rows = [row for row in rows if row["lane"] == "B" and row["status"] == "ok"]
    query_counts = sorted({int(row["resources"]["queries"]) for row in lane_b_rows})
    checkpoint_counts = sorted({int(key) for row in lane_b_rows for key in row["checkpoint_output_sha256"]})

    tasks = {}
    for sublane in sorted(freeze["schedules"]["D"]["task_sublanes"]):
        for lifecycle in freeze["schedules"]["D"]["task_lifecycles"]:
            arms = [f"{backend}/{lifecycle}" for backend in freeze["schedules"]["D"]["task_sublanes"][sublane]["arms"]]
            tasks[f"{sublane}/{lifecycle}"] = _fixed_winner(rows, sublane=sublane, arms=arms)
    reload_arms = list(freeze["schedules"]["D"]["structural_reload"]["arms"])
    tasks["structural_reload"] = _fixed_winner(
        rows, sublane="structural_reload", arms=reload_arms
    )

    peak_rss = [int(row["peak_rss_bytes"]) for row in rows]
    rss_nondecreasing = all(left <= right for left, right in zip(peak_rss, peak_rss[1:]))
    native_gate = float(freeze["publication_gates"]["native_single_root_minimum_case_floor"])
    native_vs_r2 = speed_b_r2["native_fused_slots"]
    analysis = {
        "schema": SCHEMA,
        "status": "verified_interpretation_complete",
        "generated_date": "2026-09-03",
        "inputs": {
            "run_dir": str(run_dir.relative_to(ROOT)).replace("\\", "/"),
            "results_sha256": _sha256(results_path),
            "independent_verification_sha256": _sha256(verification_path),
            "raw_measurements_sha256": _sha256(raw_path),
            "freeze_sha256": _sha256(freeze_path),
            "controller_state_sha256": _sha256(controller_path),
        },
        "verification": {
            "status": verification["status"],
            "rows_checked": verification["rows_checked"],
            "counts": verification["counts"],
            "lane_rows": verification["lane_rows"],
            "schedule_mismatches": verification["schedule_mismatches"],
            "semantic_mismatches": verification["semantic_mismatches"],
            "source_or_artifact_mismatches": verification["source_or_artifact_mismatches"],
        },
        "execution": {
            "pod_id": controller["pod_id"],
            "quoted_rate_usd_per_hour": controller["quoted_rate_usd_per_hour"],
            "elapsed_since_create_s": controller["elapsed_since_create_s"],
            "estimated_compute_cost_usd": controller["estimated_compute_cost_usd"],
            "owned_pod_absent": controller["cleanup"]["owned_pod_absent"],
            "final_inventories": controller["cleanup"]["inventories"],
        },
        "statistics": {
            "primary_metric": "paired accounted_total_ns speedup",
            "bootstrap_unit": "frozen case_id",
            "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
            "confidence_scope": "case heterogeneity conditional on one execution host",
            "selector_fitted": False,
        },
        "lanes": {
            "A": {
                "contract": "complete explicit relation",
                "arm_order": arms_a,
                "arms": _arm_summary(rows, "A"),
                "speedup_over_dense_cm": speed_a_dense,
                "speedup_over_direct_bitset": speed_a_bitset,
                "best_fixed_cm_arm": best_cm,
                "best_fixed_cm_over_dense": speed_a_dense[best_cm],
                "direct_bitset_over_best_fixed_cm": speed_a_bitset[best_cm],
                "decision": "retain packed/recursive CM benefit but do not claim a complete-vector win over current direct BitSet",
            },
            "B": {
                "contract": "64 repeated exact restrictions with q1/q4/q16/q64 prefix digests",
                "arm_order": arms_b,
                "arms": _arm_summary(rows, "B"),
                "speedup_over_r2": speed_b_r2,
                "speedup_over_projection": speed_b_projection,
                "timed_query_counts": query_counts,
                "correctness_checkpoint_counts": checkpoint_counts,
                "query_count_break_even_interpretation_permitted": query_counts == checkpoint_counts,
                "native_minimum_case_floor": native_gate,
                "native_minimum_case_speedup_over_r2": native_vs_r2["minimum_case_speedup"],
                "native_minimum_case_gate_passed": native_vs_r2["minimum_case_speedup"] >= native_gate,
                "decision": "native remains guarded because the frozen single-case floor fails; q1/q4/q16 timing follow-up required",
            },
            "C": {
                "contract": "ordered explicit related-root outputs",
                "arm_order": arms_c,
                "arms": _arm_summary(rows, "C"),
                "python_union_over_separate": paired_speedup(
                    rows, lane="C", baseline="python_sharing_separate",
                    candidate="python_sharing_union", observed_case_ids=observed_c,
                ),
                "native_union_over_separate": paired_speedup(
                    rows, lane="C", baseline="native_separate", candidate="native_union",
                    observed_case_ids=observed_c,
                ),
                "native_union_over_python_union": paired_speedup(
                    rows, lane="C", baseline="python_sharing_union", candidate="native_union",
                    observed_case_ids=observed_c,
                ),
                "decision": "retain shared union arenas; do not claim unconditional native superiority",
            },
            "D": {
                "contract": "task-matched smaller queries and structural persistence",
                "tasks": tasks,
                "decision": "use natural task-specific controls; CM is not the fixed winner",
            },
        },
        "measurement_limits": {
            "q1_q4_q16_separately_timed": query_counts == checkpoint_counts,
            "lane_b_observed_timed_query_counts": query_counts,
            "lane_b_correctness_checkpoint_counts": checkpoint_counts,
            "peak_rss_source": "resource.getrusage(resource.RUSAGE_SELF).ru_maxrss",
            "peak_rss_nondecreasing_in_file_order": rss_nondecreasing,
            "peak_rss_unique_values": len(set(peak_rss)),
            "per_arm_memory_interpretation_permitted": False,
            "cross_machine_claim_permitted": False,
            "website_update_permitted": False,
            "selector_or_neural_claim_permitted": False,
        },
    }
    return analysis


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--controller-state", type=Path, default=DEFAULT_CONTROLLER)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-markdown", required=True, type=Path)
    args = parser.parse_args()
    analysis = analyze(
        args.run_dir.resolve(), args.freeze.resolve(), args.controller_state.resolve()
    )
    for output in (args.output_json.resolve(), args.output_markdown.resolve()):
        _require(output.is_relative_to(ROOT) and not output.exists(), "outputs must be new in-project paths")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(analysis, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    args.output_markdown.write_text(_markdown(analysis), encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": analysis["status"],
        "output_json": str(args.output_json),
        "output_markdown": str(args.output_markdown),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
