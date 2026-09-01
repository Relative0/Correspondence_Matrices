"""Register independently verified C32 shadow-boundary evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c32-prepared-shadow-windows-20260901-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C32_PREPARED_POLICY_SHADOW_BOUNDARY_2026_09_01.md"
MACHINE = "learning_milestone_c32_prepared_policy_shadow_results.json"
C31_MACHINE = "learning_milestone_c31_prepared_policy_replication_results.json"


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
        raise RuntimeError("duplicate C32 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    controls = load(RUN / "functional_controls.json")
    spec = load(RUN / "run_spec.json")
    summary = result.get("summary", {})
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("dataset_cases") != 48
        or result.get("functional_controls_passed") is not True
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("policy_refit") is not False
        or result.get("training") is not False
        or result.get("production_write") is not False
        or result.get("shadow_promotion") is not False
        or result.get("production_promotion") is not False
        or controls.get("all_passed") is not True
        or controls.get("served_candidate_results") != 0
        or controls.get("production_writes") != 0
        or summary.get("measurement_batches") != 128
        or summary.get("paired_batches") != 64
        or summary.get("served_exact_queries") != 1024
        or summary.get("shadow_candidate_observations") != 512
        or summary.get("semantic_or_artifact_mismatches") != 0
        or summary.get("shadow_review_gate") is not True
        or summary.get("timing_is_observational_not_a_promotion_gate") is not True
        or verification.get("status") != "verified"
        or verification.get("served_exact_queries_replayed") != 1024
        or verification.get("shadow_candidate_observations_replayed") != 512
        or verification.get("candidate_results_served") != 0
        or verification.get("production_writes") != 0
        or verification.get("semantic_or_artifact_mismatches") != 0
        or verification.get("results_sha256") != sha256(RUN / "results.json")
        or verification.get("manifest_sha256") != sha256(RUN / "manifest.json")
        or spec.get("candidate_observed_only") is not True
    ):
        raise RuntimeError("refusing C32 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c32-prepared-policy-shadow-summary/v1",
        "date": "2026-09-01",
        "status": "verified_local_shadow_boundary_no_promotion",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "source_milestone": "C31",
        "dataset_cases": 48,
        "measurement_batches": 128,
        "paired_batches": 64,
        "served_exact_queries": 1024,
        "shadow_candidate_observations": 512,
        "semantic_or_artifact_mismatches": 0,
        "candidate_results_served": 0,
        "production_writes": 0,
        "functional_controls_replayed": 6,
        "shadow_review_gate": True,
        "aggregate_shadow_enabled_synchronous_overhead_ratio": summary[
            "aggregate_shadow_enabled_synchronous_overhead_ratio"],
        "aggregate_served_baseline_latency_ratio_enabled_over_disabled": summary[
            "aggregate_served_baseline_latency_ratio_enabled_over_disabled"],
        "by_width": summary["by_width"],
        "controls": controls,
        "policy_refit": False,
        "training": False,
        "production_write": False,
        "shadow_promotion": False,
        "production_promotion": False,
        "verification": {
            "path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace(
                "\\", "/"),
            **verification,
        },
        "interpretation": (
            "C32 serves only the exact screened baseline while observing the frozen C30 "
            "candidate. All 1,024 baseline requests and 512 candidate observations were "
            "exact, and injected exception, refusal, divergence, binding, and source-change "
            "controls were contained. Synchronous shadow work roughly doubles total time, "
            "so a later review should isolate or sample candidate work off the response path."
        ),
    }
    write(DOCS / MACHINE, machine)

    scope = (
        "C32 adds an opt-in boundary that always serves the exact screened baseline and "
        "observes the frozen C30 candidate only. Across 1,024 served requests and 512 "
        "candidate observations, independent replay found zero mismatches and zero "
        "candidate results served. Exception, refusal, exact-but-nonbest divergence, "
        "wrong-binding, and changed-source controls were contained. Synchronous shadow "
        "work costs 2.045x total while baseline latency remains 1.003x; no promotion occurred."
    )
    next_experiment = (
        "C33 should move observational candidate work behind a bounded asynchronous or "
        "sampled queue: return the exact baseline before candidate execution, copy/hash-bind "
        "the request, drop safely under backpressure, and independently replay queued "
        "comparisons while measuring enqueue overhead and coverage."
    )
    register = load(REGISTER)
    track_ids = [row["id"] for row in register["tracks"]]
    application_names = [row["name"] for row in register["applications"]]
    if len(track_ids) != 18 or len(set(track_ids)) != 18 or len(application_names) != 8:
        raise RuntimeError("track/application inventory changed before C32 registration")
    registrations = 0
    for collection in (register["tracks"], register["applications"]):
        for row in collection:
            if not any(item.get("machine_summary") == C31_MACHINE
                       for item in row.get("results", [])):
                continue
            upsert(row, scope)
            registrations += 1
            if "status_reason" in row:
                row["status_reason"] = scope
            if "next_experiment" in row:
                row["next_experiment"] = next_experiment
    if registrations != 9:
        raise RuntimeError(f"expected nine C32 registrations, observed {registrations}")
    register["milestones"]["F"] = (
        "C32 implements a baseline-serving, candidate-observing prepared-policy boundary; "
        "all local exactness and containment controls pass with zero candidate delivery or "
        "production writes, while synchronous overhead motivates bounded asynchronous shadowing"
    )
    register["updated"] = "2026-09-01"
    if (
        [row["id"] for row in register["tracks"]] != track_ids
        or [row["name"] for row in register["applications"]] != application_names
    ):
        raise RuntimeError("C32 registration changed track/application identity or order")
    write(REGISTER, register)
    print(json.dumps({
        "status": "registered",
        "tracks": len(track_ids),
        "applications": len(application_names),
        "c32_registrations": registrations,
        "served_exact_queries": 1024,
        "shadow_candidate_observations": 512,
        "candidate_results_served": 0,
        "shadow_promotion": False,
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
