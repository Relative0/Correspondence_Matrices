from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_query_ladder_cross_machine_execution_20260904"
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
CONTRACT = HERE / "EXECUTION_CONTRACT.json"
VALIDATION = HERE / "LOCAL_PACKAGE_VALIDATION.json"
REQUEST = (
    HERE
    / "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_AUTHORIZATION_REQUEST_20260904.json"
)
AUTHORIZATION = (
    HERE
    / "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_EXACT_PAYLOAD_AUTHORIZED_2026_09_04.json"
)
FREEZE = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904"
    / "FREEZE.json"
)
PRIOR_ROOT = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
    / "runpod-architecture-query-ladder-execute-002"
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _controller():
    path = ROOT / "scripts/runpod_architecture_query_ladder_cross_machine_controller.py"
    spec = importlib.util.spec_from_file_location(
        "query_ladder_cross_machine_controller_test", path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cross_machine_package_is_source_exact_and_non_authorizing() -> None:
    manifest = _load(MANIFEST)
    contract = _load(CONTRACT)
    validation = _load(VALIDATION)
    freeze = _load(FREEZE)

    assert manifest["authorization_status"] == "upload_not_authorized_exact_approval_pending"
    assert manifest["file_count"] == len(manifest["files"]) == 70
    assert manifest["bytes"] == sum(row["bytes"] for row in manifest["files"])
    assert {row["path"] for row in freeze["source_closure"]} <= {
        row["source"] for row in manifest["files"]
    }
    for row in manifest["files"]:
        source = ROOT.joinpath(*Path(row["source"]).parts)
        assert source.stat().st_size == row["bytes"]
        assert _sha256(source) == row["sha256"]

    assert contract["status"] == "prepared_not_authorized"
    assert contract["schedule"]["total_cells"] == 27_648
    assert contract["schedule"]["query_counts"] == [1, 4, 16, 64]
    assert contract["host_separation"] == {
        "prior_pod_id": "r5wx3ximopqw7g",
        "new_pod_id_required": True,
        "prior_cpu_flavor": "cpu3c",
        "required_cpu_flavor": "cpu5c",
        "cpu_flavor_must_differ": True,
        "prior_cpu_model": "AMD EPYC 9655 96-Core Processor",
        "reject_prior_cpu_model_before_workload": True,
        "runpod_machine_id_required": True,
        "host_boot_id_sha256_recorded": True,
    }
    assert contract["compiler_separation"]["prior_family"] == "GCC"
    assert contract["compiler_separation"]["required_family"] == "Clang"
    assert contract["compiler_separation"]["required_package_version"] == "1:14.0.6-12"
    assert manifest["setup"]["host_preflight_before_dependency_or_workload"] is True
    command = manifest["commands"][0]
    assert command[command.index("--compiler") + 1] == "/usr/bin/clang-14"

    assert validation["status"] == "pass"
    assert validation["manifest_sha256"] == _sha256(MANIFEST)
    assert validation["functional_rows_checked"] == 32
    assert validation["functional_query_counts"] == [1, 4, 16, 64]
    assert validation["network_used"] is False
    assert validation["runpod_resource_created"] is False
    assert validation["pythonpath_injected"] is False
    assert validation["timing_evidence_produced"] is False
    assert validation["memory_evidence_produced"] is False
    assert validation["decision_bearing_result_produced"] is False


def test_cross_machine_request_binds_package_controller_and_prior_result() -> None:
    request = _load(REQUEST)
    controller = _controller()
    controller_path = ROOT / "scripts/runpod_architecture_query_ladder_cross_machine_controller.py"

    assert request["status"] == "exact_user_authorization_required_not_granted"
    assert request["authorization"] == {
        "granted": False, "prior_authorization_reused": False, "record_created": False,
    }
    assert request["exact_approval_text"] == (
        "I authorize the exact Architecture Query-Ladder Cross-Machine RunPod run described in "
        "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_AUTHORIZATION_REQUEST_20260904.json, "
        "with a maximum total charge of $0.02."
    )
    assert request["resource_and_cost_boundary"]["total_cost_cap_usd"] == 0.02
    assert request["resource_and_cost_boundary"]["cumulative_hard_ceiling_usd"] == 0.04
    assert request["resource_and_cost_boundary"]["one_create"] is True
    assert request["resource_and_cost_boundary"]["no_replacement"] is True
    assert request["host_and_compiler_boundary"]["preferred_cpu_flavor"] == "cpu5c"
    assert request["host_and_compiler_boundary"][
        "reject_same_cpu_model_before_dependency_setup_or_workload"
    ] is True
    assert request["host_and_compiler_boundary"]["compiler"] == "/usr/bin/clang-14"
    assert request["controller_sha256"] == _sha256(controller_path)
    assert request["transport_sources"] == controller.transport_source_identities()
    assert request["upload_manifest_sha256"] == _sha256(MANIFEST)
    assert request["execution_contract_sha256"] == _sha256(CONTRACT)
    assert request["local_validation_sha256"] == _sha256(VALIDATION)
    assert request["freeze_sha256"] == _sha256(FREEZE)
    assert request["prior_run_sha256"] == _sha256(PRIOR_ROOT / "RUN.json")
    assert request["prior_runtime_sha256"] == _sha256(
        PRIOR_ROOT / "evidence/run-output/RUNTIME.json"
    )


def test_cross_machine_controller_compiles_and_fails_closed_without_authorization() -> None:
    controller = _controller()
    compile(controller.HOST_PREFLIGHT_CODE, "<cross-machine-host-preflight>", "exec")
    compile(controller.CLANG_INSTALL_CODE, "<cross-machine-clang-install>", "exec")
    compile(controller.base.REMOTE_CODE, "<cross-machine-query-ladder-remote>", "exec")

    assert controller.RUN_NAME in controller.base.REMOTE_CODE
    assert "architecture-cross-machine-host-preflight" in controller.base.REMOTE_CODE
    assert "architecture-clang-install" in controller.base.REMOTE_CODE
    assert "/usr/bin/clang-14" in controller.base.REMOTE_CODE
    assert controller.shared.CAMPAIGN_CAP == 0.02
    assert controller.shared.RATE_CAP == 0.10
    assert controller.AUTHORIZATION == AUTHORIZATION
    assert AUTHORIZATION.exists() is False
    with pytest.raises(FileNotFoundError):
        controller.require_authorization()


def test_cross_machine_preflight_selects_only_the_frozen_cpu_flavor() -> None:
    controller = _controller()

    class Delegate:
        @staticmethod
        def check():
            return {
                "offers": [
                    {"id": "cpu3c", "eligible": True, "rate_usd_per_hour": 0.06},
                    {"id": "cpu5c", "eligible": True, "rate_usd_per_hour": 0.08},
                ],
                "prior_cost_bound_usd": 0.0115828542470932,
                "inventories": {"v1": [], "v2": []},
                "credit_sufficient": True,
                "spend_limit_sufficient": True,
            }

    result = controller._ReplicationPreflight(Delegate()).check()
    assert result["ready"] is True
    assert result["selected_offer"]["id"] == "cpu5c"
    assert result["budget"]["rate_usd_per_hour"] == 0.08
    assert result["budget"]["phase_cost_cap_usd"] == 0.02
    assert result["budget"]["maximum_authorized_cumulative_cost_usd"] < 0.04
    assert result["cross_machine_cpu_constraint"]["prior_cpu_flavor"] == "cpu3c"
    assert result["cross_machine_cpu_constraint"][
        "same_cpu_model_rejected_before_workload"
    ] is True


def test_cross_machine_preflight_rejects_an_over_cap_cpu5c_offer() -> None:
    controller = _controller()

    class Delegate:
        @staticmethod
        def check():
            return {
                "offers": [
                    {"id": "cpu5c", "eligible": True, "rate_usd_per_hour": 0.11},
                ],
                "prior_cost_bound_usd": 0.03,
                "inventories": {"v1": [], "v2": []},
                "credit_sufficient": True,
                "spend_limit_sufficient": True,
            }

    result = controller._ReplicationPreflight(Delegate()).check()
    assert result["selected_offer"]["id"] == "cpu5c"
    assert result["budget"]["ready"] is False
    assert result["ready"] is False


def test_remote_host_preflight_rejects_the_prior_cpu_model() -> None:
    controller = _controller()
    runtime = PRIOR_ROOT / "evidence/run-output/RUNTIME.json"
    output = HERE / ".HOST-PREFLIGHT-REJECTION-TEST.json"
    assert _load(runtime)["cpu_model"] == "AMD EPYC 9655 96-Core Processor"
    assert output.exists() is False

    completed = subprocess.run(
        [sys.executable, "-c", controller.HOST_PREFLIGHT_CODE, str(output), str(runtime)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode != 0
    assert output.exists() is False
