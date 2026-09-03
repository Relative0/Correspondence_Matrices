from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_comparison_execution_20260903"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _controller():
    path = ROOT / "scripts/runpod_architecture_comparison_controller.py"
    spec = importlib.util.spec_from_file_location("architecture_comparison_controller_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_package_is_exactly_bound_and_non_authorizing():
    manifest = _load(HERE / "UPLOAD_MANIFEST.json")
    contract = _load(HERE / "EXECUTION_CONTRACT.json")
    validation = _load(HERE / "LOCAL_PACKAGE_VALIDATION.json")
    request = _load(HERE / "RUNPOD_AUTHORIZATION_REQUEST_20260903.json")

    assert manifest["authorization_status"] == "upload_not_authorized_exact_approval_pending"
    assert manifest["file_count"] == len(manifest["files"]) == 55
    assert manifest["bytes"] == sum(row["bytes"] for row in manifest["files"])
    for row in manifest["files"]:
        source = ROOT.joinpath(*Path(row["source"]).parts)
        assert source.stat().st_size == row["bytes"]
        assert _sha256(source) == row["sha256"]

    assert contract["status"] == "prepared_not_authorized"
    assert contract["schedule"]["total_cells"] == 19_646
    assert contract["schedule"]["lane_cells"] == {
        "A": 10_880, "B": 6_912, "C": 384, "D": 1_470,
    }
    assert validation["status"] == "pass"
    assert validation["manifest_sha256"] == _sha256(HERE / "UPLOAD_MANIFEST.json")
    assert validation["timing_evidence_produced"] is False
    assert validation["decision_bearing_result_produced"] is False
    assert request["status"] == "exact_user_authorization_required_not_granted"
    assert request["authorization"] == {
        "granted": False, "prior_c38_authorization_reused": False, "record_created": False,
    }
    assert request["resource_and_cost_boundary"]["total_cost_cap_usd"] == 0.05


def test_declared_refusal_count_matches_the_frozen_schedule():
    freeze = _load(ROOT / "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json")
    oracles = _load(HERE / "ORACLES.json")
    refused = 0
    a = freeze["schedules"]["A"]
    refused += sum(
        oracles["lanes"]["A"][case_id]["status"] == "refused"
        for case_id in a["case_order"]
    ) * a["blocks"] * len(a["arms"])
    for name, schedule in freeze["schedules"]["D"]["task_sublanes"].items():
        refused += sum(
            oracles["lanes"]["D"][case_id]["status"] == "refused"
            for case_id in schedule["case_order"]
        ) * schedule["blocks"] * len(schedule["arms"])
    structural = freeze["schedules"]["D"]["structural_reload"]
    refused += sum(
        oracles["lanes"]["D"][case_id]["status"] == "refused"
        for case_id in structural["case_order"]
    ) * structural["blocks"] * len(structural["arms"])
    request = _load(HERE / "RUNPOD_AUTHORIZATION_REQUEST_20260903.json")
    assert refused == request["scope"]["expected_counts"]["refused"] == 1_736
    assert 19_646 - refused == request["scope"]["expected_counts"]["ok"] == 17_910


def test_controller_remote_program_compiles_and_authorization_gate_is_closed():
    controller = _controller()
    compile(controller.base.REMOTE_CODE, "<architecture-comparison-remote>", "exec")
    compile(controller.INSTALL_CODE, "<architecture-comparison-install>", "exec")
    assert "architecture-comparison-campaign" in controller.base.REMOTE_CODE
    assert "architecture-comparison-verification" in controller.base.REMOTE_CODE
    assert "--max-seconds', '420'" in controller.base.REMOTE_CODE
    assert controller.RESULT_CAP_BYTES == 48 << 20
    assert not controller.AUTHORIZATION.exists()
    with pytest.raises(FileNotFoundError):
        controller.require_authorization()
