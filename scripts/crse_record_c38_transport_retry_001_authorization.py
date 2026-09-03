"""Bind a user's exact approval to the corrected C38 transport controller."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c38_linux_confirmation"
REQUEST = HERE / "RUNPOD_C38_TRANSPORT_RETRY_001_REQUEST_20260903.json"
RECONCILIATION = HERE / "C38_INITIAL_NO_CREATE_RECONCILIATION_20260903.json"
MANIFEST = HERE / "c38_linux_upload_manifest.json"
PROTOCOL = HERE / "C38_C37_NATIVE_SECOND_MACHINE_PROTOCOL_2026_09_03.md"
VALIDATION = HERE / "C38_PACKAGE_LOCAL_VALIDATION_20260903.json"
CONTRACT = HERE / "c38_c37_native_replication_contract.json"
CONTROLLER = HERE / "runpod_c38_linux_controller_retry_001.py"
OUTPUT = HERE / "RUNPOD_C38_TRANSPORT_RETRY_001_AUTHORIZED_2026_09_03.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirmation-reference",
        required=True,
        help="Short traceability note identifying the user's exact approval message.",
    )
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C38 transport retry authorization")
    request = load(REQUEST)
    required = {
        "authorization_granted": False,
        "resource_writes": 0,
        "one_create": True,
        "no_replacement": True,
        "source_files": 44,
        "source_bytes": 1_797_840,
        "scientific_payload_changed": False,
        "authorized_create_consumed_before_retry": False,
        "replacement_attempt": False,
        "controller_total_ceiling_usd": 0.05,
        "total_cost_cap_usd": 0.05,
    }
    if (
        request.get("schema")
        != "crse-runpod-c38-transport-retry-001-authorization-request/v1"
        or any(request.get(key) != value for key, value in required.items())
        or request.get("initial_no_create_reconciliation_sha256")
        != sha256(RECONCILIATION)
        or request.get("upload_manifest_sha256") != sha256(MANIFEST)
        or request.get("protocol_sha256") != sha256(PROTOCOL)
        or request.get("local_validation_sha256") != sha256(VALIDATION)
        or request.get("replication_contract_sha256") != sha256(CONTRACT)
        or request.get("controller_sha256") != sha256(CONTROLLER)
    ):
        raise ValueError("C38 retry request, reconciliation, or frozen artifact changed")
    authorization = {
        key: value
        for key, value in request.items()
        if key not in {"schema", "recorded_utc", "authorization_granted", "resource_writes"}
    }
    authorization.update(
        {
            "schema": "crse-runpod-c38-transport-retry-001-authorization/v1",
            "authorized": True,
            "recorded_utc": datetime.now(timezone.utc).isoformat(),
            "authorization_basis": (
                "User explicitly approved this exact corrected C38 transport request; "
                "the reconciled initial invocation made no pod create request."
            ),
            "authorization_request_sha256": sha256(REQUEST),
            "user_confirmation_reference": args.confirmation_reference,
        }
    )
    with OUTPUT.open("xb") as stream:
        stream.write(
            json.dumps(authorization, indent=2, sort_keys=True, allow_nan=False).encode(
                "utf-8"
            )
            + b"\n"
        )
    print(
        json.dumps(
            {
                "status": "authorized",
                "authorization_sha256": sha256(OUTPUT),
                "authorization_request_sha256": sha256(REQUEST),
                "source_files": authorization["source_files"],
                "source_bytes": authorization["source_bytes"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
