"""Create the exact, non-authorizing request for the frozen C38 RunPod run."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c38_linux_confirmation"
CONTROLLER = HERE / "runpod_c38_linux_controller.py"
MANIFEST = HERE / "c38_linux_upload_manifest.json"
PROTOCOL = HERE / "C38_C37_NATIVE_SECOND_MACHINE_PROTOCOL_2026_09_03.md"
CONTRACT = HERE / "c38_c37_native_replication_contract.json"
LOCAL_VALIDATION = HERE / "C38_PACKAGE_LOCAL_VALIDATION_20260903.json"
OUTPUT = HERE / "RUNPOD_C38_AUTHORIZATION_REQUEST_20260903.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: Any) -> None:
    with path.open("xb") as stream:
        stream.write(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
            + b"\n"
        )


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite the C38 authorization request")
    manifest = load(MANIFEST)
    validation = load(LOCAL_VALIDATION)
    if (
        validation.get("status") != "pass"
        or validation.get("manifest_sha256") != sha256(MANIFEST)
        or validation.get("timing_result_used_for_c38_decision") is not False
        or manifest.get("authorization_status")
        != "upload_not_authorized_exact_approval_pending"
    ):
        raise ValueError("C38 exact authorization request requires passing local validation")

    spec = importlib.util.spec_from_file_location("c38_controller_for_request", CONTROLLER)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    document = {
        "schema": "crse-runpod-c38-exact-payload-authorization-request/v1",
        "authorization_granted": False,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "requested_effect": (
            "Upload only the frozen C38 44-file package to one newly created Secure "
            "CPU Pod, rebuild the C37 C11 library with Linux cc/GCC, run the unchanged "
            "C37 schedule and two independent verifiers, retrieve at most 24 MiB, "
            "delete the owned Pod, and reconcile RunPod inventories."
        ),
        "upload_manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "replication_contract_sha256": sha256(CONTRACT),
        "local_validation_sha256": sha256(LOCAL_VALIDATION),
        "controller_sha256": sha256(CONTROLLER),
        "transport_sources": controller.transport_source_identities(),
        "source_files": manifest["file_count"],
        "source_bytes": manifest["bytes"],
        "image": controller.IMAGE,
        "compiler": "cc",
        "single_root_cases": 18,
        "single_root_blocks": 12,
        "multi_root_workloads": 6,
        "multi_root_blocks": 20,
        "raw_sessions": 954,
        "single_root_query_checks": 44928,
        "multi_root_output_query_checks": 48384,
        "one_create": True,
        "no_replacement": True,
        "cloud_type": "SECURE",
        "compute_type": "CPU",
        "vcpu_count": 2,
        "minimum_ram_gb": 4,
        "container_disk_gb": 12,
        "pod_volume_gb": 0,
        "network_volume": False,
        "https_ports": ["8080/http"],
        "rate_cap_usd_per_hour": 0.25,
        "total_cost_cap_usd": 0.05,
        "controller_total_ceiling_usd": 0.05,
        "user_total_ceiling_usd": 5.0,
        "cleanup_seconds": 600,
        "reconciliation_seconds": 720,
        "same_pod_payload_attempt_limit": 6,
        "health_checks_before_upload": 2,
        "result_cap_bytes": 24 << 20,
        "network_during_setup": manifest["network_during_setup"],
        "network_during_workload": False,
        "local_isolated_validation": "pass",
        "local_validation_pythonpath_injected": False,
        "credentials_recorded_or_uploaded": False,
        "credential_reference_names": ["RUNPOD_API_KEY", "RP_TOKEN"],
        "training": False,
        "website_update": False,
        "deployment": False,
        "production_write": False,
        "shadow_promotion": False,
        "production_promotion": False,
        "commit": False,
        "push": False,
    }
    write_new(OUTPUT, document)
    print(json.dumps({
        "authorization_granted": False,
        "request_sha256": sha256(OUTPUT),
        "controller_sha256": document["controller_sha256"],
        "manifest_sha256": document["upload_manifest_sha256"],
        "source_files": document["source_files"],
        "source_bytes": document["source_bytes"],
        "maximum_controller_cost_usd": document["controller_total_ceiling_usd"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
