"""Register independently verified C29 variance-localization evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c29-variance-localization-windows-20260901-002"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C29_VARIANCE_LOCALIZATION_2026_09_01.md"
MACHINE = "learning_milestone_c29_variance_localization_results.json"
C28_MACHINE = "learning_milestone_c28_cross_machine_profitability_adjudication_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False,
    ).encode("utf-8") + b"\n")


def upsert(container: dict, scope: str) -> None:
    value = {"report": REPORT, "machine_summary": MACHINE, "scope": scope}
    matches = [row for row in container["results"] if row.get("report") == REPORT]
    if len(matches) > 1:
        raise RuntimeError("duplicate C29 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    frozen = load(RUN / "frozen_localization.json")
    verification = load(RUN / "independent_verification.json")
    summary = result["summary"]
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("dataset_cases") != 48
        or result.get("frozen_executions_localized") != 5
        or result.get("frozen_physical_machines") != 2
        or result.get("frozen_paired_q8_cells") != 100
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("policy_refit") is not False
        or result.get("training") is not False
        or result.get("diagnostic_only") is not True
        or result.get("shadow_promotion") is not False
        or result.get("production_promotion") is not False
        or summary.get("measurement_batches") != 128
        or summary.get("paired_batches") != 64
        or summary.get("timed_queries") != 1024
        or summary.get("exactness_gate") is not True
        or summary.get("arm_order_balanced") is not True
        or summary.get("width_position_balanced") is not True
        or summary["by_width"]["3"]["ratio_of_median_total_speedup"] >= 0.90
        or summary["by_width"]["4"]["ratio_of_median_query_speedup"] <= 1.0
        or summary["by_width"]["4"]["ratio_of_median_total_speedup"] >= 1.0
        or frozen.get("paired_cells") != 100
        or frozen["by_width"]["3"]["total_regression_cells"] != 16
        or verification.get("status") != "verified"
        or verification.get("frozen_c27_measurement_rows_checked") != 3600
        or verification.get("frozen_q8_paired_cells_recomputed") != 100
        or verification.get("measurement_batches_checked") != 128
        or verification.get("paired_batches_checked") != 64
        or verification.get("timed_query_records_checked") != 1024
        or verification.get("verified_context_records_replayed") != 512
        or verification.get("semantic_or_artifact_mismatches") != 0
        or verification.get("summary_recomputed") is not True
        or verification.get("schedule_recomputed") is not True
        or verification.get("results_sha256") != sha256(RUN / "results.json")
        or verification.get("manifest_sha256") != sha256(RUN / "manifest.json")
    ):
        raise RuntimeError("refusing C29 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c29-variance-localization-summary/v1",
        "date": "2026-09-01",
        "status": "verified_variance_localized_promotion_refused",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "source_milestones": ["C27", "C28"],
        "query_count": 8,
        "frozen_execution_count": 5,
        "frozen_physical_machine_count": 2,
        "frozen_measurement_rows_checked": 3600,
        "frozen_paired_q8_cells": 100,
        "measurement_batches": 128,
        "paired_batches": 64,
        "timed_queries": 1024,
        "verified_context_records_replayed": 512,
        "aggregate_ratio_of_median_total_speedup": summary[
            "aggregate_ratio_of_median_total_speedup"],
        "aggregate_ratio_of_median_query_speedup": summary[
            "aggregate_ratio_of_median_query_speedup"],
        "candidate_setup_detail_median_ns": summary["candidate_setup_detail_median_ns"],
        "candidate_policy_load_median_share_of_setup": summary[
            "candidate_policy_load_median_share_of_setup"],
        "frozen_by_width": frozen["by_width"],
        "counterbalanced_by_width": summary["by_width"],
        "semantic_or_artifact_mismatches": 0,
        "policy_refit": False,
        "training": False,
        "diagnostic_only": True,
        "shadow_promotion": False,
        "production_promotion": False,
        "verification": {
            "path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace(
                "\\", "/"),
            **verification,
        },
        "interpretation": (
            "Frozen q8 regressions concentrate at n=3 and in isolated query-path outliers. "
            "The new counterbalanced run measures n=3 at 0.846x total/0.978x query-only "
            "and n=4 at 0.969x total/1.042x query-only. Policy loading and validation "
            "consume 92.38% of median candidate setup, but query variance also remains. "
            "This diagnostic does not supersede C28 and promotion remains refused."
        ),
    }
    write(DOCS / MACHINE, machine)

    scope = (
        "C29 localizes the frozen C27 q8 variance and adds 64 adjacent, fully "
        "counterbalanced exact pairs. Policy load/validation accounts for 92.38% of "
        "candidate setup. n=3 remains 0.846x total and n=4 is 0.969x despite a 1.042x "
        "query-only gain; query-path outliers also remain. This is diagnostic evidence, "
        "and shadow/production promotion stays refused."
    )
    next_experiment = (
        "C30 should hash-bind C27/C22 policies in an immutable prepared context, charge "
        "preparation once at the resident lifecycle boundary, retain fail-closed controls, "
        "and repeat the unchanged C29 counterbalanced exact diagnostic before any "
        "two-machine confirmation or learned selector."
    )
    register = load(REGISTER)
    track_ids = [row["id"] for row in register["tracks"]]
    application_names = [row["name"] for row in register["applications"]]
    if len(track_ids) != 18 or len(set(track_ids)) != 18 or len(application_names) != 8:
        raise RuntimeError("track/application inventory changed before C29 registration")
    registrations = 0
    for collection in (register["tracks"], register["applications"]):
        for row in collection:
            has_c28 = any(item.get("machine_summary") == C28_MACHINE
                          for item in row.get("results", []))
            if not has_c28:
                continue
            upsert(row, scope)
            registrations += 1
            if "status_reason" in row:
                row["status_reason"] = scope
            if "next_experiment" in row:
                row["next_experiment"] = next_experiment
    if registrations != 9:
        raise RuntimeError(f"expected nine C29 registrations, observed {registrations}")
    register["milestones"]["F"] = (
        "C29 localizes q8 variance with frozen C27 evidence plus a counterbalanced exact "
        "diagnostic; repeated policy validation dominates setup, n=3 remains negative, "
        "query-path outliers remain, and promotion is refused"
    )
    register["updated"] = "2026-09-01"
    if (
        [row["id"] for row in register["tracks"]] != track_ids
        or [row["name"] for row in register["applications"]] != application_names
    ):
        raise RuntimeError("C29 registration changed track/application identity or order")
    write(REGISTER, register)
    print(json.dumps({
        "status": "registered",
        "tracks": len(track_ids),
        "applications": len(application_names),
        "c29_registrations": registrations,
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
