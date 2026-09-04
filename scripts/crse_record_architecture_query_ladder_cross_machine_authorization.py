"""Record the user's exact authorization for the cross-machine query-ladder run."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_query_ladder_cross_machine_execution_20260904"
REQUEST = (
    HERE
    / "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_AUTHORIZATION_REQUEST_20260904.json"
)
OUTPUT = (
    HERE
    / "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_EXACT_PAYLOAD_AUTHORIZED_2026_09_04.json"
)
CONTROLLER = ROOT / "scripts/runpod_architecture_query_ladder_cross_machine_controller.py"
EXPECTED_REQUEST_SHA256 = "b9b9a8aba4eb71c70609eff705a26bbf2de6efe935253dc2404c5e8da83e3bad"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite cross-machine query-ladder authorization")
    request = _load(REQUEST)
    exact_text = (
        "I authorize the exact Architecture Query-Ladder Cross-Machine RunPod run described in "
        "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_AUTHORIZATION_REQUEST_20260904.json, "
        "with a maximum total charge of $0.02."
    )
    if (
        _sha256(REQUEST) != EXPECTED_REQUEST_SHA256
        or request.get("schema")
        != "cm-runpod-architecture-query-ladder-cross-machine-authorization-request/v1"
        or request.get("status") != "exact_user_authorization_required_not_granted"
        or request.get("exact_approval_text") != exact_text
        or request.get("authorization") != {
            "granted": False, "prior_authorization_reused": False, "record_created": False,
        }
    ):
        raise ValueError("cross-machine request is not the exact authorized artifact")

    scope = request["scope"]
    boundary = request["resource_and_cost_boundary"]
    host = request["host_and_compiler_boundary"]
    package = request["package"]
    spec = importlib.util.spec_from_file_location(
        "query_ladder_cross_machine_authorization", CONTROLLER,
    )
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    if (
        request.get("controller_sha256") != _sha256(CONTROLLER)
        or request.get("transport_sources") != controller.transport_source_identities()
    ):
        raise ValueError("cross-machine controller or transport changed after request")

    authorization = {
        "schema": "cm-runpod-architecture-query-ladder-cross-machine-exact-payload-authorization/v1",
        "authorized": True,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "user_authorization_text": exact_text,
        "authorization_request_sha256": _sha256(REQUEST),
        "user_total_ceiling_usd": boundary["total_cost_cap_usd"],
        "controller_total_ceiling_usd": boundary["total_cost_cap_usd"],
        "cumulative_hard_ceiling_usd": boundary["cumulative_hard_ceiling_usd"],
        "prior_estimated_cost_usd": boundary["prior_estimated_cost_usd"],
        "one_create": boundary["one_create"],
        "no_replacement": boundary["no_replacement"],
        "source_files": package["source_files"],
        "source_bytes": package["source_bytes"],
        "planned_rows": scope["planned_rows"],
        "query_rows": scope["query_rows"],
        "https": False,
        "https_ports": boundary["https_ports"],
        "vcpu_count": boundary["vcpu_count"],
        "minimum_ram_gb": boundary["minimum_ram_gb"],
        "container_disk_gb": boundary["container_disk_gb"],
        "pod_volume_gb": boundary["pod_volume_gb"],
        "network_volume": boundary["network_volume"],
        "cleanup_seconds": boundary["cleanup_seconds"],
        "reconciliation": False,
        "reconciliation_seconds": boundary["reconciliation_seconds"],
        "rate_cap_usd_per_hour": boundary["rate_cap_usd_per_hour"],
        "total_cost_cap_usd": boundary["total_cost_cap_usd"],
        "same_pod_payload_attempt_limit": boundary["same_pod_payload_attempt_limit"],
        "health_checks_before_upload": boundary["health_checks_before_upload"],
        "result_cap_bytes": boundary["result_cap_bytes"],
        "preferred_cpu_flavor": host["preferred_cpu_flavor"],
        "prior_cpu_flavor": host["prior_cpu_flavor"],
        "prior_pod_id": host["prior_pod_id"],
        "prior_cpu_model": host["prior_cpu_model"],
        "reject_same_cpu_model": host[
            "reject_same_cpu_model_before_dependency_setup_or_workload"
        ],
        "compiler": host["compiler"],
        "clang_package": host["clang_package"],
        "clang_package_version": host["clang_package_version"],
        "image": request["runtime"]["image"],
        "local_isolated_validation": package["local_isolated_validation"],
        "local_validation_pythonpath_injected": package[
            "local_validation_pythonpath_injected"
        ],
        "isolated_memory_method": scope["isolated_memory_method"],
        "isolated_cleanup_method": scope["isolated_cleanup_method"],
        "credentials_recorded_or_uploaded": False,
        "prior_authorization_reused": False,
        "training": False,
        "selector_fit": False,
        "website_update": False,
        "production_write": False,
        "upload_manifest_sha256": request["upload_manifest_sha256"],
        "protocol_sha256": request["protocol_sha256"],
        "execution_contract_sha256": request["execution_contract_sha256"],
        "local_validation_sha256": request["local_validation_sha256"],
        "freeze_sha256": request["freeze_sha256"],
        "controller_sha256": request["controller_sha256"],
        "prior_run_sha256": request["prior_run_sha256"],
        "prior_results_sha256": request["prior_results_sha256"],
        "prior_verification_sha256": request["prior_verification_sha256"],
        "prior_runtime_sha256": request["prior_runtime_sha256"],
        "prior_binding_sha256": request["prior_binding_sha256"],
        "prior_post_inventory_sha256": request["prior_post_inventory_sha256"],
        "transport_sources": request["transport_sources"],
    }
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(authorization, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")

    controller.require_authorization()
    print(json.dumps({
        "authorized": True,
        "authorization_sha256": _sha256(OUTPUT),
        "authorization_request_sha256": authorization["authorization_request_sha256"],
        "run_ceiling_usd": authorization["user_total_ceiling_usd"],
        "cumulative_hard_ceiling_usd": authorization["cumulative_hard_ceiling_usd"],
        "required_cpu_flavor": authorization["preferred_cpu_flavor"],
        "compiler": authorization["compiler"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
