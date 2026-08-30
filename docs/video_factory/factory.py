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
GENERATED_DATE = "2026-08-30"
SCHEMA_VERSION = "1.0"
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
    ("src-cm-ir", "cm_ir.py", "implementation", "current", "2026-08-30", [], []),
    ("src-cm-build", "cm_build.py", "implementation", "current", "2026-08-30", [], []),
    ("src-bitset", "bitset_backend.py", "implementation", "current", "2026-08-30", [], []),
    ("src-recognition-readme", "docs/recognition/README.md", "research_index", "current", "2026-08-30", [], []),
    ("src-recognition-roadmap", "docs/recognition/LEARNING_ROADMAP.md", "research_roadmap", "current", "2026-08-30", [], []),
    ("src-recognition-register", "docs/recognition/experiment_register.json", "machine_json", "current", "2026-08-30", [], []),
    ("src-runpod-handoff", "docs/runpod/RUNPOD-SETUP-HANDOFF-2026-08-28.md", "safety_handoff", "current", "2026-08-28", [], []),
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
        claim("cm-explicit-definition", "An explicit CM is a dense truth-layout representation over a declared row/column variable split.", "A CM lays a Boolean function's truth values out as a matrix.", "The public dense output arranges assignments over row variables R and column variables C, with fixed values applied at evaluation.", "fact", "confirmed", "implemented dense output contract", "representation", "none", "not a ratio", "none", [source("src-cm-build", "compile_expr_to_cm and eval_cm_boolean")]),
        claim("live-vs-ambient", "Live support and ambient variables are distinct: live variables affect the function, while ambient variables may still define the displayed assignment universe.", "A function can depend on fewer variables than the table around it.", "Materialization tracks live variables after fixed bindings; an ambient layout may include axes absent from node.vars.", "fact", "confirmed", "CM IR materialization semantics", "representation", "none", "not a ratio", "none", [source("src-cm-ir", "CMNode.vars and materialize_cm"), source("src-cm-build", "R/C/fixed output contract")]),
        claim("cm-ir-definition", "CM-IR is a canonicalized, interned shared DAG intermediate representation.", "CM-IR stores reusable computation structure, not a dense matrix.", "compile_expr_to_cm_ir builds canonical CMNode structures with interning, simplification, sharing-aware associative flattening, and optional persistent caching.", "fact", "confirmed", "current implementation", "representation", "none", "not a ratio", "none", [source("src-cm-ir", "CMIRBuilder and compile_expr_to_cm_ir")]),
        claim("dense-vs-ir-distinct", "An explicit dense CM and CM-IR are different artifacts with different construction, storage, and evaluation boundaries.", "The matrix is an output layout; CM-IR is a reusable program graph.", "materialize_cm produces a dense array, whereas evaluate_compiled/materialize_hybrid_no_reinflate can return packed or flat truth output without dense CM reinflation.", "fact", "confirmed", "current implementation", "representation and evaluation", "none", "not a ratio", "none", [source("src-cm-ir", "CompiledExpr, evaluate_compiled, materialize_cm, materialize_hybrid_no_reinflate"), source("src-cm-build", "compile_expr_to_cm")]),
        claim("cse-definition", "Common subexpression elimination computes repeated expression subtrees once and reuses them.", "CSE shares repeated work.", "Plain structural CSE interns repeated subtrees but may retain binary associative chains.", "fact", "confirmed", "comparator definition used by correction", "mechanism", "plain CSE", "not a ratio", "none", [source("src-correction-report", "What CSE means")]),
        claim("cse-flat-definition", "Sharing-aware CSE-flat additionally flattens eligible associative chains while preserving shared nodes.", "CSE-flat shares repeats and safely widens associative chains.", "The primary comparator is sharing-aware structural CSE with flatten=True; it is stronger than the raw-AST ablation and plain unflattened CSE.", "fact", "confirmed", "corrected comparator contract", "mechanism", "CSE-flat", "not a ratio", "none", [source("src-correction-report", "What CSE means and Corrected issues 3"), source("src-b2b4-v3-audit", "primary_comparator")]),
        claim("cm-extra-transformations", "CM-IR can add canonical normalization and merging beyond the transformations shared with CSE-flat.", "CM-IR and CSE-flat overlap, but CM-IR may normalize more structure.", "Any observed difference must be attributed to the actual instruction/operation reductions on the scoped workload, not to the CM label alone.", "interpretation", "confirmed", "corrected mechanism interpretation", "mechanism", "CSE-flat", "not a ratio", "workload dependent", [source("src-correction-report", "What CSE means")]),
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
        claim("exactness-gates", "Corrected benchmark rows required frozen truth verification and equality across eligible timed arms before performance evidence was accepted.", "Timing rows counted only after exact outputs matched.", "The V3 audit records 264 rows and zero packed mismatches; corrected EPFL verification similarly fails closed on truth digests.", "fact", "confirmed", "corrected benchmark protocols", "correctness gate outside performance claim", "all eligible arms", "not a ratio", "hash/equality gate", [source("src-b2b4-v3-audit", "row_count and packed_mismatch_count"), source("src-correction-report", "EPFL order and frozen truth verification")]),
        claim("crse-experimental", "The CRSE recognition program is experimental; no learned model is promoted.", "The learning work has useful engineering results and retained failures, but no production model.", "The register separates measured slices, exact controls, negative transfer, held or failed criteria, and no-promotion decisions.", "fact", "not_promoted", "current recognition program", "scientific promotion", "exact deterministic controls", "not a ratio", "per-milestone frozen splits and criteria", [source("src-recognition-readme", "What is implemented"), source("src-recognition-register", "research tracks and status reasons")]),
        claim("crse-c2-negative", "Milestone C2's learned representation and size-transfer criteria failed while the exact CM detector remained perfect.", "The learned decomposition detector did not transfer, even though the exact control worked.", "Independent verification recomputed retained tables and model decisions without error; learned criteria failed and no model was promoted.", "measurement", "negative", "Milestone C2 frozen generated/held-out slices", "recognition evaluation", "exact CM detector", "per frozen criterion", "limited target/domain scope", [source("src-recognition-readme", "Milestone C2 summary")]),
        claim("crse-c3-c5-negative", "Natural decomposition, direct-cut, and variable-conditioned learned arms improved some slices but failed the required held-out transfer/promotion criteria.", "Better scores on some circuits did not become reliable held-out cuts.", "C3–C5 retain exact verification, weak accepted-positive recall, held-out square failures, and learned paths slower than exact ANF.", "measurement", "negative", "Milestones C3–C5 natural circuit-disjoint studies", "recognition plus exact acceptance", "exact ANF", "varies by milestone", "circuit-family transfer remained limited", [source("src-recognition-readme", "Milestones C3, C4, C5 summaries")]),
        claim("crse-c6-advance", "Milestone C6's packed exact source-ANF core advanced, but its gate and production path did not.", "A deterministic packed core improved, without promoting the whole system.", "Packed/cached cores achieved retained median and p95 gains over truth-vector ANF; the validation-frozen gate missed confirmatory p95 by 1.4%.", "measurement", "revised", "Milestone C6 frozen EPFL splits", "exact recognition core and gate", "truth-vector ANF", "speedup stated as comparator/core", "bounded one-program slice", [source("src-recognition-readme", "Milestone C6 summary")]),
        claim("crse-d-mixed", "Milestone D task routing helped restrictions and repeated work but slowed complete-vector requests; dense-CM construction and per-instance rewrite proof were negative.", "Routing helped some tasks and hurt others.", "Construction, routing, proof, kernel, cache, and audit costs were measured separately.", "measurement", "revised", "Milestone D generated task-computation study", "end-to-end task boundaries", "direct, CSE, CM-IR, dense CM", "per task", "bounded generated workload", [source("src-recognition-readme", "Milestone D summary")]),
        claim("crse-d8-negative", "The frozen one-pass rewrite result changed from 1.050x on Windows to 0.929x on Linux, so unconditional one-pass rewriting was not promoted.", "The rewrite looked helpful on one machine and lost on Linux.", "Exactness and rule incidence reproduced, but profitability did not transfer; the Linux result is a retained negative control.", "measurement", "negative", "Milestone D8 frozen Linux confirmation", "overhead-inclusive one-pass rewrite", "no rewrite", "reported as speedup; below one loses", "one bounded cross-machine confirmation", [source("src-recognition-readme", "Milestone D8 summary")]),
        claim("crse-d9-not-promoted", "Milestone D9's frozen policy abstained on all evaluation workloads and preserved exactness, but the charged gate remained slower and no rewrite policy was promoted.", "Abstention avoided bad rewrites but still cost time.", "Exact factoring reduced operations, unconditional one pass lost, and the all-abstain gate measured 0.982x versus no rewrite.", "measurement", "not_promoted", "Milestone D9 circuit-disjoint split", "charged policy plus task execution", "no rewrite", "speedup versus no rewrite", "bounded evaluation split", [source("src-recognition-readme", "Milestone D9 summary")]),
        claim("conceptual-label-rule", "Teaching diagrams, proposed mechanisms, and hypotheses must be visibly labeled and may not be presented as measured traces.", "An animation can explain an idea without pretending it was observed.", "Conceptual scene metadata and visible status remain separate from measurement claims and result cards.", "fact", "confirmed", "video evidence contract", "editorial/visual status", "none", "not a ratio", "not applicable", [source("src-recognition-readme", "program scope and promotion boundaries"), source("src-correction-report", "workload-specific interpretation")]),
    ]
    return {"schema_version": SCHEMA_VERSION, "generated_date": GENERATED_DATE, "claims": claims}


def build_glossary() -> dict[str, Any]:
    entries = [
        ("Correspondence matrix", "CM", "A matrix layout of a Boolean function's truth values.", "A dense output indexed by assignments over declared row and column variable sets.", "Not every use of the label CM refers to this dense artifact.", ["src-cm-build", "src-repo-readme"]),
        ("CM intermediate representation", "CM-IR", "A reusable graph program for Boolean computation.", "A canonicalized and interned CMNode DAG with simplification, sharing-aware flattening, and multiple evaluation/materialization paths.", "CM-IR is not the same object as the dense matrix returned by materialize_cm.", ["src-cm-ir"]),
        ("Live support", "", "Variables that can change the function's output.", "The variable set retained by an expression/IR node after simplification and fixed bindings.", "Live support can be smaller than the ambient or syntactic variable universe.", ["src-cm-ir"]),
        ("Ambient universe", "", "Variables included in the surrounding assignment layout.", "The declared row/column or corpus variable axes, including variables that may be semantically dead for one function.", "Ambient count is not a substitute for live support.", ["src-cm-build", "src-correction-report"]),
        ("Common subexpression elimination", "CSE", "Compute a repeated subtree once and reuse it.", "Structural sharing/interning of repeated expression subtrees.", "Plain CSE does not necessarily flatten eligible associative chains.", ["src-correction-report"]),
        ("Sharing-aware CSE-flat", "CSE-flat", "CSE plus safe flattening of associative chains.", "The corrected strong generic comparator: structural sharing with flatten=True while preserving shared nodes.", "It is stronger than raw AST and plain unflattened CSE.", ["src-correction-report", "src-b2b4-v3-audit"]),
        ("Preparation", "", "One-time work to build a reusable compiled artifact.", "Compiler/canonicalizer time measured separately from evaluation.", "Preparation must not be blended into a bare-kernel ratio unless explicitly declared.", ["src-epfl-report"]),
        ("Evaluator kernel", "", "Repeated execution after the program and environment already exist.", "The compiled-program measurement boundary used by the corrected CM/CSE-flat ratios.", "It is not a public-wrapper or end-to-end result.", ["src-correction-report"]),
        ("Public wrapper", "", "The convenient public call including surrounding work.", "The complete wrapper boundary reported separately from bare compiled evaluation.", "A faster kernel does not imply a faster wrapper.", ["src-correction-report"]),
        ("Break-even reuse", "", "How many evaluations are needed to repay extra preparation.", "The solution to accumulated preparation plus per-evaluation cost under a declared model.", "Some workloads never break even.", ["src-epfl-report"]),
        ("Packed bitset", "", "Many truth values stored in machine words or a big integer.", "An exact truth-vector execution backend with explicit ordering and width masking.", "Packed execution is not automatically a dense CM.", ["src-bitset"]),
        ("CRSE", "", "The repository's experimental recognition and computation-selection research program.", "A set of frozen milestone studies with learned proposal paths, exact controls, verification, and explicit promotion decisions.", "Engineering verification is not scientific generalization or deployment.", ["src-recognition-readme", "src-recognition-register"]),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "entries": [
            {"term": term, "expansion": expansion, "plain_definition": plain,
             "technical_definition": technical, "common_confusion": confusion, "source_ids": sources}
            for term, expansion, plain, technical, confusion, sources in entries
        ],
    }


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


def build_catalog() -> tuple[dict[str, Any], dict[str, Any]]:
    rows = [
        ("why-boolean-computation", "Foundations", "Why Boolean computation matters", "visual_short", ["cm-explicit-definition"], [], "Show how one decision rule becomes assignments and outputs."),
        ("expression-truth-function", "Foundations", "Expression, truth table, and Boolean function", "core_explainer", ["cm-explicit-definition"], ["why-boolean-computation"], "Separate syntax from the function it denotes."),
        ("live-support-ambient", "Foundations", "Live support versus ambient variables", "visual_short", ["live-vs-ambient"], ["expression-truth-function"], "Explain why nominal width can overstate the active problem."),
        ("what-is-explicit-cm", "Foundations", "What a correspondence matrix is", "core_explainer", ["cm-explicit-definition", "live-vs-ambient"], ["expression-truth-function"], "Build the row/column truth layout from assignments."),
        ("what-cm-does-not-claim", "Foundations", "What CM does not claim to be", "visual_short", ["dense-vs-ir-distinct", "no-universal-winner"], ["what-is-explicit-cm"], "Refuse speed, solver, and universal representation overclaims."),
        ("explicit-cm-vs-cm-ir", "Foundations", "Explicit dense CM versus CM-IR", "core_explainer", ["cm-ir-definition", "dense-vs-ir-distinct"], ["what-is-explicit-cm"], "Compare truth layout with a canonical computation graph."),
        ("cm-ir-nodes-sharing", "Representations", "CM-IR nodes, sharing, and roots", "core_explainer", ["cm-ir-definition"], ["explicit-cm-vs-cm-ir"], "Read a CMNode DAG and identify reuse."),
        ("canonicalization-interning", "Representations", "Canonicalization, interning, and normalization", "core_explainer", ["cm-ir-definition", "cm-extra-transformations"], ["cm-ir-nodes-sharing"], "Show which rewrites change keys and which preserve meaning."),
        ("eager-lazy", "Representations", "Eager and lazy CM paths", "visual_short", ["variants-implemented"], ["explicit-cm-vs-cm-ir"], "Distinguish when dense work is performed, without inventing a ranking."),
        ("pair-aware", "Representations", "Pair-aware CM collapse", "visual_short", ["variants-implemented"], ["cm-ir-nodes-sharing"], "Explain the fixed-input and two-live-variable eligibility boundary."),
        ("hybrid-partial", "Representations", "Hybrid versus partial-hybrid materialization", "core_explainer", ["variants-implemented"], ["cm-ir-nodes-sharing"], "Separate full bitset collapse from child-level hybrid dispatch."),
        ("parallel-cm", "Representations", "Parallel CM materialization", "visual_short", ["variants-implemented"], ["hybrid-partial"], "Show where parallelism applies and why it is secondary to work reduction."),
        ("packed-words-selection", "Representations", "Packed bitsets, words, and width selection", "core_explainer", ["variants-implemented", "selector-no-width-rule"], ["live-support-ambient"], "Connect support width to packed execution without claiming width alone is sufficient."),
        ("cm-ir-persistence", "Representations", "CM-IR persistence and version identity", "deep_dive", ["cm-ir-definition", "exactness-gates"], ["canonicalization-interning"], "Trace canonical hashes, reload, invalidation, and exact byte checks."),
        ("raw-ast", "Comparators", "Raw AST evaluation as an ablation", "visual_short", ["cse-definition"], ["expression-truth-function"], "Explain why raw AST is informative but not the strongest comparator."),
        ("cse-plain-language", "Comparators", "Common subexpression elimination in plain language", "visual_short", ["cse-definition"], ["raw-ast"], "Animate one repeated subtree becoming one shared result."),
        ("cse-vs-cse-flat", "Comparators", "Plain CSE versus sharing-aware CSE-flat", "core_explainer", ["cse-definition", "cse-flat-definition"], ["cse-plain-language"], "Show safe associative flattening without destroying shared nodes."),
        ("cm-ir-vs-cse-flat-mechanism", "Comparators", "CM-IR versus CSE-flat: common ground and extra transformations", "core_explainer", ["cse-flat-definition", "cm-extra-transformations"], ["cse-vs-cse-flat", "canonicalization-interning"], "Attribute reductions to sharing, flattening, normalization, or merging."),
        ("instruction-operations-memory", "Comparators", "Instructions, primitive operations, and memory traffic", "deep_dive", ["epfl-mechanism", "no-universal-winner"], ["cm-ir-vs-cse-flat-mechanism"], "Keep three proposed mechanisms separate and measurable."),
        ("no-fastest-chart", "Comparators", "Why one blended fastest-method chart is dishonest", "visual_short", ["no-universal-winner", "ratio-label-rule"], ["cm-ir-vs-cse-flat-mechanism"], "Expose incomparable boundaries before ranking anything."),
        ("measurement-boundaries", "Performance", "Preparation, kernel, wrapper, and end-to-end time", "core_explainer", ["b2b4-v3-kernel", "public-wrapper-slower", "epfl-preparation-cost"], ["cm-ir-vs-cse-flat-mechanism"], "Place every cost on a boundary pipeline."),
        ("reuse-break-even", "Performance", "Reuse and break-even economics", "core_explainer", ["epfl-preparation-cost"], ["measurement-boundaries"], "Animate one-time cost and per-evaluation cost without implying all cases break even."),
        ("b2b4-corrected", "Performance", "Corrected B2/B4 V3 kernel result", "core_explainer", ["b2b4-v3-kernel", "b2b4-v3-k16", "exactness-gates"], ["measurement-boundaries", "cse-vs-cse-flat"], "Read the formula-balanced interval and the narrowing k-dependence."),
        ("b2b4-runpod", "Performance", "Three-pod B2/B4 replication", "visual_short", ["b2b4-runpod-replication"], ["b2b4-corrected"], "Distinguish descriptive machine replication from the local interval."),
        ("epfl-parity", "Performance", "EPFL AND/INV parity and its mechanism", "core_explainer", ["epfl-parity", "epfl-mechanism", "epfl-preparation-cost"], ["cse-vs-cse-flat", "measurement-boundaries"], "Show why equal instruction structure predicted parity."),
        ("selector-width-limit", "Performance", "Why width alone did not select the engine", "core_explainer", ["selector-no-width-rule"], ["packed-words-selection"], "Read regret gates and reused-validation limitations."),
        ("exact-comparison-protocol", "Performance", "Truth digests, alternating schedules, clustering, and intervals", "deep_dive", ["exactness-gates", "ratio-label-rule"], ["b2b4-corrected"], "Explain how exactness and dependence-aware inference protect a timing claim."),
        ("correction-story", "Performance", "How an audit changed the headline", "core_explainer", ["b2b4-v3-kernel", "no-universal-winner", "exactness-gates"], ["b2b4-corrected", "epfl-parity"], "Walk from weak comparator language to scoped corrected claims."),
        ("toolbox-map", "Toolbox", "CM, CSE, BitSet, BDD, SAT, Espresso, and SymPy: different questions", "deep_dive", ["variants-implemented", "no-universal-winner"], ["what-cm-does-not-claim"], "Map representations and solvers only to retained evidence and interfaces."),
        ("configuration-models", "Applications", "Configuration and feature-model workloads", "deep_dive", ["no-universal-winner"], ["toolbox-map"], "Separate retained pilots, version deltas, persistence, and direct-task baselines."),
        ("circuits", "Applications", "Circuit workloads: structure, truth, and exact controls", "core_explainer", ["epfl-parity", "exactness-gates"], ["toolbox-map"], "Explain cone support and why AND/INV shape matters."),
        ("policy-rule-systems", "Applications", "Policy and rule systems with related revisions", "core_explainer", ["crse-d-mixed"], ["toolbox-map"], "Frame canonical reuse as a measured question, not a guaranteed win."),
        ("representation-decision", "Applications", "Which representation should I try?", "core_explainer", ["dense-vs-ir-distinct", "no-universal-winner", "selector-no-width-rule"], ["toolbox-map", "measurement-boundaries"], "Choose based on output, reuse, support, exact operations, and evidence status."),
        ("recognition-question", "Recognition", "What the CRSE recognition program asks", "core_explainer", ["crse-experimental", "conceptual-label-rule"], ["cm-ir-nodes-sharing"], "Separate proposal learning from exact verification and promotion."),
        ("recognition-c2", "Recognition", "C2 variable-size decomposition: exact control, learned failure", "core_explainer", ["crse-c2-negative"], ["recognition-question"], "State frozen split, comparator, failure, and no-promotion decision."),
        ("recognition-c3-c5", "Recognition", "C3–C5 natural cuts: improvements without held-out promotion", "deep_dive", ["crse-c3-c5-negative"], ["recognition-c2"], "Track natural positives, matched negatives, cut heads, and transfer failures."),
        ("recognition-c6", "Recognition", "C6 packed exact source ANF: what advanced and what did not", "core_explainer", ["crse-c6-advance"], ["recognition-c3-c5"], "Promote the deterministic core only within its passed criterion."),
        ("recognition-d-tasks", "Recognition", "Milestone D task routing: mixed boundaries", "core_explainer", ["crse-d-mixed"], ["recognition-question", "measurement-boundaries"], "Compare complete vectors, points, restrictions, and repeated work separately."),
        ("recognition-d8", "Recognition", "D8 Linux confirmation: exact but unprofitable", "visual_short", ["crse-d8-negative"], ["recognition-d-tasks"], "Show a successful verification with a negative promotion result."),
        ("recognition-d9", "Recognition", "D9 abstention policy: safe, charged, not promoted", "core_explainer", ["crse-d9-not-promoted"], ["recognition-d8"], "Separate correct abstention from profitable deployment."),
        ("read-a-ratio", "Evidence literacy", "How to read a CM/comparator ratio", "visual_short", ["ratio-label-rule"], ["measurement-boundaries"], "Name direction, scope, interval, and boundary before reading position."),
        ("scope-boundaries", "Evidence literacy", "Why scopes and boundaries matter", "visual_short", ["no-universal-winner", "ratio-label-rule"], ["read-a-ratio"], "Compare B2/B4, EPFL, preparation, kernel, and wrapper without pooling."),
        ("conceptual-vs-measured", "Evidence literacy", "Conceptual animation versus measured result", "visual_short", ["conceptual-label-rule"], [], "Teach the status grammar used in every video."),
        ("source-hash-reproduction", "Evidence literacy", "How a video is bound to source hashes", "core_explainer", ["exactness-gates", "conceptual-label-rule"], ["conceptual-vs-measured"], "Trace source registry to claim, brief, render job, result, and batch identity."),
        ("cm-flagship-representation-to-evidence-v1", "Long-form", "Correspondence Matrices: From Representation to Honest Evidence", "deep_dive", ["cm-explicit-definition", "cm-ir-definition", "cse-flat-definition", "b2b4-v3-kernel", "epfl-parity", "no-universal-winner"], ["what-is-explicit-cm", "explicit-cm-vs-cm-ir", "cm-ir-vs-cse-flat-mechanism", "measurement-boundaries"], "Follow the complete seven-chapter path from truth layout through transformation mechanisms to scoped corrected evidence."),
    ]
    candidates = []
    for video_id, track, title, tier, claim_ids, prerequisites, outcome in rows:
        candidates.append({
            "video_id": video_id, "track": track, "title": title,
            "audience": "Nontechnical viewers" if track in {"Foundations", "Evidence literacy"} else "Technical and research viewers",
            "prerequisites": prerequisites, "central_question": title + "?", "viewer_outcome": outcome,
            "claim_ids": claim_ids, "visuals_and_data": ["Validated claim cards", "Scope/boundary badge", "Source-ID footer"],
            "misconceptions": ["A method label alone determines performance", "An engineering pass implies scientific promotion"],
            "caveats": ["Use only retained evidence within its declared scope", "Do not pool incomparable boundaries"],
            "duration_tier": tier, "reuse_opportunities": ["CM matrix", "CM-IR DAG", "boundary pipeline", "evidence status card"],
            "render_complexity": "high" if tier == "deep_dive" else ("medium" if tier == "core_explainer" else "low"),
            "priority": "P0" if video_id in {
                "what-is-explicit-cm", "explicit-cm-vs-cm-ir", "cse-vs-cse-flat", "cm-ir-vs-cse-flat-mechanism",
                "measurement-boundaries", "b2b4-corrected", "epfl-parity", "read-a-ratio", "correction-story", "recognition-d8",
                "cm-flagship-representation-to-evidence-v1",
            } else "P1",
            "status": "rendered" if video_id == "cm-flagship-representation-to-evidence-v1" else "proposed",
            "long_form_master": None if tier == "deep_dive" else (
                "cm-flagship-representation-to-evidence-v1" if track in {"Foundations", "Representations", "Comparators", "Performance", "Evidence literacy"} else
                "toolbox-map" if track in {"Toolbox", "Applications"} else
                "recognition-c3-c5" if track == "Recognition" else "expression-truth-function"
            ),
        })
    first_wave = [
        "what-is-explicit-cm", "explicit-cm-vs-cm-ir", "cse-vs-cse-flat",
        "cm-ir-vs-cse-flat-mechanism", "measurement-boundaries", "b2b4-corrected",
        "epfl-parity", "read-a-ratio", "correction-story", "recognition-d8",
    ]
    catalog = {"schema_version": SCHEMA_VERSION, "status": "proposed", "generated_date": GENERATED_DATE, "candidates": candidates, "first_wave": first_wave}
    nontechnical = ["why-boolean-computation", "expression-truth-function", "live-support-ambient", "what-is-explicit-cm", "what-cm-does-not-claim", "explicit-cm-vs-cm-ir", "read-a-ratio", "scope-boundaries", "correction-story"]
    technical = ["expression-truth-function", "explicit-cm-vs-cm-ir", "cm-ir-nodes-sharing", "canonicalization-interning", "cse-vs-cse-flat", "cm-ir-vs-cse-flat-mechanism", "measurement-boundaries", "b2b4-corrected", "epfl-parity", "exact-comparison-protocol", "recognition-question", "recognition-d8"]
    edges = []
    for path in (nontechnical, technical):
        edges.extend({"from": left, "to": right} for left, right in zip(path, path[1:]))
    series = {
        "schema_version": SCHEMA_VERSION,
        "paths": [
            {"id": "nontechnical", "audience": "Curious nontechnical viewers", "video_ids": nontechnical, "outcome": "Explain what CM is, what it is not, and how to read scoped evidence."},
            {"id": "technical-research", "audience": "Implementers and research reviewers", "video_ids": technical, "outcome": "Trace representation, compiler transformations, measurement boundaries, inference, and negative promotion results."},
        ],
        "edges": list({(edge["from"], edge["to"]): edge for edge in edges}.values()),
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
    visual_data = build_visual_data(source_registry)
    write_json(FACTORY_ROOT / "source_registry.json", source_registry)
    write_json(FACTORY_ROOT / "claim_registry.json", claim_registry)
    write_json(FACTORY_ROOT / "glossary.json", glossary)
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
    catalog, series = build_catalog()
    write_json(FACTORY_ROOT / "video_catalog.json", catalog)
    write_json(FACTORY_ROOT / "series_map.json", series)
    write_text(FACTORY_ROOT / "VIDEO_CATALOG.md", render_catalog_markdown(catalog, series))
    build_fixtures(briefs, claim_registry, source_registry)
    validate()


def validate() -> None:
    source_registry = json.loads((FACTORY_ROOT / "source_registry.json").read_text("utf-8"))
    claim_registry = json.loads((FACTORY_ROOT / "claim_registry.json").read_text("utf-8"))
    glossary = json.loads((FACTORY_ROOT / "glossary.json").read_text("utf-8"))
    validate_schema("source_registry.schema.json", source_registry)
    validate_schema("claim_registry.schema.json", claim_registry)
    validate_schema("glossary.schema.json", glossary)
    visual_files = sorted((FACTORY_ROOT / "visual_data").glob("*.json"))
    for path in visual_files:
        validate_schema("visual_data.schema.json", json.loads(path.read_text("utf-8")))
    briefs = [json.loads(path.read_text("utf-8")) for path in sorted((FACTORY_ROOT / "briefs").glob("*.json"))]
    validate_business(source_registry, claim_registry, briefs)
    validate_schema("video_catalog.schema.json", json.loads((FACTORY_ROOT / "video_catalog.json").read_text("utf-8")))
    validate_schema("series_map.schema.json", json.loads((FACTORY_ROOT / "series_map.json").read_text("utf-8")))
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
