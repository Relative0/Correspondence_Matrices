from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


FACTORY_ROOT = Path(__file__).resolve().parents[1]
if str(FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(FACTORY_ROOT))

import deep_series_authoring as authoring


def load(relative: str):
    return json.loads((FACTORY_ROOT / relative).read_text("utf-8"))


def test_all_51_authored_packages_pass_semantic_validation():
    authoring.validate()
    bible = load("deep_series/episode_content_bible.json")
    assert len(bible["episodes"]) == 51
    assert all((authoring.EPISODES_ROOT / item["video_id"] / "script.md").is_file() for item in bible["episodes"])


def test_authoring_schemas_are_strict_and_reject_missing_content():
    value = load("deep_series/episodes/conceptual-vs-measured/narration_contract.json")
    changed = copy.deepcopy(value)
    changed["unexpected"] = True
    with pytest.raises(authoring.DeepSeriesError, match="Additional properties"):
        authoring.validate_with("deep_narration_contract.schema.json", changed)
    changed = copy.deepcopy(value)
    changed["cues"] = []
    with pytest.raises(authoring.DeepSeriesError, match="too short"):
        authoring.validate_with("deep_narration_contract.schema.json", changed)


def test_late_and_cyclic_prerequisites_are_rejected():
    bible = load("deep_series/episode_content_bible.json")
    late = copy.deepcopy(bible)
    late["episodes"][0]["prerequisite_ids"] = [late["episodes"][1]["video_id"]]
    with pytest.raises(authoring.DeepSeriesError, match="late-or-cyclic"):
        authoring.validate_prerequisites(late)
    cyclic = copy.deepcopy(bible)
    cyclic["episodes"][1]["prerequisite_ids"] = [cyclic["episodes"][2]["video_id"]]
    with pytest.raises(authoring.DeepSeriesError, match="late-or-cyclic"):
        authoring.validate_prerequisites(cyclic)


def test_duration_cue_scene_and_visual_budgets_agree():
    bible = load("deep_series/episode_content_bible.json")
    for episode in bible["episodes"]:
        root = authoring.EPISODES_ROOT / episode["video_id"]
        narration = json.loads((root / "narration_contract.json").read_text("utf-8"))
        storyboard = json.loads((root / "storyboard.json").read_text("utf-8"))
        assert narration["duration_target_s"] == storyboard["duration_s"]
        assert storyboard["composition_count"] >= episode["visual_contract"]["minimum_distinct_compositions"]
        assert storyboard["meaningful_state_change_count"] >= episode["visual_contract"]["minimum_meaningful_state_changes"]
        assert all(scene["beats"] for scene in storyboard["scenes"])


def test_claim_bindings_have_current_hashes_and_exact_locators():
    sources = {item["id"]: item for item in load("source_registry.json")["sources"]}
    bible = load("deep_series/episode_content_bible.json")
    for episode in bible["episodes"]:
        claim_map = json.loads((authoring.EPISODES_ROOT / episode["video_id"] / "claim_map.json").read_text("utf-8"))
        for binding in claim_map["bindings"]:
            for claim in binding["claims"]:
                assert claim["sources"]
                for ref in claim["sources"]:
                    assert ref["locator"]
                    assert ref["sha256"] == sources[ref["source_id"]]["sha256"]


def test_invalid_locator_empty_scene_and_illegal_route_fail_schemas():
    claim_map = load("deep_series/episodes/conceptual-vs-measured/claim_map.json")
    changed_claim_map = copy.deepcopy(claim_map)
    binding = next(item for item in changed_claim_map["bindings"] if item["claims"])
    binding["claims"][0]["sources"][0]["locator"] = ""
    with pytest.raises(authoring.DeepSeriesError, match="should be non-empty"):
        authoring.validate_with("deep_claim_map.schema.json", changed_claim_map)

    storyboard = load("deep_series/episodes/conceptual-vs-measured/storyboard.json")
    changed_storyboard = copy.deepcopy(storyboard)
    changed_storyboard["scenes"][0]["beats"] = []
    with pytest.raises(authoring.DeepSeriesError, match="non-empty"):
        authoring.validate_with("deep_storyboard.schema.json", changed_storyboard)

    plan = load("deep_series/episodes/conceptual-vs-measured/production_plan.json")
    changed_plan = copy.deepcopy(plan)
    changed_plan["remote_route"] = "runpod"
    with pytest.raises(authoring.DeepSeriesError, match="was expected"):
        authoring.validate_with("deep_production_plan.schema.json", changed_plan)


def test_caption_text_fits_and_generic_direction_is_absent():
    bible = load("deep_series/episode_content_bible.json")
    banned = ("show boxes", "add diagram later", "<todo>", "tbd")
    for episode in bible["episodes"]:
        root = authoring.EPISODES_ROOT / episode["video_id"]
        narration = json.loads((root / "narration_contract.json").read_text("utf-8"))
        assert max(authoring.words(item["text"]) for item in narration["cues"]) <= 58
        text = (root / "script.md").read_text("utf-8").lower()
        assert not any(value in text for value in banned)


def test_preview_assets_are_hash_bound_and_reviewable():
    bible = load("deep_series/episode_content_bible.json")
    for episode in bible["episodes"]:
        root = authoring.EPISODES_ROOT / episode["video_id"]
        assets = json.loads((root / "asset_manifest.json").read_text("utf-8"))
        by_kind = {item["kind"]: item for item in assets["assets"]}
        assert by_kind["storyboard-contact-sheet"]["width"] == 1920
        assert by_kind["storyboard-contact-sheet"]["height"] == 776
        assert by_kind["low-resolution-animatic"]["width"] == 640
        assert by_kind["low-resolution-animatic"]["height"] == 360
        for item in assets["assets"]:
            path = authoring.REPO_ROOT / item["path"]
            assert path.is_file()
            assert authoring.file_sha256(path) == item["sha256"]


def test_editorial_quality_rejects_repeated_padding_and_fake_visual_counts():
    bible = load("deep_series/episode_content_bible.json")
    for episode in bible["episodes"]:
        root = authoring.EPISODES_ROOT / episode["video_id"]
        narration = json.loads((root / "narration_contract.json").read_text("utf-8"))
        storyboard = json.loads((root / "storyboard.json").read_text("utf-8"))
        editorial = json.loads((root / "editorial_audit.json").read_text("utf-8"))
        spoken = [" ".join(item["text"].casefold().split()) for item in narration["cues"] if item["spoken"]]
        assert len(spoken) == len(set(spoken))
        assert not any(phrase in text for text in spoken for phrase in authoring.GENERIC_FILLER_PHRASES)
        beats = [beat for scene in storyboard["scenes"] for beat in scene["beats"]]
        assert len(beats) == storyboard["meaningful_state_change_count"]
        assert len({item["state_change"].casefold() for item in beats}) == len(beats)
        assert max(item["end_s"] - item["start_s"] for item in beats) <= 8.001
        assert editorial["duplicate_spoken_cues"] == 0
        assert editorial["generic_filler_cues"] == 0
        assert editorial["duplicate_state_changes"] == 0


def test_preview_briefs_are_diagram_led_not_passive_card_rows():
    bible = load("deep_series/episode_content_bible.json")
    for episode in bible["episodes"]:
        brief = load(f"deep_series/episodes/{episode['video_id']}/preview.renderer_brief.json")
        diagram_scenes = [
            item for item in brief["scenes"]
            if item["data"]["visual"] in {"transform_compare", "expression_matrix"}
        ]
        assert len(diagram_scenes) >= 5
    recognition = load("deep_series/episodes/recognition-c12-c16/preview.renderer_brief.json")
    node_labels = {
        node["label"]
        for scene in recognition["scenes"]
        for graph in scene["data"].get("graphs", [])
        for node in graph["nodes"]
    }
    assert {"Proposal", "Exact verify", "Witness", "Reject", "Fallback", "Promotion gate"} <= node_labels
