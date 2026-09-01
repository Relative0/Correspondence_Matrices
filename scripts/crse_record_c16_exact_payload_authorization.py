"""Bind the owner's exact C16 RunPod approval to the frozen payload hashes."""
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
AUTHORIZATION = OUT / "RUNPOD_C16_EXACT_PAYLOAD_AUTHORIZED_2026_08_31.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if AUTHORIZATION.exists():
        raise SystemExit("refusing to overwrite exact C16 authorization record")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if (manifest.get("file_count") != 18 or manifest.get("bytes") != 423661
            or validation.get("status") != "pass"
            or validation.get("manifest_sha256") != sha(MANIFEST)):
        raise SystemExit("frozen C16 package no longer matches the approved payload")
    value = {
        "schema": "crse-runpod-c16-exact-payload-authorization/v2",
        "authorized": True,
        "authorization_basis": (
            "Owner explicitly approved the frozen 18-file, 423661-byte C16 manifest and "
            "C16 protocol for RunPod upload on 2026-08-31."
        ),
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "user_total_ceiling_usd": 5.0,
        "controller_total_ceiling_usd": 0.05,
        "one_create": True,
        "no_replacement": True,
        "source_files": 18,
        "source_bytes": 423661,
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
    print(json.dumps({
        "authorization": str(AUTHORIZATION.relative_to(ROOT)).replace("\\", "/"),
        "manifest_sha256": value["upload_manifest_sha256"],
        "protocol_sha256": value["proposal_sha256"],
        "controller_cap_usd": value["controller_total_ceiling_usd"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
