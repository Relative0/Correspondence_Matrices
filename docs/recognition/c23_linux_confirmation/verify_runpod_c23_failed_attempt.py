"""Verify safe reconciliation of the failed first C23 create request."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "runpod-c23-linux-execute-001"
MANIFEST = HERE / "c23_linux_upload_manifest.json"
AUTHORIZATION = HERE / "RUNPOD_C23_EXACT_PAYLOAD_AUTHORIZED_2026_08_31.json"
PROTOCOL = HERE / "C23_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md"
LOCAL_VALIDATION = HERE / "C23_PACKAGE_LOCAL_VALIDATION_20260831.json"
OUTPUT = HERE / "RUNPOD_C23_FAILED_ATTEMPT_VERIFICATION_20260831.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    run = load(RUN_DIR / "RUN.json")
    watchdog = load(RUN_DIR / "WATCHDOG-RESULT.json")
    preflight = load(RUN_DIR / "PREFLIGHT.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    manifest = load(MANIFEST)
    authorization = load(AUTHORIZATION)
    local_validation = load(LOCAL_VALIDATION)
    final = watchdog.get("final", {})

    invariants = {
        "single_create_failed_at_api": (
            run.get("status") == "failed"
            and run.get("creation_attempted") is True
            and run.get("creation_http_status") == 500
            and run.get("creation_uncertain") is True
            and run.get("error") == "C23 pod creation failed HTTP 500"
        ),
        "no_pod_identity_or_upload": (
            run.get("pod_created") is False
            and run.get("uploaded_source_files") == 0
            and run.get("automatic_replacement_queued") is False
            and run.get("estimated_compute_cost_usd") is None
            and not (RUN_DIR / "POD-IDENTITY.json").exists()
            and not (RUN_DIR / "POD-RESOURCE-CHECK.json").exists()
            and not (RUN_DIR / "evidence.zip").exists()
            and not (RUN_DIR / "evidence").exists()
        ),
        "controller_cleanup_empty": (
            run.get("cleanup", {}).get("owned_pod_absent") is True
            and run.get("cleanup", {}).get("inventories") == {"v1": [], "v2": []}
            and run.get("cleanup", {}).get("attempts") == []
        ),
        "watchdog_horizon_reconciled": (
            watchdog.get("status") == "horizon_reconciled"
            and watchdog.get("errors") == []
            and final.get("owned_pod_absent") is True
            and final.get("inventories") == {"v1": [], "v2": []}
            and final.get("attempts") == []
        ),
        "zero_pod_preflight": (
            preflight.get("ready") is True
            and preflight.get("inventories") == {"v1": [], "v2": []}
            and preflight.get("c23_budget", {}).get("ready") is True
        ),
        "frozen_payload_not_changed": (
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
            and local_validation.get("status") == "pass"
            and authorization.get("one_create") is True
            and authorization.get("no_replacement") is True
        ),
    }
    failed = [name for name, passed in invariants.items() if not passed]
    if failed:
        raise SystemExit("C23 failed-attempt verification failed: " + ", ".join(failed))

    output = {
        "schema": "crse-runpod-c23-failed-attempt-verification/v1",
        "status": "pass",
        "scientific_replication_complete": False,
        "failure_stage": "pod_create_api",
        "creation_http_status": 500,
        "create_requests_this_authorization": 1,
        "pod_created": False,
        "files_uploaded": 0,
        "automatic_replacement_queued": False,
        "estimated_compute_cost_usd": None,
        "owned_pod_absent_verified": True,
        "final_inventories": {"v1": [], "v2": []},
        "invariants": invariants,
        "run_sha256": sha256(RUN_DIR / "RUN.json"),
        "watchdog_sha256": sha256(RUN_DIR / "WATCHDOG-RESULT.json"),
        "transport_freeze_sha256": sha256(RUN_DIR / "TRANSPORT-FREEZE.json"),
        "manifest_sha256": sha256(MANIFEST),
        "authorization_sha256": sha256(AUTHORIZATION),
    }
    OUTPUT.write_bytes(json.dumps(output, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
