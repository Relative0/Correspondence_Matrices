from __future__ import annotations

import json
import sys
from pathlib import Path


FACTORY_ROOT = Path(__file__).resolve().parents[1]
if str(FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(FACTORY_ROOT))

import deep_series_chapter_compiler as compiler
import deep_series_pilot as pilot


def load(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def test_sparse_first_five_preflight_is_current_and_nonremote():
    pilot.validate()
    report = load(pilot.PILOT_ROOT / "sparse_visual_preflight.json")
    assert report["status"] == "first_five_sparse_visual_preflight_passed"
    assert report["remote_or_paid_work_authorized"] is False
    assert report["render_scope"] == "one settled 1080p frame per composition"
    assert report["video_count"] == 5
    assert report["scene_count"] == 93
    assert set(report["primitive_coverage"]) == pilot.EXPECTED_PRIMITIVES
    assert all(item["all_frames_passed"] for item in report["episodes"])
    assert all(item["unique_frame_hashes"] == item["scene_count"] for item in report["episodes"])


def test_first_five_contracts_use_the_required_visual_primitive_progression():
    expected = {
        "conceptual-vs-measured": {"transform_compare", "boundary", "result"},
        "why-boolean-computation": {"expression_matrix", "representation_compare", "boundary"},
        "expression-truth-function": {"expression_matrix", "representation_compare", "boundary"},
        "live-support-ambient": {"expression_matrix", "representation_compare", "boundary"},
        "what-is-explicit-cm": {"expression_matrix", "representation_compare", "boundary"},
    }
    assert tuple(expected) == pilot.PILOT_VIDEO_IDS
    for video_id, expected_primitives in expected.items():
        _, scenes = pilot.episode_brief(video_id)
        assert {scene["primitive"] for scene in scenes} == expected_primitives
        assert all(scene["primitive"] == compiler.VISUAL_SYSTEM_TO_POP_VISUAL[scene["visual_system"]] for scene in scenes)


def test_live_support_matrix_keeps_d_ambient_and_visibly_inert():
    _, scenes = pilot.episode_brief("live-support-ambient")
    matrices = [scene["pop_scene"]["data"] for scene in scenes if scene["primitive"] == "expression_matrix"]
    assert matrices
    for data in matrices:
        assert data["expression"] == "(A AND B) XOR C"
        assert data["live_variables"] == ["A", "B", "C"]
        assert data["ambient_variables"] == ["A", "B", "C", "D"]
        matrix = data["matrix"]
        assert matrix["row_labels"] == ["AB=00", "AB=01", "AB=10", "AB=11"]
        assert matrix["column_labels"] == ["CD=00", "CD=01", "CD=10", "CD=11"]
        rows = [matrix["bits"][start:start + 4] for start in range(0, 16, 4)]
        assert all(row[0] == row[1] and row[2] == row[3] for row in rows)
