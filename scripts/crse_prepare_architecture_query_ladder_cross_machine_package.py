"""Prepare the immutable, non-authorizing cross-machine query-ladder package."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_query_ladder_cross_machine_execution_20260904"
CONTRACT = HERE / "EXECUTION_CONTRACT.json"
PROTOCOL = HERE / "PROTOCOL.md"
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
PRIOR_PACKAGE = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
)
PRIOR_MANIFEST = PRIOR_PACKAGE / "UPLOAD_MANIFEST.json"
PRIOR_CONTRACT = PRIOR_PACKAGE / "EXECUTION_CONTRACT.json"
PRIOR_PROTOCOL = PRIOR_PACKAGE / "PROTOCOL.md"
FREEZE = ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904/FREEZE.json"
FREEZE_VERIFICATION = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904"
    / "VERIFICATION.json"
)
ORACLES = ROOT / "docs/recognition/architecture_comparison_execution_retry_20260903/ORACLES.json"
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
RUN_NAME = "architecture-query-ladder-linux-clang-20260904-003"
COMPILER = "/usr/bin/clang-14"
CLANG_PACKAGE_VERSION = "1:14.0.6-12"
RESULT_CAP_BYTES = 48 << 20


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, value: Any) -> None:
    if path.exists() or not path.resolve().is_relative_to(ROOT):
        raise ValueError("cross-machine package output must be a new in-project file")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _verify_prior_result() -> dict[str, Any]:
    run = _load(PRIOR_RUN)
    runtime = _load(PRIOR_RUNTIME)
    results = _load(PRIOR_RESULTS)
    verification = _load(PRIOR_VERIFICATION)
    binding = _load(PRIOR_BINDING)
    inventory = _load(PRIOR_POST_INVENTORY)
    if (
        run.get("status") != "complete"
        or run.get("pod_id") != "r5wx3ximopqw7g"
        or run.get("selected_cpu") != "cpu3c"
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or runtime.get("cpu_model") != "AMD EPYC 9655 96-Core Processor"
        or results.get("status") != "complete"
        or results.get("expected_rows") != 27_648
        or verification.get("status") != "verified_complete"
        or verification.get("rows_checked") != 27_648
        or any(
            verification.get(field) != 0
            for field in (
                "semantic_mismatches",
                "schedule_mismatches",
                "source_or_artifact_mismatches",
                "memory_measurement_mismatches",
            )
        )
        or binding.get("compiler_executable_sha256")
        != "75e997ec62297a6484f491bae28ab0ccb489daba23e398fd10fe68e9e6f0def8"
        or inventory.get("owned_pod_absent") is not True
        or inventory.get("inventories") != {"v1": [], "v2": []}
    ):
        raise ValueError("prior query-ladder result is not a closed verified replication parent")
    return {
        "run_sha256": _sha256(PRIOR_RUN),
        "runtime_sha256": _sha256(PRIOR_RUNTIME),
        "results_sha256": _sha256(PRIOR_RESULTS),
        "verification_sha256": _sha256(PRIOR_VERIFICATION),
        "binding_sha256": _sha256(PRIOR_BINDING),
        "post_inventory_sha256": _sha256(PRIOR_POST_INVENTORY),
        "pod_id": run["pod_id"],
        "cpu_flavor": run["selected_cpu"],
        "cpu_model": runtime["cpu_model"],
        "compiler_executable": binding["compiler_executable"],
        "compiler_executable_sha256": binding["compiler_executable_sha256"],
        "compiler_version": binding["compiler_version"],
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
    }


def main() -> int:
    if not PROTOCOL.is_file() or CONTRACT.exists() or MANIFEST.exists():
        raise SystemExit("cross-machine protocol missing or package outputs already exist")
    prior = _verify_prior_result()
    previous_contract = _load(PRIOR_CONTRACT)
    freeze = _load(FREEZE)
    if (
        freeze.get("status") != "frozen_not_authorized"
        or freeze.get("schedule", {}).get("planned_cells") != 27_648
        or previous_contract.get("schedule", {}).get("total_cells") != 27_648
        or previous_contract.get("cleanup", {}).get("method")
        != "cache_clear_then_isolated_child_exit"
    ):
        raise ValueError("query-ladder source freeze or prior contract changed")

    runtime = copy.deepcopy(previous_contract["runtime"])
    runtime["compiler"] = "Debian Clang 14"
    runtime["compiler_executable"] = COMPILER
    runtime["compiler_package"] = {
        "name": "clang-14",
        "version": CLANG_PACKAGE_VERSION,
        "repository": "Debian Bookworm main",
        "installation": "apt-get with exact package version and no recommends",
        "runtime_executable_sha256_required": True,
    }
    contract = {
        "schema": "cm-architecture-query-ladder-cross-machine-execution-contract/v1",
        "status": "prepared_not_authorized",
        "date": "2026-09-04",
        "run_name": RUN_NAME,
        "source_checkpoint": previous_contract["source_checkpoint"],
        "freeze_file_sha256": _sha256(FREEZE),
        "freeze_canonical_sha256": freeze["freeze_sha256"],
        "freeze_verification_sha256": _sha256(FREEZE_VERIFICATION),
        "oracles_sha256": _sha256(ORACLES),
        "prior_result": prior,
        "host_separation": {
            "prior_pod_id": prior["pod_id"],
            "new_pod_id_required": True,
            "prior_cpu_flavor": prior["cpu_flavor"],
            "required_cpu_flavor": "cpu5c",
            "cpu_flavor_must_differ": True,
            "prior_cpu_model": prior["cpu_model"],
            "reject_prior_cpu_model_before_workload": True,
            "runpod_machine_id_required": True,
            "host_boot_id_sha256_recorded": True,
        },
        "compiler_separation": {
            "prior_family": "GCC",
            "prior_executable_sha256": prior["compiler_executable_sha256"],
            "required_family": "Clang",
            "required_package": "clang-14",
            "required_package_version": CLANG_PACKAGE_VERSION,
            "compiler_executable_sha256_recorded": True,
            "compiler_version_recorded": True,
        },
        "runtime": runtime,
        "schedule": previous_contract["schedule"],
        "memory": previous_contract["memory"],
        "cleanup": previous_contract["cleanup"],
        "timing_isolation": previous_contract["timing_isolation"],
        "limits": {
            "one_cloud_create": True,
            "automatic_replacement": False,
            "compiler_install_seconds": 180,
            "setup_deadline_seconds": 300,
            "workload_wall_seconds": 420,
            "remote_command_seconds": 480,
            "cleanup_seconds": 600,
            "reconciliation_seconds": 720,
            "result_cap_bytes": RESULT_CAP_BYTES,
        },
        "analysis_boundary": {
            "paired_cross_host_analysis_after_independent_verification": True,
            "retain_all_favorable_and_unfavorable_cells": True,
            "selector_or_gate_fitting": False,
            "neural_training": False,
            "production_routing_change": False,
            "website_update": False,
            "publication": False,
        },
        "permissions": {
            "local_functional_validation": True,
            "local_timing": False,
            "runpod_authorization_request": True,
            "runpod_execution": False,
            "selector_fitting": False,
            "neural_training": False,
            "production_routing_change": False,
            "website_update": False,
            "publication": False,
        },
    }
    _write_new(CONTRACT, contract)

    previous_manifest = _load(PRIOR_MANIFEST)
    replacements = {
        PRIOR_CONTRACT.relative_to(ROOT).as_posix(): CONTRACT.relative_to(ROOT).as_posix(),
        PRIOR_PROTOCOL.relative_to(ROOT).as_posix(): PROTOCOL.relative_to(ROOT).as_posix(),
    }
    files = []
    for previous in previous_manifest["files"]:
        source_relative = replacements.get(previous["source"], previous["source"])
        source = ROOT.joinpath(*Path(source_relative).parts)
        if not source.is_file():
            raise FileNotFoundError(source_relative)
        if previous["source"] not in replacements and (
            source.stat().st_size != previous["bytes"] or _sha256(source) != previous["sha256"]
        ):
            raise ValueError(f"frozen source changed before replication: {source_relative}")
        files.append({
            "source": source_relative,
            "target": source_relative,
            "bytes": source.stat().st_size,
            "sha256": _sha256(source),
        })
    if len(files) != 70 or len({row["target"] for row in files}) != 70:
        raise ValueError("cross-machine upload closure cardinality")
    manifest = {
        "schema": "cm-architecture-query-ladder-runpod-upload-manifest/v1",
        "authorization_status": "upload_not_authorized_exact_approval_pending",
        "created_date": "2026-09-04",
        "run_name": RUN_NAME,
        "file_count": len(files),
        "bytes": sum(row["bytes"] for row in files),
        "files": files,
        "setup": {
            "host_preflight_before_dependency_or_workload": True,
            "required_cpu_flavor": "cpu5c",
            "rejected_cpu_model": prior["cpu_model"],
            "compiler_package": "clang-14",
            "compiler_package_version": CLANG_PACKAGE_VERSION,
            "compiler_executable": COMPILER,
        },
        "commands": [
            [
                "python", "-B", "scripts/cm_architecture_query_ladder_campaign.py",
                "--output", f"run-output/{RUN_NAME}", "--compiler", COMPILER,
                "--freeze", FREEZE.relative_to(ROOT).as_posix(),
                "--oracles", ORACLES.relative_to(ROOT).as_posix(),
                "--max-seconds", "420",
            ],
            [
                "python", "-B", "scripts/crse_verify_architecture_query_ladder_campaign.py",
                "--run-dir", f"run-output/{RUN_NAME}",
                "--freeze", FREEZE.relative_to(ROOT).as_posix(),
                "--oracles", ORACLES.relative_to(ROOT).as_posix(),
            ],
        ],
        "execution_contract_sha256": _sha256(CONTRACT),
        "protocol_sha256": _sha256(PROTOCOL),
        "freeze_sha256": _sha256(FREEZE),
        "freeze_verification_sha256": _sha256(FREEZE_VERIFICATION),
        "oracles_sha256": _sha256(ORACLES),
        "prior_result_hashes": {
            key: value for key, value in prior.items() if key.endswith("_sha256")
        },
        "runtime": contract["runtime"],
        "limits": contract["limits"],
        "network_during_setup": (
            "pinned image, version-locked Debian clang-14 package, and four hash-locked wheels"
        ),
        "network_during_workload": False,
        "result_cap_bytes": RESULT_CAP_BYTES,
        "excluded": [
            ".env*", ".git/", "credentials", "tokens", "Windows DLLs", "website files",
            "unrelated dirty work", "prior RunPod raw evidence",
        ],
    }
    _write_new(MANIFEST, manifest)
    print(json.dumps({
        "status": manifest["authorization_status"],
        "planned_cells": 27_648,
        "files": manifest["file_count"],
        "bytes": manifest["bytes"],
        "compiler": COMPILER,
        "required_cpu_flavor": "cpu5c",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
