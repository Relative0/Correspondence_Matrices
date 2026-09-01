"""Register independently verified C27 support-aware confirmation evidence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c27-support-aware-fresh-windows-20260831-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C27_SUPPORT_AWARE_FRESH_CONFIRMATION_2026_08_31.md"
MACHINE = "learning_milestone_c27_support_aware_fresh_confirmation_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False,
    ).encode("utf-8") + b"\n")


def upsert(container: dict, scope: str) -> None:
    value = {"report": REPORT, "machine_summary": MACHINE, "scope": scope}
    matches = [row for row in container["results"] if row.get("report") == REPORT]
    if len(matches) > 1:
        raise SystemExit("duplicate C27 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    controls = load(RUN / "functional_controls.json")
    corpus_verification = load(DOCS / "c27_yosys_fresh_gf2_dataset_verification.json")
    linux_manifest_path = DOCS / "c27_linux_confirmation/c27_linux_upload_manifest.json"
    linux_validation_path = DOCS / (
        "c27_linux_confirmation/C27_PACKAGE_LOCAL_VALIDATION_20260831.json")
    availability_path = DOCS / (
        "c27_linux_confirmation/RUNPOD_C27_AVAILABILITY_BLOCKED_VERIFICATION_V2_20260901.json")
    reconciliation_path = DOCS / (
        "c27_linux_confirmation/RUNPOD_C27_PROXY_404_RECONCILIATION_20260901.json")
    retry_reconciliation_path = DOCS / (
        "c27_linux_confirmation/RUNPOD_C27_RETRY_002_HTTP500_RECONCILIATION_20260901.json")
    docker_verification_path = DOCS / (
        "c27_linux_confirmation/C27_DOCKER_LINUX_PORTABILITY_VERIFICATION_20260901.json")
    docker_repeatability_path = DOCS / (
        "c27_linux_confirmation/C27_DOCKER_LINUX_REPEATABILITY_VERIFICATION_20260901.json")
    portable_validation_path = DOCS / (
        "c27_independent_docker_confirmation/"
        "C27_INDEPENDENT_DOCKER_PACKAGE_LOCAL_VALIDATION_20260901.json")
    retry003_readiness_path = DOCS / (
        "c27_linux_confirmation/RUNPOD_C27_RETRY_003_READINESS_20260901.json")
    retry003_request_path = DOCS / (
        "c27_linux_confirmation/RUNPOD_C27_RETRY_003_AUTHORIZATION_REQUEST_20260901.json")
    linux_manifest = load(linux_manifest_path)
    linux_validation = load(linux_validation_path)
    availability = load(availability_path)
    reconciliation = load(reconciliation_path)
    retry_reconciliation = load(retry_reconciliation_path)
    docker_verification = load(docker_verification_path)
    docker_repeatability = load(docker_repeatability_path)
    portable_validation = load(portable_validation_path)
    retry003_readiness = load(retry003_readiness_path)
    retry003_request = load(retry003_request_path)
    summary = result["summary"]
    q8 = summary["by_query_count"]["8"]["methods"]["support_aware_c27_advice_on"]
    q16 = summary["by_query_count"]["16"]["methods"]["support_aware_c27_advice_on"]
    q32 = summary["by_query_count"]["32"]["methods"]["support_aware_c27_advice_on"]
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("measurement_batches") != 720
        or result.get("timed_queries") != 7560
        or result.get("memory_measurement_batches") != 24
        or result.get("fallback_controls") != 48
        or result.get("selected_path_controls") != 48
        or result.get("tiny_truth_path_controls") != 24
        or result.get("large_packed_path_controls") != 24
        or result.get("refusal_controls") != 10
        or result.get("context_tamper_controls") != 4
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("claims", {}).get("support_policy_frozen_before_corpus") is not True
        or result.get("claims", {}).get("transparent_support_rule") is not True
        or result.get("claims", {}).get("fresh_confirmation") is not True
        or result.get("claims", {}).get("policy_refit") is not False
        or result.get("claims", {}).get("production_promotion") is not False
        or summary.get("exactness_gate") is not True
        or summary.get("functional_control_gate") is not True
        or summary.get("support_aware_break_even_query_count") != 8
        or summary.get("support_aware_confirmation_gate") is not True
        or controls.get("all_passed") is not True
        or corpus_verification.get("status") != "verified"
        or corpus_verification.get("dataset_reconstruction_mismatches") != 0
        or corpus_verification.get("scalar_oracle_mismatches") != 0
        or corpus_verification.get("prior_truth_overlaps") != 0
        or verification.get("status") != "verified"
        or verification.get("fallback_controls_replayed") != 48
        or verification.get("selected_path_controls_checked") != 48
        or verification.get("refusal_controls_checked") != 10
        or verification.get("measurement_batches_checked") != 720
        or verification.get("timed_query_records_checked") != 7560
        or verification.get("support_aware_contexts_semantically_replayed") != 2520
        or verification.get("support_aware_cache_records_checked") != 2520
        or verification.get("memory_batches_checked") != 24
        or verification.get("summary_recomputed") is not True
        or verification.get("semantic_or_artifact_mismatches") != 0
        or verification.get("production_promotion") is not False
        or linux_manifest.get("file_count") != 63
        or linux_manifest.get("bytes") != 1078671
        or linux_manifest.get("authorization_status")
        != "upload_not_authorized_exact_approval_pending"
        or linux_validation.get("status") != "pass"
        or linux_validation.get("measurement_batches") != 720
        or linux_validation.get("timed_queries") != 7560
        or linux_validation.get("semantic_or_artifact_mismatches") != 0
        or linux_validation.get("independent_verification") != "verified"
        or linux_validation.get("support_aware_confirmation_gate") is not False
        or availability.get("status") != "verified_reconciled"
        or availability.get("create_requests") != 0
        or availability.get("pod_created") is not False
        or availability.get("files_uploaded") != 0
        or availability.get("estimated_cost_usd") != 0.0
        or availability.get("authorization_remains_unused") is not True
        or availability.get("blocker") != "no_eligible_secure_cpu_offer"
        or reconciliation.get("status") != "verified_reconciled"
        or reconciliation.get("create_requests") != 1
        or reconciliation.get("authorization_consumed") is not True
        or reconciliation.get("replacement_authorized") is not False
        or reconciliation.get("new_exact_create_authorization_required") is not True
        or reconciliation.get("resource_contract_passed") is not True
        or reconciliation.get("source_files_uploaded") != 0
        or reconciliation.get("owned_pod_absent") is not True
        or reconciliation.get("unrelated_pod_preserved") is not True
        or reconciliation.get("failure")
        != "transient_proxy_http_404_before_payload_acceptance"
        or float(reconciliation.get("estimated_compute_cost_usd", 1)) > 0.05
        or retry_reconciliation.get("status") != "verified_reconciled"
        or retry_reconciliation.get("retry_attempt") != 2
        or retry_reconciliation.get("create_requests") != 1
        or retry_reconciliation.get("create_http_status") != 500
        or retry_reconciliation.get("create_response_uncertain") is not True
        or retry_reconciliation.get("authorization_consumed") is not True
        or retry_reconciliation.get("replacement_authorized") is not False
        or retry_reconciliation.get("pod_ever_observed") is not False
        or retry_reconciliation.get("pod_created") is not False
        or retry_reconciliation.get("source_files_uploaded") != 0
        or retry_reconciliation.get("post_horizon_inventory_checked") is not True
        or retry_reconciliation.get("owned_pod_absent") is not True
        or retry_reconciliation.get("unrelated_pod_preserved") is not True
        or retry_reconciliation.get("scientific_replication_complete") is not False
        or docker_verification.get("status") != "verified"
        or docker_verification.get("second_machine_replication") is not False
        or docker_verification.get("second_machine_replication_pending") is not True
        or docker_verification.get("network_during_workload") is not False
        or docker_verification.get("measurement_batches") != 720
        or docker_verification.get("timed_queries") != 7560
        or docker_verification.get("semantic_or_artifact_mismatches") != 0
        or docker_verification.get("independent_verification") != "verified"
        or docker_verification.get("docker_linux", {}).get("gate") is not True
        or docker_verification.get("docker_linux", {}).get(
            "break_even_query_count") != 8
        or docker_verification.get("timing_gate_passes_across_three_same_host_runs") != 2
        or docker_verification.get("production_promotion") is not False
        or docker_repeatability.get("status") != "verified"
        or docker_repeatability.get("repetition_count") != 3
        or docker_repeatability.get("timing_gate_passes") != 3
        or docker_repeatability.get("break_even_query_counts") != [8, 8, 8]
        or docker_repeatability.get("timed_queries_total") != 22680
        or docker_repeatability.get("semantic_or_artifact_mismatches") != 0
        or docker_repeatability.get("all_independent_verifications_passed") is not True
        or docker_repeatability.get("network_during_workload") is not False
        or docker_repeatability.get("second_machine_replication") is not False
        or docker_repeatability.get("production_promotion") is not False
        or portable_validation.get("status") != "pass"
        or portable_validation.get("package_files") != 70
        or portable_validation.get("archive_bytes") != 211551
        or portable_validation.get("source_files") != 63
        or portable_validation.get("source_bytes") != 1078671
        or portable_validation.get("second_machine_replication") is not False
        or portable_validation.get("network_during_workload") is not False
        or portable_validation.get("result_summary", {}).get("status") != "verified"
        or portable_validation.get("result_summary", {}).get(
            "semantic_or_artifact_mismatches") != 0
        or retry003_readiness.get("status") != "ready_read_only"
        or retry003_readiness.get("preferred_cpu_flavor") != "cpu5c"
        or retry003_readiness.get("preferred_availability") != "HIGH"
        or retry003_readiness.get("resource_writes") != 0
        or retry003_request.get("status") != "awaiting_exact_user_approval"
        or retry003_request.get("authorization_granted") is not False
        or retry003_request.get("requested_additional_create_requests") != 1
        or retry003_request.get("required_cpu_flavor") != "cpu5c"
    ):
        raise SystemExit("refusing C27 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c27-support-aware-summary/v1",
        "date": "2026-08-31",
        "status": "fresh_local_and_same_host_linux_confirmation_second_machine_pending",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "dataset": result["dataset"],
        "methods": list(summary["by_query_count"]["1"]["methods"]),
        "measurement_batches": result["measurement_batches"],
        "timed_queries": result["timed_queries"],
        "memory_measurement_batches": result["memory_measurement_batches"],
        "fallback_controls": result["fallback_controls"],
        "selected_path_controls": result["selected_path_controls"],
        "refusal_controls": result["refusal_controls"],
        "context_tamper_controls": result["context_tamper_controls"],
        "summary": summary,
        "corpus_verification": corpus_verification,
        "verification": {
            "path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace(
                "\\", "/"),
            **verification,
        },
        "semantic_or_artifact_mismatches": 0,
        "policy_refit": False,
        "fresh_confirmation": True,
        "linux_replication": {
            "status": "retry_002_http500_reconciled_no_scientific_result",
            "manifest": str(linux_manifest_path.relative_to(ROOT)).replace("\\", "/"),
            "manifest_file_count": linux_manifest["file_count"],
            "manifest_bytes": linux_manifest["bytes"],
            "manifest_authorization_status_at_freeze": linux_manifest["authorization_status"],
            "local_validation": str(linux_validation_path.relative_to(ROOT)).replace(
                "\\", "/"),
            "local_validation_status": linux_validation["status"],
            "isolated_timing_gate": linux_validation["support_aware_confirmation_gate"],
            "availability_verification": str(availability_path.relative_to(ROOT)).replace(
                "\\", "/"),
            "availability_status": availability["status"],
            "prior_blocker": availability["blocker"],
            "reconciliation": str(reconciliation_path.relative_to(ROOT)).replace(
                "\\", "/"),
            "reconciliation_status": reconciliation["status"],
            "prior_failure": reconciliation["failure"],
            "retry_reconciliation": str(
                retry_reconciliation_path.relative_to(ROOT)).replace("\\", "/"),
            "retry_reconciliation_status": retry_reconciliation["status"],
            "failure": retry_reconciliation["failure"],
            "create_requests_total": 2,
            "pods_created_total": 1,
            "source_files_uploaded_total": 0,
            "retry_create_requests": retry_reconciliation["create_requests"],
            "retry_authorization_consumed": retry_reconciliation[
                "authorization_consumed"],
            "post_horizon_inventory_checked": retry_reconciliation[
                "post_horizon_inventory_checked"],
            "scientific_replication_complete": False,
            "unrelated_pod_modified": False,
            "used": True,
            "cost_usd": reconciliation["estimated_compute_cost_usd"],
        },
        "same_host_linux_portability": {
            "status": "verified_three_of_three_gate_passed_not_second_machine",
            "verification": str(docker_verification_path.relative_to(ROOT)).replace(
                "\\", "/"),
            "runtime": docker_verification["runtime"],
            "network_during_workload": False,
            "measurement_batches": docker_verification["measurement_batches"],
            "timed_queries": docker_verification["timed_queries"],
            "semantic_or_artifact_mismatches": 0,
            "timing_gate": docker_verification["docker_linux"]["gate"],
            "break_even_query_count": docker_verification[
                "docker_linux"]["break_even_query_count"],
            "second_machine_replication": False,
            "repeatability_verification": str(
                docker_repeatability_path.relative_to(ROOT)).replace("\\", "/"),
            "repetition_count": docker_repeatability["repetition_count"],
            "timing_gate_passes": docker_repeatability["timing_gate_passes"],
            "break_even_query_counts": docker_repeatability["break_even_query_counts"],
            "q8_aggregate_min": docker_repeatability["q8_aggregate_min"],
            "q8_minimum_width_min": docker_repeatability["q8_minimum_width_min"],
            "timed_queries_total": docker_repeatability["timed_queries_total"],
        },
        "independent_docker_package": {
            "status": "locally_validated_awaiting_independent_host",
            "validation": str(portable_validation_path.relative_to(ROOT)).replace(
                "\\", "/"),
            "package_files": portable_validation["package_files"],
            "archive_bytes": portable_validation["archive_bytes"],
            "result_archive_bytes": portable_validation["result_archive_bytes"],
            "local_validation_scope": portable_validation["scientific_scope"],
            "local_validation_timing_gate": portable_validation[
                "result_summary"]["support_aware_confirmation_gate"],
            "second_machine_replication": False,
        },
        "retry_003": {
            "status": "readiness_high_awaiting_exact_user_approval",
            "readiness": str(retry003_readiness_path.relative_to(ROOT)).replace(
                "\\", "/"),
            "authorization_request": str(
                retry003_request_path.relative_to(ROOT)).replace("\\", "/"),
            "authorization_granted": False,
            "required_cpu_flavor": "cpu5c",
            "quoted_rate_usd_per_hour": retry003_request[
                "quoted_rate_usd_per_hour"],
            "create_requests": 0,
        },
        "production_promotion": False,
        "interpretation": (
            "The support rule was frozen before a 48-case unused-generator corpus. It first "
            f"passed at eight queries with {q8['aggregate_speedup_over_direct_screened']:.3f}x "
            f"aggregate and {q8['minimum_width_speedup_over_direct_screened']:.3f}x worst width, "
            f"and also passed at sixteen ({q16['aggregate_speedup_over_direct_screened']:.3f}x, "
            f"{q16['minimum_width_speedup_over_direct_screened']:.3f}x). The 32-query aggregate "
            f"was {q32['aggregate_speedup_over_direct_screened']:.3f}x, so profitability is not "
            "monotonic. The isolated package rerun also failed the timing gate while preserving "
            "every exact invariant. Unchanged Linux replication remains informative, but the "
            "current profitability evidence is timing-sensitive and production remains false. "
            "After earlier zero-create capacity waits, one compliant Secure CPU pod was created, "
            "but a transient proxy 404 occurred before payload acceptance. A separately "
            "authorized retry later received HTTP 500 from the create endpoint; no retry pod "
            "appeared in 35 ownership-scoped inventory checks through the full horizon. Across "
            "both RunPod create requests, zero source files were uploaded and no remote Linux "
            "scientific result was produced. The unchanged package subsequently passed all "
            "exactness gates in three same-host network-disabled Linux Docker repetitions. The "
            "timing gate passed at eight queries in all three, with a worst observed q8 aggregate "
            f"of {docker_repeatability['q8_aggregate_min']:.3f}x. This adds repeatable "
            "OS/container portability evidence but is not an independent second-machine result."
            " A transport-neutral Docker archive has passed extracted-package validation and "
            "is ready for a distinct host. RunPod retry-003 readiness is high for the diversified "
            "cpu5c flavor, but its exact one-create request remains unapproved and zero-write."
        ),
    }
    write(DOCS / MACHINE, machine)

    data = load(REGISTER)
    if (
        [row["id"] for row in data.get("tracks", [])]
        != [f"R{index:02d}" for index in range(1, 19)]
        or len(data.get("applications", [])) != 8
    ):
        raise SystemExit("refusing C27 update: 18-track or 8-application shape changed")
    tracks = {row["id"]: row for row in data["tracks"]}
    scope = (
        "C27 froze an n<=4 truth-screened / n>=5 packed-screened rule before a new 48-case "
        "unused-generator corpus. All 7,560 exact timed queries and controls passed; the local "
        "confirmation gate first passed at 8 queries. An isolated package rerun preserved every "
        "exact invariant but not the timing gate. After earlier capacity waits, one compliant "
        "Linux pod was created, but a transient proxy 404 occurred before payload acceptance. "
        "Retry-002 then received HTTP 500 at create and no pod appeared through the full "
        "reconciliation horizon. Across both requests, zero source files were uploaded and no "
        "remote Linux timing evidence was produced. Three same-host Linux Docker repetitions "
        "then preserved all exact invariants and passed the timing gate at eight queries, adding "
        "repeatable OS/container portability evidence while leaving second-machine replication "
        "pending. A 70-file transport-neutral Docker archive passed extracted-package local "
        "validation and is ready for a physically distinct host; a cpu5c RunPod retry-003 "
        "request is prepared but not authorized."
    )
    for track_id in ("R01", "R02", "R06", "R11", "R13", "R16", "R17", "R18"):
        upsert(tracks[track_id], scope)
        tracks[track_id]["status"] = "measured"
        tracks[track_id]["status_reason"] = scope
    next_experiment = (
        "Run the unchanged frozen C27 package on an independent Linux machine with the same "
        "pinned runtime and network-disabled workload; compare its timing surface with the "
        "three verified same-host Docker repetitions and retain all exactness controls."
    )
    for track_id in ("R01", "R02", "R06", "R11", "R13", "R16", "R17", "R18"):
        tracks[track_id]["next_experiment"] = next_experiment
    hardware = next(
        item for item in data["applications"] if item["name"] == "Hardware verification/design")
    upsert(hardware, scope)
    data["milestones"]["F"] = (
        "C27 independently verifies a frozen support-aware exact GF(2) rule on a fresh corpus; "
        "the primary gate passes at 8 and 16 queries, an isolated rerun preserves exactness but "
        "not timing profitability; two authorized Linux create requests were safely reconciled "
        "after proxy-404 and create-HTTP-500 transport failures, with zero source uploads; a "
        "three same-host Linux Docker repetitions then preserve exactness and pass at eight "
        "queries, but are not a second-machine result"
    )
    data["updated"] = "2026-08-31"
    write(REGISTER, data)
    print(json.dumps({
        "tracks": len(data["tracks"]), "applications": len(data["applications"]),
        "updated_tracks": ["R01", "R02", "R06", "R11", "R13", "R16", "R17", "R18"],
        "milestone": "C27/F7", "support_aware_confirmation_gate": True,
        "isolated_package_timing_gate": False,
        "linux_replication": "retry_002_http500_reconciled_no_scientific_result",
        "same_host_linux_portability": (
            "verified_three_of_three_gate_passed_not_second_machine"),
        "independent_docker_package": "locally_validated_awaiting_independent_host",
        "retry_003": "readiness_high_awaiting_exact_user_approval",
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
