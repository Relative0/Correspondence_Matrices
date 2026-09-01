"""Bind the user's exact C31 approval to the corrected local transport controller."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c31_linux_confirmation"
REQUEST = HERE / "RUNPOD_C31_TRANSPORT_RETRY_001_REQUEST_20260901.json"
RECONCILIATION = HERE / "C31_INITIAL_NO_CREATE_RECONCILIATION_20260901.json"
MANIFEST = HERE / "c31_linux_upload_manifest.json"
PROTOCOL = HERE / "C31_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_09_01.md"
VALIDATION = HERE / "C31_PACKAGE_LOCAL_VALIDATION_20260901.json"
CONTRACT = ROOT / "docs/recognition/c31_prepared_policy_replication_contract.json"
CONTROLLER = HERE / "runpod_c31_linux_controller_retry_001.py"
OUTPUT = HERE / "RUNPOD_C31_TRANSPORT_RETRY_001_AUTHORIZED_2026_09_01.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C31 transport retry authorization")
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    required = {
        "authorization_granted": False,
        "resource_writes": 0,
        "one_create": True,
        "no_replacement": True,
        "source_files": 71,
        "source_bytes": 1153868,
        "scientific_payload_changed": False,
        "authorized_create_consumed_before_retry": False,
        "replacement_attempt": False,
    }
    if (
        request.get("schema")
        != "crse-runpod-c31-transport-retry-001-authorization-request/v1"
        or any(request.get(key) != value for key, value in required.items())
        or request.get("initial_no_create_reconciliation_sha256") != sha256(RECONCILIATION)
        or request.get("upload_manifest_sha256") != sha256(MANIFEST)
        or request.get("protocol_sha256") != sha256(PROTOCOL)
        or request.get("local_validation_sha256") != sha256(VALIDATION)
        or request.get("replication_contract_sha256") != sha256(CONTRACT)
        or request.get("controller_sha256") != sha256(CONTROLLER)
    ):
        raise ValueError("C31 retry request, reconciliation, or frozen artifact changed")
    authorization = {
        key: value for key, value in request.items()
        if key not in {"schema", "recorded_utc", "authorization_granted", "resource_writes"}
    }
    authorization.update({
        "schema": "crse-runpod-c31-transport-retry-001-authorization/v1",
        "authorized": True,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "authorization_basis": (
            "User explicitly approved the exact frozen C31 package and exactly one pod; "
            "the reconciled initial invocation made no create request, so that create remains unused."
        ),
        "authorization_request_sha256": sha256(REQUEST),
    })
    OUTPUT.write_bytes(json.dumps(authorization, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps({
        "status": "authorized",
        "authorization_sha256": sha256(OUTPUT),
        "authorization_request_sha256": sha256(REQUEST),
        "source_files": authorization["source_files"],
        "source_bytes": authorization["source_bytes"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
