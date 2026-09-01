"""Record an exact user authorization for the already frozen C31 package."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c31_linux_confirmation"
REQUEST = HERE / "RUNPOD_C31_AUTHORIZATION_REQUEST_20260901.json"
MANIFEST = HERE / "c31_linux_upload_manifest.json"
PROTOCOL = HERE / "C31_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_09_01.md"
VALIDATION = HERE / "C31_PACKAGE_LOCAL_VALIDATION_20260901.json"
CONTRACT = ROOT / "docs/recognition/c31_prepared_policy_replication_contract.json"
CONTROLLER = HERE / "runpod_c31_linux_controller.py"
OUTPUT = HERE / "RUNPOD_C31_EXACT_PAYLOAD_AUTHORIZED_2026_09_01.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C31 authorization")
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    if (
        request.get("schema")
        != "crse-runpod-c31-exact-payload-authorization-request/v1"
        or request.get("authorization_granted") is not False
        or request.get("resource_writes") != 0
        or request.get("source_files") != 71
        or request.get("source_bytes") != 1153868
        or request.get("one_create") is not True
        or request.get("no_replacement") is not True
        or request.get("upload_manifest_sha256") != sha256(MANIFEST)
        or request.get("protocol_sha256") != sha256(PROTOCOL)
        or request.get("local_validation_sha256") != sha256(VALIDATION)
        or request.get("replication_contract_sha256") != sha256(CONTRACT)
        or request.get("controller_sha256") != sha256(CONTROLLER)
    ):
        raise ValueError("C31 authorization request or frozen artifact changed")
    authorization = {
        key: value for key, value in request.items()
        if key not in {"schema", "recorded_utc", "authorization_granted", "resource_writes"}
    }
    authorization.update({
        "schema": "crse-runpod-c31-exact-payload-authorization/v1",
        "authorized": True,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "authorization_request_sha256": sha256(REQUEST),
    })
    OUTPUT.write_bytes(
        json.dumps(authorization, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
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
