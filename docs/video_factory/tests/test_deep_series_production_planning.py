from __future__ import annotations

import json
from pathlib import Path
import sys


FACTORY_ROOT = Path(__file__).resolve().parents[1]
if str(FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(FACTORY_ROOT))

import deep_series_production_planning as planning


DEEP_ROOT = FACTORY_ROOT / "deep_series"
PLANNING_ROOT = DEEP_ROOT / "production_planning"


def load(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def test_superseded_planning_is_preserved_as_history():
    history_root = PLANNING_ROOT / "history"
    archives = sorted(path for path in history_root.iterdir() if path.is_dir())
    assert archives
    archive = archives[-1]
    approval = load(archive / "content_approval.json")
    manifest = load(archive / "archive_manifest.json")
    assert manifest["status"] == "historical_content_approval_superseded"
    assert manifest["approval_identity"] == approval["approval_identity"]
    assert approval["content_approval_authorizes_remote_or_paid_work"] is False
    for name in (
        "routing_manifest.json",
        "render_benchmark_plan.json",
        "production_readiness_audit.json",
        "bundle_allowlist_draft.json",
        "runpod_proposal_status.json",
        "renderer_primitive_smoke_results.json",
    ):
        assert load(archive / name)["remote_or_paid_work_authorized"] is False


def test_current_revision_has_scoped_first_five_review_without_inherited_approval():
    bible = load(DEEP_ROOT / "episode_content_bible.json")
    assert bible["approval_gate"]["status"] == "not_requested"
    assert bible["approval_gate"]["approval_identity"] is None
    assert not (PLANNING_ROOT / "content_approval.json").exists()
    assert not (DEEP_ROOT / "content_review_request.json").exists()
    manifest = load(DEEP_ROOT / "first_five_review" / "manifest.json")
    assert manifest["status"] == "review_requested_first_five_only"
    assert manifest["bible_content_hash"] == bible["content_hash"]
    assert manifest["episode_count"] == 5
    assert manifest["chapter_count"] == 17
    assert manifest["remote_or_paid_work_authorized"] is False


def test_planner_recognizes_every_wp1_contract_as_executable():
    bible = load(DEEP_ROOT / "episode_content_bible.json")
    chapters = [
        chapter
        for episode in bible["episodes"]
        for chapter in planning.chapter_inventory(episode["video_id"])
    ]
    assert len(chapters) == 203
    assert all(chapter["executable_render_payload"] for chapter in chapters)
    assert all(chapter["executable_render_contract_path"] for chapter in chapters)


def test_superseded_review_packet_is_preserved_as_history():
    history_root = DEEP_ROOT / "content_review_history"
    archives = sorted(path for path in history_root.iterdir() if path.is_dir())
    assert archives
    archive = archives[-1]
    manifest = load(archive / "archive_manifest.json")
    request = load(archive / "content_review_request.json")
    assert manifest["status"] == "historical_content_review_superseded"
    assert manifest["review_manifest_sha256"] == request["review_manifest_sha256"]
    assert (archive / "content_review_packet" / "manifest.json").is_file()
