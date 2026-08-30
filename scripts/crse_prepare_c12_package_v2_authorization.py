"""Record the user's exact C12 package-v2 Runpod authorization."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c12_linux_confirmation"
MANIFEST = HERE / "c12_linux_upload_manifest_v2.json"
PROTOCOL = HERE / "C12_SECOND_MACHINE_TIMING_PACKAGE_V2_PROTOCOL_2026_08_30.md"
LOCAL_VALIDATION = HERE / "C12_PACKAGE_V2_LOCAL_VALIDATION_20260830.json"
AUTHORIZATION = HERE / "RUNPOD_C12_LINUX_PACKAGE_V2_AUTHORIZED_2026_08_30.json"

EXPECTED_MANIFEST_SHA256 = "32f7d37c980d776c750b3001020244d5bd8f15cb19f7632cf40888fe56b08035"
EXPECTED_PROTOCOL_SHA256 = "b9527faff6602a1c275a5bf8be7ca2cfe5c59ba0d952b46efd862ec09449dc29"
EXPECTED_LOCAL_VALIDATION_SHA256 = "85bdc5c5d61574d012eb78fcbbe9d971f2da0fbef62c4d3abeddb9ce5a40725d"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    manifest = load(MANIFEST)
    validation = load(LOCAL_VALIDATION)
    if (sha(MANIFEST) != EXPECTED_MANIFEST_SHA256
            or sha(PROTOCOL) != EXPECTED_PROTOCOL_SHA256
            or sha(LOCAL_VALIDATION) != EXPECTED_LOCAL_VALIDATION_SHA256):
        raise SystemExit("refusing authorization record: frozen artifact hash changed")
    if (manifest.get("schema") != "crse-c12-linux-confirmation-upload-manifest/v2"
            or manifest.get("file_count") != 16
            or len(manifest.get("files", [])) != 16
            or manifest.get("bytes") != 368532
            or manifest.get("authorization_status") != "pending_payload_specific_authorization"):
        raise SystemExit("refusing authorization record: package scope changed")
    if (validation.get("status") != "pass"
            or validation.get("initial_file_count") != 16
            or validation.get("measurement_rows") != 2560
            or validation.get("semantic_mismatches") != 0
            or validation.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256):
        raise SystemExit("refusing authorization record: isolated validation is incomplete")

    record = {
        "schema": "crse-runpod-c12-linux-package-v2-authorization/v1",
        "authorized": True,
        "authorization_basis": (
            "User explicitly approved the frozen 16-file, 368,532-byte v2 manifest "
            "and v2 protocol on 2026-08-30."
        ),
        "user_total_ceiling_usd": 5.0,
        "controller_total_ceiling_usd": 0.05,
        "one_create": True,
        "no_replacement": True,
        "source_files": 16,
        "source_bytes": 368532,
        "cases": 40,
        "repetitions": 16,
        "methods": 4,
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
        "prior_attempts_reconciled": True,
        "local_isolated_validation": "pass",
        "proposal_sha256": EXPECTED_PROTOCOL_SHA256,
        "upload_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "local_validation_sha256": EXPECTED_LOCAL_VALIDATION_SHA256,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
    }
    with AUTHORIZATION.open("xb") as stream:
        stream.write(json.dumps(record, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps({
        "authorization": str(AUTHORIZATION.relative_to(ROOT)).replace("\\", "/"),
        "authorization_sha256": sha(AUTHORIZATION),
        "manifest_sha256": sha(MANIFEST),
        "protocol_sha256": sha(PROTOCOL),
        "local_validation_sha256": sha(LOCAL_VALIDATION),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
