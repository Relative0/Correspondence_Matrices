from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_module():
    path = ROOT / "docs/video_factory/foundational_cm_corrections_v3.py"
    spec = importlib.util.spec_from_file_location("foundational_cm_corrections_v3", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_candidate_contracts_keep_retrieval_and_caption_limits() -> None:
    module = load_module()
    manifest = module.build_contracts()
    assert manifest["status"] == "bounded_local_preview_ready_full_render_not_authorized"
    assert manifest["limits"] == {
        "width": 960, "height": 540, "fps": 15,
        "stills": 22, "clips": 7, "clip_seconds": 70, "workers": 2,
    }
    assert [item["video_id"] for item in manifest["episodes"]] == list(module.SCRIPT_PATHS)
    for item in manifest["episodes"]:
        root = module.PACKAGE / "episodes" / item["video_id"]
        narration = json.loads((root / "NARRATION_CONTRACT_V3.json").read_text(encoding="utf-8"))
        captions = json.loads((root / "CAPTION_CONTRACT_V3.json").read_text(encoding="utf-8"))
        pauses = [cue for cue in narration["cues"] if cue["kind"] == "pause"]
        assert len(pauses) == 1
        assert pauses[0]["end_s"] - pauses[0]["start_s"] == 4
        assert narration["audio_generated"] is False
        assert all(
            len(cue["text"].splitlines()) <= 2
            and max(map(len, cue["text"].splitlines())) <= 42
            and cue["end_s"] - cue["start_s"] <= 6.001
            and cue["characters_per_second"] <= 20
            for cue in captions["cues"]
        )


def test_corrected_matrix_and_real_rectangle_geometry_are_encoded() -> None:
    module = load_module()
    title, order = module.body("l_order")
    assert "WY 10" in order and "WY 01" in order
    assert "WXYZ=0111" in order and "implication = 0" in order
    _, modifier = module.body("l_modifier")
    for term in ("A⊗B", "¬A⊗B", "¬A⊗¬B", "1100"):
        assert term in modifier
    _, rectangles = module.body("r_repartition")
    bits = "".join(re.findall(r'<i class="bit(?: selected)?"[^>]*>([01])</i>', rectangles))
    assert bits == "0111011101111000" + "0111011101111000" + "0111011101111000"
    assert all(row in rectangles for row in ("ABC 000", "ABC 111"))
    assert "8×2" not in rectangles  # geometry and headers carry the shape; no fake shape card
    _, operator_motion = module.body("o_dyad_implication")
    assert 'data-segment="dyad"' in operator_motion
    assert 'data-segment="implication"' in operator_motion
    assert "|1⟩⟨0|" in operator_motion and "zero moves to XY=01" in operator_motion


def test_preview_scope_is_exactly_bounded() -> None:
    module = load_module()
    assert len(module.STILLS) == 22
    assert len(module.CLIPS) == 7
    assert sum(duration for _, _, duration in module.CLIPS) == 70
    assert module.CLIPS[-1] == (
        "operator_outer_product_and_zero_move", "o_dyad_implication", 10
    )
    assert module.WIDTH == 960 and module.HEIGHT == 540 and module.FPS == 15
