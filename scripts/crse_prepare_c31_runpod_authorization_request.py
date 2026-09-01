"""Record the exact bounded C31 RunPod request without authorizing or creating resources."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c31_linux_confirmation"
MANIFEST = HERE / "c31_linux_upload_manifest.json"
PROTOCOL = HERE / "C31_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_09_01.md"
VALIDATION = HERE / "C31_PACKAGE_LOCAL_VALIDATION_20260901.json"
CONTRACT = ROOT / "docs/recognition/c31_prepared_policy_replication_contract.json"
CONTROLLER = HERE / "runpod_c31_linux_controller.py"
OUTPUT = HERE / "RUNPOD_C31_AUTHORIZATION_REQUEST_20260901.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C31 authorization request")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if (
        manifest.get("file_count") != 71
        or manifest.get("bytes") != 1153868
        or manifest.get("authorization_status")
        != "upload_not_authorized_exact_approval_pending"
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != sha256(MANIFEST)
        or validation.get("replication_contract_sha256") != sha256(CONTRACT)
    ):
        raise ValueError("C31 exact package is not locally validated")
    request = {
        "schema": "crse-runpod-c31-exact-payload-authorization-request/v1",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "authorization_granted": False,
        "resource_writes": 0,
        "requested_effect": (
            "Upload only the frozen C31 package to one newly created Secure CPU pod, "
            "run the unchanged C30 experiment and independent verifier, retrieve bounded "
            "evidence, and delete the owned pod."
        ),
        "user_total_ceiling_usd": 5.0,
        "controller_total_ceiling_usd": 0.05,
        "one_create": True,
        "no_replacement": True,
        "source_files": 71,
        "source_bytes": 1153868,
        "cases": 48,
        "blocks": 16,
        "query_count": 8,
        "measurement_batches": 128,
        "paired_batches": 64,
        "timed_queries": 1024,
        "verified_context_records": 512,
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
        "credentials_recorded_or_uploaded": False,
        "credential_reference_names": ["RUNPOD_API_KEY", "RP_TOKEN"],
        "upload_manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "local_validation_sha256": sha256(VALIDATION),
        "replication_contract_sha256": sha256(CONTRACT),
        "controller_sha256": sha256(CONTROLLER),
        "policy_refit": False,
        "training": False,
        "production_write": False,
        "shadow_promotion": False,
        "production_promotion": False,
    }
    OUTPUT.write_bytes(
        json.dumps(request, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "status": "exact_approval_pending",
        "request_sha256": sha256(OUTPUT),
        "source_files": request["source_files"],
        "source_bytes": request["source_bytes"],
        "resource_writes": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
