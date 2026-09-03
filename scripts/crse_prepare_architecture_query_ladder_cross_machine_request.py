"""Create the exact, non-authorizing request for the Clang/second-host replication."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_query_ladder_cross_machine_execution_20260904"
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
CONTRACT = HERE / "EXECUTION_CONTRACT.json"
PROTOCOL = HERE / "PROTOCOL.md"
LOCAL_VALIDATION = HERE / "LOCAL_PACKAGE_VALIDATION.json"
REQUEST = HERE / "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_AUTHORIZATION_REQUEST_20260904.json"
AUTHORIZATION = (
    HERE
    / "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_EXACT_PAYLOAD_AUTHORIZED_2026_09_04.json"
)
FREEZE = ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904/FREEZE.json"
CONTROLLER = ROOT / "scripts/runpod_architecture_query_ladder_cross_machine_controller.py"
PRIOR_PACKAGE = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
)
PRIOR_ROOT = PRIOR_PACKAGE / "runpod-architecture-query-ladder-execute-002"
PRIOR_RUN = PRIOR_ROOT / "RUN.json"
PRIOR_RUNTIME = PRIOR_ROOT / "evidence/run-output/RUNTIME.json"
PRIOR_STUDY = (
    PRIOR_ROOT / "evidence/run-output/architecture-query-ladder-linux-gcc-20260904-002"
)
PRIOR_RESULTS = PRIOR_STUDY / "results.json"
PRIOR_VERIFICATION = PRIOR_STUDY / "independent_verification.json"
PRIOR_BINDING = PRIOR_STUDY / "runtime_binding.json"
PRIOR_POST_INVENTORY = PRIOR_PACKAGE / "POST_RUN_INVENTORY.json"
TOTAL_COST_CAP_USD = 0.02
PRIOR_ESTIMATED_COST_USD = 0.0115828542470932
CUMULATIVE_HARD_CEILING_USD = 0.04


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, value: Any) -> None:
    if path.exists() or not path.resolve().is_relative_to(ROOT):
        raise ValueError("cross-machine request must be a new in-project file")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main() -> int:
    if REQUEST.exists():
        raise SystemExit("refusing to overwrite cross-machine authorization request")
    if AUTHORIZATION.exists():
        raise SystemExit("cross-machine authorization already exists")
    manifest = _load(MANIFEST)
    contract = _load(CONTRACT)
    validation = _load(LOCAL_VALIDATION)
    prior_run = _load(PRIOR_RUN)
    prior_runtime = _load(PRIOR_RUNTIME)
    prior_verification = _load(PRIOR_VERIFICATION)
    prior_binding = _load(PRIOR_BINDING)
    prior_inventory = _load(PRIOR_POST_INVENTORY)
    if (
        manifest.get("authorization_status")
        != "upload_not_authorized_exact_approval_pending"
        or manifest.get("file_count") != 70
        or manifest.get("bytes") != sum(row["bytes"] for row in manifest.get("files", []))
        or manifest.get("commands", [[], []])[0][
            manifest["commands"][0].index("--compiler") + 1
        ] != "/usr/bin/clang-14"
        or contract.get("status") != "prepared_not_authorized"
        or contract.get("host_separation", {}).get("required_cpu_flavor") != "cpu5c"
        or contract.get("host_separation", {}).get("reject_prior_cpu_model_before_workload")
        is not True
        or contract.get("compiler_separation", {}).get("required_family") != "Clang"
        or contract.get("compiler_separation", {}).get("required_package_version")
        != "1:14.0.6-12"
        or contract.get("schedule", {}).get("total_cells") != 27_648
        or contract.get("limits", {}).get("workload_wall_seconds") != 420
        or contract.get("limits", {}).get("cleanup_seconds") != 600
        or validation.get("status") != "pass"
        or validation.get("manifest_sha256") != _sha256(MANIFEST)
        or validation.get("network_used") is not False
        or validation.get("pythonpath_injected") is not False
        or validation.get("timing_evidence_produced") is not False
        or validation.get("memory_evidence_produced") is not False
        or validation.get("decision_bearing_result_produced") is not False
        or prior_run.get("status") != "complete"
        or prior_run.get("pod_id") != "r5wx3ximopqw7g"
        or prior_run.get("cleanup", {}).get("owned_pod_absent") is not True
        or prior_runtime.get("cpu_model") != "AMD EPYC 9655 96-Core Processor"
        or prior_verification.get("status") != "verified_complete"
        or prior_verification.get("rows_checked") != 27_648
        or prior_binding.get("compiler_executable_sha256")
        != "75e997ec62297a6484f491bae28ab0ccb489daba23e398fd10fe68e9e6f0def8"
        or prior_inventory.get("owned_pod_absent") is not True
        or prior_inventory.get("inventories") != {"v1": [], "v2": []}
    ):
        raise ValueError("cross-machine package or prior result is not ready")
    spec = importlib.util.spec_from_file_location(
        "query_ladder_cross_machine_request_controller", CONTROLLER,
    )
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    compile(controller.HOST_PREFLIGHT_CODE, "<cross-machine-host-preflight>", "exec")
    compile(controller.CLANG_INSTALL_CODE, "<cross-machine-clang-install>", "exec")
    compile(controller.base.REMOTE_CODE, "<cross-machine-remote>", "exec")
    query_rows = {str(query_count): 6_912 for query_count in (1, 4, 16, 64)}
    request = {
        "schema": "cm-runpod-architecture-query-ladder-cross-machine-authorization-request/v1",
        "status": "exact_user_authorization_required_not_granted",
        "created_date": "2026-09-04",
        "run_name": manifest["run_name"],
        "purpose": (
            "Repeat the exact non-neural 27,648-cell Lane-B query ladder with a new Pod, "
            "a different RunPod CPU flavor and CPU model, and Debian Clang 14 instead of "
            "GCC 12. The run supports paired portability analysis only after independent "
            "verification; it does not authorize selection, routing, or publication."
        ),
        "exact_approval_text": (
            "I authorize the exact Architecture Query-Ladder Cross-Machine RunPod run described in "
            "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_AUTHORIZATION_REQUEST_20260904.json, "
            "with a maximum total charge of $0.02."
        ),
        "prior_result": {
            "pod_id": prior_run["pod_id"],
            "cpu_flavor": prior_run["selected_cpu"],
            "cpu_model": prior_runtime["cpu_model"],
            "compiler_executable_sha256": prior_binding["compiler_executable_sha256"],
            "verification_status": prior_verification["status"],
            "rows_checked": prior_verification["rows_checked"],
            "owned_pod_absent": True,
            "authorization_reused": False,
        },
        "scope": {
            "planned_rows": 27_648,
            "query_rows": query_rows,
            "expected_counts": {"ok": 27_648, "refused": 0, "failed": 0},
            "same_freeze_schedule_arms_oracles_and_artifact": True,
            "all_query_counts_separately_timed": True,
            "one_fresh_child_per_timed_cell": True,
            "isolated_memory_method": "isolated_fork_child_wait4_ru_maxrss/v1",
            "isolated_cleanup_method": "cache_clear_then_isolated_child_exit",
            "isolation_lifecycle_reported_separately": True,
            "commands": manifest["commands"],
        },
        "host_and_compiler_boundary": {
            "preferred_cpu_flavor": "cpu5c",
            "prior_cpu_flavor": "cpu3c",
            "cpu_flavor_must_differ": True,
            "prior_pod_id": "r5wx3ximopqw7g",
            "new_pod_id_required": True,
            "prior_cpu_model": "AMD EPYC 9655 96-Core Processor",
            "reject_same_cpu_model_before_dependency_setup_or_workload": True,
            "runpod_machine_id_required": True,
            "compiler": "/usr/bin/clang-14",
            "clang_package": "clang-14",
            "clang_package_version": "1:14.0.6-12",
            "compiler_executable_sha256_recorded": True,
            "compiler_version_recorded": True,
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
            "rate_cap_usd_per_hour": 0.10,
            "total_cost_cap_usd": TOTAL_COST_CAP_USD,
            "prior_estimated_cost_usd": PRIOR_ESTIMATED_COST_USD,
            "cumulative_hard_ceiling_usd": CUMULATIVE_HARD_CEILING_USD,
            "cleanup_seconds": 600,
            "reconciliation_seconds": 720,
            "same_pod_payload_attempt_limit": 6,
            "health_checks_before_upload": 2,
            "result_cap_bytes": manifest["result_cap_bytes"],
        },
        "network_boundary": {
            "during_setup": manifest["network_during_setup"],
            "during_workload": False,
            "clang_package_version_locked": True,
            "apt_repository_metadata_verified_by_apt": True,
            "python_dependency_urls_hash_and_size_bound": True,
        },
        "analysis_boundary": contract["analysis_boundary"],
        "package": {
            "source_files": manifest["file_count"],
            "source_bytes": manifest["bytes"],
            "local_isolated_validation": "pass",
            "local_validation_pythonpath_injected": False,
        },
        "runtime": manifest["runtime"],
        "upload_manifest_sha256": _sha256(MANIFEST),
        "protocol_sha256": _sha256(PROTOCOL),
        "execution_contract_sha256": _sha256(CONTRACT),
        "local_validation_sha256": _sha256(LOCAL_VALIDATION),
        "freeze_sha256": _sha256(FREEZE),
        "controller_sha256": _sha256(CONTROLLER),
        "prior_run_sha256": _sha256(PRIOR_RUN),
        "prior_results_sha256": _sha256(PRIOR_RESULTS),
        "prior_verification_sha256": _sha256(PRIOR_VERIFICATION),
        "prior_runtime_sha256": _sha256(PRIOR_RUNTIME),
        "prior_binding_sha256": _sha256(PRIOR_BINDING),
        "prior_post_inventory_sha256": _sha256(PRIOR_POST_INVENTORY),
        "transport_sources": controller.transport_source_identities(),
        "authorization": {
            "granted": False,
            "prior_authorization_reused": False,
            "record_created": False,
        },
        "excluded": [
            "neural training", "selector or gate fitting", "production routing changes",
            "website updates", "publication", "git push", "automatic replacement pod",
            "persistent storage", "credential recording or upload", "same CPU model as prior run",
        ],
    }
    _write_new(REQUEST, request)
    print(json.dumps({
        "status": request["status"],
        "request_sha256": _sha256(REQUEST),
        "planned_rows": 27_648,
        "maximum_charge_usd": TOTAL_COST_CAP_USD,
        "cumulative_hard_ceiling_usd": CUMULATIVE_HARD_CEILING_USD,
        "required_cpu_flavor": "cpu5c",
        "compiler": "/usr/bin/clang-14",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
