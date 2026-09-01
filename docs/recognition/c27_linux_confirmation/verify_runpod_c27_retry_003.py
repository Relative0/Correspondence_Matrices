"""Independently adjudicate the completed C27 retry-003 RunPod replication."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_support_aware_experiment import METHODS, summarize


RUN_DIR = HERE / "runpod-c27-linux-execute-001f"
STUDY_NAME = "c27-support-aware-fresh-linux-20260831-001"
STUDY = RUN_DIR / "evidence/run-output" / STUDY_NAME
REPLAY = RUN_DIR / "post-retrieval-independent-replay"
MANIFEST = HERE / "c27_linux_upload_manifest.json"
AUTHORIZATION = HERE / "RUNPOD_C27_RETRY_003_EXACT_PAYLOAD_AUTHORIZED_2026_09_01.json"
REQUEST = HERE / "RUNPOD_C27_RETRY_003_AUTHORIZATION_REQUEST_20260901.json"
READINESS = HERE / "RUNPOD_C27_RETRY_003_READINESS_20260901.json"
PROTOCOL = HERE / "C27_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md"
LOCAL_VALIDATION = HERE / "C27_PACKAGE_LOCAL_VALIDATION_20260831.json"
PRIOR_RECONCILIATION = HERE / "RUNPOD_C27_RETRY_002_HTTP500_RECONCILIATION_20260901.json"
OUTPUT = HERE / "RUNPOD_C27_RETRY_003_FINAL_VERIFICATION_20260901.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    run = load(RUN_DIR / "RUN.json")
    watchdog = load(RUN_DIR / "WATCHDOG-RESULT.json")
    preflight = load(RUN_DIR / "PREFLIGHT.json")
    resources = load(RUN_DIR / "POD-RESOURCE-CHECK.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    manifest = load(MANIFEST)
    authorization = load(AUTHORIZATION)
    request = load(REQUEST)
    readiness = load(READINESS)
    local_validation = load(LOCAL_VALIDATION)
    prior = load(PRIOR_RECONCILIATION)

    evidence = RUN_DIR / "evidence/run-output"
    remote_validation = load(evidence / "REMOTE-VALIDATION.json")
    runtime = load(evidence / "RUNTIME.json")
    dependencies = load(evidence / "DEPENDENCIES.json")
    command = load(evidence / "c27-linux-replication.json")
    verification_command = load(evidence / "c27-linux-verification.json")
    result = load(STUDY / "results.json")
    remote_verification = load(STUDY / "independent_verification.json")
    replay_verification = load(REPLAY / "independent_verification.json")
    controls = load(STUDY / "functional_controls.json")
    rows = load_rows(STUDY / "measurements.jsonl")
    memory_rows = load_rows(STUDY / "memory_measurements.jsonl")

    identities = {
        (row.get("n_vars"), row.get("query_count"), row.get("method"), row.get("round"))
        for row in rows
    }
    memory_identities = {(row.get("n_vars"), row.get("method")) for row in memory_rows}
    recomputed_summary = summarize(rows, memory_rows, controls)
    actual = run.get("actual_resources", {})
    cleanup = run.get("cleanup", {})
    payload_attempts = run.get("payload_attempts", [])
    estimated_cost = run.get("estimated_compute_cost_usd")
    projected_cost = actual.get("projected_10_min_cost_usd")
    confirmation = remote_validation.get("confirmation_summary", {})
    image_tag, separator, image_digest = manifest["runtime"]["image"].partition("@")
    cpu5c_rows = [row for row in preflight.get("offers", []) if row.get("id") == "cpu5c"]

    invariants = {
        "one_create_remote_complete_no_replacement": (
            run.get("status") == "failed"
            and run.get("error_type") == "RuntimeError"
            and run.get("error") == "retrieved C27 evidence failed frozen gates"
            and run.get("creation_attempted") is True
            and run.get("creation_uncertain") is False
            and run.get("pod_created") is True
            and run.get("automatic_replacement_queued") is False
            and run.get("creation_http_status") == 201
            and run.get("remote_progress", {}).get("done") is True
            and run.get("remote_progress", {}).get("error") is None
            and run.get("remote_progress", {}).get("remote_status") == "complete"
            and run.get("remote_progress", {}).get("returncode") == 0
        ),
        "cpu5c_only_authorized_and_selected": (
            authorization.get("retry_attempt") == 3
            and authorization.get("create_requests") == 1
            and authorization.get("additional_create_requests") == 1
            and authorization.get("prior_create_requests") == 2
            and authorization.get("required_cpu_flavor") == "cpu5c"
            and authorization.get("fallback_cpu_flavors") == []
            and authorization.get("rate_cap_usd_per_hour") == 0.07
            and run.get("selected_cpu") == "cpu5c"
            and run.get("quoted_rate_usd_per_hour") == 0.07
            and actual.get("cpu_flavor") == "cpu5c"
            and len(cpu5c_rows) == 1
            and cpu5c_rows[0].get("eligible") is True
            and cpu5c_rows[0].get("rate_usd_per_hour") == 0.07
        ),
        "payload_accepted_within_same_pod_limit": (
            1 <= len(payload_attempts) <= 6
            and payload_attempts[-1].get("status") == "accepted"
            and run.get("uploaded_source_files") == 63
        ),
        "resource_contract": (
            actual.get("vcpu_count") == 2
            and actual.get("ram_gb") == 4.0
            and actual.get("container_disk_gb") == 12
            and actual.get("pod_volume_gb") == 0
            and actual.get("ports") == ["8080/http"]
            and actual.get("cloud_evidence") == ["SECURE"]
            and resources.get("network_volume_present") is False
            and actual.get("rate_usd_per_hour") == 0.07
            and isinstance(projected_cost, (int, float))
            and 0 <= projected_cost <= 0.05
        ),
        "bounded_cost_and_time": (
            isinstance(estimated_cost, (int, float))
            and 0 <= estimated_cost <= 0.05
            and 0 <= run.get("elapsed_since_create_s", math.inf) <= 600
        ),
        "cleanup_and_reconciliation": (
            cleanup.get("owned_pod_absent") is True
            and cleanup.get("inventories") == {"v1": [], "v2": []}
            and watchdog.get("status") == "controller_cleanup_verified"
            and watchdog.get("errors") == []
        ),
        "zero_write_preflight": (
            preflight.get("ready") is True
            and preflight.get("inventories") == {"v1": [], "v2": []}
            and preflight.get("resource_writes") == 0
            and preflight.get("c27_budget", {}).get("ready") is True
            and preflight.get("c27_budget", {}).get("rate_usd_per_hour") == 0.07
        ),
        "frozen_payload": (
            manifest.get("file_count") == 63
            and manifest.get("bytes") == 1078671
            and freeze.get("source_files") == 63
            and freeze.get("source_bytes") == 1078671
            and freeze.get("manifest_sha256") == sha256(MANIFEST)
            and freeze.get("authorization_sha256") == sha256(AUTHORIZATION)
            and freeze.get("protocol_sha256") == sha256(PROTOCOL)
            and freeze.get("local_validation_sha256") == sha256(LOCAL_VALIDATION)
            and freeze.get("prior_reconciliation_sha256") == sha256(PRIOR_RECONCILIATION)
            and freeze.get("retry_authorization_request_sha256") == sha256(REQUEST)
            and freeze.get("retry_readiness_sha256") == sha256(READINESS)
            and freeze.get("credentials_recorded_or_uploaded") is False
            and 0 < freeze.get("transport_payload_bytes", 1 << 20) < (1 << 20)
        ),
        "authorization_and_prior_attempt": (
            authorization.get("authorized") is True
            and authorization.get("one_create") is True
            and authorization.get("no_replacement") is True
            and authorization.get("controller_total_ceiling_usd") == 0.05
            and authorization.get("credentials_recorded_or_uploaded") is False
            and authorization.get("authorization_request_sha256") == sha256(REQUEST)
            and authorization.get("readiness_sha256") == sha256(READINESS)
            and authorization.get("prior_reconciliation_sha256") == sha256(PRIOR_RECONCILIATION)
            and request.get("retry_attempt") == 3
            and request.get("authorization_granted") is False
            and readiness.get("status") == "ready_read_only"
            and readiness.get("resource_writes") == 0
            and local_validation.get("status") == "pass"
            and local_validation.get("initial_file_count") == 63
            and local_validation.get("pythonpath_injected") is False
            and local_validation.get("vendored_dd_loaded_from_package") is True
            and prior.get("status") == "verified_reconciled"
            and prior.get("create_http_status") == 500
            and prior.get("pod_ever_observed") is False
            and prior.get("owned_pod_absent") is True
        ),
        "remote_runtime_and_vendored_dependencies": (
            runtime.get("source_files") == 63
            and runtime.get("runpod_pod_id") == run.get("pod_id")
            and separator == "@"
            and runtime.get("image_tag") == image_tag
            and runtime.get("image_amd64_digest") == image_digest
            and runtime.get("python", "").startswith("3.13.15 ")
            and set(dependencies) == {"numpy", "pip"}
            and dependencies.get("numpy") == "2.3.2"
            and dependencies.get("dd") is None
            and result.get("environment", {}).get("dd_version") == "0.6.0"
            and any(row.get("target") == "dd-0.6.0.dist-info/METADATA"
                    for row in manifest.get("files", []))
            and any(row.get("target") == "dd/autoref.py" for row in manifest.get("files", []))
        ),
        "remote_commands": (
            command.get("returncode") == 0
            and verification_command.get("returncode") == 0
            and (evidence / "c27-linux-replication.stderr.txt").stat().st_size == 0
            and (evidence / "c27-linux-verification.stderr.txt").stat().st_size == 0
            and remote_validation.get("status") == "complete"
            and remote_validation.get("error") is None
            and remote_validation.get("validation_error") is None
            and confirmation.get("status") == "complete"
            and confirmation.get("verification_status") == "verified"
        ),
        "exact_measurements": (
            len(rows) == 720
            and len(identities) == 720
            and {row.get("method") for row in rows} == set(METHODS)
            and sum(len(row.get("query_records", [])) for row in rows) == 7560
            and all(row.get("exact_check_passed") is True for row in rows)
            and len(memory_rows) == 24
            and len(memory_identities) == 24
            and all(row.get("exact_check_passed") is True for row in memory_rows)
        ),
        "independent_scientific_verification": (
            result.get("status") == "complete"
            and result.get("measurement_batches") == 720
            and result.get("timed_queries") == 7560
            and result.get("memory_measurement_batches") == 24
            and result.get("semantic_or_artifact_mismatches") == 0
            and result.get("claims", {}).get("unchanged_c25_direct_controls") is True
            and result.get("claims", {}).get("support_policy_frozen_before_corpus") is True
            and result.get("claims", {}).get("fresh_confirmation") is True
            and result.get("claims", {}).get("production_promotion") is False
            and result.get("summary") == recomputed_summary
            and remote_verification.get("status") == "verified"
            and remote_verification.get("measurement_batches_checked") == 720
            and remote_verification.get("timed_query_records_checked") == 7560
            and remote_verification.get("semantic_or_artifact_mismatches") == 0
            and replay_verification == remote_verification
            and sha256(REPLAY / "independent_verification.json")
            == sha256(STUDY / "independent_verification.json")
        ),
        "bounded_retrieval": (
            (RUN_DIR / "evidence.zip").is_file()
            and (RUN_DIR / "evidence.zip").stat().st_size <= 16 << 20
        ),
    }
    failed = [name for name, passed in invariants.items() if not passed]
    if failed:
        raise SystemExit("C27 retry-003 verification failed: " + ", ".join(failed))

    output = {
        "schema": "crse-runpod-c27-retry-003-final-verification/v1",
        "status": "pass",
        "complete": True,
        "scientific_confirmation_complete": True,
        "controller_status": "failed_local_vendored_dependency_metadata_gate",
        "controller_gate_adjudication": (
            "dd 0.6.0 was vendored and imported by the verified workload; it was intentionally "
            "absent from the installed-distribution inventory"
        ),
        "fresh_confirmation": True,
        "production_promotion": False,
        "invariants": invariants,
        "cases": 48,
        "methods": 6,
        "rounds": 5,
        "measurement_batches": 720,
        "timed_queries": 7560,
        "memory_batches": 24,
        "semantic_or_artifact_mismatches": 0,
        "support_aware_confirmation_gate": recomputed_summary[
            "support_aware_confirmation_gate"],
        "support_aware_break_even_query_count": recomputed_summary[
            "support_aware_break_even_query_count"],
        "summary": recomputed_summary,
        "create_requests_this_authorization": 1,
        "retry_attempt": 3,
        "automatic_replacement_queued": False,
        "pod_created": True,
        "pod_id": run["pod_id"],
        "cpu_flavor": actual["cpu_flavor"],
        "cpu_model": runtime["cpu_model"],
        "uploaded_source_files": 63,
        "uploaded_source_bytes": 1078671,
        "owned_pod_absent_verified": True,
        "final_inventories": {"v1": [], "v2": []},
        "estimated_compute_cost_usd": estimated_cost,
        "elapsed_since_create_s": run["elapsed_since_create_s"],
        "run_sha256": sha256(RUN_DIR / "RUN.json"),
        "watchdog_sha256": sha256(RUN_DIR / "WATCHDOG-RESULT.json"),
        "transport_freeze_sha256": sha256(RUN_DIR / "TRANSPORT-FREEZE.json"),
        "evidence_zip_sha256": sha256(RUN_DIR / "evidence.zip"),
        "measurements_sha256": sha256(STUDY / "measurements.jsonl"),
        "results_sha256": sha256(STUDY / "results.json"),
        "remote_verification_sha256": sha256(STUDY / "independent_verification.json"),
        "post_retrieval_replay_sha256": sha256(REPLAY / "independent_verification.json"),
        "manifest_sha256": sha256(MANIFEST),
        "authorization_sha256": sha256(AUTHORIZATION),
    }
    OUTPUT.write_bytes(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
