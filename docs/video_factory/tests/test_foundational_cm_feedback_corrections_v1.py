from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_module():
    path = ROOT / "docs/video_factory/foundational_cm_feedback_corrections_v1.py"
    spec = importlib.util.spec_from_file_location("foundational_cm_feedback_corrections_v1", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_logical_tensor_is_complete_and_unambiguous() -> None:
    module = load_module()
    logical = module.logical_body()
    assert "M<sub>WX</sub> ⊗ M<sub>YZ</sub> = M<sub>WXYZ</sub>" in logical
    assert logical.count("data-lm-cell=") == 16
    assert logical.count("block-cell") == 4
    assert "WX × M<sub>YZ</sub> fills the highlighted 2×2 block" in logical


def test_repository_examples_are_correct_and_fill_the_frame() -> None:
    module = load_module()
    repository = module.repository_body()
    assert repository.count("data-repo-cell=") == 16
    for expected in ("(3,2): 1⊕1=0", "(2,3): 0⊕1=1", "(1,0): 0⊕0=0"):
        assert expected in repository
    assert "F(1110) → output?" in repository
    assert "white-space:nowrap" in module.css("sans", "mono")
    assert "grid-template-rows:285px 125px" in module.css("sans", "mono")


def test_feedback_scope_is_focused() -> None:
    module = load_module()
    assert len(module.STILLS) == 7
    assert module.CLIPS == [
        ("logical_valuation_and_block_v2", "logical_block_v2", 14),
        ("repository_retrieval_v2", "repository_retrieval_v2", 14),
    ]
    assert module.WIDTH == 960 and module.HEIGHT == 540 and module.FPS == 15


def test_successor_scripts_parse_into_complete_scene_cues() -> None:
    module = load_module()
    for path, duration in (
        (module.LOGICAL_ROOT / "SCRIPT_V5.md", 265),
        (module.REPOSITORY_ROOT / "SCRIPT_V6.md", 218),
    ):
        scenes = module.BASE.LEGACY.parse_script(path)
        cue_groups = module.BASE.split_script_cues(path, scenes)
        assert len(scenes) == len(cue_groups) == 7
        assert scenes[-1]["end_s"] == duration
        assert sum(len(group) for group in cue_groups) > 40
