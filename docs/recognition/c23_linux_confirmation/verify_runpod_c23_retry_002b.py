"""Independently verify successful retry 002b of the C23 Linux replication."""
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

from cmbench.comparative.gf2_fresh_table_experiment import fresh_summary


RUN_DIR = HERE / "runpod-c23-linux-execute-002b"
STUDY = RUN_DIR / "evidence/run-output/c23-yosys-fresh-gf2-table-linux-20260831-001"
MANIFEST = HERE / "c23_linux_upload_manifest.json"
AUTHORIZATION = HERE / "RUNPOD_C23_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_08_31.json"
PROTOCOL = HERE / "C23_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md"
LOCAL_VALIDATION = HERE / "C23_PACKAGE_LOCAL_VALIDATION_20260831.json"
PRIOR_FAILURE = HERE / "RUNPOD_C23_FAILED_ATTEMPT_VERIFICATION_20260831.json"
OUTPUT = HERE / "RUNPOD_C23_RETRY_002B_FINAL_VERIFICATION_20260831.json"
METHODS = {
    "cm_exhaustive",
    "cm_screened",
    "cm_compiled_screened",
    "truth_anf_min_cut",
    "source_packed_anf",
    "bdd_level_cut",
    "source_interaction_cut",
}


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
    local_validation = load(LOCAL_VALIDATION)
    prior_failure = load(PRIOR_FAILURE)

    evidence_root = RUN_DIR / "evidence/run-output"
    remote_validation = load(evidence_root / "REMOTE-VALIDATION.json")
    runtime = load(evidence_root / "RUNTIME.json")
    dependencies = load(evidence_root / "DEPENDENCIES.json")
    command = load(evidence_root / "c23-linux-replication.json")
    verification_command = load(evidence_root / "c23-linux-verification.json")
    result = load(STUDY / "results.json")
    remote_verification = load(STUDY / "independent_verification.json")
    functional = load(STUDY / "functional.json")
    rows = load_rows(STUDY / "measurements.jsonl")
    memory_rows = load_rows(STUDY / "memory_measurements.jsonl")

    identities = {
        (row.get("case_id"), row.get("method"), row.get("round")) for row in rows
    }
    memory_identities = {
        (row.get("case_id"), row.get("method")) for row in memory_rows
    }
    recomputed_summary = fresh_summary(rows, memory_rows, functional)
    actual = run.get("actual_resources", {})
    projected_cost = actual.get("projected_10_min_cost_usd")
    estimated_cost = run.get("estimated_compute_cost_usd")
    payload_attempts = run.get("payload_attempts", [])
    cleanup = run.get("cleanup", {})
    confirmation = remote_validation.get("confirmation_summary", {})
    manifest_image_tag, separator, manifest_image_digest = (
        manifest["runtime"]["image"].partition("@"))

    invariants = {
        "one_create_no_replacement": (
            run.get("status") == "complete"
            and run.get("creation_attempted") is True
            and run.get("creation_uncertain") is False
            and run.get("pod_created") is True
            and run.get("automatic_replacement_queued") is False
            and run.get("creation_http_status") in (200, 201)
        ),
        "payload_accepted_within_same_pod_limit": (
            1 <= len(payload_attempts) <= 6
            and payload_attempts[-1].get("status") == "accepted"
            and run.get("uploaded_source_files") == 52
        ),
        "resource_contract": (
            actual.get("vcpu_count") == 2
            and isinstance(actual.get("ram_gb"), (int, float))
            and actual["ram_gb"] >= 4
            and actual.get("container_disk_gb") == 12
            and actual.get("pod_volume_gb") == 0
            and actual.get("ports") == ["8080/http"]
            and actual.get("cloud_evidence") == ["SECURE"]
            and resources.get("network_volume_present") is False
            and 0 < actual.get("rate_usd_per_hour", math.inf) <= 0.25
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
        "zero_pod_preflight": (
            preflight.get("ready") is True
            and preflight.get("inventories") == {"v1": [], "v2": []}
            and preflight.get("c23_budget", {}).get("ready") is True
        ),
        "frozen_payload": (
            manifest.get("file_count") == 52
            and manifest.get("bytes") == 903745
            and freeze.get("source_files") == 52
            and freeze.get("source_bytes") == 903745
            and freeze.get("manifest_sha256") == sha256(MANIFEST)
            and freeze.get("authorization_sha256") == sha256(AUTHORIZATION)
            and freeze.get("protocol_sha256") == sha256(PROTOCOL)
            and freeze.get("local_validation_sha256") == sha256(LOCAL_VALIDATION)
            and freeze.get("credentials_recorded_or_uploaded") is False
            and 0 < freeze.get("transport_payload_bytes", 1 << 20) < (1 << 20)
        ),
        "authorization_and_local_validation": (
            authorization.get("authorized") is True
            and authorization.get("retry_attempt") == 2
            and authorization.get("additional_create_requests") == 1
            and authorization.get("prior_failed_attempt_status") == "verified_reconciled"
            and authorization.get("prior_failed_attempt_verification_sha256") == sha256(PRIOR_FAILURE)
            and authorization.get("one_create") is True
            and authorization.get("no_replacement") is True
            and authorization.get("controller_total_ceiling_usd") == 0.05
            and authorization.get("credentials_recorded_or_uploaded") is False
            and local_validation.get("status") == "pass"
            and local_validation.get("initial_file_count") == 52
            and local_validation.get("pythonpath_injected") is False
            and local_validation.get("vendored_dd_loaded_from_package") is True
            and prior_failure.get("status") == "pass"
            and prior_failure.get("scientific_replication_complete") is False
            and prior_failure.get("pod_created") is False
            and prior_failure.get("files_uploaded") == 0
            and prior_failure.get("owned_pod_absent_verified") is True
        ),
        "remote_runtime": (
            runtime.get("source_files") == 52
            and runtime.get("runpod_pod_id") == run.get("pod_id")
            and separator == "@"
            and runtime.get("image_tag") == manifest_image_tag
            and runtime.get("image_amd64_digest") == manifest_image_digest
            and runtime.get("python", "").startswith("3.13.15 ")
            and dependencies.get("numpy") == "2.3.2"
            and dependencies.get("dd") == "0.6.0"
        ),
        "remote_commands": (
            command.get("returncode") == 0
            and verification_command.get("returncode") == 0
            and command.get("stderr_tail") in (None, "")
            and verification_command.get("stderr_tail") in (None, "")
            and remote_validation.get("status") == "complete"
            and remote_validation.get("error") is None
            and remote_validation.get("validation_error") is None
            and confirmation.get("status") == "complete"
            and confirmation.get("verification_status") == "verified"
        ),
        "exact_measurements": (
            len(rows) == 1680
            and len(identities) == 1680
            and {row.get("method") for row in rows} == METHODS
            and all(row.get("exact_check_passed") is True for row in rows)
            and len(memory_rows) == 56
            and len(memory_identities) == 56
            and all(row.get("exact_check_passed") is True for row in memory_rows)
        ),
        "independent_scientific_verification": (
            result.get("status") == "complete"
            and result.get("measurement_rows") == 1680
            and result.get("memory_measurement_rows") == 56
            and result.get("semantic_or_artifact_mismatches") == 0
            and result.get("claims", {}).get("same_requested_artifact") is True
            and result.get("claims", {}).get("unchanged_c21_methods") is True
            and result.get("claims", {}).get("fresh_confirmation") is True
            and result.get("claims", {}).get("production_promotion") is False
            and result.get("summary") == recomputed_summary
            and remote_verification.get("status") == "verified"
            and remote_verification.get("measurement_rows_checked") == 1680
            and remote_verification.get("memory_rows_checked") == 56
            and remote_verification.get("summary_recomputed") is True
            and remote_verification.get("semantic_or_artifact_mismatches") == 0
        ),
        "bounded_retrieval": (
            (RUN_DIR / "evidence.zip").is_file()
            and (RUN_DIR / "evidence.zip").stat().st_size <= 16 << 20
        ),
    }
    failed = [name for name, passed in invariants.items() if not passed]
    if failed:
        raise SystemExit("C23 RunPod verification failed: " + ", ".join(failed))

    output = {
        "schema": "crse-runpod-c23-retry-002b-final-verification/v1",
        "status": "pass",
        "complete": True,
        "scientific_confirmation_complete": True,
        "fresh_confirmation": True,
        "production_promotion": False,
        "invariants": invariants,
        "cases": 48,
        "methods": 7,
        "rounds": 5,
        "measurement_rows": 1680,
        "memory_rows": 56,
        "semantic_or_artifact_mismatches": 0,
        "summary": recomputed_summary,
        "create_requests_this_authorization": 1,
        "retry_attempt": 2,
        "prior_failed_attempt_verification_sha256": sha256(PRIOR_FAILURE),
        "automatic_replacement_queued": False,
        "pod_created": True,
        "pod_id": run["pod_id"],
        "uploaded_source_files": 52,
        "uploaded_source_bytes": 903745,
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
        "manifest_sha256": sha256(MANIFEST),
        "authorization_sha256": sha256(AUTHORIZATION),
    }
    OUTPUT.write_bytes(json.dumps(output, indent=2, sort_keys=True, allow_nan=False).encode()
                       + b"\n")
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
