from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_module():
    path = ROOT / "docs/video_factory/foundational_cm_seven_clip_assembly_v1.py"
    spec = importlib.util.spec_from_file_location("foundational_cm_seven_clip_assembly_v1", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_timeline_has_seven_clips_in_teaching_order() -> None:
    module = load_module()
    assert [clip["id"] for clip in module.CLIPS] == [
        "operator_outer_product_and_zero_move",
        "operator_retrieval",
        "logical_valuation_and_block",
        "logical_order_and_modifier",
        "logical_retrieval",
        "repository_retrieval",
        "repository_repartition",
    ]
    assert sum(clip["duration_s"] for clip in module.CLIPS) == 78


def test_tensor_callout_is_absent_but_full_matrix_remains() -> None:
    module = load_module()
    sans, mono = module.BASE.font_data()
    page = module.corrected_page(module.CLIPS[2], sans, mono)
    assert "class=\"block-note\"" not in page
    assert "top-left entry of [M<sub>WX</sub>] is WX" not in page
    assert page.count("data-lm-cell=") == 16
    assert page.count('class="block-cell"') == 4


def test_all_rendered_pages_use_canonical_exclusive_or() -> None:
    module = load_module()
    sans, mono = module.BASE.font_data()
    pages = [module.corrected_page(clip, sans, mono) for clip in module.CLIPS]
    assert all("⊕" not in page and "\\oplus" not in page for page in pages)
    assert any("⇕" in page for page in pages)


def test_repository_page_keeps_progressive_trace() -> None:
    module = load_module()
    sans, mono = module.BASE.font_data()
    page = module.corrected_page(module.CLIPS[5], sans, mono)
    for expected in ("1 · split", "2 · index", "3 · evaluate", "data-row-header", "data-col-header"):
        assert expected in page
