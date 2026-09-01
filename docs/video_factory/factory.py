"""Build and validate the evidence-bound CM video-factory artifacts.

Run with Master-Video-Creator's Python 3.10 environment; it already contains
the pinned jsonschema dependency used by IVC. No command in this module makes a
network request, reruns a benchmark, reads a secret, or invokes a paid service.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator


FACTORY_ROOT = Path(__file__).resolve().parent
REPO_ROOT = FACTORY_ROOT.parents[1]
GENERATED_DATE = "2026-08-31"
SCHEMA_VERSION = "1.0"
DEEP_SERIES_SCHEMA_VERSION = "2.0"
DEEP_SERIES_EPISODE_COUNT = 51
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class FactoryError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def write_json(path: Path, value: Any) -> None:
    """Atomically update draft/generated output; never replace approved production."""
    text = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if path.exists():
        current = path.read_text("utf-8")
        if current == text:
            return
        try:
            prior = json.loads(current)
        except json.JSONDecodeError as exc:
            raise FactoryError(f"refusing to replace non-JSON artifact: {path}") from exc
        if prior.get("status") in {"approved", "production", "published"}:
            raise FactoryError(f"refusing to replace approved production artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def write_text(path: Path, text: str) -> None:
    if not text.endswith("\n"):
        text += "\n"
    if path.exists() and path.read_text("utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def strict_object(properties: dict[str, Any], required: Iterable[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(required),
    }


STRING = {"type": "string", "minLength": 1}
STRINGS = {"type": "array", "items": STRING, "uniqueItems": True}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
GIT_SHA = {"type": "string", "pattern": "^[0-9a-f]{40}$"}


def schemas() -> dict[str, dict[str, Any]]:
    source_ref = strict_object(
        {"source_id": STRING, "locator": STRING}, ["source_id", "locator"]
    )
    source_entry = strict_object(
        {
            "id": STRING, "path": STRING, "sha256": SHA, "type": STRING,
            "status": {"enum": ["current", "accepted", "reference", "superseded"]},
            "date": STRING, "supersedes": STRINGS, "superseded_by": STRINGS,
        },
        ["id", "path", "sha256", "type", "status", "date", "supersedes", "superseded_by"],
    )
    source_registry = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION}, "generated_date": STRING,
            "repository_head": GIT_SHA,
            "sources": {"type": "array", "minItems": 1, "items": source_entry},
        },
        ["schema_version", "generated_date", "repository_head", "sources"],
    )
    claim_entry = strict_object(
        {
            "id": STRING, "allowed_wording": STRING, "plain_wording": STRING,
            "technical_wording": STRING,
            "type": {"enum": ["fact", "measurement", "interpretation", "hypothesis", "conceptual"]},
            "status": {"enum": ["confirmed", "revised", "superseded", "exploratory", "negative", "not_promoted"]},
            "scope": STRING, "measurement_boundary": {"type": "string"},
            "comparator": {"type": "string"}, "ratio_direction": {"type": "string"},
            "uncertainty": {"type": "string"},
            "sources": {"type": "array", "minItems": 1, "items": source_ref},
        },
        ["id", "allowed_wording", "plain_wording", "technical_wording", "type", "status",
         "scope", "measurement_boundary", "comparator", "ratio_direction", "uncertainty", "sources"],
    )
    claim_registry = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION}, "generated_date": STRING,
            "claims": {"type": "array", "minItems": 1, "items": claim_entry},
        }, ["schema_version", "generated_date", "claims"],
    )
    glossary_entry = strict_object(
        {
            "term": STRING, "expansion": {"type": "string"}, "plain_definition": STRING,
            "technical_definition": STRING, "common_confusion": STRING, "source_ids": STRINGS,
        }, ["term", "expansion", "plain_definition", "technical_definition", "common_confusion", "source_ids"],
    )
    glossary = strict_object(
        {"schema_version": {"const": SCHEMA_VERSION}, "entries": {"type": "array", "items": glossary_entry}},
        ["schema_version", "entries"],
    )
    selected_claim = strict_object(
        {"claim_id": STRING, "wording": {"enum": ["plain", "technical"]}},
        ["claim_id", "wording"],
    )
    scene = strict_object(
        {
            "id": STRING, "purpose": STRING, "primitive": STRING, "data_refs": STRINGS,
            "claim_ids": STRINGS, "caption": STRING, "narration": {"type": "string"},
            "duration_s": {"type": "number", "exclusiveMinimum": 0}, "transition": STRING,
            "measurement_boundary": {"type": "string"},
            "status": {"enum": ["conceptual", "confirmed", "revised", "mixed", "negative", "not_promoted", "correction_history"]},
        },
        ["id", "purpose", "primitive", "data_refs", "claim_ids", "caption", "narration",
         "duration_s", "transition", "measurement_boundary", "status"],
    )
    display_rules = strict_object(
        {
            "scope": STRING, "boundary": STRING, "uncertainty": STRING,
            "conceptual": STRING, "source_footnotes": STRING,
        }, ["scope", "boundary", "uncertainty", "conceptual", "source_footnotes"],
    )
    narration = strict_object(
        {
            "mode": {"enum": ["off", "on"]}, "pronunciations": {"type": "object", "additionalProperties": {"type": "string"}},
            "caption_contract": STRING,
        }, ["mode", "pronunciations", "caption_contract"],
    )
    video_brief = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION}, "video_id": STRING, "series": STRING,
            "title": STRING, "promise": STRING, "audience": STRING, "assumed_knowledge": STRINGS,
            "prerequisites": STRINGS, "duration_tier": {"enum": ["visual_short", "core_explainer", "deep_dive"]},
            "target_formats": STRINGS, "status": {"enum": ["draft", "validated", "proposed", "approved"]},
            "hook": STRING, "central_question": STRING, "answer": STRING, "limits": STRINGS,
            "closing_takeaway": STRING,
            "claims": {"type": "array", "minItems": 1, "items": selected_claim},
            "scenes": {"type": "array", "minItems": 1, "items": scene},
            "display_rules": display_rules, "narration": narration, "expected_outputs": STRINGS,
            "execution": strict_object(
                {"local_suitability": STRING, "remote_suitability": STRING, "render_class": STRING},
                ["local_suitability", "remote_suitability", "render_class"],
            ),
            "content_hash": SHA,
        },
        ["schema_version", "video_id", "series", "title", "promise", "audience", "assumed_knowledge",
         "prerequisites", "duration_tier", "target_formats", "status", "hook", "central_question",
         "answer", "limits", "closing_takeaway", "claims", "scenes", "display_rules", "narration",
         "expected_outputs", "execution", "content_hash"],
    )
    candidate = strict_object(
        {
            "video_id": STRING, "track": STRING, "title": STRING, "audience": STRING,
            "prerequisites": STRINGS, "central_question": STRING, "viewer_outcome": STRING,
            "claim_ids": STRINGS, "visuals_and_data": STRINGS, "misconceptions": STRINGS,
            "caveats": STRINGS, "duration_tier": {"enum": ["visual_short", "core_explainer", "deep_dive"]},
            "reuse_opportunities": STRINGS, "render_complexity": {"enum": ["low", "medium", "high"]},
            "priority": {"enum": ["P0", "P1", "P2"]}, "status": {"enum": ["proposed", "rendered", "blocked", "not_promoted"]},
            "long_form_master": {"type": ["string", "null"]},
        },
        ["video_id", "track", "title", "audience", "prerequisites", "central_question", "viewer_outcome",
         "claim_ids", "visuals_and_data", "misconceptions", "caveats", "duration_tier", "reuse_opportunities",
         "render_complexity", "priority", "status", "long_form_master"],
    )
    video_catalog = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION}, "status": {"const": "proposed"},
            "generated_date": STRING, "candidates": {"type": "array", "minItems": 20, "items": candidate},
            "first_wave": {"type": "array", "minItems": 1, "maxItems": 12, "items": STRING, "uniqueItems": True},
        }, ["schema_version", "status", "generated_date", "candidates", "first_wave"],
    )
    learning_path = strict_object(
        {"id": STRING, "audience": STRING, "video_ids": STRINGS, "outcome": STRING},
        ["id", "audience", "video_ids", "outcome"],
    )
    series_map = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "paths": {"type": "array", "minItems": 2, "items": learning_path},
            "edges": {"type": "array", "items": strict_object({"from": STRING, "to": STRING}, ["from", "to"])},
        }, ["schema_version", "paths", "edges"],
    )
    content_section = strict_object(
        {
            "section_id": STRING,
            "order": {"type": "integer", "minimum": 1},
            "title": STRING,
            "purpose": STRING,
            "episode_ids": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
        },
        ["section_id", "order", "title", "purpose", "episode_ids"],
    )
    stable_example = strict_object(
        {
            "example_id": STRING,
            "title": STRING,
            "purpose": STRING,
            "definition": STRING,
            "conceptual": {"type": "boolean"},
            "source_ids": STRINGS,
        },
        ["example_id", "title", "purpose", "definition", "conceptual", "source_ids"],
    )
    dialogue_anchors = strict_object(
        {
            "hook": STRING,
            "definition": STRING,
            "boundary": STRING,
            "closing": STRING,
        },
        ["hook", "definition", "boundary", "closing"],
    )
    duration_minutes = strict_object(
        {
            "minimum": {"type": "number", "minimum": 1},
            "maximum": {"type": "number", "minimum": 1},
        },
        ["minimum", "maximum"],
    )
    content_chapter = strict_object(
        {
            "chapter_id": {"type": "string", "pattern": "^c[0-9]{2}$"},
            "working_title": STRING,
            "purpose": STRING,
            "teaching_beat_numbers": {
                "type": "array", "minItems": 1,
                "items": {"type": "integer", "minimum": 1}, "uniqueItems": True,
            },
            "visual_spine_indices": {
                "type": "array", "minItems": 1,
                "items": {"type": "integer", "minimum": 1}, "uniqueItems": True,
            },
        },
        ["chapter_id", "working_title", "purpose", "teaching_beat_numbers", "visual_spine_indices"],
    )
    visual_contract = strict_object(
        {
            "minimum_distinct_compositions": {"type": "integer", "minimum": 1},
            "minimum_meaningful_state_changes": {"type": "integer", "minimum": 1},
            "required_asset_kinds": {
                "type": "array", "minItems": 5, "items": STRING, "uniqueItems": True,
            },
            "continuity_assets": {
                "type": "array", "minItems": 3, "items": STRING, "uniqueItems": True,
            },
            "external_imagery_policy": STRING,
            "progression_rule": STRING,
            "forbidden_shortcuts": {
                "type": "array", "minItems": 3, "items": STRING, "uniqueItems": True,
            },
        },
        [
            "minimum_distinct_compositions", "minimum_meaningful_state_changes",
            "required_asset_kinds", "continuity_assets", "external_imagery_policy",
            "progression_rule", "forbidden_shortcuts",
        ],
    )
    content_episode = strict_object(
        {
            "video_id": STRING,
            "section_id": STRING,
            "order": {"type": "integer", "minimum": 1},
            "title": STRING,
            "audience": STRING,
            "duration_tier": {"enum": ["focused_explainer", "core_episode", "deep_episode"]},
            "duration_minutes": duration_minutes,
            "prerequisite_ids": STRINGS,
            "thesis": STRING,
            "owns": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "references": STRINGS,
            "excludes": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "definitions": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "claim_ids": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "source_ids": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "worked_example_id": STRING,
            "teaching_beats": {"type": "array", "minItems": 6, "maxItems": 10, "items": STRING},
            "visual_spine": {"type": "array", "minItems": 3, "maxItems": 8, "items": STRING},
            "chapter_plan": {"type": "array", "minItems": 3, "maxItems": 5, "items": content_chapter},
            "visual_contract": visual_contract,
            "dialogue_anchors": dialogue_anchors,
            "retrieval_check": STRING,
            "closing_takeaway": STRING,
            "misconceptions": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "caveats": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "content_hash": SHA,
        },
        [
            "video_id", "section_id", "order", "title", "audience", "duration_tier",
            "duration_minutes", "prerequisite_ids", "thesis", "owns", "references",
            "excludes", "definitions", "claim_ids", "source_ids", "worked_example_id", "teaching_beats",
            "visual_spine", "chapter_plan", "visual_contract", "dialogue_anchors",
            "retrieval_check", "closing_takeaway",
            "misconceptions", "caveats", "content_hash",
        ],
    )
    content_approval_gate = strict_object(
        {
            "required": {"const": True},
            "separate_from_runpod_authorization": {"const": True},
            "status": {"enum": ["not_requested", "review_requested", "changes_requested", "approved", "stale"]},
            "required_artifact_types": {"type": "array", "minItems": 6, "items": STRING, "uniqueItems": True},
            "review_manifest_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
            "approved_by": {"type": ["string", "null"]},
            "approved_at": {"type": ["string", "null"], "format": "date-time"},
            "approval_identity": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
        },
        [
            "required", "separate_from_runpod_authorization", "status",
            "required_artifact_types", "review_manifest_sha256", "approved_by",
            "approved_at", "approval_identity",
        ],
    )
    episode_content_bible = strict_object(
        {
            "schema_version": {"const": DEEP_SERIES_SCHEMA_VERSION},
            "status": {"const": "proposed"},
            "generated_date": STRING,
            "baseline_episode_count": {"const": DEEP_SERIES_EPISODE_COUNT},
            "sections": {"type": "array", "minItems": 8, "items": content_section},
            "stable_examples": {"type": "array", "minItems": 6, "items": stable_example},
            "dialogue_rules": {"type": "array", "minItems": 8, "items": STRING, "uniqueItems": True},
            "approval_gate": content_approval_gate,
            "episodes": {"type": "array", "minItems": DEEP_SERIES_EPISODE_COUNT, "maxItems": DEEP_SERIES_EPISODE_COUNT, "items": content_episode},
            "content_hash": SHA,
        },
        [
            "schema_version", "status", "generated_date", "baseline_episode_count", "sections",
            "stable_examples", "dialogue_rules", "approval_gate", "episodes", "content_hash",
        ],
    )
    readiness_summary = strict_object(
        {
            "episodes": {"type": "integer", "minimum": 1},
            "sections": {"type": "integer", "minimum": 1},
            "stable_examples": {"type": "integer", "minimum": 1},
            "glossary_terms": {"type": "integer", "minimum": 1},
            "used_claims": {"type": "integer", "minimum": 1},
            "used_sources": {"type": "integer", "minimum": 1},
            "minimum_runtime_minutes": {"type": "number", "minimum": 1},
            "maximum_runtime_minutes": {"type": "number", "minimum": 1},
            "planned_chapters": {"type": "integer", "minimum": 1},
            "visual_systems": {"type": "integer", "minimum": 1},
            "minimum_distinct_compositions": {"type": "integer", "minimum": 1},
            "minimum_meaningful_state_changes": {"type": "integer", "minimum": 1},
        },
        [
            "episodes", "sections", "stable_examples", "glossary_terms", "used_claims", "used_sources",
            "minimum_runtime_minutes", "maximum_runtime_minutes", "planned_chapters",
            "visual_systems", "minimum_distinct_compositions", "minimum_meaningful_state_changes",
        ],
    )
    readiness_gate = strict_object(
        {"gate_id": STRING, "status": {"enum": ["pass", "pending"]}, "detail": STRING},
        ["gate_id", "status", "detail"],
    )
    partition_decision = strict_object(
        {"scope": STRING, "decision": STRING, "rationale": STRING},
        ["scope", "decision", "rationale"],
    )
    readiness_episode = strict_object(
        {
            "video_id": STRING,
            "status": {"const": "ready_for_authoring"},
            "chapter_count": {"type": "integer", "minimum": 3},
            "visual_system_count": {"type": "integer", "minimum": 3},
            "minimum_distinct_compositions": {"type": "integer", "minimum": 1},
            "minimum_meaningful_state_changes": {"type": "integer", "minimum": 1},
            "claim_count": {"type": "integer", "minimum": 1},
            "source_count": {"type": "integer", "minimum": 1},
            "cross_reference_count": {"type": "integer", "minimum": 1},
        },
        [
            "video_id", "status", "chapter_count", "visual_system_count",
            "minimum_distinct_compositions", "minimum_meaningful_state_changes",
            "claim_count", "source_count", "cross_reference_count",
        ],
    )
    content_readiness_audit = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "audit_date": STRING,
            "status": {"const": "ready_for_script_and_storyboard_authoring"},
            "bible_content_hash": SHA,
            "summary": readiness_summary,
            "gates": {"type": "array", "minItems": 6, "items": readiness_gate},
            "partition_decisions": {"type": "array", "minItems": 5, "items": partition_decision},
            "corrections_applied": {"type": "array", "minItems": 4, "items": STRING, "uniqueItems": True},
            "open_gates": {"type": "array", "minItems": 4, "items": STRING, "uniqueItems": True},
            "episodes": {"type": "array", "minItems": DEEP_SERIES_EPISODE_COUNT, "maxItems": DEEP_SERIES_EPISODE_COUNT, "items": readiness_episode},
            "audit_sha256": SHA,
        },
        [
            "schema_version", "audit_date", "status", "bible_content_hash", "summary",
            "gates", "partition_decisions", "corrections_applied", "open_gates",
            "episodes", "audit_sha256",
        ],
    )
    render_job = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION}, "job_id": STRING, "video_id": STRING,
            "brief_hash": SHA, "resolved_spec_hash": SHA, "renderer_revision": GIT_SHA,
            "orchestrator_revision": GIT_SHA, "evidence_hashes": {"type": "object", "additionalProperties": SHA},
            "format": strict_object(
                {"name": STRING, "width": {"type": "integer"}, "height": {"type": "integer"}, "fps": {"type": "integer"}},
                ["name", "width", "height", "fps"],
            ),
            "resources": strict_object(
                {"class": STRING, "cpu": {"type": "integer"}, "ram_gb": {"type": "integer"}, "gpu": {"type": "boolean"}},
                ["class", "cpu", "ram_gb", "gpu"],
            ),
            "cache_identity": SHA, "output_directory": STRING,
            "retry_policy": strict_object(
                {"max_attempts": {"type": "integer", "minimum": 1}, "timeout_seconds": {"type": "integer", "minimum": 1}, "retry_same_hash_only": {"const": True}},
                ["max_attempts", "timeout_seconds", "retry_same_hash_only"],
            ),
        },
        ["schema_version", "job_id", "video_id", "brief_hash", "resolved_spec_hash", "renderer_revision",
         "orchestrator_revision", "evidence_hashes", "format", "resources", "cache_identity", "output_directory", "retry_policy"],
    )
    render_result = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION}, "job_id": STRING, "cache_identity": SHA,
            "status": {"enum": ["passed", "failed"]}, "outputs": {"type": "object", "additionalProperties": SHA},
            "technical_observations": {"type": "object"}, "preview_frame_hashes": {"type": "object", "additionalProperties": SHA},
            "warnings": {"type": "array", "items": {"type": "string"}}, "passed": {"type": "boolean"},
        }, ["schema_version", "job_id", "cache_identity", "status", "outputs", "technical_observations", "preview_frame_hashes", "warnings", "passed"],
    )
    batch_manifest = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION}, "batch_id": STRING, "status": {"enum": ["draft", "proposed", "approved"]},
            "jobs": STRINGS, "job_hashes": {"type": "object", "additionalProperties": SHA},
            "aggregate": strict_object(
                {"videos": {"type": "integer"}, "estimated_cpu_minutes": {"type": "number"}, "max_parallel": {"type": "integer"}},
                ["videos", "estimated_cpu_minutes", "max_parallel"],
            ),
            "resume": strict_object(
                {"completed_cache_identities": STRINGS, "continuation_token": SHA},
                ["completed_cache_identities", "continuation_token"],
            ),
            "approval_identity": SHA,
        }, ["schema_version", "batch_id", "status", "jobs", "job_hashes", "aggregate", "resume", "approval_identity"],
    )
    visual_data = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION}, "id": STRING, "chart_type": STRING,
            "claim_ids": STRINGS, "source_ids": STRINGS, "values": {"type": "array", "minItems": 1, "items": {"type": "object"}},
            "transformation": strict_object(
                {"script": STRING, "description": STRING, "input_hashes": {"type": "object", "additionalProperties": SHA}},
                ["script", "description", "input_hashes"],
            ),
        }, ["schema_version", "id", "chart_type", "claim_ids", "source_ids", "values", "transformation"],
    )
    artifact_ref = strict_object(
        {"path": STRING, "sha256": SHA}, ["path", "sha256"]
    )
    chapter_ref = strict_object(
        {"chapter_id": STRING, "path": STRING, "sha256": SHA},
        ["chapter_id", "path", "sha256"],
    )
    episode_format = strict_object(
        {
            "name": STRING,
            "width": {"type": "integer", "minimum": 640},
            "height": {"type": "integer", "minimum": 360},
            "fps": {"type": "integer", "minimum": 24, "maximum": 60},
            "video_codec": {"const": "h264"},
            "pixel_format": {"const": "yuv420p"},
            "audio_codec": {"const": "aac"},
        },
        ["name", "width", "height", "fps", "video_codec", "pixel_format", "audio_codec"],
    )
    episode = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "episode_id": STRING,
            "title": STRING,
            "promise": STRING,
            "audience": STRING,
            "target_duration_s": {"type": "number", "minimum": 360, "maximum": 480},
            "actual_duration_s": {"type": ["number", "null"], "exclusiveMinimum": 0},
            "format": episode_format,
            "claim_ids": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "source_ids": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "chapters": {"type": "array", "minItems": 2, "items": chapter_ref},
            "narration_contract": artifact_ref,
            "caption_contract": artifact_ref,
            "release_manifest_path": STRING,
            "status": {"enum": ["draft", "planned", "rendered", "passed", "released"]},
            "content_hash": SHA,
        },
        [
            "schema_version", "episode_id", "title", "promise", "audience",
            "target_duration_s", "actual_duration_s", "format", "claim_ids", "source_ids",
            "chapters", "narration_contract", "caption_contract", "release_manifest_path",
            "status", "content_hash",
        ],
    )
    chapter = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "episode_id": STRING,
            "chapter_id": STRING,
            "order": {"type": "integer", "minimum": 1},
            "title": STRING,
            "purpose": STRING,
            "planned_duration_s": {"type": "number", "minimum": 15, "maximum": 120},
            "claim_ids": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "source_ids": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "renderer_brief": artifact_ref,
            "narration_cue_ids": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "dependencies": STRINGS,
            "status": {"enum": ["draft", "planned", "rendered", "passed"]},
            "cache_identity": SHA,
        },
        [
            "schema_version", "episode_id", "chapter_id", "order", "title", "purpose",
            "planned_duration_s", "claim_ids", "source_ids", "renderer_brief",
            "narration_cue_ids", "dependencies", "status", "cache_identity",
        ],
    )
    narration_cue = strict_object(
        {
            "cue_id": STRING,
            "chapter_id": STRING,
            "scene_id": STRING,
            "text": STRING,
            "text_sha256": SHA,
            "word_count": {"type": "integer", "minimum": 1},
            "planned_start_s": {"type": "number", "minimum": 0},
            "planned_end_s": {"type": "number", "exclusiveMinimum": 0},
        },
        [
            "cue_id", "chapter_id", "scene_id", "text", "text_sha256", "word_count",
            "planned_start_s", "planned_end_s",
        ],
    )
    narration_contract = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "episode_id": STRING,
            "provider": {"enum": ["local_windows_sapi", "manual_recording", "off"]},
            "voice": STRING,
            "dialect": STRING,
            "rate": {"type": "integer", "minimum": -10, "maximum": 10},
            "volume": {"type": "integer", "minimum": 0, "maximum": 100},
            "sample_rate": {"enum": [16000, 22050, 24000, 44100, 48000]},
            "channels": {"const": 1},
            "pronunciations": {"type": "object", "additionalProperties": {"type": "string"}},
            "cues": {"type": "array", "minItems": 1, "items": narration_cue},
            "status": {"enum": ["planned", "rendered", "approved"]},
            "content_hash": SHA,
        },
        [
            "schema_version", "episode_id", "provider", "voice", "dialect", "rate",
            "volume", "sample_rate", "channels", "pronunciations", "cues", "status",
            "content_hash",
        ],
    )
    caption_cue = strict_object(
        {
            "cue_id": STRING,
            "chapter_id": STRING,
            "scene_id": STRING,
            "text": STRING,
            "start_s": {"type": "number", "minimum": 0},
            "end_s": {"type": "number", "exclusiveMinimum": 0},
        },
        ["cue_id", "chapter_id", "scene_id", "text", "start_s", "end_s"],
    )
    caption_contract = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "episode_id": STRING,
            "language": STRING,
            "format": {"const": "webvtt"},
            "delivery": {"enum": ["sidecar", "burned_in", "both"]},
            "readability": strict_object(
                {
                    "max_characters_per_line": {"type": "integer", "minimum": 24, "maximum": 60},
                    "max_lines": {"type": "integer", "minimum": 1, "maximum": 3},
                    "minimum_display_s": {"type": "number", "minimum": 0.5},
                },
                ["max_characters_per_line", "max_lines", "minimum_display_s"],
            ),
            "cues": {"type": "array", "minItems": 1, "items": caption_cue},
            "status": {"enum": ["planned", "rendered", "approved"]},
            "content_hash": SHA,
        },
        [
            "schema_version", "episode_id", "language", "format", "delivery",
            "readability", "cues", "status", "content_hash",
        ],
    )
    release_chapter = strict_object(
        {
            "chapter_id": STRING,
            "video": artifact_ref,
            "audio": artifact_ref,
            "duration_s": {"type": "number", "exclusiveMinimum": 0},
        },
        ["chapter_id", "video", "audio", "duration_s"],
    )
    release_qa = strict_object(
        {
            "duration_in_range": {"type": "boolean"},
            "chapter_count_matches": {"type": "boolean"},
            "video_contract_passed": {"type": "boolean"},
            "audio_contract_passed": {"type": "boolean"},
            "caption_contract_passed": {"type": "boolean"},
            "all_hashes_verified": {"type": "boolean"},
            "passed": {"type": "boolean"},
            "notes": {"type": "array", "items": {"type": "string"}},
        },
        [
            "duration_in_range", "chapter_count_matches", "video_contract_passed",
            "audio_contract_passed", "caption_contract_passed", "all_hashes_verified",
            "passed", "notes",
        ],
    )
    release_manifest = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "release_id": STRING,
            "episode_id": STRING,
            "created_at": STRING,
            "status": {"enum": ["draft", "qa_passed", "approved", "published"]},
            "inputs": {"type": "object", "minProperties": 1, "additionalProperties": SHA},
            "chapters": {"type": "array", "minItems": 2, "items": release_chapter},
            "outputs": strict_object(
                {
                    "video": artifact_ref,
                    "captions": artifact_ref,
                    "audio_master": artifact_ref,
                },
                ["video", "captions", "audio_master"],
            ),
            "qa": release_qa,
            "content_hash": SHA,
        },
        [
            "schema_version", "release_id", "episode_id", "created_at", "status",
            "inputs", "chapters", "outputs", "qa", "content_hash",
        ],
    )
    return {
        "source_registry.schema.json": source_registry,
        "claim_registry.schema.json": claim_registry,
        "glossary.schema.json": glossary,
        "video_brief.schema.json": video_brief,
        "video_catalog.schema.json": video_catalog,
        "series_map.schema.json": series_map,
        "episode_content_bible.schema.json": episode_content_bible,
        "content_readiness_audit.schema.json": content_readiness_audit,
        "render_job.schema.json": render_job,
        "render_result.schema.json": render_result,
        "batch_manifest.schema.json": batch_manifest,
        "visual_data.schema.json": visual_data,
        "episode.schema.json": episode,
        "chapter.schema.json": chapter,
        "narration_contract.schema.json": narration_contract,
        "caption_contract.schema.json": caption_contract,
        "release_manifest.schema.json": release_manifest,
    }


SOURCE_SPECS = [
    ("src-correction-report", "deliverables_n22_24/corrections_2026_08_25/CM_BENCHMARK_AUDIT_CORRECTION_REPORT_2026-08-25.md", "correction_report", "current", "2026-08-25", [], []),
    ("src-b2b4-v3-inference", "deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v3_inference.csv", "machine_csv", "current", "2026-08-25", ["src-b2b4-v2-summary"], []),
    ("src-b2b4-v3-summary", "deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v3_summary.csv", "machine_csv", "current", "2026-08-25", ["src-b2b4-v2-summary"], []),
    ("src-b2b4-v3-audit", "deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v3_audit.json", "machine_json", "current", "2026-08-25", [], []),
    ("src-b2b4-v2-summary", "deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v2_summary.csv", "machine_csv", "superseded", "2026-08-25", [], ["src-b2b4-v3-summary"]),
    ("src-runpod-correction-report", "deliverables_n22_24/correction_runpod_2026_08_25/CM_CORRECTED_RUNPOD_PASS_2026-08-25.md", "replication_report", "accepted", "2026-08-25", [], []),
    ("src-runpod-pod1-raw", "deliverables_n22_24/correction_runpod_2026_08_25/pod1_juhyi9fpkolh1g/deliverables_n22_24/pod_out/symmetric/current_raw.csv", "machine_csv", "accepted", "2026-08-25", [], []),
    ("src-runpod-pod2-raw", "deliverables_n22_24/correction_runpod_2026_08_25/pod2_bzpf7a9j6hmt6v/deliverables_n22_24/pod_out/symmetric/current_raw.csv", "machine_csv", "accepted", "2026-08-25", [], []),
    ("src-runpod-pod3-raw", "deliverables_n22_24/correction_runpod_2026_08_25/pod3_0yki225dikil17/deliverables_n22_24/pod_out/symmetric/current_raw.csv", "machine_csv", "accepted", "2026-08-25", [], []),
    ("src-epfl-report", "deliverables_n22_24/CM_GAP_EPFL_VALIDATION_2026-08-03.md", "validation_report", "accepted", "2026-08-03", [], []),
    ("src-epfl-summary", "deliverables_n22_24/CM_gap_epfl_summary_2026_08_03.csv", "machine_csv", "accepted", "2026-08-03", [], []),
    ("src-epfl-results", "deliverables_n22_24/cm_gap_epfl_results_2026_08_03.json", "machine_json", "accepted", "2026-08-03", [], []),
    ("src-claim-map", "deliverables_n22_24/CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md", "claim_map", "reference", "2026-08-03", [], ["src-correction-report"]),
    ("src-claim-addendum", "deliverables_n22_24/CM_BENCHMARK_REFRESH_CLAIM_MAP_ADDENDUM_2026-08-03.md", "claim_map", "reference", "2026-08-03", [], ["src-correction-report"]),
    ("src-repo-readme", "README.md", "documentation", "current", "2026-08-30", [], []),
    ("src-cm-exprlib", "cm_exprlib.py", "implementation", "current", "2026-08-31", [], []),
    ("src-cm-ir", "cm_ir.py", "implementation", "current", "2026-08-30", [], []),
    ("src-cm-build", "cm_build.py", "implementation", "current", "2026-08-30", [], []),
    ("src-cm-build-lazy", "cm_build_lazy.py", "implementation", "current", "2026-08-31", [], []),
    ("src-cm-build-pair", "cm_build_pair.py", "implementation", "current", "2026-08-31", [], []),
    ("src-cm-parallel", "cm_parallel.py", "implementation", "current", "2026-08-31", [], []),
    ("src-bitset", "bitset_backend.py", "implementation", "current", "2026-08-30", [], []),
    ("src-recognition-readme", "docs/recognition/README.md", "research_index", "current", "2026-08-30", [], []),
    ("src-recognition-roadmap", "docs/recognition/LEARNING_ROADMAP.md", "research_roadmap", "current", "2026-08-30", [], []),
    ("src-recognition-register", "docs/recognition/experiment_register.json", "machine_json", "current", "2026-08-30", [], []),
    ("src-crse-milestone-c", "docs/recognition/LEARNING_MILESTONE_C_2026_08_29.md", "research_report", "current", "2026-08-29", [], []),
    ("src-c12-report", "docs/recognition/LEARNING_MILESTONE_C12_ADAPTIVE_EXACT_DISPATCHER_2026_08_30.md", "research_report", "current", "2026-08-30", [], []),
    ("src-c16-report", "docs/recognition/LEARNING_MILESTONE_C16_EXACT_SCREENED_GF2_2026_08_30.md", "research_report", "current", "2026-08-31", [], []),
    ("src-c16-linux-v2-final", "docs/recognition/c16_linux_confirmation/RUNPOD_C16_PACKAGE_V2_FINAL_VERIFICATION_20260831.json", "machine_json", "current", "2026-08-31", [], []),
    ("src-c17-report", "docs/recognition/LEARNING_MILESTONE_C17_GF2_TASK_DISPATCHER_2026_08_31.md", "research_report", "current", "2026-08-31", [], []),
    ("src-c17-results", "docs/recognition/learning_milestone_c17_gf2_task_dispatcher_results.json", "machine_json", "current", "2026-08-31", [], []),
    ("src-c18-report", "docs/recognition/LEARNING_MILESTONE_C18_INDEPENDENT_GF2_TRANSFER_2026_08_31.md", "research_report", "current", "2026-08-31", [], []),
    ("src-c18-results", "docs/recognition/learning_milestone_c18_independent_gf2_transfer_results.json", "machine_json", "current", "2026-08-31", [], []),
    ("src-c19-report", "docs/recognition/LEARNING_MILESTONE_C19_CHEAP_GF2_WORK_POLICY_2026_08_31.md", "research_report", "current", "2026-08-31", [], []),
    ("src-c19-results", "docs/recognition/learning_milestone_c19_cheap_gf2_work_policy_results.json", "machine_json", "current", "2026-08-31", [], []),
    ("src-c20-report", "docs/recognition/LEARNING_MILESTONE_C20_COMPILED_GF2_POLICY_VTR_TAIL_2026_08_31.md", "research_report", "current", "2026-08-31", [], []),
    ("src-c20-results", "docs/recognition/learning_milestone_c20_compiled_gf2_policy_vtr_tail_results.json", "machine_json", "current", "2026-08-31", [], []),
    ("src-c21-report", "docs/recognition/LEARNING_MILESTONE_C21_TASK_MATCHED_GF2_METHOD_TABLE_2026_08_31.md", "research_report", "current", "2026-08-31", [], []),
    ("src-c21-results", "docs/recognition/learning_milestone_c21_task_matched_gf2_method_table_results.json", "machine_json", "current", "2026-08-31", [], []),
    ("src-c22-report", "docs/recognition/C22_SOURCE_PACKED_GF2_PORTFOLIO_IMPLEMENTATION_2026_08_31.md", "implementation_report", "current", "2026-08-31", [], []),
    ("src-c22-policy", "docs/recognition/c22_source_portfolio_policy.json", "machine_json", "current", "2026-08-31", [], []),
    ("src-c23-report", "docs/recognition/LEARNING_MILESTONE_C23_FRESH_YOSYS_GF2_TABLE_2026_08_31.md", "research_report", "current", "2026-08-31", [], []),
    ("src-c23-results", "docs/recognition/learning_milestone_c23_fresh_yosys_gf2_table_results.json", "machine_json", "current", "2026-08-31", [], []),
    ("src-runpod-handoff", "docs/runpod/RUNPOD-SETUP-HANDOFF-2026-08-28.md", "safety_handoff", "current", "2026-08-28", [], []),
    ("src-video-factory", "docs/video_factory/factory.py", "implementation", "current", "2026-08-31", [], []),
    ("src-deep-series-authoring", "docs/video_factory/deep_series_authoring.py", "implementation", "current", "2026-08-31", [], []),
    ("src-deep-series-chapter-compiler", "docs/video_factory/deep_series_chapter_compiler.py", "implementation", "current", "2026-08-31", [], []),
    ("src-deep-series-pilot", "docs/video_factory/deep_series_pilot.py", "implementation", "current", "2026-08-31", [], []),
]


def build_source_registry() -> dict[str, Any]:
    entries = []
    for source_id, rel, kind, status, date, supersedes, superseded_by in SOURCE_SPECS:
        path = REPO_ROOT / rel
        if not path.is_file():
            raise FactoryError(f"required evidence source is missing: {rel}")
        entries.append({
            "id": source_id, "path": rel, "sha256": file_sha256(path), "type": kind,
            "status": status, "date": date, "supersedes": supersedes, "superseded_by": superseded_by,
        })
    return {
        "schema_version": SCHEMA_VERSION, "generated_date": GENERATED_DATE,
        "repository_head": "7a18649e96ea4e9fd1994d0a4310947f60dee64a", "sources": entries,
    }


def source(source_id: str, locator: str) -> dict[str, str]:
    return {"source_id": source_id, "locator": locator}


def claim(
    claim_id: str, allowed: str, plain: str, technical: str, kind: str, status: str,
    scope: str, boundary: str, comparator: str, direction: str, uncertainty: str,
    refs: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "id": claim_id, "allowed_wording": allowed, "plain_wording": plain,
        "technical_wording": technical, "type": kind, "status": status, "scope": scope,
        "measurement_boundary": boundary, "comparator": comparator,
        "ratio_direction": direction, "uncertainty": uncertainty, "sources": refs,
    }


def build_claim_registry() -> dict[str, Any]:
    claims = [
        claim(
            "boolean-decision-semantics",
            "A Boolean expression maps each complete assignment of its variables to one Boolean output.",
            "A Boolean rule turns each assignment into true or false.",
            "The expression classes evaluate a declared variable assignment to one Boolean value; enumerating assignments exposes the denoted Boolean function.",
            "fact", "confirmed", "current Boolean expression implementation", "semantics",
            "none", "not a ratio", "none",
            [source("src-cm-exprlib", "Expr hierarchy and eval methods")],
        ),
        claim(
            "expression-function-distinction",
            "An expression is syntax; its Boolean function is the assignment-to-output mapping it denotes, so different expressions may denote the same function.",
            "The written rule and the function it computes are not the same object.",
            "Structural form is an expression property, while exact equality is established by matching outputs over the declared assignment universe.",
            "fact", "confirmed", "Boolean expression and exact-output contracts", "semantics",
            "none", "not a ratio", "none",
            [source("src-cm-exprlib", "expression node definitions and evaluation"), source("src-repo-readme", "correctness checks and backend outputs")],
        ),
        claim("cm-explicit-definition", "An explicit CM is a dense truth-layout representation over a declared row/column variable split.", "A CM lays a Boolean function's truth values out as a matrix.", "The public dense output arranges assignments over row variables R and column variables C, with fixed values applied at evaluation.", "fact", "confirmed", "implemented dense output contract", "representation", "none", "not a ratio", "none", [source("src-cm-build", "compile_expr_to_cm and eval_cm_boolean")]),
        claim("live-vs-ambient", "Live support and ambient variables are distinct: live variables affect the function, while ambient variables may still define the displayed assignment universe.", "A function can depend on fewer variables than the table around it.", "Materialization tracks live variables after fixed bindings; an ambient layout may include axes absent from node.vars.", "fact", "confirmed", "CM IR materialization semantics", "representation", "none", "not a ratio", "none", [source("src-cm-ir", "CMNode.vars and materialize_cm"), source("src-cm-build", "R/C/fixed output contract")]),
        claim("cm-ir-definition", "CM-IR is a canonicalized, interned shared DAG intermediate representation.", "CM-IR stores reusable computation structure, not a dense matrix.", "compile_expr_to_cm_ir builds canonical CMNode structures with interning, simplification, sharing-aware associative flattening, and optional persistent caching.", "fact", "confirmed", "current implementation", "representation", "none", "not a ratio", "none", [source("src-cm-ir", "CMIRBuilder and compile_expr_to_cm_ir")]),
        claim("dense-vs-ir-distinct", "An explicit dense CM and CM-IR are different artifacts with different construction, storage, and evaluation boundaries.", "The matrix is an output layout; CM-IR is a reusable program graph.", "materialize_cm produces a dense array, whereas evaluate_compiled/materialize_hybrid_no_reinflate can return packed or flat truth output without dense CM reinflation.", "fact", "confirmed", "current implementation", "representation and evaluation", "none", "not a ratio", "none", [source("src-cm-ir", "CompiledExpr, evaluate_compiled, materialize_cm, materialize_hybrid_no_reinflate"), source("src-cm-build", "compile_expr_to_cm")]),
        claim(
            "cm-output-contract-boundary",
            "CM, CM-IR, SAT, BDD, minimization, and symbolic algebra answer different questions and must be compared under matched output contracts.",
            "A truth layout, a reusable program, and a satisfying assignment are different outputs.",
            "Complete-vector extraction, point queries, restrictions, satisfiability, equivalence, minimization, and symbolic rewriting charge different work and cannot be ranked as one task.",
            "fact", "confirmed", "implemented backend and task contracts", "output contract",
            "task-matched backends", "not a ratio", "scope dependent",
            [source("src-repo-readme", "Backend summary and output columns"), source("src-recognition-readme", "Milestone D and E task summaries")],
        ),
        claim(
            "cm-ir-sharing-roots",
            "CM-IR interns reusable nodes in a DAG and can retain roots that share descendants.",
            "Several outputs can point into one shared computation graph.",
            "CMNode identity and interning permit repeated structure to be stored once while compiled roots retain the requested outputs.",
            "fact", "confirmed", "current CM-IR implementation", "representation",
            "none", "not a ratio", "none",
            [source("src-cm-ir", "CMNode, CMIRBuilder, interning and compiled roots")],
        ),
        claim(
            "cm-ir-normalization-interning",
            "Normalization, canonical structural keys, and interning are distinct stages: rewrites choose a canonical form, keys identify it, and interning reuses an existing node.",
            "First make equivalent structure look alike; then reuse the matching node.",
            "Associative/commutative normalization and simplification affect canonical structure; structural digests identify it; intern tables reuse the resulting CMNode.",
            "fact", "confirmed", "current CM-IR compiler", "representation construction",
            "none", "not a ratio", "implementation-defined",
            [source("src-cm-ir", "_structural_digest, CMIRBuilder normalization and interning")],
        ),
        claim(
            "cm-ir-persistence-contract",
            "Persistent CM-IR reuse is keyed by canonical identity and must verify version/input identity before accepting a cached artifact.",
            "A saved graph is reusable only while its identity still matches.",
            "The persistent IR cache records deterministic structural identity; changed structure or versioned inputs must miss or invalidate rather than reuse stale state.",
            "fact", "confirmed", "current process-local persistent cache and versioned research contracts", "persistence and invalidation",
            "none", "not a ratio", "cache scope is implementation-specific",
            [source("src-cm-ir", "persistent cache and structural hash"), source("src-recognition-readme", "Milestone D3 and D6 summaries")],
        ),
        claim(
            "raw-ast-ablation-definition",
            "Raw AST evaluation follows the expression tree without structural sharing or sharing-aware associative flattening, so it is an ablation rather than the strongest generic comparator.",
            "A raw tree may repeat the same work each time the subtree appears.",
            "The corrected comparator ladder separates raw AST, plain structural CSE, sharing-aware CSE-flat, and CM-IR.",
            "fact", "confirmed", "corrected comparator ladder", "mechanism",
            "raw AST", "not a ratio", "none",
            [source("src-correction-report", "What CSE means and comparator correction"), source("src-bitset", "compile_expr_cse")],
        ),
        claim("cse-definition", "Common subexpression elimination computes repeated expression subtrees once and reuses them.", "CSE shares repeated work.", "Plain structural CSE interns repeated subtrees but may retain binary associative chains.", "fact", "confirmed", "comparator definition used by correction", "mechanism", "plain CSE", "not a ratio", "none", [source("src-correction-report", "What CSE means")]),
        claim("cse-flat-definition", "Sharing-aware CSE-flat additionally flattens eligible associative chains while preserving shared nodes.", "CSE-flat shares repeats and safely widens associative chains.", "The primary comparator is sharing-aware structural CSE with flatten=True; it is stronger than the raw-AST ablation and plain unflattened CSE.", "fact", "confirmed", "corrected comparator contract", "mechanism", "CSE-flat", "not a ratio", "none", [source("src-correction-report", "What CSE means and Corrected issues 3"), source("src-b2b4-v3-audit", "primary_comparator")]),
        claim("cm-extra-transformations", "CM-IR can add canonical normalization and merging beyond the transformations shared with CSE-flat.", "CM-IR and CSE-flat overlap, but CM-IR may normalize more structure.", "Any observed difference must be attributed to the actual instruction/operation reductions on the scoped workload, not to the CM label alone.", "interpretation", "confirmed", "corrected mechanism interpretation", "mechanism", "CSE-flat", "not a ratio", "workload dependent", [source("src-correction-report", "What CSE means")]),
        claim(
            "flat-program-lowering",
            "A shared DAG can be lowered once into a linear postorder FlatProgram with one instruction per unique DAG node; this flat program is distinct from CSE-flat's source transformation and from packed storage.",
            "A shared graph can become an ordered instruction list without becoming a matrix.",
            "compile_flat lowers unique CMNode DAG nodes into dependency-ordered slots and operations; CSE-flat describes sharing-aware associative flattening before or during comparator compilation, while bigint/words describe execution storage.",
            "fact", "confirmed", "current flat evaluator implementation", "lowering and execution representation",
            "CSE-flat and packed evaluators", "not a ratio", "none",
            [source("src-bitset", "FlatProgram and compile_flat")],
        ),
        claim(
            "operation-metrics-distinct",
            "Flat instruction count, argument edges, executed primitive operations, and peak live buffers are different metrics and may not be substituted for one another or for elapsed time.",
            "One instruction can perform more than one primitive operation.",
            "program_metrics defines flat_instructions, argument_edges, executed_word_ops, executed_bigint_ops, and peak_live_word_buffers separately.",
            "fact", "confirmed", "current deterministic program metrics", "mechanism accounting",
            "flat execution backends", "not a ratio", "not elapsed-time evidence",
            [source("src-bitset", "FlatProgram and program_metrics")],
        ),
        claim(
            "memory-traffic-hypothesis",
            "A graph or instruction reduction may change allocation or memory traffic, but memory traffic is a proposed mechanism unless it is measured directly on the declared workload.",
            "Fewer operations may help memory behavior, but the diagram is not a measurement.",
            "Peak live buffers and release schedules are deterministic structural metrics; claims about hardware memory traffic require separate measurement and must remain visibly hypothetical here.",
            "hypothesis", "exploratory", "mechanism explanation only", "conceptual mechanism",
            "flat execution backends", "not a ratio", "not directly measured",
            [source("src-bitset", "release_after, word plan and program_metrics"), source("src-correction-report", "mechanism wording boundary")],
        ),
        claim("b2b4-v3-kernel", "On the exactly counterbalanced B2/B4 V3 workload, formula-balanced bare CM/CSE-flat was 0.8906 with a formula-cluster 95% interval [0.8741, 0.9073].", "Compiled bare CM was modestly faster than CSE-flat on this one corrected workload.", "CM/CSE-flat=0.8905696773, paired formula-cluster percentile-bootstrap 95% CI [0.8740654100,0.9072717742], 216 formula clusters and 264 rows.", "measurement", "confirmed", "B2/B4 V3 formulas on one Windows run", "compiled evaluator kernel after compilation", "sharing-aware CSE-flat", "CM/CSE-flat; below one favors CM", "formula-cluster bootstrap; does not model between-run or between-machine variation", [source("src-b2b4-v3-inference", "overall/all/all cm_current_over_cse_flat_current"), source("src-b2b4-v3-audit", "statistical_inference.headline")]),
        claim("b2b4-v3-k16", "The B2/B4 V3 bare CM/CSE-flat advantage narrowed toward k=16: formula-balanced ratio 0.9612 [0.9290, 0.9942].", "The measured gap got smaller at support 16.", "At live_k=16, CM/CSE-flat=0.9612336537 with formula-cluster 95% CI [0.9289740604,0.9941768792].", "measurement", "confirmed", "B2/B4 V3 live support k=16", "compiled evaluator kernel after compilation", "sharing-aware CSE-flat", "CM/CSE-flat; below one favors CM", "formula-cluster bootstrap within one run", [source("src-b2b4-v3-inference", "live_k/all/16 cm_current_over_cse_flat_current")]),
        claim("b2b4-runpod-replication", "Across three guarded CPU pods, row-weighted bare CM/CSE-flat was 0.9026–0.9126 overall and 0.9746–0.9766 at k=16.", "Three Linux CPU replications put the overall ratio near 0.909, with a much smaller k=16 gap.", "Immutable pod raw CSVs reproduce overall geomeans 0.9026, 0.9118, and 0.9126; k=16 0.9766, 0.9746, and 0.9752.", "measurement", "confirmed", "B2/B4 corrected three-pod CPU replication", "compiled evaluator kernel after compilation", "sharing-aware CSE-flat", "CM/CSE-flat; below one favors CM", "descriptive across three machines; post-hoc per-pod formula intervals are separate", [source("src-runpod-pod1-raw", "cm_current_over_cse_flat_current"), source("src-runpod-pod2-raw", "cm_current_over_cse_flat_current"), source("src-runpod-pod3-raw", "cm_current_over_cse_flat_current")]),
        claim("public-wrapper-slower", "The public CM wrapper was slower than CSE-flat in the corrected comparison.", "The easy public call did not produce an end-to-end speedup.", "Formula-balanced local wrapper/CSE-flat was 3.0941 [2.8831,3.3108]; the earlier corrected three-pod row-weighted ratios were approximately 2.78–2.81 overall.", "measurement", "confirmed", "corrected B2/B4 comparison", "public wrapper complete truth-output call", "sharing-aware CSE-flat", "CM wrapper/CSE-flat; above one disfavors CM", "local formula-cluster interval plus descriptive pod replication", [source("src-b2b4-v3-inference", "overall/all/all cm_wrapper_over_cse_flat_current"), source("src-runpod-correction-report", "CM versus sharing-aware CSE-flat")]),
        claim("epfl-parity", "On the accepted EPFL AND/INV workload, CM/CSE-flat was 0.9998 with a circuit-clustered 95% interval [0.9747, 1.0249].", "On this circuit workload, the two compiled kernels were at parity.", "Blocked CM/CSE-flat geomean=0.9998256739, circuit-clustered bootstrap CI [0.9746915270,1.0249051889], n=129.", "measurement", "confirmed", "EPFL AND/INV cones, semantic support 8–16, one Windows machine", "compiled evaluator kernel after compilation", "sharing-aware CSE-flat", "CM/CSE-flat; interval spans one", "circuit-clustered bootstrap, 4000 draws", [source("src-epfl-summary", "all:primary_cm_cse_flat_blocked")]),
        claim("epfl-mechanism", "On the EPFL AND/INV workload, CM and CSE-flat had equal instruction and executed-operation counts, matching the parity mechanism prediction.", "There was no extra mergeable chain left for CM on this workload.", "Instruction and executed-operation ratios were both exactly 1.000; flattening already captured the available associative reduction.", "measurement", "confirmed", "EPFL AND/INV cones", "compiled program structure and kernel", "sharing-aware CSE-flat", "CM/CSE-flat operation ratios", "exact count equality on accepted corpus", [source("src-epfl-report", "Results and mechanism check")]),
        claim("epfl-preparation-cost", "EPFL CM preparation was 4.11x CSE-flat preparation; 55 of 129 cases never broke even under the retained calculation.", "One-time CM preparation can erase a kernel gain unless the artifact is reused enough.", "Preparation multiple geomean 4.11; finite break-even median 174.5 over 74 cases, with 55/129 never reaching break-even.", "measurement", "confirmed", "accepted EPFL workload", "preparation and modeled reuse break-even", "sharing-aware CSE-flat", "CM prep/CSE-flat prep; above one disfavors CM", "descriptive retained calculation", [source("src-epfl-report", "Results table")]),
        claim("no-universal-winner", "Current evidence does not support a universal claim that CM beats CSE-flat.", "The winner depends on workload and measurement boundary.", "B2/B4 V3 shows a scoped bare-kernel reduction; EPFL shows parity; the public wrapper remains slower.", "interpretation", "confirmed", "cross-study synthesis", "multiple boundaries kept separate", "CSE-flat", "not a single ratio", "scopes are intentionally not pooled", [source("src-correction-report", "Bottom line"), source("src-epfl-report", "Scope and verdict")]),
        claim("ratio-label-rule", "Every ratio must state numerator, denominator, workload, measurement boundary, and uncertainty; below one favors CM only for CM/comparator.", "A ratio has no honest direction without its labels.", "No chart may infer direction from position or color alone.", "fact", "confirmed", "video evidence contract", "all numeric scenes", "explicit", "declared per ratio", "declared per ratio", [source("src-correction-report", "Bottom line and scope")]),
        claim("selector-no-width-rule", "The corrected focused k=13–15 study did not justify a universal width-only selector change.", "Width alone did not choose the best engine reliably.", "The predeclared gate failed on reused validation because one CM row reached catastrophic regret; no selector change was made.", "measurement", "negative", "corrected selector-gap study", "selection policy", "flat versus words engine", "regret; above one is worse", "reused validation is not untouched held-out evidence", [source("src-correction-report", "Selector results after correction")]),
        claim("variants-implemented", "Eager, lazy, pair-aware, hybrid, partial-hybrid, parallel, and packed/word paths must be described only within their implemented and tested contracts.", "The project has several execution paths, but their names do not imply one winner.", "Current documentation and code distinguish dense wrappers, delayed materialization, pair-aware collapse, hybrid dispatch, partial-hybrid structure preservation, parallel materialization, and packed evaluators.", "fact", "confirmed", "current repository implementation", "implementation status", "none", "not a ratio", "performance varies by workload", [source("src-repo-readme", "What the project does and Backend summary"), source("src-cm-ir", "materialize modes"), source("src-bitset", "packed evaluators")]),
        claim(
            "eager-lazy-contract",
            "The eager and lazy CM paths differ in when aligned dense work is materialized, not in the Boolean function returned.",
            "Eager performs layout work earlier; lazy defers it until the result is needed.",
            "The eager builder constructs through the standard path, while the lazy builder aligns subexpressions and materializes once at the end; both remain subject to exact-output checks.",
            "fact", "confirmed", "current eager/lazy implementations", "construction timing",
            "eager versus lazy CM", "not a ratio", "no performance ranking",
            [source("src-repo-readme", "eager and lazy paths and technical notes"), source("src-cm-build-lazy", "lazy compilation and materialization")],
        ),
        claim(
            "pair-aware-contract",
            "Pair-aware collapse applies only after fixed assignments leave one live row variable and one live column variable; otherwise it forwards to the standard path.",
            "The pair shortcut needs exactly one live variable on each matrix axis.",
            "The experimental pair compiler honors fixed assignments, records eligibility/collapse diagnostics, and falls back without changing semantics when the token-pair boundary is not met.",
            "fact", "confirmed", "current experimental pair-aware implementation", "construction eligibility",
            "standard CM path", "not a ratio", "experimental implementation status",
            [source("src-repo-readme", "CM pair backend summary and technical notes"), source("src-cm-build-pair", "pair eligibility and fallback")],
        ),
        claim(
            "hybrid-partial-contract",
            "Hybrid and partial-hybrid materialization are distinct dispatch modes: whole-subtree collapse and child-level structure-preserving dispatch must not be conflated.",
            "One mode can collapse a whole result; the other can keep structure and choose per child.",
            "CM-IR materialization diagnostics distinguish full collapse, bitset/numpy node decisions, child dispatch, and no-reinflation output paths.",
            "fact", "confirmed", "current CM-IR materialization modes", "materialization strategy",
            "hybrid versus partial-hybrid", "not a ratio", "workload dependent",
            [source("src-cm-ir", "materialize modes and diagnostics"), source("src-repo-readme", "Backend summary")],
        ),
        claim(
            "parallel-materialization-contract",
            "Parallel CM partitions eligible materialization work and deterministically assembles the result; parallel availability does not imply a speedup after scheduling and transport overhead.",
            "Independent matrix regions can run in worker lanes and still return in one fixed order.",
            "The parallel path applies minimum-work guards, row/chunk partitioning, optional shared memory, and deterministic output reconstruction around the same exact materialization contract.",
            "fact", "confirmed", "current parallel CM implementation", "materialization strategy",
            "serial CM materialization", "not a ratio", "no universal performance claim",
            [source("src-cm-parallel", "compile_expr_to_cm_parallel and work guards"), source("src-repo-readme", "CM parallel backend summary")],
        ),
        claim(
            "packed-truth-vector-contract",
            "Packed bigint and machine-word evaluators store the same ordered truth vector in different exact execution layouts with explicit masks and tail handling.",
            "Many truth values can travel together in one integer or several machine words.",
            "The packed backends define variable ordering, full masks, word plans, tail masking, and exact conversion independently of dense CM layout.",
            "fact", "confirmed", "current packed evaluator implementations", "execution representation",
            "bigint and word-packed truth vectors", "not a ratio", "backend choice remains workload dependent",
            [source("src-bitset", "bitset environments, word plans and evaluators")],
        ),
        claim("exactness-gates", "Corrected benchmark rows required frozen truth verification and equality across eligible timed arms before performance evidence was accepted.", "Timing rows counted only after exact outputs matched.", "The V3 audit records 264 rows and zero packed mismatches; corrected EPFL verification similarly fails closed on truth digests.", "fact", "confirmed", "corrected benchmark protocols", "correctness gate outside performance claim", "all eligible arms", "not a ratio", "hash/equality gate", [source("src-b2b4-v3-audit", "row_count and packed_mismatch_count"), source("src-correction-report", "EPFL order and frozen truth verification")]),
        claim(
            "toolbox-output-contracts",
            "CM, CSE, BitSet, BDD, SAT, Espresso, and SymPy expose different representation, evaluation, decision, minimization, and symbolic-manipulation contracts.",
            "These tools answer different questions, so the first choice is the required output.",
            "The repository's backend summary separates CM materialization, structural CSE, packed evaluation, ROBDD/BDD construction, SAT-style decision tasks, Espresso minimization, and SymPy symbolic simplification with exact validation outside timing.",
            "fact", "confirmed", "implemented and documented repository interfaces", "tool output contract",
            "task-matched tools", "not a ratio", "optional dependencies and bounded interfaces vary",
            [source("src-repo-readme", "Backend summary, toggles and output columns"), source("src-recognition-readme", "Milestone E1 and E2 summaries")],
        ),
        claim(
            "configuration-revision-workload",
            "Configuration workloads combine constraints, related revisions, and repeated queries; identical-output cache hits are insufficient without source/version identity.",
            "Feature models change over time, so reuse must know what changed, not only what output happened to match.",
            "Milestone D6 evaluates adjacent feature-model revisions with exact invalidation and refuses equal-output but changed-source cases as cache hits.",
            "fact", "confirmed", "bounded natural configuration revisions", "versioned task and cache boundary",
            "cold and version-aware exact paths", "not a ratio", "bounded retained workload",
            [source("src-recognition-readme", "Milestone D6 summary")],
        ),
        claim(
            "circuit-cone-support",
            "A circuit cone's semantic support and gate structure determine the exact function under study; nominal circuit size is not a substitute for cone support.",
            "A large circuit can contain a smaller cone whose output depends on only part of it.",
            "The accepted EPFL workload uses AND/INV cones selected and checked under declared semantic-support and exact-output contracts.",
            "fact", "confirmed", "accepted EPFL AND/INV cone workload", "workload definition",
            "none", "not a ratio", "corpus and support range scoped",
            [source("src-epfl-report", "cone selection, semantic support and exact verification")],
        ),
        claim(
            "policy-rule-revision-workload",
            "Policy/rule systems with related revisions can reuse proved structure only when matching, proof, invalidation, and overhead are charged at the declared task boundary.",
            "A reusable rule is useful only if proving, finding, and applying it costs less than the work it saves.",
            "Milestones D2-D7 separate proved rules, versioned caches, profitability gates, natural incidence, adjacent revisions, and bounded normalization with exact fallback.",
            "fact", "confirmed", "bounded CRSE rule and revision studies", "overhead-inclusive task boundary",
            "no rewrite and direct exact paths", "not a ratio", "no general deployment claim",
            [source("src-recognition-readme", "Milestones D2 through D7 summaries")],
        ),
        claim(
            "representation-decision-factors",
            "Representation choice should begin with required output, live support, reuse, update pattern, exact operations, preparation cost, and evidence scope rather than a method label.",
            "Choose from the question and workload, not from a universal ranking.",
            "Complete vectors, points, restrictions, satisfiability, equivalence, revisions, and repeated execution imply different eligible backends and charged boundaries.",
            "interpretation", "confirmed", "cross-contract decision guidance", "decision policy",
            "task-matched backends", "not a ratio", "must remain evidence scoped",
            [source("src-correction-report", "scope and boundary conclusions"), source("src-recognition-readme", "Milestone D and E task routing summaries")],
        ),
        claim(
            "source-provenance-contract",
            "A video production artifact is reproducible only when source locators, source hashes, claim IDs, script/storyboard identities, render jobs, outputs, and approval identities remain linked.",
            "Changing an evidence source must invalidate every downstream video artifact that depended on it.",
            "The factory recomputes source hashes and content identities, while the RunPod package binds allowlisted inputs, jobs, results, and cleanup authorization to immutable hashes.",
            "fact", "confirmed", "CM video factory and RunPod safety contract", "production provenance",
            "none", "not a ratio", "hash identity does not itself establish scientific truth",
            [source("src-video-factory", "source registry, brief_content_hash and validation"), source("src-runpod-handoff", "hash-bound authorization and verification")],
        ),
        claim("crse-experimental", "The CRSE recognition program is experimental; no learned model is promoted.", "The learning work has useful engineering results and retained failures, but no production model.", "The register separates measured slices, exact controls, negative transfer, held or failed criteria, and no-promotion decisions.", "fact", "not_promoted", "current recognition program", "scientific promotion", "exact deterministic controls", "not a ratio", "per-milestone frozen splits and criteria", [source("src-recognition-readme", "What is implemented"), source("src-recognition-register", "research tracks and status reasons")]),
        claim(
            "crse-initial-learning-slice",
            "The initial Milestone C compared matched matrix MLP, matrix CNN, source-DAG GNN, fused, and contrastive-retrieval models: graph/fused arms learned the generated representation signal, retrieval missed its gate, real EPFL transfer was poor, exact rejection preserved outputs, and no model was promoted.",
            "The first learned comparison found a generated-data signal but failed retrieval and real-source transfer, so exact verification and fallback stayed in charge.",
            "Ten bounded model artifacts were saved and reloaded under matched budgets. Generated classification, contrastive retrieval, and the all-negative EPFL transfer slice retained separate criteria; independent truth-vector checks admitted or rejected proposals with zero final semantic mismatches.",
            "measurement", "negative", "initial CRSE Milestone C generated and EPFL transfer slices", "learned proposal plus exact acceptance",
            "matched matrix/graph/fused arms and advice-off exact fallback", "per frozen criterion", "bounded generated functions and all-negative EPFL slice",
            [
                source("src-crse-milestone-c", "Result, classification evidence, contrastive retrieval, and remaining work"),
                source("src-recognition-register", "initial C classifier/retrieval and negative-transfer results"),
            ],
        ),
        claim(
            "crse-current-program-map",
            "The current CRSE program spans learned proposals, exact subclass recognition, task routing, proved rules, representation dispatch, BDD/SAT guidance, exact verification, negative controls, and explicit promotion decisions.",
            "CRSE is a research program with several exact and learned branches, not one model.",
            "The current register retains 18 research tracks and milestone evidence through C16, D10, E1, and E2; each track remains scoped to its measured slices and pending work.",
            "fact", "confirmed", "current recognition register", "research-program structure",
            "exact controls and learned proposal paths", "not a ratio", "track completion varies",
            [source("src-recognition-register", "tracks R01-R18, status reasons, and retained milestone results")],
        ),
        claim("crse-c2-negative", "Milestone C2's learned representation and size-transfer criteria failed while the exact CM detector remained perfect.", "The learned decomposition detector did not transfer, even though the exact control worked.", "Independent verification recomputed retained tables and model decisions without error; learned criteria failed and no model was promoted.", "measurement", "negative", "Milestone C2 frozen generated/held-out slices", "recognition evaluation", "exact CM detector", "per frozen criterion", "limited target/domain scope", [source("src-recognition-readme", "Milestone C2 summary"), source("src-recognition-register", "retained C2 exact-control and negative learned results")]),
        claim("crse-c3-c5-negative", "Natural decomposition, direct-cut, and variable-conditioned learned arms improved some slices but failed the required held-out transfer/promotion criteria.", "Better scores on some circuits did not become reliable held-out cuts.", "C3–C5 retain exact verification, weak accepted-positive recall, held-out square failures, and learned paths slower than exact ANF.", "measurement", "negative", "Milestones C3–C5 natural circuit-disjoint studies", "recognition plus exact acceptance", "exact ANF", "varies by milestone", "circuit-family transfer remained limited", [source("src-recognition-readme", "Milestones C3, C4, C5 summaries"), source("src-recognition-register", "retained C3-C5 natural-cut and promotion results")]),
        claim("crse-c6-advance", "Milestone C6's packed exact source-ANF core advanced, but its gate and production path did not.", "A deterministic packed core improved, without promoting the whole system.", "Packed/cached cores achieved retained median and p95 gains over truth-vector ANF; the validation-frozen gate missed confirmatory p95 by 1.4%.", "measurement", "revised", "Milestone C6 frozen EPFL splits", "exact recognition core and gate", "truth-vector ANF", "speedup stated as comparator/core", "bounded one-program slice", [source("src-recognition-readme", "Milestone C6 summary"), source("src-recognition-register", "retained C6 core/gate results")]),
        claim(
            "crse-c7-c8-transfer",
            "C7 and C8 retained exact source-ANF identities across an independent Yosys-derived family and Linux, while backend profitability remained representation- and machine-sensitive.",
            "The exact result transferred, but the fastest exact backend did not stay the same everywhere.",
            "Independent source cases and a separately provisioned Linux CPU reproduced canonical partitions; sparse set, packed, and bitset paths retained different median and tail behavior.",
            "measurement", "revised", "Milestones C7-C8 exact transfer studies", "exact recognition and cross-machine execution",
            "set, packed and bitset exact controls", "per reported speedup", "bounded source families and machines",
            [source("src-recognition-register", "R06/R03 retained C7-C8 exact-transfer results")],
        ),
        claim(
            "crse-c9-c11-negative",
            "C9 static routing, C10 guarded restart, and C11 one-pass conversion preserved exact labels and partitions but remained slower than the best fixed arm on their retained evaluation splits; C10 nevertheless protected the catastrophic p95 tail.",
            "Three exact routing designs improved tail safety and avoided duplicate prefix work, but none became a profitable default.",
            "C9's frozen static tree failed transfer, C10 restarted exactly after a frozen product budget, and C11 converted the set prefix in place so the DAG prefix was not evaluated twice. Independent replay retained zero semantic mismatches.",
            "measurement", "negative", "Milestones C9-C11 exact representation-routing progression", "exact recognition and overhead-inclusive routing",
            "best fixed exact set/packed/bitset arm", "speedup over best fixed; below one loses", "bounded C6/C7 and fresh Yosys-derived splits",
            [
                source("src-c12-report", "What was implemented and Results table for C9-C11"),
                source("src-recognition-register", "R03 and R18 C9-C12 exact-path and negative-control results"),
            ],
        ),
        claim(
            "crse-c12-c16-exact",
            "C12-C16 advanced exact dispatch, tail protection, task guards, and reconstructible GF(2) artifacts; C16 preserved exact artifact identity and measured about 3.545x local and 3.178x Linux whole-path screening gains while retaining a tiny-case regression and fresh-family limits.",
            "Exact dispatch and screened GF(2) artifacts passed locally and on Linux, but guarded fallback and broader-family testing remain necessary.",
            "C12-C14 cover adaptive exact dispatch, an in-kernel tail sentinel, and task-aware guarding. C15-C16 add reconstructible CM/GF(2) artifacts and screen 64 partitions before bounded materialization. The corrected 18-file Linux v2 package produced 360 timing rows with zero semantic or artifact mismatches.",
            "measurement", "revised", "Milestones C12-C16 bounded exact studies", "exact recognition, dispatch and whole-path cost",
            "frozen exhaustive materializer and advice-off exact paths", "local and Linux screened/exhaustive whole-path ratios", "bounded 40-case Yosys family plus structured/dense controls",
            [
                source("src-recognition-register", "R06 retained C12-C16 results"),
                source("src-c16-report", "Exact results, local timing, corrected v2 package, and interpretation"),
                source("src-c16-linux-v2-final", "criteria, speedup, semantic_mismatches, artifact_mismatches, and second_machine_gate"),
            ],
        ),
        claim(
            "crse-c17-c20-exact-policy",
            "C17-C20 kept exhaustive and screened CM/GF(2) artifacts exact while moving from a guarded dispatcher through independent VTR transfer and a frozen LogikBench work policy to a constant-folded screened selector; aggregate results improved, but per-case, freshness, and machine-scope limits kept production disabled.",
            "The exact arms agreed, while successive milestones isolated wrapper overhead, source transfer, a trivial frozen policy, and a retrospective small-support timing outlier.",
            "C17 failed its slow-tail and minimum gates despite a 3.831x aggregate result. C18 transferred exactly to 73 independent VTR cones at 8.378x aggregate but retained a single-round 0.621x minimum. C19 selected an always-screened leaf before confirmation and passed its 24-case LogikBench gate at 2.769x aggregate and 0.972x minimum. C20 constant-folded that leaf and reached 1.760x aggregate and 1.463x minimum on nine retrospective rounds over the 11 small C18 controls; no production call site changed.",
            "measurement", "revised", "Milestones C17-C20 exact-arm routing and transfer studies", "whole-task exact arm selection and policy overhead",
            "direct exhaustive and direct screened exact CM/GF(2)", "speedup over exhaustive; below one loses", "bounded Windows studies; C18 cross-family, C19 cluster-separated confirmation, C20 retrospective same-machine tail replay",
            [
                source("src-c17-report", "Local results and Decision"),
                source("src-c17-results", "summary, gates, verification, and production_promotion"),
                source("src-c18-report", "Exact transfer and timing; Verification and decision"),
                source("src-c18-results", "summary, verification, and production_promotion"),
                source("src-c19-report", "Sealed confirmation; Independent verification and decision"),
                source("src-c19-results", "confirmation, policy, verification, and production_promotion"),
                source("src-c20-report", "Retrospective VTR control; Verification and decision"),
                source("src-c20-results", "summary, verification, retrospective, and production_promotion"),
            ],
        ),
        claim(
            "crse-c21-c22-task-matched",
            "C21 compared seven methods under one exhaustive-best GF(2) artifact contract: packed source ANF was narrowly fastest at 3.007x over exhaustive and 1.006x over screened CM, while the per-case oracle left only 1.059x headroom before routing cost; C22 froze that arm behind exact fallback and shadow checks but added no fresh timing or promotion evidence.",
            "Task matching showed a small source-packed representation advantage, not broad evidence that proposal methods avoid exact completion or that a learned router is worthwhile.",
            "All 3,360 C21 executions returned the exhaustive-best artifact. Packed source ANF proposed a component on 10 of 96 cases and abstained on 86; fresh BDD was negative for this single-query lifecycle. The C22 policy selects the source-packed screened arm, restores exhaustive CM when advice is off or input is refused, and remains implementation-only pending fresh evaluation.",
            "measurement", "not_promoted", "C21 retrospective task-matched table and C22 implementation boundary", "best-exact-artifact whole-task comparison",
            "exhaustive CM and direct screened CM", "aggregate and per-case speedup over exhaustive/screened", "96 retrospective LogikBench cones on one Windows machine; C22 has no fresh timing",
            [
                source("src-c21-report", "Exact task-matched results; Support-width and routing headroom; Decision"),
                source("src-c21-results", "summary, methods, verification, and production_promotion"),
                source("src-c22-report", "Exact boundary, Frozen policy, and Status"),
                source("src-c22-policy", "selected_arm, advice_off_arm, exact_fallback_arm, status, and production_promotion"),
            ],
        ),
        claim(
            "crse-c23-fresh-yosys-transfer",
            "C23 transferred the unchanged seven-method exhaustive-best GF(2) task to 48 previously unused Yosys generator-family functions: all 1,680 timed executions returned the same exact artifact, packed source ANF led at 3.306x over exhaustive and only 1.006x over screened CM, and the per-case oracle left 1.047x headroom before routing cost.",
            "Fresh-source transfer confirmed the screened-CM and packed-source fixed paths, while leaving too little routing headroom and too much per-case variation for production promotion.",
            "The first freeze was preserved as incomplete after exposing a task-contract error above support six. The task-complete v2 set restricts supports to 3-6, excludes prior truth overlaps, covers eight unused generator families, and independently replays every source and scalar oracle. Compiled screened CM still regressed on individual cases, fresh single-query BDD remained negative, and the unchanged Linux package had not been uploaded when this source was frozen.",
            "measurement", "not_promoted", "C23 fresh Yosys-family exact seven-method transfer", "exhaustive-best GF(2) artifact on task-complete supports",
            "exhaustive CM and direct screened CM", "aggregate and per-case speedup over exhaustive/screened", "48 fresh same-machine Yosys-family functions at supports 3-6; second-machine replication pending",
            [
                source("src-c23-report", "Fresh corpus and task contract; Fresh local results; Decision and next work"),
                source("src-c23-results", "dataset, verification, summary, production_promotion, and linux_replication"),
            ],
        ),
        claim("crse-d-mixed", "Milestone D task routing helped restrictions and repeated work but slowed complete-vector requests; dense-CM construction and per-instance rewrite proof were negative.", "Routing helped some tasks and hurt others.", "Construction, routing, proof, kernel, cache, and audit costs were measured separately.", "measurement", "revised", "Milestone D generated task-computation study", "end-to-end task boundaries", "direct, CSE, CM-IR, dense CM", "per task", "bounded generated workload", [source("src-recognition-readme", "Milestone D summary"), source("src-recognition-register", "retained D task-routing results")]),
        claim(
            "crse-d2-d7-evolution",
            "D2-D7 moved from one proved macro through versioned rule packs, profitability gates, natural incidence, real revisions, and bounded normalization; exactness advanced more consistently than profitability.",
            "The rule system became safer and more complete, but extra exact rewrites did not always save time.",
            "The milestones separately charge matching, proof, cache identity, rule incidence, reuse count, revision invalidation, overlap, termination, and second-pass overhead.",
            "measurement", "revised", "Milestones D2-D7 bounded rule studies", "overhead-inclusive rule task",
            "no rewrite and exact direct controls", "per milestone", "no universal rewrite policy",
            [source("src-recognition-readme", "Milestones D2-D7 summaries"), source("src-recognition-register", "retained D2-D7 rule, cache, revision, and normalization results")],
        ),
        claim("crse-d8-negative", "The frozen one-pass rewrite result changed from 1.050x on Windows to 0.929x on Linux, so unconditional one-pass rewriting was not promoted.", "The rewrite looked helpful on one machine and lost on Linux.", "Exactness and rule incidence reproduced, but profitability did not transfer; the Linux result is a retained negative control.", "measurement", "negative", "Milestone D8 frozen Linux confirmation", "overhead-inclusive one-pass rewrite", "no rewrite", "reported as speedup; below one loses", "one bounded cross-machine confirmation", [source("src-recognition-readme", "Milestone D8 summary"), source("src-recognition-register", "retained D8 Linux exactness and profitability result")]),
        claim("crse-d9-not-promoted", "Milestone D9's frozen policy abstained on all evaluation workloads and preserved exactness, but the charged gate remained slower and no rewrite policy was promoted.", "Abstention avoided bad rewrites but still cost time.", "Exact factoring reduced operations, unconditional one pass lost, and the all-abstain gate measured 0.982x versus no rewrite.", "measurement", "not_promoted", "Milestone D9 circuit-disjoint split", "charged policy plus task execution", "no rewrite", "speedup versus no rewrite", "bounded evaluation split", [source("src-recognition-readme", "Milestone D9 summary"), source("src-recognition-register", "retained D9 abstention and charged no-promotion result")]),
        claim(
            "crse-d10-negative",
            "D10 added indexed screening, exact versioned replay, and four proved rule families, but whole-path profitability remained negative.",
            "The indexed rule engine found and verified more structure without beating the no-rewrite path overall.",
            "Mux, comparator, carry, and XOR-cancellation rules use strict decrease, provenance, cache replay, and exact fallback; the retained whole-path criterion did not promote the engine.",
            "measurement", "negative", "Milestone D10 indexed rule engine", "overhead-inclusive rule execution",
            "no rewrite", "per retained result", "bounded rule pack and workloads",
            [source("src-recognition-readme", "Milestone D10 summary"), source("src-recognition-register", "D10 retained result")],
        ),
        claim(
            "crse-e1-e2-guidance",
            "E1 and E2 added exact BDD-order and SAT/equivalence guidance with advice-off fallback; learned advice did not establish a general timing win.",
            "The system can recommend exact BDD or SAT strategies, but safe fallback remains the authority.",
            "E1 separates BDD node, build, restriction, and equivalence objectives; E2 separates CNF construction, solver lifecycle, assumptions, and equivalence miters with independent witness/core checks.",
            "measurement", "not_promoted", "Milestones E1-E2 bounded guidance studies", "task-aware exact guidance",
            "fixed exact strategies and advice-off fallback", "per task", "bounded solver and BDD studies",
            [source("src-recognition-readme", "Milestones E1 and E2 summaries"), source("src-recognition-register", "E1-E2 retained results")],
        ),
        claim("conceptual-label-rule", "Teaching diagrams, proposed mechanisms, and hypotheses must be visibly labeled and may not be presented as measured traces.", "An animation can explain an idea without pretending it was observed.", "Conceptual scene metadata and visible status remain separate from measurement claims and result cards.", "fact", "confirmed", "video evidence contract", "editorial/visual status", "none", "not a ratio", "not applicable", [source("src-recognition-readme", "program scope and promotion boundaries"), source("src-correction-report", "workload-specific interpretation")]),
    ]
    return {"schema_version": SCHEMA_VERSION, "generated_date": GENERATED_DATE, "claims": claims}


def build_glossary() -> dict[str, Any]:
    entries = [
        ("Boolean expression", "", "A written Boolean rule built from variables and operators.", "A syntax tree whose evaluation maps a complete variable assignment to one Boolean value.", "The expression is syntax; it is not the same object as the function it denotes.", ["src-cm-exprlib"]),
        ("Boolean function", "", "The true-or-false output produced for every assignment.", "The assignment-to-output mapping denoted by one or more equivalent Boolean expressions.", "Different expression trees can denote the same Boolean function.", ["src-cm-exprlib"]),
        ("Abstract syntax tree", "AST", "A tree representation of the written expression.", "A syntax node graph before structural sharing; the raw-AST ablation may recompute repeated subtrees.", "Raw AST is not the strongest generic comparator.", ["src-cm-exprlib", "src-correction-report"]),
        ("Correspondence matrix", "CM", "A matrix layout of a Boolean function's truth values.", "A dense output indexed by assignments over declared row and column variable sets.", "Not every use of the label CM refers to this dense artifact.", ["src-cm-build", "src-repo-readme"]),
        ("CM intermediate representation", "CM-IR", "A reusable graph program for Boolean computation.", "A canonicalized and interned CMNode DAG with simplification, sharing-aware flattening, and multiple evaluation/materialization paths.", "CM-IR is not the same object as the dense matrix returned by materialize_cm.", ["src-cm-ir"]),
        ("Live support", "", "Variables that can change the function's output.", "The variable set retained by an expression/IR node after simplification and fixed bindings.", "Live support can be smaller than the ambient or syntactic variable universe.", ["src-cm-ir"]),
        ("Ambient universe", "", "Variables included in the surrounding assignment layout.", "The declared row/column or corpus variable axes, including variables that may be semantically dead for one function.", "Ambient count is not a substitute for live support.", ["src-cm-build", "src-correction-report"]),
        ("Common subexpression elimination", "CSE", "Compute a repeated subtree once and reuse it.", "Structural sharing/interning of repeated expression subtrees.", "Plain CSE does not necessarily flatten eligible associative chains.", ["src-correction-report"]),
        ("Sharing-aware CSE-flat", "CSE-flat", "CSE plus safe flattening of associative chains.", "The corrected strong generic comparator: structural sharing with flatten=True while preserving shared nodes.", "It is stronger than raw AST and plain unflattened CSE.", ["src-correction-report", "src-b2b4-v3-audit"]),
        ("Flat instruction program", "FlatProgram", "An ordered list of loads and operations lowered from a shared graph.", "A linear postorder execution representation with one instruction per unique DAG node and explicit slot dependencies.", "FlatProgram is not CSE-flat and is not the same thing as packed word storage.", ["src-bitset"]),
        ("Preparation", "", "One-time work to build a reusable compiled artifact.", "Compiler/canonicalizer time measured separately from evaluation.", "Preparation must not be blended into a bare-kernel ratio unless explicitly declared.", ["src-epfl-report"]),
        ("Evaluator kernel", "", "Repeated execution after the program and environment already exist.", "The compiled-program measurement boundary used by the corrected CM/CSE-flat ratios.", "It is not a public-wrapper or end-to-end result.", ["src-correction-report"]),
        ("Public wrapper", "", "The convenient public call including surrounding work.", "The complete wrapper boundary reported separately from bare compiled evaluation.", "A faster kernel does not imply a faster wrapper.", ["src-correction-report"]),
        ("Break-even reuse", "", "How many evaluations are needed to repay extra preparation.", "The solution to accumulated preparation plus per-evaluation cost under a declared model.", "Some workloads never break even.", ["src-epfl-report"]),
        ("Packed bitset", "", "Many truth values stored in machine words or a big integer.", "An exact truth-vector execution backend with explicit ordering and width masking.", "Packed execution is not automatically a dense CM.", ["src-bitset"]),
        ("CRSE", "", "The repository's experimental recognition and computation-selection research program.", "A project label for frozen milestone studies with learned proposal paths, exact controls, verification, and explicit promotion decisions.", "The current authoritative sources do not supply an expansion; scripts must not invent one, and engineering verification is not scientific generalization or deployment.", ["src-recognition-readme", "src-recognition-register"]),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "entries": [
            {"term": term, "expansion": expansion, "plain_definition": plain,
             "technical_definition": technical, "common_confusion": confusion, "source_ids": sources}
            for term, expansion, plain, technical, confusion, sources in entries
        ],
    }


def episode_content_hash(
    episode: dict[str, Any], claims_by_id: dict[str, Any], sources_by_id: dict[str, Any]
) -> str:
    payload = dict(episode)
    payload.pop("content_hash", None)
    referenced_sources = sorted({
        ref["source_id"]
        for claim_id in episode["claim_ids"]
        for ref in claims_by_id[claim_id]["sources"]
    })
    evidence = {source_id: sources_by_id[source_id]["sha256"] for source_id in referenced_sources}
    return canonical_sha256({"episode": payload, "evidence": evidence})


def content_bible_hash(bible: dict[str, Any]) -> str:
    """Hash immutable curriculum content without mutable review state."""
    return canonical_sha256({
        key: value for key, value in bible.items()
        if key not in {"content_hash", "approval_gate"}
    })


def content_approval_identity(bible: dict[str, Any]) -> str:
    gate = bible["approval_gate"]
    return canonical_sha256({
        "content_hash": bible["content_hash"],
        "review_manifest_sha256": gate["review_manifest_sha256"],
        "approved_by": gate["approved_by"],
        "approved_at": gate["approved_at"],
    })


def load_content_review_request() -> dict[str, Any] | None:
    """Load the versioned local review request; it never implies execution approval."""
    path = FACTORY_ROOT / "deep_series" / "content_review_request.json"
    if not path.is_file():
        return None
    request = json.loads(path.read_text("utf-8"))
    expected_keys = {
        "schema_version", "status", "requested_at", "bible_content_hash",
        "review_manifest_sha256", "content_approval_authorizes_remote_or_paid_work",
    }
    if set(request) != expected_keys:
        raise FactoryError("content-review-request:unknown-or-missing-fields")
    if request["schema_version"] != DEEP_SERIES_SCHEMA_VERSION:
        raise FactoryError("content-review-request:schema-version")
    if request["status"] != "review_requested":
        raise FactoryError("content-review-request:status")
    if request["content_approval_authorizes_remote_or_paid_work"] is not False:
        raise FactoryError("content-review-request:execution-authorization")
    if not SHA256_RE.fullmatch(request["bible_content_hash"]):
        raise FactoryError("content-review-request:bible-hash")
    if not SHA256_RE.fullmatch(request["review_manifest_sha256"]):
        raise FactoryError("content-review-request:manifest-hash")
    manifest_path = FACTORY_ROOT / "deep_series" / "content_review_packet" / "manifest.json"
    if not manifest_path.is_file():
        raise FactoryError("content-review-request:manifest-missing")
    manifest = json.loads(manifest_path.read_text("utf-8"))
    if manifest.get("review_manifest_sha256") != request["review_manifest_sha256"]:
        raise FactoryError("content-review-request:manifest-mismatch")
    return request


CHAPTER_TITLE_OVERRIDES = {
    "instruction-operations-memory": [
        "The layers that are usually conflated",
        "From shared DAG to flat instruction tape",
        "Instructions, executions, and lifetime counts",
        "Packed storage versus hardware-traffic hypotheses",
        "Boundary, retrieval, and transfer",
    ],
    "exact-comparison-protocol": [
        "Four validity threats, four safeguards",
        "Exact-output admission",
        "Order and timing design",
        "Formula clusters and uncertainty",
        "Controlled threats and remaining limits",
    ],
    "toolbox-map": [
        "Start with the requested output",
        "Representations and reusable evaluators",
        "Solvers, minimizers, and symbolic systems",
        "Build, query, extraction, and reuse costs",
        "Route the task without a podium",
    ],
    "configuration-models": [
        "Configuration questions and output contracts",
        "Constraints on the stable feature model",
        "Adjacent revisions and invalidation",
        "Cold, cached, and refused-reuse paths",
        "Limits and representation choices",
    ],
    "recognition-question": [
        "The falsifiable CRSE question",
        "Stable proposal, verifier, fallback, and promotion graph",
        "A/B foundations and the initial matrix/graph/fused/retrieval baseline",
        "Eighteen tracks with exactness, transfer, cost, and promotion gates",
    ],
    "recognition-c3-c5": [
        "One frozen recognition question",
        "C3 natural positives and matched negatives",
        "C4 complete cuts and ranking",
        "C5 equivariant variable heads",
        "Held-out transfer, charged cost, and non-promotion",
    ],
    "recognition-c6": [
        "From learned proposals to an exact source core",
        "C6 packed source ANF",
        "C7 independent-family transfer",
        "C8 Linux exact transfer and backend sensitivity",
        "What advanced and what stayed guarded",
    ],
    "recognition-c9-c11": [
        "Why exact routing can still lose",
        "Stable source example and fixed exact arms",
        "C9 static tree, C10 guarded restart, and C11 one-pass conversion",
        "Tail protection, overhead, and the bridge to C12",
    ],
    "recognition-c12-c16": [
        "The exact-dispatch problem",
        "C12 adaptive exact routing",
        "C13-C14 tail sentinel and task guard",
        "C15 reconstructible GF(2) artifacts",
        "C16 screened materialization: local and Linux evidence",
    ],
    "recognition-c17-c20": [
        "C17 exact task dispatch and the charged tiny-case tail",
        "C18 independent VTR transfer and the single-round minimum",
        "C19 phase-separated work-policy fitting and sealed confirmation",
        "C20 constant-folded policy and retrospective repeated-tail evidence",
        "What advanced, what changed, and why production stayed disabled",
    ],
    "recognition-c21-c22": [
        "One task contract: the exhaustive-best GF(2) artifact",
        "Seven exact methods and where their work is charged",
        "Packed source ANF, screened CM, and the narrow fixed-path result",
        "Proposal abstention, BDD lifecycle failure, and routing headroom",
        "C22 frozen source-packed portfolio with exact fallback",
    ],
    "recognition-c23": [
        "Why fresh source families are a separate evidence gate",
        "The failed broad-support freeze and the corrected task-complete v2 contract",
        "Seven unchanged exact methods on 48 unused Yosys-family functions",
        "Packed source ANF, screened CM, and the narrow fixed-path gap",
        "Per-case regressions, routing headroom, and the unpromoted decision",
    ],
    "recognition-d-tasks": [
        "D: four task contracts and mixed routing",
        "D2: one proved rule and exact control",
        "D3-D4: versioned rule packs and profitability gates",
        "D5-D6: natural incidence and real revisions",
        "D7: bounded normalization and charged loss",
    ],
    "recognition-e1-e2": [
        "Exact guidance is task-specific",
        "E1 BDD artifacts and order objectives",
        "E1 charged search and learned-selection result",
        "E2 SAT sessions, assumptions, and equivalence miters",
        "Advice-off fallback and cross-tool limits",
    ],
    "source-hash-reproduction": [
        "What reproducibility must bind",
        "Source locator through claim and content",
        "Script, storyboard, job, and media identity",
        "Downstream invalidation and two separate approvals",
    ],
}


REFERENCE_GROUPS = [
    ["conceptual-vs-measured", "measurement-boundaries", "exact-comparison-protocol", "source-hash-reproduction"],
    ["why-boolean-computation", "expression-truth-function", "live-support-ambient", "what-is-explicit-cm"],
    ["what-is-explicit-cm", "what-cm-does-not-claim", "explicit-cm-vs-cm-ir", "cm-ir-nodes-sharing"],
    ["cm-ir-nodes-sharing", "canonicalization-interning", "cm-ir-persistence", "source-hash-reproduction"],
    ["packed-words-selection", "eager-lazy", "pair-aware", "hybrid-partial", "parallel-cm"],
    ["raw-ast", "cse-plain-language", "cse-vs-cse-flat", "cm-ir-vs-cse-flat-mechanism", "instruction-operations-memory"],
    ["measurement-boundaries", "read-a-ratio", "scope-boundaries", "reuse-break-even", "exact-comparison-protocol", "no-fastest-chart"],
    ["b2b4-corrected", "b2b4-runpod", "exact-comparison-protocol", "correction-story"],
    ["epfl-parity", "scope-boundaries", "reuse-break-even", "no-fastest-chart", "circuits", "correction-story"],
    ["packed-words-selection", "selector-width-limit", "representation-decision"],
    ["toolbox-map", "configuration-models", "circuits", "policy-rule-systems", "representation-decision"],
    ["recognition-question", "recognition-c2", "recognition-c3-c5", "recognition-c6", "recognition-c9-c11", "recognition-c12-c16", "recognition-c17-c20", "recognition-c21-c22", "recognition-c23"],
    ["recognition-d-tasks", "recognition-d8", "recognition-d9", "recognition-d10", "policy-rule-systems"],
    ["recognition-e1-e2", "recognition-question", "toolbox-map", "representation-decision"],
    ["source-hash-reproduction", "conceptual-vs-measured", "exact-comparison-protocol", "correction-story"],
]


VISUAL_ASSET_KINDS_BY_SECTION = {
    "orientation": ["evidence-status legend", "matched conceptual/measured split screen", "source-and-boundary evidence panel"],
    "boolean-foundations": ["animated Boolean rule or expression", "assignment/truth-table construction", "matrix or representation transformation"],
    "cm-representations": ["animated shared DAG", "identity/interning ledger", "version/cache provenance flow"],
    "execution-materialization": ["synchronized execution trace", "storage/layout transformation", "exact-output comparison gate"],
    "comparators-lowering": ["matched comparator trace", "DAG-to-instruction transformation", "operation/storage counter ledger"],
    "measurement-evidence": ["measurement-boundary pipeline", "programmatically extracted chart or timeline", "scope/uncertainty evidence panel"],
    "toolbox-applications": ["domain-grounded system diagram", "task-to-output decision map", "revision/reuse or query timeline"],
    "recognition-research": ["milestone progression timeline", "proposal-verifier-fallback graph", "measured promotion/negative-result panel"],
    "provenance": ["source-to-release provenance graph", "hash invalidation animation", "content-versus-RunPod approval locks"],
}


def episode_chapter_plan(episode: dict[str, Any], example_title: str) -> list[dict[str, Any]]:
    beat_count = len(episode["teaching_beats"])
    visual_count = len(episode["visual_spine"])
    tier = episode["duration_tier"]
    if tier == "focused_explainer":
        beat_groups = [[1, 2], list(range(3, beat_count - 2)), list(range(beat_count - 2, beat_count + 1))]
        visual_groups = [[1], list(range(1, min(visual_count, 2) + 1)), [visual_count]]
        titles = [
            f"Question and definition: {episode['owns'][0]}",
            f"Worked example: {example_title}",
            "Boundary, retrieval, and transfer",
        ]
    elif tier == "core_episode":
        beat_groups = [[1, 2], [3], list(range(4, beat_count - 2)), list(range(beat_count - 2, beat_count + 1))]
        visual_groups = [[1], list(range(1, min(visual_count, 2) + 1)), list(range(2, visual_count + 1)), [visual_count]]
        titles = [
            f"Question and definition: {episode['owns'][0]}",
            f"Worked example: {example_title}",
            f"Mechanism: {'; '.join(episode['owns'][1:]) or episode['owns'][0]}",
            "Boundary, retrieval, and transfer",
        ]
    else:
        if beat_count == 8:
            beat_groups = [[1, 2], [3], [4], [5], [6, 7, 8]]
        else:
            beat_groups = [[1, 2], [3], [4, 5], [6], list(range(7, beat_count + 1))]
        visual_groups = [[1], [1, 2], [2, min(3, visual_count)], list(range(min(3, visual_count), visual_count + 1)), [visual_count]]
        middle = episode["owns"] + [episode["owns"][-1]] * 3
        titles = [
            f"Question and contract: {episode['owns'][0]}",
            f"Worked example: {example_title}",
            f"Mechanism I: {middle[1]}",
            f"Mechanism II: {'; '.join(middle[2:4])}",
            "Evidence boundary, retrieval, and transfer",
        ]
    titles = CHAPTER_TITLE_OVERRIDES.get(episode["video_id"], titles)
    purposes = [
        "Establish the concrete problem, promised distinction, and terms the viewer needs.",
        f"Construct `{episode['worked_example_id']}` progressively and orient every entity before analysis.",
        "Animate the first owned mechanism and connect each narration cue to a visible state change.",
        "Complete the comparison or evidence mechanism without merging distinct contracts.",
        "State the limitation, pause for retrieval, repair the misconception, and transfer the lesson.",
    ]
    if len(beat_groups) == 3:
        purposes = [purposes[0], purposes[1], purposes[4]]
    elif len(beat_groups) == 4:
        purposes = [purposes[0], purposes[1], purposes[2], purposes[4]]
    return [
        {
            "chapter_id": f"c{index:02d}",
            "working_title": titles[index - 1],
            "purpose": purposes[index - 1],
            "teaching_beat_numbers": beat_numbers,
            "visual_spine_indices": sorted(set(visual_groups[index - 1])),
        }
        for index, beat_numbers in enumerate(beat_groups, 1)
    ]


def episode_visual_contract(episode: dict[str, Any]) -> dict[str, Any]:
    tier_budgets = {
        "focused_explainer": (15, 38),
        "core_episode": (24, 60),
        "deep_episode": (42, 105),
    }
    minimum_compositions, minimum_state_changes = tier_budgets[episode["duration_tier"]]
    contextual = episode["section_id"] == "toolbox-applications"
    return {
        "minimum_distinct_compositions": minimum_compositions,
        "minimum_meaningful_state_changes": minimum_state_changes,
        "required_asset_kinds": [
            *VISUAL_ASSET_KINDS_BY_SECTION[episode["section_id"]],
            "stable worked-example construction",
            "prediction-and-answer retrieval state",
            "limitation or nearest-confusion comparison",
        ],
        "continuity_assets": [
            episode["worked_example_id"],
            "series evidence-status legend",
            "claim/source footer and measurement-boundary band",
        ],
        "external_imagery_policy": (
            "Optional only for one licensed domain-setting opener; the mechanism must still be taught with reproducible vector diagrams and data views."
            if contextual else
            "No external or generated imagery is required; prefer reproducible vector diagrams, exact traces, and source-bound data views over decorative stock imagery."
        ),
        "progression_rule": (
            f"Evolve the {len(episode['visual_spine'])} visual systems through at least "
            f"{minimum_compositions} compositions and {minimum_state_changes} meaningful state changes; "
            f"every change must teach or test {', '.join(episode['owns'])}."
        ),
        "forbidden_shortcuts": [
            "passive three-card or three-box row",
            "unlabeled conceptual animation presented as measurement",
            "decorative image that displaces the worked mechanism",
            "paragraph text used in place of a diagram or narrated explanation",
        ],
    }


def build_episode_content_bible(
    claim_registry: dict[str, Any], source_registry: dict[str, Any]
) -> dict[str, Any]:
    duration_by_tier = {
        "focused_explainer": {"minimum": 5, "maximum": 7},
        "core_episode": {"minimum": 8, "maximum": 12},
        "deep_episode": {"minimum": 14, "maximum": 20},
    }
    audience_by_section = {
        "orientation": "All viewers",
        "boolean-foundations": "Curious nontechnical and technical viewers",
        "cm-representations": "Technical viewers and implementers",
        "execution-materialization": "Technical viewers and implementers",
        "comparators-lowering": "Technical viewers and research reviewers",
        "measurement-evidence": "Technical viewers and evidence reviewers",
        "toolbox-applications": "Practitioners and technical decision makers",
        "recognition-research": "Technical and research viewers",
        "provenance": "Implementers, reviewers, and production maintainers",
    }

    def E(
        *, video_id: str, section_id: str, order: int, title: str, tier: str,
        prerequisites: list[str], thesis: str, owns: list[str], definitions: list[str],
        claim_ids: list[str], example: str, mechanism_beats: list[str], visuals: list[str],
        anchors: tuple[str, str, str, str], retrieval: str, closing: str,
        misconception: str, excludes: list[str] | None = None,
        references: list[str] | None = None, audience: str | None = None,
    ) -> dict[str, Any]:
        hook, definition, boundary, anchor_closing = anchors
        return {
            "video_id": video_id,
            "section_id": section_id,
            "order": order,
            "title": title,
            "audience": audience or audience_by_section[section_id],
            "duration_tier": tier,
            "duration_minutes": duration_by_tier[tier],
            "prerequisite_ids": prerequisites,
            "thesis": thesis,
            "owns": owns,
            "references": references or [],
            "excludes": excludes or [boundary],
            "definitions": definitions,
            "claim_ids": claim_ids,
            "worked_example_id": example,
            "teaching_beats": [
                f"Open with the concrete question: {hook}",
                f"Define the lesson's central distinction: {definition}",
                f"Construct and orient the stable example `{example}`.",
                *mechanism_beats,
                f"State the evidence boundary: {boundary}",
                f"Pause for retrieval: {retrieval}",
                f"Close by transferring the rule: {closing}",
            ],
            "visual_spine": visuals,
            "dialogue_anchors": {
                "hook": hook,
                "definition": definition,
                "boundary": boundary,
                "closing": anchor_closing,
            },
            "retrieval_check": retrieval,
            "closing_takeaway": closing,
            "misconceptions": [misconception],
            "caveats": [boundary],
            "content_hash": "0" * 64,
        }

    specs: list[dict[str, Any]] = []

    specs.extend([
        E(
            video_id="conceptual-vs-measured", section_id="orientation", order=1,
            title="Conceptual animation versus measured result", tier="focused_explainer",
            prerequisites=[],
            thesis="The series uses an explicit visual grammar so an explanatory mechanism can never masquerade as an observed result.",
            owns=["conceptual, measured, revised, negative, and not-promoted scene status"],
            definitions=["conceptual scene", "measured result", "promotion status"],
            claim_ids=["conceptual-label-rule"], example="ex-recognition-graph",
            mechanism_beats=[
                "Render the same mechanism first as a conceptual diagram and then as a measured panel with source, scope, boundary, and uncertainty.",
                "Introduce the persistent status badges and show how revised, negative, and not-promoted outcomes change wording without changing exactness.",
            ],
            visuals=[
                "Split screen: unlabeled-looking mechanism is corrected into a visibly CONCEPTUAL diagram.",
                "The same layout receives measured axes, workload, boundary, interval, and source locator.",
                "Five status badges settle into the series legend and remain available as a persistent corner key.",
            ],
            anchors=(
                "Did this animation happen in an experiment, or is it only showing how an idea could work?",
                "A conceptual animation explains a relationship; a measured result reports an observation under a declared protocol.",
                "A clear diagram is not evidence until its source, scope, boundary, and uncertainty are attached.",
                "From here on, the badge tells you what kind of statement you are seeing before you judge the statement itself.",
            ),
            retrieval="Classify three matched panels as conceptual, measured, or revised before their badges appear.",
            closing="Read the status before reading the result.",
            misconception="Polished motion graphics are automatically experimental evidence.",
        ),
        E(
            video_id="why-boolean-computation", section_id="boolean-foundations", order=2,
            title="Why Boolean computation matters", tier="focused_explainer",
            prerequisites=["conceptual-vs-measured"],
            thesis="Boolean computation turns a decision rule into a precise assignment-to-output mapping that can be represented and evaluated in several different ways.",
            owns=["decision rule to assignment-to-output mapping", "why repeated exact Boolean evaluation is useful"],
            definitions=["Boolean variable", "assignment", "Boolean output"],
            claim_ids=["boolean-decision-semantics"], example="ex-truth-layout-4",
            mechanism_beats=[
                "Toggle one input at a time and trace why the rule's output changes or stays fixed.",
                "Separate the rule's meaning from any later choice of matrix, graph, solver, or packed evaluator.",
            ],
            visuals=[
                "A concrete four-input decision rule lights its inputs and one true/false output.",
                "The rule expands into assignment cards that become rows of an output column.",
                "The output column fans into several possible representations, none marked as the winner.",
            ],
            anchors=(
                "How do we turn a rule that sounds reasonable into something every machine must answer the same way?",
                "A Boolean rule maps every complete assignment of its variables to exactly one true-or-false output.",
                "This lesson motivates exact Boolean computation; it does not establish that CM is the best representation for every task.",
                "First fix the function; only then choose how to represent or evaluate it.",
            ),
            retrieval="Predict the output after one input changes, then explain which part of the rule caused it.",
            closing="The stable object is the assignment-to-output mapping, not the syntax or storage chosen later.",
            misconception="Boolean computation is only about one written expression rather than the function over all assignments.",
        ),
        E(
            video_id="expression-truth-function", section_id="boolean-foundations", order=3,
            title="Expression, truth table, and Boolean function", tier="core_episode",
            prerequisites=["why-boolean-computation"],
            thesis="An expression is syntax, a truth table enumerates evaluations, and the Boolean function is the mapping they denote.",
            owns=["syntax-versus-semantics distinction", "equivalent expressions with one function"],
            definitions=["Boolean expression", "truth table", "Boolean function", "semantic equivalence"],
            claim_ids=["boolean-decision-semantics", "expression-function-distinction"], example="ex-truth-layout-4",
            mechanism_beats=[
                "Build an expression tree and evaluate it row by row into a truth column.",
                "Rewrite the syntax without changing the truth column, making semantic equivalence visible.",
            ],
            visuals=[
                "Expression tree and assignment row stay synchronized as gates evaluate.",
                "A second differently shaped tree grows beside the first and produces the same truth column.",
                "Both trees recede while the shared assignment-to-output mapping remains centered.",
            ],
            anchors=(
                "If two formulas look different, are they necessarily different computations?",
                "The expression is the written structure; the Boolean function is the output assigned to every input assignment.",
                "Matching one or two examples is not equivalence; the declared assignment universe must match exactly.",
                "Representations may change the structure, but exact semantics must stay fixed.",
            ),
            retrieval="Choose which of two rewritten expressions denotes the same function before the last truth rows are revealed.",
            closing="Syntax can change while the function remains identical.",
            misconception="A changed expression tree necessarily means a changed Boolean function.",
        ),
        E(
            video_id="live-support-ambient", section_id="boolean-foundations", order=4,
            title="Live support versus ambient variables", tier="focused_explainer",
            prerequisites=["expression-truth-function"],
            thesis="The surrounding assignment universe may name more variables than the function can actually depend on after simplification or fixed bindings.",
            owns=["live support", "ambient universe", "fixed-variable reduction"],
            definitions=["live support", "ambient variable", "fixed binding"],
            claim_ids=["live-vs-ambient"], example="ex-truth-layout-4",
            mechanism_beats=[
                "Hold one input fixed and test which remaining variables can still change the output.",
                "Collapse duplicate ambient rows into the smaller semantic-support view without claiming an automatic timing gain.",
            ],
            visuals=[
                "Ambient variables form an outer ring; only output-changing wires remain bright.",
                "A fixed binding removes one axis while paired rows collapse onto identical outputs.",
                "Nominal width and live support settle as two separate labeled counters.",
            ],
            anchors=(
                "Why can a six-variable table contain a function that really depends on only three variables?",
                "Live support contains variables that can change the output; ambient variables merely belong to the surrounding layout.",
                "Smaller live support changes the active problem description, but it does not by itself select the fastest engine.",
                "Count the variables that matter to this function, not only the variables named around it.",
            ),
            retrieval="Identify which variable is ambient after two assignments produce the same output under both of its values.",
            closing="Nominal width and semantic support answer different questions.",
            misconception="Every named variable necessarily doubles the function's active computational support.",
        ),
        E(
            video_id="what-is-explicit-cm", section_id="boolean-foundations", order=5,
            title="What a correspondence matrix is", tier="core_episode",
            prerequisites=["expression-truth-function"],
            thesis="An explicit correspondence matrix is a dense truth-layout obtained by partitioning variables into row and column axes and placing one exact output in each assignment cell.",
            owns=["row/column variable partition", "assignment-to-cell indexing", "dense CM output layout"],
            definitions=["correspondence matrix", "row variables", "column variables", "cell assignment"],
            claim_ids=["cm-explicit-definition", "live-vs-ambient"], example="ex-truth-layout-4",
            mechanism_beats=[
                "Partition A,B onto rows and C,D onto columns, then derive binary indices from one assignment.",
                "Fold the truth-table output column into the 4-by-4 grid and query several cells in both directions.",
            ],
            visuals=[
                "A sixteen-row truth table folds physically into a four-by-four matrix.",
                "One assignment splits into row bits and column bits; two index cursors meet at its cell.",
                "Live-support highlighting removes an inert axis while the declared ambient layout remains outlined.",
            ],
            anchors=(
                "How can one truth table become a two-dimensional object without changing a single output?",
                "An explicit CM lays the truth values out over a declared split between row and column variables.",
                "The matrix is a dense output layout; this definition does not make it compact, a solver, or universally fast.",
                "A CM cell is simply one exact assignment viewed through two coordinated indices.",
            ),
            retrieval="Given one four-bit assignment, choose its row and column cell before the cursors move.",
            closing="The matrix changes the layout, not the underlying Boolean function.",
            misconception="A correspondence matrix is an unrelated numerical approximation rather than an exact truth layout.",
        ),
        E(
            video_id="what-cm-does-not-claim", section_id="boolean-foundations", order=6,
            title="What CM does not claim to be", tier="focused_explainer",
            prerequisites=["what-is-explicit-cm"],
            thesis="CM is not automatically a compact representation, a satisfiability solver, CM-IR, or a universally fastest execution method.",
            owns=["CM non-claims", "output-contract mismatch examples"],
            definitions=["complete truth layout", "satisfiability question", "universal performance claim"],
            claim_ids=["cm-output-contract-boundary", "dense-vs-ir-distinct", "no-universal-winner"], example="ex-truth-layout-4",
            mechanism_beats=[
                "Ask for a complete vector, one satisfying assignment, and a reusable program, then show the different output each task requires.",
                "Pair a scoped kernel result with the slower public wrapper to reject method-label reasoning.",
            ],
            visuals=[
                "Three real task questions replace passive cards and route to visibly different artifacts.",
                "A dense grid, SAT witness, and CM-IR DAG are aligned by requested output rather than ranked.",
                "A universal-winner podium fractures into workload and boundary labels.",
            ],
            anchors=(
                "What goes wrong when one method name is used as the answer to three different questions?",
                "A representation or solver is defined partly by the output contract it satisfies.",
                "Current evidence supports scoped comparisons, not a claim that CM wins every task or boundary.",
                "Ask what must be returned before asking which method should return it.",
            ),
            retrieval="Match matrix, program graph, and SAT witness to three output requests.",
            closing="CM is one exact representation family, not a universal answer label.",
            misconception="Calling an approach CM establishes compactness, solver behavior, or speed.",
        ),
        E(
            video_id="explicit-cm-vs-cm-ir", section_id="boolean-foundations", order=7,
            title="Explicit dense CM versus CM-IR", tier="core_episode",
            prerequisites=["what-is-explicit-cm", "what-cm-does-not-claim"],
            thesis="The explicit CM is a dense truth-layout artifact; CM-IR is a canonicalized shared program graph that may later produce dense, flat, or packed outputs.",
            owns=["dense CM versus CM-IR artifact distinction", "construction/evaluation/materialization separation"],
            definitions=["explicit dense CM", "CM-IR", "materialization"],
            claim_ids=["cm-ir-definition", "dense-vs-ir-distinct", "cm-output-contract-boundary"], example="ex-truth-layout-4",
            mechanism_beats=[
                "Compile the same expression into a shared CM-IR DAG while the explicit matrix remains empty.",
                "Evaluate or materialize the DAG into several outputs and show which costs belong to graph construction versus output construction.",
            ],
            visuals=[
                "The same expression forks into a dense grid and an interned DAG with different identity labels.",
                "The DAG feeds point, flat/packed, and dense materialization exits; the grid remains the dense result.",
                "Matched axes compare artifact, storage, reuse, and charged boundary without declaring a winner.",
            ],
            anchors=(
                "When a benchmark says CM, is it timing a matrix, a program graph, or a wrapper that creates both?",
                "The explicit CM is the dense truth layout; CM-IR is the reusable canonical computation graph.",
                "A CM-IR kernel result is not automatically a dense-CM or public-wrapper result.",
                "Name the artifact and the boundary every time the label CM appears.",
            ),
            retrieval="Classify four displayed artifacts as explicit CM, CM-IR, lowered program, or packed output.",
            closing="The matrix is an output layout; CM-IR is a program that can produce outputs.",
            misconception="CM and CM-IR are two names for the same in-memory object.",
        ),
        E(
            video_id="cm-ir-nodes-sharing", section_id="cm-representations", order=8,
            title="CM-IR nodes, sharing, and roots", tier="core_episode",
            prerequisites=["explicit-cm-vs-cm-ir"],
            thesis="CM-IR stores unique computation nodes in a DAG so repeated structure and multiple roots can reuse the same descendants.",
            owns=["CMNode structure", "DAG sharing", "multiple roots"],
            definitions=["node", "directed acyclic graph", "shared descendant", "root"],
            claim_ids=["cm-ir-definition", "cm-ir-sharing-roots"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Build the repeated subtree twice as syntax, assign its structural identity, and intern it once.",
                "Attach two roots to shared descendants and trace one evaluation without recomputing the shared node.",
            ],
            visuals=[
                "Two duplicate syntax branches bend toward one interned CMNode.",
                "Reference-count and root badges appear while shared edges remain visibly distinct from tree edges.",
                "An evaluation pulse visits each unique node once and fans the result to both consumers.",
            ],
            anchors=(
                "If the same Boolean subproblem appears twice, why store and compute it twice?",
                "A CM-IR DAG stores unique nodes and lets several parents or roots point to the same descendant.",
                "Sharing reduces repeated structure, but the amount of reduction depends on the expression and canonicalization rules.",
                "Read CM-IR as a graph of reusable computations, not as a filled truth matrix.",
            ),
            retrieval="Point to the node that would be duplicated in a tree but shared in the DAG.",
            closing="One node can serve several consumers without changing the function.",
            misconception="A CM-IR DAG must contain one independent copy of every syntactic subtree.",
        ),
        E(
            video_id="canonicalization-interning", section_id="cm-representations", order=9,
            title="Canonicalization, interning, and normalization", tier="core_episode",
            prerequisites=["cm-ir-nodes-sharing"],
            thesis="Normalization chooses a stable structure, structural keys identify it, and interning reuses the matching node; these stages cooperate but are not synonyms.",
            owns=["normalization", "canonical structural identity", "interning"],
            definitions=["normalization", "canonical form", "structural key", "interning"],
            claim_ids=["cm-ir-normalization-interning", "cm-extra-transformations"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Send differently ordered associative/commutative syntax through normalization and display the resulting stable child order.",
                "Compute the structural key, query the intern table, and reuse or create the node as separate visible actions.",
            ],
            visuals=[
                "Messy equivalent syntax enters three labeled stations: NORMALIZE, KEY, INTERN.",
                "Tokens reorder and flatten before a digest appears; only then does the intern table return a node.",
                "A transformation ledger records which stage changed syntax, identity, or storage reuse.",
            ],
            anchors=(
                "What has to happen before two differently written subexpressions can share one node?",
                "Normalization makes structure stable, a key identifies that structure, and interning reuses the stored node.",
                "Canonicalization is implementation scoped; it does not prove a globally minimal representation.",
                "Do not collapse rewriting, identification, and reuse into one magic step.",
            ),
            retrieval="Place normalization, key construction, and intern-table lookup in the correct order.",
            closing="Equivalent structure becomes reusable only after its identity is made explicit.",
            misconception="Canonicalization, hashing, and interning are the same operation.",
        ),
        E(
            video_id="cm-ir-persistence", section_id="cm-representations", order=10,
            title="CM-IR persistence and version identity", tier="deep_episode",
            prerequisites=["canonicalization-interning"],
            thesis="Persistent reuse is safe only when canonical artifact identity, source/version identity, invalidation, reload, and exact-output checks remain connected.",
            owns=["CM-IR persistent identity", "cache hit/miss/invalidation", "reload verification"],
            definitions=["persistent cache", "artifact identity", "invalidation", "reload verification"],
            claim_ids=["cm-ir-persistence-contract", "source-provenance-contract"], example="ex-policy-revisions",
            mechanism_beats=[
                "Serialize a canonical DAG identity, record source/version inputs, and demonstrate one exact cache hit.",
                "Change one policy revision, propagate invalidation to the affected identity, reload the valid artifact, and compare exact outputs.",
            ],
            visuals=[
                "Canonical DAG becomes bytes, identity, and a versioned cache entry in one continuous chain.",
                "A source edit travels only through affected dependency edges and converts one hit into a miss.",
                "Reloaded graph and fresh compilation meet at an exact-output digest gate.",
                "A collision/equal-output warning demonstrates why output equality alone is not cache authority.",
            ],
            anchors=(
                "When is a graph saved yesterday still the right graph for today's source?",
                "Persistent reuse requires a stable artifact identity plus the source and version identity that made it valid.",
                "A hash match supports identity checking; it does not by itself establish scientific truth or permit stale reuse.",
                "A cache is trustworthy only when it knows why an artifact is still valid.",
            ),
            retrieval="Choose whether three changed-source scenarios are a cache hit, miss, or explicit invalidation.",
            closing="Persistence is an identity and invalidation contract, not merely saving bytes.",
            misconception="Equal output on one check is sufficient authority to reuse an artifact from changed source.",
        ),
        E(
            video_id="packed-words-selection", section_id="execution-materialization", order=11,
            title="Packed truth vectors: big integers, machine words, and masks", tier="core_episode",
            prerequisites=["live-support-ambient", "explicit-cm-vs-cm-ir"],
            thesis="Bigint and word-packed evaluators carry the same ordered truth vector in different exact storage/execution layouts; selector performance belongs to a later episode.",
            owns=["packed truth-vector ordering", "bigint versus word arrays", "tail masking"],
            definitions=["packed bitset", "machine word", "full mask", "tail mask"],
            claim_ids=["packed-truth-vector-contract"], example="ex-truth-layout-4",
            mechanism_beats=[
                "Pack sixteen ordered truth bits into an integer, then re-express the same ordering as machine-word lanes.",
                "Apply one Boolean operation in parallel and demonstrate why unused tail bits must be masked.",
            ],
            visuals=[
                "Truth-table outputs slide into bit positions with MSB-first ordering labeled.",
                "One long bigint bar splits into fixed-width word lanes without changing bit identities.",
                "A gate operates across all bits; a tail mask removes invalid high positions.",
            ],
            anchors=(
                "How can one machine operation evaluate many assignments at the same time?",
                "Packed evaluation stores many ordered truth values in one integer or several machine words.",
                "Packing is an exact execution layout, not a dense CM and not evidence that words are always faster than bigint.",
                "Keep truth ordering, storage layout, and backend selection as three separate ideas.",
            ),
            retrieval="Locate the bit representing one assignment and predict the correct tail mask.",
            closing="Packed storage changes how outputs travel through the machine, not what outputs mean.",
            misconception="Packed words, CSE-flat, and a dense correspondence matrix are interchangeable representations.",
        ),
        E(
            video_id="eager-lazy", section_id="execution-materialization", order=12,
            title="Eager and lazy CM paths", tier="focused_explainer",
            prerequisites=["explicit-cm-vs-cm-ir", "cm-ir-nodes-sharing"],
            thesis="Eager and lazy paths preserve exact semantics while placing aligned materialization work at different points in the construction timeline.",
            owns=["eager construction timing", "lazy deferred materialization"],
            definitions=["eager materialization", "lazy materialization", "deferred work"],
            claim_ids=["eager-lazy-contract"], example="ex-truth-layout-4",
            mechanism_beats=[
                "Run matched timelines: the eager path constructs aligned arrays during compilation while the lazy path retains deferred structure.",
                "Request the final output and show the lazy materialization occurring once before exact outputs meet.",
            ],
            visuals=[
                "Two synchronized timelines place identical work blocks at different stages.",
                "Eager fills aligned regions early; lazy carries outlined placeholders until output demand.",
                "Both paths terminate at one exact truth layout with no winner badge.",
            ],
            anchors=(
                "If both paths return the same output, what exactly makes one eager and the other lazy?",
                "Eager work happens during construction; lazy work is deferred until the requested result must be materialized.",
                "The implementation distinction does not establish a universal performance ranking.",
                "Ask when the work occurs before asking how long the whole task takes.",
            ),
            retrieval="Place three construction and materialization steps on the eager or lazy timeline.",
            closing="Eager and lazy change scheduling, not semantics.",
            misconception="Lazy means no materialization work is ever performed.",
        ),
        E(
            video_id="pair-aware", section_id="execution-materialization", order=13,
            title="Pair-aware CM collapse", tier="focused_explainer",
            prerequisites=["cm-ir-nodes-sharing", "live-support-ambient"],
            thesis="Pair-aware collapse is an experimental shortcut for the precise boundary of one live row variable and one live column variable after fixed bindings, with exact fallback otherwise.",
            owns=["pair eligibility", "2-by-2 token-pair collapse", "fallback boundary"],
            definitions=["pair-aware path", "one live row variable", "one live column variable", "fallback"],
            claim_ids=["pair-aware-contract"], example="ex-truth-layout-4",
            mechanism_beats=[
                "Apply fixed bindings until exactly one live variable remains on each axis and construct the eligible two-by-two tile.",
                "Add a third live variable, refuse the shortcut, and forward the unchanged problem to the standard path.",
            ],
            visuals=[
                "Row and column support counters shrink independently to one and one.",
                "The eligible axes snap into a two-by-two token tile and compute all four cases.",
                "An ineligible third variable diverts through a clearly labeled exact fallback arrow.",
            ],
            anchors=(
                "When can a larger expression safely collapse to one tiny row-column pair?",
                "The pair-aware shortcut requires exactly one live row variable and one live column variable after fixed inputs are applied.",
                "Pair eligibility is experimental and local; ineligible cases must fall back without changing semantics.",
                "The shortcut is defined by its boundary and fallback, not by its name.",
            ),
            retrieval="Decide whether three support/fixed-binding cases are pair-eligible before the fallback arrow appears.",
            closing="One live variable per axis makes the pair path possible; everything else stays on the exact fallback path.",
            misconception="Any subexpression with two total variables is automatically pair-eligible regardless of axis placement.",
        ),
        E(
            video_id="hybrid-partial", section_id="execution-materialization", order=14,
            title="Hybrid versus partial-hybrid materialization", tier="core_episode",
            prerequisites=["cm-ir-nodes-sharing", "packed-words-selection"],
            thesis="Hybrid and partial-hybrid modes differ in whether they collapse a whole subtree or preserve upper structure while dispatching selected children to packed or dense materialization.",
            owns=["whole-subtree hybrid collapse", "child-level partial-hybrid dispatch", "no-reinflation output"],
            definitions=["hybrid materialization", "partial-hybrid materialization", "full collapse", "no reinflation"],
            claim_ids=["hybrid-partial-contract", "packed-truth-vector-contract"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Color nodes by live support and show whole-subtree hybrid collapse under one declared mode.",
                "Restore the DAG, dispatch only eligible children in partial-hybrid mode, and preserve the parent structure through output.",
            ],
            visuals=[
                "A shared DAG carries a live-support heat map and explicit dispatch decisions.",
                "Hybrid view collapses the selected whole region into one packed block.",
                "Partial-hybrid view collapses children while the upper graph remains and feeds a no-reinflation output.",
            ],
            anchors=(
                "Does hybrid execution collapse the whole graph, or can it preserve structure and choose child by child?",
                "Hybrid can collapse an eligible region; partial-hybrid preserves more graph structure and dispatches selected children.",
                "These are implemented strategies, not guarantees that one wins every support size or workload.",
                "Watch which structure survives the dispatch decision.",
            ),
            retrieval="Identify which of two resulting artifacts came from whole collapse and which from child-level dispatch.",
            closing="Hybrid changes the materialization boundary; partial-hybrid changes it selectively.",
            misconception="Hybrid and partial-hybrid are two labels for the same full-collapse behavior.",
        ),
        E(
            video_id="parallel-cm", section_id="execution-materialization", order=15,
            title="Parallel CM materialization", tier="focused_explainer",
            prerequisites=["hybrid-partial"],
            thesis="Parallel CM partitions eligible materialization work into deterministic chunks, then reassembles the same exact output while charging scheduling and data-movement overhead.",
            owns=["parallel work eligibility", "chunk/worker partition", "deterministic assembly and overhead"],
            definitions=["parallel materialization", "work chunk", "shared memory", "deterministic assembly"],
            claim_ids=["parallel-materialization-contract"], example="ex-truth-layout-4",
            mechanism_beats=[
                "Partition matrix rows into ordered chunks, send them through worker lanes, and keep global indices attached.",
                "Reassemble chunks in deterministic order while an overhead band shows scheduling, transfer, and merge work.",
            ],
            visuals=[
                "A matrix gains chunk boundaries only after minimum-work guards pass.",
                "Ordered tiles enter worker swim lanes with stable row-index tags.",
                "Tiles return to one exact matrix while overhead remains a separate visible band.",
            ],
            anchors=(
                "If rows can be computed independently, why not always send every row to another worker?",
                "Parallel materialization divides eligible output work into chunks and deterministically reconstructs the same result.",
                "Parallelism adds scheduling and data-movement cost, so availability is not evidence of a speedup.",
                "Parallel work is useful only after its independent work and overhead are both visible.",
            ),
            retrieval="Choose whether a small, large, or dependency-coupled case should cross the parallel work guard.",
            closing="Parallelism redistributes work; it does not remove the need to count the work.",
            misconception="More workers necessarily make every materialization faster.",
        ),
    ])

    specs.extend([
        E(
            video_id="raw-ast", section_id="comparators-lowering", order=16,
            title="Why a raw expression tree repeats work", tier="focused_explainer",
            prerequisites=["expression-truth-function"],
            thesis="Raw AST evaluation follows every syntactic occurrence, making repeated work visible as an ablation but not providing the strongest generic comparator.",
            owns=["raw AST evaluation", "repeated syntactic work", "ablation role"],
            definitions=["abstract syntax tree", "raw evaluation", "ablation"],
            claim_ids=["raw-ast-ablation-definition"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Evaluate the repeated S=A AND B branch once in each syntactic location and increment the counter twice.",
                "Freeze the repeated result and preview the sharing question without yet implementing CSE.",
            ],
            visuals=[
                "The repeated subtree is outlined in two positions of the syntax tree.",
                "An evaluation pulse visits both copies and an operation counter advances twice.",
                "The two identical result tokens hover near each other, setting up the next episode's merge.",
            ],
            anchors=(
                "Why does the evaluator compute A AND B twice when both copies mean the same thing?",
                "A raw AST follows the written tree and performs work at each syntactic occurrence.",
                "Raw AST is an informative ablation, not the strongest comparator for a system that shares structure.",
                "Repeated syntax makes the cost of not sharing visible.",
            ),
            retrieval="Count how many times the repeated subtree is evaluated before the counter reveals the answer.",
            closing="The raw tree shows the duplication that later comparators are designed to remove.",
            misconception="Raw AST is a fair final baseline for a compiler whose competitors share repeated subexpressions.",
        ),
        E(
            video_id="cse-plain-language", section_id="comparators-lowering", order=17,
            title="Common subexpression elimination in plain language", tier="focused_explainer",
            prerequisites=["raw-ast"],
            thesis="Plain structural CSE identifies repeated expression subtrees, computes each once, and reuses the result while preserving exact semantics.",
            owns=["plain structural CSE", "structural key and shared result"],
            definitions=["common subexpression", "structural identity", "reuse"],
            claim_ids=["cse-definition"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Assign structural keys to both S subtrees and show their equality before any merge occurs.",
                "Replace the second computation with a reference to the first result and replay the evaluation counter.",
            ],
            visuals=[
                "Duplicate subtrees receive matching structural-key tags.",
                "Their branches bend toward one shared node while both consumer edges remain.",
                "The evaluation pulse computes S once and distributes one result token twice.",
            ],
            anchors=(
                "What is the simplest way to stop computing the same subtree twice?",
                "Common subexpression elimination computes a repeated structural subtree once and reuses its result.",
                "Plain CSE shares repeats; it does not necessarily flatten an associative chain into a wider instruction.",
                "CSE removes repeated computation by making structural reuse explicit.",
            ),
            retrieval="Choose which two subtrees have a matching structural key and which merely happen to share one operator.",
            closing="Share identical work first; ask about flattening next.",
            misconception="CSE automatically performs every normalization or associative flattening available to CM-IR.",
        ),
        E(
            video_id="cse-vs-cse-flat", section_id="comparators-lowering", order=18,
            title="Plain CSE versus sharing-aware CSE-flat", tier="core_episode",
            prerequisites=["cse-plain-language"],
            thesis="CSE-flat keeps structural sharing and also widens eligible associative chains, but it must not splice through a shared child and destroy reuse.",
            owns=["plain CSE versus CSE-flat", "safe associative flattening", "shared-child preservation"],
            definitions=["associative chain", "n-ary instruction", "single-consumer child", "sharing-aware flattening"],
            claim_ids=["cse-definition", "cse-flat-definition"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Start from the shared CSE DAG and mark which AND chains are eligible for widening.",
                "Flatten only through single-consumer associative children while protecting the shared S node, then compare instruction structure.",
            ],
            visuals=[
                "Raw AST, plain CSE, and CSE-flat remain synchronized in three narrow panels.",
                "Shared nodes carry lock icons; eligible single-consumer chains unfold into one n-ary operation.",
                "A before/after instruction ledger attributes reductions to sharing or flattening separately.",
            ],
            anchors=(
                "Can we widen an AND chain without tearing apart the sharing we just created?",
                "CSE-flat is structural CSE plus safe flattening of eligible associative chains while shared nodes remain shared.",
                "Always-splice flattening is not the comparator contract; shared children must be preserved.",
                "The strongest generic comparator used here includes both reuse and safe flattening.",
            ),
            retrieval="Select which associative child may be flattened and which must remain a shared node.",
            closing="CSE-flat strengthens plain CSE without sacrificing the sharing that made CSE useful.",
            misconception="CSE-flat means flatten every matching operator regardless of shared consumers.",
        ),
        E(
            video_id="cm-ir-vs-cse-flat-mechanism", section_id="comparators-lowering", order=19,
            title="CM-IR versus CSE-flat: shared mechanisms and extra transformations", tier="core_episode",
            prerequisites=["cse-vs-cse-flat", "canonicalization-interning"],
            thesis="CM-IR and CSE-flat overlap in sharing and flattening; any remaining difference must be attributed to actual normalization, merging, or lowered-program changes on the scoped workload.",
            owns=["mechanism overlap", "transformation attribution", "CM-label overclaim prevention"],
            definitions=["shared transformation", "additional normalization", "mechanism attribution"],
            claim_ids=["cse-flat-definition", "cm-extra-transformations", "cm-ir-normalization-interning"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Apply sharing and safe flattening to both arms, then remove those common steps from the comparison ledger.",
                "Add only observed CM-IR normalization or merging deltas and trace them into the lowered instruction structure.",
            ],
            visuals=[
                "A common transformation stack feeds both arms before they diverge.",
                "A delta ledger labels each changed node as sharing, flattening, normalization, or merging.",
                "The final graphs align by semantic node and lowered instruction rather than by method logo.",
            ],
            anchors=(
                "After CSE-flat already shares and flattens, what work is actually left for CM-IR to remove?",
                "The two compilers share mechanisms; only the remaining observed transformations can explain a scoped difference.",
                "A method label is not a mechanism, and one workload's residual reduction is not universal.",
                "Attribute every reduction to a visible transformation, not to the letters CM.",
            ),
            retrieval="Classify four graph changes as shared CSE-flat work or an additional CM-IR transformation.",
            closing="Common mechanisms belong to both arms; only measured deltas belong to the comparison.",
            misconception="Every difference between CM-IR and raw AST is an advantage unique to CM-IR over CSE-flat.",
        ),
        E(
            video_id="instruction-operations-memory", section_id="comparators-lowering", order=20,
            title="From DAGs to flat instructions: operations, storage, and execution", tier="deep_episode",
            prerequisites=["cm-ir-vs-cse-flat-mechanism", "packed-words-selection"],
            thesis="A shared DAG, CSE-flat transformation, lowered FlatProgram, instruction count, executed operations, live buffers, and packed storage are distinct layers that must be named separately.",
            owns=["DAG-to-FlatProgram lowering", "instruction versus executed-operation metrics", "structural memory metrics versus hardware-memory hypothesis"],
            definitions=["FlatProgram", "flat instruction", "executed primitive operation", "argument edge", "peak live buffer"],
            claim_ids=["flat-program-lowering", "operation-metrics-distinct", "memory-traffic-hypothesis", "epfl-mechanism"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Lower each unique DAG node into a dependency-ordered slot and instruction while preserving the shared S node.",
                "Expand one n-ary instruction into backend-specific primitive operations and update separate counters.",
                "Animate slot lifetimes and buffer release, then label hardware memory traffic as a hypothesis unless a retained measurement is present.",
            ],
            visuals=[
                "DAG nodes descend into a linear postorder instruction tape with matching identity colors.",
                "One instruction expands into several primitive-operation pulses while counters remain separate.",
                "Slot lifetime bars end at last use and release buffers; a HYPOTHESIS badge appears over hardware traffic arrows.",
                "CSE-flat transformation, FlatProgram, bigint bits, and word lanes settle as four noninterchangeable layers.",
            ],
            anchors=(
                "When someone says flat, do they mean a flattened expression, a linear instruction program, or packed bits?",
                "CSE-flat is a sharing-aware source transformation; FlatProgram is a lowered instruction list; bigint and words are execution storage layouts.",
                "Instruction and operation counts are measured structural metrics, but hardware memory traffic remains a hypothesis unless measured directly.",
                "Name the layer before interpreting its count.",
            ),
            retrieval="Match CSE-flat, FlatProgram, instruction count, primitive operation count, and packed word storage to five displayed artifacts.",
            closing="Flat syntax, flat instructions, and packed storage are different stages of one execution pipeline.",
            misconception="CSE-flat, FlatProgram, and word-packed execution are three names for the same artifact.",
        ),
        E(
            video_id="measurement-boundaries", section_id="measurement-evidence", order=21,
            title="Preparation, kernel, wrapper, and end-to-end time", tier="core_episode",
            prerequisites=["instruction-operations-memory"],
            thesis="A timing claim is meaningful only after every included and excluded stage is placed on a common pipeline.",
            owns=["preparation, kernel, wrapper, extraction, persistence, and end-to-end timing boundaries"],
            definitions=["preparation", "evaluator kernel", "public wrapper", "end-to-end task"],
            claim_ids=["b2b4-v3-kernel", "public-wrapper-slower", "epfl-preparation-cost", "no-universal-winner"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Move one request through preparation, artifact construction, repeated kernel, wrapper, extraction, persistence, and task completion.",
                "Slide timing brackets over different stage subsets and change the allowed claim wording in lockstep.",
            ],
            visuals=[
                "One persistent horizontal pipeline replaces separate cards for every boundary.",
                "Colored brackets expand from kernel-only to wrapper and end-to-end scopes.",
                "The B2/B4 kernel advantage and wrapper loss occupy different brackets simultaneously.",
            ],
            anchors=(
                "How can a kernel be faster while the easy public call is slower?",
                "A measurement boundary specifies exactly which stages the timer includes.",
                "Numbers from different boundaries may be shown together only when they remain visibly separate.",
                "Before comparing times, compare the work inside the timers.",
            ),
            retrieval="Choose which stages belong inside kernel, wrapper, and end-to-end brackets.",
            closing="The boundary is part of the result, not a footnote to it.",
            misconception="A faster compiled kernel automatically makes preparation, wrapper, and end-to-end execution faster.",
        ),
        E(
            video_id="read-a-ratio", section_id="measurement-evidence", order=22,
            title="How to read a CM/comparator ratio", tier="focused_explainer",
            prerequisites=["measurement-boundaries"],
            thesis="A ratio has no honest direction until numerator, denominator, favorable direction, workload, boundary, and uncertainty are visible.",
            owns=["ratio direction", "parity line", "interval interpretation"],
            definitions=["numerator", "denominator", "ratio", "parity", "confidence interval"],
            claim_ids=["ratio-label-rule"], example="ex-truth-layout-4",
            mechanism_beats=[
                "Compute two toy elapsed-time ratios, then reverse numerator and denominator without changing the underlying times.",
                "Add the parity line and interval before introducing a retained CM/comparator result.",
            ],
            visuals=[
                "Two labeled timers form CM/comparator and comparator/CM fractions side by side.",
                "The same point flips around one when the ratio direction reverses.",
                "A retained ratio appears only after workload, boundary, interval, and favorable arrow are in place.",
            ],
            anchors=(
                "Does a ratio below one mean faster, slower, or nothing at all?",
                "A ratio compares a named numerator with a named denominator; below one favors the numerator only for a time or cost ratio.",
                "Position and color cannot substitute for labels, scope, boundary, and uncertainty.",
                "Read the fraction before reading the dot.",
            ),
            retrieval="Interpret two reversed ratios and identify which arm is favored before the arrows appear.",
            closing="A ratio becomes evidence only after its direction and scope are explicit.",
            misconception="Every point below one favors CM regardless of numerator, metric, or boundary.",
        ),
        E(
            video_id="scope-boundaries", section_id="measurement-evidence", order=23,
            title="Why scopes and boundaries matter", tier="focused_explainer",
            prerequisites=["read-a-ratio"],
            thesis="Workload, output contract, machine, reuse, and measurement boundary define a claim's scope; similar-looking ratios outside that scope cannot be pooled into one conclusion.",
            owns=["scope comparison", "boundary mismatch", "non-pooling rule"],
            definitions=["scope", "workload", "output contract", "incomparable boundary"],
            claim_ids=["no-universal-winner", "ratio-label-rule", "cm-output-contract-boundary"], example="ex-circuit-cone",
            mechanism_beats=[
                "Place B2/B4 kernel, EPFL kernel, preparation, and wrapper panels on a two-axis workload/boundary grid.",
                "Attempt to pool them, surface the mismatches, and return to separate scoped conclusions.",
            ],
            visuals=[
                "A matrix uses workloads as rows and timing boundaries as columns; results occupy different cells.",
                "A pooling funnel rejects cards with mismatched output, boundary, machine, or dependence structure.",
                "Allowed wording updates as the viewer drags a scope bracket across cells.",
            ],
            anchors=(
                "Why can't four honest numbers be averaged into one honest winner?",
                "Scope names the conditions under which a claim is supported; the boundary names the work that was measured.",
                "B2/B4, EPFL, preparation, kernel, and wrapper evidence remain separate when their scopes differ.",
                "Keep each result inside the conditions that made it true.",
            ),
            retrieval="Reject the two results that cannot be pooled with a declared kernel/workload cell.",
            closing="Honest evidence gets narrower before it gets stronger.",
            misconception="All CM/comparator ratios estimate one underlying universal performance number.",
        ),
        E(
            video_id="reuse-break-even", section_id="measurement-evidence", order=24,
            title="Reuse and break-even economics", tier="core_episode",
            prerequisites=["measurement-boundaries", "read-a-ratio"],
            thesis="Extra preparation is repaid only when a per-evaluation advantage accumulates across enough genuinely reusable requests; some cases never break even.",
            owns=["one-time versus repeated cost", "finite break-even", "never-break-even case"],
            definitions=["one-time preparation", "per-evaluation cost", "break-even reuse", "never break even"],
            claim_ids=["epfl-preparation-cost"], example="ex-circuit-cone",
            mechanism_beats=[
                "Build cumulative cost lines from preparation intercepts and per-use slopes under a toy model.",
                "Replace the toy values with the scoped EPFL preparation and break-even summary, preserving never cases separately.",
            ],
            visuals=[
                "Two cumulative-cost lines grow from different preparation intercepts.",
                "A reuse slider moves the crossing point or reveals that no crossing exists.",
                "The retained EPFL distribution separates finite break-even cases from 55 never cases.",
            ],
            anchors=(
                "How many evaluations does it take to repay a more expensive compilation?",
                "Break-even reuse is the request count where accumulated preparation plus execution costs cross under a declared model.",
                "Some retained cases never break even, and a modeled crossing is not an end-to-end deployment guarantee.",
                "A kernel advantage matters only when reuse can repay the work that created it.",
            ),
            retrieval="Predict whether three pairs of intercepts and slopes cross, cross late, or never cross.",
            closing="Preparation is a debt; reuse determines whether the debt is ever repaid.",
            misconception="Any per-evaluation advantage guarantees a finite and useful break-even point.",
        ),
        E(
            video_id="b2b4-corrected", section_id="measurement-evidence", order=25,
            title="Corrected B2/B4 V3 kernel result", tier="core_episode",
            prerequisites=["scope-boundaries", "cse-vs-cse-flat"],
            thesis="The corrected B2/B4 V3 study supports a workload-scoped bare-kernel CM/CSE-flat reduction, a narrower k=16 gap, and a slower public wrapper—not universal dominance.",
            owns=["B2/B4 V3 formula-balanced result", "k=16 narrowing", "wrapper contrast"],
            definitions=["formula-balanced estimate", "formula-cluster interval", "support stratum"],
            claim_ids=["b2b4-v3-kernel", "b2b4-v3-k16", "public-wrapper-slower", "exactness-gates"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Introduce the strongest CSE-flat comparator and exact-output gate before revealing a timing point.",
                "Build the overall and k=16 ratio intervals, then place the wrapper result on a separate boundary row.",
            ],
            visuals=[
                "Comparator ladder locks CSE-flat as primary while raw AST moves to an ablation lane.",
                "A formula-balanced interval plot constructs overall and k=16 points progressively.",
                "Kernel and wrapper rows stay aligned but cannot merge; their favorable directions visibly differ.",
            ],
            anchors=(
                "What survives after the comparator, balancing, exactness, and boundary problems are corrected?",
                "On this B2/B4 V3 workload, bare CM/CSE-flat was about 0.8906 overall and 0.9612 at live support sixteen, while the public wrapper was slower.",
                "These estimates are conditional on this workload, machine, run, comparator, and boundary.",
                "The corrected result is modest, scoped, and stronger precisely because it is narrower.",
            ),
            retrieval="Choose the only allowed headline from kernel, k=16, and wrapper panels.",
            closing="The bare-kernel result survived correction; the universal speed claim did not.",
            misconception="The corrected kernel ratio establishes that the public CM API is faster end to end.",
        ),
        E(
            video_id="b2b4-runpod", section_id="measurement-evidence", order=26,
            title="Three-pod B2/B4 replication", tier="focused_explainer",
            prerequisites=["b2b4-corrected"],
            thesis="Three guarded Linux CPU runs reproduced the B2/B4 direction descriptively, but they do not become one pooled inferential interval or erase the local study's scope.",
            owns=["three-pod descriptive replication", "local inference versus machine replication"],
            definitions=["replication", "descriptive machine result", "within-run interval", "between-machine variation"],
            claim_ids=["b2b4-runpod-replication", "ratio-label-rule"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Place the accepted local estimate and three pod estimates in separate machine columns with identical ratio labels.",
                "Attempt and refuse an unjustified pooled interval, then state what direction replication does support.",
            ],
            visuals=[
                "Four machine columns build independently from verified raw results.",
                "Overall and k=16 points remain paired within each column.",
                "A POOL button is visibly refused because the design lacks a declared between-machine model.",
            ],
            anchors=(
                "What does three-machine agreement add, and what does it still not prove?",
                "Replication checks whether a scoped direction appears again under separately recorded machines and runs.",
                "The three pod values are descriptive; they are not a predeclared pooled confidence interval.",
                "Repeated direction strengthens portability evidence without broadening the scientific claim for free.",
            ),
            retrieval="Identify which uncertainty belongs within one run and which would require a between-machine design.",
            closing="Replication adds another scope; it does not erase scope.",
            misconception="Three similar pod ratios can automatically be averaged into the local study's confidence interval.",
        ),
        E(
            video_id="epfl-parity", section_id="measurement-evidence", order=27,
            title="EPFL AND/INV parity and its mechanism", tier="core_episode",
            prerequisites=["scope-boundaries", "cse-vs-cse-flat", "measurement-boundaries"],
            thesis="On accepted EPFL AND/INV cones, CSE-flat already captured the available associative reduction, instruction and operation counts matched, and the compiled kernels measured parity while CM preparation cost more.",
            owns=["EPFL parity result", "instruction/operation equality mechanism", "preparation penalty"],
            definitions=["AND/INV cone", "mechanism prediction", "parity interval"],
            claim_ids=["epfl-parity", "epfl-mechanism", "epfl-preparation-cost", "circuit-cone-support"], example="ex-circuit-cone",
            mechanism_beats=[
                "Lower the binary AND/INV cone through CSE-flat and CM-IR, showing that no additional mergeable chain remains.",
                "Set instruction and executed-operation ratios to one before revealing the kernel parity interval and separate preparation result.",
            ],
            visuals=[
                "A circuit cone zooms to binary gates and semantic support.",
                "Matched lowered instruction streams align one for one and lock both mechanism counters at 1.000.",
                "The timing interval settles across the parity line while preparation remains on a separate cost band.",
            ],
            anchors=(
                "What happens when the strong comparator has already captured every associative merge available in the circuit?",
                "On this AND/INV workload, CM and CSE-flat had equal instruction structure and measured compiled-kernel parity.",
                "EPFL parity is scoped to these cones and does not contradict the distinct B2/B4 kernel result.",
                "When the mechanism predicts no structural difference, parity is an informative result.",
            ),
            retrieval="Predict the instruction ratio before the matched streams and parity interval are revealed.",
            closing="No extra structural reduction meant no accepted kernel advantage on this workload.",
            misconception="EPFL parity proves CM and CSE-flat are universally identical on every workload.",
        ),
        E(
            video_id="selector-width-limit", section_id="measurement-evidence", order=28,
            title="Why width alone did not select the engine", tier="core_episode",
            prerequisites=["packed-words-selection", "measurement-boundaries"],
            thesis="A simple width-only flat-versus-words rule failed its declared regret gate, showing that support width is one feature rather than a universal selector.",
            owns=["width-only selector", "regret gate", "counterexample and no-change decision"],
            definitions=["selector", "regret", "validation reuse", "promotion gate"],
            claim_ids=["selector-no-width-rule", "representation-decision-factors"], example="ex-truth-layout-4",
            mechanism_beats=[
                "Draw the proposed width threshold and let most cases appear to follow it.",
                "Introduce the catastrophic-regret row, recompute the predeclared gate, and retain the existing selector.",
            ],
            visuals=[
                "A width axis routes cases toward bigint or word lanes.",
                "Per-case regret bars reveal one severe counterexample that aggregate medians would hide.",
                "The promotion gate turns red and the deployed-rule box remains unchanged.",
            ],
            anchors=(
                "If machine words sound natural above a certain width, why not switch at that number?",
                "A selector chooses an engine from pre-execution features and must control regret on the declared evaluation set.",
                "The focused study reused validation and failed its gate; it did not justify a universal width threshold.",
                "One cheap feature is useful only when its worst mistakes remain acceptable.",
            ),
            retrieval="Choose whether a selector with a good median but one catastrophic row passes the declared gate.",
            closing="Width informs the decision; it does not make the decision alone.",
            misconception="A support-width cutoff can universally choose between bigint and word-packed evaluation.",
        ),
        E(
            video_id="exact-comparison-protocol", section_id="measurement-evidence", order=29,
            title="Truth digests, alternating schedules, clustering, and intervals", tier="deep_episode",
            prerequisites=["b2b4-corrected", "read-a-ratio"],
            thesis="Exactness gates, order alternation, cluster-aware inference, and uncertainty intervals protect against different validity threats and must be shown as separate safeguards.",
            owns=["truth-digest exactness", "alternating/counterbalanced schedules", "cluster-aware inference", "cluster-aware interval construction"],
            definitions=["truth digest", "schedule alternation", "cluster", "bootstrap interval"],
            claim_ids=["exactness-gates", "ratio-label-rule", "b2b4-v3-kernel"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Introduce wrong-output, warm-order, pseudoreplication, and point-estimate threats one at a time.",
                "Pair each threat with its guard, then run one row through exact verification, alternation, formula clustering, and interval construction.",
            ],
            visuals=[
                "Four red validity threats enter four lanes and meet distinct guards.",
                "A timing ribbon alternates arm order while exact output digests remain outside the timed bracket.",
                "Repeated rows gather into formula clusters before resampling and interval construction.",
                "A final audit card lists which threats are controlled and which uncertainties remain out of scope.",
            ],
            anchors=(
                "What can make a precise timing number wrong even when the timer itself is accurate?",
                "Correctness, execution order, dependence, and sampling uncertainty are different problems with different guards.",
                "The retained interval models formula clustering within the declared run; it does not model every machine or future workload.",
                "A trustworthy comparison is a chain of safeguards, not one stopwatch reading.",
            ),
            retrieval="Match four threats to digest checking, schedule alternation, clustering, or interval construction.",
            closing="Each protocol guard earns one part of the claim and no more.",
            misconception="Passing exact-output equality automatically removes timing-order, dependence, and external-validity problems.",
        ),
        E(
            video_id="no-fastest-chart", section_id="measurement-evidence", order=30,
            title="Why one blended fastest-method chart is dishonest", tier="focused_explainer",
            prerequisites=["scope-boundaries", "b2b4-corrected", "epfl-parity"],
            thesis="A single podium destroys the output, workload, boundary, preparation, reuse, and uncertainty information needed to interpret method performance.",
            owns=["anti-podium argument", "task/boundary decision grid"],
            definitions=["blended ranking", "task-matched comparison", "decision grid"],
            claim_ids=["no-universal-winner", "ratio-label-rule", "cm-output-contract-boundary"], example="ex-circuit-cone",
            mechanism_beats=[
                "Construct a tempting fastest-method podium by hiding scope labels.",
                "Restore output contract, workload, boundary, reuse, and uncertainty until the podium becomes a conditional decision grid.",
            ],
            visuals=[
                "A glossy three-place podium appears with method logos but no task labels.",
                "Missing labels return as physical layers and pull results into different grid cells.",
                "The podium dissolves into an animated decision map with no universal top cell.",
            ],
            anchors=(
                "What had to be hidden to make one method look fastest everywhere?",
                "A fastest-method ranking is meaningful only for one matched output, workload, boundary, reuse pattern, and comparator set.",
                "Current CM evidence deliberately contains a kernel advantage, a parity workload, and a slower wrapper.",
                "A useful chart helps choose for a task; it does not manufacture one champion.",
            ),
            retrieval="Name the missing label that invalidates each of three apparent rankings.",
            closing="The honest answer is conditional because the actual tasks are different.",
            misconception="A blended chart can summarize unlike measurement boundaries without changing their meaning.",
        ),
        E(
            video_id="correction-story", section_id="measurement-evidence", order=31,
            title="How an audit changed the headline", tier="core_episode",
            prerequisites=["exact-comparison-protocol", "no-fastest-chart"],
            thesis="The audit replaced weak-comparator and blended-boundary language with stronger CSE-flat comparisons, exact verification, formula-balanced inference, and narrower scoped conclusions while retaining valid older scopes.",
            owns=["claim supersession", "comparator correction", "retained-scope history"],
            definitions=["audit correction", "supersession", "retained scope", "revised headline"],
            claim_ids=["b2b4-v3-kernel", "epfl-parity", "public-wrapper-slower", "no-universal-winner", "exactness-gates"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Place the earlier headline, comparator, and boundary on a versioned evidence graph without deleting them.",
                "Apply comparator, exactness, balancing, and boundary corrections, then derive the current allowed wording from surviving evidence edges.",
            ],
            visuals=[
                "A source-to-claim timeline preserves older artifacts but marks superseded wording.",
                "Four audit changes enter as patches and update comparator, exactness, weighting, and boundary nodes.",
                "EPFL parity, B2/B4 kernel reduction, and wrapper loss remain as separate current leaves.",
            ],
            anchors=(
                "Did the audit erase the old work, or did it change what the work was allowed to claim?",
                "A correction supersedes unsupported wording while retaining evidence that remains valid inside its original scope.",
                "The current conclusion is not one replacement ratio: EPFL, B2/B4 kernel, and the wrapper remain separate results.",
                "Credibility improves when the headline becomes as narrow as the evidence.",
            ),
            retrieval="Select which earlier statement is retained, revised, or superseded after the audit patches.",
            closing="A good audit changes the claim without pretending the history never happened.",
            misconception="A correction either invalidates every earlier result or can be ignored as a wording-only change.",
        ),
    ])

    specs.extend([
        E(
            video_id="toolbox-map", section_id="toolbox-applications", order=32,
            title="CM, CSE, BitSet, BDD, SAT, Espresso, and SymPy: different questions", tier="deep_episode",
            prerequisites=["what-cm-does-not-claim", "cse-vs-cse-flat", "packed-words-selection"],
            thesis="The toolbox should be organized by requested output and task lifecycle, not by one winner ranking or seven compressed tutorials.",
            owns=["tool output-contract map", "representation/evaluator/solver/minimizer distinction"],
            definitions=["truth-layout representation", "shared compiler", "packed evaluator", "decision diagram", "SAT solver", "minimizer", "symbolic algebra"],
            claim_ids=["toolbox-output-contracts", "cm-output-contract-boundary", "no-universal-winner"], example="ex-feature-model",
            mechanism_beats=[
                "Ask for a complete truth vector, repeated evaluation, canonical decision diagram, satisfying assignment, equivalence check, minimized form, and symbolic rewrite.",
                "Route each request to eligible tools and make construction/extraction charges visible before any comparison.",
                "Run two feature-model requests through the map to show that one workload can legitimately choose different tools for different questions.",
            ],
            visuals=[
                "A task question enters a radial router whose exits are labeled by returned artifact, not method prestige.",
                "Each tool produces a visibly different object: matrix, DAG/program, packed vector, BDD, witness, minimized expression, or symbolic expression.",
                "Cost bands for build, query, extraction, and reuse appear only on relevant routes.",
                "Two example requests take different branches and settle side by side without a podium.",
            ],
            anchors=(
                "Which tool is best—the one that returns every output, one witness, a canonical graph, or a smaller expression?",
                "The right first question is what artifact or answer the task requires.",
                "This map explains interfaces and retained evidence; it is not a full tutorial or universal benchmark for every tool.",
                "Choose the question first, then compare eligible tools under the same output contract.",
            ),
            retrieval="Route five requested outputs to eligible tool families and reject one output-mismatched comparison.",
            closing="Tools become comparable only after they are asked to do the same job.",
            misconception="CM, BDD, SAT, Espresso, and SymPy are interchangeable engines for one common output contract.",
        ),
        E(
            video_id="configuration-models", section_id="toolbox-applications", order=33,
            title="Configuration and feature-model workloads", tier="deep_episode",
            prerequisites=["toolbox-map", "cm-ir-persistence"],
            thesis="Configuration workloads combine constraints, repeated questions, adjacent revisions, and invalidation, making task contract and version identity more important than a method label.",
            owns=["feature constraints", "adjacent revisions", "version-aware reuse", "configuration query contracts"],
            definitions=["feature model", "requires/excludes constraint", "revision", "version-aware cache"],
            claim_ids=["configuration-revision-workload", "cm-ir-persistence-contract", "representation-decision-factors"], example="ex-feature-model",
            mechanism_beats=[
                "Build a feature tree with requires/excludes edges and evaluate validity of one selection.",
                "Apply an adjacent source revision, highlight the changed dependency region, and compare correct hit, miss, and invalidation outcomes.",
                "Ask complete-vector, point-validity, and repeated-revision questions to route through different eligible paths.",
            ],
            visuals=[
                "Feature tree and constraint graph respond to interactive-looking toggles with exact conflict paths.",
                "Three source revisions align as a diff; only affected graph regions and identities change color.",
                "Cold, cached, and invalidated paths share one timeline with all validation work charged.",
                "A task router sends enumeration, point checks, and revision reuse to different output contracts.",
            ],
            anchors=(
                "What changes when the rule set is almost the same tomorrow but not byte-for-byte identical?",
                "A feature model combines selectable features with exact constraints, and a revision changes the validity context for reuse.",
                "The retained studies are bounded revision and task cases; they do not establish universal CM dominance for configuration systems.",
                "Reuse is valuable only when changed dependencies and validation costs are part of the task.",
            ),
            retrieval="Classify three revision cases as safe reuse, invalidation, or fresh construction.",
            closing="Configuration performance lives in the sequence of related questions, not one isolated formula.",
            misconception="Equal output on adjacent feature-model revisions proves that cached structure is valid.",
        ),
        E(
            video_id="circuits", section_id="toolbox-applications", order=34,
            title="Circuit workloads: structure, truth, and exact controls", tier="core_episode",
            prerequisites=["toolbox-map", "live-support-ambient", "cse-vs-cse-flat"],
            thesis="Circuit evaluation starts from gates and cones but must define semantic support, exact output, comparator structure, and task boundary before interpreting performance.",
            owns=["circuit cone", "fanout and support", "AND/INV workload shape", "exact circuit controls"],
            definitions=["logic circuit", "cone", "fanout", "semantic support", "AND/INV"],
            claim_ids=["circuit-cone-support", "epfl-parity", "epfl-mechanism", "exactness-gates"], example="ex-circuit-cone",
            mechanism_beats=[
                "Zoom from a larger circuit into one output cone and trace which input variables can affect it.",
                "Lower the cone through CSE-flat and CM-IR, verify one truth digest, and connect its binary shape to the retained EPFL mechanism.",
            ],
            visuals=[
                "A full circuit fades while one output cone and its fan-in remain bright.",
                "Semantic-support testing removes an ambient input that cannot influence the cone output.",
                "Matched gate graph, lowered instructions, and exact digest remain synchronized.",
                "The conceptual cone hands off to a separately badged retained EPFL panel.",
            ],
            anchors=(
                "When a circuit has thousands of gates, what exact function is one output cone asking us to compute?",
                "A cone is the gate region that can influence one output; its semantic support is the subset of inputs that can change that output.",
                "The accepted parity result belongs to selected EPFL AND/INV cones, not to all circuits or all tasks.",
                "Circuit structure becomes evidence only after the cone, support, output, and comparator are fixed.",
            ),
            retrieval="Identify the gates and variables outside one selected cone and predict whether removing them changes its output function.",
            closing="Measure the function of the cone you actually selected, not the size of the circuit around it.",
            misconception="Nominal circuit size directly determines the semantic support and strongest evaluation method for every cone.",
        ),
        E(
            video_id="policy-rule-systems", section_id="toolbox-applications", order=35,
            title="Policy and rule systems with related revisions", tier="core_episode",
            prerequisites=["toolbox-map", "cm-ir-persistence", "measurement-boundaries"],
            thesis="Related policy revisions offer structural reuse and proved rewrites only when matching, proof, invalidation, fallback, and execution overhead are charged together.",
            owns=["versioned policy rules", "proved rewrite reuse", "changed-region invalidation", "charged fallback"],
            definitions=["policy rule", "proved rewrite", "rule pack", "charged fallback"],
            claim_ids=["policy-rule-revision-workload", "crse-d2-d7-evolution", "crse-d-mixed"], example="ex-policy-revisions",
            mechanism_beats=[
                "Build one decision from several related rules and expose repeated substructure across policy versions.",
                "Apply one proved rewrite with provenance, then change a source clause and invalidate only affected cached matches.",
                "Compare saved operations with matching, proof, cache, and fallback costs on the same end-to-end timeline.",
            ],
            visuals=[
                "A policy graph grows from role, region, resource, and risk predicates into one decision.",
                "Three revisions align; unchanged subgraphs remain shared while one clause and its dependents invalidate.",
                "A proved-rule certificate travels with the rewrite and returns to exact fallback on refusal.",
                "An overhead ledger prevents the operation reduction from becoming an automatic speedup badge.",
            ],
            anchors=(
                "If two policy versions share most of their rules, how much work can be reused safely?",
                "Versioned rule reuse needs exact identity, proved transformations, invalidation, and a fallback that preserves the original decision.",
                "More exact rewrites or fewer operations do not guarantee a faster overhead-inclusive policy task.",
                "Charge the work required to know that reuse and rewriting are safe.",
            ),
            retrieval="Choose which cached match survives a clause edit and whether one proved rewrite is profitable after overhead.",
            closing="Safe rule reuse is an end-to-end identity and cost problem.",
            misconception="A rewrite that reduces expression operations necessarily improves the complete policy request.",
        ),
        E(
            video_id="representation-decision", section_id="toolbox-applications", order=36,
            title="Which representation should I try?", tier="core_episode",
            prerequisites=["configuration-models", "circuits", "policy-rule-systems", "no-fastest-chart"],
            thesis="Representation choice should follow the required output, live support, reuse, update pattern, exact operation, preparation budget, and evidence status.",
            owns=["representation decision flow", "task-first selection factors", "evidence-status fallback"],
            definitions=["required output", "reuse pattern", "update pattern", "preparation budget", "evidence status"],
            claim_ids=["representation-decision-factors", "dense-vs-ir-distinct", "selector-no-width-rule", "no-universal-winner"], example="ex-feature-model",
            mechanism_beats=[
                "Walk a complete-vector circuit request through the decision questions and land on eligible exact evaluators.",
                "Walk a versioned configuration restriction request through the same tree and land on a different shortlist.",
                "Refuse an unsupported branch and return to measurement rather than forcing a recommendation.",
            ],
            visuals=[
                "An animated decision tree asks one concrete question per branch and shows why each answer matters.",
                "Two persistent workload tokens traverse different branches and retain their reasoning trail.",
                "Unsupported evidence ends at a MEASURE/ABSTAIN node rather than a guessed winner.",
            ],
            anchors=(
                "What should you ask before choosing CM, CSE-flat, packed evaluation, BDD, or SAT?",
                "Choose by the answer required, the work reused, the structure updated, and the costs included.",
                "The decision flow narrows eligible approaches; it does not replace measurement on a new workload.",
                "A good recommendation explains why a method fits this task and why the others answer a different question.",
            ),
            retrieval="Route two new workloads through the tree and explain the first branch where their choices diverge.",
            closing="The right representation is conditional on the task you actually need to complete.",
            misconception="One property such as width or nominal variable count can universally select the best representation.",
        ),
        E(
            video_id="recognition-question", section_id="recognition-research", order=37,
            title="What the CRSE research program asks", tier="core_episode",
            prerequisites=["conceptual-vs-measured", "cm-ir-nodes-sharing", "exact-comparison-protocol"],
            thesis="CRSE is a multi-track experimental program whose initial learned comparisons and later heuristic proposals remain subordinate to exact verification, charged fallback, frozen evaluation, and explicit promotion decisions.",
            owns=["current CRSE program map", "initial matrix/graph/fused/retrieval learning baseline", "proposal-verifier-fallback-promotion pipeline", "18-track scope"],
            definitions=["CRSE project label", "proposal path", "exact verifier", "fallback", "promotion decision"],
            claim_ids=["crse-experimental", "crse-initial-learning-slice", "crse-current-program-map", "conceptual-label-rule"], example="ex-recognition-graph",
            mechanism_beats=[
                "Locate the A/B foundation and initial C matrix, graph, fused, and retrieval arms; keep generated-data signal, failed retrieval, and poor EPFL transfer as separate outcomes.",
                "Map the current research branches without expanding CRSE into an unsupported phrase.",
                "Send one learned proposal through exact verification, rejection/fallback, measured cost, and a separate promotion gate.",
                "Contrast engineering success, exact scientific validity, generalization, and production promotion as four different statuses.",
            ],
            visuals=[
                "An 18-track program map groups routing, recognition, rewrites, exact dispatch, guidance, and negative controls.",
                "Matrix MLP, CNN, source-DAG GNN, fused, and retrieval tokens reach separate generated, retrieval, and EPFL outcome panels.",
                "Proposal and exact-verification lanes use distinct colors and never merge before acceptance.",
                "A four-stage gate separates exactness, measured benefit, transfer, and promotion for every later milestone.",
            ],
            anchors=(
                "Can a learned system suggest useful Boolean structure without becoming the authority on correctness?",
                "The project's CRSE program tests learned and deterministic proposals behind exact verification, fallback, and explicit promotion gates.",
                "CRSE is a project label in the authoritative sources; no production model or invented acronym expansion is allowed.",
                "A proposal may help find an answer, but the exact checker decides whether the answer is admitted.",
            ),
            retrieval="Place proposal, exact verification, charged fallback, measured result, and promotion in the correct order.",
            closing="CRSE studies when guidance helps while exact computation remains the safety authority.",
            misconception="A milestone that passes exact verification automatically proves learned generalization or production readiness.",
        ),
        E(
            video_id="recognition-c2", section_id="recognition-research", order=38,
            title="C2 variable-size decomposition: exact control, learned failure", tier="core_episode",
            prerequisites=["recognition-question"],
            thesis="C2 produced an exact balanced-cofactor decomposition detector and witnesses, while the learned representation and size-transfer criteria failed and no model was promoted.",
            owns=["C2 frozen question and split", "exact decomposition control", "learned transfer failure"],
            definitions=["balanced cofactor decomposition", "exact witness", "size transfer", "no promotion"],
            claim_ids=["crse-c2-negative", "crse-experimental"], example="ex-recognition-graph",
            mechanism_beats=[
                "Construct a conceptual row/column partition and exact factor witness before introducing the frozen learned task.",
                "Show generated training sizes and held-out n=10 separately, then reveal exact-control success and learned criteria failure.",
            ],
            visuals=[
                "A small truth layout splits into row and column factors and recomposes through an exact witness gate.",
                "Training and held-out size lanes never visually overlap.",
                "Exact-control and learned-model result cards settle independently; only the learned promotion gate fails.",
            ],
            anchors=(
                "What if the exact detector works perfectly but the learned detector fails on a larger size?",
                "C2 asked whether a learned representation could transfer a balanced decomposition recognized by an exact control.",
                "The exact detector's success does not rescue the failed learned size-transfer criterion.",
                "C2 retained a useful exact teacher and an equally useful learned failure.",
            ),
            retrieval="Predict which result can advance—the exact control, learned model, both, or neither—after the frozen criteria appear.",
            closing="Exact recognition advanced; learned transfer did not.",
            misconception="A perfect exact control implies that the trained learner has discovered the same transferable rule.",
        ),
        E(
            video_id="recognition-c3-c5", section_id="recognition-research", order=39,
            title="C3-C5 natural cuts: improvements without held-out promotion", tier="deep_episode",
            prerequisites=["recognition-c2"],
            thesis="C3-C5 improved natural data, cut supervision, ranking, and equivariant variable heads, but held-out recovery and charged learned paths remained below promotion criteria.",
            owns=["C3 natural decomposition data", "C4 direct-cut/ranking", "C5 variable-conditioned equivariant cuts", "held-out non-promotion"],
            definitions=["natural positive", "matched negative", "canonical cut", "equivariance", "accepted recall"],
            claim_ids=["crse-c3-c5-negative", "crse-experimental"], example="ex-recognition-graph",
            mechanism_beats=[
                "Advance one fixed example through C3 dataset construction, C4 direct cut supervision, and C5 variable-conditioned scoring.",
                "Keep confirmatory improvements, held-out square failures, exact acceptance, and charged inference time on separate axes.",
                "End with exact ANF retained as the accepted control while learned fitting remains paused.",
            ],
            visuals=[
                "A milestone timeline adds one methodological change at C3, C4, and C5 without resetting earlier evidence.",
                "Matched positive/negative graph pairs expose why superficial graph cues are insufficient.",
                "Predicted cut edges pass through an exact witness gate before acceptance.",
                "Confirmatory and held-out panels remain side by side, with cost charged below both.",
            ],
            anchors=(
                "Can better natural data and a better readout turn local improvement into a reliable held-out cut?",
                "C3-C5 progressively changed data, target, and equivariant readout while retaining exact acceptance and held-out criteria.",
                "Improvement on confirmatory circuits did not satisfy the required held-out promotion or cost criteria.",
                "A better model can still be a retained negative result when the frozen question remains unanswered.",
            ),
            retrieval="Match each C3-C5 change to data, supervision, or readout, then choose the final promotion status.",
            closing="The learned path improved, but the exact control remained the accepted path.",
            misconception="Any increase in confirmatory accuracy is sufficient evidence of held-out generalization.",
        ),
        E(
            video_id="recognition-c6", section_id="recognition-research", order=40,
            title="C6-C8 exact source ANF: packed cores and transfer", tier="deep_episode",
            prerequisites=["recognition-c3-c5", "packed-words-selection"],
            thesis="C6 advanced a deterministic packed exact source-ANF core; C7-C8 then preserved exact identities on an independent family and Linux while showing that the fastest exact representation remained workload- and machine-sensitive.",
            owns=["C6 packed exact source ANF", "C7 independent-source transfer", "C8 Linux exact transfer and backend sensitivity"],
            definitions=["algebraic normal form", "source-DAG ANF", "packed coefficient vector", "cross-machine exact transfer"],
            claim_ids=["crse-c6-advance", "crse-c7-c8-transfer", "packed-truth-vector-contract"], example="ex-recognition-graph",
            mechanism_beats=[
                "Transform a tiny source graph into exact ANF coefficients and pack them while preserving the witness path.",
                "Separate C6 core advancement from its missed gate, then carry identical source cases into C7 and C8 transfer lanes.",
                "Show set, packed, and bitset medians/tails changing order without changing exact partition identity.",
            ],
            visuals=[
                "A source DAG becomes a coefficient map and then a packed integer with bit identities visible.",
                "Core, gate, and production-path cards use separate status badges.",
                "Windows, independent Yosys source, and Linux lanes compare exact identities before any timing.",
                "A backend portfolio triangle shifts by sparse median, tail protection, and machine without choosing one universal vertex.",
            ],
            anchors=(
                "What can advance when a deterministic exact core improves but one frozen gate still misses?",
                "C6-C8 study exact source-ANF representations, their guarded cost, and transfer across source families and machines.",
                "Exact identity transferred; the fastest set, packed, or bitset representation did not become universal.",
                "Promote the exact component that passed, not the whole surrounding policy.",
            ),
            retrieval="Classify core, gate, transfer, and backend-ranking outcomes as advanced, held, or workload-sensitive.",
            closing="Exact transfer was stronger than any universal backend ranking.",
            misconception="A packed-core improvement proves that packed ANF is the fastest exact representation on every source and machine.",
        ),
        E(
            video_id="recognition-c9-c11", section_id="recognition-research", order=41,
            title="C9-C11 exact routing: static trees, guarded restart, and one-pass conversion", tier="core_episode",
            prerequisites=["recognition-c6"],
            thesis="C9-C11 retained three exact routing designs that protected tails or removed duplicate prefix work, yet each remained slower than the best fixed exact arm on its declared evaluation splits.",
            owns=["C9 static analytic routing", "C10 guarded exact restart", "C11 one-pass set-to-packed conversion"],
            definitions=["static analytic router", "product-budget restart", "one-pass conversion", "best fixed exact arm"],
            claim_ids=["crse-c9-c11-negative", "crse-current-program-map"], example="ex-recognition-graph",
            mechanism_beats=[
                "Freeze the C9 source-only timing tree before held-out evaluation and show its exact route losing after transfer.",
                "Stop C10 set ANF at a frozen product budget, restart with packed ANF, and separate p95 protection from sparse-case overhead.",
                "Convert C11's set prefix in place to packed coefficients so no DAG prefix repeats, then compare its full cost with restart and the best fixed arm.",
            ],
            visuals=[
                "A fixed set/packed/bitset arm rail stays visible beneath all three experimental routers.",
                "The C9 tree chooses an exact arm, then its held-out cost token lands below the profitability gate.",
                "C10's product counter triggers a guarded restart while median and p95 gauges move independently.",
                "C11 transforms one live set prefix into packed bits without a second DAG traversal, but its complete-cost bar still misses one.",
            ],
            anchors=(
                "Can an exact router solve a catastrophic tail and still be the wrong default?",
                "C9 chooses from a frozen static tree, C10 restarts after a product budget, and C11 converts the existing set prefix in one pass.",
                "All three preserved exact outputs; none beat the best fixed arm on every retained split, so tail protection and median profitability remain separate.",
                "An exact routing mechanism advances only when its charged whole path clears the declared gate.",
            ),
            retrieval="Match static transfer failure, restart tail protection, and one-pass prefix reuse to C9, C10, or C11.",
            closing="C9-C11 explain why C12 needed a robust guarded policy rather than a more confident universal router.",
            misconception="Eliminating duplicate prefix work or improving p95 automatically makes an exact router profitable on sparse cases.",
        ),
        E(
            video_id="recognition-c12-c16", section_id="recognition-research", order=42,
            title="C12-C16 exact dispatch, tail guards, and GF(2) artifacts", tier="deep_episode",
            prerequisites=["recognition-c9-c11"],
            thesis="C12-C16 combine exact adaptive dispatch, catastrophic-tail protection, task guards, reconstructible GF(2) artifacts, and screened materialization; C16 then passed exact local and Linux confirmation while retaining tiny-case and fresh-family limits.",
            owns=["C12 exact adaptive dispatch", "C13 tail sentinel", "C14 task guard", "C15 exact CM/GF(2) artifacts", "C16 screened materialization"],
            definitions=["exact dispatcher", "tail sentinel", "task guard", "GF(2) artifact", "screened materialization"],
            claim_ids=["crse-c12-c16-exact", "crse-current-program-map"], example="ex-recognition-graph",
            mechanism_beats=[
                "Route one exact task among set, packed, bitset, restart, and sentinel paths while preserving the same admitted result.",
                "Add the C14 task contract so sparse and latency-sensitive requests choose differently or abstain.",
                "Construct reconstructible GF(2) artifacts, screen bounded partitions, and compare exhaustive versus screened materialization locally and on the corrected Linux v2 package.",
            ],
            visuals=[
                "An exact dispatcher moves one task token through fixed arms while a fallback rail remains visible.",
                "Latency-tail and sparse-throughput gauges expose why C13 needs the C14 task guard.",
                "A GF(2) matrix decomposes into reconstructible component/rank/cofactor/Kronecker artifacts.",
                "Sixty-four partition outlines share one layout; four selected descriptors become solid artifacts before matched local/Linux evidence panels settle.",
            ],
            anchors=(
                "Can one exact system protect catastrophic tails without slowing every sparse case?",
                "C12-C16 route among exact representations, guard by task, and screen reconstructible GF(2) artifacts before materialization.",
                "C16 passed the corrected Linux second-machine gate, but one tiny local case regressed and a fresh non-XOR-heavy family remains untested.",
                "Exact dispatch advances by preserving fallback, reconstructibility, and workload limits across machines.",
            ),
            retrieval="Choose set, sentinel, guarded fallback, or screened GF(2) path for four declared task conditions.",
            closing="The later C milestones advance a cross-machine exact guarded portfolio, not one universal engine.",
            misconception="Passing a Linux confirmation makes the screened path a universal per-case or cross-family winner.",
        ),
        E(
            video_id="recognition-c17-c20", section_id="recognition-research", order=43,
            title="C17-C20 exact policies: dispatch, transfer, fitting, and compilation", tier="deep_episode",
            prerequisites=["recognition-c12-c16", "measurement-boundaries"],
            thesis="C17-C20 preserve one exact CM/GF(2) artifact while successively exposing dispatcher overhead, independent-source transfer, phase-separated policy fitting, and constant-folded execution; stronger aggregate evidence never erased the declared per-case, freshness, or machine limits.",
            owns=["C17 charged exact-task dispatcher", "C18 unchanged-policy VTR transfer", "C19 phase-separated exact-arm policy", "C20 constant-folded retrospective tail replay"],
            definitions=["exact-arm dispatcher", "advice-off fallback", "source-cluster split", "sealed confirmation", "constant-folded policy", "retrospective evidence"],
            claim_ids=["crse-c17-c20-exact-policy", "crse-current-program-map"], example="ex-recognition-graph",
            mechanism_beats=[
                "Wrap exhaustive and screened CM/GF(2) behind the C17 task contract, then charge the wrapper separately from the selected exact arm and expose the tiny-case tail failure.",
                "Freeze that policy before moving to 73 independently sourced VTR cones, preserving exact artifact identity while keeping the single-round minimum distinct from aggregate transfer.",
                "Partition 96 LogikBench cones by source cluster into development, validation, and untouched confirmation; fit only exact-arm cost choices and reveal that the selected tree collapses to an always-screened leaf.",
                "Compile the frozen leaf into a direct screened call, replay nine balanced rounds over the 11 retrospective C18 small-support controls, and keep the non-fresh same-machine label attached to the improved tail.",
            ],
            visuals=[
                "Two exact CM/GF(2) arm lanes feed one artifact-identity checker while a separately metered C17 wrapper exposes aggregate, slow-tail, and minimum gates.",
                "A frozen-policy seal crosses from the Yosys-derived lane to a 73-cone VTR source map; exact matches settle before the one-round timing distribution appears.",
                "A source-cluster wall partitions 96 LogikBench cones into development, validation, and confirmation without any cluster crossing the boundaries.",
                "The fitted C19 tree visibly collapses to one screened leaf; feature and tree overhead remain highlighted as removable work rather than mathematical evidence.",
                "A compiler folds that leaf into a direct selector, then nine retrospective timing rings replace the earlier one-round outlier without changing the production lock.",
            ],
            anchors=(
                "How can the same exact policy look strong in aggregate and still fail the rule needed for safe deployment?",
                "C17-C20 change the selection and evidence boundary around two exact arms; they never let policy advice define the Boolean answer.",
                "C19 supplies fresh source-cluster confirmation on one machine, while C20 is a retrospective same-machine replay, so neither licenses a universal production rule.",
                "Exactness, aggregate speed, per-case regret, source freshness, and machine transfer are five separate gates.",
            ),
            retrieval="Place wrapper overhead, independent transfer, sealed phase separation, constant folding, and retrospective replay on C17, C18, C19, or C20.",
            closing="C17-C20 turn a promising exact arm into a better-understood policy boundary, not a promoted universal dispatcher.",
            misconception="The C20 repeated-tail pass retroactively makes the C18 single-round scout fresh confirmation or promotes the policy.",
        ),
        E(
            video_id="recognition-c21-c22", section_id="recognition-research", order=44,
            title="C21-C22 task-matched GF(2): seven methods and a frozen source-packed portfolio", tier="deep_episode",
            prerequisites=["recognition-c17-c20", "exact-comparison-protocol", "instruction-operations-memory"],
            thesis="C21 charges seven methods for the same exhaustive-best GF(2) artifact and finds a narrow source-packed representation advantage with little routing headroom; C22 freezes that arm behind exhaustive fallback and shadow checks without adding fresh evaluation or production promotion.",
            owns=["C21 exhaustive-best task contract", "C21 seven-method whole-task table", "source-packed representation versus proposal effect", "C22 frozen source-packed exact portfolio"],
            definitions=["task-matched artifact", "screened completion", "proposal abstention", "per-case oracle headroom", "source-packed ANF", "shadow mode"],
            claim_ids=["crse-c21-c22-task-matched", "crse-experimental"], example="ex-recognition-graph",
            mechanism_beats=[
                "Bind exhaustive CM, screened CM, compiled screened CM, truth-ANF priority, source-packed ANF, fresh ROBDD, and source-interaction proposals to one charged exhaustive-best-artifact boundary, so a valid but non-best factor cannot substitute for the requested computation.",
                "Separate source-packed truth construction from component-proposal success: the representation path runs on every case, while the proposal abstains on 86 of 96 cases and screened completion remains authoritative.",
                "Compare the narrow best-fixed advantage with the unattainable per-case oracle headroom before any routing cost, then retain fresh single-query BDD as a lifecycle-specific negative control.",
                "Freeze C22 to the source-packed screened arm with advice-off exhaustive restoration, refusal fallback, and shadow artifact identity while marking fresh timing and promotion as absent.",
            ],
            visuals=[
                "One exhaustive-best artifact silhouette sits above seven method lanes; each lane must deliver the same identity before its timing cell unlocks.",
                "A stacked whole-task ledger separates input decode, representation, proposal, exact completion, checking, cleanup, and wrapper cost for every method.",
                "The source-packed lane forks into representation and proposal signals: ten proposal tokens advance, eighty-six abstain, and all ninety-six still enter screened completion.",
                "Best-fixed, width-rule, and per-case-oracle bars expose only a narrow remaining routing interval before decision overhead is charged.",
                "The C22 portfolio contract connects source-packed screened selection to exhaustive advice-off/refusal fallback and a parallel shadow identity checker; the fresh-evidence cell remains empty and labeled pending.",
            ],
            anchors=(
                "What changes when seven methods must return the best exact artifact instead of any reconstructible factor?",
                "A task-matched comparison charges representation, proposal, exact completion, checks, cleanup, and wrappers needed to deliver one common output contract.",
                "C21 is retrospective one-machine evidence, and C22 is implementation readiness without fresh timing, so the narrow source-packed lead is not a production claim.",
                "A faster representation path and a successful structural proposal are different mechanisms and must be measured separately.",
            ),
            retrieval="Classify each C21 cost as representation, proposal, completion, check, cleanup, or wrapper, then identify what evidence C22 still lacks.",
            closing="C21-C22 justify a guarded source-packed candidate for fresh testing, not a learned router or deployed default.",
            misconception="Because source-packed ANF was the fastest fixed arm, its component proposal usually pruned the exact search or C22 is already production-ready.",
        ),
        E(
            video_id="recognition-c23", section_id="recognition-research", order=45,
            title="C23 fresh Yosys transfer: exact confirmation without routing headroom", tier="deep_episode",
            prerequisites=["recognition-c21-c22", "exact-comparison-protocol", "measurement-boundaries"],
            thesis="C23 repeats the unchanged seven-method exhaustive-best GF(2) task on 48 previously unused Yosys-family functions and confirms the two strongest fixed paths, but a 0.62% packed-source lead, per-case regressions, and only 4.7% oracle headroom keep routing and production promotion unjustified.",
            owns=["C23 task-complete fresh-source freeze", "C23 unchanged seven-method transfer", "C23 fresh same-machine exact results", "C23 routing-headroom and non-promotion decision"],
            definitions=["fresh generator family", "task-complete support bound", "prior-truth exclusion", "unchanged-method transfer", "oracle routing headroom", "same-machine confirmation"],
            claim_ids=["crse-c23-fresh-yosys-transfer", "crse-experimental"], example="ex-recognition-graph",
            mechanism_beats=[
                "Separate source freshness from machine freshness, preserve the first incomplete freeze, then select previously unused Yosys generator families under the corrected support-3-to-6 task where the declared 64-partition reference is complete and every prior truth overlap is excluded.",
                "Run the seven C21 implementations unchanged, require the same exhaustive-best artifact on all 1,680 timed executions, and independently replay source fingerprints, scalar oracles, selections, and artifact identities.",
                "Compare packed source ANF, compiled screened CM, direct screened CM, two proposal methods, fresh ROBDD, and exhaustive CM while keeping representation and proposal effects visually separate.",
                "Place the narrow fixed-path gap beside the 1.047x unattainable oracle headroom, the compiled per-case regressions, and the pending second-machine package before leaving the production lock closed.",
            ],
            visuals=[
                "A two-axis evidence map separates new source families from a new machine; C23 advances only along the source-family axis.",
                "The original support-3-to-10 corpus hits a red task-contract boundary above six, is retained as incomplete, and becomes a verified support-3-to-6 v2 freeze with prior-overlap filters visible.",
                "Forty-eight function tokens from eight Yosys generator families pass independent scalar-oracle and prior-truth gates before entering the unchanged seven-lane task table.",
                "Seven aligned cost lanes end at one exhaustive-best artifact identity; representation, proposal, completion, checking, cleanup, and wrapper bands remain separately labeled.",
                "Packed source ANF, screened CM, and compiled screened CM bars settle almost together while per-case regret markers and a thin oracle-headroom bracket keep the production lock closed.",
            ],
            anchors=(
                "Does a fresh source family turn the narrow C21 winner into a deployable routing rule?",
                "C23 changes the corpus, not the task or methods: every arm must still return the same exhaustive-best exact artifact under a corrected complete support bound.",
                "The fixed paths transfer, but the best two are separated by only 0.62%, the oracle offers only 4.7% pre-router headroom, and compiled execution still regresses on individual cases.",
                "Fresh-source confirmation strengthens an evidence claim without automatically supplying second-machine confirmation or production authority.",
            ),
            retrieval="Distinguish the failed freeze, corrected task-complete corpus, unchanged-method exact table, source-family transfer, machine-transfer gap, and non-promotion decision.",
            closing="C23 strengthens the fixed exact portfolio evidence while making another learned router less compelling, not more.",
            misconception="Because C23 uses fresh Yosys families and packed source ANF wins in aggregate, the result is already cross-machine proof or a production routing policy.",
        ),
        E(
            video_id="recognition-d-tasks", section_id="recognition-research", order=46,
            title="Milestones D-D7: task routing, proved rules, caching, and normalization", tier="deep_episode",
            prerequisites=["recognition-question", "measurement-boundaries", "cm-ir-persistence"],
            thesis="D-D7 expand from task-aware exact routing into proved rules, versioned caches, profitability gates, natural incidence, real revisions, and bounded normalization; exact engineering improves more consistently than end-to-end profitability.",
            owns=["D task contracts", "D2-D4 proved/versioned/profitability rule pack", "D5-D7 natural incidence, revisions, and normalization"],
            definitions=["task routing", "proved metavariable rule", "versioned rule cache", "profitability gate", "bounded normalization"],
            claim_ids=["crse-d-mixed", "crse-d2-d7-evolution", "policy-rule-revision-workload"], example="ex-policy-revisions",
            mechanism_beats=[
                "Route complete-vector, point, restriction, and repeated-vector tasks through exact arms with all construction and audit costs present.",
                "Grow the rule pack from a proved identity to versioned cache and profitability gate, preserving proof provenance.",
                "Move into natural circuits and revisions, then add bounded multi-pass normalization and retain its negative second-pass economics.",
            ],
            visuals=[
                "Four task tokens traverse separate cost pipelines rather than one blended benchmark.",
                "A rule-pack timeline adds proof rows, deterministic priority, cache identity, and gates at D2-D4.",
                "Natural incidence heatmaps and revision diffs ground D5-D6 in retained workloads.",
                "A bounded normalization loop shows strict decrease, termination, extra reductions, and charged loss.",
            ],
            anchors=(
                "What happens when exact routing and rewriting are judged by the complete task rather than their inner kernel?",
                "D-D7 separate task outputs, proved rules, cache identity, reuse, natural incidence, revisions, and bounded normalization.",
                "Exactness and engineering completion do not guarantee overhead-inclusive profitability.",
                "The D sequence asks whether safe structure saves enough whole-task work to matter.",
            ),
            retrieval="Place routing, proof, cache, gate, natural incidence, revision, and normalization milestones on the D-D7 sequence.",
            closing="The system became more exact and accountable faster than it became profitable.",
            misconception="A proved rewrite or cache hit is automatically beneficial after its matching and validation costs are charged.",
        ),
        E(
            video_id="recognition-d8", section_id="recognition-research", order=47,
            title="D8 Linux confirmation: exact but unprofitable", tier="focused_explainer",
            prerequisites=["recognition-d-tasks"],
            thesis="D8 reproduced exact outputs and rule incidence on Linux but reversed the Windows profitability direction, so unconditional one-pass rewriting was not promoted.",
            owns=["D8 frozen Linux transfer", "exactness versus profitability separation"],
            definitions=["frozen confirmation", "rule incidence", "profitability transfer", "negative control"],
            claim_ids=["crse-d8-negative"], example="ex-policy-revisions",
            mechanism_beats=[
                "Freeze the Windows package, carry identical rules and inputs to Linux, and verify exact outputs and application counts first.",
                "Reveal the reversed overhead-inclusive timing only after correctness and incidence match.",
            ],
            visuals=[
                "Windows and Linux lanes share frozen package, input, rule, and digest identities.",
                "Exactness and rule-incidence checks turn green in both lanes.",
                "Profitability arrows point in opposite directions and the promotion gate remains closed.",
            ],
            anchors=(
                "Can an experiment reproduce perfectly and still fail its reason for deployment?",
                "D8 froze the one-pass rewrite package and checked exactness, rule incidence, and whole-task profitability on Linux.",
                "Exact transfer passed, but profitability did not; the negative result is the final promotion authority.",
                "Reproduction includes the failed criterion, not only the successful checks.",
            ),
            retrieval="Choose the correct promotion decision when exactness and incidence pass but overhead-inclusive speed loses.",
            closing="D8 is an exact engineering success and a profitability failure at the same time.",
            misconception="Reproducing exact outputs and rule counts is sufficient to promote a performance optimization.",
        ),
        E(
            video_id="recognition-d9", section_id="recognition-research", order=48,
            title="D9 abstention policy: safe, charged, not promoted", tier="core_episode",
            prerequisites=["recognition-d8"],
            thesis="D9's frozen policy safely abstained on all evaluation workloads, but the charged decision path still cost time, so correct abstention did not become a promoted rewrite policy.",
            owns=["D9 calibrated policy", "in-range refusal and out-of-range abstention", "charged no-promotion result"],
            definitions=["abstention", "calibrated policy", "advice overhead", "no-promotion decision"],
            claim_ids=["crse-d9-not-promoted", "crse-experimental"], example="ex-policy-revisions",
            mechanism_beats=[
                "Score in-range and out-of-range workloads, separate insufficient-gain refusal from novelty abstention, and preserve exact fallback.",
                "Charge feature acquisition and decision overhead even when no rewrite is applied, then compare with the no-rewrite control.",
            ],
            visuals=[
                "A two-gate policy separates applicability from expected gain.",
                "All 33 workload tokens return to exact no-rewrite fallback for different documented reasons.",
                "An overhead meter continues accumulating during abstention and closes the promotion gate.",
            ],
            anchors=(
                "If a policy avoids every bad rewrite, has it succeeded?",
                "Abstention is a safe decision to decline advice, but the system must still charge the cost of reaching that decision.",
                "D9 selected the faster fixed arm correctly but remained slower after advice overhead, so no policy was promoted.",
                "Safety can pass while profitability remains a retained negative result.",
            ),
            retrieval="Distinguish refusal, novelty abstention, accepted advice, and unconditional fallback in four policy cases.",
            closing="A safe no-op is not free, and its cost belongs in the deployment decision.",
            misconception="An all-abstain policy is automatically equivalent in cost to having no policy.",
        ),
        E(
            video_id="recognition-d10", section_id="recognition-research", order=49,
            title="D10 indexed rule execution: richer exact rules, negative whole-path economics", tier="core_episode",
            prerequisites=["recognition-d9"],
            thesis="D10 added indexed screening, four exhaustively proved rule families, strict decrease, provenance, and versioned replay, yet the complete indexed engine remained unprofitable.",
            owns=["D10 indexed screening", "four proved rule families", "strict decrease and provenance", "negative whole-path result"],
            definitions=["indexed rule engine", "strict decrease", "versioned replay", "whole-path profitability"],
            claim_ids=["crse-d10-negative", "policy-rule-revision-workload"], example="ex-policy-revisions",
            mechanism_beats=[
                "Index candidate nodes by operator/shape before matching mux, comparator, carry, and XOR-cancellation rules.",
                "Attach exhaustive proof and strict-decrease provenance to each accepted rewrite, then replay through a versioned cache.",
                "Compare structural savings with indexing, matching, proof, cache, and execution costs at the complete boundary.",
            ],
            visuals=[
                "A rule index narrows candidate nodes before four rule-family matchers activate.",
                "Accepted rewrites carry proof, decrease, source, and cache-identity tags through execution.",
                "A whole-path ledger shows structural reductions and exact replay alongside larger total overhead.",
            ],
            anchors=(
                "Can a much better-engineered exact rule system still lose to doing nothing?",
                "D10 screens candidates through an index and applies only exhaustively proved, strictly decreasing rules with exact replay.",
                "More rule families and safer execution did not satisfy the retained whole-path profitability criterion.",
                "Engineering completeness and economic usefulness remain separate promotion gates.",
            ),
            retrieval="Identify which costs remain after indexing reduces the number of full rule matches.",
            closing="D10 advanced the exact engine while retaining no rewrite as the economic control.",
            misconception="Indexed matching guarantees that a larger exact rule pack repays its execution overhead.",
        ),
        E(
            video_id="recognition-e1-e2", section_id="recognition-research", order=50,
            title="E1-E2 exact BDD and SAT guidance: task-aware advice with fallback", tier="deep_episode",
            prerequisites=["recognition-question", "toolbox-map", "measurement-boundaries"],
            thesis="E1-E2 extend task-aware guidance to BDD order and SAT/equivalence lifecycles, keeping exact artifacts and advice-off fallback authoritative while learned advice remains unpromoted.",
            owns=["E1 BDD-order objectives", "E2 SAT/equivalence lifecycles", "exact advice-off fallback"],
            definitions=["BDD variable order", "restriction query", "CNF", "assumption session", "equivalence miter", "advice-off fallback"],
            claim_ids=["crse-e1-e2-guidance", "toolbox-output-contracts", "crse-experimental"], example="ex-feature-model",
            mechanism_beats=[
                "Build the same Boolean task under several BDD variable orders and separate node, cold-build, and build-plus-query objectives.",
                "Translate a second task to CNF and separate fresh solve, resident assumptions, and equivalence-miter lifecycles.",
                "Place learned/fixed advice in front of exact construction and witness/core checks, then demonstrate advice-off fallback.",
            ],
            visuals=[
                "One function produces differently shaped BDDs as the variable order ribbon changes.",
                "Objective tabs switch between nodes, build, restriction, and equivalence without pooling them.",
                "Expression-to-CNF animation feeds fresh, assumption-session, and miter solver lanes.",
                "Advice controls a route selector but exact BDD/SAT artifacts and fallback remain visually downstream and authoritative.",
            ],
            anchors=(
                "Should one advisor choose the same BDD order and SAT lifecycle for every question about a Boolean function?",
                "E1-E2 choose among exact BDD-order and SAT/equivalence strategies under task-specific lifecycles with advice-off fallback.",
                "The retained learned advice did not establish a general timing win, and solver/BDD results answer different output contracts.",
                "Guidance may choose an exact path; it never replaces the exact artifact or witness.",
            ),
            retrieval="Route node minimization, repeated restriction, one SAT query, assumption session, and equivalence check to their correct objective/lifecycle.",
            closing="Task-aware advice is useful only while exact construction, checking, and fallback stay in charge.",
            misconception="One learned policy can optimize BDD size, build time, restrictions, SAT, and equivalence as one common objective.",
        ),
        E(
            video_id="source-hash-reproduction", section_id="provenance", order=51,
            title="How a video is bound to source hashes", tier="core_episode",
            prerequisites=["conceptual-vs-measured", "exact-comparison-protocol"],
            thesis="Reproducible video production links source locator and hash to claim, content bible, script cue, storyboard, render job, output, and separate content and RunPod approval identities.",
            owns=["source-to-release provenance chain", "downstream invalidation", "content approval versus RunPod authorization"],
            definitions=["source locator", "content hash", "cache identity", "content approval identity", "RunPod authorization identity"],
            claim_ids=["source-provenance-contract", "conceptual-label-rule"], example="ex-repeated-subexpression",
            mechanism_beats=[
                "Trace one retained claim from source path/locator/hash through the content bible, script cue, scene, job, result, and release manifest.",
                "Change the source, propagate invalidation through every dependent identity, and preserve unrelated cached episodes.",
                "Construct a content-approval manifest and a separate RunPod authorization, showing that neither implies the other.",
            ],
            visuals=[
                "A provenance graph grows source -> locator -> claim -> bible -> script -> storyboard -> render job -> output -> release.",
                "One source hash changes and red invalidation travels only along dependent edges.",
                "Content approval and RunPod authorization appear as two separate locks over different artifact sets and effects.",
                "A final reproducibility card lists exact paths, hashes, and commands without exposing a secret.",
            ],
            anchors=(
                "If one evidence file changes, how do we know which sentence, scene, and rendered chapter are stale?",
                "A content hash binds normalized inputs; provenance records which sources and transformations produced each downstream artifact.",
                "Hash identity supports reproducibility and invalidation, but it does not establish scientific truth or authorize cloud spending.",
                "Every claim and pixel should be traceable without placing a credential anywhere in the chain.",
            ),
            retrieval="Identify which episodes invalidate after one shared source changes and which cached episodes remain valid.",
            closing="Reproducibility is a connected chain of identities, evidence, and approvals.",
            misconception="A valid SHA-256 alone proves the underlying scientific claim and authorizes its remote production.",
        ),
    ])

    # CONTENT_BIBLE_EPISODES

    sections = [
        ("orientation", "Series orientation", "Teach the evidence-status grammar before any scientific or performance claim."),
        ("boolean-foundations", "Boolean functions and explicit CM", "Build the semantic foundation and distinguish the dense CM artifact from CM-IR."),
        ("cm-representations", "CM-IR representation and identity", "Explain shared graph structure, canonical identity, and persistence."),
        ("execution-materialization", "Execution and materialization paths", "Separate packed storage and each implemented CM execution/materialization path."),
        ("comparators-lowering", "Comparators and lowering", "Build the AST-to-CSE-to-CSE-flat-to-CM-IR ladder and own the flat-program distinction."),
        ("measurement-evidence", "Measurement, evidence, and corrections", "Teach boundaries, ratios, inference, replication, negative evidence, and correction history."),
        ("toolbox-applications", "Toolbox and applications", "Choose tools by output contract and apply the distinctions to concrete workload families."),
        ("recognition-research", "CRSE recognition research", "Present the current experimental program as learned proposals plus exact controls and promotion decisions."),
        ("provenance", "Provenance and reproducibility", "Bind sources, claims, scripts, renders, approvals, and invalidation."),
    ]
    section_values = []
    for section_order, (section_id, title, purpose) in enumerate(sections, 1):
        section_values.append({
            "section_id": section_id,
            "order": section_order,
            "title": title,
            "purpose": purpose,
            "episode_ids": [episode["video_id"] for episode in specs if episode["section_id"] == section_id],
        })

    stable_examples = [
        {
            "example_id": "ex-repeated-subexpression",
            "title": "Shared Boolean expression",
            "purpose": "Carry AST, CSE, CSE-flat, CM-IR, lowering, and operation accounting across episodes.",
            "definition": "S=A AND B; F=(S AND C AND D) OR (S AND E), with binary source syntax and stable variable order A,B,C,D,E.",
            "conceptual": True,
            "source_ids": ["src-cm-exprlib", "src-bitset"],
        },
        {
            "example_id": "ex-truth-layout-4",
            "title": "Four-variable truth layout",
            "purpose": "Carry assignments, live support, explicit CM, packed truth vectors, and exact output across episodes.",
            "definition": "F(A,B,C,D)=(A AND B) XOR (C OR D), row variables A,B, column variables C,D, MSB-first ordering.",
            "conceptual": True,
            "source_ids": ["src-cm-build", "src-bitset"],
        },
        {
            "example_id": "ex-feature-model",
            "title": "Versioned feature model",
            "purpose": "Teach constraints, revisions, invalidation, and repeated queries without borrowing an unsupported product claim.",
            "definition": "A conceptual product family with Core, Cloud, Local, Analytics, and Export features plus requires/excludes constraints and three adjacent revisions.",
            "conceptual": True,
            "source_ids": ["src-recognition-readme"],
        },
        {
            "example_id": "ex-circuit-cone",
            "title": "Small AND/INV cone",
            "purpose": "Teach cone support, fanout, lowering, exact digests, and the accepted EPFL mechanism.",
            "definition": "A conceptual five-input AND/INV cone whose output has four-variable semantic support, paired later with separately labeled retained EPFL evidence.",
            "conceptual": True,
            "source_ids": ["src-epfl-report"],
        },
        {
            "example_id": "ex-policy-revisions",
            "title": "Versioned policy rules",
            "purpose": "Teach related rules, exact reuse, changed-region invalidation, and charged rewrite overhead.",
            "definition": "A conceptual access policy over role, region, resource, and risk, shown across three source revisions.",
            "conceptual": True,
            "source_ids": ["src-recognition-readme"],
        },
        {
            "example_id": "ex-recognition-graph",
            "title": "Conceptual recognition/decomposition graph",
            "purpose": "Keep proposal, exact verification, fallback, and promotion visually stable across CRSE episodes.",
            "definition": "A tiny labeled expression graph with a proposed partition, an exact witness path, a rejection/fallback path, and a promotion gate; it is never presented as a measured trace.",
            "conceptual": True,
            "source_ids": ["src-recognition-readme", "src-recognition-register"],
        },
    ]
    episodes_by_id = {episode["video_id"]: episode for episode in specs}
    order_by_id = {episode["video_id"]: episode["order"] for episode in specs}
    reference_candidates: dict[str, set[str]] = {episode_id: set() for episode_id in episodes_by_id}
    for group in REFERENCE_GROUPS:
        for episode_id in group:
            reference_candidates[episode_id].update(other for other in group if other != episode_id)
    for episode in specs:
        episode_id = episode["video_id"]
        excluded = {episode_id, *episode["prerequisite_ids"]}
        candidates = (set(episode["references"]) | reference_candidates[episode_id]) - excluded
        if not candidates:
            adjacent_order = episode["order"] + (1 if episode["order"] < len(specs) else -1)
            candidates.add(next(item["video_id"] for item in specs if item["order"] == adjacent_order))
        episode["references"] = sorted(
            candidates,
            key=lambda other: (abs(order_by_id[other] - episode["order"]), order_by_id[other]),
        )[:4]
    example_titles = {example["example_id"]: example["title"] for example in stable_examples}
    for episode in specs:
        episode["chapter_plan"] = episode_chapter_plan(
            episode, example_titles[episode["worked_example_id"]]
        )
        episode["visual_contract"] = episode_visual_contract(episode)
    dialogue_rules = [
        "Each narration cue carries one primary idea.",
        "Every explanatory cue causes or interprets a visible change; narration may not merely read labels.",
        "Define a term in plain language before technical qualifications or acronyms.",
        "Show numerator, denominator, workload, boundary, and uncertainty before speaking a retained ratio.",
        "Leave quiet inspection time after a dense diagram settles.",
        "State what each episode does not establish.",
        "Use matched wording for matched comparisons and neutral wording for mixed, negative, or not-promoted results.",
        "Do not invent an expansion for CRSE; introduce it as the project's CRSE research program.",
        "The closing sentence restates the transferable lesson rather than claiming project superiority.",
        "A script cue is invalid when no reviewer can answer what changed on screen because of that cue.",
    ]
    review_request = load_content_review_request()
    approval_gate = {
        "required": True,
        "separate_from_runpod_authorization": True,
        "status": "review_requested" if review_request else "not_requested",
        "required_artifact_types": [
            "series_manifest", "episode_content_bible", "scripts", "claim_maps",
            "storyboards", "visual_directors", "representative_previews",
        ],
        "review_manifest_sha256": None if review_request is None else review_request["review_manifest_sha256"],
        "approved_by": None,
        "approved_at": None,
        "approval_identity": None,
    }
    claims_by_id = {entry["id"]: entry for entry in claim_registry["claims"]}
    sources_by_id = {entry["id"]: entry for entry in source_registry["sources"]}
    for episode in specs:
        episode["source_ids"] = sorted({
            ref["source_id"]
            for claim_id in episode["claim_ids"]
            for ref in claims_by_id[claim_id]["sources"]
        })
        episode["content_hash"] = episode_content_hash(episode, claims_by_id, sources_by_id)
    result = {
        "schema_version": DEEP_SERIES_SCHEMA_VERSION,
        "status": "proposed",
        "generated_date": GENERATED_DATE,
        "baseline_episode_count": DEEP_SERIES_EPISODE_COUNT,
        "sections": section_values,
        "stable_examples": stable_examples,
        "dialogue_rules": dialogue_rules,
        "approval_gate": approval_gate,
        "episodes": specs,
        "content_hash": "0" * 64,
    }
    result["content_hash"] = content_bible_hash(result)
    if review_request and review_request["bible_content_hash"] != result["content_hash"]:
        # Preserve the old manifest identity as an audit trail, but make the
        # gate visibly stale until the authoring pipeline issues a new request.
        result["approval_gate"]["status"] = "stale"
    return result


def render_episode_content_bible_markdown(bible: dict[str, Any]) -> str:
    gate = bible["approval_gate"]
    if gate["status"] == "review_requested":
        status = "proposed; content review requested"
    elif gate["status"] == "approved":
        status = "content approved; remote and paid work still require separate authorization"
    elif gate["status"] == "stale":
        status = "proposed; prior content review request invalidated by changed source identity"
    else:
        status = "proposed; content approval not yet requested"
    lines = [
        "# CM deep-series episode content bible v2", "",
        f"Status: **{status}**", "",
        f"Baseline episodes: **{bible['baseline_episode_count']}**", "",
        f"Content identity: `{bible['content_hash']}`", "",
        f"Review-manifest identity: `{gate['review_manifest_sha256'] or 'not assigned'}`", "",
        "This document locks lesson ownership, evidence boundaries, visual spines, and dialogue anchors before scripts or paid rendering.", "",
        "## Dialogue rules", "",
    ]
    lines.extend(f"- {rule}" for rule in bible["dialogue_rules"])
    lines.append("")
    by_id = {episode["video_id"]: episode for episode in bible["episodes"]}
    for section in bible["sections"]:
        lines.extend([f"## {section['order']}. {section['title']}", "", section["purpose"], ""])
        for video_id in section["episode_ids"]:
            episode = by_id[video_id]
            lines.extend([
                f"### {episode['order']}. {episode['title']} (`{video_id}`)", "",
                f"**Thesis:** {episode['thesis']}", "",
                f"**Owns:** {'; '.join(episode['owns'])}", "",
                f"**Claims:** {', '.join(episode['claim_ids'])}", "",
                f"**Sources:** {', '.join(episode['source_ids'])}", "",
                f"**Related episodes:** {', '.join(episode['references'])}", "",
                f"**Worked example:** `{episode['worked_example_id']}`", "",
                "**Chapter partition**", "",
            ])
            lines.extend(
                f"- `{chapter['chapter_id']}` {chapter['working_title']} — beats "
                f"{', '.join(str(number) for number in chapter['teaching_beat_numbers'])}; visual systems "
                f"{', '.join(str(number) for number in chapter['visual_spine_indices'])}."
                for chapter in episode["chapter_plan"]
            )
            lines.extend([
                "", "**Visual readiness contract**", "",
                f"- Minimum compositions / meaningful state changes: {episode['visual_contract']['minimum_distinct_compositions']} / {episode['visual_contract']['minimum_meaningful_state_changes']}",
                f"- Required asset kinds: {'; '.join(episode['visual_contract']['required_asset_kinds'])}",
                f"- Imagery policy: {episode['visual_contract']['external_imagery_policy']}",
                f"- Progression: {episode['visual_contract']['progression_rule']}",
                "",
                "**Teaching beats**", "",
            ])
            lines.extend(f"1. {beat}" for beat in episode["teaching_beats"])
            lines.extend(["", "**Visual spine**", ""])
            lines.extend(f"- {visual}" for visual in episode["visual_spine"])
            lines.extend([
                "", "**Dialogue anchors**", "",
                f"- Hook: {episode['dialogue_anchors']['hook']}",
                f"- Definition: {episode['dialogue_anchors']['definition']}",
                f"- Boundary: {episode['dialogue_anchors']['boundary']}",
                f"- Closing: {episode['dialogue_anchors']['closing']}",
                "", f"**Retrieval check:** {episode['retrieval_check']}", "",
                f"**Content hash:** `{episode['content_hash']}`", "",
            ])
    return "\n".join(lines)


def validate_episode_content_bible(
    bible: dict[str, Any], claim_registry: dict[str, Any], source_registry: dict[str, Any]
) -> None:
    validate_schema("episode_content_bible.schema.json", bible)
    episodes = bible["episodes"]
    episode_ids = [episode["video_id"] for episode in episodes]
    if len(episode_ids) != len(set(episode_ids)):
        raise FactoryError("content-bible:duplicate-episode")
    if [episode["order"] for episode in episodes] != list(range(1, DEEP_SERIES_EPISODE_COUNT + 1)):
        raise FactoryError("content-bible:episode-order")
    titles = [episode["title"] for episode in episodes]
    if len(titles) != len(set(titles)):
        raise FactoryError("content-bible:duplicate-title")
    ownership = [owned for episode in episodes for owned in episode["owns"]]
    if len(ownership) != len(set(ownership)):
        raise FactoryError("content-bible:duplicate-ownership")
    known_ids = set(episode_ids)
    known_claims = {entry["id"] for entry in claim_registry["claims"]}
    known_sources = {entry["id"] for entry in source_registry["sources"]}
    example_ids = [example["example_id"] for example in bible["stable_examples"]]
    if len(example_ids) != len(set(example_ids)):
        raise FactoryError("content-bible:duplicate-example")
    for example in bible["stable_examples"]:
        missing_sources = set(example["source_ids"]) - known_sources
        if missing_sources:
            raise FactoryError(f"content-bible:example-source:{example['example_id']}:{sorted(missing_sources)}")
    section_ids = [section["section_id"] for section in bible["sections"]]
    if len(section_ids) != len(set(section_ids)):
        raise FactoryError("content-bible:duplicate-section")
    if [section["order"] for section in bible["sections"]] != list(range(1, len(section_ids) + 1)):
        raise FactoryError("content-bible:section-order")
    section_membership: list[str] = []
    for section in bible["sections"]:
        expected = [
            episode["video_id"] for episode in episodes
            if episode["section_id"] == section["section_id"]
        ]
        if section["episode_ids"] != expected:
            raise FactoryError(f"content-bible:section-membership:{section['section_id']}")
        section_membership.extend(section["episode_ids"])
    if section_membership != episode_ids:
        raise FactoryError("content-bible:section-coverage")
    order_by_id = {episode["video_id"]: episode["order"] for episode in episodes}
    claims_by_id = {entry["id"]: entry for entry in claim_registry["claims"]}
    sources_by_id = {entry["id"]: entry for entry in source_registry["sources"]}
    generic_visuals = {"Validated claim cards", "Scope/boundary badge", "Source-ID footer"}
    expected_chapters = {"focused_explainer": 3, "core_episode": 4, "deep_episode": 5}
    minimum_visual_budgets = {
        "focused_explainer": (15, 38), "core_episode": (24, 60), "deep_episode": (42, 105),
    }
    for episode in episodes:
        video_id = episode["video_id"]
        if not episode["references"]:
            raise FactoryError(f"content-bible:no-cross-reference:{video_id}")
        missing_references = set(episode["references"]) - known_ids
        if missing_references:
            raise FactoryError(f"content-bible:unknown-reference:{video_id}:{sorted(missing_references)}")
        if video_id in episode["references"]:
            raise FactoryError(f"content-bible:self-reference:{video_id}")
        if len(episode["thesis"].split()) > 55:
            raise FactoryError(f"content-bible:verbose-thesis:{video_id}")
        if episode["worked_example_id"] not in example_ids:
            raise FactoryError(f"content-bible:unknown-example:{video_id}")
        missing_claims = set(episode["claim_ids"]) - known_claims
        if missing_claims:
            raise FactoryError(f"content-bible:unknown-claim:{video_id}:{sorted(missing_claims)}")
        expected_source_ids = sorted({
            ref["source_id"]
            for claim_id in episode["claim_ids"]
            for ref in claims_by_id[claim_id]["sources"]
        })
        if episode["source_ids"] != expected_source_ids:
            raise FactoryError(f"content-bible:source-coverage:{video_id}")
        missing_prereqs = set(episode["prerequisite_ids"]) - known_ids
        if missing_prereqs:
            raise FactoryError(f"content-bible:unknown-prerequisite:{video_id}:{sorted(missing_prereqs)}")
        late_prereqs = [
            prereq for prereq in episode["prerequisite_ids"]
            if order_by_id[prereq] >= episode["order"]
        ]
        if late_prereqs:
            raise FactoryError(f"content-bible:late-prerequisite:{video_id}:{late_prereqs}")
        if generic_visuals.intersection(episode["visual_spine"]):
            raise FactoryError(f"content-bible:generic-visual:{video_id}")
        if any(len(visual.split()) < 6 for visual in episode["visual_spine"]):
            raise FactoryError(f"content-bible:underspecified-visual:{video_id}")
        if any("add diagram later" in beat.lower() or "show boxes" in beat.lower() for beat in episode["teaching_beats"]):
            raise FactoryError(f"content-bible:placeholder:{video_id}")
        if episode["duration_minutes"]["minimum"] > episode["duration_minutes"]["maximum"]:
            raise FactoryError(f"content-bible:duration:{video_id}")
        chapters = episode["chapter_plan"]
        if len(chapters) != expected_chapters[episode["duration_tier"]]:
            raise FactoryError(f"content-bible:chapter-count:{video_id}")
        if [chapter["chapter_id"] for chapter in chapters] != [f"c{index:02d}" for index in range(1, len(chapters) + 1)]:
            raise FactoryError(f"content-bible:chapter-order:{video_id}")
        covered_beats = [number for chapter in chapters for number in chapter["teaching_beat_numbers"]]
        if covered_beats != list(range(1, len(episode["teaching_beats"]) + 1)):
            raise FactoryError(f"content-bible:chapter-beat-coverage:{video_id}")
        if any(
            index > len(episode["visual_spine"])
            for chapter in chapters for index in chapter["visual_spine_indices"]
        ):
            raise FactoryError(f"content-bible:chapter-visual-reference:{video_id}")
        visual_contract = episode["visual_contract"]
        minimum_compositions, minimum_states = minimum_visual_budgets[episode["duration_tier"]]
        if visual_contract["minimum_distinct_compositions"] < minimum_compositions:
            raise FactoryError(f"content-bible:visual-composition-budget:{video_id}")
        if visual_contract["minimum_meaningful_state_changes"] < minimum_states:
            raise FactoryError(f"content-bible:visual-state-budget:{video_id}")
        if episode["duration_tier"] == "deep_episode" and len(episode["visual_spine"]) < 4:
            raise FactoryError(f"content-bible:deep-visual-systems:{video_id}")
        if episode["content_hash"] != episode_content_hash(episode, claims_by_id, sources_by_id):
            raise FactoryError(f"content-bible:changed-content-hash:{video_id}")
    expected_hash = content_bible_hash(bible)
    if bible["content_hash"] != expected_hash:
        raise FactoryError("content-bible:changed-root-hash")
    gate = bible["approval_gate"]
    if gate["status"] in {"review_requested", "approved"} and gate["review_manifest_sha256"] is None:
        raise FactoryError("content-bible:review-without-manifest")
    if gate["status"] == "approved":
        if not gate["approved_by"] or not gate["approved_at"] or gate["approval_identity"] is None:
            raise FactoryError("content-bible:approved-without-identity")
        if gate["approval_identity"] != content_approval_identity(bible):
            raise FactoryError("content-bible:changed-approval-identity")
    elif gate["approval_identity"] is not None:
        raise FactoryError("content-bible:identity-without-approval")


def validate_glossary_coverage(bible: dict[str, Any], glossary: dict[str, Any]) -> None:
    corpus = "\n".join(
        " ".join([
            episode["title"], episode["thesis"], *episode["owns"],
            *episode["definitions"], *episode["teaching_beats"],
        ])
        for episode in bible["episodes"]
    )
    missing = []
    for entry in glossary["entries"]:
        candidates = [entry["term"], entry["expansion"]]
        if not any(
            candidate and re.search(rf"(?<!\w){re.escape(candidate)}(?!\w)", corpus, flags=re.IGNORECASE)
            for candidate in candidates
        ):
            missing.append(entry["term"])
    if missing:
        raise FactoryError(f"content-bible:glossary-coverage:{missing}")


def build_content_readiness_audit(bible: dict[str, Any], glossary: dict[str, Any]) -> dict[str, Any]:
    episodes = bible["episodes"]
    summary = {
        "episodes": len(episodes),
        "sections": len(bible["sections"]),
        "stable_examples": len(bible["stable_examples"]),
        "glossary_terms": len(glossary["entries"]),
        "used_claims": len({claim_id for episode in episodes for claim_id in episode["claim_ids"]}),
        "used_sources": len({source_id for episode in episodes for source_id in episode["source_ids"]}),
        "minimum_runtime_minutes": sum(episode["duration_minutes"]["minimum"] for episode in episodes),
        "maximum_runtime_minutes": sum(episode["duration_minutes"]["maximum"] for episode in episodes),
        "planned_chapters": sum(len(episode["chapter_plan"]) for episode in episodes),
        "visual_systems": sum(len(episode["visual_spine"]) for episode in episodes),
        "minimum_distinct_compositions": sum(
            episode["visual_contract"]["minimum_distinct_compositions"] for episode in episodes
        ),
        "minimum_meaningful_state_changes": sum(
            episode["visual_contract"]["minimum_meaningful_state_changes"] for episode in episodes
        ),
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "audit_date": GENERATED_DATE,
        "status": "ready_for_script_and_storyboard_authoring",
        "bible_content_hash": bible["content_hash"],
        "summary": summary,
        "gates": [
            {
                "gate_id": "curriculum-coverage",
                "status": "pass",
                "detail": f"All {DEEP_SERIES_EPISODE_COUNT} stable IDs appear once across nine ordered sections and six stable examples.",
            },
            {
                "gate_id": "partition-and-prerequisites",
                "status": "pass",
                "detail": "Lesson ownership is unique, prerequisites point backward, cross-references are explicit, and every teaching beat belongs to one planned chapter.",
            },
            {
                "gate_id": "wording-and-scope",
                "status": "pass",
                "detail": "Titles are unique, theses stay under 55 words, exclusions/caveats are explicit, and grouped milestones retain separate chapter contracts.",
            },
            {
                "gate_id": "terminology-coverage",
                "status": "pass",
                "detail": f"All {len(glossary['entries'])} controlled glossary terms or acronyms appear in the planned episode content.",
            },
            {
                "gate_id": "claim-source-coverage",
                "status": "pass",
                "detail": "Every episode claim resolves to current registered source hashes; the corrected C16 Linux result and current C17-C23 evidence boundaries are included.",
            },
            {
                "gate_id": "visual-authoring-readiness",
                "status": "pass",
                "detail": "Every episode has specific visual systems, asset kinds, continuity assets, forbidden shortcuts, and duration-scaled composition/state-change budgets.",
            },
            {
                "gate_id": "complete-scripts",
                "status": "pending",
                "detail": f"The content bible is ready to drive authoring, but {DEEP_SERIES_EPISODE_COUNT} complete scripts and sentence-level claim maps have not yet been produced.",
            },
            {
                "gate_id": "storyboards-assets-previews",
                "status": "pending",
                "detail": "Shot-level storyboards, rendered assets, contact sheets, animatics, and representative full-resolution previews remain production work.",
            },
            {
                "gate_id": "human-content-approval",
                "status": "pending",
                "detail": "Content approval has not been requested and remains separate from any future RunPod authorization.",
            },
        ],
        "partition_decisions": [
            {
                "scope": "Foundations through CM-IR",
                "decision": "Keep Boolean semantics, explicit dense CM, CM-IR identity, and execution paths in separate sequential sections.",
                "rationale": "This prevents a dense output layout, a shared graph, and an evaluator backend from being narrated as one object.",
            },
            {
                "scope": "Comparator and measurement sequence",
                "decision": "Teach AST/CSE/CSE-flat/CM-IR mechanisms and flat lowering before timing boundaries, ratios, and retained results.",
                "rationale": "Viewers can interpret instruction and timing evidence only after the compared artifacts and boundaries are visible.",
            },
            {
                "scope": "Applications",
                "decision": "Keep configuration, circuits, and policy/rule workloads as separate episodes under one task-to-output toolbox map.",
                "rationale": "Their requested outputs, reuse patterns, revisions, and retained evidence differ enough that one generic application montage would mislead.",
            },
            {
                "scope": "CRSE C milestones",
                "decision": "Keep C3-C5 and C6-C8 as deep progression episodes, retain dedicated C9-C11 and C12-C16 episodes, split C17-C20 policy evidence from the task-matched C21-C22 portfolio, and give C23 fresh-source transfer its own evidence episode.",
                "rationale": "The post-C16 work has two different questions: whether an exact-arm policy transfers and sheds overhead, and whether task-matched methods reveal a worthwhile new representation path. Combining them would hide freshness, lifecycle, and completion-cost boundaries.",
            },
            {
                "scope": "CRSE D and E milestones",
                "decision": "Use one chaptered D-D7 evolution episode, keep D8, D9, and D10 separate, and pair E1/E2 only inside distinct BDD and SAT chapters.",
                "rationale": "D8-D10 have independent promotion decisions; E1/E2 share exact-advice/fallback logic but retain different output contracts and visual systems.",
            },
            {
                "scope": "Provenance",
                "decision": "End with a dedicated source-hash and approval-identity episode rather than scattering provenance as footnotes.",
                "rationale": "Source, claim, content, render, release, content approval, and RunPod authorization form one teachable chain with distinct effects.",
            },
        ],
        "corrections_applied": [
            "Made the initial matrix/CNN/GNN/fused/retrieval Milestone C result an explicit chapter and claim in the CRSE orientation episode.",
            "Added the previously missing C9-C11 exact-routing progression as a dedicated episode with retained negative profitability evidence.",
            "Reconciled C16 with the corrected Linux v2 second-machine pass and retained tiny-case/fresh-family limits.",
            "Added a dedicated C17-C20 episode separating charged dispatch, independent transfer, sealed phase separation, constant folding, and retrospective tail evidence.",
            "Added a dedicated C21-C22 episode separating the best-exact task contract, seven-method whole-task table, source-packed representation effect, proposal abstention, and implementation-only portfolio status.",
            "Added a dedicated C23 episode separating source-family freshness, the corrected task-complete freeze, unchanged-method exact transfer, narrow fixed-path differences, routing headroom, and pending machine transfer.",
            "Added explicit related-episode references so prerequisite and neighboring lesson boundaries are reviewable.",
            f"Partitioned all {sum(len(episode['teaching_beats']) for episode in episodes)} teaching beats into duration-scaled chapter plans, including explicit C9-C11, C12-C16, C17-C20, C21-C22, C23, D-D7, and E1/E2 chapters.",
            "Added duration-scaled visual composition and meaningful-state budgets plus asset-kind and imagery policies for every episode.",
            "Added validation for unique ownership, succinct theses, complete beat/chapter coverage, specific visuals, source coverage, and visual budgets.",
        ],
        "open_gates": [
            f"Author all {DEEP_SERIES_EPISODE_COUNT} complete scripts and sentence-level narration/caption/claim maps.",
            "Create shot-level storyboards and visual-director documents from the chapter and visual contracts.",
            "Build or license required assets and produce contact sheets, animatics, and representative previews.",
            "Preserve the final editorial contracts and newly registered authoritative evidence files in version control before treating the baseline as portable.",
            "Run human editorial/listening review and approve one exact content-review manifest.",
            "Prepare and request a separate exact RunPod proposal only after content approval, if remote rendering is still needed.",
        ],
        "episodes": [
            {
                "video_id": episode["video_id"],
                "status": "ready_for_authoring",
                "chapter_count": len(episode["chapter_plan"]),
                "visual_system_count": len(episode["visual_spine"]),
                "minimum_distinct_compositions": episode["visual_contract"]["minimum_distinct_compositions"],
                "minimum_meaningful_state_changes": episode["visual_contract"]["minimum_meaningful_state_changes"],
                "claim_count": len(episode["claim_ids"]),
                "source_count": len(episode["source_ids"]),
                "cross_reference_count": len(episode["references"]),
            }
            for episode in episodes
        ],
        "audit_sha256": "0" * 64,
    }
    result["audit_sha256"] = canonical_sha256({key: value for key, value in result.items() if key != "audit_sha256"})
    return result


def render_content_readiness_audit_markdown(audit: dict[str, Any]) -> str:
    summary = audit["summary"]
    lines = [
        "# CM deep-series v2 content-readiness audit", "",
        f"Status: **{audit['status'].replace('_', ' ')}**", "",
        f"Bible content identity: `{audit['bible_content_hash']}`", "",
        f"Audit identity: `{audit['audit_sha256']}`", "",
        "The curriculum is ready to drive full script and storyboard authoring. It is not yet render-ready or content-approved.", "",
        "## Coverage summary", "",
        f"- {summary['episodes']} episodes in {summary['sections']} sections; {summary['stable_examples']} stable examples and {summary['glossary_terms']} controlled glossary terms.",
        f"- {summary['used_claims']} used claims bound to {summary['used_sources']} used sources.",
        f"- {summary['minimum_runtime_minutes']}-{summary['maximum_runtime_minutes']} planned finished minutes.",
        f"- {summary['planned_chapters']} planned chapters and {summary['visual_systems']} episode-specific visual systems.",
        f"- At least {summary['minimum_distinct_compositions']} distinct compositions and {summary['minimum_meaningful_state_changes']} meaningful state changes across the series.",
        "", "A state change can be a highlight, construction step, value update, camera/composition change, prediction pause, or answer reveal; it is not a requirement for a separate asset.", "",
        "## Gates", "",
    ]
    lines.extend(
        f"- **{gate['status'].upper()} — {gate['gate_id']}**: {gate['detail']}"
        for gate in audit["gates"]
    )
    lines.extend(["", "## Partition decisions", ""])
    for decision in audit["partition_decisions"]:
        lines.extend([
            f"### {decision['scope']}", "",
            decision["decision"], "", decision["rationale"], "",
        ])
    lines.extend(["## Corrections applied", ""])
    lines.extend(f"- {item}" for item in audit["corrections_applied"])
    lines.extend(["", "## Open production gates", ""])
    lines.extend(f"- {item}" for item in audit["open_gates"])
    lines.extend(["", "## Episode readiness", ""])
    lines.append("| Episode | Chapters | Visual systems | Min compositions | Min state changes | Claims | Sources | Related |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for episode in audit["episodes"]:
        lines.append(
            f"| `{episode['video_id']}` | {episode['chapter_count']} | {episode['visual_system_count']} | "
            f"{episode['minimum_distinct_compositions']} | {episode['minimum_meaningful_state_changes']} | "
            f"{episode['claim_count']} | {episode['source_count']} | {episode['cross_reference_count']} |"
        )
    lines.append("")
    return "\n".join(lines)


def validate_content_readiness_audit(
    audit: dict[str, Any], bible: dict[str, Any], glossary: dict[str, Any]
) -> None:
    validate_schema("content_readiness_audit.schema.json", audit)
    validate_glossary_coverage(bible, glossary)
    if audit["bible_content_hash"] != bible["content_hash"]:
        raise FactoryError("content-audit:bible-hash")
    if [episode["video_id"] for episode in audit["episodes"]] != [episode["video_id"] for episode in bible["episodes"]]:
        raise FactoryError("content-audit:episode-coverage")
    expected = build_content_readiness_audit(bible, glossary)
    if audit != expected:
        raise FactoryError("content-audit:out-of-sync")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def geomean(values: Iterable[float]) -> float:
    values = list(values)
    if not values or any(value <= 0 for value in values):
        raise FactoryError("geomean requires positive values")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def build_visual_data(source_registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_id = {entry["id"]: entry for entry in source_registry["sources"]}
    inference = read_csv(REPO_ROOT / by_id["src-b2b4-v3-inference"]["path"])

    def inference_row(scope: str, live_k: str, metric: str) -> dict[str, str]:
        matches = [row for row in inference if row["scope"] == scope and row["live_k"] == live_k and row["metric"] == metric]
        if len(matches) != 1:
            raise FactoryError(f"expected one inference row for {scope}/{live_k}/{metric}")
        return matches[0]

    overall = inference_row("overall", "all", "cm_current_over_cse_flat_current")
    k16 = inference_row("live_k", "16", "cm_current_over_cse_flat_current")
    wrapper = inference_row("overall", "all", "cm_wrapper_over_cse_flat_current")
    b2b4 = {
        "schema_version": SCHEMA_VERSION, "id": "b2b4-v3-kernel-ratios", "chart_type": "ratio_ci",
        "claim_ids": ["b2b4-v3-kernel", "b2b4-v3-k16", "public-wrapper-slower"],
        "source_ids": ["src-b2b4-v3-inference", "src-b2b4-v3-audit"],
        "values": [
            {"label": "Bare CM / CSE-flat · all", "value": float(overall["paired_formula_cluster_geomean"]),
             "ci_low": float(overall["paired_formula_cluster_bootstrap_ci95_low"]), "ci_high": float(overall["paired_formula_cluster_bootstrap_ci95_high"]),
             "numerator": "bare CM", "denominator": "sharing-aware CSE-flat", "boundary": "compiled evaluator kernel", "workload": "B2/B4 V3", "formula_clusters": int(overall["formula_cluster_count"])},
            {"label": "Bare CM / CSE-flat · k=16", "value": float(k16["paired_formula_cluster_geomean"]),
             "ci_low": float(k16["paired_formula_cluster_bootstrap_ci95_low"]), "ci_high": float(k16["paired_formula_cluster_bootstrap_ci95_high"]),
             "numerator": "bare CM", "denominator": "sharing-aware CSE-flat", "boundary": "compiled evaluator kernel", "workload": "B2/B4 V3 · live support 16", "formula_clusters": int(k16["formula_cluster_count"])},
            {"label": "Public wrapper / CSE-flat", "value": float(wrapper["paired_formula_cluster_geomean"]),
             "ci_low": float(wrapper["paired_formula_cluster_bootstrap_ci95_low"]), "ci_high": float(wrapper["paired_formula_cluster_bootstrap_ci95_high"]),
             "numerator": "public CM wrapper", "denominator": "sharing-aware CSE-flat", "boundary": "public wrapper", "workload": "B2/B4 V3", "formula_clusters": int(wrapper["formula_cluster_count"])},
        ],
        "transformation": {
            "script": "docs/video_factory/factory.py:build_visual_data",
            "description": "Select exact accepted inference rows by scope/live_k/metric; convert CSV numeric fields without narrative retyping.",
            "input_hashes": {"src-b2b4-v3-inference": by_id["src-b2b4-v3-inference"]["sha256"]},
        },
    }
    epfl_rows = read_csv(REPO_ROOT / by_id["src-epfl-summary"]["path"])
    epfl_row = [row for row in epfl_rows if row["group"] == "all:primary_cm_cse_flat_blocked"]
    if len(epfl_row) != 1:
        raise FactoryError("accepted EPFL primary row is missing or ambiguous")
    row = epfl_row[0]
    epfl = {
        "schema_version": SCHEMA_VERSION, "id": "epfl-parity", "chart_type": "ratio_ci",
        "claim_ids": ["epfl-parity", "epfl-mechanism", "epfl-preparation-cost"],
        "source_ids": ["src-epfl-summary", "src-epfl-results", "src-epfl-report"],
        "values": [{
            "label": "CM / CSE-flat · EPFL", "value": float(row["geomean_cm_cse_flat_blocked"]),
            "ci_low": float(row["ci95_lo"]), "ci_high": float(row["ci95_hi"]),
            "numerator": "CM", "denominator": "sharing-aware CSE-flat", "boundary": "compiled evaluator kernel",
            "workload": "EPFL AND/INV cones", "n_formulas": int(row["n_formulas"]),
            "instruction_ratio": 1.0, "executed_operation_ratio": 1.0,
            "preparation_multiple": 4.11, "finite_break_even_median": 174.5, "never_break_even": 55,
        }],
        "transformation": {
            "script": "docs/video_factory/factory.py:build_visual_data",
            "description": "Select the accepted all:primary CM/CSE-flat blocked row from retained machine CSV; attach protocol fields whose exact values are retained in the accepted report.",
            "input_hashes": {"src-epfl-summary": by_id["src-epfl-summary"]["sha256"], "src-epfl-results": by_id["src-epfl-results"]["sha256"]},
        },
    }
    pod_ids = ["src-runpod-pod1-raw", "src-runpod-pod2-raw", "src-runpod-pod3-raw"]
    pod_values = []
    for index, source_id in enumerate(pod_ids, 1):
        rows = read_csv(REPO_ROOT / by_id[source_id]["path"])
        all_values = [float(row["cm_current_over_cse_flat_current"]) for row in rows]
        k16_values = [float(row["cm_current_over_cse_flat_current"]) for row in rows if row["live_k"] == "16"]
        pod_values.append({
            "label": f"CPU pod {index}", "overall": geomean(all_values), "k16": geomean(k16_values),
            "numerator": "bare CM", "denominator": "sharing-aware CSE-flat",
            "boundary": "compiled evaluator kernel", "workload": "B2/B4 corrected", "rows": len(rows),
        })
    runpod = {
        "schema_version": SCHEMA_VERSION, "id": "b2b4-runpod-replication", "chart_type": "replication_range",
        "claim_ids": ["b2b4-runpod-replication"], "source_ids": pod_ids,
        "values": pod_values,
        "transformation": {
            "script": "docs/video_factory/factory.py:build_visual_data",
            "description": "Compute the geometric mean of retained per-formula CM/CSE-flat ratios for all rows and live_k=16 independently for each immutable pod CSV.",
            "input_hashes": {source_id: by_id[source_id]["sha256"] for source_id in pod_ids},
        },
    }
    return {"b2b4_v3_kernel.json": b2b4, "epfl_parity.json": epfl, "runpod_replication.json": runpod}


def graph(label: str, tone: str, nodes: list[dict[str, Any]], edges: list[dict[str, Any]], note: str = "") -> dict[str, Any]:
    return {"label": label, "note": note, "tone": tone, "nodes": nodes, "edges": edges}


def teaching_matrix() -> dict[str, Any]:
    bits = []
    row_labels = []
    column_labels = []
    for x0 in (0, 1):
        for x1 in (0, 1):
            row_labels.append(f"x0x1={x0}{x1}")
            for _x2 in (0, 1):
                for _x3 in (0, 1):
                    bits.append(str(x0 ^ x1))
    for x2 in (0, 1):
        for x3 in (0, 1):
            column_labels.append(f"x2x3={x2}{x3}")
    return {"rows": 4, "columns": 4, "bits": "".join(bits), "row_labels": row_labels, "column_labels": column_labels}


def cm_scene(
    scene_id: str, purpose: str, visual: str, data: dict[str, Any], claim_ids: list[str],
    source_ids: list[str], caption: str, duration: float, status: str, boundary: str = "",
    data_refs: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    renderer_status = "conceptual" if status == "conceptual" else ("mixed" if status == "mixed" else status)
    renderer = {
        "id": scene_id, "kind": "cm_science", "duration": duration,
        "data": {
            "eyebrow": "CORRESPONDENCE MATRICES", "title": purpose, "caption": caption,
            "status": renderer_status, "conceptual": status == "conceptual",
            "claim_ids": claim_ids, "source_ids": source_ids, "visual": visual, **data,
        }, "script": "",
    }
    editorial = {
        "id": scene_id, "purpose": purpose, "primitive": f"cm_science:{visual}",
        "data_refs": data_refs or [], "claim_ids": claim_ids, "caption": caption,
        "narration": "", "duration_s": duration, "transition": "cut",
        "measurement_boundary": boundary, "status": status,
    }
    return editorial, renderer


def build_proofs(visual_data: dict[str, dict[str, Any]]) -> tuple[dict[str, dict], dict[str, dict]]:
    matrix = teaching_matrix()
    foundation_scenes: list[tuple[dict, dict]] = []
    foundation_scenes.append(cm_scene(
        "expression-to-layout", "A Boolean function inside an ambient assignment universe", "expression_matrix",
        {"expression": "x0 XOR x1", "ambient_variables": ["x0", "x1", "x2", "x3"], "live_variables": ["x0", "x1"], "matrix": matrix},
        ["cm-explicit-definition", "live-vs-ambient"], ["src-cm-build", "src-cm-ir"],
        "CONCEPTUAL TEACHING EXAMPLE · x2 and x3 shape the 4×4 layout but do not change this function.", 2.4, "conceptual", "representation",
    ))
    foundation_scenes.append(cm_scene(
        "what-is-cm", "What the explicit matrix is — and is not", "result",
        {"bullets": [
            "It is an exact truth-layout over declared row and column variables.",
            "It is not proof that a dense matrix is the cheapest execution path.",
            "It is not the same artifact as the canonical CM-IR program graph.",
        ]},
        ["cm-explicit-definition", "dense-vs-ir-distinct"], ["src-cm-build", "src-cm-ir"],
        "Representation, compilation, and execution cost remain separate questions.", 2.0, "confirmed", "representation",
    ))
    foundation_scenes.append(cm_scene(
        "foundation-close", "Keep live support and ambient size separate", "result",
        {"bullets": ["Ask which variables affect the function.", "Then ask which variables define the displayed universe."]},
        ["live-vs-ambient"], ["src-cm-ir", "src-cm-build"],
        "The same function can sit inside more than one ambient layout.", 1.4, "confirmed", "representation",
    ))

    ir_nodes = [
        {"id": "x0", "label": "x0", "x": 180, "y": 570, "tone": "cm_ir", "shape": "circle"},
        {"id": "x1", "label": "x1", "x": 420, "y": 570, "tone": "cm_ir", "shape": "circle"},
        {"id": "x2", "label": "x2", "x": 820, "y": 570, "tone": "cm_ir", "shape": "circle"},
        {"id": "and", "label": "AND", "x": 300, "y": 380, "tone": "cm_ir", "shape": "box"},
        {"id": "root", "label": "OR", "x": 540, "y": 150, "tone": "cm_ir", "shape": "double"},
    ]
    ir_edges = [
        {"source": "x0", "target": "and"}, {"source": "x1", "target": "and"},
        {"source": "and", "target": "root", "label": "shared", "shared": True},
        {"source": "x2", "target": "root"},
    ]
    representation_scenes: list[tuple[dict, dict]] = []
    representation_scenes.append(cm_scene(
        "two-artifacts", "One Boolean computation, two different artifacts", "representation_compare",
        {"matrix": matrix, "graphs": [graph("Canonical / interned CM-IR DAG", "cm_ir", ir_nodes, ir_edges, "Structure and reuse are explicit")]} ,
        ["cm-explicit-definition", "cm-ir-definition", "dense-vs-ir-distinct"], ["src-cm-build", "src-cm-ir"],
        "The matrix indexes truth positions. The DAG indexes reusable computation structure.", 2.8, "conceptual", "representation",
    ))
    representation_scenes.append(cm_scene(
        "ir-to-output", "CM-IR can evaluate without rebuilding a dense matrix", "boundary",
        {"steps": [
            {"label": "Canonical CM-IR", "note": "interned DAG and reusable keys", "boundary": "COMPILED ARTIFACT", "tone": "cm_ir"},
            {"label": "Packed / flat evaluation", "note": "exact truth output without dense reinflation", "boundary": "EVALUATION", "tone": "confirmed"},
            {"label": "Optional dense CM", "note": "materialize only when the matrix contract is required", "boundary": "OUTPUT", "tone": "cm"},
        ]},
        ["cm-ir-definition", "dense-vs-ir-distinct", "variants-implemented"], ["src-cm-ir", "src-bitset"],
        "A dense CM is one output choice, not the definition of every CM-IR execution.", 2.4, "confirmed", "evaluation and output",
    ))
    representation_scenes.append(cm_scene(
        "different-costs", "Different artifacts answer different questions", "result",
        {"bullets": [
            "Use the dense CM when the explicit row/column truth layout is the required artifact.",
            "Use CM-IR when canonical structure, reuse, compiled evaluation, or persistence is the question.",
            "Measure construction, extraction, and reuse separately.",
        ]},
        ["dense-vs-ir-distinct", "no-universal-winner"], ["src-cm-ir", "src-cm-build", "src-correction-report"],
        "The label CM never erases the boundary being measured.", 1.8, "confirmed", "multiple boundaries",
    ))

    leaf_nodes = [
        {"id": "a1", "label": "A", "x": 120, "y": 610, "tone": "ast", "shape": "circle"},
        {"id": "b1", "label": "B", "x": 310, "y": 610, "tone": "ast", "shape": "circle"},
        {"id": "ab1", "label": "AND", "x": 210, "y": 430, "tone": "ast", "shape": "box"},
        {"id": "a2", "label": "A", "x": 520, "y": 610, "tone": "ast", "shape": "circle"},
        {"id": "b2", "label": "B", "x": 710, "y": 610, "tone": "ast", "shape": "circle"},
        {"id": "ab2", "label": "AND", "x": 615, "y": 430, "tone": "ast", "shape": "box"},
        {"id": "c", "label": "C", "x": 890, "y": 430, "tone": "ast", "shape": "circle"},
        {"id": "root", "label": "OR", "x": 520, "y": 150, "tone": "ast", "shape": "double"},
    ]
    ast_edges = [
        {"source": "a1", "target": "ab1"}, {"source": "b1", "target": "ab1"},
        {"source": "a2", "target": "ab2"}, {"source": "b2", "target": "ab2"},
        {"source": "ab1", "target": "root"}, {"source": "ab2", "target": "root"}, {"source": "c", "target": "root"},
    ]
    shared_nodes = [node for node in leaf_nodes if node["id"] not in {"a2", "b2", "ab2"}]
    shared_edges = [edge for edge in ast_edges if edge["source"] not in {"a2", "b2", "ab2"}]
    shared_edges.append({"source": "ab1", "target": "root", "label": "reuse", "shared": True})
    flat_nodes = [dict(node) for node in shared_nodes]
    flat_nodes[-1] = {**flat_nodes[-1], "label": "OR₃", "tone": "cse_flat"}
    cmir_nodes = [dict(node) for node in flat_nodes]
    cmir_nodes[-1] = {**cmir_nodes[-1], "label": "OR · canonical", "tone": "cm_ir"}
    comparison_scenes: list[tuple[dict, dict]] = []
    comparison_scenes.append(cm_scene(
        "mechanisms", "Which transformation removed the work?", "transform_compare",
        {"graphs": [
            graph("Raw AST", "ast", leaf_nodes, ast_edges, "Repeated (A AND B) appears twice"),
            graph("Plain structural CSE", "cse", shared_nodes, shared_edges, "One shared subtree; binary chain may remain"),
            graph("Sharing-aware CSE-flat", "cse_flat", flat_nodes, shared_edges, "Reuse plus safe associative flattening"),
            graph("CM-IR", "cm_ir", cmir_nodes, shared_edges, "Shared ground plus canonical normalization / merging"),
        ]},
        ["cse-definition", "cse-flat-definition", "cm-extra-transformations"], ["src-correction-report", "src-cm-ir"],
        "CONCEPTUAL MECHANISM · attribute a measured change only to transformations present on that workload.", 3.2, "conceptual", "mechanism",
    ))
    comparison_scenes.append(cm_scene(
        "boundaries", "Three timing boundaries that must not be blended", "boundary",
        {"steps": [
            {"label": "Prepare", "note": "compile, canonicalize, intern", "boundary": "ONE-TIME", "tone": "cm_ir"},
            {"label": "Evaluate bare program", "note": "program and environment already built", "boundary": "KERNEL", "tone": "confirmed"},
            {"label": "Call public wrapper", "note": "surrounding work and truth-output contract", "boundary": "WRAPPER", "tone": "wrapper"},
        ]},
        ["b2b4-v3-kernel", "public-wrapper-slower", "epfl-preparation-cost"], ["src-correction-report", "src-b2b4-v3-inference", "src-epfl-report"],
        "A bare-kernel ratio is not a one-off public-API speedup.", 2.3, "confirmed", "preparation / kernel / wrapper",
    ))
    b2_values = visual_data["b2b4_v3_kernel.json"]["values"]
    epfl_value = visual_data["epfl_parity.json"]["values"][0]
    comparison_scenes.append(cm_scene(
        "evidence", "Current corrected evidence: scoped reduction, scoped parity, slower wrapper", "ratio",
        {"ratios": [
            {**{key: b2_values[0][key] for key in ("label", "value", "ci_low", "ci_high", "numerator", "denominator", "boundary", "workload")}, "note": "formula-cluster 95% CI", "tone": "confirmed"},
            {**{key: epfl_value[key] for key in ("label", "value", "ci_low", "ci_high", "numerator", "denominator", "boundary", "workload")}, "note": "circuit-cluster 95% CI", "tone": "mixed"},
            {**{key: b2_values[2][key] for key in ("label", "value", "ci_low", "ci_high", "numerator", "denominator", "boundary", "workload")}, "note": "formula-cluster 95% CI", "tone": "negative"},
        ]},
        ["b2b4-v3-kernel", "epfl-parity", "public-wrapper-slower", "ratio-label-rule"],
        ["src-b2b4-v3-inference", "src-epfl-summary"],
        "Below one favors CM only because each row declares CM as numerator. Workloads and boundaries are not pooled.", 3.6, "mixed", "multiple explicit boundaries",
        ["visual_data/b2b4_v3_kernel.json", "visual_data/epfl_parity.json"],
    ))
    runpod_values = visual_data["runpod_replication.json"]["values"]
    comparison_scenes.append(cm_scene(
        "replication", "The requested approximately 0.909 result is a replication range", "result",
        {"bullets": [
            f"Three guarded CPU pods: overall {min(v['overall'] for v in runpod_values):.4f}–{max(v['overall'] for v in runpod_values):.4f} CM/CSE-flat.",
            f"At k=16: {min(v['k16'] for v in runpod_values):.4f}–{max(v['k16'] for v in runpod_values):.4f}; the gap narrowed.",
            "This is compiled-kernel evidence on B2/B4, not universal CM dominance.",
        ]},
        ["b2b4-runpod-replication", "no-universal-winner"],
        ["src-runpod-pod1-raw", "src-runpod-pod2-raw", "src-runpod-pod3-raw"],
        "All three pods passed exactness and source-integrity gates; the public wrapper remained slower.", 2.0, "mixed", "compiled evaluator kernel",
        ["visual_data/runpod_replication.json"],
    ))
    comparison_scenes.append(cm_scene(
        "honest-close", "No single fastest-method headline survives these boundaries", "result",
        {"bullets": [
            "B2/B4 V3: a workload-specific bare-program reduction.",
            "EPFL AND/INV: parity where CSE-flat already captured the available flattening.",
            "Public wrapper and preparation: costs can dominate without sufficient reuse.",
        ]},
        ["no-universal-winner", "epfl-mechanism", "epfl-preparation-cost"], ["src-correction-report", "src-epfl-report"],
        "Choose by workload, transformation, reuse, and boundary — not by label.", 1.8, "mixed", "cross-study synthesis",
    ))

    proof_parts = {
        "cm-foundation": foundation_scenes,
        "explicit-cm-vs-cm-ir": representation_scenes,
        "cm-ir-vs-cse-flat": comparison_scenes,
    }
    briefs: dict[str, dict] = {}
    renderer_briefs: dict[str, dict] = {}
    metadata = {
        "cm-foundation": ("Foundations", "What is a correspondence matrix?", "An explicit CM is a truth layout whose live support can be smaller than its ambient universe.", []),
        "explicit-cm-vs-cm-ir": ("Representations", "Are an explicit CM and CM-IR the same thing?", "No. One is a dense truth layout; the other is a canonical shared computation graph.", ["cm-foundation"]),
        "cm-ir-vs-cse-flat": ("Comparators", "What differs between CM-IR and sharing-aware CSE-flat, and what do current timings actually measure?", "They share structural reuse and flattening; CM may add normalization, while measured outcomes remain workload- and boundary-specific.", ["explicit-cm-vs-cm-ir"]),
    }
    for video_id, parts in proof_parts.items():
        series, central, answer, prerequisites = metadata[video_id]
        editorial_scenes = [part[0] for part in parts]
        renderer_scenes = [part[1] for part in parts]
        claim_ids = list(dict.fromkeys(cid for scene in editorial_scenes for cid in scene["claim_ids"]))
        brief = {
            "schema_version": SCHEMA_VERSION, "video_id": video_id, "series": series,
            "title": video_id.replace("-", " ").title(), "promise": answer,
            "audience": "Curious technical viewers; no prior CM implementation knowledge required",
            "assumed_knowledge": ["Boolean values 0 and 1"], "prerequisites": prerequisites,
            "duration_tier": "visual_short", "target_formats": ["16x9"], "status": "draft",
            "hook": central, "central_question": central, "answer": answer,
            "limits": ["Silent local proof with complete on-screen captions", "No universal performance claim", "No paid or cloud service"],
            "closing_takeaway": editorial_scenes[-1]["caption"],
            "claims": [{"claim_id": cid, "wording": "plain"} for cid in claim_ids],
            "scenes": editorial_scenes,
            "display_rules": {
                "scope": "Show workload and population on every measurement scene.",
                "boundary": "Show representation, preparation, kernel, wrapper, or end-to-end explicitly.",
                "uncertainty": "Show interval method and never turn a point estimate into a universal ranking.",
                "conceptual": "Use a visible CONCEPTUAL status and do not imply measured traces.",
                "source_footnotes": "Show source and claim IDs in the safe-zone footer.",
            },
            "narration": {"mode": "off", "pronunciations": {"CM-IR": "C M I R", "CSE": "C S E"}, "caption_contract": "Every explanatory sentence is visible long enough to read; no audio is required."},
            "expected_outputs": ["resolved.spec.json", "ivc.request.json", "assembly.spec.json", "video.mp4", "provenance.json", "gap_report.json", "render_observations.json", "contact-sheet.png"],
            "execution": {"local_suitability": "required Level 1 proof", "remote_suitability": "CPU-only after exact approval", "render_class": "chromium-svg-cpu-small"},
            "content_hash": "0" * 64,
        }
        briefs[video_id] = brief
        renderer_briefs[video_id] = {
            "schema_id": "deterministic-video-brief/v1", "version": "1",
            "title": brief["title"], "subject": "cm_science", "audience": brief["audience"],
            "purpose": brief["promise"], "width": 1920, "height": 1080, "fps": 30,
            "theme": {"id": "technical_reference", "version": "1.0.0"}, "brand": None,
            "content_packs": [{"id": "cm_science", "version": "1.0.0"}], "narration": "off",
            "provenance": {"authority": "CM_Computation/docs/video_factory", "video_id": video_id, "cm_brief_hash": "pending"},
            "scenes": renderer_scenes,
        }
    return briefs, renderer_briefs


def brief_content_hash(brief: dict[str, Any], claims_by_id: dict[str, Any], sources_by_id: dict[str, Any]) -> str:
    payload = dict(brief)
    payload.pop("content_hash", None)
    claim_ids = [entry["claim_id"] for entry in brief["claims"]]
    referenced_sources = sorted({
        ref["source_id"] for claim_id in claim_ids for ref in claims_by_id[claim_id]["sources"]
    })
    evidence = {source_id: sources_by_id[source_id]["sha256"] for source_id in referenced_sources}
    return canonical_sha256({"brief": payload, "evidence": evidence})


def build_catalog(content_bible: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if content_bible is None:
        content_bible = build_episode_content_bible(build_claim_registry(), build_source_registry())
    section_titles = {section["section_id"]: section["title"] for section in content_bible["sections"]}
    legacy_tier = {
        "focused_explainer": "visual_short",
        "core_episode": "core_explainer",
        "deep_episode": "deep_dive",
    }
    priority_ids = {
        "conceptual-vs-measured", "what-is-explicit-cm", "explicit-cm-vs-cm-ir",
        "cse-vs-cse-flat", "instruction-operations-memory", "measurement-boundaries",
        "read-a-ratio", "b2b4-corrected", "epfl-parity", "correction-story",
        "recognition-d8", "source-hash-reproduction",
    }
    candidates = []
    for episode in content_bible["episodes"]:
        tier = legacy_tier[episode["duration_tier"]]
        candidates.append({
            "video_id": episode["video_id"],
            "track": section_titles[episode["section_id"]],
            "title": episode["title"],
            "audience": episode["audience"],
            "prerequisites": episode["prerequisite_ids"],
            "central_question": episode["dialogue_anchors"]["hook"],
            "viewer_outcome": episode["closing_takeaway"],
            "claim_ids": episode["claim_ids"],
            "visuals_and_data": episode["visual_spine"],
            "misconceptions": episode["misconceptions"],
            "caveats": episode["caveats"],
            "duration_tier": tier,
            "reuse_opportunities": [episode["worked_example_id"], *episode["owns"]],
            "render_complexity": "high" if tier == "deep_dive" else ("medium" if tier == "core_explainer" else "low"),
            "priority": "P0" if episode["video_id"] in priority_ids else "P1",
            "status": "proposed",
            "long_form_master": None if tier == "deep_dive" else (
                "recognition-c3-c5" if episode["section_id"] == "recognition-research" else
                "toolbox-map" if episode["section_id"] == "toolbox-applications" else
                "cm-flagship-representation-to-evidence-v1"
            ),
        })
    candidates.append({
        "video_id": "cm-flagship-representation-to-evidence-v1",
        "track": "Rendered pilot",
        "title": "Correspondence Matrices: From Representation to Honest Evidence",
        "audience": "Curious technical viewers",
        "prerequisites": ["conceptual-vs-measured", "what-is-explicit-cm", "explicit-cm-vs-cm-ir", "measurement-boundaries"],
        "central_question": "How do representation, transformation, and measurement boundaries change what CM evidence is allowed to claim?",
        "viewer_outcome": "Follow the seven-chapter pilot from truth layout to scoped corrected evidence.",
        "claim_ids": ["cm-explicit-definition", "cm-ir-definition", "cse-flat-definition", "b2b4-v3-kernel", "epfl-parity", "no-universal-winner"],
        "visuals_and_data": ["Existing seven-chapter rendered pilot and release manifest"],
        "misconceptions": ["The pilot is a substitute for the dedicated deep-series episodes."],
        "caveats": ["The pilot remains a rendered historical baseline; v2 does not mutate its locked release identity."],
        "duration_tier": "deep_dive",
        "reuse_opportunities": ["chapter visual grammar", "claim/source footers", "offline narration pipeline"],
        "render_complexity": "high",
        "priority": "P0",
        "status": "rendered",
        "long_form_master": None,
    })
    first_wave = [
        "conceptual-vs-measured", "what-is-explicit-cm", "explicit-cm-vs-cm-ir",
        "cse-vs-cse-flat", "instruction-operations-memory", "measurement-boundaries",
        "read-a-ratio", "b2b4-corrected", "epfl-parity", "correction-story",
        "recognition-d8",
    ]
    catalog = {
        "schema_version": SCHEMA_VERSION,
        "status": "proposed",
        "generated_date": GENERATED_DATE,
        "candidates": candidates,
        "first_wave": first_wave,
    }
    general = [
        "conceptual-vs-measured", "why-boolean-computation", "expression-truth-function",
        "live-support-ambient", "what-is-explicit-cm", "what-cm-does-not-claim",
        "explicit-cm-vs-cm-ir", "cse-plain-language", "cse-vs-cse-flat",
        "measurement-boundaries", "read-a-ratio", "scope-boundaries", "toolbox-map",
        "representation-decision", "source-hash-reproduction",
    ]
    technical = [episode["video_id"] for episode in content_bible["episodes"]]
    recognition = [
        episode["video_id"] for episode in content_bible["episodes"]
        if episode["section_id"] == "recognition-research"
    ]
    edges = [
        {"from": prereq, "to": episode["video_id"]}
        for episode in content_bible["episodes"]
        for prereq in episode["prerequisite_ids"]
    ]
    series = {
        "schema_version": SCHEMA_VERSION,
        "paths": [
            {"id": "general", "audience": "Curious nontechnical and technical viewers", "video_ids": general, "outcome": "Explain Boolean functions, CM artifacts, comparator fairness, and scoped evidence before choosing a representation."},
            {"id": "technical-research", "audience": "Implementers and research reviewers", "video_ids": technical, "outcome": "Trace every v2 lesson from evidence grammar through representation, execution, comparison, applications, CRSE, and provenance."},
            {"id": "recognition-research", "audience": "Research reviewers", "video_ids": recognition, "outcome": "Follow the current CRSE arc from proposal learning through exact guarded systems and retained negative results."},
        ],
        "edges": edges,
    }
    return catalog, series


def render_catalog_markdown(catalog: dict[str, Any], series: dict[str, Any]) -> str:
    lines = ["# CM candidate video catalog", "", "Status: **proposed, not approved**", "", f"Candidates: {len(catalog['candidates'])}", "", "## Proposed first wave", ""]
    by_id = {item["video_id"]: item for item in catalog["candidates"]}
    for index, video_id in enumerate(catalog["first_wave"], 1):
        item = by_id[video_id]
        lines.append(f"{index}. **{item['title']}** (`{video_id}`) — {item['duration_tier']}; {item['viewer_outcome']}")
    lines.extend(["", "## Learning paths", ""])
    for path in series["paths"]:
        lines.append(f"### {path['id']}")
        lines.append("")
        lines.append(path["outcome"])
        lines.append("")
        lines.append(" → ".join(path["video_ids"]))
        lines.append("")
    lines.extend(["## Full catalog", ""])
    for item in catalog["candidates"]:
        lines.extend([
            f"### {item['title']} (`{item['video_id']}`)", "",
            f"- Track / tier / priority: {item['track']} / {item['duration_tier']} / {item['priority']}",
            f"- Central question: {item['central_question']}",
            f"- Viewer outcome: {item['viewer_outcome']}",
            f"- Prerequisites: {', '.join(item['prerequisites']) or 'none'}",
            f"- Claims: {', '.join(item['claim_ids'])}",
            f"- Caveats: {'; '.join(item['caveats'])}", "",
        ])
    return "\n".join(lines)


def validate_schema(name: str, value: Any) -> None:
    validator = Draft202012Validator(schemas()[name])
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.path) or "$"
        raise FactoryError(f"schema:{name}:{path}: {first.message}")


def validate_business(
    source_registry: dict[str, Any], claim_registry: dict[str, Any], briefs: Iterable[dict[str, Any]],
    *, verify_source_hashes: bool = True,
) -> None:
    sources = source_registry["sources"]
    source_ids = [entry["id"] for entry in sources]
    if len(source_ids) != len(set(source_ids)):
        raise FactoryError("source:duplicate-id")
    sources_by_id = {entry["id"]: entry for entry in sources}
    if verify_source_hashes:
        for entry in sources:
            path = REPO_ROOT / entry["path"]
            if not path.is_file():
                raise FactoryError(f"source:missing:{entry['id']}")
            if file_sha256(path) != entry["sha256"]:
                raise FactoryError(f"source:changed-hash:{entry['id']}")
    claims = claim_registry["claims"]
    claim_ids = [entry["id"] for entry in claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise FactoryError("claim:duplicate-id")
    claims_by_id = {entry["id"]: entry for entry in claims}
    for entry in claims:
        for ref in entry["sources"]:
            if ref["source_id"] not in sources_by_id:
                raise FactoryError(f"claim:missing-source:{entry['id']}:{ref['source_id']}")
    for brief in briefs:
        validate_schema("video_brief.schema.json", brief)
        chosen = [entry["claim_id"] for entry in brief["claims"]]
        for claim_id in chosen:
            if claim_id not in claims_by_id:
                raise FactoryError(f"brief:missing-claim:{brief['video_id']}:{claim_id}")
            if claims_by_id[claim_id]["status"] == "superseded":
                allowed_history = any(
                    scene["status"] == "correction_history" and claim_id in scene["claim_ids"]
                    for scene in brief["scenes"]
                )
                if not allowed_history:
                    raise FactoryError(f"brief:superseded-claim:{brief['video_id']}:{claim_id}")
        for scene in brief["scenes"]:
            for claim_id in scene["claim_ids"]:
                if claim_id not in chosen:
                    raise FactoryError(f"brief:scene-claim-not-selected:{brief['video_id']}:{claim_id}")
                claim_boundary = claims_by_id[claim_id]["measurement_boundary"]
                if claims_by_id[claim_id]["type"] == "measurement" and scene["measurement_boundary"]:
                    if scene["measurement_boundary"] not in claim_boundary and claim_boundary not in scene["measurement_boundary"]:
                        broad = {"multiple explicit boundaries", "preparation / kernel / wrapper", "cross-study synthesis"}
                        if scene["measurement_boundary"] not in broad:
                            raise FactoryError(f"brief:conflicting-boundary:{brief['video_id']}:{scene['id']}:{claim_id}")
            for ref in scene["data_refs"]:
                target = FACTORY_ROOT / ref.split("#", 1)[0]
                if not target.is_file():
                    raise FactoryError(f"brief:missing-data:{brief['video_id']}:{ref}")
        expected = brief_content_hash(brief, claims_by_id, sources_by_id)
        if brief["content_hash"] != expected:
            raise FactoryError(f"brief:changed-hash:{brief['video_id']}")


def content_identity(value: dict[str, Any], field: str = "content_hash") -> str:
    payload = dict(value)
    payload.pop(field, None)
    return canonical_sha256(payload)


def chapter_cache_identity(chapter: dict[str, Any]) -> str:
    return canonical_sha256({
        key: value for key, value in chapter.items()
        if key not in {"status", "cache_identity"}
    })


def _factory_artifact(path_value: str) -> Path:
    path = (FACTORY_ROOT / path_value).resolve()
    try:
        path.relative_to(FACTORY_ROOT.resolve())
    except ValueError as exc:
        raise FactoryError(f"longform:path-outside-factory:{path_value}") from exc
    if not path.is_file():
        raise FactoryError(f"longform:missing-artifact:{path_value}")
    return path


def _verified_artifact(ref: dict[str, str]) -> Path:
    path = _factory_artifact(ref["path"])
    if file_sha256(path) != ref["sha256"]:
        raise FactoryError(f"longform:changed-hash:{ref['path']}")
    return path


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w]+(?:[-'’][\w]+)*\b", text, flags=re.UNICODE))


def validate_longform(source_registry: dict[str, Any], claim_registry: dict[str, Any]) -> None:
    episodes_root = FACTORY_ROOT / "episodes"
    if not episodes_root.is_dir():
        return
    known_sources = {entry["id"] for entry in source_registry["sources"]}
    known_claims = {entry["id"] for entry in claim_registry["claims"]}
    for episode_path in sorted(episodes_root.glob("*/episode.json")):
        episode = json.loads(episode_path.read_text("utf-8"))
        validate_schema("episode.schema.json", episode)
        episode_id = episode["episode_id"]
        if episode["content_hash"] != content_identity(episode):
            raise FactoryError(f"episode:changed-hash:{episode_id}")
        if set(episode["claim_ids"]) - known_claims:
            raise FactoryError(f"episode:missing-claim:{episode_id}")
        if set(episode["source_ids"]) - known_sources:
            raise FactoryError(f"episode:missing-source:{episode_id}")

        chapters: list[dict[str, Any]] = []
        chapter_ids: list[str] = []
        scene_ids_by_chapter: dict[str, set[str]] = {}
        for ref in episode["chapters"]:
            chapter_path = _verified_artifact(ref)
            chapter_value = json.loads(chapter_path.read_text("utf-8"))
            validate_schema("chapter.schema.json", chapter_value)
            if chapter_value["episode_id"] != episode_id or chapter_value["chapter_id"] != ref["chapter_id"]:
                raise FactoryError(f"chapter:identity-mismatch:{ref['chapter_id']}")
            if chapter_value["cache_identity"] != chapter_cache_identity(chapter_value):
                raise FactoryError(f"chapter:changed-cache-identity:{ref['chapter_id']}")
            if set(chapter_value["claim_ids"]) - set(episode["claim_ids"]):
                raise FactoryError(f"chapter:claim-outside-episode:{ref['chapter_id']}")
            if set(chapter_value["source_ids"]) - set(episode["source_ids"]):
                raise FactoryError(f"chapter:source-outside-episode:{ref['chapter_id']}")
            renderer_path = _verified_artifact(chapter_value["renderer_brief"])
            renderer = json.loads(renderer_path.read_text("utf-8"))
            if renderer.get("width") != episode["format"]["width"] or renderer.get("height") != episode["format"]["height"] or renderer.get("fps") != episode["format"]["fps"]:
                raise FactoryError(f"chapter:format-mismatch:{ref['chapter_id']}")
            renderer_duration = sum(float(scene["duration"]) for scene in renderer.get("scenes", []))
            frame_tolerance = 1 / episode["format"]["fps"]
            if abs(renderer_duration - chapter_value["planned_duration_s"]) > frame_tolerance:
                raise FactoryError(f"chapter:duration-mismatch:{ref['chapter_id']}")
            scene_ids_by_chapter[ref["chapter_id"]] = {scene["id"] for scene in renderer.get("scenes", [])}
            chapters.append(chapter_value)
            chapter_ids.append(ref["chapter_id"])
        if len(chapter_ids) != len(set(chapter_ids)):
            raise FactoryError(f"episode:duplicate-chapter:{episode_id}")
        if sorted(chapter["order"] for chapter in chapters) != list(range(1, len(chapters) + 1)):
            raise FactoryError(f"episode:chapter-order:{episode_id}")
        planned_total = sum(float(chapter["planned_duration_s"]) for chapter in chapters)
        if abs(planned_total - episode["target_duration_s"]) > 1 / episode["format"]["fps"]:
            raise FactoryError(f"episode:duration-mismatch:{episode_id}")

        narration_path = _verified_artifact(episode["narration_contract"])
        narration_value = json.loads(narration_path.read_text("utf-8"))
        validate_schema("narration_contract.schema.json", narration_value)
        if narration_value["episode_id"] != episode_id or narration_value["content_hash"] != content_identity(narration_value):
            raise FactoryError(f"narration:identity-mismatch:{episode_id}")
        cue_ids: list[str] = []
        cues_by_chapter: dict[str, list[dict[str, Any]]] = {chapter_id: [] for chapter_id in chapter_ids}
        for cue in narration_value["cues"]:
            cue_id = cue["cue_id"]
            cue_ids.append(cue_id)
            if cue["chapter_id"] not in cues_by_chapter:
                raise FactoryError(f"narration:unknown-chapter:{cue_id}")
            if cue["scene_id"] not in scene_ids_by_chapter[cue["chapter_id"]]:
                raise FactoryError(f"narration:unknown-scene:{cue_id}")
            if cue["text_sha256"] != hashlib.sha256(cue["text"].encode("utf-8")).hexdigest():
                raise FactoryError(f"narration:changed-text-hash:{cue_id}")
            if cue["word_count"] != _word_count(cue["text"]):
                raise FactoryError(f"narration:changed-word-count:{cue_id}")
            if cue["planned_end_s"] <= cue["planned_start_s"]:
                raise FactoryError(f"narration:invalid-window:{cue_id}")
            cues_by_chapter[cue["chapter_id"]].append(cue)
        if len(cue_ids) != len(set(cue_ids)):
            raise FactoryError(f"narration:duplicate-cue:{episode_id}")
        chapter_by_id = {chapter["chapter_id"]: chapter for chapter in chapters}
        for chapter_id, chapter_cues in cues_by_chapter.items():
            ordered = sorted(chapter_cues, key=lambda item: item["planned_start_s"])
            for previous, current in zip(ordered, ordered[1:]):
                if current["planned_start_s"] < previous["planned_end_s"]:
                    raise FactoryError(f"narration:overlap:{current['cue_id']}")
            if ordered and ordered[-1]["planned_end_s"] > chapter_by_id[chapter_id]["planned_duration_s"]:
                raise FactoryError(f"narration:past-chapter:{chapter_id}")
            if set(chapter_by_id[chapter_id]["narration_cue_ids"]) != {cue["cue_id"] for cue in chapter_cues}:
                raise FactoryError(f"chapter:cue-set-mismatch:{chapter_id}")

        caption_path = _verified_artifact(episode["caption_contract"])
        caption_value = json.loads(caption_path.read_text("utf-8"))
        validate_schema("caption_contract.schema.json", caption_value)
        if caption_value["episode_id"] != episode_id or caption_value["content_hash"] != content_identity(caption_value):
            raise FactoryError(f"caption:identity-mismatch:{episode_id}")
        narration_by_id = {cue["cue_id"]: cue for cue in narration_value["cues"]}
        if {cue["cue_id"] for cue in caption_value["cues"]} != set(narration_by_id):
            raise FactoryError(f"caption:cue-set-mismatch:{episode_id}")
        for cue in caption_value["cues"]:
            narration_cue_value = narration_by_id[cue["cue_id"]]
            if cue["chapter_id"] != narration_cue_value["chapter_id"] or cue["scene_id"] != narration_cue_value["scene_id"] or cue["text"] != narration_cue_value["text"]:
                raise FactoryError(f"caption:cue-identity-mismatch:{cue['cue_id']}")
            if cue["end_s"] <= cue["start_s"]:
                raise FactoryError(f"caption:invalid-window:{cue['cue_id']}")

        release_path = FACTORY_ROOT / episode["release_manifest_path"]
        if release_path.is_file():
            release_value = json.loads(release_path.read_text("utf-8"))
            validate_schema("release_manifest.schema.json", release_value)
            if release_value["episode_id"] != episode_id or release_value["content_hash"] != content_identity(release_value):
                raise FactoryError(f"release:identity-mismatch:{episode_id}")


def build_fixtures(briefs: dict[str, dict], claims: dict[str, Any], sources: dict[str, Any]) -> None:
    valid = json.loads(json.dumps(briefs["cm-foundation"]))
    write_json(FACTORY_ROOT / "fixtures" / "valid" / "video_brief.json", valid)
    missing_source_claims = json.loads(json.dumps(claims))
    missing_source_claims["claims"][0]["sources"][0]["source_id"] = "source-does-not-exist"
    write_json(FACTORY_ROOT / "fixtures" / "invalid" / "missing_source.claim_registry.json", missing_source_claims)
    superseded = json.loads(json.dumps(claims))
    superseded["claims"].append({
        **superseded["claims"][0], "id": "historical-superseded-fixture", "status": "superseded",
    })
    bad_brief = json.loads(json.dumps(valid))
    bad_brief["claims"].append({"claim_id": "historical-superseded-fixture", "wording": "plain"})
    bad_brief["content_hash"] = brief_content_hash(
        bad_brief, {entry["id"]: entry for entry in superseded["claims"]},
        {entry["id"]: entry for entry in sources["sources"]},
    )
    write_json(FACTORY_ROOT / "fixtures" / "invalid" / "superseded_claim.video_brief.json", bad_brief)
    write_json(FACTORY_ROOT / "fixtures" / "invalid" / "superseded_claim.claim_registry.json", superseded)
    boundary = json.loads(json.dumps(valid))
    boundary["claims"].append({"claim_id": "b2b4-v3-kernel", "wording": "plain"})
    boundary["scenes"][0]["claim_ids"].append("b2b4-v3-kernel")
    boundary["scenes"][0]["measurement_boundary"] = "public wrapper complete truth-output call"
    boundary["content_hash"] = brief_content_hash(
        boundary, {entry["id"]: entry for entry in claims["claims"]},
        {entry["id"]: entry for entry in sources["sources"]},
    )
    write_json(FACTORY_ROOT / "fixtures" / "invalid" / "conflicting_boundary.video_brief.json", boundary)
    changed = json.loads(json.dumps(valid))
    changed["title"] += " changed"
    write_json(FACTORY_ROOT / "fixtures" / "invalid" / "changed_hash.video_brief.json", changed)


def build() -> None:
    for name, schema in schemas().items():
        write_json(FACTORY_ROOT / "schemas" / name, {"$schema": "https://json-schema.org/draft/2020-12/schema", **schema})
    source_registry = build_source_registry()
    claim_registry = build_claim_registry()
    glossary = build_glossary()
    content_bible = build_episode_content_bible(claim_registry, source_registry)
    content_audit = build_content_readiness_audit(content_bible, glossary)
    visual_data = build_visual_data(source_registry)
    write_json(FACTORY_ROOT / "source_registry.json", source_registry)
    write_json(FACTORY_ROOT / "claim_registry.json", claim_registry)
    write_json(FACTORY_ROOT / "glossary.json", glossary)
    write_json(FACTORY_ROOT / "deep_series" / "episode_content_bible.json", content_bible)
    write_text(
        FACTORY_ROOT / "deep_series" / "EPISODE_CONTENT_BIBLE.md",
        render_episode_content_bible_markdown(content_bible),
    )
    write_json(FACTORY_ROOT / "deep_series" / "content_readiness_audit.json", content_audit)
    write_text(
        FACTORY_ROOT / "deep_series" / "CONTENT_READINESS_AUDIT.md",
        render_content_readiness_audit_markdown(content_audit),
    )
    for name, value in visual_data.items():
        write_json(FACTORY_ROOT / "visual_data" / name, value)
    briefs, renderer_briefs = build_proofs(visual_data)
    sources_by_id = {entry["id"]: entry for entry in source_registry["sources"]}
    claims_by_id = {entry["id"]: entry for entry in claim_registry["claims"]}
    for video_id, brief in briefs.items():
        brief["content_hash"] = brief_content_hash(brief, claims_by_id, sources_by_id)
        renderer_briefs[video_id]["provenance"]["cm_brief_hash"] = brief["content_hash"]
        write_json(FACTORY_ROOT / "briefs" / f"{video_id}.video_brief.json", brief)
        write_json(FACTORY_ROOT / "renderer_briefs" / f"{video_id}.renderer_brief.json", renderer_briefs[video_id])
    catalog, series = build_catalog(content_bible)
    write_json(FACTORY_ROOT / "video_catalog.json", catalog)
    write_json(FACTORY_ROOT / "series_map.json", series)
    write_text(FACTORY_ROOT / "VIDEO_CATALOG.md", render_catalog_markdown(catalog, series))
    build_fixtures(briefs, claim_registry, source_registry)
    validate()


def validate() -> None:
    source_registry = json.loads((FACTORY_ROOT / "source_registry.json").read_text("utf-8"))
    claim_registry = json.loads((FACTORY_ROOT / "claim_registry.json").read_text("utf-8"))
    glossary = json.loads((FACTORY_ROOT / "glossary.json").read_text("utf-8"))
    content_bible = json.loads(
        (FACTORY_ROOT / "deep_series" / "episode_content_bible.json").read_text("utf-8")
    )
    content_audit = json.loads(
        (FACTORY_ROOT / "deep_series" / "content_readiness_audit.json").read_text("utf-8")
    )
    validate_schema("source_registry.schema.json", source_registry)
    validate_schema("claim_registry.schema.json", claim_registry)
    validate_schema("glossary.schema.json", glossary)
    validate_episode_content_bible(content_bible, claim_registry, source_registry)
    validate_content_readiness_audit(content_audit, content_bible, glossary)
    visual_files = sorted((FACTORY_ROOT / "visual_data").glob("*.json"))
    for path in visual_files:
        validate_schema("visual_data.schema.json", json.loads(path.read_text("utf-8")))
    briefs = [json.loads(path.read_text("utf-8")) for path in sorted((FACTORY_ROOT / "briefs").glob("*.json"))]
    validate_business(source_registry, claim_registry, briefs)
    catalog = json.loads((FACTORY_ROOT / "video_catalog.json").read_text("utf-8"))
    series = json.loads((FACTORY_ROOT / "series_map.json").read_text("utf-8"))
    validate_schema("video_catalog.schema.json", catalog)
    validate_schema("series_map.schema.json", series)
    expected_catalog, expected_series = build_catalog(content_bible)
    if catalog != expected_catalog:
        raise FactoryError("content-bible:catalog-out-of-sync")
    if series != expected_series:
        raise FactoryError("content-bible:series-map-out-of-sync")
    validate_longform(source_registry, claim_registry)


def resolved_identity(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "render_sha256": spec["render_sha256"],
        "theme": {
            "id": spec["theme"]["manifest"]["id"], "version": spec["theme"]["manifest"]["theme_version"],
            "pixel_sha256": spec["theme"]["pixel_sha256"],
        },
        "brand": None if spec.get("brand") is None else {
            "id": spec["brand"]["manifest"]["id"], "version": spec["brand"]["manifest"]["brand_version"],
            "pixel_sha256": spec["brand"]["pixel_sha256"],
        },
        "content_packs": [
            {"id": pack["manifest"]["id"], "version": pack["manifest"]["pack_version"], "contract_sha256": pack["contract_sha256"]}
            for pack in spec["content_packs"]
        ],
    }


def integrate() -> None:
    source_registry = json.loads((FACTORY_ROOT / "source_registry.json").read_text("utf-8"))
    sources = {entry["id"]: entry for entry in source_registry["sources"]}
    jobs = []
    job_hashes = {}
    for video_id in ("cm-foundation", "explicit-cm-vs-cm-ir", "cm-ir-vs-cse-flat"):
        proof = FACTORY_ROOT / "proofs" / video_id
        spec_path = proof / "resolved.spec.json"
        if not spec_path.is_file():
            raise FactoryError(f"resolved spec missing for {video_id}: run POP planning first")
        spec = json.loads(spec_path.read_text("utf-8"))
        identity = resolved_identity(spec)
        request = {"spec": str(spec_path.resolve()), "spec_sha256": file_sha256(spec_path), **identity}
        write_json(proof / "ivc.request.json", request)
        duration = sum(float(scene["duration"]) for scene in spec["scenes"])
        assembly = {
            "schema_version": "1.0", "spec_id": video_id.replace("-", "_"),
            "formats": [{"name": "16x9", "width": 1920, "height": 1080, "fps": 30, "audio": False, "burn_captions": False}],
            "slots": [{
                "slot_id": "s01", "duration_s": duration, "fit": "fit",
                "source": {"kind": "generated", "generator": "video_spec", "request": request},
            }],
        }
        write_json(proof / "assembly.spec.json", assembly)
        brief = json.loads((FACTORY_ROOT / "briefs" / f"{video_id}.video_brief.json").read_text("utf-8"))
        evidence_hashes = {source_id: sources[source_id]["sha256"] for source_id in sorted({ref["source_id"] for claim_id in [c["claim_id"] for c in brief["claims"]] for ref in next(item for item in json.loads((FACTORY_ROOT / "claim_registry.json").read_text("utf-8"))["claims"] if item["id"] == claim_id)["sources"]})}
        cache_identity = canonical_sha256({"brief_hash": brief["content_hash"], "spec_hash": file_sha256(spec_path), "format": "16x9", "evidence": evidence_hashes})
        job = {
            "schema_version": SCHEMA_VERSION, "job_id": f"cm-video-level1-{video_id}-16x9-v1", "video_id": video_id,
            "brief_hash": brief["content_hash"], "resolved_spec_hash": file_sha256(spec_path),
            "renderer_revision": "81af0adec2e74bd0a0fa28a99cc0884dbb9b77ec", "orchestrator_revision": "81af0adec2e74bd0a0fa28a99cc0884dbb9b77ec",
            "evidence_hashes": evidence_hashes, "format": {"name": "16x9", "width": 1920, "height": 1080, "fps": 30},
            "resources": {"class": "cpu-chromium-small", "cpu": 4, "ram_gb": 8, "gpu": False},
            "cache_identity": cache_identity, "output_directory": f"proofs/{video_id}/ivc-output",
            "retry_policy": {"max_attempts": 2, "timeout_seconds": 1800, "retry_same_hash_only": True},
        }
        validate_schema("render_job.schema.json", job)
        job_path = proof / "render_job.json"
        write_json(job_path, job)
        jobs.append(job["job_id"])
        job_hashes[job["job_id"]] = file_sha256(job_path)
    batch = {
        "schema_version": SCHEMA_VERSION, "batch_id": "cm-video-level1-proof3-v1", "status": "draft",
        "jobs": jobs, "job_hashes": job_hashes,
        "aggregate": {"videos": 3, "estimated_cpu_minutes": 30.0, "max_parallel": 1},
        "resume": {"completed_cache_identities": [], "continuation_token": canonical_sha256({"jobs": job_hashes, "completed": []})},
        "approval_identity": "0" * 64,
    }
    batch["approval_identity"] = canonical_sha256({key: value for key, value in batch.items() if key != "approval_identity"})
    validate_schema("batch_manifest.schema.json", batch)
    write_json(FACTORY_ROOT / "batch_manifest.json", batch)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "validate", "integrate"))
    args = parser.parse_args()
    if args.command == "build":
        build()
    elif args.command == "validate":
        validate()
    else:
        integrate()


if __name__ == "__main__":
    main()
