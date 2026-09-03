from __future__ import annotations

import importlib.util
import inspect
import json
import math
from pathlib import Path

import pytest

from scripts.crse_verify_c38_retrieval import replay_verifiers, sha256


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c38_linux_confirmation"
INITIAL = HERE / "runpod-c38-linux-execute-001"
RETRY = HERE / "runpod-c38-linux-execute-002"
REMOTE = RETRY / "evidence/run-output/c38-c37-native-linux-gcc-20260903-001"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_retry_controller():
    path = HERE / "runpod_c38_linux_controller_retry_001.py"
    spec = importlib.util.spec_from_file_location("c38_retry_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_initial_c38_attempt_is_a_reconciled_no_create_failure() -> None:
    run = load(INITIAL / "RUN.json")
    reconciliation = load(HERE / "C38_INITIAL_NO_CREATE_RECONCILIATION_20260903.json")

    assert run["status"] == "failed"
    assert run["error"] == "watchdog exited before create"
    assert run["creation_attempted"] is False
    assert run["creation_uncertain"] is False
    assert run["pod_created"] is False
    assert run["uploaded_source_files"] == 0
    assert run["cleanup"]["owned_pod_absent"] is True
    assert all(not rows for rows in run["cleanup"]["inventories"].values())
    assert reconciliation["status"] == "reconciled_no_create"
    assert reconciliation["authorized_create_consumed"] is False
    assert reconciliation["initial_run_sha256"] == sha256(INITIAL / "RUN.json")


def test_c38_retry_controller_is_bound_and_watchdog_compatible() -> None:
    controller = load_retry_controller()
    request = load(HERE / "RUNPOD_C38_TRANSPORT_RETRY_001_REQUEST_20260903.json")
    authorization = load(
        HERE / "RUNPOD_C38_TRANSPORT_RETRY_001_AUTHORIZED_2026_09_03.json"
    )
    controller_path = HERE / "runpod_c38_linux_controller_retry_001.py"
    request_path = HERE / "RUNPOD_C38_TRANSPORT_RETRY_001_REQUEST_20260903.json"

    state = controller.build_watchdog_state(1000.0, "012345abcdef")
    inherited_watchdog = inspect.getsource(controller.shared.watchdog)
    assert controller.OUT.name == "runpod-c38-linux-execute-002"
    assert state == {
        "name": "cm-c7-linux-012345abcdef",
        "created_epoch": 1000.0,
        "cleanup_epoch": 1000.0 + controller.shared.CLEANUP_AT,
        "horizon_epoch": 1000.0 + controller.shared.HORIZON,
    }
    assert 'r"cm-c7-linux-[a-f0-9]{12}"' in inherited_watchdog
    with pytest.raises(ValueError):
        controller.build_watchdog_state(math.nan, "012345abcdef")
    with pytest.raises(ValueError):
        controller.build_watchdog_state(1000.0, "not-a-nonce")
    assert request["authorization_granted"] is False
    assert request["scientific_payload_changed"] is False
    assert request["authorized_create_consumed_before_retry"] is False
    assert authorization["authorized"] is True
    assert authorization["one_create"] is True
    assert authorization["no_replacement"] is True
    assert authorization["controller_sha256"] == sha256(controller_path)
    assert authorization["authorization_request_sha256"] == sha256(request_path)
    assert controller.require_authorization() == authorization


def test_c38_retrieval_and_cross_machine_decision_are_fail_closed() -> None:
    run = load(RETRY / "RUN.json")
    final = load(HERE / "RUNPOD_C38_FINAL_VERIFICATION_20260903.json")
    adjudication = load(HERE / "C38_CROSS_MACHINE_ADJUDICATION_20260903.json")
    linux = load(REMOTE / "results.json")

    assert run["status"] == "complete"
    assert run["creation_attempted"] is True
    assert run["automatic_replacement_queued"] is False
    assert 0 < run["estimated_compute_cost_usd"] <= 0.05
    assert run["cleanup"]["owned_pod_absent"] is True
    assert final["status"] == "pass"
    assert final["post_retrieval_verification_byte_identical"] is True
    assert final["semantic_or_artifact_mismatches"] == 0
    assert final["all_predeclared_performance_gates_passed"] is False
    assert linux["single_root"]["gates"][
        "minimum_case_speedup_at_least_0_95"
    ] is False
    assert adjudication["replication_admissible"] is True
    assert adjudication["exactness_verified_on_both"] is True
    assert adjudication["guarded_opt_in_backend_retained"] is True
    assert adjudication["unqualified_per_case_performance_claim"] is False
    assert adjudication["selector_training_justified"] is False
    assert adjudication["production_promotion"] is False


def test_c38_on_pod_verification_replays_byte_identically() -> None:
    manifest = load(HERE / "c38_linux_upload_manifest.json")
    replayed_c37, replayed_c38 = replay_verifiers(manifest)

    assert replayed_c37 == load(REMOTE / "independent_verification.json")
    assert replayed_c38 == load(REMOTE / "c38_independent_verification.json")
