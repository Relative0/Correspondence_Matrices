"""Freeze the C38 no-create reconciliation and transport-only retry request."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c38_linux_confirmation"
INITIAL_ATTEMPT = HERE / "runpod-c38-linux-execute-001"
INITIAL_RUN = INITIAL_ATTEMPT / "RUN.json"
INITIAL_REQUEST = HERE / "RUNPOD_C38_AUTHORIZATION_REQUEST_20260903.json"
INITIAL_AUTHORIZATION = HERE / "RUNPOD_C38_EXACT_PAYLOAD_AUTHORIZED_2026_09_03.json"
INITIAL_CONTROLLER = HERE / "runpod_c38_linux_controller.py"
MANIFEST = HERE / "c38_linux_upload_manifest.json"
PROTOCOL = HERE / "C38_C37_NATIVE_SECOND_MACHINE_PROTOCOL_2026_09_03.md"
VALIDATION = HERE / "C38_PACKAGE_LOCAL_VALIDATION_20260903.json"
CONTRACT = HERE / "c38_c37_native_replication_contract.json"
CONTROLLER = HERE / "runpod_c38_linux_controller_retry_001.py"
RECONCILIATION = HERE / "C38_INITIAL_NO_CREATE_RECONCILIATION_20260903.json"
REQUEST = HERE / "RUNPOD_C38_TRANSPORT_RETRY_001_REQUEST_20260903.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: Any) -> None:
    with path.open("xb") as stream:
        stream.write(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
            + b"\n"
        )


def main() -> int:
    run = load(INITIAL_RUN)
    watchdog_done = load(INITIAL_ATTEMPT / "watchdog-done.json")
    initial_request = load(INITIAL_REQUEST)
    initial_authorization = load(INITIAL_AUTHORIZATION)
    manifest = load(MANIFEST)
    validation = load(VALIDATION)
    cleanup = run.get("cleanup", {})
    forbidden_outputs = (
        INITIAL_ATTEMPT / "POD-IDENTITY.json",
        INITIAL_ATTEMPT / "POD-RESOURCE-CHECK.json",
        INITIAL_ATTEMPT / "evidence",
    )
    if (
        run.get("status") != "failed"
        or run.get("error") != "watchdog exited before create"
        or run.get("creation_attempted") is not False
        or run.get("creation_uncertain") is not False
        or run.get("pod_created") is not False
        or run.get("uploaded_source_files") != 0
        or run.get("estimated_compute_cost_usd") is not None
        or cleanup.get("owned_pod_absent") is not True
        or cleanup.get("attempts") != []
        or any(cleanup.get("inventories", {}).values())
        or watchdog_done.get("owned_pod_absent_verified") is not True
        or any(path.exists() for path in forbidden_outputs)
        or initial_request.get("authorization_granted") is not False
        or initial_authorization.get("authorized") is not True
        or initial_authorization.get("one_create") is not True
        or initial_authorization.get("no_replacement") is not True
        or initial_authorization.get("authorization_request_sha256")
        != sha256(INITIAL_REQUEST)
        or initial_authorization.get("controller_sha256") != sha256(INITIAL_CONTROLLER)
        or manifest.get("file_count") != 44
        or manifest.get("bytes") != 1_797_840
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != sha256(MANIFEST)
        or validation.get("timing_result_used_for_c38_decision") is not False
    ):
        raise ValueError("initial C38 attempt is not a reconciled pre-create failure")

    spec = importlib.util.spec_from_file_location("c38_retry_controller", CONTROLLER)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    state = controller.build_watchdog_state(1000.0, "012345abcdef")
    if (
        state.get("name") != "cm-c7-linux-012345abcdef"
        or state.get("cleanup_epoch") != 1000.0 + controller.shared.CLEANUP_AT
        or state.get("horizon_epoch") != 1000.0 + controller.shared.HORIZON
    ):
        raise ValueError("corrected C38 watchdog state contract failed local validation")

    recorded = datetime.now(timezone.utc).isoformat()
    reconciliation = {
        "schema": "crse-c38-initial-no-create-reconciliation/v1",
        "recorded_utc": recorded,
        "status": "reconciled_no_create",
        "failure_boundary": "local_watchdog_state_validation_before_create_request",
        "failure_reason": (
            "controller ownership prefix did not match inherited watchdog namespace"
        ),
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
        "retry_requires_new_exact_authorization": True,
        "initial_run_sha256": sha256(INITIAL_RUN),
        "initial_watchdog_done_sha256": sha256(
            INITIAL_ATTEMPT / "watchdog-done.json"
        ),
        "initial_authorization_sha256": sha256(INITIAL_AUTHORIZATION),
        "initial_authorization_request_sha256": sha256(INITIAL_REQUEST),
        "initial_controller_sha256": sha256(INITIAL_CONTROLLER),
        "upload_manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "local_validation_sha256": sha256(VALIDATION),
        "replication_contract_sha256": sha256(CONTRACT),
        "source_files": 44,
        "source_bytes": 1_797_840,
    }
    write_new(RECONCILIATION, reconciliation)

    request = {
        key: value
        for key, value in initial_authorization.items()
        if key
        not in {
            "schema",
            "authorized",
            "recorded_utc",
            "authorization_request_sha256",
            "controller_sha256",
            "transport_sources",
            "user_confirmation_reference",
        }
    }
    request.update(
        {
            "schema": "crse-runpod-c38-transport-retry-001-authorization-request/v1",
            "recorded_utc": recorded,
            "authorization_granted": False,
            "resource_writes": 0,
            "requested_effect": (
                "Use the still-unused C38 one-create allowance after a reconciled local "
                "pre-create watchdog failure; upload the unchanged frozen 44-file package "
                "to one Secure CPU Pod, rebuild with Linux cc/GCC, run the unchanged C37 "
                "schedule and both verifiers, retrieve at most 24 MiB, delete the owned "
                "Pod, and reconcile both RunPod inventories."
            ),
            "transport_change": (
                "use the inherited watchdog's historical cm-c7-linux ownership namespace"
            ),
            "scientific_payload_changed": False,
            "authorized_create_consumed_before_retry": False,
            "replacement_attempt": False,
            "initial_no_create_reconciliation_sha256": sha256(RECONCILIATION),
            "initial_authorization_sha256": sha256(INITIAL_AUTHORIZATION),
            "upload_manifest_sha256": sha256(MANIFEST),
            "protocol_sha256": sha256(PROTOCOL),
            "local_validation_sha256": sha256(VALIDATION),
            "replication_contract_sha256": sha256(CONTRACT),
            "controller_sha256": sha256(CONTROLLER),
            "transport_sources": controller.transport_source_identities(),
        }
    )
    write_new(REQUEST, request)
    print(
        json.dumps(
            {
                "status": "transport_retry_request_frozen",
                "authorization_granted": False,
                "reconciliation_sha256": sha256(RECONCILIATION),
                "request_sha256": sha256(REQUEST),
                "controller_sha256": sha256(CONTROLLER),
                "source_files": request["source_files"],
                "source_bytes": request["source_bytes"],
                "resource_writes": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
