"""Create the exact, non-authorizing RunPod request for the query-ladder follow-up."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_query_ladder_followup_execution_20260903"
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
CONTRACT = HERE / "EXECUTION_CONTRACT.json"
PROTOCOL = HERE / "PROTOCOL.md"
LOCAL_VALIDATION = HERE / "LOCAL_PACKAGE_VALIDATION.json"
REQUEST = HERE / "RUNPOD_AUTHORIZATION_REQUEST_20260903.json"
AUTHORIZATION = HERE / "RUNPOD_ARCHITECTURE_QUERY_LADDER_EXACT_PAYLOAD_AUTHORIZED_2026_09_03.json"
FREEZE = ROOT / "docs/recognition/architecture_query_ladder_followup_freeze_20260903/FREEZE.json"
CONTROLLER = ROOT / "scripts/runpod_architecture_query_ladder_controller.py"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main() -> int:
    if REQUEST.exists():
        raise SystemExit("refusing to overwrite query-ladder authorization request")
    if AUTHORIZATION.exists():
        raise SystemExit("authorization record already exists; request preparation is not valid")
    manifest = _load(MANIFEST)
    contract = _load(CONTRACT)
    validation = _load(LOCAL_VALIDATION)
    query_rows = {str(query_count): 6_912 for query_count in (1, 4, 16, 64)}
    if (
        manifest.get("authorization_status") != "upload_not_authorized_exact_approval_pending"
        or contract.get("status") != "prepared_not_authorized"
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != _sha256(MANIFEST)
        or validation.get("network_used") is not False
        or validation.get("pythonpath_injected") is not False
        or validation.get("parent_and_followup_freeze_verification_passed") is not True
        or validation.get("timing_evidence_produced") is not False
        or validation.get("memory_evidence_produced") is not False
        or validation.get("decision_bearing_result_produced") is not False
        or contract.get("schedule", {}).get("total_cells") != 27_648
        or contract.get("schedule", {}).get("cells_per_query_count") != 6_912
        or contract.get("schedule", {}).get("query_counts") != [1, 4, 16, 64]
        or contract.get("memory", {}).get("method") != "isolated_fork_child_wait4_ru_maxrss/v1"
    ):
        raise ValueError("query-ladder package is not ready for an authorization request")
    spec = importlib.util.spec_from_file_location("query_ladder_controller", CONTROLLER)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    request = {
        "schema": "cm-runpod-architecture-query-ladder-authorization-request/v1",
        "status": "exact_user_authorization_required_not_granted",
        "created_date": "2026-09-03",
        "run_name": manifest["run_name"],
        "purpose": (
            "One decision-bearing Linux/GCC follow-up for architecture comparison Lane B: "
            "time q1, q4, q16, and q64 as separate exact residual-relation cells and "
            "measure each cell in an isolated child. No selector fitting, training, "
            "publication, or routing change."
        ),
        "exact_approval_text": (
            "I authorize the exact Architecture Query-Ladder RunPod run described in "
            "RUNPOD_AUTHORIZATION_REQUEST_20260903.json, with a maximum total charge of $0.05."
        ),
        "scope": {
            "planned_rows": 27_648,
            "query_rows": query_rows,
            "expected_counts": {"ok": 27_648, "refused": 0, "failed": 0},
            "all_query_counts_separately_timed": True,
            "one_fresh_child_per_timed_cell": True,
            "isolated_memory_method": contract["memory"]["method"],
            "commands": manifest["commands"],
        },
        "resource_and_cost_boundary": {
            "secure_cpu_pod": True,
            "vcpu_count": 2,
            "minimum_ram_gb": 4,
            "container_disk_gb": 12,
            "pod_volume_gb": 0,
            "network_volume": False,
            "https_ports": ["8080/http"],
            "one_create": True,
            "no_replacement": True,
            "rate_cap_usd_per_hour": 0.25,
            "total_cost_cap_usd": 0.05,
            "cleanup_seconds": 600,
            "reconciliation_seconds": 720,
            "same_pod_payload_attempt_limit": 6,
            "health_checks_before_upload": 2,
            "result_cap_bytes": manifest["result_cap_bytes"],
        },
        "runtime": manifest["runtime"],
        "network_boundary": {
            "during_setup": manifest["network_during_setup"],
            "during_workload": False,
            "dependency_urls_are_hash_and_size_bound": True,
        },
        "package": {
            "source_files": manifest["file_count"],
            "source_bytes": manifest["bytes"],
            "local_isolated_validation": "pass",
            "local_validation_pythonpath_injected": False,
        },
        "upload_manifest_sha256": _sha256(MANIFEST),
        "protocol_sha256": _sha256(PROTOCOL),
        "execution_contract_sha256": _sha256(CONTRACT),
        "local_validation_sha256": _sha256(LOCAL_VALIDATION),
        "freeze_sha256": _sha256(FREEZE),
        "controller_sha256": _sha256(CONTROLLER),
        "transport_sources": controller.transport_source_identities(),
        "authorization": {
            "granted": False,
            "prior_authorization_reused": False,
            "record_created": False,
        },
        "excluded": [
            "neural training", "selector or gate fitting", "production routing changes",
            "website updates", "publication", "git push", "automatic replacement pod",
            "persistent storage", "credential recording or upload",
        ],
    }
    _write_new(REQUEST, request)
    print(json.dumps({
        "status": request["status"],
        "request_sha256": _sha256(REQUEST),
        "source_files": manifest["file_count"],
        "source_bytes": manifest["bytes"],
        "planned_rows": 27_648,
        "query_rows": query_rows,
        "maximum_total_charge_usd": 0.05,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
