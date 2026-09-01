"""Bind the exact retry-002 authorization to the unchanged C23 package."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c23_linux_confirmation"
MANIFEST = HERE / "c23_linux_upload_manifest.json"
PROTOCOL = HERE / "C23_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md"
VALIDATION = HERE / "C23_PACKAGE_LOCAL_VALIDATION_20260831.json"
PRIOR_FAILURE = HERE / "RUNPOD_C23_FAILED_ATTEMPT_VERIFICATION_20260831.json"
OUTPUT = HERE / "RUNPOD_C23_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_08_31.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C23 authorization record")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    prior_failure = json.loads(PRIOR_FAILURE.read_text(encoding="utf-8"))
    if (manifest.get("file_count") != 52 or manifest.get("bytes") != 903745
            or validation.get("status") != "pass"
            or validation.get("manifest_sha256") != sha256(MANIFEST)
            or prior_failure.get("status") != "pass"
            or prior_failure.get("scientific_replication_complete") is not False
            or prior_failure.get("create_requests_this_authorization") != 1
            or prior_failure.get("pod_created") is not False
            or prior_failure.get("files_uploaded") != 0
            or prior_failure.get("owned_pod_absent_verified") is not True
            or prior_failure.get("final_inventories") != {"v1": [], "v2": []}):
        raise ValueError("C23 package is not frozen and locally validated")
    record = {
        "schema": "crse-runpod-c23-retry-002-exact-payload-authorization/v1",
        "authorized": True,
        "authorization_basis": (
            "current user approval of exactly one additional create after the reconciled HTTP 500 failure"),
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "retry_attempt": 2,
        "additional_create_requests": 1,
        "prior_failed_attempt_status": "verified_reconciled",
        "prior_failed_attempt_verification_sha256": sha256(PRIOR_FAILURE),
        "user_total_ceiling_usd": 5.0,
        "controller_total_ceiling_usd": 0.05,
        "one_create": True,
        "no_replacement": True,
        "source_files": manifest["file_count"],
        "source_bytes": manifest["bytes"],
        "cases": 48,
        "rounds": 5,
        "methods": 7,
        "measurement_rows": 1680,
        "memory_rows": 56,
        "https_ports": ["8080/http"],
        "vcpu_count": 2,
        "minimum_ram_gb": 4,
        "container_disk_gb": 12,
        "pod_volume_gb": 0,
        "network_volume": False,
        "cleanup_seconds": 600,
        "reconciliation_seconds": 720,
        "rate_cap_usd_per_hour": 0.25,
        "total_cost_cap_usd": 0.05,
        "same_pod_payload_attempt_limit": 6,
        "health_checks_before_upload": 2,
        "result_cap_bytes": 16 << 20,
        "local_isolated_validation": "pass",
        "local_validation_pythonpath_injected": False,
        "upload_manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "local_validation_sha256": sha256(VALIDATION),
        "credentials_recorded_or_uploaded": False,
    }
    OUTPUT.write_bytes(json.dumps(record, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps({"authorized": True, "retry_attempt": 2,
                      "source_files": record["source_files"],
                      "source_bytes": record["source_bytes"],
                      "controller_total_ceiling_usd": 0.05,
                      "authorization_sha256": sha256(OUTPUT)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
