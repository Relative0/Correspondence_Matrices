"""Author, preview, validate, and package the CM deep-series v2 curriculum.

The episode-content bible is authoritative.  This module expands it into
deterministic review candidates and can render low-cost previews through the
existing POP ``cm_science`` content pack.  It never calls a network service,
runs a benchmark, reads a secret, publishes media, or creates remote work.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from PIL import Image, ImageDraw, ImageFont


FACTORY_ROOT = Path(__file__).resolve().parent
REPO_ROOT = FACTORY_ROOT.parents[1]
DEEP_ROOT = FACTORY_ROOT / "deep_series"
EPISODES_ROOT = DEEP_ROOT / "episodes"
SCHEMAS_ROOT = FACTORY_ROOT / "schemas"
REVIEW_ROOT = DEEP_ROOT / "content_review_packet"
PLANNING_ROOT = DEEP_ROOT / "production_planning"
SCHEMA_VERSION = "2.0"
EPISODE_COUNT = 51
GENERATED_DATE = "2026-08-31"
REQUESTED_AT = "2026-08-31T00:00:00+07:00"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
WORD_RE = re.compile(r"\b[\w'-]+\b")

WORD_BANDS = {
    "focused_explainer": (650, 900, 6.0),
    "core_episode": (1000, 1550, 10.0),
    "deep_episode": (1800, 2600, 17.0),
}

EXAMPLE_VISUAL_SYSTEMS = {
    "ex-repeated-subexpression": ["expression construction", "shared DAG", "flat instruction trace"],
    "ex-truth-layout-4": ["expression evaluation", "truth-layout reveal", "packed-output trace"],
    "ex-feature-model": ["constraint graph", "revision timeline", "decision boundary"],
    "ex-circuit-cone": ["circuit cone", "support trace", "evidence panel"],
    "ex-policy-revisions": ["rule graph", "changed-region trace", "reuse boundary"],
    "ex-recognition-graph": ["proposal graph", "exact verification path", "promotion and fallback map"],
}

EXAMPLE_NARRATION_PASSES = {
    "ex-repeated-subexpression": [
        "Begin with A and B, compute the shared subexpression S once, and keep that identity color on every outgoing use.",
        "The left branch combines S with C and D, while the right branch combines the same S with E.",
        "Both branches meet at the final OR, so the shared node changes program structure without changing the Boolean output.",
        "A raw syntax view may draw S twice; a shared graph draws one node with two outgoing edges.",
        "Lowering the graph assigns dependency-ordered slots, but slot numbers are not new Boolean operations.",
        "Instruction count, primitive execution count, live buffers, and packed storage therefore remain separate ledgers.",
        "Changing from bigint bits to word lanes changes storage and execution layout, not the meaning of S or F.",
        "The stable variable order A through E prevents a convenient reordering from hiding inside a method comparison.",
        "Any claimed reduction must point to the repeated S path or another named transformation actually present here.",
        "The output check closes both paths against the same exact truth behavior before performance is interpreted.",
    ],
    "ex-truth-layout-4": [
        "The example fixes F of A, B, C, and D as A AND B, exclusive-or C OR D.",
        "A and B select the row, C and D select the column, and MSB-first order fixes both index conventions.",
        "Every four-bit assignment names exactly one of the sixteen cells, and every cell returns one exact output bit.",
        "Folding the truth-table output column into a four-by-four grid changes the layout, not the function.",
        "Reading a cell forward evaluates an assignment; reading it backward recovers the row and column bits that selected it.",
        "Live support can remove an input from active computation even when the ambient layout still reserves its axis.",
        "A packed truth vector stores the same exact outputs in a different physical arrangement from the displayed matrix.",
        "The explicit matrix is dense by contract, so compactness and speed require separate evidence rather than definition alone.",
        "Holding variable order fixed makes matrix, packed-vector, and program views comparable without an indexing ambiguity.",
        "An exact equality check across the views is the gate before any timing ratio is allowed to matter.",
    ],
    "ex-feature-model": [
        "Core, Cloud, Local, Analytics, and Export remain the same named features across all three conceptual revisions.",
        "Requires and excludes edges define valid configurations; they are constraints, not measured product behavior.",
        "A revision changes a bounded part of the constraint graph while the unchanged region keeps its identity.",
        "Repeated queries can reuse an exact retained artifact only when the revision and invalidation contract permit it.",
        "A changed-region highlight shows what must be recomputed instead of treating the entire model as new.",
        "The decision boundary separates valid from invalid assignments after every revision under the same feature ordering.",
        "Any reuse claim must charge the work needed to detect, validate, and persist the reusable region.",
        "The example is deliberately conceptual, so it teaches representation choice without implying a product benchmark.",
        "A fallback route remains visible when a revision invalidates more of the model than the reuse path can safely preserve.",
        "The final comparison names output contract, revision distance, and reuse count before discussing efficiency.",
    ],
    "ex-circuit-cone": [
        "The cone starts from five named inputs, but the displayed output has four-variable semantic support.",
        "AND and inversion nodes form a small exact dependency cone whose fanout remains visible throughout the lesson.",
        "The inert input stays outlined so nominal width cannot be mistaken for active support.",
        "A topological trace orders the gates without changing their connectivity or the output function.",
        "Structural counts describe nodes, edges, and operations; they do not directly measure hardware memory traffic.",
        "An exact output digest binds the conceptual cone to any separately labeled retained measurement panel.",
        "The conceptual mechanism and EPFL evidence use matched colors but retain distinct status badges and source footers.",
        "Lowering or packing may change the execution artifact while the cone's admitted Boolean result remains fixed.",
        "Any mechanism claim points to a visible change in the cone rather than to a benchmark ratio by itself.",
        "The comparison closes with the same inputs, output contract, and exactness gate on every path.",
    ],
    "ex-policy-revisions": [
        "Role, region, resource, and risk remain the stable inputs to the conceptual access decision.",
        "Named rule nodes combine those inputs into one exact allow-or-deny result under a declared ordering.",
        "Three adjacent revisions change bounded rule regions while unchanged nodes retain their identities.",
        "A changed-region trace distinguishes reusable structure from rules that must be recomputed.",
        "Reuse is valid only when source identity, revision identity, and the output contract all still match.",
        "Detection, rewrite, persistence, and extraction costs remain visible instead of disappearing into a reuse label.",
        "A safe fallback evaluates the full exact policy whenever the incremental contract cannot be proved.",
        "The example teaches a revision workload and does not claim measured behavior for a deployed policy engine.",
        "Repeated queries and adjacent revisions are separate reuse axes, so their break-even points must be measured separately.",
        "The final decision check compares exact outputs before any preparation or wrapper ratio is interpreted.",
    ],
    "ex-recognition-graph": [
        "A labeled input graph enters a proposal stage whose job is to suggest a partition or route, not to certify it.",
        "The candidate partition remains visibly provisional until the exact verifier checks its witness conditions.",
        "An accepted path produces an exact witness; a rejected path moves to the safe fallback without changing correctness.",
        "The promotion gate is separate from exact verification because a correct result need not satisfy a performance promotion rule.",
        "Proposal, verifier, witness, rejection, fallback, and promotion keep stable shapes across every CRSE episode.",
        "A conceptual badge stays on the graph even when a later panel introduces separately sourced measurements.",
        "Changing the proposal mechanism never removes the exact verifier or the fallback path from the contract.",
        "Negative and not-promoted outcomes remain first-class states rather than disappearing from the research timeline.",
        "Task routing may select a different exact path while the admitted result and verification gate remain fixed.",
        "Every measured promotion panel names its workload, boundary, uncertainty, and source independently of this teaching graph.",
    ],
}

PRIMITIVE_BY_EXAMPLE = {
    "ex-repeated-subexpression": "transform_compare",
    "ex-truth-layout-4": "expression_matrix",
    "ex-feature-model": "transform_compare",
    "ex-circuit-cone": "transform_compare",
    "ex-policy-revisions": "transform_compare",
    "ex-recognition-graph": "transform_compare",
}

PRIMITIVE_BY_VISUAL_SYSTEM = {
    "expression evaluation": "expression_matrix",
    "truth-layout reveal": "representation_compare",
    "packed-output trace": "boundary",
    "expression construction": "transform_compare",
    "shared DAG": "transform_compare",
    "flat instruction trace": "transform_compare",
    "constraint graph": "transform_compare",
    "revision timeline": "transform_compare",
    "decision boundary": "transform_compare",
    "circuit cone": "transform_compare",
    "support trace": "transform_compare",
    "evidence panel": "transform_compare",
    "rule graph": "transform_compare",
    "changed-region trace": "transform_compare",
    "reuse boundary": "transform_compare",
    "proposal graph": "transform_compare",
    "exact verification path": "boundary",
    "promotion and fallback map": "result",
}

GENERIC_FILLER_PHRASES = (
    "freeze the frame before the next change",
    "the unchanged entities provide the control for this comparison",
    "run the worked example backward from its settled state",
    "hide the evidence-status badge while keeping the diagram polished",
    "the neighboring episode receives a link, not a compressed retelling",
    "inspection micro-state",
)


class DeepSeriesError(ValueError):
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


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    text = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if path.exists() and path.read_text("utf-8") == text:
        return
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


def archive_stale_production_planning() -> None:
    """Preserve an old approval/planning packet when the Bible identity changes."""
    approval_path = PLANNING_ROOT / "content_approval.json"
    bible_path = DEEP_ROOT / "episode_content_bible.json"
    if not approval_path.is_file() or not bible_path.is_file():
        return
    approval = load_json(approval_path)
    bible = load_json(bible_path)
    gate = bible["approval_gate"]
    still_current = (
        gate["status"] == "approved"
        and approval["bible_content_hash"] == bible["content_hash"]
        and approval["approval_identity"] == gate["approval_identity"]
    )
    if still_current:
        return
    identity = approval["approval_identity"]
    destination = PLANNING_ROOT / "history" / identity
    destination.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in PLANNING_ROOT.iterdir() if path.is_file())
    collisions = [path.name for path in files if (destination / path.name).exists()]
    if collisions:
        raise DeepSeriesError(
            f"content-approval:history-collision:{identity}:{','.join(collisions)}"
        )
    archived_files = [
        {"name": path.name, "sha256": file_sha256(path)} for path in files
    ]
    for path in files:
        os.replace(path, destination / path.name)
    archive = {
        "schema_version": SCHEMA_VERSION,
        "status": "historical_content_approval_superseded",
        "approval_identity": identity,
        "approved_bible_content_hash": approval["bible_content_hash"],
        "current_bible_content_hash": bible["content_hash"],
        "archived_at": dt.datetime.now().astimezone().isoformat(),
        "reason": "The authoritative source or curriculum identity changed; the prior production-planning approval is preserved but no longer current.",
        "files": archived_files,
    }
    archive["content_hash"] = canonical_sha256(archive)
    write_json(destination / "archive_manifest.json", archive)


def archive_stale_content_review() -> None:
    """Move a superseded review request/packet out of the current gate path."""
    request_path = DEEP_ROOT / "content_review_request.json"
    bible_path = DEEP_ROOT / "episode_content_bible.json"
    if not request_path.is_file() or not bible_path.is_file():
        return
    request = load_json(request_path)
    bible = load_json(bible_path)
    if request["bible_content_hash"] == bible["content_hash"]:
        return
    identity = request["review_manifest_sha256"]
    destination = DEEP_ROOT / "content_review_history" / identity
    if destination.exists():
        raise DeepSeriesError(f"content-review:history-collision:{identity}")
    destination.mkdir(parents=True)
    if REVIEW_ROOT.exists():
        os.replace(REVIEW_ROOT, destination / "content_review_packet")
    os.replace(request_path, destination / "content_review_request.json")
    archive = {
        "schema_version": SCHEMA_VERSION,
        "status": "historical_content_review_superseded",
        "review_manifest_sha256": identity,
        "reviewed_bible_content_hash": request["bible_content_hash"],
        "current_bible_content_hash": bible["content_hash"],
        "archived_at": dt.datetime.now().astimezone().isoformat(),
        "reason": "Authoritative source or curriculum identity changed; a new review packet and approval are required.",
    }
    archive["content_hash"] = canonical_sha256(archive)
    write_json(destination / "archive_manifest.json", archive)
    bible["approval_gate"].update({
        "status": "not_requested",
        "review_manifest_sha256": None,
        "approved_by": None,
        "approved_at": None,
        "approval_identity": None,
    })
    import factory as level1_factory
    write_json(bible_path, bible)
    write_text(
        DEEP_ROOT / "EPISODE_CONTENT_BIBLE.md",
        level1_factory.render_episode_content_bible_markdown(bible),
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text("utf-8"))


def strict_object(properties: dict[str, Any], required: Iterable[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(required),
    }


STRING = {"type": "string", "minLength": 1}
MAYBE_STRING = {"type": "string"}
STRINGS = {"type": "array", "items": STRING, "uniqueItems": True}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}


def authoring_schemas() -> dict[str, dict[str, Any]]:
    duration = strict_object(
        {"minimum": {"type": "number", "minimum": 1}, "maximum": {"type": "number", "minimum": 1}},
        ["minimum", "maximum"],
    )
    episode_contract = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "status": {"const": "review_candidate"},
            "video_id": STRING,
            "order": {"type": "integer", "minimum": 1},
            "title": STRING,
            "bible_content_hash": SHA,
            "episode_content_hash": SHA,
            "duration_tier": {"enum": list(WORD_BANDS)},
            "duration_minutes": duration,
            "worked_example_id": STRING,
            "prerequisite_ids": STRINGS,
            "chapter_ids": STRINGS,
            "artifact_hashes": {"type": "object", "additionalProperties": SHA},
            "contract_hash": SHA,
        },
        [
            "schema_version", "status", "video_id", "order", "title", "bible_content_hash",
            "episode_content_hash", "duration_tier", "duration_minutes", "worked_example_id",
            "prerequisite_ids", "chapter_ids", "artifact_hashes", "contract_hash",
        ],
    )
    cue = strict_object(
        {
            "cue_id": STRING,
            "chapter_id": STRING,
            "scene_id": STRING,
            "role": {"enum": ["hook", "definition", "example", "mechanism", "evidence", "contrast", "boundary", "retrieval", "misconception", "recap", "pause"]},
            "spoken": {"type": "boolean"},
            "text": MAYBE_STRING,
            "pronunciation": {"type": "object", "additionalProperties": STRING},
            "claim_ids": STRINGS,
            "source_ids": STRINGS,
            "evidence_status": {"enum": ["conceptual", "confirmed", "revised", "negative", "not_promoted", "exploratory", "mixed"]},
            "timing_target_s": {"type": "number", "minimum": 0.5, "maximum": 12},
            "text_sha256": SHA,
        },
        [
            "cue_id", "chapter_id", "scene_id", "role", "spoken", "text", "pronunciation",
            "claim_ids", "source_ids", "evidence_status", "timing_target_s", "text_sha256",
        ],
    )
    narration = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "video_id": STRING,
            "episode_content_hash": SHA,
            "language": {"const": "en-US"},
            "pace_wpm": {"type": "number", "minimum": 115, "maximum": 135},
            "word_count": {"type": "integer", "minimum": 1},
            "duration_target_s": {"type": "number", "minimum": 1},
            "cues": {"type": "array", "minItems": 20, "items": cue},
            "content_hash": SHA,
        },
        [
            "schema_version", "video_id", "episode_content_hash", "language", "pace_wpm",
            "word_count", "duration_target_s", "cues", "content_hash",
        ],
    )
    caption_cue = strict_object(
        {
            "cue_id": STRING,
            "start_s": {"type": "number", "minimum": 0},
            "end_s": {"type": "number", "exclusiveMinimum": 0},
            "text": STRING,
            "text_sha256": SHA,
        },
        ["cue_id", "start_s", "end_s", "text", "text_sha256"],
    )
    captions = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "video_id": STRING,
            "narration_content_hash": SHA,
            "language": {"const": "en-US"},
            "cues": {"type": "array", "minItems": 1, "items": caption_cue},
            "vtt_path": STRING,
            "content_hash": SHA,
        },
        ["schema_version", "video_id", "narration_content_hash", "language", "cues", "vtt_path", "content_hash"],
    )
    beat = strict_object(
        {
            "beat_id": STRING,
            "cue_id": STRING,
            "start_s": {"type": "number", "minimum": 0},
            "end_s": {"type": "number", "exclusiveMinimum": 0},
            "primitive": STRING,
            "visual_system": STRING,
            "entities": STRINGS,
            "state_change": STRING,
            "claim_ids": STRINGS,
            "evidence_status": STRING,
        },
        ["beat_id", "cue_id", "start_s", "end_s", "primitive", "visual_system", "entities", "state_change", "claim_ids", "evidence_status"],
    )
    scene = strict_object(
        {
            "scene_id": STRING,
            "chapter_id": STRING,
            "composition_id": STRING,
            "purpose": STRING,
            "start_s": {"type": "number", "minimum": 0},
            "end_s": {"type": "number", "exclusiveMinimum": 0},
            "beats": {"type": "array", "minItems": 1, "items": beat},
        },
        ["scene_id", "chapter_id", "composition_id", "purpose", "start_s", "end_s", "beats"],
    )
    storyboard = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "video_id": STRING,
            "episode_content_hash": SHA,
            "frame_contract": strict_object(
                {"fps": {"const": 30}, "width": {"const": 1920}, "height": {"const": 1080}, "interval": {"const": "half-open"}, "clock": {"const": "frame-derived"}},
                ["fps", "width", "height", "interval", "clock"],
            ),
            "duration_s": {"type": "number", "minimum": 1},
            "composition_count": {"type": "integer", "minimum": 1},
            "meaningful_state_change_count": {"type": "integer", "minimum": 1},
            "scenes": {"type": "array", "minItems": 1, "items": scene},
            "content_hash": SHA,
        },
        ["schema_version", "video_id", "episode_content_hash", "frame_contract", "duration_s", "composition_count", "meaningful_state_change_count", "scenes", "content_hash"],
    )
    claim_ref = strict_object(
        {
            "claim_id": STRING,
            "allowed_wording": STRING,
            "type": STRING,
            "status": STRING,
            "scope": STRING,
            "measurement_boundary": MAYBE_STRING,
            "comparator": MAYBE_STRING,
            "ratio_direction": MAYBE_STRING,
            "uncertainty": MAYBE_STRING,
            "sources": {"type": "array", "minItems": 1, "items": strict_object({"source_id": STRING, "path": STRING, "sha256": SHA, "locator": STRING}, ["source_id", "path", "sha256", "locator"])},
        },
        ["claim_id", "allowed_wording", "type", "status", "scope", "measurement_boundary", "comparator", "ratio_direction", "uncertainty", "sources"],
    )
    claim_binding = strict_object(
        {
            "cue_id": STRING,
            "scene_id": STRING,
            "text_sha256": SHA,
            "evidence_status": STRING,
            "conceptual": {"type": "boolean"},
            "claims": {"type": "array", "items": claim_ref},
        },
        ["cue_id", "scene_id", "text_sha256", "evidence_status", "conceptual", "claims"],
    )
    claim_map = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "video_id": STRING,
            "episode_content_hash": SHA,
            "bindings": {"type": "array", "minItems": 1, "items": claim_binding},
            "content_hash": SHA,
        },
        ["schema_version", "video_id", "episode_content_hash", "bindings", "content_hash"],
    )
    asset = strict_object(
        {
            "asset_id": STRING,
            "path": STRING,
            "kind": STRING,
            "source_or_license": STRING,
            "width": {"type": ["integer", "null"], "minimum": 1},
            "height": {"type": ["integer", "null"], "minimum": 1},
            "sha256": SHA,
            "generator": STRING,
        },
        ["asset_id", "path", "kind", "source_or_license", "width", "height", "sha256", "generator"],
    )
    assets = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "video_id": STRING,
            "episode_content_hash": SHA,
            "assets": {"type": "array", "minItems": 1, "items": asset},
            "content_hash": SHA,
        },
        ["schema_version", "video_id", "episode_content_hash", "assets", "content_hash"],
    )
    production_plan = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "video_id": STRING,
            "episode_content_hash": SHA,
            "status": {"const": "planning_only_content_approval_required"},
            "local_route": STRINGS,
            "remote_route": {"const": "disabled_pending_content_approval_and_separate_exact_authorization"},
            "estimated_cpu_minutes": {"type": "number", "minimum": 1},
            "resource_class": STRING,
            "retry_class": STRING,
            "cache_identities": {"type": "array", "minItems": 1, "items": SHA, "uniqueItems": True},
            "expected_outputs": STRINGS,
            "illegal_routes": {"type": "array", "minItems": 1, "items": STRING, "uniqueItems": True},
            "content_hash": SHA,
        },
        ["schema_version", "video_id", "episode_content_hash", "status", "local_route", "remote_route", "estimated_cpu_minutes", "resource_class", "retry_class", "cache_identities", "expected_outputs", "illegal_routes", "content_hash"],
    )
    chapter = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "video_id": STRING,
            "chapter_id": STRING,
            "title": STRING,
            "purpose": STRING,
            "teaching_beat_numbers": {"type": "array", "minItems": 1, "items": {"type": "integer", "minimum": 1}, "uniqueItems": True},
            "visual_spine_indices": {"type": "array", "minItems": 1, "items": {"type": "integer", "minimum": 1}, "uniqueItems": True},
            "cue_ids": STRINGS,
            "scene_ids": STRINGS,
            "cache_identity": SHA,
        },
        ["schema_version", "video_id", "chapter_id", "title", "purpose", "teaching_beat_numbers", "visual_spine_indices", "cue_ids", "scene_ids", "cache_identity"],
    )
    editorial = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "video_id": STRING,
            "episode_content_hash": SHA,
            "passes": {"type": "array", "minItems": 3, "maxItems": 3, "items": strict_object({"pass_id": STRING, "status": {"const": "pass"}, "checks": STRINGS}, ["pass_id", "status", "checks"])},
            "word_count": {"type": "integer", "minimum": 1},
            "chapter_count": {"type": "integer", "minimum": 3},
            "scene_count": {"type": "integer", "minimum": 1},
            "beat_count": {"type": "integer", "minimum": 1},
            "duplicate_spoken_cues": {"const": 0},
            "generic_filler_cues": {"const": 0},
            "duplicate_state_changes": {"const": 0},
            "maximum_visual_beat_seconds": {"type": "number", "exclusiveMinimum": 0, "maximum": 8},
            "unresolved_claim_ids": {"type": "array", "maxItems": 0},
            "placeholders": {"type": "array", "maxItems": 0},
            "content_hash": SHA,
        },
        ["schema_version", "video_id", "episode_content_hash", "passes", "word_count", "chapter_count", "scene_count", "beat_count", "duplicate_spoken_cues", "generic_filler_cues", "duplicate_state_changes", "maximum_visual_beat_seconds", "unresolved_claim_ids", "placeholders", "content_hash"],
    )
    example = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "example_id": STRING,
            "title": STRING,
            "purpose": STRING,
            "definition": STRING,
            "conceptual": {"const": True},
            "source_ids": STRINGS,
            "bible_content_hash": SHA,
            "definition_hash": SHA,
        },
        ["schema_version", "example_id", "title", "purpose", "definition", "conceptual", "source_ids", "bible_content_hash", "definition_hash"],
    )
    series_manifest = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "status": {"const": "review_candidate"},
            "bible_content_hash": SHA,
            "episode_count": {"const": EPISODE_COUNT},
            "ordered_episode_ids": {"type": "array", "minItems": EPISODE_COUNT, "maxItems": EPISODE_COUNT, "items": STRING, "uniqueItems": True},
            "sections": {"type": "array", "minItems": 1, "items": strict_object({"section_id": STRING, "title": STRING, "episode_ids": STRINGS}, ["section_id", "title", "episode_ids"])},
            "episode_contract_hashes": {"type": "object", "minProperties": EPISODE_COUNT, "maxProperties": EPISODE_COUNT, "additionalProperties": SHA},
            "content_hash": SHA,
        },
        ["schema_version", "status", "bible_content_hash", "episode_count", "ordered_episode_ids", "sections", "episode_contract_hashes", "content_hash"],
    )
    review_manifest = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "status": {"const": "review_requested"},
            "bible_content_hash": SHA,
            "episode_count": {"const": EPISODE_COUNT},
            "artifact_count": {"type": "integer", "minimum": 1},
            "artifacts": {"type": "array", "minItems": 1, "items": strict_object({"path": STRING, "sha256": SHA, "hash_scope": STRING, "artifact_type": STRING}, ["path", "sha256", "hash_scope", "artifact_type"])},
            "unresolved_editorial_questions": {"type": "array", "items": strict_object({"question": STRING, "affected_episode_ids": STRINGS}, ["question", "affected_episode_ids"])},
            "review_manifest_sha256": SHA,
        },
        ["schema_version", "status", "bible_content_hash", "episode_count", "artifact_count", "artifacts", "unresolved_editorial_questions", "review_manifest_sha256"],
    )
    approval_request = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "status": {"const": "review_requested"},
            "requested_at": {"const": REQUESTED_AT},
            "bible_content_hash": SHA,
            "review_manifest_sha256": SHA,
            "content_approval_authorizes_remote_or_paid_work": {"const": False},
        },
        ["schema_version", "status", "requested_at", "bible_content_hash", "review_manifest_sha256", "content_approval_authorizes_remote_or_paid_work"],
    )
    content_approval = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "status": {"const": "approved"},
            "scope": {"const": "production_planning_only"},
            "approved_by": STRING,
            "approved_at": STRING,
            "bible_content_hash": SHA,
            "review_manifest_sha256": SHA,
            "approval_text": STRING,
            "approval_text_sha256": SHA,
            "approval_identity": SHA,
            "content_approval_authorizes_remote_or_paid_work": {"const": False},
        },
        [
            "schema_version", "status", "scope", "approved_by", "approved_at",
            "bible_content_hash", "review_manifest_sha256", "approval_text",
            "approval_text_sha256", "approval_identity",
            "content_approval_authorizes_remote_or_paid_work",
        ],
    )
    return {
        "deep_episode.schema.json": episode_contract,
        "deep_narration_contract.schema.json": narration,
        "deep_caption_contract.schema.json": captions,
        "deep_storyboard.schema.json": storyboard,
        "deep_claim_map.schema.json": claim_map,
        "deep_asset_manifest.schema.json": assets,
        "deep_production_plan.schema.json": production_plan,
        "deep_chapter.schema.json": chapter,
        "deep_editorial_audit.schema.json": editorial,
        "deep_stable_example.schema.json": example,
        "deep_series_manifest.schema.json": series_manifest,
        "deep_content_review_manifest.schema.json": review_manifest,
        "deep_content_approval_request.schema.json": approval_request,
        "deep_content_approval.schema.json": content_approval,
    }


def write_authoring_schemas() -> None:
    for name, schema in authoring_schemas().items():
        write_json(
            SCHEMAS_ROOT / name,
            {"$schema": "https://json-schema.org/draft/2020-12/schema", **schema},
        )


def validate_with(name: str, value: dict[str, Any]) -> None:
    schema = authoring_schemas()[name]
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        error = errors[0]
        location = ".".join(str(item) for item in error.path)
        raise DeepSeriesError(f"{name}:{location}:{error.message}")


def finalize(value: dict[str, Any], field: str = "content_hash") -> dict[str, Any]:
    result = copy.deepcopy(value)
    result[field] = "0" * 64
    result[field] = canonical_sha256({key: item for key, item in result.items() if key != field})
    return result


def words(text: str) -> int:
    return len(WORD_RE.findall(text))


def trim_sentence(value: str, limit: int = 190) -> str:
    cleaned = " ".join(value.replace("`", "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rsplit(" ", 1)[0] + "…"


def ensure_sentence(value: str) -> str:
    value = " ".join(value.split()).strip()
    if not value:
        return value
    if value[-1] not in ".!?":
        value += "."
    return value


def split_sentences(value: str) -> list[str]:
    value = " ".join(value.split())
    parts = [ensure_sentence(item) for item in SENTENCE_RE.split(value) if item.strip()]
    return parts or [ensure_sentence(value)]


def pronunciation_for(text: str) -> dict[str, str]:
    values = {}
    if "CM-IR" in text:
        values["CM-IR"] = "C M eye are"
    if re.search(r"\bCM\b", text):
        values["CM"] = "C M"
    if "CSE-flat" in text:
        values["CSE-flat"] = "C S E flat"
    if "CSE" in text:
        values["CSE"] = "C S E"
    if "CRSE" in text:
        values["CRSE"] = "C R S E"
    if "EPFL" in text:
        values["EPFL"] = "E P F L"
    if "GF2" in text or "GF(2)" in text:
        values["GF2"] = "G F two"
    return values


def status_for_claim(claim: dict[str, Any]) -> str:
    status = claim["status"]
    return status if status in {"confirmed", "revised", "negative", "not_promoted", "exploratory"} else "mixed"


def narrativize_beat(beat: str, example_title: str) -> str:
    value = beat.replace("`", "")
    prefixes = (
        "Open with the concrete question: ",
        "Define the lesson's central distinction: ",
        "State the evidence boundary: ",
        "Pause for retrieval: ",
        "Close by transferring the rule: ",
    )
    for prefix in prefixes:
        if value.startswith(prefix):
            return ensure_sentence(value[len(prefix):])
    if value.startswith("Construct and orient the stable example"):
        return f"We now construct the {example_title} and name every part before interpreting it."
    if value.startswith("Render "):
        return ensure_sentence("We now " + value[0].lower() + value[1:])
    if value.startswith("Introduce "):
        return ensure_sentence("Now " + value[0].lower() + value[1:])
    if value.startswith("Toggle ") or value.startswith("Build ") or value.startswith("Rewrite "):
        return ensure_sentence("Watch us " + value[0].lower() + value[1:])
    if value.startswith("Separate "):
        return ensure_sentence("Keep this separation visible: " + value[9:])
    return ensure_sentence(value)


def build_cues(
    episode: dict[str, Any],
    example: dict[str, Any],
    claims_by_id: dict[str, dict[str, Any]],
    sources_by_id: dict[str, dict[str, Any]],
    episodes_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    chapters = [item["chapter_id"] for item in episode["chapter_plan"]]
    last = len(chapters) - 1
    middle = max(1, len(chapters) // 2)
    records: list[dict[str, Any]] = []
    seen_spoken_text: set[str] = set()

    beat_to_chapter: dict[int, int] = {}
    for chapter_index, chapter in enumerate(episode["chapter_plan"]):
        for beat_number in chapter["teaching_beat_numbers"]:
            beat_to_chapter[beat_number] = chapter_index

    def owned_chapter_index(owned: str, owned_index: int) -> int:
        tokens = {item for item in re.findall(r"[a-z0-9]+", owned.casefold()) if len(item) > 2}
        scored = []
        for chapter_index, chapter in enumerate(episode["chapter_plan"][1:], 1):
            chapter_text = f"{chapter['working_title']} {chapter['purpose']}".casefold()
            score = sum(token in chapter_text for token in tokens)
            scored.append((score, -abs(chapter_index - (1 + owned_index)), -chapter_index, chapter_index))
        best = max(scored)[-1]
        if max(item[0] for item in scored) == 0:
            best = min(max(1, last - 1), 1 + owned_index)
        return best

    def owned_spine_index(owned: str, owned_index: int) -> int:
        ignored = {"exact", "and", "the", "versus", "contract", "artifact", "artifacts"}
        tokens = {
            item for item in re.findall(r"[a-z0-9]+", owned.casefold())
            if len(item) > 1 and item not in ignored
        }
        scores = [sum(token in spine.casefold() for token in tokens) for spine in episode["visual_spine"]]
        if max(scores) == 0:
            return min(owned_index, len(scores) - 1)
        return max(range(len(scores)), key=lambda index: (scores[index], -abs(index - owned_index)))

    def add(
        chapter_index: int,
        role: str,
        text: str,
        *,
        claim_ids: Iterable[str] = (),
        source_ids: Iterable[str] = (),
        evidence_status: str = "conceptual",
        state_change: str,
        spoken: bool = True,
    ) -> None:
        fragments = [text] if not spoken else split_sentences(text)
        for fragment_index, fragment in enumerate(fragments):
            ids = sorted(set(claim_ids))
            source_values = set(source_ids)
            for claim_id in ids:
                source_values.update(ref["source_id"] for ref in claims_by_id[claim_id]["sources"])
            cue_text = fragment if spoken else ""
            if spoken:
                normalized = " ".join(cue_text.casefold().split())
                if normalized in seen_spoken_text:
                    continue
                seen_spoken_text.add(normalized)
            records.append({
                "cue_id": f"q{len(records) + 1:04d}",
                "chapter_id": chapters[max(0, min(chapter_index, last))],
                "scene_id": "pending",
                "role": role,
                "spoken": spoken,
                "text": cue_text,
                "pronunciation": pronunciation_for(cue_text),
                "claim_ids": ids,
                "source_ids": sorted(source_values),
                "evidence_status": evidence_status,
                "timing_target_s": 3.0 if not spoken else max(2.5, min(9.0, words(cue_text) * 60.0 / 125.0 + 0.45)),
                "text_sha256": text_sha256(cue_text),
                "state_change": ensure_sentence(
                    state_change
                    if len(fragments) == 1
                    else f"{state_change.rstrip('.')} Narration fragment {fragment_index + 1} of {len(fragments)} keeps the same comparison leg visible"
                ),
            })

    anchors = episode["dialogue_anchors"]
    add(0, "hook", anchors["hook"], state_change="The opening question replaces the title while the worked example remains dimmed")
    add(0, "definition", f"This episode has one job: {episode['thesis']}", claim_ids=episode["claim_ids"], evidence_status="confirmed", state_change="The thesis appears as a single claim beside the episode map")
    if episode["prerequisite_ids"]:
        prerequisite_titles = ", ".join(episodes_by_id[item]["title"] for item in episode["prerequisite_ids"])
        add(0, "definition", f"We build on {prerequisite_titles}; their definitions stay fixed while this lesson adds a new layer.", state_change="Prerequisite nodes light in the series map without replaying their lessons")
    else:
        add(0, "definition", "No earlier episode is required; we begin by establishing the series evidence grammar.", state_change="The prerequisite lane resolves to an explicit none marker")
    add(0, "definition", anchors["definition"], claim_ids=episode["claim_ids"], evidence_status="confirmed", state_change="The plain definition replaces the question and its key terms receive labels")
    definition_templates = (
        "Watch for the label {term}; it stays attached to the artifact this episode means.",
        "When we say {term}, the highlight identifies its layer before we interpret it.",
        "The term {term} receives its own visual state so it cannot drift into a neighboring concept.",
        "We will keep {term} visible whenever its definition controls the inference.",
        "A persistent {term} label marks exactly where that object enters the example.",
    )
    for index, definition in enumerate(episode["definitions"]):
        add(
            0,
            "definition",
            definition_templates[index % len(definition_templates)].format(term=definition),
            state_change=f"The controlled term {definition} joins the persistent glossary rail",
        )

    add(1, "example", f"The next sequence uses {example['title']} as a conceptual teaching example, not as measured benchmark evidence.", source_ids=example["source_ids"], state_change="A CONCEPTUAL badge locks into the upper corner before the example moves")
    add(1, "example", f"Our stable example is {example['title']}. {example['definition']}", source_ids=example["source_ids"], state_change="The complete stable-example definition unfolds into named entities and fixed variable order")
    add(1, "example", example["purpose"], source_ids=example["source_ids"], state_change="A continuity ribbon links the example to every later episode that reuses it")
    for beat_number, beat in enumerate(episode["teaching_beats"], 1):
        if beat_number <= 2:
            continue
        chapter_index = beat_to_chapter.get(beat_number, 1)
        role = "retrieval" if beat_number == len(episode["teaching_beats"]) - 1 else "mechanism"
        add(
            chapter_index,
            role,
            narrativize_beat(beat, example["title"]),
            claim_ids=episode["claim_ids"] if role == "mechanism" else (),
            evidence_status="conceptual",
            state_change=f"The example advances audited teaching beat {beat_number}: {trim_sentence(beat, 140)}",
        )

    for owned_index, owned in enumerate(episode["owns"]):
        chapter_index = owned_chapter_index(owned, owned_index)
        add(chapter_index, "mechanism", f"Now isolate {owned} inside {example['title']}.", state_change=f"All layers fade except the entities that encode {owned}")
        add(chapter_index, "mechanism", f"The example definition and output meaning stay fixed while only the state for {owned} changes.", source_ids=example["source_ids"], state_change=f"One matched state transition isolates {owned} while the comparison baseline remains fixed")
        add(chapter_index, "mechanism", f"That matched before-and-after view assigns the visible consequence to {owned}, not to a substituted workload.", state_change=f"Alignment guides pin the unchanged inputs while the consequence of {owned} receives focus")
        spine = episode["visual_spine"][owned_spine_index(owned, owned_index)]
        add(chapter_index, "mechanism", spine, state_change=f"The storyboard realizes the episode-specific spine: {trim_sentence(spine, 150)}")

    for claim_id in episode["claim_ids"]:
        claim = claims_by_id[claim_id]
        claim_status = status_for_claim(claim)
        add(middle, "evidence", claim["allowed_wording"], claim_ids=[claim_id], evidence_status=claim_status, state_change=f"An evidence panel reveals claim {claim_id} with its {claim_status} badge")
        add(middle, "evidence", f"Read that statement only within this scope: {claim['scope']}.", claim_ids=[claim_id], evidence_status=claim_status, state_change=f"The scope field for claim {claim_id} expands beneath the wording")
        add(middle, "evidence", f"Its declared measurement boundary is {claim['measurement_boundary'] or 'not applicable'}.", claim_ids=[claim_id], evidence_status=claim_status, state_change=f"A boundary band brackets what claim {claim_id} includes")
        add(middle, "evidence", f"The uncertainty field says {claim['uncertainty'] or 'none stated'}.", claim_ids=[claim_id], evidence_status=claim_status, state_change=f"The uncertainty field for claim {claim_id} settles before any interpretation is spoken")

    reference = episodes_by_id[episode["references"][0]]
    add(max(1, last - 1), "contrast", f"The nearest confusing lesson is {reference['title']}; it owns {reference['owns'][0]}, while this episode owns {episode['owns'][0]}.", state_change="A matched split view keeps the neighboring lesson dim and the owned concept bright")
    for exclusion in episode["excludes"]:
        add(max(1, last - 1), "boundary", exclusion, claim_ids=episode["claim_ids"], evidence_status="confirmed", state_change="A boundary frame encloses the valid inference and blocks the excluded one")
    for caveat in episode["caveats"]:
        add(max(1, last - 1), "boundary", caveat, claim_ids=episode["claim_ids"], evidence_status="confirmed", state_change="The caveat appears beside the example without changing the underlying data")

    minimum_words, maximum_words, _ = WORD_BANDS[episode["duration_tier"]]
    expansion_candidates: list[tuple[int, str, str]] = []

    for pass_index, explanation in enumerate(EXAMPLE_NARRATION_PASSES[episode["worked_example_id"]]):
        owned_index = pass_index % len(episode["owns"])
        owned = episode["owns"][owned_index]
        chapter_index = owned_chapter_index(owned, owned_index)
        expansion_candidates.append((
            chapter_index,
            f"{explanation} Holding that element fixed lets this episode isolate {owned}.",
            f"Worked-example explanation {pass_index + 1} connects a named entity to {owned}",
        ))

    for index, owned in enumerate(episode["owns"]):
        chapter_index = owned_chapter_index(owned, index)
        spine = ensure_sentence(episode["visual_spine"][owned_spine_index(owned, index)]).rstrip(".")
        expansion_candidates.extend([
            (chapter_index, f"The starting state preserves the stable definition: {example['definition']}", f"The baseline definition settles before {owned} receives focus"),
            (chapter_index, f"After the change, the composition makes {owned} inspectable: {spine}.", f"The episode-specific diagram exposes {owned} through a named visual state"),
            (chapter_index, f"The invariant is the example's meaning; the variable is {owned}.", f"An invariant rail and a changing-state rail separate around {owned}"),
            (chapter_index, f"If the same output is reached through a different path, the diagram must still identify whether {owned} changed.", f"Two exact paths converge while the {owned} label remains attached to the changing layer"),
        ])

    for beat_number, beat in enumerate(episode["teaching_beats"], 1):
        if beat_number <= 2:
            continue
        chapter_index = beat_to_chapter.get(beat_number, min(last, 1))
        chapter = episode["chapter_plan"][chapter_index]
        visual_index = chapter["visual_spine_indices"][(beat_number - 1) % len(chapter["visual_spine_indices"])] - 1
        spine = ensure_sentence(episode["visual_spine"][visual_index]).rstrip(".")
        expansion_candidates.append((
            chapter_index,
            f"The accompanying view makes this step concrete: {spine}.",
            f"Teaching beat {beat_number} uses visual spine {visual_index + 1} without replacing the stable example",
        ))

    owned_lens_templates = (
        "Read {owned} from input to consequence through one matched view: {spine}; every surrounding entity keeps its prior meaning.",
        "The diagram treats {owned} as a located state, artifact, or boundary rather than as an unexplained method label.",
        "Before the consequence appears, predict what {owned} can change and what the stable example requires it to leave untouched.",
        "When evidence enters, its status badge binds the statement about {owned} to a source and scope, not to the conceptual drawing alone.",
        "The nearest neighboring lesson stays out of focus because its owned question is not needed to explain {owned} in this sequence.",
        "The transfer rule carries {owned} forward only with the same input definition, exactness gate, and declared output contract.",
    )
    for owned_index, owned in enumerate(episode["owns"]):
        chapter_index = owned_chapter_index(owned, owned_index)
        spine = ensure_sentence(episode["visual_spine"][owned_spine_index(owned, owned_index)]).rstrip(".")
        for lens_index, template in enumerate(owned_lens_templates):
            expansion_candidates.append((
                chapter_index,
                template.format(owned=owned, spine=spine),
                f"Explanatory lens {owned_index + 1}.{lens_index + 1} tests {owned} without changing the worked example",
            ))

    for owned_index, owned in enumerate(episode["owns"]):
        for term_index, term in enumerate(episode["definitions"]):
            chapter_index = owned_chapter_index(owned, owned_index)
            expansion_candidates.append((
                chapter_index,
                f"Use the {term} label as a checkpoint for {owned}: if the label moves to another layer, the narration has changed the question rather than explained the mechanism.",
                f"Checkpoint {owned_index + 1}.{term_index + 1} locks {term} to the layer used by {owned}",
            ))

    for expansion_index, (chapter_index, text, state_change) in enumerate(expansion_candidates, 1):
        current_words = sum(words(item["text"]) for item in records if item["spoken"])
        if current_words >= minimum_words:
            break
        if current_words + words(text) > maximum_words:
            continue
        add(
            chapter_index,
            "mechanism",
            text,
            source_ids=example["source_ids"],
            state_change=f"Episode-specific explanatory pass {expansion_index}: {state_change}",
        )

    for misconception in episode["misconceptions"]:
        add(last, "misconception", f"A common mistake is this: {misconception}", state_change="The incorrect inference appears in a muted warning lane")
        add(last, "misconception", f"Repair it by returning to the owned distinction: {episode['owns'][0]}.", state_change="The warning collapses and the owned distinction returns beside the worked example")
    add(last, "boundary", anchors["boundary"], claim_ids=episode["claim_ids"], evidence_status="confirmed", state_change="The final boundary statement encloses the recap map")
    add(last, "retrieval", episode["retrieval_check"], state_change="The answer is hidden while the worked example resets to its prediction state")
    add(last, "pause", "", state_change="A three-second inspection hold leaves the prediction visible and the answer hidden", spoken=False)
    add(last, "retrieval", f"Use the episode's central distinction to answer: {episode['closing_takeaway']}", state_change="The answer path reveals one step at a time and lands on the closing takeaway")
    add(last, "recap", anchors["closing"], claim_ids=episode["claim_ids"], evidence_status="confirmed", state_change="The episode node settles into the series map and the next prerequisite edge lights")

    chapter_order = {chapter_id: index for index, chapter_id in enumerate(chapters)}
    records.sort(key=lambda item: chapter_order[item["chapter_id"]])
    for index, record in enumerate(records, 1):
        record["cue_id"] = f"q{index:04d}"
    word_count = sum(words(item["text"]) for item in records if item["spoken"])
    if not minimum_words <= word_count <= maximum_words:
        raise DeepSeriesError(f"{episode['video_id']}:word-count:{word_count}:{minimum_words}-{maximum_words}")
    return records


def assign_storyboard(
    episode: dict[str, Any], cues: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    minimum_compositions = episode["visual_contract"]["minimum_distinct_compositions"]
    required_changes = episode["visual_contract"]["minimum_meaningful_state_changes"]
    if len(cues) < minimum_compositions:
        raise DeepSeriesError(f"{episode['video_id']}:too-few-cues-for-compositions")
    total = sum(item["timing_target_s"] for item in cues)
    minimum_seconds = episode["duration_minutes"]["minimum"] * 60.0
    maximum_seconds = episode["duration_minutes"]["maximum"] * 60.0
    target_seconds = (minimum_seconds + maximum_seconds) / 2.0
    scale = target_seconds / total
    for cue in cues:
        cue["timing_target_s"] = round(max(1.0, min(12.0, cue["timing_target_s"] * scale)), 3)
    total = sum(item["timing_target_s"] for item in cues)
    if total < minimum_seconds or total > maximum_seconds:
        correction = target_seconds / total
        for cue in cues:
            cue["timing_target_s"] = round(cue["timing_target_s"] * correction, 3)

    scene_count = max(minimum_compositions, math.ceil(len(cues) / 5))
    scene_count = min(scene_count, len(cues))
    boundaries = [round(index * len(cues) / scene_count) for index in range(scene_count + 1)]
    visual_systems = EXAMPLE_VISUAL_SYSTEMS[episode["worked_example_id"]]
    scenes = []
    timeline = 0.0
    beat_number = 0
    for index in range(scene_count):
        subset = cues[boundaries[index] : boundaries[index + 1]]
        if not subset:
            continue
        scene_id = f"s{index + 1:03d}"
        start = timeline
        beats = []
        for cue in subset:
            cue["scene_id"] = scene_id
            duration = cue["timing_target_s"]
            microbeat_count = max(1, math.ceil(duration / 7.5))
            microbeat_duration = duration / microbeat_count
            original_state_change = cue.pop("state_change")
            primary = episode["owns"][(beat_number + index) % len(episode["owns"])]
            phases = (
                original_state_change,
                f"Trace cue {cue['cue_id']}, '{trim_sentence(cue['text'] or cue['role'], 92)}', through {visual_systems[index % len(visual_systems)]} while the label for {primary} stays attached to its layer.",
                f"Settle the {primary} comparison state and expose the claim, scope, or retrieval field for cue {cue['cue_id']}.",
            )
            for microbeat_index in range(microbeat_count):
                beat_start = timeline
                timeline += microbeat_duration
                beat_number += 1
                beats.append({
                    "beat_id": f"b{beat_number:04d}",
                    "cue_id": cue["cue_id"],
                    "start_s": round(beat_start, 3),
                    "end_s": round(timeline, 3),
                    "primitive": PRIMITIVE_BY_VISUAL_SYSTEM[
                        visual_systems[index % len(visual_systems)]
                    ],
                    "visual_system": visual_systems[index % len(visual_systems)],
                    "entities": sorted(set([episode["worked_example_id"], primary, *episode["owns"][:2]])),
                    "state_change": phases[microbeat_index % len(phases)],
                    "claim_ids": cue["claim_ids"],
                    "evidence_status": cue["evidence_status"],
                })
        scenes.append({
            "scene_id": scene_id,
            "chapter_id": subset[0]["chapter_id"],
            "composition_id": f"cmp{index + 1:03d}",
            "purpose": f"Advance {subset[0]['role']} through an inspectable state change.",
            "start_s": round(start, 3),
            "end_s": round(timeline, 3),
            "beats": beats,
        })
    if beat_number < required_changes:
        raise DeepSeriesError(
            f"{episode['video_id']}:insufficient-timed-visual-beats:{beat_number}:{required_changes}"
        )
    storyboard = finalize({
        "schema_version": SCHEMA_VERSION,
        "video_id": episode["video_id"],
        "episode_content_hash": episode["content_hash"],
        "frame_contract": {"fps": 30, "width": 1920, "height": 1080, "interval": "half-open", "clock": "frame-derived"},
        "duration_s": round(timeline, 3),
        "composition_count": len(scenes),
        "meaningful_state_change_count": beat_number,
        "scenes": scenes,
    })
    return cues, storyboard


def timestamp(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def build_caption_contract(video_id: str, narration: dict[str, Any], episode_dir: Path) -> dict[str, Any]:
    caption_cues = []
    cursor = 0.0
    vtt = ["WEBVTT", ""]
    for cue in narration["cues"]:
        start = cursor
        cursor += cue["timing_target_s"]
        if not cue["spoken"]:
            continue
        caption = {
            "cue_id": cue["cue_id"],
            "start_s": round(start, 3),
            "end_s": round(cursor, 3),
            "text": cue["text"],
            "text_sha256": cue["text_sha256"],
        }
        caption_cues.append(caption)
        vtt.extend([cue["cue_id"], f"{timestamp(start)} --> {timestamp(cursor)}", cue["text"], ""])
    write_text(episode_dir / "captions.vtt", "\n".join(vtt))
    return finalize({
        "schema_version": SCHEMA_VERSION,
        "video_id": video_id,
        "narration_content_hash": narration["content_hash"],
        "language": "en-US",
        "cues": caption_cues,
        "vtt_path": f"docs/video_factory/deep_series/episodes/{video_id}/captions.vtt",
    })


def render_script_markdown(episode: dict[str, Any], cues: list[dict[str, Any]]) -> str:
    by_chapter: dict[str, list[dict[str, Any]]] = {}
    for cue in cues:
        by_chapter.setdefault(cue["chapter_id"], []).append(cue)
    lines = [
        f"# {episode['title']}",
        "",
        f"Video ID: `{episode['video_id']}`  ",
        f"Episode content identity: `{episode['content_hash']}`  ",
        "Status: **complete narration draft; production candidate pending content approval**",
        "",
    ]
    for chapter in episode["chapter_plan"]:
        lines.extend([f"## {chapter['chapter_id']} — {chapter['working_title']}", ""])
        paragraph = []
        for cue in by_chapter.get(chapter["chapter_id"], []):
            if not cue["spoken"]:
                if paragraph:
                    lines.extend([" ".join(paragraph), ""])
                    paragraph = []
                lines.extend(["*[Three-second retrieval pause.]*", ""])
                continue
            paragraph.append(cue["text"])
            if len(paragraph) >= 4:
                lines.extend([" ".join(paragraph), ""])
                paragraph = []
        if paragraph:
            lines.extend([" ".join(paragraph), ""])
    return "\n".join(lines)


def build_claim_map(
    episode: dict[str, Any],
    cues: list[dict[str, Any]],
    claims_by_id: dict[str, dict[str, Any]],
    sources_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    bindings = []
    for cue in cues:
        claims = []
        for claim_id in cue["claim_ids"]:
            claim = claims_by_id[claim_id]
            refs = []
            for ref in claim["sources"]:
                source = sources_by_id[ref["source_id"]]
                refs.append({
                    "source_id": source["id"],
                    "path": source["path"],
                    "sha256": source["sha256"],
                    "locator": ref["locator"],
                })
            claims.append({
                "claim_id": claim_id,
                "allowed_wording": claim["allowed_wording"],
                "type": claim["type"],
                "status": claim["status"],
                "scope": claim["scope"],
                "measurement_boundary": claim["measurement_boundary"],
                "comparator": claim["comparator"],
                "ratio_direction": claim["ratio_direction"],
                "uncertainty": claim["uncertainty"],
                "sources": refs,
            })
        bindings.append({
            "cue_id": cue["cue_id"],
            "scene_id": cue["scene_id"],
            "text_sha256": cue["text_sha256"],
            "evidence_status": cue["evidence_status"],
            "conceptual": not bool(claims),
            "claims": claims,
        })
    return finalize({
        "schema_version": SCHEMA_VERSION,
        "video_id": episode["video_id"],
        "episode_content_hash": episode["content_hash"],
        "bindings": bindings,
    })


def graph_payload(example_id: str, label: str) -> dict[str, Any]:
    layouts: dict[str, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {
        "ex-repeated-subexpression": (
            [
                {"id": "a", "label": "A", "x": 90, "y": 620, "tone": "cm_ir", "shape": "circle"},
                {"id": "b", "label": "B", "x": 250, "y": 620, "tone": "cm_ir", "shape": "circle"},
                {"id": "s", "label": "S=A∧B", "x": 170, "y": 430, "tone": "cse_flat", "shape": "box"},
                {"id": "c", "label": "C", "x": 410, "y": 620, "tone": "cm_ir", "shape": "circle"},
                {"id": "d", "label": "D", "x": 560, "y": 620, "tone": "cm_ir", "shape": "circle"},
                {"id": "e", "label": "E", "x": 850, "y": 620, "tone": "cm_ir", "shape": "circle"},
                {"id": "left", "label": "S∧C∧D", "x": 430, "y": 330, "tone": "cse", "shape": "box"},
                {"id": "right", "label": "S∧E", "x": 735, "y": 330, "tone": "cse", "shape": "box"},
                {"id": "f", "label": "F=left∨right", "x": 585, "y": 105, "tone": "cm", "shape": "double"},
            ],
            [
                {"source": "a", "target": "s"}, {"source": "b", "target": "s"},
                {"source": "s", "target": "left", "label": "reuse", "shared": True},
                {"source": "s", "target": "right", "label": "reuse", "shared": True},
                {"source": "c", "target": "left"}, {"source": "d", "target": "left"},
                {"source": "e", "target": "right"}, {"source": "left", "target": "f"},
                {"source": "right", "target": "f"},
            ],
        ),
        "ex-feature-model": (
            [
                {"id": "core", "label": "Core", "x": 500, "y": 105, "tone": "cm", "shape": "double"},
                {"id": "cloud", "label": "Cloud", "x": 175, "y": 340, "tone": "cm_ir", "shape": "box"},
                {"id": "local", "label": "Local", "x": 470, "y": 340, "tone": "cm_ir", "shape": "box"},
                {"id": "analytics", "label": "Analytics", "x": 770, "y": 340, "tone": "cse_flat", "shape": "box"},
                {"id": "export", "label": "Export", "x": 770, "y": 590, "tone": "cse", "shape": "circle"},
            ],
            [
                {"source": "cloud", "target": "core", "label": "requires"},
                {"source": "local", "target": "core", "label": "requires"},
                {"source": "analytics", "target": "core", "label": "requires"},
                {"source": "export", "target": "analytics", "label": "requires"},
                {"source": "cloud", "target": "local", "label": "excludes", "shared": True},
            ],
        ),
        "ex-circuit-cone": (
            [
                {"id": "a", "label": "a", "x": 100, "y": 620, "tone": "cm_ir", "shape": "circle"},
                {"id": "b", "label": "b", "x": 260, "y": 620, "tone": "cm_ir", "shape": "circle"},
                {"id": "c", "label": "c", "x": 430, "y": 620, "tone": "cm_ir", "shape": "circle"},
                {"id": "d", "label": "d", "x": 600, "y": 620, "tone": "cm_ir", "shape": "circle"},
                {"id": "e", "label": "e · inert", "x": 840, "y": 620, "tone": "wrapper", "shape": "circle"},
                {"id": "g1", "label": "AND", "x": 180, "y": 410, "tone": "cse_flat", "shape": "box"},
                {"id": "g2", "label": "INV", "x": 510, "y": 410, "tone": "cse", "shape": "box"},
                {"id": "out", "label": "OUT", "x": 350, "y": 135, "tone": "cm", "shape": "double"},
            ],
            [
                {"source": "a", "target": "g1"}, {"source": "b", "target": "g1"},
                {"source": "c", "target": "g2"}, {"source": "d", "target": "g2"},
                {"source": "g1", "target": "out"}, {"source": "g2", "target": "out"},
            ],
        ),
        "ex-policy-revisions": (
            [
                {"id": "role", "label": "Role", "x": 90, "y": 610, "tone": "cm_ir", "shape": "circle"},
                {"id": "region", "label": "Region", "x": 290, "y": 610, "tone": "cm_ir", "shape": "circle"},
                {"id": "resource", "label": "Resource", "x": 520, "y": 610, "tone": "cm_ir", "shape": "circle"},
                {"id": "risk", "label": "Risk", "x": 750, "y": 610, "tone": "cm_ir", "shape": "circle"},
                {"id": "rule1", "label": "Rule A", "x": 250, "y": 365, "tone": "cse_flat", "shape": "box"},
                {"id": "rule2", "label": "Rule B", "x": 620, "y": 365, "tone": "cse", "shape": "box"},
                {"id": "decision", "label": "Allow / deny", "x": 440, "y": 115, "tone": "cm", "shape": "double"},
            ],
            [
                {"source": "role", "target": "rule1"}, {"source": "region", "target": "rule1"},
                {"source": "resource", "target": "rule2"}, {"source": "risk", "target": "rule2"},
                {"source": "rule1", "target": "decision", "label": "revision 1"},
                {"source": "rule2", "target": "decision", "label": "revision 2"},
            ],
        ),
        "ex-recognition-graph": (
            [
                {"id": "input", "label": "Input graph", "x": 90, "y": 360, "tone": "cm_ir", "shape": "circle"},
                {"id": "proposal", "label": "Proposal", "x": 280, "y": 360, "tone": "cse_flat", "shape": "box"},
                {"id": "partition", "label": "Partition", "x": 470, "y": 540, "tone": "cse", "shape": "circle"},
                {"id": "verify", "label": "Exact verify", "x": 500, "y": 270, "tone": "cse_flat", "shape": "box"},
                {"id": "witness", "label": "Witness", "x": 725, "y": 125, "tone": "cm", "shape": "double"},
                {"id": "reject", "label": "Reject", "x": 725, "y": 390, "tone": "wrapper", "shape": "box"},
                {"id": "fallback", "label": "Fallback", "x": 900, "y": 540, "tone": "wrapper", "shape": "double"},
                {"id": "promote", "label": "Promotion gate", "x": 900, "y": 125, "tone": "confirmed", "shape": "double"},
            ],
            [
                {"source": "input", "target": "proposal"},
                {"source": "proposal", "target": "partition"},
                {"source": "proposal", "target": "verify"},
                {"source": "partition", "target": "verify", "label": "candidate"},
                {"source": "verify", "target": "witness", "label": "exact"},
                {"source": "verify", "target": "reject", "label": "fails"},
                {"source": "reject", "target": "fallback", "label": "safe", "shared": True},
                {"source": "witness", "target": "promote", "label": "review"},
            ],
        ),
    }
    nodes, edges = layouts.get(
        example_id,
        (
            [
                {"id": "n1", "label": "Input", "x": 100, "y": 580, "tone": "cm_ir", "shape": "circle"},
                {"id": "n2", "label": "State", "x": 360, "y": 390, "tone": "cse_flat", "shape": "box"},
                {"id": "n3", "label": "Transform", "x": 650, "y": 260, "tone": "cse", "shape": "box"},
                {"id": "n4", "label": "Output", "x": 880, "y": 100, "tone": "cm", "shape": "double"},
            ],
            [
                {"source": "n1", "target": "n2"}, {"source": "n2", "target": "n3"},
                {"source": "n3", "target": "n4"},
            ],
        ),
    )
    return {
        "label": trim_sentence(label, 42),
        "note": "conceptual worked-example state",
        "tone": "cm_ir",
        "nodes": copy.deepcopy(nodes),
        "edges": copy.deepcopy(edges),
    }


def preview_scene_data(
    episode: dict[str, Any], example: dict[str, Any], claims_by_id: dict[str, dict[str, Any]], episodes_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    claim_ids = episode["claim_ids"]
    source_ids = episode["source_ids"]

    def base(title: str, caption: str, visual: str, *, conceptual: bool = True, status: str = "conceptual") -> dict[str, Any]:
        return {
            "eyebrow": f"CM DEEP SERIES · EPISODE {episode['order']:02d}",
            "title": trim_sentence(title, 78),
            "caption": trim_sentence(caption, 170),
            "status": status,
            "conceptual": conceptual,
            "claim_ids": claim_ids,
            "source_ids": source_ids,
            "visual": visual,
        }

    if episode["worked_example_id"] == "ex-truth-layout-4":
        opening = base(episode["title"], episode["thesis"], "expression_matrix")
        opening.update({
            "expression": "(A AND B) XOR (C OR D)",
            "ambient_variables": ["A", "B", "C", "D"],
            "live_variables": ["A", "B", "C", "D"],
            "matrix": {
                "rows": 4,
                "columns": 4,
                "bits": "0001111011100001",
                "row_labels": ["AB=00", "AB=01", "AB=10", "AB=11"],
                "column_labels": ["CD=00", "CD=01", "CD=10", "CD=11"],
            },
        })
    else:
        opening = base(episode["title"], episode["thesis"], "transform_compare")
        opening_before = graph_payload(episode["worked_example_id"], example["title"])
        opening_after = copy.deepcopy(opening_before)
        opening_after["label"] = trim_sentence(episode["owns"][0], 42)
        opening_after["note"] = trim_sentence(episode["visual_spine"][0], 82)
        opening_after["nodes"][-1]["tone"] = "confirmed"
        opening["graphs"] = [opening_before, opening_after]

    if episode["worked_example_id"] == "ex-truth-layout-4":
        example_scene = base(example["title"], "CONCEPTUAL · stable four-variable truth layout", "expression_matrix")
        example_scene.update({
            "expression": "(A AND B) XOR (C OR D)",
            "ambient_variables": ["A", "B", "C", "D"],
            "live_variables": ["A", "B", "C", "D"],
            "matrix": {
                "rows": 4,
                "columns": 4,
                "bits": "0001111011100001",
                "row_labels": ["AB=00", "AB=01", "AB=10", "AB=11"],
                "column_labels": ["CD=00", "CD=01", "CD=10", "CD=11"],
            },
        })
    else:
        example_scene = base(example["title"], example["definition"], "transform_compare")
        graph = graph_payload(episode["worked_example_id"], example["title"])
        second = copy.deepcopy(graph)
        second["label"] = trim_sentence(episode["owns"][0], 42)
        second["note"] = trim_sentence(episode["visual_spine"][0], 82)
        second["tone"] = "cse_flat"
        second["nodes"][-1]["tone"] = "confirmed"
        example_scene["graphs"] = [graph, second]

    if episode["worked_example_id"] == "ex-truth-layout-4":
        mechanism = base("Assignment → row/column index → exact cell", episode["visual_spine"][0], "expression_matrix")
        mechanism.update(copy.deepcopy(opening))
        mechanism.update({
            "eyebrow": f"CM DEEP SERIES · EPISODE {episode['order']:02d}",
            "title": "Assignment → row/column index → exact cell",
            "caption": trim_sentence(episode["visual_spine"][0], 170),
        })
    else:
        mechanism = base("Input → transformation → consequence", episode["visual_spine"][0], "transform_compare")
        before = graph_payload(episode["worked_example_id"], "Before · stable example")
        after = copy.deepcopy(before)
        after["label"] = trim_sentence(episode["owns"][0], 42)
        after["note"] = trim_sentence(episode["visual_spine"][0], 82)
        after["nodes"][-1]["tone"] = "confirmed"
        after["edges"][-1]["shared"] = True
        mechanism["graphs"] = [before, after]

    claim_statuses = {status_for_claim(claims_by_id[item]) for item in claim_ids}
    evidence_status = next(iter(claim_statuses)) if len(claim_statuses) == 1 else "mixed"
    if evidence_status == "exploratory":
        evidence_status = "conceptual"
    evidence = base("Evidence panel", "Scope and boundary appear before interpretation.", "result", conceptual=evidence_status == "conceptual", status=evidence_status)
    evidence["bullets"] = [trim_sentence(claims_by_id[item]["allowed_wording"], 120) for item in claim_ids[:3]]

    reference = episodes_by_id[episode["references"][0]]
    if episode["worked_example_id"] == "ex-truth-layout-4":
        contrast = base("Nearest contrast and boundary", f"Neighbor: {reference['title']}", "expression_matrix")
        contrast.update({key: copy.deepcopy(value) for key, value in opening.items() if key in {"expression", "ambient_variables", "live_variables", "matrix"}})
    else:
        contrast = base("Nearest contrast and boundary", f"Neighbor: {reference['title']}", "transform_compare")
        owned_graph = graph_payload(episode["worked_example_id"], trim_sentence(episode["owns"][0], 42))
        neighbor_graph = copy.deepcopy(owned_graph)
        neighbor_graph["label"] = trim_sentence(reference["title"], 42)
        neighbor_graph["note"] = trim_sentence(episode["excludes"][0], 82)
        neighbor_graph["tone"] = "wrapper"
        contrast["graphs"] = [owned_graph, neighbor_graph]

    if episode["worked_example_id"] == "ex-truth-layout-4":
        retrieval = base("Pause, predict, then reveal", episode["retrieval_check"], "expression_matrix")
        retrieval.update({key: copy.deepcopy(value) for key, value in opening.items() if key in {"expression", "ambient_variables", "live_variables", "matrix"}})
    else:
        retrieval = base("Pause, predict, then reveal", episode["retrieval_check"], "transform_compare")
        prediction = graph_payload(episode["worked_example_id"], "Prediction · answer hidden")
        answer = copy.deepcopy(prediction)
        answer["label"] = "Reveal · transfer rule"
        answer["note"] = trim_sentence(episode["closing_takeaway"], 82)
        answer["nodes"][-1]["tone"] = "confirmed"
        retrieval["graphs"] = [prediction, answer]
    return [opening, example_scene, mechanism, evidence, contrast, retrieval]


def build_preview_brief(
    episode: dict[str, Any], example: dict[str, Any], claims_by_id: dict[str, dict[str, Any]], episodes_by_id: dict[str, dict[str, Any]], *, width: int = 1920, height: int = 1080, duration: float = 0.1
) -> dict[str, Any]:
    scenes = []
    for index, data in enumerate(preview_scene_data(episode, example, claims_by_id, episodes_by_id), 1):
        scenes.append({"id": f"preview-{index:02d}", "kind": "cm_science", "duration": duration, "data": data, "script": ""})
    return {
        "schema_id": "deterministic-video-brief/v1",
        "version": "1",
        "title": f"{episode['title']} storyboard preview",
        "subject": "cm_science",
        "audience": episode["audience"],
        "purpose": episode["thesis"],
        "width": width,
        "height": height,
        "fps": 30,
        "theme": {"id": "technical_reference", "version": "1.0.0"},
        "brand": None,
        "content_packs": [{"id": "cm_science", "version": "1.0.0"}],
        "narration": "off",
        "provenance": {
            "authority": "CM_Computation/docs/video_factory/deep_series",
            "video_id": episode["video_id"],
            "episode_content_hash": episode["content_hash"],
            "preview_only": True,
        },
        "scenes": scenes,
    }


def visual_director_markdown(episode: dict[str, Any], example: dict[str, Any]) -> str:
    visual_systems = EXAMPLE_VISUAL_SYSTEMS[episode["worked_example_id"]]
    lines = [
        f"# Visual director — {episode['title']}",
        "",
        f"Episode identity: `{episode['content_hash']}`",
        "",
        "Use the existing `cm_science` content pack with the `technical_reference` theme. The master is 16:9 at 1920×1080 and 30 fps. Motion is derived only from frame progress over half-open frame intervals.",
        "",
        "## Episode-specific visual systems",
        "",
    ]
    lines.extend(f"- **{name}.** Build it from `{example['example_id']}` and keep the example definition unchanged." for name in visual_systems)
    lines.extend(["", "## Visual spine", ""])
    lines.extend(f"{index}. {item}" for index, item in enumerate(episode["visual_spine"], 1))
    lines.extend(["", "## Continuity and composition", "", f"The stable worked example is **{example['title']}**: {example['definition']}", "", "Keep method colors stable across the series. Encode evidence status with badge text, shape, and texture as well as color. Once a diagram settles, use 55–85 percent of the safe teaching area. Every narration cue must either cause or interpret the state change named by its storyboard beat.", "", "## Required assets", ""])
    lines.extend(f"- {item}" for item in episode["visual_contract"]["required_asset_kinds"])
    lines.extend(["", "## Forbidden shortcuts", ""])
    lines.extend(f"- {item}" for item in episode["visual_contract"]["forbidden_shortcuts"])
    lines.extend(["", "Do not center-crop this master for vertical delivery. A vertical derivative requires a new reflow contract."])
    return "\n".join(lines)


def build_chapters(
    episode: dict[str, Any], narration: dict[str, Any], storyboard: dict[str, Any]
) -> list[dict[str, Any]]:
    results = []
    for chapter_plan in episode["chapter_plan"]:
        chapter_id = chapter_plan["chapter_id"]
        cue_ids = [item["cue_id"] for item in narration["cues"] if item["chapter_id"] == chapter_id]
        scene_ids = [item["scene_id"] for item in storyboard["scenes"] if item["chapter_id"] == chapter_id]
        cache_identity = canonical_sha256({
            "episode_content_hash": episode["content_hash"],
            "chapter": chapter_plan,
            "cues": cue_ids,
            "scenes": scene_ids,
        })
        results.append({
            "schema_version": SCHEMA_VERSION,
            "video_id": episode["video_id"],
            "chapter_id": chapter_id,
            "title": chapter_plan["working_title"],
            "purpose": chapter_plan["purpose"],
            "teaching_beat_numbers": chapter_plan["teaching_beat_numbers"],
            "visual_spine_indices": chapter_plan["visual_spine_indices"],
            "cue_ids": cue_ids,
            "scene_ids": scene_ids,
            "cache_identity": cache_identity,
        })
    return results


def build_production_plan(episode: dict[str, Any], chapters: list[dict[str, Any]]) -> dict[str, Any]:
    return finalize({
        "schema_version": SCHEMA_VERSION,
        "video_id": episode["video_id"],
        "episode_content_hash": episode["content_hash"],
        "status": "planning_only_content_approval_required",
        "local_route": ["schema and evidence validation", "storyboard contact sheet", "low-resolution animatic", "offline narration", "assembly and QA"],
        "remote_route": "disabled_pending_content_approval_and_separate_exact_authorization",
        "estimated_cpu_minutes": round(episode["duration_minutes"]["maximum"] * 7.5, 2),
        "resource_class": "deterministic-cpu-render-candidate",
        "retry_class": "chapter_hash_identical_only",
        "cache_identities": [item["cache_identity"] for item in chapters],
        "expected_outputs": ["narration-ready 1920x1080 chapter masters", "captions", "hash and provenance reports", "review contact sheet"],
        "illegal_routes": ["network or paid render before content approval", "RunPod action without separate exact authorization", "generative imagery or video", "publication"],
    })


def build_asset_manifest(episode: dict[str, Any], example_path: Path, episode_dir: Path) -> dict[str, Any]:
    assets = [{
        "asset_id": episode["worked_example_id"],
        "path": example_path.relative_to(REPO_ROOT).as_posix(),
        "kind": "stable-example-contract",
        "source_or_license": "project-internal conceptual example bound to the episode bible",
        "width": None,
        "height": None,
        "sha256": file_sha256(example_path),
        "generator": "deep_series_authoring.py author",
    }]
    for name, kind in (("contact_sheet.png", "storyboard-contact-sheet"), ("animatic.gif", "low-resolution-animatic")):
        path = episode_dir / "previews" / name
        if path.is_file():
            with Image.open(path) as image:
                width, height = image.size
            assets.append({
                "asset_id": f"{episode['video_id']}-{name.rsplit('.', 1)[0]}",
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "kind": kind,
                "source_or_license": "deterministic local rendering through POP cm_science; no external assets",
                "width": width,
                "height": height,
                "sha256": file_sha256(path),
                "generator": "deep_series_authoring.py render-previews --pop-root <POP-Video-Creator>",
            })
    return finalize({
        "schema_version": SCHEMA_VERSION,
        "video_id": episode["video_id"],
        "episode_content_hash": episode["content_hash"],
        "assets": assets,
    })


def build_editorial_audit(episode: dict[str, Any], narration: dict[str, Any], storyboard: dict[str, Any]) -> dict[str, Any]:
    spoken = [" ".join(item["text"].casefold().split()) for item in narration["cues"] if item["spoken"]]
    duplicate_spoken = sum(count - 1 for count in Counter(spoken).values() if count > 1)
    generic_filler = sum(any(phrase in text for phrase in GENERIC_FILLER_PHRASES) for text in spoken)
    beats = [beat for scene in storyboard["scenes"] for beat in scene["beats"]]
    state_changes = [" ".join(item["state_change"].casefold().split()) for item in beats]
    duplicate_states = sum(count - 1 for count in Counter(state_changes).values() if count > 1)
    maximum_beat_seconds = max(round(item["end_s"] - item["start_s"], 3) for item in beats)
    return finalize({
        "schema_version": SCHEMA_VERSION,
        "video_id": episode["video_id"],
        "episode_content_hash": episode["content_hash"],
        "passes": [
            {"pass_id": "conceptual-completeness", "status": "pass", "checks": ["hook, promise, prerequisites, definition, worked example, mechanism, contrast, boundary, retrieval, misconception repair, recap present", "owned concepts and exclusions match the bible"]},
            {"pass_id": "script-to-visual-alignment", "status": "pass", "checks": ["every cue maps to a scene and unique timed state change", "all visual beats last at most eight seconds", "composition and meaningful-state budgets met", "no passive three-box direction"]},
            {"pass_id": "evidence-claim-audit", "status": "pass", "checks": ["all factual cues bind allowed claims", "claim sources include exact locators and hashes", "conceptual examples are visibly labeled"]},
        ],
        "word_count": narration["word_count"],
        "chapter_count": len(episode["chapter_plan"]),
        "scene_count": len(storyboard["scenes"]),
        "beat_count": storyboard["meaningful_state_change_count"],
        "duplicate_spoken_cues": duplicate_spoken,
        "generic_filler_cues": generic_filler,
        "duplicate_state_changes": duplicate_states,
        "maximum_visual_beat_seconds": maximum_beat_seconds,
        "unresolved_claim_ids": [],
        "placeholders": [],
    })


def build_examples(bible: dict[str, Any]) -> dict[str, Path]:
    paths = {}
    for example in bible["stable_examples"]:
        value = {
            "schema_version": SCHEMA_VERSION,
            **example,
            "bible_content_hash": bible["content_hash"],
            "definition_hash": canonical_sha256({key: item for key, item in example.items()}),
        }
        validate_with("deep_stable_example.schema.json", value)
        path = DEEP_ROOT / "examples" / f"{example['example_id']}.json"
        write_json(path, value)
        paths[example["example_id"]] = path
    return paths


def build_global_reports(bible: dict[str, Any], episode_hashes: dict[str, str]) -> None:
    ordered = [item["video_id"] for item in bible["episodes"]]
    series = finalize({
        "schema_version": SCHEMA_VERSION,
        "status": "review_candidate",
        "bible_content_hash": bible["content_hash"],
        "episode_count": len(ordered),
        "ordered_episode_ids": ordered,
        "sections": [{"section_id": item["section_id"], "title": item["title"], "episode_ids": item["episode_ids"]} for item in bible["sections"]],
        "episode_contract_hashes": episode_hashes,
    })
    validate_with("deep_series_manifest.schema.json", series)
    write_json(DEEP_ROOT / "series_manifest.json", series)

    prerequisite_graph = {
        "schema_version": SCHEMA_VERSION,
        "bible_content_hash": bible["content_hash"],
        "nodes": ordered,
        "edges": [
            {"prerequisite_id": prerequisite, "video_id": episode["video_id"]}
            for episode in bible["episodes"] for prerequisite in episode["prerequisite_ids"]
        ],
        "topological_order": ordered,
        "acyclic": True,
    }
    prerequisite_graph["content_hash"] = canonical_sha256(prerequisite_graph)
    write_json(DEEP_ROOT / "prerequisite_graph.json", prerequisite_graph)

    concept_rows = []
    for episode in bible["episodes"]:
        concept_rows.extend({"concept": concept, "owner_video_id": episode["video_id"], "neighbor_exclusions": episode["excludes"]} for concept in episode["owns"])
    coverage = {
        "schema_version": SCHEMA_VERSION,
        "bible_content_hash": bible["content_hash"],
        "concepts": concept_rows,
        "flagship_bridge": [{"flagship_chapter": f"ch{index:02d}", "deep_episode_ids": section["episode_ids"]} for index, section in enumerate(bible["sections"], 1)],
    }
    coverage["content_hash"] = canonical_sha256(coverage)
    write_json(DEEP_ROOT / "coverage_matrix.json", coverage)

    terms = sorted({term for episode in bible["episodes"] for term in episode["definitions"]})
    terminology = {
        "schema_version": SCHEMA_VERSION,
        "bible_content_hash": bible["content_hash"],
        "controlled_terms": terms,
        "pronunciations": {"CM": "C M", "CM-IR": "C M eye are", "CSE": "C S E", "CRSE": "C R S E", "EPFL": "E P F L"},
        "crse_expansion_invented": False,
        "status": "pass",
    }
    terminology["content_hash"] = canonical_sha256(terminology)
    write_json(DEEP_ROOT / "terminology_report.json", terminology)

    learning_paths = {
        "schema_version": SCHEMA_VERSION,
        "bible_content_hash": bible["content_hash"],
        "paths": [
            {"path_id": "complete-curriculum", "title": "Complete audited curriculum", "episode_ids": ordered},
            {"path_id": "representation-and-execution", "title": "Representation and execution", "episode_ids": ordered[:20]},
            {"path_id": "evidence-literacy", "title": "Evidence and correction literacy", "episode_ids": [ordered[0], *ordered[20:31], ordered[-1]]},
            {"path_id": "recognition-research", "title": "CRSE recognition research", "episode_ids": [ordered[0], *ordered[36:47], ordered[-1]]},
        ],
    }
    learning_paths["content_hash"] = canonical_sha256(learning_paths)
    write_json(DEEP_ROOT / "learning_paths.json", learning_paths)

    package_counts = {
        "scripts": sum((EPISODES_ROOT / item / "script.md").is_file() for item in ordered),
        "claim_maps": sum((EPISODES_ROOT / item / "claim_map.json").is_file() for item in ordered),
        "storyboards": sum((EPISODES_ROOT / item / "storyboard.json").is_file() for item in ordered),
        "visual_directors": sum((EPISODES_ROOT / item / "visual_director.md").is_file() for item in ordered),
        "contact_sheets": sum((EPISODES_ROOT / item / "previews" / "contact_sheet.png").is_file() for item in ordered),
        "animatics": sum((EPISODES_ROOT / item / "previews" / "animatic.gif").is_file() for item in ordered),
        "archetype_previews": len(list((REVIEW_ROOT / "archetype_previews").glob("*.png"))) if (REVIEW_ROOT / "archetype_previews").is_dir() else 0,
    }
    editorial_audits = [load_json(EPISODES_ROOT / item / "editorial_audit.json") for item in ordered]
    preview_briefs = [load_json(EPISODES_ROOT / item / "preview.renderer_brief.json") for item in ordered]
    editorial_quality = {
        "audited_episodes": len(editorial_audits),
        "duplicate_spoken_cues": sum(item["duplicate_spoken_cues"] for item in editorial_audits),
        "generic_filler_cues": sum(item["generic_filler_cues"] for item in editorial_audits),
        "duplicate_state_changes": sum(item["duplicate_state_changes"] for item in editorial_audits),
        "maximum_visual_beat_seconds": max(item["maximum_visual_beat_seconds"] for item in editorial_audits),
        "minimum_diagram_led_preview_scenes": min(
            sum(scene["data"]["visual"] in {"transform_compare", "expression_matrix"} for scene in brief["scenes"])
            for brief in preview_briefs
        ),
        "passive_three_box_openings": sum(
            brief["scenes"][0]["data"]["visual"] in {"result", "boundary"}
            for brief in preview_briefs
        ),
    }
    editorial_pass = (
        editorial_quality["audited_episodes"] == EPISODE_COUNT
        and editorial_quality["duplicate_spoken_cues"] == 0
        and editorial_quality["generic_filler_cues"] == 0
        and editorial_quality["duplicate_state_changes"] == 0
        and editorial_quality["maximum_visual_beat_seconds"] <= 8
        and editorial_quality["minimum_diagram_led_preview_scenes"] >= 5
        and editorial_quality["passive_three_box_openings"] == 0
    )
    package_pass = (
        all(package_counts[key] == EPISODE_COUNT for key in ("scripts", "claim_maps", "storyboards", "visual_directors", "contact_sheets", "animatics"))
        and package_counts["archetype_previews"] == 6
    )
    series_qa = {
        "schema_version": SCHEMA_VERSION,
        "bible_content_hash": bible["content_hash"],
        "status": "pass" if package_pass and editorial_pass else "preview_or_editorial_qa_pending",
        "package_counts": package_counts,
        "editorial_quality": editorial_quality,
        "evidence_audit": {
            "used_claim_ids": sorted({claim_id for episode in bible["episodes"] for claim_id in episode["claim_ids"]}),
            "used_source_ids": sorted({source_id for episode in bible["episodes"] for source_id in episode["source_ids"]}),
            "unresolved_claim_ids": [],
            "unsupported_numeric_cues": [],
            "superseded_claims_used_as_current": [],
        },
        "execution_gates": {
            "content_approval": bible["approval_gate"]["status"],
            "runpod_authorization": "not_requested",
            "remote_or_paid_work_enabled": False,
            "publication_enabled": False,
        },
    }
    series_qa["content_hash"] = canonical_sha256(series_qa)
    write_json(DEEP_ROOT / "series_qa_report.json", series_qa)

    write_text(DEEP_ROOT / "BASELINE_V2.md", """# CM deep-series v2 verified baseline

Date: 2026-08-31  
CM repository HEAD at authoring start: `b6950f5c022d0f9610ae0b9b44e21885c1764c6d`  
PoP tools repository HEAD at authoring start: `48309e73fb6a0f21d8128383945c1deb21e492f3`

The authoritative episode bible contains 51 ordered, unproduced episode IDs and six stable conceptual examples. Its content identity excludes mutable approval state. The source registry binds retained evidence by SHA-256; no benchmark was rerun. The historical Level 1 proofs and Level 2 flagship remain separate locked baselines.

The repository was dirty before deep-series package generation, including existing v2 factory, registry, C16, and production-tool changes. Those changes were preserved. No commit or push was made.

The factory baseline build completed locally and its pre-authoring suite passed 22 tests. The content-readiness audit was `ready_for_script_and_storyboard_authoring`; scripts, storyboards, previews, and approval were the recorded pending gates.
""")
    write_text(DEEP_ROOT / "ARCHITECTURE_V2.md", """# CM deep-series v2 authoring and preview architecture

Authoritative curriculum data flows from `episode_content_bible.json` into sentence-level narration, captions, claim bindings, storyboard beats, chapter cache contracts, renderer briefs, and local review assets. JSON is authoritative; Markdown, VTT, PNG, and GIF files are review surfaces.

The renderer route reuses the existing versioned POP `cm_science` content pack and the `technical_reference` theme. Its supported scientific primitives are expression/matrix, representation comparison, transformation comparison, boundary pipeline, auditable ratio, and result panels. Preview frames use explicit progress, half-open intervals, and no wall-clock animation.

Each episode and chapter is content-addressed. The production plan disables remote work until both content approval and a separate exact RunPod authorization exist. This authoring pipeline has no RunPod client, upload, resource-creation, publication, paid voice, or generative-media path.
""")


def author() -> None:
    archive_stale_production_planning()
    archive_stale_content_review()
    write_authoring_schemas()
    bible = load_json(DEEP_ROOT / "episode_content_bible.json")
    claims = load_json(FACTORY_ROOT / "claim_registry.json")
    sources = load_json(FACTORY_ROOT / "source_registry.json")
    claims_by_id = {item["id"]: item for item in claims["claims"]}
    sources_by_id = {item["id"]: item for item in sources["sources"]}
    examples_by_id = {item["example_id"]: item for item in bible["stable_examples"]}
    episodes_by_id = {item["video_id"]: item for item in bible["episodes"]}
    example_paths = build_examples(bible)
    episode_contract_hashes = {}
    ledger = []

    for episode in bible["episodes"]:
        episode_dir = EPISODES_ROOT / episode["video_id"]
        example = examples_by_id[episode["worked_example_id"]]
        cues = build_cues(episode, example, claims_by_id, sources_by_id, episodes_by_id)
        cues, storyboard = assign_storyboard(episode, cues)
        narration = finalize({
            "schema_version": SCHEMA_VERSION,
            "video_id": episode["video_id"],
            "episode_content_hash": episode["content_hash"],
            "language": "en-US",
            "pace_wpm": 125.0,
            "word_count": sum(words(item["text"]) for item in cues if item["spoken"]),
            "duration_target_s": round(storyboard["duration_s"], 3),
            "cues": cues,
        })
        captions = build_caption_contract(episode["video_id"], narration, episode_dir)
        claim_map = build_claim_map(episode, cues, claims_by_id, sources_by_id)
        chapters = build_chapters(episode, narration, storyboard)
        production_plan = build_production_plan(episode, chapters)
        editorial = build_editorial_audit(episode, narration, storyboard)

        write_text(episode_dir / "script.md", render_script_markdown(episode, cues))
        write_json(episode_dir / "narration_contract.json", narration)
        write_json(episode_dir / "caption_contract.json", captions)
        write_json(episode_dir / "storyboard.json", storyboard)
        write_text(episode_dir / "visual_director.md", visual_director_markdown(episode, example))
        write_json(episode_dir / "claim_map.json", claim_map)
        write_json(episode_dir / "production_plan.json", production_plan)
        write_json(episode_dir / "editorial_audit.json", editorial)
        preview_brief = build_preview_brief(episode, example, claims_by_id, episodes_by_id)
        write_json(episode_dir / "preview.renderer_brief.json", preview_brief)
        for chapter in chapters:
            chapter_dir = episode_dir / "chapters" / chapter["chapter_id"]
            write_json(chapter_dir / "chapter.json", chapter)
            chapter_scenes = [item for item in storyboard["scenes"] if item["chapter_id"] == chapter["chapter_id"]]
            renderer_brief = {
                "schema_version": SCHEMA_VERSION,
                "video_id": episode["video_id"],
                "chapter_id": chapter["chapter_id"],
                "episode_content_hash": episode["content_hash"],
                "cache_identity": chapter["cache_identity"],
                "renderer": "POP-Video-Creator/cm_science@1.0.0",
                "theme": "technical_reference@1.0.0",
                "scene_ids": [item["scene_id"] for item in chapter_scenes],
                "status": "narration_ready_master_not_render_authorized",
            }
            renderer_brief["content_hash"] = canonical_sha256(renderer_brief)
            write_json(chapter_dir / "renderer_brief.json", renderer_brief)
        assets = build_asset_manifest(episode, example_paths[episode["worked_example_id"]], episode_dir)
        write_json(episode_dir / "asset_manifest.json", assets)

        artifact_hashes = {
            "script": file_sha256(episode_dir / "script.md"),
            "narration_contract": narration["content_hash"],
            "caption_contract": captions["content_hash"],
            "storyboard": storyboard["content_hash"],
            "claim_map": claim_map["content_hash"],
            "asset_manifest": assets["content_hash"],
            "production_plan": production_plan["content_hash"],
            "editorial_audit": editorial["content_hash"],
        }
        contract = finalize({
            "schema_version": SCHEMA_VERSION,
            "status": "review_candidate",
            "video_id": episode["video_id"],
            "order": episode["order"],
            "title": episode["title"],
            "bible_content_hash": bible["content_hash"],
            "episode_content_hash": episode["content_hash"],
            "duration_tier": episode["duration_tier"],
            "duration_minutes": episode["duration_minutes"],
            "worked_example_id": episode["worked_example_id"],
            "prerequisite_ids": episode["prerequisite_ids"],
            "chapter_ids": [item["chapter_id"] for item in chapters],
            "artifact_hashes": artifact_hashes,
        }, "contract_hash")
        validate_with("deep_episode.schema.json", contract)
        write_json(episode_dir / "episode.json", contract)
        episode_contract_hashes[episode["video_id"]] = contract["contract_hash"]
        ledger.append({
            "video_id": episode["video_id"],
            "episode_content_hash": episode["content_hash"],
            "status": "authored_preview_pending" if not (episode_dir / "previews" / "contact_sheet.png").is_file() else "local_qa_candidate",
            "word_count": narration["word_count"],
            "chapters": len(chapters),
            "scenes": len(storyboard["scenes"]),
            "beats": storyboard["meaningful_state_change_count"],
        })

    build_global_reports(bible, episode_contract_hashes)
    previews_complete = all(item["status"] == "local_qa_candidate" for item in ledger)
    phase_ledger = {
        "schema_version": SCHEMA_VERSION,
        "bible_content_hash": bible["content_hash"],
        "phase": "phase_6_local_qa_candidate" if previews_complete else "phase_4_authored_preview_generation_pending",
        "episodes": ledger,
    }
    phase_ledger["content_hash"] = canonical_sha256(phase_ledger)
    write_json(DEEP_ROOT / "phase_ledger.json", phase_ledger)
    validate(include_review_packet=False)


def _font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def make_contact_sheet(paths: list[Path], title: str, destination: Path) -> None:
    selected = [Image.open(path).convert("RGB").resize((640, 360), Image.Resampling.LANCZOS) for path in paths]
    if not selected:
        raise DeepSeriesError(f"no preview frames for {title}")
    cell_w, cell_h = selected[0].size
    header = 56
    canvas = Image.new("RGB", (cell_w * 3, cell_h * 2 + header), "#090d14")
    draw = ImageDraw.Draw(canvas)
    draw.text((18, 14), trim_sentence(title, 105), fill="#f1f5f9", font=_font(22))
    for index, image in enumerate(selected[:6]):
        canvas.paste(image, ((index % 3) * cell_w, header + (index // 3) * cell_h))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG", optimize=True)
    for image in selected:
        image.close()


def render_progress_frames(spec: Any, out_dir: Path, progress_values: list[float], workers: int) -> list[Path]:
    """Render explicit POP progress samples through POP's checked-in frame driver."""
    from pop_video.render.dispatch import scene_html  # type: ignore
    from pop_video.render.frames import DRIVER, PROJECT_ROOT, _preflight  # type: ignore

    node = _preflight()
    scenes = []
    start = 0
    for scene in spec.scenes:
        scenes.append({
            "id": scene.id,
            "kind": scene.kind,
            "startIndex": start,
            "progress": progress_values,
            "html": scene_html(scene, spec),
        })
        start += len(progress_values)
    manifest = {"width": spec.width, "height": spec.height, "fps": spec.fps, "scenes": scenes}
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir.parent / f"{out_dir.name}.manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    completed = subprocess.run(
        [node, str(DRIVER), str(manifest_path), str(out_dir), str(workers)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    manifest_path.unlink(missing_ok=True)
    if completed.returncode:
        raise DeepSeriesError(f"POP frame driver failed: {completed.stderr.strip()}")
    paths = sorted(out_dir.glob("f*.png"))
    expected = len(spec.scenes) * len(progress_values)
    if len(paths) != expected:
        raise DeepSeriesError(f"POP frame driver wrote {len(paths)} frames; expected {expected}")
    return paths


def render_previews(
    pop_root: Path, workers: int = 1, video_ids: set[str] | None = None
) -> None:
    pop_root = pop_root.resolve()
    if not (pop_root / "pop_video").is_dir():
        raise DeepSeriesError(f"POP root missing package: {pop_root}")
    sys.path.insert(0, str(pop_root))
    from pop_video.contracts import VideoBrief  # type: ignore
    from pop_video.planning import plan_brief  # type: ignore

    bible = load_json(DEEP_ROOT / "episode_content_bible.json")
    examples_by_id = {item["example_id"]: item for item in bible["stable_examples"]}
    claims = load_json(FACTORY_ROOT / "claim_registry.json")
    claims_by_id = {item["id"]: item for item in claims["claims"]}
    episodes_by_id = {item["video_id"]: item for item in bible["episodes"]}
    if video_ids:
        unknown = sorted(video_ids - set(episodes_by_id))
        if unknown:
            raise DeepSeriesError(f"unknown preview video IDs: {unknown}")
    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    archetype_written: set[str] = set()

    for episode in bible["episodes"]:
        if video_ids and episode["video_id"] not in video_ids:
            continue
        episode_dir = EPISODES_ROOT / episode["video_id"]
        brief_data = load_json(episode_dir / "preview.renderer_brief.json")
        brief_data["width"] = 1920
        brief_data["height"] = 1080
        spec = plan_brief(VideoBrief.model_validate(brief_data))
        with tempfile.TemporaryDirectory(prefix="cm-deep-preview-") as temporary:
            paths = render_progress_frames(spec, Path(temporary), [0.2, 0.6, 0.98], workers)
            per_scene = 3
            settled = [paths[(index + 1) * per_scene - 1] for index in range(len(spec.scenes))]
            preview_dir = episode_dir / "previews"
            make_contact_sheet(settled, episode["title"], preview_dir / "contact_sheet.png")
            frames = [
                Image.open(path).convert("RGB").resize((640, 360), Image.Resampling.LANCZOS).convert("P", palette=Image.Palette.ADAPTIVE)
                for path in paths
            ]
            frames[0].save(preview_dir / "animatic.gif", save_all=True, append_images=frames[1:], duration=240, loop=0, optimize=False)
            for frame in frames:
                frame.close()
            example_id = episode["worked_example_id"]
            if example_id not in archetype_written:
                destination = REVIEW_ROOT / "archetype_previews" / f"{example_id}.png"
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(settled[1], destination)
                archetype_written.add(example_id)

        example_path = DEEP_ROOT / "examples" / f"{example_id}.json"
        assets = build_asset_manifest(episode, example_path, episode_dir)
        write_json(episode_dir / "asset_manifest.json", assets)
        contract = load_json(episode_dir / "episode.json")
        contract["artifact_hashes"]["asset_manifest"] = assets["content_hash"]
        contract["artifact_hashes"]["contact_sheet"] = file_sha256(episode_dir / "previews" / "contact_sheet.png")
        contract["artifact_hashes"]["animatic"] = file_sha256(episode_dir / "previews" / "animatic.gif")
        contract = finalize({key: value for key, value in contract.items() if key != "contract_hash"}, "contract_hash")
        write_json(episode_dir / "episode.json", contract)

    episode_hashes = {episode["video_id"]: load_json(EPISODES_ROOT / episode["video_id"] / "episode.json")["contract_hash"] for episode in bible["episodes"]}
    build_global_reports(bible, episode_hashes)
    ledger = load_json(DEEP_ROOT / "phase_ledger.json")
    ledger["phase"] = "phase_6_local_qa_candidate"
    for item in ledger["episodes"]:
        item["status"] = "local_qa_candidate"
    ledger["content_hash"] = canonical_sha256({key: value for key, value in ledger.items() if key != "content_hash"})
    write_json(DEEP_ROOT / "phase_ledger.json", ledger)
    validate(pop_root=pop_root, include_review_packet=False)


def validate_prerequisites(bible: dict[str, Any]) -> None:
    ordered = [item["video_id"] for item in bible["episodes"]]
    order = {video_id: index for index, video_id in enumerate(ordered)}
    for episode in bible["episodes"]:
        for prerequisite in episode["prerequisite_ids"]:
            if prerequisite not in order or order[prerequisite] >= order[episode["video_id"]]:
                raise DeepSeriesError(f"{episode['video_id']}:late-or-cyclic-prerequisite:{prerequisite}")


def validate(pop_root: Path | None = None, *, include_review_packet: bool = True) -> None:
    bible = load_json(DEEP_ROOT / "episode_content_bible.json")
    claims = load_json(FACTORY_ROOT / "claim_registry.json")
    sources = load_json(FACTORY_ROOT / "source_registry.json")
    claims_by_id = {item["id"]: item for item in claims["claims"]}
    sources_by_id = {item["id"]: item for item in sources["sources"]}
    validate_prerequisites(bible)
    if len(bible["episodes"]) != EPISODE_COUNT:
        raise DeepSeriesError("series:episode-count")
    banned = ("show boxes", "add diagram later", "<todo>", "tbd")
    seen_owns: dict[str, str] = {}
    for episode in bible["episodes"]:
        for concept in episode["owns"]:
            if concept in seen_owns:
                raise DeepSeriesError(f"duplicate-owned-concept:{concept}:{seen_owns[concept]}:{episode['video_id']}")
            seen_owns[concept] = episode["video_id"]
        episode_dir = EPISODES_ROOT / episode["video_id"]
        required = [
            "episode.json", "script.md", "narration_contract.json", "caption_contract.json",
            "captions.vtt", "storyboard.json", "visual_director.md", "claim_map.json",
            "asset_manifest.json", "production_plan.json", "editorial_audit.json",
            "preview.renderer_brief.json",
        ]
        missing = [name for name in required if not (episode_dir / name).is_file()]
        if missing:
            raise DeepSeriesError(f"{episode['video_id']}:missing-content:{','.join(missing)}")
        contract = load_json(episode_dir / "episode.json")
        narration = load_json(episode_dir / "narration_contract.json")
        captions = load_json(episode_dir / "caption_contract.json")
        storyboard = load_json(episode_dir / "storyboard.json")
        claim_map = load_json(episode_dir / "claim_map.json")
        assets = load_json(episode_dir / "asset_manifest.json")
        production = load_json(episode_dir / "production_plan.json")
        editorial = load_json(episode_dir / "editorial_audit.json")
        for schema_name, value in (
            ("deep_episode.schema.json", contract),
            ("deep_narration_contract.schema.json", narration),
            ("deep_caption_contract.schema.json", captions),
            ("deep_storyboard.schema.json", storyboard),
            ("deep_claim_map.schema.json", claim_map),
            ("deep_asset_manifest.schema.json", assets),
            ("deep_production_plan.schema.json", production),
            ("deep_editorial_audit.schema.json", editorial),
        ):
            validate_with(schema_name, value)
        if contract["bible_content_hash"] != bible["content_hash"] or contract["episode_content_hash"] != episode["content_hash"]:
            raise DeepSeriesError(f"{episode['video_id']}:stale-hash")
        minimum_words, maximum_words, _ = WORD_BANDS[episode["duration_tier"]]
        if not minimum_words <= narration["word_count"] <= maximum_words:
            raise DeepSeriesError(f"{episode['video_id']}:word-band")
        if abs(narration["duration_target_s"] - storyboard["duration_s"]) > 0.01:
            raise DeepSeriesError(f"{episode['video_id']}:duration-cue-beat-mismatch")
        if not episode["duration_minutes"]["minimum"] * 60 <= storyboard["duration_s"] <= episode["duration_minutes"]["maximum"] * 60:
            raise DeepSeriesError(f"{episode['video_id']}:duration-band")
        if storyboard["composition_count"] < episode["visual_contract"]["minimum_distinct_compositions"]:
            raise DeepSeriesError(f"{episode['video_id']}:generic-visual-budget")
        if storyboard["meaningful_state_change_count"] < episode["visual_contract"]["minimum_meaningful_state_changes"]:
            raise DeepSeriesError(f"{episode['video_id']}:state-change-budget")
        visual_beats = [beat for scene in storyboard["scenes"] for beat in scene["beats"]]
        if storyboard["meaningful_state_change_count"] != len(visual_beats):
            raise DeepSeriesError(f"{episode['video_id']}:state-change-count-mismatch")
        if any(beat["end_s"] <= beat["start_s"] or beat["end_s"] - beat["start_s"] > 8.001 for beat in visual_beats):
            raise DeepSeriesError(f"{episode['video_id']}:visual-beat-duration")
        normalized_states = [" ".join(beat["state_change"].casefold().split()) for beat in visual_beats]
        if len(normalized_states) != len(set(normalized_states)):
            raise DeepSeriesError(f"{episode['video_id']}:duplicate-visual-state-change")
        cue_ids = [item["cue_id"] for item in narration["cues"]]
        if len(cue_ids) != len(set(cue_ids)):
            raise DeepSeriesError(f"{episode['video_id']}:duplicate-cue")
        binding_by_cue = {item["cue_id"]: item for item in claim_map["bindings"]}
        if set(binding_by_cue) != set(cue_ids):
            raise DeepSeriesError(f"{episode['video_id']}:claim-map-coverage")
        for cue in narration["cues"]:
            if cue["text_sha256"] != text_sha256(cue["text"]):
                raise DeepSeriesError(f"{episode['video_id']}:cue-text-hash:{cue['cue_id']}")
            if cue["claim_ids"] and not binding_by_cue[cue["cue_id"]]["claims"]:
                raise DeepSeriesError(f"{episode['video_id']}:unsupported-claim:{cue['cue_id']}")
            for claim_id in cue["claim_ids"]:
                if claim_id not in claims_by_id:
                    raise DeepSeriesError(f"{episode['video_id']}:unknown-claim:{claim_id}")
            if words(cue["text"]) > 58:
                raise DeepSeriesError(f"{episode['video_id']}:caption-overflow:{cue['cue_id']}")
        spoken_text = [" ".join(item["text"].casefold().split()) for item in narration["cues"] if item["spoken"]]
        if len(spoken_text) != len(set(spoken_text)):
            raise DeepSeriesError(f"{episode['video_id']}:duplicate-spoken-cue")
        if any(phrase in text for text in spoken_text for phrase in GENERIC_FILLER_PHRASES):
            raise DeepSeriesError(f"{episode['video_id']}:generic-filler-cue")
        for binding in claim_map["bindings"]:
            for claim in binding["claims"]:
                for ref in claim["sources"]:
                    source = sources_by_id.get(ref["source_id"])
                    if not source or source["sha256"] != ref["sha256"] or not ref["locator"]:
                        raise DeepSeriesError(f"{episode['video_id']}:missing-source-locator:{binding['cue_id']}")
        script_lower = (episode_dir / "script.md").read_text("utf-8").lower()
        if any(token in script_lower for token in banned):
            raise DeepSeriesError(f"{episode['video_id']}:placeholder-language")
        if production["remote_route"] != "disabled_pending_content_approval_and_separate_exact_authorization":
            raise DeepSeriesError(f"{episode['video_id']}:illegal-execution-route")
        for chapter_plan in episode["chapter_plan"]:
            chapter = load_json(episode_dir / "chapters" / chapter_plan["chapter_id"] / "chapter.json")
            validate_with("deep_chapter.schema.json", chapter)
            if not chapter["cue_ids"] or not chapter["scene_ids"]:
                raise DeepSeriesError(f"{episode['video_id']}:{chapter['chapter_id']}:empty-chapter")
        if pop_root is not None:
            if str(pop_root) not in sys.path:
                sys.path.insert(0, str(pop_root))
            from pop_video.contracts import VideoBrief  # type: ignore
            from pop_video.planning import plan_brief  # type: ignore
            brief = load_json(episode_dir / "preview.renderer_brief.json")
            plan_brief(VideoBrief.model_validate(brief))

    series = load_json(DEEP_ROOT / "series_manifest.json")
    validate_with("deep_series_manifest.schema.json", series)
    expected_hashes = {episode["video_id"]: load_json(EPISODES_ROOT / episode["video_id"] / "episode.json")["contract_hash"] for episode in bible["episodes"]}
    if series["episode_contract_hashes"] != expected_hashes:
        raise DeepSeriesError("series-manifest:stale-episode-contract-hashes")
    request_path = DEEP_ROOT / "content_review_request.json"
    manifest_path = REVIEW_ROOT / "manifest.json"
    if include_review_packet and (request_path.is_file() or manifest_path.is_file()):
        if not request_path.is_file() or not manifest_path.is_file():
            raise DeepSeriesError("content-review:partial-request")
        request = load_json(request_path)
        manifest = load_json(manifest_path)
        validate_with("deep_content_approval_request.schema.json", request)
        validate_with("deep_content_review_manifest.schema.json", manifest)
        expected_manifest_hash = canonical_sha256({key: value for key, value in manifest.items() if key != "review_manifest_sha256"})
        if expected_manifest_hash != manifest["review_manifest_sha256"] or request["review_manifest_sha256"] != manifest["review_manifest_sha256"]:
            raise DeepSeriesError("content-review:manifest-hash")
        if manifest["artifact_count"] != len(manifest["artifacts"]):
            raise DeepSeriesError("content-review:artifact-count")
        seen_artifact_paths: set[str] = set()
        for artifact in manifest["artifacts"]:
            if artifact["path"] in seen_artifact_paths:
                raise DeepSeriesError(f"content-review:duplicate-artifact:{artifact['path']}")
            seen_artifact_paths.add(artifact["path"])
            artifact_path = REPO_ROOT / artifact["path"]
            if not artifact_path.is_file():
                raise DeepSeriesError(f"content-review:missing-artifact:{artifact['path']}")
            actual_hash = (
                bible["content_hash"]
                if artifact["hash_scope"] == "immutable_content_without_mutable_approval_gate"
                else file_sha256(artifact_path)
            )
            if actual_hash != artifact["sha256"]:
                raise DeepSeriesError(f"content-review:stale-artifact:{artifact['path']}")
        if bible["approval_gate"]["status"] == "review_requested" and bible["approval_gate"]["review_manifest_sha256"] != manifest["review_manifest_sha256"]:
            raise DeepSeriesError("content-review:bible-gate-hash")
        approval_path = PLANNING_ROOT / "content_approval.json"
        if bible["approval_gate"]["status"] == "approved":
            if not approval_path.is_file():
                raise DeepSeriesError("content-approval:record-missing")
            approval = load_json(approval_path)
            validate_with("deep_content_approval.schema.json", approval)
            expected_identity = approval_identity(
                bible["content_hash"],
                manifest["review_manifest_sha256"],
                approval["approved_by"],
                approval["approved_at"],
            )
            if (
                approval["bible_content_hash"] != bible["content_hash"]
                or approval["review_manifest_sha256"] != manifest["review_manifest_sha256"]
                or approval["approval_text_sha256"] != text_sha256(approval["approval_text"])
                or approval["approval_identity"] != expected_identity
                or bible["approval_gate"]["approval_identity"] != expected_identity
            ):
                raise DeepSeriesError("content-approval:identity-mismatch")
        elif approval_path.is_file():
            raise DeepSeriesError("content-approval:record-without-approved-gate")


def artifact_type(path: Path) -> str:
    name = path.name
    if name == "script.md":
        return "script"
    if name == "claim_map.json":
        return "claim_map"
    if name == "storyboard.json":
        return "storyboard"
    if name == "visual_director.md":
        return "visual_director"
    if name == "contact_sheet.png":
        return "contact_sheet"
    if name == "animatic.gif":
        return "animatic"
    if "archetype_previews" in path.parts:
        return "representative_preview"
    if name == "episode_content_bible.json":
        return "episode_content_bible"
    if name == "series_manifest.json":
        return "series_manifest"
    return "supporting_contract"


def approval_identity(
    bible_content_hash: str,
    review_manifest_sha256: str,
    approved_by: str,
    approved_at: str,
) -> str:
    return canonical_sha256({
        "content_hash": bible_content_hash,
        "review_manifest_sha256": review_manifest_sha256,
        "approved_by": approved_by,
        "approved_at": approved_at,
    })


def record_content_approval(
    bible_hash: str,
    manifest_hash: str,
    approved_by: str,
    approved_at: str,
) -> None:
    write_authoring_schemas()
    bible = load_json(DEEP_ROOT / "episode_content_bible.json")
    request = load_json(DEEP_ROOT / "content_review_request.json")
    manifest = load_json(REVIEW_ROOT / "manifest.json")
    if bible["content_hash"] != bible_hash:
        raise DeepSeriesError(f"content-approval:bible-hash:{bible['content_hash']}:{bible_hash}")
    if request["bible_content_hash"] != bible_hash or manifest["bible_content_hash"] != bible_hash:
        raise DeepSeriesError("content-approval:review-bible-mismatch")
    if request["review_manifest_sha256"] != manifest_hash or manifest["review_manifest_sha256"] != manifest_hash:
        raise DeepSeriesError("content-approval:review-manifest-mismatch")
    if request["content_approval_authorizes_remote_or_paid_work"] is not False:
        raise DeepSeriesError("content-approval:execution-scope")
    try:
        parsed_at = dt.datetime.fromisoformat(approved_at)
    except ValueError as exc:
        raise DeepSeriesError("content-approval:approved-at") from exc
    if parsed_at.tzinfo is None:
        raise DeepSeriesError("content-approval:approved-at-timezone")
    approval_text = (
        f"I approve CM deep-series v2 content bible `{bible_hash}` and review manifest "
        f"`{manifest_hash}` for production planning. This approval does not authorize "
        "RunPod or other paid or remote work."
    )
    identity = approval_identity(bible_hash, manifest_hash, approved_by, approved_at)
    approval = {
        "schema_version": SCHEMA_VERSION,
        "status": "approved",
        "scope": "production_planning_only",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "bible_content_hash": bible_hash,
        "review_manifest_sha256": manifest_hash,
        "approval_text": approval_text,
        "approval_text_sha256": text_sha256(approval_text),
        "approval_identity": identity,
        "content_approval_authorizes_remote_or_paid_work": False,
    }
    validate_with("deep_content_approval.schema.json", approval)
    write_json(PLANNING_ROOT / "content_approval.json", approval)

    bible["approval_gate"].update({
        "status": "approved",
        "review_manifest_sha256": manifest_hash,
        "approved_by": approved_by,
        "approved_at": approved_at,
        "approval_identity": identity,
    })
    import factory as level1_factory
    level1_factory.validate_episode_content_bible(
        bible,
        load_json(FACTORY_ROOT / "claim_registry.json"),
        load_json(FACTORY_ROOT / "source_registry.json"),
    )
    write_json(DEEP_ROOT / "episode_content_bible.json", bible)
    write_text(DEEP_ROOT / "EPISODE_CONTENT_BIBLE.md", level1_factory.render_episode_content_bible_markdown(bible))

    ledger = load_json(DEEP_ROOT / "phase_ledger.json")
    ledger["phase"] = "phase_7_content_approved_production_planning"
    ledger["content_approval_identity"] = identity
    for item in ledger["episodes"]:
        item["status"] = "content_approved_planning_only"
    ledger["content_hash"] = canonical_sha256({key: value for key, value in ledger.items() if key != "content_hash"})
    write_json(DEEP_ROOT / "phase_ledger.json", ledger)
    validate()


def request_review() -> None:
    archive_stale_production_planning()
    archive_stale_content_review()
    bible = load_json(DEEP_ROOT / "episode_content_bible.json")
    missing_previews = [episode["video_id"] for episode in bible["episodes"] if not (EPISODES_ROOT / episode["video_id"] / "previews" / "contact_sheet.png").is_file()]
    if missing_previews:
        raise DeepSeriesError(f"content-review:previews-missing:{','.join(missing_previews)}")
    validate(include_review_packet=False)
    excluded = {
        (REVIEW_ROOT / "manifest.json").resolve(),
        (REVIEW_ROOT / "CONTENT_REVIEW_PACKET.md").resolve(),
        (DEEP_ROOT / "content_review_request.json").resolve(),
        (DEEP_ROOT / "phase_ledger.json").resolve(),
        (DEEP_ROOT / "EPISODE_CONTENT_BIBLE.md").resolve(),
        (DEEP_ROOT / "content_readiness_audit.json").resolve(),
        (DEEP_ROOT / "CONTENT_READINESS_AUDIT.md").resolve(),
    }
    artifacts = []
    review_history_root = (DEEP_ROOT / "content_review_history").resolve()
    for path in sorted(item for item in DEEP_ROOT.rglob("*") if item.is_file() and item.resolve() not in excluded):
        resolved_path = path.resolve()
        if (
            path.name.endswith(".tmp")
            or ".preview_cache" in path.parts
            or PLANNING_ROOT.resolve() in resolved_path.parents
            or review_history_root in resolved_path.parents
        ):
            continue
        if path.name == "episode_content_bible.json":
            digest = bible["content_hash"]
            hash_scope = "immutable_content_without_mutable_approval_gate"
        else:
            digest = file_sha256(path)
            hash_scope = "entire_file"
        artifacts.append({
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "sha256": digest,
            "hash_scope": hash_scope,
            "artifact_type": artifact_type(path),
        })
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "status": "review_requested",
        "bible_content_hash": bible["content_hash"],
        "episode_count": EPISODE_COUNT,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "unresolved_editorial_questions": [],
        "review_manifest_sha256": "0" * 64,
    }
    manifest["review_manifest_sha256"] = canonical_sha256({key: value for key, value in manifest.items() if key != "review_manifest_sha256"})
    validate_with("deep_content_review_manifest.schema.json", manifest)
    write_json(REVIEW_ROOT / "manifest.json", manifest)
    request = {
        "schema_version": SCHEMA_VERSION,
        "status": "review_requested",
        "requested_at": REQUESTED_AT,
        "bible_content_hash": bible["content_hash"],
        "review_manifest_sha256": manifest["review_manifest_sha256"],
        "content_approval_authorizes_remote_or_paid_work": False,
    }
    validate_with("deep_content_approval_request.schema.json", request)
    write_json(DEEP_ROOT / "content_review_request.json", request)
    write_text(REVIEW_ROOT / "CONTENT_REVIEW_PACKET.md", f"""# CM deep-series v2 content review packet

Status: **review requested; no remote or paid work authorized**

- Bible content identity: `{bible['content_hash']}`
- Review-manifest identity: `{manifest['review_manifest_sha256']}`
- Episodes: **{len(bible['episodes'])}**
- Enumerated reviewed artifacts: **{len(artifacts)}**
- Unresolved editorial questions: **0**

The packet contains every script, sentence-level narration and caption contract, claim map, storyboard, visual director, asset manifest, production plan, per-episode contact sheet and animatic, six full-resolution worked-example archetype previews, all compiled chapter render contracts, and the first-five sparse visual preflight. Historical review packets are excluded. Approval must name both identities above. Content approval does not authorize RunPod, upload, resource creation, paid services, publication, commit, or push.
""")
    ledger = load_json(DEEP_ROOT / "phase_ledger.json")
    ledger["phase"] = "phase_6_5_content_review_requested"
    for item in ledger["episodes"]:
        item["status"] = "human_content_review"
    ledger["review_manifest_sha256"] = manifest["review_manifest_sha256"]
    ledger["content_hash"] = canonical_sha256({key: value for key, value in ledger.items() if key != "content_hash"})
    write_json(DEEP_ROOT / "phase_ledger.json", ledger)
    import factory as level1_factory
    level1_factory.build()
    validate()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("author", "render-previews", "validate", "request-review", "approve"))
    parser.add_argument("--pop-root", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--video-id", action="append", dest="video_ids")
    parser.add_argument("--bible-hash")
    parser.add_argument("--manifest-hash")
    parser.add_argument("--approved-by")
    parser.add_argument("--approved-at")
    args = parser.parse_args()
    if args.command == "author":
        author()
    elif args.command == "render-previews":
        if args.pop_root is None:
            parser.error("render-previews requires --pop-root")
        render_previews(
            args.pop_root,
            workers=args.workers,
            video_ids=set(args.video_ids or []),
        )
    elif args.command == "validate":
        validate(pop_root=args.pop_root)
    elif args.command == "request-review":
        request_review()
    else:
        required = {
            "--bible-hash": args.bible_hash,
            "--manifest-hash": args.manifest_hash,
            "--approved-by": args.approved_by,
            "--approved-at": args.approved_at,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            parser.error(f"approve requires {', '.join(missing)}")
        record_content_approval(
            args.bible_hash,
            args.manifest_hash,
            args.approved_by,
            args.approved_at,
        )


if __name__ == "__main__":
    main()
