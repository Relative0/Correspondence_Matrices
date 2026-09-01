from __future__ import annotations

import json
import sys
from pathlib import Path


FACTORY_ROOT = Path(__file__).resolve().parents[1]
if str(FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(FACTORY_ROOT))

import deep_series_chapter_compiler as compiler


def load(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def test_wp1_manifest_covers_every_episode_chapter_scene_beat_and_cue():
    manifest = load(compiler.WP1_ROOT / "chapter_render_contract_manifest.json")
    assert manifest["status"] == "wp1_complete_local_review_required"
    assert manifest["episode_count"] == 51
    assert manifest["chapter_count"] == 203
    assert manifest["scene_count"] == 1332
    assert manifest["beat_count"] == 6307
    assert manifest["cue_count"] == 3648
    assert len(manifest["contracts"]) == 203


def test_wp1_contracts_are_nonremote_and_frame_contiguous():
    manifest = load(compiler.WP1_ROOT / "chapter_render_contract_manifest.json")
    assert manifest["remote_or_paid_work_authorized"] is False
    for item in manifest["contracts"]:
        contract = load(compiler.REPO_ROOT / item["path"])
        assert contract["remote_or_paid_work_authorized"] is False
        frame = contract["frame_contract"]
        assert frame["duration_frames"] == frame["chapter_end_frame"] - frame["chapter_start_frame"]
        expected = frame["chapter_start_frame"]
        for scene in contract["resolved_scenes"]:
            assert scene["start_frame"] == expected
            assert scene["duration_frames"] == scene["end_frame"] - scene["start_frame"]
            expected = scene["end_frame"]
        assert expected == frame["chapter_end_frame"]


def test_wp1_uses_only_explicit_visual_system_mappings():
    manifest = load(compiler.WP1_ROOT / "chapter_render_contract_manifest.json")
    assert manifest["visual_system_mapping"] == compiler.VISUAL_SYSTEM_TO_POP_VISUAL
    for item in manifest["contracts"]:
        contract = load(compiler.REPO_ROOT / item["path"])
        for scene in contract["resolved_scenes"]:
            assert scene["visual_system"] in compiler.VISUAL_SYSTEM_TO_POP_VISUAL
            assert scene["primitive"] == compiler.VISUAL_SYSTEM_TO_POP_VISUAL[scene["visual_system"]]


def test_wp1_viewer_copy_excludes_internal_scaffolding_and_truncation():
    manifest = load(compiler.WP1_ROOT / "chapter_render_contract_manifest.json")
    for item in manifest["contracts"]:
        contract = load(compiler.REPO_ROOT / item["path"])
        for scene in contract["resolved_scenes"]:
            pop_scene = scene["pop_scene"]
            compiler.assert_viewer_copy_is_clean(
                pop_scene,
                f"{contract['video_id']}.{contract['chapter_id']}.{scene['scene_id']}",
            )
            assert scene["composition_id"] not in pop_scene["data"]["title"]
