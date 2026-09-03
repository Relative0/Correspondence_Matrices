from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
FREEZE = ROOT / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904/FREEZE.json"
ATTEMPT = ROOT / "docs/recognition/architecture_query_ladder_followup_execution_20260903/ATTEMPT_001_STATUS.json"
AUTHORIZATION = (
    HERE / "RUNPOD_ARCHITECTURE_QUERY_LADDER_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_09_04.json"
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _controller():
    path = ROOT / "scripts/runpod_architecture_query_ladder_retry_002_controller.py"
    spec = importlib.util.spec_from_file_location("query_ladder_retry_002_controller_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_retry_package_is_source_exact_and_non_authorizing() -> None:
    manifest = _load(HERE / "UPLOAD_MANIFEST.json")
    contract = _load(HERE / "EXECUTION_CONTRACT.json")
    validation = _load(HERE / "LOCAL_PACKAGE_VALIDATION.json")
    request = _load(HERE / "RUNPOD_RETRY_002_AUTHORIZATION_REQUEST_20260904.json")
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
    assert contract["cleanup"] == freeze["measurement_contract"]["cleanup"]
    assert contract["cleanup"]["method"] == "cache_clear_then_isolated_child_exit"
    assert contract["cleanup"]["gc_collect_in_fork_child"] is False
    assert contract["timing_isolation"]["isolation_lifecycle_reported_separately"] is True
    assert contract["limits"]["workload_wall_seconds"] == 420
    assert contract["limits"]["cleanup_seconds"] == 600

    assert validation["status"] == "pass"
    assert validation["manifest_sha256"] == _sha256(HERE / "UPLOAD_MANIFEST.json")
    assert validation["parent_and_followup_freeze_verification_passed"] is True
    assert validation["pythonpath_injected"] is False
    assert validation["timing_evidence_produced"] is False
    assert validation["memory_evidence_produced"] is False
    assert validation["decision_bearing_result_produced"] is False

    assert request["status"] == "exact_user_authorization_required_not_granted"
    assert request["authorization"] == {
        "granted": False, "prior_authorization_reused": False, "record_created": False,
    }
    assert request["resource_and_cost_boundary"]["total_cost_cap_usd"] == 0.04
    assert request["resource_and_cost_boundary"]["cumulative_hard_ceiling_usd"] == 0.05
    assert request["prior_attempt"]["status_sha256"] == _sha256(ATTEMPT)
    assert request["prior_attempt"]["authorization_reused"] is False


def test_retry_controller_compiles_and_accepts_only_the_exact_authorization() -> None:
    retry = _controller()
    compile(retry.base.REMOTE_CODE, "<query-ladder-retry-002-remote>", "exec")
    assert retry.RUN_NAME in retry.base.REMOTE_CODE
    assert "architecture-query-ladder-linux-gcc-20260903-001" not in retry.base.REMOTE_CODE
    assert retry.shared.CAMPAIGN_CAP == 0.04
    assert retry.AUTHORIZATION == AUTHORIZATION
    authorization = retry.require_authorization()
    assert authorization["schema"] == (
        "cm-runpod-architecture-query-ladder-retry-002-exact-payload-authorization/v1"
    )
    assert authorization["authorized"] is True
    assert authorization["authorization_request_sha256"] == _sha256(
        HERE / "RUNPOD_RETRY_002_AUTHORIZATION_REQUEST_20260904.json"
    )
    assert authorization["total_cost_cap_usd"] == 0.04
    assert authorization["cumulative_hard_ceiling_usd"] == 0.05
    assert authorization["prior_authorization_reused"] is False


def test_retry_request_binds_controller_transport_and_package() -> None:
    request = _load(HERE / "RUNPOD_RETRY_002_AUTHORIZATION_REQUEST_20260904.json")
    retry = _controller()
    controller_path = ROOT / "scripts/runpod_architecture_query_ladder_retry_002_controller.py"
    assert request["controller_sha256"] == _sha256(controller_path)
    assert request["transport_sources"] == retry.transport_source_identities()
    assert request["freeze_sha256"] == _sha256(FREEZE)
    assert request["upload_manifest_sha256"] == _sha256(HERE / "UPLOAD_MANIFEST.json")
    assert request["local_validation_sha256"] == _sha256(HERE / "LOCAL_PACKAGE_VALIDATION.json")
