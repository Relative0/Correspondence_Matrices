"""Register independently verified C30 prepared-policy lifecycle evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c30-prepared-policy-windows-20260901-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C30_PREPARED_POLICY_CONTEXT_2026_09_01.md"
MACHINE = "learning_milestone_c30_prepared_policy_context_results.json"
C29_MACHINE = "learning_milestone_c29_variance_localization_results.json"


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
        raise RuntimeError("duplicate C30 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    prepared = load(RUN / "prepared_context.json")
    controls = load(RUN / "functional_controls.json")
    summary = result["summary"]
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("dataset_cases") != 48
        or result.get("functional_controls_passed") is not True
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("policy_refit") is not False
        or result.get("training") is not False
        or result.get("development_evidence") is not True
        or result.get("shadow_promotion") is not False
        or result.get("production_promotion") is not False
        or controls.get("all_passed") is not True
        or controls.get("exact_controls_passed") is not True
        or controls.get("refusal_controls_passed") is not True
        or summary.get("measurement_batches") != 128
        or summary.get("paired_batches") != 64
        or summary.get("timed_queries") != 1024
        or summary.get("exactness_gate") is not True
        or summary.get("lifecycle_preparation_charge_conserved") is not True
        or summary.get("prepared_no_regret_gate") is not True
        or summary.get("arm_order_balanced") is not True
        or summary.get("width_position_balanced") is not True
        or summary.get("aggregate_ratio_of_median_charged_total_speedup") < 1.0
        or summary.get("minimum_width_ratio_of_median_charged_total_speedup") < 0.90
        or prepared.get("schema") != "crse-c30-prepared-support-policy-context/v1"
        or prepared.get("preparation_ns") != summary.get("lifecycle_preparation_ns")
        or verification.get("status") != "verified"
        or verification.get("measurement_batches_checked") != 128
        or verification.get("paired_batches_checked") != 64
        or verification.get("timed_query_records_checked") != 1024
        or verification.get("verified_context_records_replayed") != 512
        or verification.get("functional_controls_replayed") != 6
        or verification.get("preparation_charge_conserved") is not True
        or verification.get("semantic_or_artifact_mismatches") != 0
        or verification.get("summary_recomputed") is not True
        or verification.get("schedule_recomputed") is not True
        or verification.get("results_sha256") != sha256(RUN / "results.json")
        or verification.get("manifest_sha256") != sha256(RUN / "manifest.json")
    ):
        raise RuntimeError("refusing C30 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c30-prepared-policy-context-summary/v1",
        "date": "2026-09-01",
        "status": "verified_local_no_regret_gate_passed_promotion_refused",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "source_milestones": ["C29", "C28", "C27"],
        "query_count": 8,
        "dataset_cases": 48,
        "measurement_batches": 128,
        "paired_batches": 64,
        "timed_queries": 1024,
        "verified_context_records_replayed": 512,
        "functional_controls_replayed": 6,
        "prepared_context": prepared,
        "candidate_setup_detail_median_ns": summary["candidate_setup_detail_median_ns"],
        "aggregate_ratio_of_median_charged_total_speedup": summary[
            "aggregate_ratio_of_median_charged_total_speedup"],
        "aggregate_ratio_of_median_query_speedup": summary[
            "aggregate_ratio_of_median_query_speedup"],
        "minimum_width_ratio_of_median_charged_total_speedup": summary[
            "minimum_width_ratio_of_median_charged_total_speedup"],
        "prepared_no_regret_gate": summary["prepared_no_regret_gate"],
        "by_width": summary["by_width"],
        "c29_comparison": result["c29_comparison"],
        "semantic_or_artifact_mismatches": 0,
        "policy_refit": False,
        "training": False,
        "development_evidence": True,
        "shadow_promotion": False,
        "production_promotion": False,
        "verification": {
            "path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace(
                "\\", "/"),
            **verification,
        },
        "interpretation": (
            "C30 validates and hash-binds C27/C22 once per resident lifecycle, fully "
            "allocates its 0.752 ms preparation charge, and reduces median per-session "
            "setup to 0.043 ms. The unchanged q8 schedule measures 1.036x aggregate and "
            "1.000x minimum-width charged speedup. The local no-regret diagnostic passes, "
            "but n=3 is neutral and this is not cross-machine promotion evidence."
        ),
    }
    write(DOCS / MACHINE, machine)

    scope = (
        "C30 replaces per-batch C27/C22 file validation with one immutable hash-bound "
        "prepared context and conserves the lifecycle charge. Across 64 exact q8 pairs, "
        "median setup falls to 0.043 ms and the fully charged local surface reaches 1.036x "
        "aggregate with a 1.000x minimum width. Safety and local no-regret gates pass; "
        "shadow and production promotion remain refused pending unchanged replication."
    )
    next_experiment = (
        "C31 should freeze the C30 package and prospective paired-block adjudication, "
        "then run the unchanged schedule on a second physical machine with no refit. "
        "Same-host containers count only as portability evidence."
    )
    register = load(REGISTER)
    track_ids = [row["id"] for row in register["tracks"]]
    application_names = [row["name"] for row in register["applications"]]
    if len(track_ids) != 18 or len(set(track_ids)) != 18 or len(application_names) != 8:
        raise RuntimeError("track/application inventory changed before C30 registration")
    registrations = 0
    for collection in (register["tracks"], register["applications"]):
        for row in collection:
            has_c29 = any(item.get("machine_summary") == C29_MACHINE
                          for item in row.get("results", []))
            if not has_c29:
                continue
            upsert(row, scope)
            registrations += 1
            if "status_reason" in row:
                row["status_reason"] = scope
            if "next_experiment" in row:
                row["next_experiment"] = next_experiment
    if registrations != 9:
        raise RuntimeError(f"expected nine C30 registrations, observed {registrations}")
    register["milestones"]["F"] = (
        "C30 hash-binds validated C27/C22 policies once per resident lifecycle; the fully "
        "charged unchanged q8 diagnostic passes locally at 1.036x aggregate and 1.000x "
        "minimum width, while cross-machine promotion remains pending"
    )
    register["updated"] = "2026-09-01"
    if (
        [row["id"] for row in register["tracks"]] != track_ids
        or [row["name"] for row in register["applications"]] != application_names
    ):
        raise RuntimeError("C30 registration changed track/application identity or order")
    write(REGISTER, register)
    print(json.dumps({
        "status": "registered",
        "tracks": len(track_ids),
        "applications": len(application_names),
        "c30_registrations": registrations,
        "prepared_no_regret_gate": summary["prepared_no_regret_gate"],
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
