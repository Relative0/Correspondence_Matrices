"""Freeze the no-create C31 reconciliation and its transport-only retry request."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c31_linux_confirmation"
INITIAL_RUN = HERE / "runpod-c31-linux-execute-001/RUN.json"
INITIAL_REQUEST = HERE / "RUNPOD_C31_AUTHORIZATION_REQUEST_20260901.json"
INITIAL_AUTHORIZATION = HERE / "RUNPOD_C31_EXACT_PAYLOAD_AUTHORIZED_2026_09_01.json"
MANIFEST = HERE / "c31_linux_upload_manifest.json"
PROTOCOL = HERE / "C31_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_09_01.md"
VALIDATION = HERE / "C31_PACKAGE_LOCAL_VALIDATION_20260901.json"
CONTRACT = ROOT / "docs/recognition/c31_prepared_policy_replication_contract.json"
CONTROLLER = HERE / "runpod_c31_linux_controller_retry_001.py"
RECONCILIATION = HERE / "C31_INITIAL_NO_CREATE_RECONCILIATION_20260901.json"
REQUEST = HERE / "RUNPOD_C31_TRANSPORT_RETRY_001_REQUEST_20260901.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, value: dict) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite {path.name}")
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True).encode() + b"\n")


def main() -> int:
    run = json.loads(INITIAL_RUN.read_text(encoding="utf-8"))
    initial_authorization = json.loads(INITIAL_AUTHORIZATION.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    cleanup = run.get("cleanup", {})
    if (
        run.get("status") != "failed"
        or run.get("error") != "watchdog exited before create"
        or run.get("creation_attempted") is not False
        or run.get("creation_uncertain") is not False
        or run.get("pod_created") is not False
        or run.get("uploaded_source_files") != 0
        or run.get("estimated_compute_cost_usd") is not None
        or cleanup.get("owned_pod_absent") is not True
        or any(cleanup.get("inventories", {}).values())
        or initial_authorization.get("authorized") is not True
        or initial_authorization.get("one_create") is not True
        or initial_authorization.get("no_replacement") is not True
        or manifest.get("file_count") != 71
        or manifest.get("bytes") != 1153868
        or validation.get("status") != "pass"
    ):
        raise ValueError("initial C31 attempt is not a reconciled pre-create failure")

    recorded = datetime.now(timezone.utc).isoformat()
    reconciliation = {
        "schema": "crse-c31-initial-no-create-reconciliation/v1",
        "recorded_utc": recorded,
        "status": "reconciled_no_create",
        "failure_boundary": "local_watchdog_state_validation_before_create_request",
        "failure_reason": "controller ownership prefix did not match inherited watchdog namespace",
        "creation_attempted": False,
        "creation_uncertain": False,
        "pod_created": False,
        "uploaded_source_files": 0,
        "estimated_compute_cost_usd": None,
        "owned_pod_absent": True,
        "v1_inventory": [],
        "v2_inventory": [],
        "authorized_create_consumed": False,
        "replacement_attempt": False,
        "initial_run_sha256": sha256(INITIAL_RUN),
        "initial_authorization_sha256": sha256(INITIAL_AUTHORIZATION),
        "initial_authorization_request_sha256": sha256(INITIAL_REQUEST),
        "initial_controller_sha256": initial_authorization["controller_sha256"],
        "upload_manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "source_files": 71,
        "source_bytes": 1153868,
    }
    write_new(RECONCILIATION, reconciliation)

    request = {
        key: value for key, value in initial_authorization.items()
        if key not in {"schema", "authorized", "recorded_utc", "authorization_request_sha256",
                       "controller_sha256"}
    }
    request.update({
        "schema": "crse-runpod-c31-transport-retry-001-authorization-request/v1",
        "recorded_utc": recorded,
        "authorization_granted": False,
        "resource_writes": 0,
        "requested_effect": (
            "Use the still-unused exact C31 one-create authorization after a reconciled "
            "local pre-create watchdog failure; upload the unchanged frozen package to one "
            "Secure CPU pod, retrieve bounded evidence, and delete the owned pod."
        ),
        "transport_change": "use the inherited watchdog's historical cm-c7-linux ownership namespace",
        "scientific_payload_changed": False,
        "authorized_create_consumed_before_retry": False,
        "replacement_attempt": False,
        "initial_no_create_reconciliation_sha256": sha256(RECONCILIATION),
        "upload_manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "local_validation_sha256": sha256(VALIDATION),
        "replication_contract_sha256": sha256(CONTRACT),
        "controller_sha256": sha256(CONTROLLER),
    })
    write_new(REQUEST, request)
    print(json.dumps({
        "status": "transport_retry_request_frozen",
        "reconciliation_sha256": sha256(RECONCILIATION),
        "request_sha256": sha256(REQUEST),
        "source_files": request["source_files"],
        "source_bytes": request["source_bytes"],
        "resource_writes": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
