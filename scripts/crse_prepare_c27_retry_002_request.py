"""Prepare, but do not grant, the exact C27 retry-002 authorization request."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c27_linux_confirmation"
MANIFEST = HERE / "c27_linux_upload_manifest.json"
PROTOCOL = HERE / "C27_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md"
VALIDATION = HERE / "C27_PACKAGE_LOCAL_VALIDATION_20260831.json"
RECONCILIATION = HERE / "RUNPOD_C27_PROXY_404_RECONCILIATION_20260901.json"
TEST = ROOT / "tests/test_c27_runpod_transport.py"
OUTPUT = HERE / "RUNPOD_C27_RETRY_002_AUTHORIZATION_REQUEST_20260901.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 retry authorization request")
    manifest = load(MANIFEST)
    validation = load(VALIDATION)
    reconciliation = load(RECONCILIATION)
    if (
        manifest.get("file_count") != 63
        or manifest.get("bytes") != 1078671
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != sha256(MANIFEST)
        or reconciliation.get("status") != "verified_reconciled"
        or reconciliation.get("create_requests") != 1
        or reconciliation.get("authorization_consumed") is not True
        or reconciliation.get("replacement_authorized") is not False
        or reconciliation.get("owned_pod_absent") is not True
        or reconciliation.get("source_files_uploaded") != 0
    ):
        raise ValueError("C27 retry request prerequisites do not match")
    exact_text = (
        "Approve exactly one additional RunPod create attempt using the unchanged frozen "
        "63-file, 1,078,671-byte C27 package and C27 protocol, after the independently "
        "reconciled proxy-404 failure. Keep the same Secure CPU, no-replacement, pinned "
        "Python 3.13.15, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, zero persistent "
        "volumes, $0.25/hour rate ceiling, $0.05 controller cost ceiling within the "
        "authorized $5, bounded 16 MiB retrieval, ten-minute cleanup, twelve-minute "
        "reconciliation, and no-training/no-production-write limits."
    )
    request = {
        "schema": "crse-runpod-c27-retry-002-authorization-request/v1",
        "status": "awaiting_exact_user_approval",
        "authorization_granted": False,
        "requested_additional_create_requests": 1,
        "retry_attempt": 2,
        "one_create": True,
        "no_replacement": True,
        "source_files": 63,
        "source_bytes": 1078671,
        "package_unchanged": True,
        "manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "local_validation_sha256": sha256(VALIDATION),
        "prior_reconciliation_sha256": sha256(RECONCILIATION),
        "transport_regression_test_sha256": sha256(TEST),
        "transport_regression_test": "pass",
        "prior_failure": "transient_proxy_http_404_before_payload_acceptance",
        "prior_owned_pod_absent": True,
        "prior_source_files_uploaded": 0,
        "https_ports": ["8080/http"],
        "vcpu_count": 2,
        "minimum_ram_gb": 4,
        "container_disk_gb": 12,
        "pod_volume_gb": 0,
        "network_volume": False,
        "cleanup_seconds": 600,
        "reconciliation_seconds": 720,
        "rate_cap_usd_per_hour": 0.25,
        "controller_total_ceiling_usd": 0.05,
        "result_cap_bytes": 16 << 20,
        "same_pod_payload_attempt_limit": 6,
        "training": False,
        "production_write": False,
        "credentials_recorded_or_uploaded": False,
        "exact_approval_text": exact_text,
    }
    OUTPUT.write_bytes(json.dumps(
        request, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "status": request["status"],
        "requested_additional_create_requests": 1,
        "source_files": 63,
        "source_bytes": 1078671,
        "request_sha256": sha256(OUTPUT),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
