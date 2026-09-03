"""Register independently verified C33 asynchronous-shadow evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c33-async-shadow-windows-20260901-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C33_BOUNDED_ASYNC_SHADOW_2026_09_01.md"
MACHINE = "learning_milestone_c33_async_shadow_results.json"
C32_MACHINE = "learning_milestone_c32_prepared_policy_shadow_results.json"


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
        raise RuntimeError("duplicate C33 registration")
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
    ratios = summary.get("aggregate_ratios", {})
    enqueue = summary.get("async_full_enqueue_ns", {})
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
        or summary.get("measurement_batches") != 256
        or summary.get("counterbalanced_groups") != 64
        or summary.get("served_exact_queries") != 2048
        or summary.get("candidate_observations") != 1152
        or summary.get("pre_ack_candidate_observations") != 0
        or summary.get("semantic_or_artifact_mismatches") != 0
        or summary.get("candidate_results_served") != 0
        or summary.get("exact_containment_gate") is not True
        or summary.get("timing_gate") is not True
        or summary.get("c33_local_gate") is not True
        or verification.get("status") != "verified"
        or verification.get("served_exact_queries_replayed") != 2048
        or verification.get("async_candidate_observations_replayed") != 640
        or verification.get("synchronous_candidate_observations_replayed") != 512
        or verification.get("candidate_results_served") != 0
        or verification.get("pre_ack_candidate_observations") != 0
        or verification.get("semantic_or_artifact_mismatches") != 0
        or verification.get("results_sha256") != sha256(RUN / "results.json")
        or verification.get("manifest_sha256") != sha256(RUN / "manifest.json")
        or spec.get("delivery_ack_required_before_candidate") is not True
        or spec.get("candidate_observed_only") is not True
    ):
        raise RuntimeError("refusing C33 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c33-async-shadow-summary/v1",
        "date": "2026-09-01",
        "status": "verified_local_async_shadow_no_promotion",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "source_milestone": "C32",
        "dataset_cases": 48,
        "measurement_batches": 256,
        "counterbalanced_groups": 64,
        "served_exact_queries": 2048,
        "candidate_observations": 1152,
        "candidate_observations_by_method": summary[
            "candidate_observations_by_method"],
        "observation_coverage_by_method": summary[
            "observation_coverage_by_method"],
        "pre_ack_candidate_observations": 0,
        "semantic_or_artifact_mismatches": 0,
        "candidate_results_served": 0,
        "production_writes": 0,
        "functional_controls_replayed": 10,
        "exact_containment_gate": True,
        "timing_gate": True,
        "c33_local_gate": True,
        "aggregate_ratios": ratios,
        "async_full_enqueue_ns": enqueue,
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
            "C33 structurally prevents candidate execution before exact-response delivery, "
            "then observes the unchanged prepared candidate behind a bounded queue. Full "
            "asynchronous shadowing costs 1.038x the disabled serving path with an 80.3 "
            "microsecond enqueue p95, versus 2.040x for synchronous C32 shadowing. This is "
            "verified local engineering evidence only; no candidate was served or promoted."
        ),
    }
    write(DOCS / MACHINE, machine)

    scope = (
        "C33 adds an immutable, hash-bound, bounded shadow queue with explicit post-delivery "
        "acknowledgement. Across 2,048 exact responses and 1,152 observations, independent "
        "replay found zero pre-ack starts, mismatches, candidate deliveries, writes, or "
        "promotions. Full asynchronous serving measured 1.038x disabled versus 2.040x for "
        "synchronous shadowing; all ten failure and lifecycle controls passed."
    )
    next_experiment = (
        "C34 should freeze a task-matched larger natural workload suite and measure exact "
        "end-to-end headroom before more learning: compare CM/GF(2), plain and flattened CSE, "
        "packed operations, ABC/AIG, CUDD/BDD, and SAT only on contracts where outputs and "
        "setup/amortization charges align. Resume ranking only for paths that beat their "
        "native controls by enough to pay recognition and verification overhead."
    )
    register = load(REGISTER)
    track_ids = [row["id"] for row in register["tracks"]]
    application_names = [row["name"] for row in register["applications"]]
    if len(track_ids) != 18 or len(set(track_ids)) != 18 or len(application_names) != 8:
        raise RuntimeError("track/application inventory changed before C33 registration")
    registrations = 0
    for collection in (register["tracks"], register["applications"]):
        for row in collection:
            if not any(item.get("machine_summary") == C32_MACHINE
                       for item in row.get("results", [])):
                continue
            upsert(row, scope)
            registrations += 1
            if "status_reason" in row:
                row["status_reason"] = scope
            if "next_experiment" in row:
                row["next_experiment"] = next_experiment
    if registrations != 9:
        raise RuntimeError(f"expected nine C33 registrations, observed {registrations}")
    register["milestones"]["F"] = (
        "C33 replaces synchronous prepared-policy observation with an acknowledged bounded "
        "queue; exact containment and local timing gates pass with zero candidate delivery "
        "or production write, enabling a shift to larger task-matched natural workloads"
    )
    register["updated"] = "2026-09-01"
    if (
        [row["id"] for row in register["tracks"]] != track_ids
        or [row["name"] for row in register["applications"]] != application_names
    ):
        raise RuntimeError("C33 registration changed track/application identity or order")
    write(REGISTER, register)
    print(json.dumps({
        "status": "registered",
        "tracks": len(track_ids),
        "applications": len(application_names),
        "c33_registrations": registrations,
        "served_exact_queries": 2048,
        "candidate_observations": 1152,
        "pre_ack_candidate_observations": 0,
        "candidate_results_served": 0,
        "shadow_promotion": False,
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
