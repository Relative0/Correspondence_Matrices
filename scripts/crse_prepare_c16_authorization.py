"""Record the owner's standing $5 authorization against the frozen C16 payload."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/recognition/c16_linux_confirmation"
MANIFEST = OUT / "c16_linux_upload_manifest.json"
PROTOCOL = OUT / "C16_SECOND_MACHINE_TIMING_PROTOCOL_2026_08_30.md"
VALIDATION = OUT / "C16_PACKAGE_LOCAL_VALIDATION_20260830.json"
AUTHORIZATION = OUT / "RUNPOD_C16_LINUX_AUTHORIZED_2026_08_30.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if AUTHORIZATION.exists():
        raise SystemExit("refusing to overwrite C16 authorization record")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if (manifest.get("file_count") != 18 or manifest.get("bytes") != 423661
            or validation.get("status") != "pass"
            or validation.get("manifest_sha256") != sha(MANIFEST)):
        raise SystemExit("C16 package is not in its authorized validated state")
    value = {
        "schema": "crse-runpod-c16-linux-authorization/v1",
        "authorized": True,
        "authorization_basis": "Owner authorized Runpod work up to $5 without repeat approval, including retries, on 2026-08-30.",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "user_total_ceiling_usd": 5.0,
        "controller_total_ceiling_usd": 0.05,
        "one_create": True,
        "no_replacement": True,
        "source_files": 18,
        "source_bytes": manifest["bytes"],
        "cases": 40,
        "repetitions": 3,
        "methods": 3,
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
        "local_isolated_validation": "pass",
        "upload_manifest_sha256": sha(MANIFEST),
        "proposal_sha256": sha(PROTOCOL),
        "local_validation_sha256": sha(VALIDATION),
        "credentials_recorded_or_uploaded": False,
    }
    AUTHORIZATION.write_bytes(json.dumps(value, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps({"authorization": str(AUTHORIZATION.relative_to(ROOT)).replace("\\", "/"),
                      "manifest_sha256": value["upload_manifest_sha256"],
                      "controller_cap_usd": value["controller_total_ceiling_usd"]}, sort_keys=True))


if __name__ == "__main__":
    main()
