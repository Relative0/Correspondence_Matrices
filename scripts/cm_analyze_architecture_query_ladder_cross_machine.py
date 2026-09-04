"""Compare the two exact query-ladder hosts without fitting a selector."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_query_ladder_cross_machine_execution_20260904"
CURRENT_ATTEMPT = HERE / "runpod-architecture-query-ladder-cross-machine-execute-001"
CURRENT_EVIDENCE = CURRENT_ATTEMPT / "evidence/run-output"
CURRENT_STUDY = CURRENT_EVIDENCE / "architecture-query-ladder-linux-clang-20260904-003"
PRIOR_PACKAGE = (
    ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
)
PRIOR_ATTEMPT = PRIOR_PACKAGE / "runpod-architecture-query-ladder-execute-002"
PRIOR_EVIDENCE = PRIOR_ATTEMPT / "evidence/run-output"
PRIOR_STUDY = PRIOR_EVIDENCE / "architecture-query-ladder-linux-gcc-20260904-002"
FREEZE = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904"
    / "FREEZE.json"
)
PARENT_FREEZE = ROOT / "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json"
POST_INVENTORY = HERE / "POST_RUN_INVENTORY.json"
LOCAL_VERIFICATION = HERE / "LOCAL_INDEPENDENT_VERIFICATION.json"
PRIOR_ANALYSIS = PRIOR_PACKAGE / "ANALYSIS.json"
BASE_ANALYZER = ROOT / "scripts/cm_analyze_architecture_query_ladder.py"
OUTPUT = HERE / "CROSS_MACHINE_ANALYSIS.json"
MARKDOWN = HERE / "VERIFIED_CROSS_MACHINE_INTERPRETATION.md"
QUERY_COUNTS = (1, 4, 16, 64)
BASELINE = "r2_topological_liveness"
NATIVE = "native_fused_slots"
CSE = "cse_flat_bigint"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, value: Any) -> None:
    if path.exists() or not path.resolve().is_relative_to(ROOT):
        raise ValueError("cross-machine analysis output must be a new in-project file")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        if isinstance(value, str):
            stream.write(value)
        else:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")


def _host_analysis(
    analyzer, *, label: str, study: Path, evidence: Path, attempt: Path,
    arms: list[str], observed: set[str],
) -> dict[str, Any]:
    results = _load(study / "results.json")
    verification = _load(study / "independent_verification.json")
    binding = _load(study / "runtime_binding.json")
    runtime = _load(evidence / "RUNTIME.json")
    run = _load(attempt / "RUN.json")
    raw_path = study / "raw_measurements.jsonl"
    if (
        results.get("status") != "complete"
        or verification.get("status") != "verified_complete"
        or verification.get("rows_checked") != 27_648
        or verification.get("results_sha256") != _sha256(study / "results.json")
        or verification.get("raw_measurements_sha256") != _sha256(raw_path)
        or any(verification.get(key) != 0 for key in (
            "semantic_mismatches", "schedule_mismatches", "source_or_artifact_mismatches",
            "memory_measurement_mismatches",
        ))
        or run.get("status") != "complete"
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
    ):
        raise ValueError(f"{label} input is not a verified complete run")
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
    if len(rows) != 27_648 or not all(row.get("exact_check_passed") is True for row in rows):
        raise ValueError(f"{label} raw rows are incomplete")

    query_results = {}
    for query_count in QUERY_COUNTS:
        comparisons = {
            arm: analyzer.paired_speedup(
                rows,
                query_count=query_count,
                baseline=BASELINE,
                candidate=arm,
                observed_case_ids=observed,
            )
            for arm in arms if arm != BASELINE
        }
        query_results[str(query_count)] = {
            "best_fixed": analyzer.fixed_arm(
                rows, query_count=query_count, arms=arms,
            ),
            "arms": {
                arm: analyzer.arm_summary(rows, query_count=query_count, arm=arm)
                for arm in arms
            },
            "speedup_over_r2": comparisons,
        }
    cleanup_ns = sum(row["timings_ns"]["cleanup_ns"] for row in rows)
    task_ns = sum(row["timings_ns"]["accounted_total_ns"] for row in rows)
    incremental_nonzero = sum(
        row["memory_measurement"]["incremental_peak_rss_bytes"] > 0 for row in rows
    )
    return {
        "label": label,
        "pod_id": run["pod_id"],
        "cpu_flavor": run["selected_cpu"],
        "cpu_model": runtime["cpu_model"],
        "platform": runtime["platform"],
        "compiler_executable": binding["compiler_executable"],
        "compiler_executable_sha256": binding["compiler_executable_sha256"],
        "compiler_version": binding["compiler_version"],
        "native_library_sha256": binding["native_library_sha256"],
        "results_sha256": _sha256(study / "results.json"),
        "raw_measurements_sha256": _sha256(raw_path),
        "verification_sha256": _sha256(study / "independent_verification.json"),
        "runtime_binding_sha256": _sha256(study / "runtime_binding.json"),
        "run_sha256": _sha256(attempt / "RUN.json"),
        "rows": len(rows),
        "query_rows": verification["query_rows"],
        "cleanup_share_of_accounted_time": cleanup_ns / task_ns,
        "incremental_peak_nonzero_rows": incremental_nonzero,
        "quoted_rate_usd_per_hour": run["quoted_rate_usd_per_hour"],
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "query_counts": query_results,
    }


def _metric(host: Mapping[str, Any], query_count: int, arm: str) -> Mapping[str, Any]:
    return host["query_counts"][str(query_count)]["speedup_over_r2"][arm]


def _render(analysis: Mapping[str, Any]) -> str:
    prior = analysis["hosts"]["gcc_epyc_9655"]
    current = analysis["hosts"]["clang_epyc_9575f"]
    lines = [
        "# Verified cross-machine query-ladder interpretation",
        "",
        "Date: 2026-09-04",
        "Status: exact separate-host/compiler replication complete",
        "",
        "Both runs completed the same 27,648-cell frozen q1/q4/q16/q64 schedule. The",
        "independent verifier found zero semantic, schedule, source/artifact, or memory-field",
        "mismatches on both hosts, and the Clang result was reverified locally byte-for-byte.",
        "",
        "The comparison uses within-host speedups over Python R2. Absolute timings are not",
        "compared across unlike CPUs, and the host and compiler changed together, so their",
        "individual causal effects cannot be separated.",
        "",
        "| q | GCC/EPYC 9655 best fixed | Clang/EPYC 9575F best fixed | CSE-flat/R2, GCC → Clang | native/R2, GCC → Clang | native minimum, GCC → Clang |",
        "|---:|---|---|---:|---:|---:|",
    ]
    for query_count in QUERY_COUNTS:
        prior_fixed = prior["query_counts"][str(query_count)]["best_fixed"]["best_fixed_arm"]
        current_fixed = current["query_counts"][str(query_count)]["best_fixed"]["best_fixed_arm"]
        prior_cse = _metric(prior, query_count, CSE)
        current_cse = _metric(current, query_count, CSE)
        prior_native = _metric(prior, query_count, NATIVE)
        current_native = _metric(current, query_count, NATIVE)
        lines.append(
            f"| {query_count} | `{prior_fixed}` | `{current_fixed}` | "
            f"{prior_cse['case_cluster_geomean_speedup']:.3f}x → "
            f"{current_cse['case_cluster_geomean_speedup']:.3f}x | "
            f"{prior_native['case_cluster_geomean_speedup']:.3f}x → "
            f"{current_native['case_cluster_geomean_speedup']:.3f}x | "
            f"{prior_native['minimum_case_speedup']:.3f}x → "
            f"{current_native['minimum_case_speedup']:.3f}x |"
        )
    transfer = analysis["transfer"]
    q64_native = transfer["query_counts"]["64"][NATIVE]
    q64_cse = transfer["query_counts"]["64"][CSE]
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The best fixed arm agreed on three of four query counts. Python R2 remained the",
        "best fixed arm at q1/q4 on both hosts, and CSE-flat bigint remained best at q64.",
        "At q16, CSE-flat narrowly led on the GCC host but narrowly trailed R2 on the",
        "Clang host, so q16 is a threshold-straddling sample rather than a portable",
        "crossover. At q64, CSE-flat stayed faster than R2 on both hosts",
        f"({q64_cse['prior_speedup']:.3f}x and {q64_cse['current_speedup']:.3f}x), won",
        f"{q64_cse['prior_case_wins']} and {q64_cse['current_case_wins']} of 54 cases, and",
        f"kept its minimum above 1.0 ({q64_cse['prior_minimum_case']:.3f}x and",
        f"{q64_cse['current_minimum_case']:.3f}x).",
        "",
        f"Native q64 changed from {q64_native['prior_speedup']:.3f}x to",
        f"{q64_native['current_speedup']:.3f}x over R2, while its minimum changed from",
        f"{q64_native['prior_minimum_case']:.3f}x to {q64_native['current_minimum_case']:.3f}x.",
        "The observed C36 cohort stayed favorable but the fresh cohort stayed unfavorable:",
        f"{q64_native['prior_observed_regression']['case_cluster_geomean_speedup']:.3f}x → "
        f"{q64_native['current_observed_regression']['case_cluster_geomean_speedup']:.3f}x",
        f"versus {q64_native['prior_fresh']['case_cluster_geomean_speedup']:.3f}x →",
        f"{q64_native['current_fresh']['case_cluster_geomean_speedup']:.3f}x.",
        "The complete JSON retains every arm, case-cluster interval, cohort split, and",
        "unfavorable minimum. This supports a portable task map, not a universal native default.",
        "",
        "The isolated-child incremental RSS field remained zero for every row on both hosts.",
        "It therefore remains descriptive evidence and cannot calibrate a memory router.",
        "",
        "## Boundary",
        "",
        "The separate-host/compiler evidence gate is complete. This analysis does not fit a",
        "selector, train a neural model, change production routing, or itself authorize a",
        "website edit or publication. A public update must retain the historical Windows/MSVC",
        "1.472x result and label these Linux task-specific results by host, compiler, and contract.",
        "",
        "## Execution",
        "",
        f"The Clang replication used Pod `{current['pod_id']}` at",
        f"${current['quoted_rate_usd_per_hour']:.2f}/hour and cost an estimated",
        f"${current['estimated_compute_cost_usd']:.6f}. The cumulative estimate for the",
        f"incomplete first ladder attempt, GCC retry, and Clang replication is",
        f"${analysis['execution']['three_attempt_estimated_cost_usd']:.6f}.",
        "Controller cleanup and the later independent inventory both found empty v1/v2 inventories.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    if OUTPUT.exists() or MARKDOWN.exists():
        raise SystemExit("refusing to overwrite cross-machine analysis")
    spec = importlib.util.spec_from_file_location("query_ladder_base_analysis", BASE_ANALYZER)
    analyzer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyzer)
    freeze = _load(FREEZE)
    parent_freeze = _load(PARENT_FREEZE)
    arms = list(freeze["schedule"]["arms"])
    observed = set(
        parent_freeze["observed_regression_bindings"]["repeated_restriction_regression"][
            "case_ids"
        ]
    )
    prior = _host_analysis(
        analyzer,
        label="Linux/GCC 12 on AMD EPYC 9655",
        study=PRIOR_STUDY,
        evidence=PRIOR_EVIDENCE,
        attempt=PRIOR_ATTEMPT,
        arms=arms,
        observed=observed,
    )
    current = _host_analysis(
        analyzer,
        label="Linux/Clang 14 on AMD EPYC 9575F",
        study=CURRENT_STUDY,
        evidence=CURRENT_EVIDENCE,
        attempt=CURRENT_ATTEMPT,
        arms=arms,
        observed=observed,
    )
    local_verification = _load(LOCAL_VERIFICATION)
    post_inventory = _load(POST_INVENTORY)
    if (
        local_verification.get("status") != "verified_complete"
        or local_verification.get("rows_reverified") != 27_648
        or local_verification.get("remote_verification_reproduced_byte_for_byte") is not True
        or post_inventory.get("owned_pod_absent") is not True
        or post_inventory.get("inventories") != {"v1": [], "v2": []}
        or prior["cpu_model"] == current["cpu_model"]
        or prior["compiler_executable_sha256"] == current["compiler_executable_sha256"]
    ):
        raise ValueError("cross-machine analysis admission failed")

    transfer_by_q = {}
    best_fixed_agreement = 0
    for query_count in QUERY_COUNTS:
        prior_fixed = prior["query_counts"][str(query_count)]["best_fixed"]["best_fixed_arm"]
        current_fixed = current["query_counts"][str(query_count)]["best_fixed"]["best_fixed_arm"]
        best_fixed_agreement += prior_fixed == current_fixed
        transfer_by_q[str(query_count)] = {}
        for arm in arms:
            if arm == BASELINE:
                continue
            old = _metric(prior, query_count, arm)
            new = _metric(current, query_count, arm)
            transfer_by_q[str(query_count)][arm] = {
                "prior_speedup": old["case_cluster_geomean_speedup"],
                "current_speedup": new["case_cluster_geomean_speedup"],
                "current_to_prior_speedup_ratio": (
                    new["case_cluster_geomean_speedup"]
                    / old["case_cluster_geomean_speedup"]
                ),
                "faster_than_r2_on_both_hosts": (
                    old["case_cluster_geomean_speedup"] > 1.0
                    and new["case_cluster_geomean_speedup"] > 1.0
                ),
                "prior_ci95": [
                    old["case_cluster_bootstrap_ci95_low"],
                    old["case_cluster_bootstrap_ci95_high"],
                ],
                "current_ci95": [
                    new["case_cluster_bootstrap_ci95_low"],
                    new["case_cluster_bootstrap_ci95_high"],
                ],
                "prior_minimum_case": old["minimum_case_speedup"],
                "current_minimum_case": new["minimum_case_speedup"],
                "minimum_0_95_floor_on_both_hosts": (
                    old["minimum_case_speedup"] >= 0.95
                    and new["minimum_case_speedup"] >= 0.95
                ),
                "prior_case_wins": old["candidate_case_wins"],
                "current_case_wins": new["candidate_case_wins"],
                "prior_observed_regression": old["observed_regression"],
                "current_observed_regression": new["observed_regression"],
                "prior_fresh": old["fresh"],
                "current_fresh": new["fresh"],
            }

    prior_total = _load(PRIOR_ANALYSIS)["execution"]["combined_estimated_compute_cost_usd"]
    analysis = {
        "schema": "cm-architecture-query-ladder-cross-machine-analysis/v1",
        "status": "verified_cross_machine_interpretation_complete",
        "generated_date": "2026-09-04",
        "task_contract": {
            "freeze_sha256": _sha256(FREEZE),
            "planned_cells_per_host": 27_648,
            "query_counts": list(QUERY_COUNTS),
            "arms": arms,
            "same_frozen_schedule_artifact_and_oracles": True,
            "absolute_cross_host_timing_comparison_permitted": False,
            "within_host_speedup_transfer_comparison_permitted": True,
        },
        "inputs": {
            "local_independent_verification_sha256": _sha256(LOCAL_VERIFICATION),
            "post_run_inventory_sha256": _sha256(POST_INVENTORY),
            "prior_analysis_sha256": _sha256(PRIOR_ANALYSIS),
        },
        "hosts": {
            "gcc_epyc_9655": prior,
            "clang_epyc_9575f": current,
        },
        "transfer": {
            "best_fixed_agreement_count": best_fixed_agreement,
            "best_fixed_query_counts": len(QUERY_COUNTS),
            "query_counts": transfer_by_q,
        },
        "memory": {
            "prior_incremental_peak_nonzero_rows": prior["incremental_peak_nonzero_rows"],
            "current_incremental_peak_nonzero_rows": current["incremental_peak_nonzero_rows"],
            "memory_router_calibration_permitted": False,
        },
        "execution": {
            "current_estimated_compute_cost_usd": current["estimated_compute_cost_usd"],
            "prior_two_attempt_estimated_cost_usd": prior_total,
            "three_attempt_estimated_cost_usd": prior_total + current["estimated_compute_cost_usd"],
            "current_owned_pod_absent": True,
            "independent_post_run_inventories": {"v1": [], "v2": []},
        },
        "claim_boundary": {
            "separate_host_and_compiler_replication_complete": True,
            "task_specific_portability_interpretation_permitted": True,
            "host_and_compiler_effects_separately_attributable": False,
            "universal_break_even_claim_permitted": False,
            "universal_native_default_claim_permitted": False,
            "selector_or_neural_claim_permitted": False,
            "production_routing_change_permitted": False,
            "website_update_permitted_by_this_run": False,
            "publication_permitted_by_this_run": False,
        },
    }
    _write_new(OUTPUT, analysis)
    _write_new(MARKDOWN, _render(analysis))
    print(json.dumps({
        "status": analysis["status"],
        "analysis_sha256": _sha256(OUTPUT),
        "markdown_sha256": _sha256(MARKDOWN),
        "best_fixed_agreement_count": best_fixed_agreement,
        "q64_cse_speedup": {
            "gcc": transfer_by_q["64"][CSE]["prior_speedup"],
            "clang": transfer_by_q["64"][CSE]["current_speedup"],
        },
        "q64_native_speedup": {
            "gcc": transfer_by_q["64"][NATIVE]["prior_speedup"],
            "clang": transfer_by_q["64"][NATIVE]["current_speedup"],
        },
        "three_attempt_estimated_cost_usd": analysis["execution"][
            "three_attempt_estimated_cost_usd"
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
