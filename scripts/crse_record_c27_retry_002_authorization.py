"""Bind the user's exact C27 retry-002 approval to the unchanged frozen package."""
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
RECONCILIATION = HERE / "RUNPOD_C27_PROXY_404_RECONCILIATION_20260901.json"
REQUEST = HERE / "RUNPOD_C27_RETRY_002_AUTHORIZATION_REQUEST_20260901.json"
TEST = ROOT / "tests/test_c27_runpod_transport.py"
OUTPUT = HERE / "RUNPOD_C27_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_09_01.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 retry-002 authorization")
    manifest = load(MANIFEST)
    validation = load(VALIDATION)
    reconciliation = load(RECONCILIATION)
    request = load(REQUEST)
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
        or request.get("status") != "awaiting_exact_user_approval"
        or request.get("authorization_granted") is not False
        or request.get("requested_additional_create_requests") != 1
        or request.get("manifest_sha256") != sha256(MANIFEST)
        or request.get("prior_reconciliation_sha256") != sha256(RECONCILIATION)
        or request.get("transport_regression_test") != "pass"
        or request.get("transport_regression_test_sha256") != sha256(TEST)
    ):
        raise ValueError("C27 retry-002 authorization prerequisites do not match")
    record = {
        "schema": "crse-runpod-c27-retry-002-exact-payload-authorization/v1",
        "authorized": True,
        "authorization_basis": (
            "current user message approving the C27 retry-002 authorization request"),
        "user_approval_message": "I approve the C27 retry-002 authorization request.",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "retry_attempt": 2,
        "additional_create_requests": 1,
        "create_requests": 1,
        "prior_create_requests": 1,
        "one_create": True,
        "no_replacement": True,
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
        "user_total_ceiling_usd": 5.0,
        "controller_total_ceiling_usd": 0.05,
        "total_cost_cap_usd": 0.05,
        "same_pod_payload_attempt_limit": 6,
        "health_checks_before_upload": 2,
        "result_cap_bytes": 16 << 20,
        "local_isolated_validation": "pass",
        "local_validation_pythonpath_injected": False,
        "isolated_timing_gate": False,
        "timing_gate_failure_is_valid_evidence": True,
        "training": False,
        "production_write": False,
        "production_promotion": False,
        "upload_manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "local_validation_sha256": sha256(VALIDATION),
        "prior_reconciliation_sha256": sha256(RECONCILIATION),
        "authorization_request_sha256": sha256(REQUEST),
        "transport_regression_test_sha256": sha256(TEST),
        "credentials_recorded_or_uploaded": False,
    }
    OUTPUT.write_bytes(json.dumps(
        record, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "authorized": True,
        "retry_attempt": 2,
        "additional_create_requests": 1,
        "source_files": 63,
        "source_bytes": 1078671,
        "controller_total_ceiling_usd": 0.05,
        "authorization_sha256": sha256(OUTPUT),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
