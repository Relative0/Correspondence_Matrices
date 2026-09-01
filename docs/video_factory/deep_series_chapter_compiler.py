"""Compile CM deep-series storyboards into executable local POP chapter briefs.

WP1 is a deterministic local transformation.  It does not render media, read a
credential, contact RunPod, create a remote resource, or authorize paid work.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

from jsonschema import Draft202012Validator

import deep_series_authoring as authoring


REPO_ROOT = Path(__file__).resolve().parents[2]
FACTORY_ROOT = REPO_ROOT / "docs" / "video_factory"
DEEP_ROOT = FACTORY_ROOT / "deep_series"
EPISODES_ROOT = DEEP_ROOT / "episodes"
SCHEMAS_ROOT = FACTORY_ROOT / "schemas"
WP1_ROOT = DEEP_ROOT / "wp1"
SCHEMA_VERSION = "2.0"
COMPILER_VERSION = "1.2.0"

INTERNAL_AUTHORING_MARKERS = (
    "trace cue",
    "narration fragment",
    "episode-specific explanatory pass",
)

VISUAL_SYSTEM_TO_POP_VISUAL = dict(authoring.PRIMITIVE_BY_VISUAL_SYSTEM)

STATUS_PRIORITY = {
    "negative": 6,
    "not_promoted": 5,
    "revised": 4,
    "mixed": 3,
    "confirmed": 2,
    "exploratory": 1,
    "conceptual": 0,
}


class CompilerError(RuntimeError):
    """Raised when an approved authoring contract cannot compile exactly."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def viewer_texts(
    scene: dict[str, Any], cues_by_id: dict[str, dict[str, Any]]
) -> list[str]:
    """Return full narration sentences suitable for persistent on-screen copy.

    Storyboard state changes are renderer directions, not prose.  Keeping this
    boundary explicit prevents cue IDs, composition IDs, and animation notes
    from leaking into the finished video.
    """
    values: list[str] = []
    for cue_id in dict.fromkeys(beat["cue_id"] for beat in scene["beats"]):
        cue = cues_by_id[cue_id]
        text = " ".join(cue["text"].replace("`", "").split())
        if cue["spoken"] and text and text not in values:
            values.append(text)
    return values


def succinct_viewer_text(values: list[str], limit: int) -> str:
    """Choose a complete narration sentence that fits a visible text field."""
    complete = [value for value in values if len(value) <= limit]
    if complete:
        # Prefer the most informative complete line without filling the panel.
        return max(complete, key=lambda value: (min(len(value), 110), -len(value)))
    clauses: list[str] = []
    for value in values:
        for clause in re.split(r"[;:]|,\s+(?:while|so|because)\b", value):
            sentence = authoring.ensure_sentence(clause.strip())
            if 24 <= len(sentence) <= limit and sentence not in clauses:
                clauses.append(sentence)
    if clauses:
        return max(clauses, key=len)
    return "Keep the labeled concept attached to its layer before interpreting it."


def assert_viewer_copy_is_clean(value: Any, location: str = "viewer-copy") -> None:
    """Reject internal authoring scaffolding anywhere in a POP scene payload."""
    if isinstance(value, dict):
        for key, item in value.items():
            assert_viewer_copy_is_clean(item, f"{location}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            assert_viewer_copy_is_clean(item, f"{location}[{index}]")
        return
    if not isinstance(value, str):
        return
    normalized = value.casefold()
    if any(marker in normalized for marker in INTERNAL_AUTHORING_MARKERS):
        raise CompilerError(f"internal authoring marker leaked into {location}")
    if re.search(r"\b(?:cmp\d{3}|q\d{4}|b\d{4})\b", normalized):
        raise CompilerError(f"internal authoring identifier leaked into {location}")
    if "…" in value:
        raise CompilerError(f"truncated viewer copy leaked into {location}")


def finalize(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result["content_hash"] = canonical_sha256(result)
    return result


def write_json(path: Path, value: Any) -> None:
    text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def strict_object(
    properties: dict[str, Any], required: list[str]
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }


def schema() -> dict[str, Any]:
    string = {"type": "string", "minLength": 1}
    sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    strings = {
        "type": "array",
        "items": string,
        "uniqueItems": True,
    }
    graph_node = strict_object(
        {
            "id": string,
            "label": string,
            "x": {"type": "number"},
            "y": {"type": "number"},
            "tone": string,
            "shape": string,
        },
        ["id", "label", "x", "y", "tone", "shape"],
    )
    graph_edge = strict_object(
        {
            "source": string,
            "target": string,
            "label": {"type": "string"},
            "shared": {"type": "boolean"},
        },
        ["source", "target", "label", "shared"],
    )
    graph = strict_object(
        {
            "label": string,
            "note": {"type": "string"},
            "tone": string,
            "nodes": {"type": "array", "minItems": 1, "items": graph_node},
            "edges": {"type": "array", "items": graph_edge},
        },
        ["label", "note", "tone", "nodes", "edges"],
    )
    matrix = strict_object(
        {
            "rows": {"type": "integer", "minimum": 2},
            "columns": {"type": "integer", "minimum": 2},
            "bits": string,
            "row_labels": strings,
            "column_labels": strings,
        },
        ["rows", "columns", "bits", "row_labels", "column_labels"],
    )
    base_data = {
        "eyebrow": string,
        "title": string,
        "caption": string,
        "status": {
            "enum": [
                "confirmed",
                "revised",
                "mixed",
                "exploratory",
                "negative",
                "not_promoted",
                "conceptual",
            ]
        },
        "conceptual": {"type": "boolean"},
        "claim_ids": {"type": "array", "minItems": 1, "items": string, "uniqueItems": True},
        "source_ids": {"type": "array", "minItems": 1, "items": string, "uniqueItems": True},
    }
    expression_data = strict_object(
        {
            **base_data,
            "visual": {"const": "expression_matrix"},
            "expression": string,
            "ambient_variables": {"type": "array", "minItems": 1, "items": string},
            "live_variables": {"type": "array", "minItems": 1, "items": string},
            "matrix": matrix,
        },
        [
            *base_data,
            "visual",
            "expression",
            "ambient_variables",
            "live_variables",
            "matrix",
        ],
    )
    transform_data = strict_object(
        {
            **base_data,
            "visual": {"const": "transform_compare"},
            "graphs": {"type": "array", "minItems": 2, "items": graph},
        },
        [*base_data, "visual", "graphs"],
    )
    representation_data = strict_object(
        {
            **base_data,
            "visual": {"const": "representation_compare"},
            "matrix": matrix,
            "graphs": {"type": "array", "minItems": 1, "items": graph},
        },
        [*base_data, "visual", "matrix", "graphs"],
    )
    boundary_step = strict_object(
        {
            "label": string,
            "note": string,
            "boundary": string,
            "tone": string,
        },
        ["label", "note", "boundary", "tone"],
    )
    boundary_data = strict_object(
        {
            **base_data,
            "visual": {"const": "boundary"},
            "steps": {
                "type": "array",
                "minItems": 2,
                "maxItems": 4,
                "items": boundary_step,
            },
        },
        [*base_data, "visual", "steps"],
    )
    result_data = strict_object(
        {
            **base_data,
            "visual": {"const": "result"},
            "bullets": {
                "type": "array",
                "minItems": 2,
                "maxItems": 4,
                "items": string,
                "uniqueItems": True,
            },
        },
        [*base_data, "visual", "bullets"],
    )
    pop_scene = strict_object(
        {
            "id": string,
            "kind": {"const": "cm_science"},
            "duration": {"type": "number", "exclusiveMinimum": 0},
            "data": {
                "oneOf": [
                    expression_data,
                    transform_data,
                    representation_data,
                    boundary_data,
                    result_data,
                ]
            },
            "script": {"type": "string"},
        },
        ["id", "kind", "duration", "data", "script"],
    )
    beat = strict_object(
        {
            "beat_id": string,
            "cue_id": string,
            "start_frame": {"type": "integer", "minimum": 0},
            "end_frame": {"type": "integer", "minimum": 1},
            "claim_ids": strings,
            "evidence_status": string,
            "state_change": string,
        },
        [
            "beat_id",
            "cue_id",
            "start_frame",
            "end_frame",
            "claim_ids",
            "evidence_status",
            "state_change",
        ],
    )
    resolved_scene = strict_object(
        {
            "scene_id": string,
            "composition_id": string,
            "source_storyboard_scene_sha256": sha,
            "start_frame": {"type": "integer", "minimum": 0},
            "end_frame": {"type": "integer", "minimum": 1},
            "duration_frames": {"type": "integer", "minimum": 1},
            "visual_system": {"enum": sorted(VISUAL_SYSTEM_TO_POP_VISUAL)},
            "primitive": {"enum": sorted(set(VISUAL_SYSTEM_TO_POP_VISUAL.values()))},
            "cue_ids": strings,
            "claim_ids": strings,
            "source_ids": strings,
            "beats": {"type": "array", "minItems": 1, "items": beat},
            "pop_scene": pop_scene,
        },
        [
            "scene_id",
            "composition_id",
            "source_storyboard_scene_sha256",
            "start_frame",
            "end_frame",
            "duration_frames",
            "visual_system",
            "primitive",
            "cue_ids",
            "claim_ids",
            "source_ids",
            "beats",
            "pop_scene",
        ],
    )
    pop_brief = strict_object(
        {
            "schema_id": {"const": "deterministic-video-brief/v1"},
            "version": {"const": "1"},
            "title": string,
            "subject": {"const": "cm_science"},
            "audience": string,
            "purpose": string,
            "width": {"const": 1920},
            "height": {"const": 1080},
            "fps": {"const": 30},
            "theme": strict_object(
                {"id": {"const": "technical_reference"}, "version": {"const": "1.0.0"}},
                ["id", "version"],
            ),
            "brand": {"type": "null"},
            "content_packs": {
                "type": "array",
                "minItems": 1,
                "maxItems": 1,
                "items": strict_object(
                    {"id": {"const": "cm_science"}, "version": {"const": "1.0.0"}},
                    ["id", "version"],
                ),
            },
            "narration": {"const": "off"},
            "provenance": strict_object(
                {
                    "authority": string,
                    "video_id": string,
                    "chapter_id": string,
                    "episode_content_hash": sha,
                    "chapter_cache_identity": sha,
                    "compiler_version": {"const": COMPILER_VERSION},
                    "content_review_status": {"const": "revision_unapproved"},
                },
                [
                    "authority",
                    "video_id",
                    "chapter_id",
                    "episode_content_hash",
                    "chapter_cache_identity",
                    "compiler_version",
                    "content_review_status",
                ],
            ),
            "scenes": {"type": "array", "minItems": 1, "items": pop_scene},
        },
        [
            "schema_id",
            "version",
            "title",
            "subject",
            "audience",
            "purpose",
            "width",
            "height",
            "fps",
            "theme",
            "brand",
            "content_packs",
            "narration",
            "provenance",
            "scenes",
        ],
    )
    contract = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "contract_type": {"const": "executable_chapter_render"},
            "compiler_version": {"const": COMPILER_VERSION},
            "status": {"const": "compiled_local_review_required"},
            "video_id": string,
            "chapter_id": string,
            "episode_content_hash": sha,
            "chapter_cache_identity": sha,
            "content_review_status": {"const": "revision_unapproved"},
            "remote_or_paid_work_authorized": {"const": False},
            "frame_contract": strict_object(
                {
                    "width": {"const": 1920},
                    "height": {"const": 1080},
                    "fps": {"const": 30},
                    "interval": {"const": "half-open"},
                    "clock": {"const": "frame-derived"},
                    "chapter_start_frame": {"type": "integer", "minimum": 0},
                    "chapter_end_frame": {"type": "integer", "minimum": 1},
                    "duration_frames": {"type": "integer", "minimum": 1},
                },
                [
                    "width",
                    "height",
                    "fps",
                    "interval",
                    "clock",
                    "chapter_start_frame",
                    "chapter_end_frame",
                    "duration_frames",
                ],
            ),
            "input_artifact_hashes": {
                "type": "object",
                "minProperties": 5,
                "additionalProperties": sha,
            },
            "renderer_lock": strict_object(
                {
                    "renderer": {"const": "POP-Video-Creator/cm_science@1.0.0"},
                    "theme": {"const": "technical_reference@1.0.0"},
                    "scene_kind": {"const": "cm_science"},
                    "visual_mapping_version": {"const": "wp2-foundation-map/v1"},
                },
                ["renderer", "theme", "scene_kind", "visual_mapping_version"],
            ),
            "scene_count": {"type": "integer", "minimum": 1},
            "beat_count": {"type": "integer", "minimum": 1},
            "resolved_scenes": {"type": "array", "minItems": 1, "items": resolved_scene},
            "pop_video_brief": pop_brief,
            "expected_output_contract": strict_object(
                {
                    "frame_pattern": {"const": "frames/f%08d.png"},
                    "master_filename": {"const": "chapter_master.mp4"},
                    "video_codec": {"const": "h264"},
                    "pixel_format": {"const": "yuv420p"},
                    "audio": {"const": "none_in_wp1"},
                    "captions": {"const": "muxed_later_from_approved_caption_contract"},
                    "hashes_required": {"const": True},
                },
                [
                    "frame_pattern",
                    "master_filename",
                    "video_codec",
                    "pixel_format",
                    "audio",
                    "captions",
                    "hashes_required",
                ],
            ),
            "content_hash": sha,
        },
        [
            "schema_version",
            "contract_type",
            "compiler_version",
            "status",
            "video_id",
            "chapter_id",
            "episode_content_hash",
            "chapter_cache_identity",
            "content_review_status",
            "remote_or_paid_work_authorized",
            "frame_contract",
            "input_artifact_hashes",
            "renderer_lock",
            "scene_count",
            "beat_count",
            "resolved_scenes",
            "pop_video_brief",
            "expected_output_contract",
            "content_hash",
        ],
    )
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **contract}


def validate_schema(value: dict[str, Any]) -> None:
    errors = sorted(Draft202012Validator(schema()).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        error = errors[0]
        path = ".".join(str(part) for part in error.path)
        raise CompilerError(f"schema:{path}:{error.message}")


def select_status(beats: list[dict[str, Any]]) -> str:
    statuses = {beat["evidence_status"] for beat in beats}
    if len(statuses) > 1 and statuses <= {"conceptual", "confirmed"}:
        return "confirmed"
    return max(statuses, key=lambda status: STATUS_PRIORITY[status])


def chapter_frame_bounds(
    chapter_scenes: list[dict[str, Any]], fps: int
) -> tuple[int, int]:
    return (
        int(round(chapter_scenes[0]["start_s"] * fps)),
        int(round(chapter_scenes[-1]["end_s"] * fps)),
    )


def truth_layout_payload(video_id: str) -> dict[str, Any]:
    """Return the exact stable 4-variable truth layout used by foundation scenes."""
    if video_id == "live-support-ambient":
        expression = "(A AND B) XOR C"
        live = ["A", "B", "C"]

        def evaluate(a: int, b: int, c: int, _d: int) -> int:
            return int(bool(a and b) ^ bool(c))
    else:
        expression = "(A AND B) XOR (C OR D)"
        live = ["A", "B", "C", "D"]

        def evaluate(a: int, b: int, c: int, d: int) -> int:
            return int(bool(a and b) ^ bool(c or d))

    bits = "".join(
        str(evaluate(a, b, c, d))
        for a, b in ((0, 0), (0, 1), (1, 0), (1, 1))
        for c, d in ((0, 0), (0, 1), (1, 0), (1, 1))
    )
    return {
        "expression": expression,
        "ambient_variables": ["A", "B", "C", "D"],
        "live_variables": live,
        "matrix": {
            "rows": 4,
            "columns": 4,
            "bits": bits,
            "row_labels": ["AB=00", "AB=01", "AB=10", "AB=11"],
            "column_labels": ["CD=00", "CD=01", "CD=10", "CD=11"],
        },
    }


def representation_graph(
    video_id: str,
    visual_system: str,
    scene: dict[str, Any],
    cues_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    visible = viewer_texts(scene, cues_by_id)
    lesson_graphs: dict[str, dict[str, Any]] = {
        "why-boolean-computation": {
            "label": "Every assignment gets one output",
            "note": "Evaluation maps each complete input assignment to exactly one Boolean value.",
            "tone": "cm_ir",
            "nodes": [
                {"id": "inputs", "label": "16 assignments", "x": 90, "y": 540, "tone": "ast", "shape": "circle"},
                {"id": "evaluate", "label": "evaluate", "x": 350, "y": 390, "tone": "cse_flat", "shape": "box"},
                {"id": "bit", "label": "0 or 1", "x": 625, "y": 250, "tone": "cm", "shape": "double"},
                {"id": "function", "label": "Boolean function", "x": 870, "y": 110, "tone": "confirmed", "shape": "double"},
            ],
            "edges": [
                {"source": "inputs", "target": "evaluate", "label": "one at a time", "shared": False},
                {"source": "evaluate", "target": "bit", "label": "exact", "shared": False},
                {"source": "bit", "target": "function", "label": "all rows", "shared": True},
            ],
        },
        "expression-truth-function": {
            "label": "Three views of one meaning",
            "note": "Syntax, an enumerated truth table, and the resulting function are related but distinct.",
            "tone": "cm_ir",
            "nodes": [
                {"id": "syntax", "label": "Expression", "x": 80, "y": 520, "tone": "ast", "shape": "circle"},
                {"id": "assignments", "label": "Assignments", "x": 310, "y": 390, "tone": "cse_flat", "shape": "box"},
                {"id": "table", "label": "Truth table", "x": 600, "y": 260, "tone": "cm_ir", "shape": "box"},
                {"id": "function", "label": "Boolean function", "x": 880, "y": 110, "tone": "confirmed", "shape": "double"},
            ],
            "edges": [
                {"source": "syntax", "target": "assignments", "label": "evaluate", "shared": False},
                {"source": "assignments", "target": "table", "label": "enumerate", "shared": False},
                {"source": "table", "target": "function", "label": "same mapping", "shared": True},
            ],
        },
        "live-support-ambient": {
            "label": "Only live variables reach the output",
            "note": "A, B, and C can affect the result; D remains in the ambient universe without an output path.",
            "tone": "cm_ir",
            "nodes": [
                {"id": "live", "label": "A, B, C · live", "x": 90, "y": 510, "tone": "cse_flat", "shape": "circle"},
                {"id": "expression", "label": "(A∧B) XOR C", "x": 430, "y": 340, "tone": "cm_ir", "shape": "box"},
                {"id": "output", "label": "output", "x": 820, "y": 150, "tone": "confirmed", "shape": "double"},
                {"id": "ambient", "label": "D · ambient", "x": 90, "y": 640, "tone": "wrapper", "shape": "circle"},
                {"id": "universe", "label": "declared universe", "x": 430, "y": 590, "tone": "wrapper", "shape": "box"},
            ],
            "edges": [
                {"source": "live", "target": "expression", "label": "can change", "shared": False},
                {"source": "expression", "target": "output", "label": "determines", "shared": False},
                {"source": "ambient", "target": "universe", "label": "declared only", "shared": True},
            ],
        },
    }
    if video_id in lesson_graphs:
        return lesson_graphs[video_id]
    if visual_system == "truth-layout reveal":
        return {
            "label": "Assignment indexing",
            "note": succinct_viewer_text(visible, 82),
            "tone": "cm_ir",
            "nodes": [
                {"id": "assignment", "label": "A,B,C,D", "x": 90, "y": 560, "tone": "ast", "shape": "circle"},
                {"id": "row", "label": "row = AB", "x": 325, "y": 390, "tone": "cse_flat", "shape": "box"},
                {"id": "column", "label": "column = CD", "x": 610, "y": 390, "tone": "cse", "shape": "box"},
                {"id": "cell", "label": "one exact cell", "x": 865, "y": 170, "tone": "cm", "shape": "double"},
            ],
            "edges": [
                {"source": "assignment", "target": "row", "label": "high bits", "shared": False},
                {"source": "assignment", "target": "column", "label": "low bits", "shared": False},
                {"source": "row", "target": "cell", "label": "index", "shared": False},
                {"source": "column", "target": "cell", "label": "index", "shared": False},
            ],
        }
    return {
        "label": "Packed output trace",
        "note": authoring.trim_sentence(
            "The assignment index selects one exact truth bit; packing changes storage, not meaning.",
            82,
        ),
        "tone": "cm_ir",
        "nodes": [
            {"id": "assignment", "label": "A,B,C,D", "x": 90, "y": 560, "tone": "ast", "shape": "circle"},
            {"id": "index", "label": "row / column", "x": 300, "y": 400, "tone": "cse_flat", "shape": "box"},
            {"id": "cell", "label": "exact cell", "x": 515, "y": 250, "tone": "cm", "shape": "double"},
            {"id": "word", "label": "packed word", "x": 735, "y": 400, "tone": "cm_ir", "shape": "box"},
            {"id": "meaning", "label": "same Boolean bit", "x": 900, "y": 170, "tone": "confirmed", "shape": "double"},
        ],
        "edges": [
            {"source": "assignment", "target": "index", "label": "encode", "shared": False},
            {"source": "index", "target": "cell", "label": "select", "shared": False},
            {"source": "cell", "target": "word", "label": "pack", "shared": True},
            {"source": "word", "target": "meaning", "label": "same bit", "shared": False},
        ],
    }


def boundary_steps(
    episode: dict[str, Any],
    scene: dict[str, Any],
    status: str,
    visual_system: str,
    cues_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    lesson_steps: dict[str, list[dict[str, str]]] = {
        "why-boolean-computation": [
            {"label": "Assign", "note": "Choose one complete input assignment.", "boundary": "INPUT", "tone": "ast"},
            {"label": "Evaluate", "note": "Apply the Boolean expression exactly.", "boundary": "RULE", "tone": "cse_flat"},
            {"label": "Emit", "note": "Produce one true-or-false output.", "boundary": "OUTPUT", "tone": "cm_ir"},
            {"label": "Repeat", "note": "All assignments together define the function.", "boundary": "FUNCTION", "tone": "confirmed"},
        ],
        "expression-truth-function": [
            {"label": "Expression", "note": "Written syntax names how to compute.", "boundary": "SYNTAX", "tone": "ast"},
            {"label": "Truth table", "note": "Rows enumerate every assignment and result.", "boundary": "ENUMERATION", "tone": "cse_flat"},
            {"label": "Function", "note": "The mapping assigns one output to each input.", "boundary": "SEMANTICS", "tone": "cm_ir"},
            {"label": "Compare", "note": "Different expressions may denote the same function.", "boundary": "EQUIVALENCE", "tone": "confirmed"},
        ],
        "live-support-ambient": [
            {"label": "Universe", "note": "Declare ambient variables A through D.", "boundary": "AMBIENT", "tone": "wrapper"},
            {"label": "Toggle D", "note": "Change D while holding A, B, and C fixed.", "boundary": "TEST", "tone": "ast"},
            {"label": "Compare", "note": "The output remains unchanged across D.", "boundary": "OBSERVE", "tone": "cm_ir"},
            {"label": "Live support", "note": "Only A, B, and C can change this output.", "boundary": "DEPENDENCY", "tone": "confirmed"},
        ],
    }
    if episode["video_id"] in lesson_steps:
        return lesson_steps[episode["video_id"]]
    if visual_system == "packed-output trace":
        return [
            {"label": "Assignment", "note": "Fix A, B, C, and D in the declared variable order.", "boundary": "INPUT", "tone": "ast"},
            {"label": "Index", "note": "A and B choose the row; C and D choose the column.", "boundary": "LAYOUT", "tone": "cse_flat"},
            {"label": "Pack", "note": "Store the sixteen exact outputs in a deterministic bit order.", "boundary": "STORAGE", "tone": "cm_ir"},
            {"label": "Read", "note": "Selecting the packed bit returns the same Boolean value as the matrix cell.", "boundary": "SAME MEANING", "tone": "confirmed"},
        ]
    visible = viewer_texts(scene, cues_by_id)
    first = succinct_viewer_text(visible[:1], 82)
    final = succinct_viewer_text(visible[-1:], 82)
    scope = succinct_viewer_text([episode["caveats"][0]], 82)
    tone = status if status in {"confirmed", "mixed", "negative", "conceptual"} else "neutral"
    return [
        {"label": "Explain", "note": first, "boundary": "CONCEPT", "tone": "conceptual"},
        {"label": "Bind", "note": scope, "boundary": "SOURCE + SCOPE", "tone": "wrapper"},
        {"label": "Verify", "note": "Check the declared output and comparison boundary before interpreting the scene.", "boundary": "EXACT CHECK", "tone": "cm"},
        {"label": status.replace("_", " ").title(), "note": final, "boundary": "DECISION", "tone": tone},
    ]


def result_bullets(
    episode: dict[str, Any],
    scene: dict[str, Any],
    cues_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    candidates = [
        episode["thesis"],
        *viewer_texts(scene, cues_by_id),
        episode["caveats"][0],
        episode["closing_takeaway"],
    ]
    results: list[str] = []
    for candidate in candidates:
        item = succinct_viewer_text([candidate], 118)
        if item not in results:
            results.append(item)
    return results[:4]


def scene_payload(
    episode: dict[str, Any],
    example: dict[str, Any],
    scene: dict[str, Any],
    cues_by_id: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[str], list[str], str]:
    visual_systems = {beat["visual_system"] for beat in scene["beats"]}
    primitives = {beat["primitive"] for beat in scene["beats"]}
    if len(visual_systems) != 1 or len(primitives) != 1:
        raise CompilerError(f"{episode['video_id']}:{scene['scene_id']}:mixed-scene-primitive")
    visual_system = next(iter(visual_systems))
    primitive = next(iter(primitives))
    if visual_system not in VISUAL_SYSTEM_TO_POP_VISUAL:
        raise CompilerError(f"{episode['video_id']}:{scene['scene_id']}:unsupported-visual-system:{visual_system}")
    mapped_visual = VISUAL_SYSTEM_TO_POP_VISUAL[visual_system]
    if mapped_visual != primitive:
        raise CompilerError(f"{episode['video_id']}:{scene['scene_id']}:primitive-map-mismatch")
    claim_ids = sorted({claim for beat in scene["beats"] for claim in beat["claim_ids"]})
    if not claim_ids:
        claim_ids = [episode["claim_ids"][0]]
    source_ids = episode["source_ids"]
    status = select_status(scene["beats"])
    cue_ids = list(dict.fromkeys(beat["cue_id"] for beat in scene["beats"]))
    spoken = " ".join(cues_by_id[cue_id]["text"] for cue_id in cue_ids if cues_by_id[cue_id]["spoken"])
    visible = viewer_texts(scene, cues_by_id)
    lesson_titles = {
        "why-boolean-computation": {
            "expression evaluation": "Assignments Become Outputs",
            "truth-layout reveal": "Boolean Function Map",
            "packed-output trace": "Evaluate Every Assignment",
        },
        "expression-truth-function": {
            "expression evaluation": "Expression And Evaluation",
            "truth-layout reveal": "Three Representations",
            "packed-output trace": "One Function, Three Views",
        },
        "live-support-ambient": {
            "expression evaluation": "Live Variables",
            "truth-layout reveal": "Dependency Reveal",
            "packed-output trace": "Ambient Variable Check",
        },
    }
    title = lesson_titles.get(episode["video_id"], {}).get(
        visual_system, visual_system.title()
    )
    caption = succinct_viewer_text(visible, 150)
    base = {
        "eyebrow": f"CM DEEP SERIES · EPISODE {episode['order']:02d}",
        "title": title,
        "caption": caption,
        "status": status,
        "conceptual": status == "conceptual",
        "claim_ids": claim_ids,
        "source_ids": source_ids,
        "visual": mapped_visual,
    }
    if mapped_visual == "expression_matrix":
        base.update(truth_layout_payload(episode["video_id"]))
    elif mapped_visual == "representation_compare":
        base.update({
            "matrix": truth_layout_payload(episode["video_id"])["matrix"],
            "graphs": [representation_graph(
                episode["video_id"], visual_system, scene, cues_by_id
            )],
        })
    elif mapped_visual == "boundary":
        base["steps"] = boundary_steps(
            episode, scene, status, visual_system, cues_by_id
        )
    elif mapped_visual == "result":
        base["bullets"] = result_bullets(episode, scene, cues_by_id)
    elif mapped_visual == "transform_compare":
        templates = authoring.preview_scene_data(
            episode,
            example,
            {claim_id: {"status": "confirmed", "allowed_wording": claim_id} for claim_id in episode["claim_ids"]},
            {episode["video_id"]: episode, **{ref: episode for ref in episode["references"]}},
        )
        template = next((item for item in templates if item["visual"] == mapped_visual), None)
        if template is None:
            raise CompilerError(f"{episode['video_id']}:{scene['scene_id']}:missing-template:{mapped_visual}")
        graphs = copy.deepcopy(template["graphs"])
        first_entity = scene["beats"][0]["entities"][0]
        last_entity = scene["beats"][-1]["entities"][-1]
        graphs[0]["label"] = authoring.trim_sentence(visual_system, 42)
        graphs[0]["note"] = succinct_viewer_text([first_entity], 82)
        graphs[1]["label"] = authoring.trim_sentence("Resolved state", 42)
        graphs[1]["note"] = succinct_viewer_text([last_entity], 82)
        for graph in graphs:
            for edge in graph["edges"]:
                edge.setdefault("label", "")
                edge.setdefault("shared", False)
        base["graphs"] = graphs
    else:
        raise CompilerError(
            f"{episode['video_id']}:{scene['scene_id']}:no-payload-builder:{mapped_visual}"
        )
    pop_scene = {
        "id": scene["scene_id"],
        "kind": "cm_science",
        "duration": 0.1,
        "data": base,
        "script": spoken,
    }
    assert_viewer_copy_is_clean(pop_scene, f"{episode['video_id']}.{scene['scene_id']}")
    return pop_scene, cue_ids, claim_ids, visual_system


def compile_chapter(
    episode: dict[str, Any],
    example: dict[str, Any],
    chapter: dict[str, Any],
    storyboard: dict[str, Any],
    narration: dict[str, Any],
    input_hashes: dict[str, str],
) -> dict[str, Any]:
    fps = storyboard["frame_contract"]["fps"]
    cues_by_id = {cue["cue_id"]: cue for cue in narration["cues"]}
    scenes_by_id = {scene["scene_id"]: scene for scene in storyboard["scenes"]}
    chapter_scenes = [scenes_by_id[scene_id] for scene_id in chapter["scene_ids"]]
    start_frame, end_frame = chapter_frame_bounds(chapter_scenes, fps)
    resolved: list[dict[str, Any]] = []
    expected_scene_start = start_frame
    for scene in chapter_scenes:
        scene_start = int(round(scene["start_s"] * fps))
        scene_end = int(round(scene["end_s"] * fps))
        if scene_start != expected_scene_start or scene_end <= scene_start:
            raise CompilerError(f"{episode['video_id']}:{chapter['chapter_id']}:{scene['scene_id']}:frame-gap")
        pop_scene, cue_ids, claim_ids, visual_system = scene_payload(
            episode, example, scene, cues_by_id
        )
        pop_scene["duration"] = (scene_end - scene_start) / fps
        beat_values = []
        previous_beat_end = scene_start
        for beat in scene["beats"]:
            beat_start = int(round(beat["start_s"] * fps))
            beat_end = int(round(beat["end_s"] * fps))
            if beat_start != previous_beat_end or beat_end <= beat_start:
                raise CompilerError(
                    f"{episode['video_id']}:{chapter['chapter_id']}:{beat['beat_id']}:beat-frame-gap"
                )
            beat_values.append({
                "beat_id": beat["beat_id"],
                "cue_id": beat["cue_id"],
                "start_frame": beat_start,
                "end_frame": beat_end,
                "claim_ids": beat["claim_ids"],
                "evidence_status": beat["evidence_status"],
                "state_change": beat["state_change"],
            })
            previous_beat_end = beat_end
        if previous_beat_end != scene_end:
            raise CompilerError(f"{episode['video_id']}:{chapter['chapter_id']}:{scene['scene_id']}:beat-tail-gap")
        resolved.append({
            "scene_id": scene["scene_id"],
            "composition_id": scene["composition_id"],
            "source_storyboard_scene_sha256": canonical_sha256(scene),
            "start_frame": scene_start,
            "end_frame": scene_end,
            "duration_frames": scene_end - scene_start,
            "visual_system": visual_system,
            "primitive": VISUAL_SYSTEM_TO_POP_VISUAL[visual_system],
            "cue_ids": cue_ids,
            "claim_ids": claim_ids,
            "source_ids": episode["source_ids"],
            "beats": beat_values,
            "pop_scene": pop_scene,
        })
        expected_scene_start = scene_end
    if expected_scene_start != end_frame:
        raise CompilerError(f"{episode['video_id']}:{chapter['chapter_id']}:chapter-tail-gap")
    pop_scenes = [item["pop_scene"] for item in resolved]
    pop_brief = {
        "schema_id": "deterministic-video-brief/v1",
        "version": "1",
        "title": f"{episode['title']} · {chapter['title']}",
        "subject": "cm_science",
        "audience": episode["audience"],
        "purpose": chapter["purpose"],
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "theme": {"id": "technical_reference", "version": "1.0.0"},
        "brand": None,
        "content_packs": [{"id": "cm_science", "version": "1.0.0"}],
        "narration": "off",
        "provenance": {
            "authority": "CM_Computation/docs/video_factory/deep_series",
            "video_id": episode["video_id"],
            "chapter_id": chapter["chapter_id"],
            "episode_content_hash": episode["content_hash"],
            "chapter_cache_identity": chapter["cache_identity"],
            "compiler_version": COMPILER_VERSION,
            "content_review_status": "revision_unapproved",
        },
        "scenes": pop_scenes,
    }
    contract = finalize({
        "schema_version": SCHEMA_VERSION,
        "contract_type": "executable_chapter_render",
        "compiler_version": COMPILER_VERSION,
        "status": "compiled_local_review_required",
        "video_id": episode["video_id"],
        "chapter_id": chapter["chapter_id"],
        "episode_content_hash": episode["content_hash"],
        "chapter_cache_identity": chapter["cache_identity"],
        "content_review_status": "revision_unapproved",
        "remote_or_paid_work_authorized": False,
        "frame_contract": {
            "width": 1920,
            "height": 1080,
            "fps": fps,
            "interval": "half-open",
            "clock": "frame-derived",
            "chapter_start_frame": start_frame,
            "chapter_end_frame": end_frame,
            "duration_frames": end_frame - start_frame,
        },
        "input_artifact_hashes": input_hashes,
        "renderer_lock": {
            "renderer": "POP-Video-Creator/cm_science@1.0.0",
            "theme": "technical_reference@1.0.0",
            "scene_kind": "cm_science",
            "visual_mapping_version": "wp2-foundation-map/v1",
        },
        "scene_count": len(resolved),
        "beat_count": sum(len(item["beats"]) for item in resolved),
        "resolved_scenes": resolved,
        "pop_video_brief": pop_brief,
        "expected_output_contract": {
            "frame_pattern": "frames/f%08d.png",
            "master_filename": "chapter_master.mp4",
            "video_codec": "h264",
            "pixel_format": "yuv420p",
            "audio": "none_in_wp1",
            "captions": "muxed_later_from_approved_caption_contract",
            "hashes_required": True,
        },
    })
    validate_schema(contract)
    return contract


def validate_pop_brief(value: dict[str, Any], pop_root: Path) -> None:
    pop_root = pop_root.resolve()
    if not (pop_root / "pop_video").is_dir():
        raise CompilerError(f"POP package is missing under {pop_root}")
    if str(pop_root) not in sys.path:
        sys.path.insert(0, str(pop_root))
    from pop_video.contracts import VideoBrief  # type: ignore
    from pop_video.planning import plan_brief  # type: ignore

    plan_brief(VideoBrief.model_validate(value))


def build(pop_root: Path) -> None:
    # A compiler revision necessarily makes the prior review packet stale.
    # Validate immutable authoring inputs here; a fresh packet is requested
    # after the revised visual artifacts have been regenerated.
    authoring.validate(include_review_packet=False)
    bible = load_json(DEEP_ROOT / "episode_content_bible.json")
    gate_status = bible["approval_gate"]["status"]
    if gate_status not in {"not_requested", "approved"}:
        raise CompilerError(f"WP1 cannot compile content gate status: {gate_status}")
    if gate_status == "approved":
        approval = load_json(DEEP_ROOT / "production_planning" / "content_approval.json")
        if (
            approval["status"] != "approved"
            or approval["bible_content_hash"] != bible["content_hash"]
            or approval["review_manifest_sha256"]
            != bible["approval_gate"]["review_manifest_sha256"]
            or approval["content_approval_authorizes_remote_or_paid_work"] is not False
        ):
            raise CompilerError("approved content gate does not match its local approval record")
    claims = load_json(FACTORY_ROOT / "claim_registry.json")
    examples = {
        item["example_id"]: item for item in bible["stable_examples"]
    }
    contracts: list[dict[str, Any]] = []
    total_scenes = 0
    total_beats = 0
    total_cues = 0
    for episode in bible["episodes"]:
        episode_dir = EPISODES_ROOT / episode["video_id"]
        storyboard_path = episode_dir / "storyboard.json"
        narration_path = episode_dir / "narration_contract.json"
        caption_path = episode_dir / "caption_contract.json"
        claim_map_path = episode_dir / "claim_map.json"
        asset_path = episode_dir / "asset_manifest.json"
        storyboard = load_json(storyboard_path)
        narration = load_json(narration_path)
        narration_cues = {cue["cue_id"] for cue in narration["cues"]}
        mapped_cues = {
            beat["cue_id"]
            for scene in storyboard["scenes"]
            for beat in scene["beats"]
        }
        if narration_cues != mapped_cues:
            raise CompilerError(f"{episode['video_id']}:cue-coverage")
        total_cues += len(narration_cues)
        common_hashes = {
            "episode_content_bible": bible["content_hash"],
            "claim_registry": file_sha256(FACTORY_ROOT / "claim_registry.json"),
            "source_registry": file_sha256(FACTORY_ROOT / "source_registry.json"),
            "storyboard": file_sha256(storyboard_path),
            "narration_contract": file_sha256(narration_path),
            "caption_contract": file_sha256(caption_path),
            "claim_map": file_sha256(claim_map_path),
            "asset_manifest": file_sha256(asset_path),
        }
        for chapter_dir in sorted(
            path for path in (episode_dir / "chapters").iterdir() if path.is_dir()
        ):
            chapter_path = chapter_dir / "chapter.json"
            renderer_path = chapter_dir / "renderer_brief.json"
            chapter = load_json(chapter_path)
            input_hashes = {
                **common_hashes,
                "chapter_contract": file_sha256(chapter_path),
                "renderer_brief": file_sha256(renderer_path),
            }
            contract = compile_chapter(
                episode,
                examples[episode["worked_example_id"]],
                chapter,
                storyboard,
                narration,
                input_hashes,
            )
            validate_pop_brief(contract["pop_video_brief"], pop_root)
            contract_path = chapter_dir / "executable_render_contract.json"
            write_json(contract_path, contract)
            total_scenes += contract["scene_count"]
            total_beats += contract["beat_count"]
            contracts.append({
                "video_id": episode["video_id"],
                "chapter_id": chapter["chapter_id"],
                "chapter_cache_identity": chapter["cache_identity"],
                "path": relative(contract_path),
                "file_sha256": file_sha256(contract_path),
                "contract_content_hash": contract["content_hash"],
                "scene_count": contract["scene_count"],
                "beat_count": contract["beat_count"],
            })
    manifest = finalize({
        "schema_version": SCHEMA_VERSION,
        "compiler_version": COMPILER_VERSION,
        "status": "wp1_complete_local_review_required",
        "bible_content_hash": bible["content_hash"],
        "content_review_status": (
            "approved_for_production_planning"
            if gate_status == "approved"
            else "revision_unapproved"
        ),
        "remote_or_paid_work_authorized": False,
        "episode_count": len(bible["episodes"]),
        "chapter_count": len(contracts),
        "scene_count": total_scenes,
        "beat_count": total_beats,
        "cue_count": total_cues,
        "visual_system_mapping": VISUAL_SYSTEM_TO_POP_VISUAL,
        "contracts": contracts,
    })
    write_json(SCHEMAS_ROOT / "deep_executable_chapter_render.schema.json", schema())
    write_json(WP1_ROOT / "chapter_render_contract_manifest.json", manifest)
    report = "\n".join([
        "# WP1 — executable chapter render contracts",
        "",
        "Status: **complete locally; content review and WP2 visual fidelity remain required**",
        "",
        f"Bible content hash: `{bible['content_hash']}`",
        "",
        f"Episodes: **{len(bible['episodes'])}**",
        "",
        f"Chapters compiled: **{len(contracts)}**",
        "",
        f"Storyboard compositions resolved: **{total_scenes}**",
        "",
        f"Timed visual beats resolved: **{total_beats}**",
        "",
        f"Narration cues covered: **{total_cues}**",
        "",
        "Every contract contains exact half-open frame spans, beat/cue/claim/source mappings, a schema-valid executable POP brief, input hashes, renderer locks, and an expected output contract.",
        "",
        "WP1 maps every declared visual system explicitly. WP2 must replace the current graph/matrix scaffolds with the specialized matrix, DAG, circuit, feature-model, policy, evidence, and recognition primitives before full-chapter production qualification.",
        "",
        "No RunPod, network, paid service, rendering, narration generation, mux, or publication action occurred.",
        "",
    ])
    (WP1_ROOT / "WP1_REPORT.md").write_text(report, encoding="utf-8")
    validate(pop_root)


def validate(pop_root: Path) -> None:
    authoring.validate(include_review_packet=False)
    manifest_path = WP1_ROOT / "chapter_render_contract_manifest.json"
    if not manifest_path.is_file():
        raise CompilerError("WP1 manifest is missing")
    manifest = load_json(manifest_path)
    expected = canonical_sha256(
        {key: value for key, value in manifest.items() if key != "content_hash"}
    )
    if manifest["content_hash"] != expected:
        raise CompilerError("WP1 manifest hash is stale")
    bible = load_json(DEEP_ROOT / "episode_content_bible.json")
    expected_chapters = sum(len(episode["chapter_plan"]) for episode in bible["episodes"])
    expected_scenes = sum(
        load_json(EPISODES_ROOT / episode["video_id"] / "storyboard.json")["composition_count"]
        for episode in bible["episodes"]
    )
    if manifest["episode_count"] != len(bible["episodes"]):
        raise CompilerError("WP1 episode coverage is stale")
    if manifest["chapter_count"] != expected_chapters:
        raise CompilerError("WP1 chapter coverage is incomplete")
    if manifest["scene_count"] != expected_scenes:
        raise CompilerError("WP1 scene coverage is incomplete")
    if manifest["remote_or_paid_work_authorized"] is not False:
        raise CompilerError("WP1 must not authorize remote work")
    seen = set()
    for item in manifest["contracts"]:
        key = (item["video_id"], item["chapter_id"])
        if key in seen:
            raise CompilerError(f"duplicate WP1 contract: {key}")
        seen.add(key)
        path = REPO_ROOT / item["path"]
        if file_sha256(path) != item["file_sha256"]:
            raise CompilerError(f"stale WP1 file: {item['path']}")
        contract = load_json(path)
        validate_schema(contract)
        contract_hash = canonical_sha256(
            {key: value for key, value in contract.items() if key != "content_hash"}
        )
        if contract_hash != contract["content_hash"]:
            raise CompilerError(f"stale WP1 contract hash: {item['path']}")
        if contract["content_hash"] != item["contract_content_hash"]:
            raise CompilerError(f"WP1 manifest contract mismatch: {item['path']}")
        if contract["scene_count"] != len(contract["resolved_scenes"]):
            raise CompilerError(f"WP1 scene count mismatch: {item['path']}")
        if contract["pop_video_brief"]["scenes"] != [
            scene["pop_scene"] for scene in contract["resolved_scenes"]
        ]:
            raise CompilerError(f"WP1 POP scene mapping mismatch: {item['path']}")
        for scene in contract["resolved_scenes"]:
            assert_viewer_copy_is_clean(
                scene["pop_scene"],
                f"{contract['video_id']}.{contract['chapter_id']}.{scene['scene_id']}",
            )
        validate_pop_brief(contract["pop_video_brief"], pop_root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "validate"))
    parser.add_argument("--pop-root", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        build(args.pop_root)
    else:
        validate(args.pop_root)


if __name__ == "__main__":
    main()
