"""Register the verified unchanged C31 physical-machine replication."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
HERE = DOCS / "c31_linux_confirmation"
RUN = HERE / "runpod-c31-linux-execute-002"
REMOTE = RUN / "evidence/run-output/c31-prepared-policy-linux-20260901-001"
FINAL = HERE / "RUNPOD_C31_FINAL_VERIFICATION_20260901.json"
ADJUDICATION = HERE / "C31_CROSS_MACHINE_ADJUDICATION_20260901.json"
RECONCILIATION = HERE / "C31_INITIAL_NO_CREATE_RECONCILIATION_20260901.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C31_PROSPECTIVE_SECOND_MACHINE_FREEZE_2026_09_01.md"
MACHINE = "learning_milestone_c31_prepared_policy_replication_results.json"
C30_MACHINE = "learning_milestone_c30_prepared_policy_context_results.json"


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
        raise RuntimeError("duplicate C31 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    final = load(FINAL)
    adjudication = load(ADJUDICATION)
    run = load(RUN / "RUN.json")
    runtime = load(RUN / "evidence/run-output/RUNTIME.json")
    remote_result = load(REMOTE / "results.json")
    reconciliation = load(RECONCILIATION)
    if (
        final.get("status") != "pass"
        or final.get("scientific_replication_complete") is not True
        or final.get("post_retrieval_verification_byte_identical") is not True
        or final.get("semantic_or_artifact_mismatches") != 0
        or final.get("owned_pod_absent_verified") is not True
        or adjudication.get("replication_admissible") is not True
        or adjudication.get("eligible_for_separate_shadow_review") is not True
        or adjudication.get("shadow_promotion") is not False
        or adjudication.get("production_promotion") is not False
        or adjudication.get("execution_count") != 2
        or adjudication.get("physical_machine_count") != 2
        or adjudication.get("exactness_and_charge_gate") is not True
        or adjudication.get("point_gate_all_executions") is not True
        or adjudication.get("paired_lower_gate_all_executions") is not True
        or run.get("status") != "complete"
        or run.get("uploaded_source_files") != 71
        or reconciliation.get("authorized_create_consumed") is not False
        or reconciliation.get("owned_pod_absent") is not True
        or remote_result.get("policy_refit") is not False
        or remote_result.get("training") is not False
    ):
        raise RuntimeError("refusing C31 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c31-prepared-policy-replication-summary/v1",
        "date": "2026-09-01",
        "status": "verified_cross_machine_replication_eligible_for_separate_shadow_review",
        "report": REPORT,
        "source_milestone": "C30",
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "remote_scientific_run": str(REMOTE.relative_to(ROOT)).replace("\\", "/"),
        "package": {"source_files": 71, "source_bytes": 1153868},
        "initial_transport_invocation": {
            "status": "reconciled_no_create",
            "creation_attempted": False,
            "pod_created": False,
            "upload_performed": False,
            "estimated_compute_cost_usd": None,
            "authorized_create_consumed": False,
            "reconciliation": str(RECONCILIATION.relative_to(ROOT)).replace("\\", "/"),
        },
        "authorized_execution": {
            "create_requests": 1,
            "replacement_attempts": 0,
            "pod_created": True,
            "pod_id": final["pod_id"],
            "cpu_flavor": final["cpu_flavor"],
            "cpu_model": final["cpu_model"],
            "quoted_rate_usd_per_hour": final["quoted_rate_usd_per_hour"],
            "estimated_compute_cost_usd": final["estimated_compute_cost_usd"],
            "elapsed_since_create_s": final["elapsed_since_create_s"],
            "owned_pod_absent_verified": True,
        },
        "runtime": runtime,
        "measurement_batches": 128,
        "paired_batches": 64,
        "timed_queries": 1024,
        "verified_context_records_replayed": 512,
        "functional_controls_replayed": 6,
        "semantic_or_artifact_mismatches": 0,
        "post_retrieval_verification_byte_identical": True,
        "remote_point_estimates": {
            "aggregate_charged_total_speedup": final["aggregate_charged_total_speedup"],
            "minimum_width_charged_total_speedup": final[
                "minimum_width_charged_total_speedup"],
        },
        "cross_machine_floors": adjudication["cross_machine_floors"],
        "execution_results": adjudication["execution_results"],
        "decision": adjudication["decision"],
        "replication_admissible": True,
        "eligible_for_separate_shadow_review": True,
        "policy_refit": False,
        "training": False,
        "shadow_promotion": False,
        "production_promotion": False,
        "final_verification": str(FINAL.relative_to(ROOT)).replace("\\", "/"),
        "cross_machine_adjudication": str(ADJUDICATION.relative_to(ROOT)).replace("\\", "/"),
        "evidence_sha256": {
            "final_verification": sha256(FINAL),
            "cross_machine_adjudication": sha256(ADJUDICATION),
            "remote_results": sha256(REMOTE / "results.json"),
            "remote_measurements": sha256(REMOTE / "measurements.jsonl"),
        },
        "interpretation": (
            "The unchanged prepared-policy candidate passed the prospective C31 point "
            "and distribution-free paired-block gates on Windows and a physical Linux "
            "RunPod host. The cross-machine floors are 1.036x aggregate point, 1.000x "
            "minimum-width point, 1.024x aggregate lower bound, and 0.956x minimum-width "
            "lower bound. This admits a separate shadow review only; no shadow or "
            "production promotion occurred."
        ),
    }
    write(DOCS / MACHINE, machine)

    scope = (
        "C31 ran the unchanged 71-file C30 package on a Secure AMD EPYC 9655 RunPod "
        "with no training or refit. The on-pod verifier and byte-identical local replay "
        "checked 128 batches, 1,024 exact queries, and 512 contexts with zero mismatches. "
        "Both physical machines pass the prospective point and paired-lower gates; the "
        "cross-machine floors are 1.036x/1.000x point and 1.024x/0.956x lower-bound. "
        "The candidate is eligible for a separate shadow review, but no promotion occurred."
    )
    next_experiment = (
        "C32 should implement an opt-in production-shaped shadow boundary around the "
        "frozen C30 prepared context: emit both exact baseline and candidate artifacts, "
        "serve only the baseline, measure boundary overhead and fallback/refusal events, "
        "and require zero divergence before considering a separately authorized rollout."
    )
    register = load(REGISTER)
    track_ids = [row["id"] for row in register["tracks"]]
    application_names = [row["name"] for row in register["applications"]]
    if len(track_ids) != 18 or len(set(track_ids)) != 18 or len(application_names) != 8:
        raise RuntimeError("track/application inventory changed before C31 registration")
    registrations = 0
    for collection in (register["tracks"], register["applications"]):
        for row in collection:
            if not any(item.get("machine_summary") == C30_MACHINE
                       for item in row.get("results", [])):
                continue
            upsert(row, scope)
            registrations += 1
            if "status_reason" in row:
                row["status_reason"] = scope
            if "next_experiment" in row:
                row["next_experiment"] = next_experiment
    if registrations != 9:
        raise RuntimeError(f"expected nine C31 registrations, observed {registrations}")
    register["milestones"]["F"] = (
        "C31 prospectively replicates the unchanged C30 prepared-policy path on a "
        "physical Linux machine; both machines pass point and paired-lower gates with "
        "zero mismatches, admitting a separate shadow review while promotion stays false"
    )
    register["updated"] = "2026-09-01"
    if (
        [row["id"] for row in register["tracks"]] != track_ids
        or [row["name"] for row in register["applications"]] != application_names
    ):
        raise RuntimeError("C31 registration changed track/application identity or order")
    write(REGISTER, register)
    print(json.dumps({
        "status": "registered",
        "tracks": len(track_ids),
        "applications": len(application_names),
        "c31_registrations": registrations,
        "replication_admissible": True,
        "eligible_for_separate_shadow_review": True,
        "shadow_promotion": False,
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
