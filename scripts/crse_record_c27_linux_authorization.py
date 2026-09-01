"""Bind the user's exact C27 RunPod approval to the frozen package."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c27_linux_confirmation"
MANIFEST = HERE / "c27_linux_upload_manifest.json"
PROTOCOL = HERE / "C27_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md"
VALIDATION = HERE / "C27_PACKAGE_LOCAL_VALIDATION_20260831.json"
OUTPUT = HERE / "RUNPOD_C27_EXACT_PAYLOAD_AUTHORIZED_2026_08_31.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 exact authorization")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if (
        manifest.get("file_count") != 63 or manifest.get("bytes") != 1078671
        or manifest.get("authorization_status")
        != "upload_not_authorized_exact_approval_pending"
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != sha256(MANIFEST)
    ):
        raise ValueError("C27 frozen package changed before authorization binding")
    record = {
        "schema": "crse-runpod-c27-exact-payload-authorization/v1",
        "authorized": True,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "user_approval_message": "I approve",
        "create_requests": 1,
        "one_create": True,
        "no_replacement": True,
        "controller_total_ceiling_usd": 0.05,
        "source_files": 63,
        "source_bytes": 1078671,
        "cases": 48,
        "rounds": 5,
        "methods": 6,
        "measurement_batches": 720,
        "timed_queries": 7560,
        "memory_batches": 24,
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
        "isolated_timing_gate": validation.get("support_aware_confirmation_gate"),
        "timing_gate_failure_is_valid_evidence": True,
        "training": False,
        "production_write": False,
        "production_promotion": False,
        "upload_manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "local_validation_sha256": sha256(VALIDATION),
        "credentials_recorded_or_uploaded": False,
    }
    OUTPUT.write_bytes(json.dumps(
        record, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "authorized": True, "create_requests": 1,
        "source_files": 63, "source_bytes": 1078671,
        "authorization_sha256": sha256(OUTPUT),
        "credentials_recorded_or_uploaded": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
