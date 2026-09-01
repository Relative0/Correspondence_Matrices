from __future__ import annotations

import json
from pathlib import Path
import sys


RUNPOD_ROOT = Path(__file__).resolve().parents[1]
if str(RUNPOD_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNPOD_ROOT))

import deep_series_first5_authorize as authorize
import deep_series_first5_execute as execute
import deep_series_first5_package as package
import deep_series_first5_proposal as proposal


def load(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def test_first5_bundle_and_proposal_are_current_and_bounded():
    package.validate()
    proposal.validate()
    record = load(package.OUTPUT_ROOT / "bundle_record.json")
    frozen = load(proposal.ROOT / "proposal.json")
    assert len(record["ordered_job_ids"]) == 17
    assert record["total_frames"] == 68399
    assert frozen["proposal_id"] == proposal.PROPOSAL_ID
    assert frozen["content_identity"]["scope"] == "first_five_only"
    assert frozen["remote_or_paid_work_authorized"] is False
    assert frozen["authorization_ceiling"]["maximum_total_runpod_spend_usd"] == 2.0
    assert frozen["authorization_ceiling"]["maximum_pod_creates"] == 1
    assert frozen["authorization_ceiling"]["maximum_parallel_pods"] == 1
    assert frozen["render_contract"]["audio"] is False


def test_exact_approval_recorder_binds_content_proposal_and_file(tmp_path, monkeypatch):
    content_path = tmp_path / "approval.json"
    authorization_path = tmp_path / "authorization.json"
    monkeypatch.setattr(authorize, "CONTENT_APPROVAL_PATH", content_path)
    monkeypatch.setattr(authorize, "AUTHORIZATION_PATH", authorization_path)
    request = authorize.current_request()
    result = authorize.record(
        bible_content_hash=request["bible_content_hash"],
        review_manifest_sha256=request["review_manifest_sha256"],
        proposal_identity=request["proposal_identity"],
        approved_by="Brian",
        approved_at="2026-08-31T22:00:00+07:00",
    )
    authorize.validate()
    content = load(content_path)
    assert content["content_approval_authorizes_remote_or_paid_work"] is False
    assert result["remote_or_paid_work_authorized"] is True
    assert result["maximum_total_runpod_spend_usd"] == 2.0
    assert result["maximum_pod_creates"] == 1
    assert result["proposal_identity"] == request["proposal_identity"]
    assert result["proposal_file_sha256"] == request["proposal_file_sha256"]
    assert result["approval_text"] == request["approval_text"]


def test_first5_execution_wrapper_sets_exact_scope():
    execute.configure()
    assert execute.controller.SMOKE_ROOT == package.OUTPUT_ROOT
    assert execute.controller.PROPOSAL_ID == proposal.PROPOSAL_ID
    assert execute.controller.TOTAL_CAP == 2.0
    assert execute.controller.MAX_CREATES == 1
    assert execute.controller.MAX_RUNTIME_SECONDS == 21600
    assert len(execute.controller.EXPECTED_JOBS) == 17
    assert execute.controller.POD_NAME_PREFIX == "cm-video-first5-production-v1-"
    assert execute.controller.APPROVAL_SCOPE == "production_planning_for_first_five_only"
