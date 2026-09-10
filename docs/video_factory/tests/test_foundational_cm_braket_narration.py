from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_braket_scripts_and_renderer_contract() -> None:
    production = load_module(
        "foundational_cm_production",
        ROOT / "docs" / "video_factory" / "foundational_cm_production.py",
    )
    operator = production.parse_script(production.SCRIPT_PATHS["operator-cms-from-truth-tables"])
    logical = production.parse_script(production.SCRIPT_PATHS["logical-matrices-to-higher-dimensional-cms"])
    explicit = production.parse_script(production.SCRIPT_PATHS["what-is-explicit-cm"])

    assert [len(operator), len(logical), len(explicit)] == [7, 7, 7]
    assert [operator[-1]["end_s"], logical[-1]["end_s"], explicit[-1]["end_s"]] == [219, 265, 220]
    assert production.dyad_expression("1000") == "|1⟩⟨1|"
    assert production.dyad_expression("0110") == "|1⟩⟨0| ⊕ |0⟩⟨1|"
    assert production.dyad_expression("0000") == "0"
    table = production.operator_table_html()
    for label in ("AND", "OR", "XOR", "equivalence", "X→Y", "Y→X", "NAND", "NOR"):
        assert label in table
    for glyph in ("⟨", "⟩", "⊗", "⊕", "ᵀ"):
        assert glyph in production.SYMBOLS.values() or glyph in table


def test_retrieval_pause_is_machine_readable() -> None:
    production = load_module(
        "foundational_cm_production_pause",
        ROOT / "docs" / "video_factory" / "foundational_cm_production.py",
    )
    for video_id, path in production.SCRIPT_PATHS.items():
        scenes = production.parse_script(path)
        retrieval = [scene for scene in scenes if scene["title"] in {"Retrieval", "Read before naming", "Map one yourself"}]
        assert retrieval, video_id
        assert any(
            segment.get("kind") == "pause" and segment.get("duration_s") == 4.0
            for scene in retrieval for segment in scene["voice_segments"]
        )


def test_offline_neural_audition_and_pending_remote_proposal() -> None:
    package = ROOT / "docs" / "video_factory" / "deep_series" / "foundational_cm_production_v2"
    audition = json.loads((package / "narration" / "auditions" / "AUDITION_MANIFEST_V2.json").read_text(encoding="utf-8"))
    assert audition["provider"] == "local_kokoro_onnx"
    assert audition["status"] == "human_voice_selection_required"
    assert audition["remote_or_paid_work"] is False
    assert [item["voice"] for item in audition["voices"]] == ["af_heart", "af_bella", "bf_emma"]
    audition_paths = [ROOT / item["path"] for item in audition["voices"]]
    assert all(path.suffix == ".wav" for path in audition_paths)
    present = [path.is_file() for path in audition_paths]
    assert all(present) or not any(present), "audition WAV set must be complete when retained locally"
    if all(present):
        for item, path in zip(audition["voices"], audition_paths):
            assert path.stat().st_size == item["bytes"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]

    proposal = json.loads(
        (ROOT / "docs" / "video_factory" / "runpod" / "foundational_three_v3" / "proposal.json").read_text(encoding="utf-8")
    )
    assert proposal["proposal_id"] == "cm-video-foundational-three-production-remote-v3"
    assert proposal["remote_or_paid_work_authorized"] is False
    assert proposal["render_contract"]["audio"] is True
    assert proposal["render_contract"]["total_frames"] == 21120
