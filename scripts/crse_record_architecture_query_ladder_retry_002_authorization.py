"""Record the user's exact authorization for query-ladder retry 002."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
REQUEST = HERE / "RUNPOD_RETRY_002_AUTHORIZATION_REQUEST_20260904.json"
OUTPUT = HERE / "RUNPOD_ARCHITECTURE_QUERY_LADDER_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_09_04.json"
CONTROLLER = ROOT / "scripts/runpod_architecture_query_ladder_retry_002_controller.py"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite query-ladder retry 002 authorization")
    request = _load(REQUEST)
    exact_text = (
        "I authorize the exact Architecture Query-Ladder RunPod retry 002 described in "
        "RUNPOD_RETRY_002_AUTHORIZATION_REQUEST_20260904.json, with a maximum total charge of $0.04."
    )
    if (
        request.get("schema")
        != "cm-runpod-architecture-query-ladder-retry-002-authorization-request/v1"
        or request.get("status") != "exact_user_authorization_required_not_granted"
        or request.get("exact_approval_text") != exact_text
        or request.get("authorization") != {
            "granted": False, "prior_authorization_reused": False, "record_created": False,
        }
    ):
        raise ValueError("retry 002 request is not the exact non-authorizing artifact")
    scope = request["scope"]
    boundary = request["resource_and_cost_boundary"]
    package = request["package"]
    spec = importlib.util.spec_from_file_location("query_ladder_retry_002_authorization", CONTROLLER)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    if (
        request.get("controller_sha256") != _sha256(CONTROLLER)
        or request.get("transport_sources") != controller.transport_source_identities()
    ):
        raise ValueError("retry 002 controller or transport source changed after request")
    authorization = {
        "schema": "cm-runpod-architecture-query-ladder-retry-002-exact-payload-authorization/v1",
        "authorized": True,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "user_authorization_text": exact_text,
        "authorization_request_sha256": _sha256(REQUEST),
        "user_total_ceiling_usd": boundary["total_cost_cap_usd"],
        "controller_total_ceiling_usd": boundary["total_cost_cap_usd"],
        "cumulative_hard_ceiling_usd": boundary["cumulative_hard_ceiling_usd"],
        "prior_attempt_estimated_cost_usd": boundary["prior_attempt_estimated_cost_usd"],
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
        "compiler": "cc",
        "image": request["runtime"]["image"],
        "local_isolated_validation": package["local_isolated_validation"],
        "local_validation_pythonpath_injected": package["local_validation_pythonpath_injected"],
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
        "retry_ceiling_usd": authorization["user_total_ceiling_usd"],
        "cumulative_hard_ceiling_usd": authorization["cumulative_hard_ceiling_usd"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
