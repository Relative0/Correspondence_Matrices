"""Prepare, without granting, the exact C27 RunPod retry-003 request."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C27 = ROOT / "docs/recognition/c27_linux_confirmation"
DOCKER = ROOT / "docs/recognition/c27_independent_docker_confirmation"
MANIFEST = C27 / "c27_linux_upload_manifest.json"
PROTOCOL = C27 / "C27_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md"
LOCAL_VALIDATION = C27 / "C27_PACKAGE_LOCAL_VALIDATION_20260831.json"
PRIOR = C27 / "RUNPOD_C27_RETRY_002_HTTP500_RECONCILIATION_20260901.json"
READINESS = C27 / "RUNPOD_C27_RETRY_003_READINESS_20260901.json"
TRANSPORT_TEST = ROOT / "tests/test_c27_runpod_transport.py"
DOCKER_REPEATABILITY = C27 / "C27_DOCKER_LINUX_REPEATABILITY_VERIFICATION_20260901.json"
PORTABLE_VALIDATION = DOCKER / "C27_INDEPENDENT_DOCKER_PACKAGE_LOCAL_VALIDATION_20260901.json"
OUTPUT = C27 / "RUNPOD_C27_RETRY_003_AUTHORIZATION_REQUEST_20260901.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 retry-003 request")
    manifest = load(MANIFEST)
    validation = load(LOCAL_VALIDATION)
    prior = load(PRIOR)
    readiness = load(READINESS)
    repeatability = load(DOCKER_REPEATABILITY)
    portable = load(PORTABLE_VALIDATION)
    if (
        manifest.get("file_count") != 63
        or manifest.get("bytes") != 1078671
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != sha256(MANIFEST)
        or prior.get("status") != "verified_reconciled"
        or prior.get("authorization_consumed") is not True
        or prior.get("owned_pod_absent") is not True
        or readiness.get("status") != "ready_read_only"
        or readiness.get("preferred_cpu_flavor") != "cpu5c"
        or readiness.get("preferred_availability") != "HIGH"
        or readiness.get("preferred_eligible") is not True
        or readiness.get("resource_writes") != 0
        or repeatability.get("status") != "verified"
        or repeatability.get("timing_gate_passes") != 3
        or repeatability.get("semantic_or_artifact_mismatches") != 0
        or portable.get("status") != "pass"
        or portable.get("second_machine_replication") is not False
    ):
        raise ValueError("C27 retry-003 request prerequisites mismatch")
    exact_text = (
        "Approve exactly one additional RunPod create request for C27 retry-003 using the "
        "unchanged frozen 63-file, 1,078,671-byte package and C27 protocol, restricted to the "
        "currently eligible Secure cpu5c flavor at no more than $0.07/hour, with 2 vCPU, at "
        "least 4 GB RAM, the pinned Python 3.13.15 image, 12 GB ephemeral disk, zero persistent "
        "or network volume, no replacement, a $0.05 controller cost ceiling within the "
        "authorized $5, bounded 16 MiB retrieval, ten-minute cleanup, twelve-minute "
        "reconciliation, six same-pod payload retries, and no training or production write."
    )
    request = {
        "schema": "crse-runpod-c27-retry-003-authorization-request/v1",
        "status": "awaiting_exact_user_approval",
        "authorization_granted": False,
        "retry_attempt": 3,
        "requested_additional_create_requests": 1,
        "one_create": True,
        "no_replacement": True,
        "package_unchanged": True,
        "source_files": 63,
        "source_bytes": 1078671,
        "manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "local_validation_sha256": sha256(LOCAL_VALIDATION),
        "prior_reconciliation_sha256": sha256(PRIOR),
        "readiness_sha256": sha256(READINESS),
        "transport_regression_test_sha256": sha256(TRANSPORT_TEST),
        "docker_repeatability_verification_sha256": sha256(DOCKER_REPEATABILITY),
        "portable_package_validation_sha256": sha256(PORTABLE_VALIDATION),
        "required_cpu_flavor": "cpu5c",
        "fallback_cpu_flavors": [],
        "readiness_at_request": "HIGH",
        "quoted_rate_usd_per_hour": 0.07,
        "rate_cap_usd_per_hour": 0.07,
        "vcpu_count": 2,
        "minimum_ram_gb": 4,
        "image": manifest["runtime"]["image"],
        "container_disk_gb": 12,
        "pod_volume_gb": 0,
        "network_volume": False,
        "https_ports": ["8080/http"],
        "precreate_wait_seconds": 900,
        "cleanup_seconds": 600,
        "reconciliation_seconds": 720,
        "same_pod_payload_attempt_limit": 6,
        "health_checks_before_upload": 2,
        "result_cap_bytes": 16 << 20,
        "user_total_ceiling_usd": 5.0,
        "controller_total_ceiling_usd": 0.05,
        "total_cost_cap_usd": 0.05,
        "timing_gate_failure_is_valid_evidence": True,
        "training": False,
        "production_write": False,
        "production_promotion": False,
        "credentials_recorded_or_uploaded": False,
        "exact_approval_text": exact_text,
    }
    OUTPUT.write_bytes(json.dumps(
        request, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "status": request["status"],
        "requested_additional_create_requests": 1,
        "required_cpu_flavor": "cpu5c",
        "rate_cap_usd_per_hour": 0.07,
        "source_files": 63,
        "source_bytes": 1078671,
        "request_sha256": sha256(OUTPUT),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
