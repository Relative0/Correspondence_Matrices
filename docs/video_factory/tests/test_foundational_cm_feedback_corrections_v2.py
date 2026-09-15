from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_module():
    path = ROOT / "docs/video_factory/foundational_cm_feedback_corrections_v2.py"
    spec = importlib.util.spec_from_file_location("foundational_cm_feedback_corrections_v2", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_logical_tensor_is_complete_and_unambiguous() -> None:
    module = load_module()
    logical = module.logical_body()
    assert "[[M<sub>WX</sub>] ⊗ [M<sub>YZ</sub>]] = [M<sub>WXYZ</sub>]" in logical
    assert logical.count("data-lm-cell=") == 16
    assert logical.count("block-cell") == 4
    assert "top-left entry of [M<sub>WX</sub>] is WX" in logical
    assert "WX × [M<sub>YZ</sub>] fills this 2×2 block" in logical
    assert "row components: (W,Y)" in logical
    assert "column components: (X,Z)" in logical
    assert "paper measurement:" in logical
    assert "╲" not in logical and "\\(X,Z)" not in logical


def test_repository_examples_are_correct_and_fill_the_frame() -> None:
    module = load_module()
    repository = module.repository_body()
    assert repository.count("data-repo-cell=") == 16
    for expected in ("1⇕1=0 → cell (3,2)", "(2,3): 0⇕1=1", "(1,0): 0⇕0=0"):
        assert expected in repository
    assert "1110 → row? column? output?" in repository
    assert repository.count("data-step=") == 3
    assert "⊕" not in repository
    assert "white-space:nowrap" in module.css("sans", "mono")
    assert "grid-template-rows:300px 102px" in module.css("sans", "mono")


def test_feedback_scope_is_focused() -> None:
    module = load_module()
    assert len(module.STILLS) == 9
    assert module.CLIPS == [
        ("logical_valuation_and_block_v3", "logical_block_v3", 14),
        ("repository_retrieval_v3", "repository_retrieval_v3", 14),
    ]
    assert module.WIDTH == 960 and module.HEIGHT == 540 and module.FPS == 15


def test_successor_scripts_parse_into_complete_scene_cues() -> None:
    module = load_module()
    for path, duration in (
        (module.OPERATOR_ROOT / "SCRIPT_V5.md", 198),
        (module.LOGICAL_ROOT / "SCRIPT_V6.md", 265),
        (module.REPOSITORY_ROOT / "SCRIPT_V7.md", 218),
    ):
        scenes = module.BASE.LEGACY.parse_script(path)
        cue_groups = module.BASE.split_script_cues(path, scenes)
        assert len(scenes) == len(cue_groups) == 7
        assert scenes[-1]["end_s"] == duration
        assert sum(len(group) for group in cue_groups) >= 39
