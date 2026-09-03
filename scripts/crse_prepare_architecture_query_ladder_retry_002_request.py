"""Create the exact, non-authorizing RunPod request for query-ladder retry 002."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
CONTRACT = HERE / "EXECUTION_CONTRACT.json"
PROTOCOL = HERE / "PROTOCOL.md"
LOCAL_VALIDATION = HERE / "LOCAL_PACKAGE_VALIDATION.json"
REQUEST = HERE / "RUNPOD_RETRY_002_AUTHORIZATION_REQUEST_20260904.json"
AUTHORIZATION = HERE / "RUNPOD_ARCHITECTURE_QUERY_LADDER_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_09_04.json"
FREEZE = ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904/FREEZE.json"
ATTEMPT_001_STATUS = (
    ROOT / "docs/recognition/architecture_query_ladder_followup_execution_20260903/ATTEMPT_001_STATUS.json"
)
CONTROLLER = ROOT / "scripts/runpod_architecture_query_ladder_retry_002_controller.py"
TOTAL_COST_CAP_USD = 0.04
CUMULATIVE_HARD_CEILING_USD = 0.05


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
        raise SystemExit("refusing to overwrite query-ladder retry 002 request")
    if AUTHORIZATION.exists():
        raise SystemExit("retry authorization already exists; request preparation is invalid")
    manifest = _load(MANIFEST)
    contract = _load(CONTRACT)
    validation = _load(LOCAL_VALIDATION)
    attempt = _load(ATTEMPT_001_STATUS)
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
        or contract.get("schedule", {}).get("query_counts") != [1, 4, 16, 64]
        or contract.get("limits", {}).get("workload_wall_seconds") != 420
        or contract.get("limits", {}).get("cleanup_seconds") != 600
        or contract.get("cleanup", {}).get("method") != "cache_clear_then_isolated_child_exit"
        or contract.get("cleanup", {}).get("gc_collect_in_fork_child") is not False
        or contract.get("timing_isolation", {}).get("isolation_lifecycle_reported_separately") is not True
        or attempt.get("status") != "closed_incomplete_timeout"
        or attempt.get("cleanup", {}).get("owned_pod_absent") is not True
        or attempt.get("cleanup", {}).get("independent_post_run_inventories") != {"v1": [], "v2": []}
    ):
        raise ValueError("query-ladder retry package or attempt closeout is not ready")
    spec = importlib.util.spec_from_file_location("query_ladder_retry_002_controller", CONTROLLER)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    query_rows = {str(query_count): 6_912 for query_count in (1, 4, 16, 64)}
    request = {
        "schema": "cm-runpod-architecture-query-ladder-retry-002-authorization-request/v1",
        "status": "exact_user_authorization_required_not_granted",
        "created_date": "2026-09-04",
        "run_name": manifest["run_name"],
        "purpose": (
            "One fresh retry of the non-neural Lane-B query ladder after attempt 001 "
            "timed out incomplete. The source correction removes inherited-parent-heap "
            "gc.collect from child task time, charges backend-cache clearing, and reports "
            "the full isolation lifecycle separately. No selector fitting, training, "
            "publication, or routing change."
        ),
        "exact_approval_text": (
            "I authorize the exact Architecture Query-Ladder RunPod retry 002 described in "
            "RUNPOD_RETRY_002_AUTHORIZATION_REQUEST_20260904.json, with a maximum total charge of $0.04."
        ),
        "prior_attempt": {
            "status_sha256": _sha256(ATTEMPT_001_STATUS),
            "status": attempt["status"],
            "completed_rows": attempt["failure"]["completed_rows"],
            "estimated_cost_usd": attempt["cost"]["estimated_compute_cost_usd"],
            "owned_pod_absent": True,
            "authorization_reused": False,
        },
        "scope": {
            "planned_rows": 27_648,
            "query_rows": query_rows,
            "expected_counts": {"ok": 27_648, "refused": 0, "failed": 0},
            "all_query_counts_separately_timed": True,
            "one_fresh_child_per_timed_cell": True,
            "isolated_memory_method": "isolated_fork_child_wait4_ru_maxrss/v1",
            "isolated_cleanup_method": "cache_clear_then_isolated_child_exit",
            "isolation_lifecycle_reported_separately": True,
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
            "total_cost_cap_usd": TOTAL_COST_CAP_USD,
            "prior_attempt_estimated_cost_usd": attempt["cost"]["estimated_compute_cost_usd"],
            "cumulative_hard_ceiling_usd": CUMULATIVE_HARD_CEILING_USD,
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
        "planned_rows": 27_648,
        "maximum_retry_charge_usd": TOTAL_COST_CAP_USD,
        "cumulative_hard_ceiling_usd": CUMULATIVE_HARD_CEILING_USD,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
