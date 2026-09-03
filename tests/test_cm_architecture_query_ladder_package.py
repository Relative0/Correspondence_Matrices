from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_query_ladder_followup_execution_20260903"
FREEZE = ROOT / "docs/recognition/architecture_query_ladder_followup_freeze_20260903/FREEZE.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _controller():
    path = ROOT / "scripts/runpod_architecture_query_ladder_controller.py"
    spec = importlib.util.spec_from_file_location("query_ladder_controller_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_package_is_exactly_bound_and_non_authorizing() -> None:
    manifest = _load(HERE / "UPLOAD_MANIFEST.json")
    contract = _load(HERE / "EXECUTION_CONTRACT.json")
    validation = _load(HERE / "LOCAL_PACKAGE_VALIDATION.json")
    request = _load(HERE / "RUNPOD_AUTHORIZATION_REQUEST_20260903.json")

    assert manifest["authorization_status"] == "upload_not_authorized_exact_approval_pending"
    assert manifest["file_count"] == len(manifest["files"]) == 70
    assert manifest["bytes"] == sum(row["bytes"] for row in manifest["files"])
    freeze = _load(FREEZE)
    assert {row["path"] for row in freeze["source_closure"]} <= {
        row["source"] for row in manifest["files"]
    }
    for row in manifest["files"]:
        source = ROOT.joinpath(*Path(row["source"]).parts)
        assert source.stat().st_size == row["bytes"]
        assert _sha256(source) == row["sha256"]

    assert contract["status"] == "prepared_not_authorized"
    assert contract["schedule"] == {
        "arms": 8,
        "cells_per_query_count": 6_912,
        "counterbalance_blocks": 16,
        "expected_counts": {"failed": 0, "ok": 27_648, "refused": 0},
        "query_counts": [1, 4, 16, 64],
        "runnable_cases": 54,
        "total_cells": 27_648,
    }
    assert contract["memory"]["method"] == "isolated_fork_child_wait4_ru_maxrss/v1"
    assert validation["status"] == "pass"
    assert validation["manifest_sha256"] == _sha256(HERE / "UPLOAD_MANIFEST.json")
    assert validation["parent_and_followup_freeze_verification_passed"] is True
    assert validation["pythonpath_injected"] is False
    assert validation["timing_evidence_produced"] is False
    assert validation["memory_evidence_produced"] is False
    assert validation["decision_bearing_result_produced"] is False
    assert request["status"] == "exact_user_authorization_required_not_granted"
    assert request["scope"]["query_rows"] == {
        "1": 6_912, "4": 6_912, "16": 6_912, "64": 6_912,
    }
    assert request["authorization"] == {
        "granted": False, "prior_authorization_reused": False, "record_created": False,
    }
    assert request["resource_and_cost_boundary"]["total_cost_cap_usd"] == 0.05


def test_controller_remote_program_compiles_and_requires_fresh_authorization() -> None:
    controller = _controller()
    compile(controller.base.REMOTE_CODE, "<architecture-query-ladder-remote>", "exec")
    compile(controller.INSTALL_CODE, "<architecture-query-ladder-install>", "exec")
    assert "architecture-query-ladder-campaign" in controller.base.REMOTE_CODE
    assert "architecture-query-ladder-verification" in controller.base.REMOTE_CODE
    assert "--max-seconds', '420'" in controller.base.REMOTE_CODE
    assert controller.TOTAL_ROWS == 27_648
    assert controller.QUERY_ROWS == {"1": 6_912, "4": 6_912, "16": 6_912, "64": 6_912}
    assert controller.RESULT_CAP_BYTES == 48 << 20
    assert controller.AUTHORIZATION.exists() is False
    with pytest.raises(FileNotFoundError):
        controller.require_authorization()


def test_request_binds_every_controller_transport_source() -> None:
    request = _load(HERE / "RUNPOD_AUTHORIZATION_REQUEST_20260903.json")
    controller = _controller()
    assert request["controller_sha256"] == _sha256(
        ROOT / "scripts/runpod_architecture_query_ladder_controller.py"
    )
    assert request["transport_sources"] == controller.transport_source_identities()
    assert request["freeze_sha256"] == _sha256(FREEZE)
    assert request["upload_manifest_sha256"] == _sha256(HERE / "UPLOAD_MANIFEST.json")
    assert request["local_validation_sha256"] == _sha256(HERE / "LOCAL_PACKAGE_VALIDATION.json")
