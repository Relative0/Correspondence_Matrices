"""Bind the user's exact C27 retry-003 approval to the unchanged package."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C27 = ROOT / "docs/recognition/c27_linux_confirmation"
DOCKER = ROOT / "docs/recognition/c27_independent_docker_confirmation"
MANIFEST = C27 / "c27_linux_upload_manifest.json"
PROTOCOL = C27 / "C27_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md"
VALIDATION = C27 / "C27_PACKAGE_LOCAL_VALIDATION_20260831.json"
PRIOR = C27 / "RUNPOD_C27_RETRY_002_HTTP500_RECONCILIATION_20260901.json"
READINESS = C27 / "RUNPOD_C27_RETRY_003_READINESS_20260901.json"
REQUEST = C27 / "RUNPOD_C27_RETRY_003_AUTHORIZATION_REQUEST_20260901.json"
TRANSPORT_TEST = ROOT / "tests/test_c27_runpod_transport.py"
DOCKER_REPEATABILITY = C27 / "C27_DOCKER_LINUX_REPEATABILITY_VERIFICATION_20260901.json"
PORTABLE_VALIDATION = DOCKER / "C27_INDEPENDENT_DOCKER_PACKAGE_LOCAL_VALIDATION_20260901.json"
OUTPUT = C27 / "RUNPOD_C27_RETRY_003_EXACT_PAYLOAD_AUTHORIZED_2026_09_01.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 retry-003 authorization")
    manifest = load(MANIFEST)
    validation = load(VALIDATION)
    prior = load(PRIOR)
    readiness = load(READINESS)
    request = load(REQUEST)
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
        or readiness.get("resource_writes") != 0
        or request.get("status") != "awaiting_exact_user_approval"
        or request.get("authorization_granted") is not False
        or request.get("requested_additional_create_requests") != 1
        or request.get("required_cpu_flavor") != "cpu5c"
        or request.get("manifest_sha256") != sha256(MANIFEST)
        or request.get("prior_reconciliation_sha256") != sha256(PRIOR)
        or request.get("readiness_sha256") != sha256(READINESS)
        or request.get("transport_regression_test_sha256") != sha256(TRANSPORT_TEST)
        or repeatability.get("status") != "verified"
        or repeatability.get("timing_gate_passes") != 3
        or portable.get("status") != "pass"
    ):
        raise ValueError("C27 retry-003 authorization prerequisites mismatch")
    record = {
        "schema": "crse-runpod-c27-retry-003-exact-payload-authorization/v1",
        "authorized": True,
        "authorization_basis": (
            "current user message approving the C27 retry-003 authorization request"),
        "user_approval_message": "I approve the C27 retry-003 authorization request.",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "retry_attempt": 3,
        "additional_create_requests": 1,
        "create_requests": 1,
        "prior_create_requests": 2,
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
        "required_cpu_flavor": "cpu5c",
        "fallback_cpu_flavors": [],
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
        "prior_reconciliation_sha256": sha256(PRIOR),
        "readiness_sha256": sha256(READINESS),
        "authorization_request_sha256": sha256(REQUEST),
        "transport_regression_test_sha256": sha256(TRANSPORT_TEST),
        "docker_repeatability_verification_sha256": sha256(DOCKER_REPEATABILITY),
        "portable_package_validation_sha256": sha256(PORTABLE_VALIDATION),
        "credentials_recorded_or_uploaded": False,
    }
    OUTPUT.write_bytes(json.dumps(
        record, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "authorized": True, "retry_attempt": 3,
        "additional_create_requests": 1, "required_cpu_flavor": "cpu5c",
        "rate_cap_usd_per_hour": 0.07,
        "source_files": 63, "source_bytes": 1078671,
        "controller_total_ceiling_usd": 0.05,
        "authorization_sha256": sha256(OUTPUT),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
