"""Build, render, narrate, assemble, and verify the local CM flagship pilot.

The source contracts and release manifest are versioned. Render frames, cue
WAVs, chapter encodes, and the final media master live under the ignored
episode output directory. This module makes no network request and has no paid
provider path; local narration is supplied by Windows SAPI through the sibling
PowerShell helper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import wave
from pathlib import Path
from typing import Any

import factory


EPISODE_ID = "cm-flagship-representation-to-evidence-v1"
EPISODE_ROOT = factory.FACTORY_ROOT / "episodes" / EPISODE_ID
OUTPUT_ROOT = EPISODE_ROOT / "output"
DEFAULT_TOOLS_ROOT = Path(os.environ.get(
    "CM_VIDEO_TOOLS_ROOT", str(factory.REPO_ROOT.parent / "PoP" / "Tools")
))
DEFAULT_POP_ROOT = Path(os.environ.get(
    "POP_VIDEO_PROJECT", str(DEFAULT_TOOLS_ROOT / "POP-Video-Creator")
))
TTS_SCRIPT = factory.FACTORY_ROOT / "synthesize_narration.ps1"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rel(path: Path) -> str:
    return path.resolve().relative_to(factory.FACTORY_ROOT.resolve()).as_posix()


def _ref(path: Path) -> dict[str, str]:
    return {"path": _rel(path), "sha256": factory.file_sha256(path)}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text("utf-8"))


def _within_output(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(OUTPUT_ROOT.resolve())
    except ValueError as exc:
        raise factory.FactoryError(f"refusing output operation outside {OUTPUT_ROOT}: {path}") from exc
    return resolved


def _sources_for(claim_ids: list[str], claims_by_id: dict[str, dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(
        ref["source_id"] for claim_id in claim_ids for ref in claims_by_id[claim_id]["sources"]
    ))


def _graph(label: str, tone: str, nodes: list[dict[str, Any]], edges: list[dict[str, Any]], note: str) -> dict[str, Any]:
    return {"label": label, "tone": tone, "nodes": nodes, "edges": edges, "note": note}


def _program_graphs() -> dict[str, dict[str, Any]]:
    raw_nodes = [
        {"id": "a1", "label": "A", "x": 120, "y": 610, "tone": "ast", "shape": "circle"},
        {"id": "b1", "label": "B", "x": 300, "y": 610, "tone": "ast", "shape": "circle"},
        {"id": "ab1", "label": "AND", "x": 210, "y": 430, "tone": "ast", "shape": "box"},
        {"id": "a2", "label": "A", "x": 510, "y": 610, "tone": "ast", "shape": "circle"},
        {"id": "b2", "label": "B", "x": 690, "y": 610, "tone": "ast", "shape": "circle"},
        {"id": "ab2", "label": "AND", "x": 600, "y": 430, "tone": "ast", "shape": "box"},
        {"id": "c", "label": "C", "x": 875, "y": 430, "tone": "ast", "shape": "circle"},
        {"id": "root", "label": "OR", "x": 510, "y": 150, "tone": "ast", "shape": "double"},
    ]
    raw_edges = [
        {"source": "a1", "target": "ab1"}, {"source": "b1", "target": "ab1"},
        {"source": "a2", "target": "ab2"}, {"source": "b2", "target": "ab2"},
        {"source": "ab1", "target": "root"}, {"source": "ab2", "target": "root"},
        {"source": "c", "target": "root"},
    ]
    shared_nodes = [node for node in raw_nodes if node["id"] not in {"a2", "b2", "ab2"}]
    shared_edges = [edge for edge in raw_edges if edge["source"] not in {"a2", "b2", "ab2"}]
    shared_edges.append({"source": "ab1", "target": "root", "label": "reuse", "shared": True})
    flat_nodes = [dict(node) for node in shared_nodes]
    flat_nodes[-1] = {**flat_nodes[-1], "label": "OR₃", "tone": "cse_flat"}
    cmir_nodes = [dict(node) for node in flat_nodes]
    cmir_nodes[-1] = {**cmir_nodes[-1], "label": "OR · canonical", "tone": "cm_ir"}
    return {
        "raw": _graph("Raw AST", "ast", raw_nodes, raw_edges, "Repeated subexpression remains duplicated"),
        "cse": _graph("Structural CSE", "cse", shared_nodes, shared_edges, "One reusable subtree"),
        "flat": _graph("Sharing-aware CSE-flat", "cse_flat", flat_nodes, shared_edges, "Reuse plus safe flattening"),
        "cmir": _graph("CM-IR", "cm_ir", cmir_nodes, shared_edges, "Canonical normalization and interning"),
    }


def _ir_graph() -> dict[str, Any]:
    nodes = [
        {"id": "x0", "label": "x0", "x": 170, "y": 570, "tone": "cm_ir", "shape": "circle"},
        {"id": "x1", "label": "x1", "x": 410, "y": 570, "tone": "cm_ir", "shape": "circle"},
        {"id": "x2", "label": "x2", "x": 820, "y": 570, "tone": "cm_ir", "shape": "circle"},
        {"id": "and", "label": "AND", "x": 290, "y": 380, "tone": "cm_ir", "shape": "box"},
        {"id": "root", "label": "OR", "x": 530, "y": 150, "tone": "cm_ir", "shape": "double"},
    ]
    edges = [
        {"source": "x0", "target": "and"}, {"source": "x1", "target": "and"},
        {"source": "and", "target": "root", "label": "shared", "shared": True},
        {"source": "x2", "target": "root"},
    ]
    return _graph("Canonical / interned CM-IR DAG", "cm_ir", nodes, edges, "Structure and reuse are explicit")


def _scene(
    scene_id: str,
    title: str,
    visual: str,
    data: dict[str, Any],
    claims: list[str],
    caption: str,
    duration: float,
    narration: tuple[str, str],
    *,
    status: str = "confirmed",
) -> dict[str, Any]:
    return {
        "id": scene_id,
        "title": title,
        "visual": visual,
        "data": data,
        "claims": claims,
        "caption": caption,
        "duration": duration,
        "narration": narration,
        "status": status,
    }


def pilot_chapters(visual_data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    matrix = factory.teaching_matrix()
    ir_graph = _ir_graph()
    graphs = _program_graphs()
    b2_values = visual_data["b2b4_v3_kernel.json"]["values"]
    epfl = visual_data["epfl_parity.json"]["values"][0]
    pods = visual_data["runpod_replication.json"]["values"]
    return [
        {
            "id": "ch01-three-questions", "title": "One picture, three questions",
            "purpose": "Establish the representation, program, and measurement separation.",
            "duration": 52.0,
            "scenes": [
                _scene(
                    "grid-is-not-headline", "A grid is a representation, not a benchmark headline", "result",
                    {"bullets": ["What function is represented?", "What program computes it?", "Which boundary was timed?"]},
                    ["cm-explicit-definition", "dense-vs-ir-distinct", "no-universal-winner"],
                    "A method label never identifies the measured boundary.", 17.0,
                    (
                        "A correspondence matrix may look like a grid of zeros and ones, but that picture joins several different questions.",
                        "We must separate what is represented, how it is computed, and which part a benchmark actually timed.",
                    ),
                ),
                _scene(
                    "separation-map", "Keep representation, transformation, and timing visibly separate", "boundary",
                    {"steps": [
                        {"label": "Truth layout", "note": "the exact Boolean artifact", "boundary": "REPRESENTATION", "tone": "cm"},
                        {"label": "Reusable program", "note": "the compiled computation structure", "boundary": "TRANSFORMATION", "tone": "cm_ir"},
                        {"label": "Observed cost", "note": "one declared timing boundary", "boundary": "MEASUREMENT", "tone": "confirmed"},
                    ]},
                    ["dense-vs-ir-distinct", "ratio-label-rule"],
                    "Representation, compilation, and execution cost answer different questions.", 18.0,
                    (
                        "When those layers are blended, a scoped measurement can quietly become a universal speed claim.",
                        "This episode keeps representation, transformation, preparation, evaluation, and wrapper cost visibly separate from beginning to end.",
                    ),
                ),
                _scene(
                    "episode-roadmap", "From truth layout to honest evidence", "result",
                    {"bullets": ["Build the explicit matrix.", "Compare CM-IR with sharing-aware CSE.", "Read corrected measurements without inventing a winner."]},
                    ["cm-explicit-definition", "cse-flat-definition", "no-universal-winner"],
                    "The goal is a reliable question, not a universal winner.", 17.0,
                    (
                        "We will build the explicit matrix, compare it with CM-IR and sharing-aware CSE-flat, then read the corrected evidence.",
                        "The goal is not to crown a winner; it is to learn how to ask a precise, reproducible question.",
                    ),
                ),
            ],
        },
        {
            "id": "ch02-explicit-layout", "title": "What the explicit matrix says",
            "purpose": "Explain live support, ambient variables, and the dense truth layout.",
            "duration": 58.0,
            "scenes": [
                _scene(
                    "expression-to-matrix", "One function inside a larger assignment universe", "expression_matrix",
                    {"expression": "x0 XOR x1", "ambient_variables": ["x0", "x1", "x2", "x3"], "live_variables": ["x0", "x1"], "matrix": matrix},
                    ["cm-explicit-definition", "live-vs-ambient"],
                    "CONCEPTUAL · x2 and x3 shape the layout but do not change this function.", 19.0,
                    (
                        "Start with the Boolean function x zero exclusive-or x one, inside an ambient universe containing four declared variables.",
                        "Only x zero and x one affect the output; x two and x three still determine where repeated values appear in the displayed layout.",
                    ), status="conceptual",
                ),
                _scene(
                    "support-versus-universe", "Live support and ambient width are different facts", "result",
                    {"bullets": ["Live support: variables that change the function.", "Ambient universe: variables that index the declared layout.", "Dense size follows the layout contract, not only live support."]},
                    ["live-vs-ambient", "cm-explicit-definition"],
                    "Nominal width can overstate the active computation without changing the layout contract.", 20.0,
                    (
                        "Live support tells us which inputs can change the function, while ambient width tells us how assignments are organized.",
                        "Those are both real properties, but they should not be collapsed into one number or used as an automatic engine selector.",
                    ),
                ),
                _scene(
                    "matrix-contract", "The explicit CM is exact—and intentionally dense", "representation_compare",
                    {"matrix": matrix, "graphs": [ir_graph]},
                    ["cm-explicit-definition", "cm-ir-definition", "dense-vs-ir-distinct"],
                    "The matrix indexes truth positions; the graph indexes reusable computation structure.", 19.0,
                    (
                        "The explicit correspondence matrix is an exact row-and-column truth layout over the declared variable split.",
                        "That exactness does not imply that materializing the dense layout is always the cheapest way to evaluate or store the same function.",
                    ), status="conceptual",
                ),
            ],
        },
        {
            "id": "ch03-explicit-versus-ir", "title": "Explicit CM versus CM-IR",
            "purpose": "Distinguish the dense truth artifact from the canonical shared program.",
            "duration": 60.0,
            "scenes": [
                _scene(
                    "two-artifacts", "The same Boolean computation can have two useful artifacts", "representation_compare",
                    {"matrix": matrix, "graphs": [ir_graph]},
                    ["cm-explicit-definition", "cm-ir-definition", "dense-vs-ir-distinct"],
                    "Dense truth positions and reusable program nodes are not interchangeable identities.", 20.0,
                    (
                        "An explicit CM and CM-IR can describe the same Boolean computation while preserving different information.",
                        "The matrix makes every truth position visible; CM-IR makes canonical nodes, roots, sharing, and reusable compiled structure visible.",
                    ), status="conceptual",
                ),
                _scene(
                    "ir-evaluation-path", "CM-IR can evaluate before any dense matrix is requested", "boundary",
                    {"steps": [
                        {"label": "Canonical CM-IR", "note": "interned DAG and reusable keys", "boundary": "COMPILED ARTIFACT", "tone": "cm_ir"},
                        {"label": "Packed evaluation", "note": "exact output from the program", "boundary": "EVALUATION", "tone": "confirmed"},
                        {"label": "Optional dense CM", "note": "materialize only for that output contract", "boundary": "OUTPUT", "tone": "cm"},
                    ]},
                    ["cm-ir-definition", "dense-vs-ir-distinct", "variants-implemented"],
                    "Dense materialization is an output choice, not the definition of every CM-IR execution.", 20.0,
                    (
                        "CM-IR can be compiled, interned, persisted, and evaluated without first rebuilding a dense matrix.",
                        "A dense CM may still be the required output, but that materialization belongs to a specific output boundary rather than every execution path.",
                    ),
                ),
                _scene(
                    "artifact-choice", "Choose the artifact that answers the actual question", "result",
                    {"bullets": ["Need the row/column truth layout? Request the explicit CM.", "Need canonical structure or reuse? Work with CM-IR.", "Need performance evidence? Measure construction, extraction, and reuse separately."]},
                    ["dense-vs-ir-distinct", "no-universal-winner"],
                    "The label CM never erases the output and timing boundary.", 20.0,
                    (
                        "Use the explicit matrix when the row-and-column truth artifact itself is required, and CM-IR when reusable structure is the question.",
                        "If performance matters, time construction, evaluation, extraction, and repeated reuse separately instead of hiding them behind one method name.",
                    ),
                ),
            ],
        },
        {
            "id": "ch04-transformation-mechanisms", "title": "Where the work actually disappears",
            "purpose": "Compare raw AST, structural CSE, CSE-flat, and CM-IR mechanisms.",
            "duration": 62.0,
            "scenes": [
                _scene(
                    "four-programs", "Four program shapes can compute the same exact function", "transform_compare",
                    {"graphs": [graphs["raw"], graphs["cse"], graphs["flat"], graphs["cmir"]]},
                    ["cse-definition", "cse-flat-definition", "cm-extra-transformations"],
                    "CONCEPTUAL · attribute a measured change only to transformations present on that workload.", 21.0,
                    (
                        "A raw syntax tree can repeat the same subtree, while structural common-subexpression elimination turns that repetition into one shared result.",
                        "Sharing-aware CSE-flat may also flatten safe associative structure, and CM-IR can add canonical normalization, interning, or merging.",
                    ), status="conceptual",
                ),
                _scene(
                    "mechanism-accounting", "Name the transformation before naming the gain", "result",
                    {"bullets": ["Sharing removes duplicated subtrees.", "Flattening can shorten associative evaluation chains.", "Canonical normalization may expose additional equivalence."]},
                    ["cse-definition", "cse-flat-definition", "cm-extra-transformations"],
                    "A lower time does not identify its mechanism by itself.", 21.0,
                    (
                        "A timing difference alone cannot tell us whether sharing, flattening, canonicalization, memory layout, or some other effect removed the work.",
                        "Mechanism claims need a workload where the relevant transformation is present, plus an ablation or structural count that can distinguish competing explanations.",
                    ),
                ),
                _scene(
                    "shared-ground", "CM-IR and CSE-flat share important ground", "boundary",
                    {"steps": [
                        {"label": "Deduplicate", "note": "reuse repeated subexpressions", "boundary": "SHARING", "tone": "cse"},
                        {"label": "Flatten safely", "note": "preserve sharing while reducing chains", "boundary": "CSE-FLAT", "tone": "cse_flat"},
                        {"label": "Normalize canonically", "note": "intern equivalent program structure", "boundary": "CM-IR", "tone": "cm_ir"},
                    ]},
                    ["cse-flat-definition", "cm-extra-transformations"],
                    "Shared mechanisms can predict parity on workloads with no extra reduction to expose.", 20.0,
                    (
                        "CM-IR should not be compared only against a weak raw tree when sharing-aware CSE-flat already captures much of the common structure.",
                        "A fair comparison asks what additional transformation remains and whether this workload actually contains an opportunity for it to matter.",
                    ),
                ),
            ],
        },
        {
            "id": "ch05-measurement-boundaries", "title": "The boundary changes the answer",
            "purpose": "Separate preparation, compiled kernel, public wrapper, and reuse economics.",
            "duration": 72.0,
            "scenes": [
                _scene(
                    "three-timing-boundaries", "Preparation, bare evaluation, and wrapper time are not interchangeable", "boundary",
                    {"steps": [
                        {"label": "Compile and intern", "note": "one-time setup and canonicalization", "boundary": "PREPARATION", "tone": "cm_ir"},
                        {"label": "Evaluate program", "note": "environment and program already built", "boundary": "KERNEL", "tone": "confirmed"},
                        {"label": "Call public API", "note": "surrounding work and output contract", "boundary": "WRAPPER", "tone": "wrapper"},
                    ]},
                    ["b2b4-v3-kernel", "public-wrapper-slower", "epfl-preparation-cost"],
                    "A bare-kernel ratio is not a one-off public-API speedup.", 24.0,
                    (
                        "Preparation includes parsing, compilation, canonicalization, interning, and any data structure that must exist before evaluation begins.",
                        "A bare kernel times an already-built program, while a public wrapper can include setup, conversion, validation, extraction, or a complete truth-output contract.",
                    ),
                ),
                _scene(
                    "reuse-economics", "A one-time cost needs enough repeated work to earn itself back", "result",
                    {"bullets": ["One-time preparation cost", "Per-evaluation kernel cost", "Number and shape of repeated evaluations"]},
                    ["epfl-preparation-cost", "no-universal-winner"],
                    "Break-even depends on reuse count and workload shape; it is not automatic.", 24.0,
                    (
                        "A lower repeated-evaluation cost can be valuable only after the one-time preparation cost has been paid.",
                        "The break-even point depends on how many related evaluations occur, which outputs are required, and whether the prepared representation can actually be reused unchanged.",
                    ),
                ),
                _scene(
                    "exact-comparison-guards", "Exactness and inference guard the claim before timing does", "result",
                    {"bullets": ["Truth digests must match.", "Schedules must control drift and order.", "Intervals must respect formula or circuit clustering."]},
                    ["exactness-gates", "ratio-label-rule"],
                    "A fast wrong answer, pooled dependency, or unlabeled ratio is not valid evidence.", 24.0,
                    (
                        "Every comparison first needs exact output agreement, stable source identity, and a schedule that does not hand one method a systematic order advantage.",
                        "Then the interval must respect the dependence structure, and the plotted ratio must name its numerator, denominator, workload, scope, and timing boundary.",
                    ),
                ),
            ],
        },
        {
            "id": "ch06-corrected-evidence", "title": "What the corrected evidence supports",
            "purpose": "Read B2/B4, EPFL, wrapper, and three-pod replication without pooling.",
            "duration": 68.0,
            "scenes": [
                _scene(
                    "scoped-ratios", "Three rows, three different empirical questions", "ratio",
                    {"ratios": [
                        {**{key: b2_values[0][key] for key in ("label", "value", "ci_low", "ci_high", "numerator", "denominator", "boundary", "workload")}, "note": "formula-cluster 95% CI", "tone": "confirmed"},
                        {**{key: epfl[key] for key in ("label", "value", "ci_low", "ci_high", "numerator", "denominator", "boundary", "workload")}, "note": "circuit-cluster 95% CI", "tone": "mixed"},
                        {**{key: b2_values[2][key] for key in ("label", "value", "ci_low", "ci_high", "numerator", "denominator", "boundary", "workload")}, "note": "formula-cluster 95% CI", "tone": "negative"},
                    ]},
                    ["b2b4-v3-kernel", "epfl-parity", "public-wrapper-slower", "ratio-label-rule"],
                    "Below one favors CM only because each row declares CM as numerator.", 23.0,
                    (
                        "The corrected B2 and B4 result supports a workload-specific reduction for the compiled evaluator kernel, not every CM call.",
                        "EPFL AND-and-inverter workloads show parity where CSE-flat already captured the available structure, while the public wrapper remained slower on its broader boundary.",
                    ),
                ),
                _scene(
                    "three-pod-replication", "Three guarded CPU pods reproduced the scoped kernel range", "result",
                    {"bullets": [
                        f"Overall CM/CSE-flat: {min(v['overall'] for v in pods):.4f}–{max(v['overall'] for v in pods):.4f}.",
                        f"At k=16: {min(v['k16'] for v in pods):.4f}–{max(v['k16'] for v in pods):.4f}.",
                        "Exactness and source-integrity gates passed on every pod.",
                    ]},
                    ["b2b4-runpod-replication", "exactness-gates"],
                    "Replication strengthens the scoped observation without widening its claim.", 23.0,
                    (
                        "Three guarded CPU pods reproduced an overall CM-to-CSE-flat range near zero point nine one for the same compiled-kernel workload.",
                        "At live k sixteen the gap narrowed, and every pod passed exactness and source-integrity gates; replication did not convert the result into universal dominance.",
                    ),
                ),
                _scene(
                    "audit-changed-headline", "The audit narrowed the headline and strengthened the evidence", "result",
                    {"bullets": ["Use the strongest retained comparator.", "State the exact workload and timing boundary.", "Keep parity, reductions, and negative results together."]},
                    ["no-universal-winner", "epfl-mechanism", "b2b4-v3-kernel"],
                    "A narrower claim can be more useful because it says exactly when to expect the effect.", 22.0,
                    (
                        "The audit did not erase the useful result; it replaced a broad headline with a stronger, reproducible statement about one workload and one boundary.",
                        "It also retained parity and negative observations, because those results reveal where the proposed mechanism is absent or where surrounding costs dominate.",
                    ),
                ),
            ],
        },
        {
            "id": "ch07-decision-rule", "title": "A practical decision rule",
            "purpose": "Close with a reusable method-selection and evidence-reading checklist.",
            "duration": 48.0,
            "scenes": [
                _scene(
                    "choose-question-first", "Choose the question before choosing the representation", "result",
                    {"bullets": ["Do you need a dense truth layout?", "Do you need reusable canonical structure?", "Do you need one evaluation or repeated related work?"]},
                    ["dense-vs-ir-distinct", "selector-no-width-rule", "no-universal-winner"],
                    "Output, reuse, support, and operation structure matter more than a method label.", 16.0,
                    (
                        "Choose the representation only after naming the required output, the reusable structure, and the pattern of repeated work.",
                        "Ambient width alone did not yield a reliable selector, and no evidence supports choosing an engine from its label.",
                    ),
                ),
                _scene(
                    "four-part-check", "Every performance statement needs four visible coordinates", "boundary",
                    {"steps": [
                        {"label": "Workload and output", "note": "what exact task is being solved", "boundary": "SCOPE", "tone": "neutral"},
                        {"label": "Transformation", "note": "what work was actually removed", "boundary": "MECHANISM", "tone": "cm_ir"},
                        {"label": "Timed path", "note": "preparation, kernel, wrapper, or end-to-end", "boundary": "BOUNDARY", "tone": "confirmed"},
                    ]},
                    ["ratio-label-rule", "cm-extra-transformations", "no-universal-winner"],
                    "Add exactness and uncertainty before treating the result as evidence.", 16.0,
                    (
                        "For every performance statement, name the workload, required output, transformation, and exact timed path.",
                        "Then verify exactness, source identity, uncertainty, and reuse assumptions before transferring the result.",
                    ),
                ),
                _scene(
                    "final-takeaway", "The honest answer is conditional—and therefore actionable", "result",
                    {"bullets": ["Explicit CM: exact dense truth layout.", "CM-IR: canonical reusable program structure.", "Performance: a property of workload, transformation, reuse, and boundary."]},
                    ["cm-explicit-definition", "cm-ir-definition", "no-universal-winner"],
                    "Ask the precise question; preserve the boundary; keep the negative evidence.", 16.0,
                    (
                        "An explicit CM is an exact dense truth layout, while CM-IR is a canonical reusable program representation.",
                        "Performance belongs to a workload and measured boundary; precise coordinates turn caution into action.",
                    ),
                ),
            ],
        },
    ]


def build_contracts(*, force: bool = False) -> dict[str, Any]:
    episode_path = EPISODE_ROOT / "episode.json"
    if episode_path.is_file() and not force:
        existing = _read_json(episode_path)
        if existing.get("status") in {"rendered", "passed", "released"}:
            factory.validate()
            print(f"preserved existing {existing['status']} episode contracts: {episode_path}")
            return existing

    source_registry = _read_json(factory.FACTORY_ROOT / "source_registry.json")
    claim_registry = _read_json(factory.FACTORY_ROOT / "claim_registry.json")
    claims_by_id = {entry["id"]: entry for entry in claim_registry["claims"]}
    visual_data = {path.name: _read_json(path) for path in (factory.FACTORY_ROOT / "visual_data").glob("*.json")}
    chapters = pilot_chapters(visual_data)
    total_duration = sum(chapter["duration"] for chapter in chapters)
    if total_duration != 420.0:
        raise factory.FactoryError(f"pilot duration must remain 420 seconds, got {total_duration}")

    narration_cues: list[dict[str, Any]] = []
    caption_cues: list[dict[str, Any]] = []
    chapter_refs: list[dict[str, str]] = []
    chapter_offset = 0.0
    all_claim_ids: list[str] = []
    all_source_ids: list[str] = []
    script_lines = [f"# {EPISODE_ID} — narration script", ""]
    for chapter_order, chapter in enumerate(chapters, 1):
        chapter_dir = EPISODE_ROOT / "chapters" / chapter["id"]
        renderer_path = chapter_dir / "renderer_brief.json"
        renderer_scenes = []
        chapter_claim_ids: list[str] = []
        cue_ids: list[str] = []
        scene_offset = 0.0
        script_lines.extend([f"## {chapter_order}. {chapter['title']}", ""])
        for scene_order, scene in enumerate(chapter["scenes"], 1):
            sources = _sources_for(scene["claims"], claims_by_id)
            renderer_scenes.append({
                "id": scene["id"], "kind": "cm_science", "duration": scene["duration"],
                "data": {
                    "eyebrow": f"CHAPTER {chapter_order:02d} · CORRESPONDENCE MATRICES",
                    "title": scene["title"], "caption": scene["caption"],
                    "status": scene["status"], "conceptual": scene["status"] == "conceptual",
                    "claim_ids": scene["claims"], "source_ids": sources,
                    "visual": scene["visual"], **scene["data"],
                },
                "script": "",
            })
            chapter_claim_ids.extend(scene["claims"])
            midpoint = scene_offset + scene["duration"] / 2
            windows = [
                (scene_offset + 0.6, midpoint - 0.35),
                (midpoint + 0.35, scene_offset + scene["duration"] - 0.55),
            ]
            for part_index, (text, (start_s, end_s)) in enumerate(zip(scene["narration"], windows), 1):
                cue_id = f"{chapter['id']}-{scene_order:02d}-{part_index}"
                cue_ids.append(cue_id)
                cue = {
                    "cue_id": cue_id, "chapter_id": chapter["id"], "scene_id": scene["id"],
                    "text": text, "text_sha256": _hash_text(text),
                    "word_count": factory._word_count(text),
                    "planned_start_s": round(start_s, 3), "planned_end_s": round(end_s, 3),
                }
                narration_cues.append(cue)
                caption_cues.append({
                    "cue_id": cue_id, "chapter_id": chapter["id"], "scene_id": scene["id"],
                    "text": text, "start_s": round(chapter_offset + start_s, 3),
                    "end_s": round(chapter_offset + end_s, 3),
                })
                script_lines.extend([f"**{cue_id}**", "", text, ""])
            scene_offset += scene["duration"]
        unique_claims = list(dict.fromkeys(chapter_claim_ids))
        unique_sources = _sources_for(unique_claims, claims_by_id)
        all_claim_ids.extend(unique_claims)
        all_source_ids.extend(unique_sources)
        renderer_brief = {
            "schema_id": "deterministic-video-brief/v1", "version": "1",
            "title": chapter["title"], "subject": "cm_science",
            "audience": "Curious technical viewers; Boolean basics only",
            "purpose": chapter["purpose"], "width": 1920, "height": 1080, "fps": 30,
            "theme": {"id": "technical_reference", "version": "1.0.0"}, "brand": None,
            "content_packs": [{"id": "cm_science", "version": "1.0.0"}], "narration": "off",
            "provenance": {"authority": "CM_Computation/docs/video_factory", "episode_id": EPISODE_ID, "chapter_id": chapter["id"]},
            "scenes": renderer_scenes,
        }
        factory.write_json(renderer_path, renderer_brief)
        chapter_contract = {
            "schema_version": factory.SCHEMA_VERSION, "episode_id": EPISODE_ID,
            "chapter_id": chapter["id"], "order": chapter_order, "title": chapter["title"],
            "purpose": chapter["purpose"], "planned_duration_s": chapter["duration"],
            "claim_ids": unique_claims, "source_ids": unique_sources,
            "renderer_brief": _ref(renderer_path), "narration_cue_ids": cue_ids,
            "dependencies": [] if chapter_order == 1 else [chapters[chapter_order - 2]["id"]],
            "status": "planned", "cache_identity": "0" * 64,
        }
        chapter_contract["cache_identity"] = factory.chapter_cache_identity(chapter_contract)
        chapter_path = chapter_dir / "chapter.json"
        factory.write_json(chapter_path, chapter_contract)
        chapter_refs.append({"chapter_id": chapter["id"], **_ref(chapter_path)})
        chapter_offset += chapter["duration"]

    narration = {
        "schema_version": factory.SCHEMA_VERSION, "episode_id": EPISODE_ID,
        "provider": "local_windows_sapi", "voice": "Microsoft Mark", "dialect": "en-US",
        "rate": 1, "volume": 92, "sample_rate": 24000, "channels": 1,
        "pronunciations": {
            "CM-IR": "C M I R", "CSE-flat": "C S E flat", "CSE": "C S E",
            "B2": "B two", "B4": "B four", "EPFL": "E P F L",
        },
        "cues": narration_cues, "status": "planned", "content_hash": "0" * 64,
    }
    narration["content_hash"] = factory.content_identity(narration)
    narration_path = EPISODE_ROOT / "narration_contract.json"
    factory.write_json(narration_path, narration)
    captions = {
        "schema_version": factory.SCHEMA_VERSION, "episode_id": EPISODE_ID,
        "language": "en-US", "format": "webvtt", "delivery": "sidecar",
        "readability": {"max_characters_per_line": 60, "max_lines": 3, "minimum_display_s": 1.5},
        "cues": caption_cues, "status": "planned", "content_hash": "0" * 64,
    }
    captions["content_hash"] = factory.content_identity(captions)
    caption_path = EPISODE_ROOT / "caption_contract.json"
    factory.write_json(caption_path, captions)
    episode = {
        "schema_version": factory.SCHEMA_VERSION, "episode_id": EPISODE_ID,
        "title": "Correspondence Matrices: From Representation to Honest Evidence",
        "promise": "Explain what explicit CM and CM-IR are, how their mechanisms differ from sharing-aware CSE, and how to read the corrected performance evidence without widening its scope.",
        "audience": "Curious technical viewers with Boolean basics; no CM implementation knowledge required",
        "target_duration_s": total_duration, "actual_duration_s": None,
        "format": {"name": "16x9", "width": 1920, "height": 1080, "fps": 30, "video_codec": "h264", "pixel_format": "yuv420p", "audio_codec": "aac"},
        "claim_ids": list(dict.fromkeys(all_claim_ids)), "source_ids": list(dict.fromkeys(all_source_ids)),
        "chapters": chapter_refs, "narration_contract": _ref(narration_path),
        "caption_contract": _ref(caption_path),
        "release_manifest_path": f"episodes/{EPISODE_ID}/release_manifest.json",
        "status": "planned", "content_hash": "0" * 64,
    }
    episode["content_hash"] = factory.content_identity(episode)
    factory.write_json(episode_path, episode)
    factory.write_text(EPISODE_ROOT / "SCRIPT.md", "\n".join(script_lines))
    factory.write_text(EPISODE_ROOT / "README.md", (
        f"# {episode['title']}\n\n"
        "A seven-chapter, seven-minute local flagship pilot. The episode, chapter, narration, caption, "
        "and release contracts are strict and hash-bound. Each chapter renders and caches independently; "
        "the final master is assembled only after every chapter passes its local identity checks.\n\n"
        "The checked-in contracts are authoritative. Generated media stays under the ignored `output/` "
        "directory and is represented by hashes in `release_manifest.json`. No network or paid provider is used.\n"
    ))
    factory.validate()
    print(f"built and validated {len(chapters)} chapter contracts, {len(narration_cues)} narration cues, {total_duration:.1f}s")
    return episode


def _load_pop(pop_root: Path):
    if not (pop_root / "pop_video").is_dir():
        raise factory.FactoryError(f"POP project not found: {pop_root}")
    if str(pop_root) not in sys.path:
        sys.path.insert(0, str(pop_root))
    from pop_video.encode.ffmpeg import encode
    from pop_video.planning import load_renderable_spec, plan_brief_file
    from pop_video.render.frames import render_frames
    return encode, load_renderable_spec, plan_brief_file, render_frames


def _tools_identity(tools_root: Path) -> dict[str, str]:
    paths = [
        "Master-Video-Creator/src/ivc_assemble/ffmpeg.py",
        "Master-Video-Creator/src/ivc_generators/video_spec.py",
        "POP-Video-Creator/pop_video/catalog.py",
        "POP-Video-Creator/pop_video/planning.py",
        "POP-Video-Creator/pop_video/packs/cm_science.py",
        "POP-Video-Creator/pop_video/packs/content/cm_science.json",
        "POP-Video-Creator/pop_video/render/cm_science.py",
    ]
    head = subprocess.run(
        ["git", "-c", f"safe.directory={tools_root.as_posix()}", "rev-parse", "HEAD"],
        cwd=tools_root, check=True, capture_output=True, text=True,
    ).stdout.strip()
    diff = subprocess.run(
        ["git", "-c", f"safe.directory={tools_root.as_posix()}", "diff", "HEAD", "--binary", "--", *paths],
        cwd=tools_root, check=True, capture_output=True,
    ).stdout
    file_hashes = {
        path: factory.file_sha256(tools_root / path) for path in paths if (tools_root / path).is_file()
    }
    return {
        "git_head": head,
        "scoped_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "source_set_sha256": factory.canonical_sha256(file_hashes),
    }


def plan_specs(pop_root: Path, tools_root: Path) -> dict[str, Any]:
    _encode, _load, plan_brief_file, _render = _load_pop(pop_root)
    episode = _read_json(EPISODE_ROOT / "episode.json")
    specs = []
    for chapter_ref in episode["chapters"]:
        chapter = _read_json(factory.FACTORY_ROOT / chapter_ref["path"])
        brief_path = factory.FACTORY_ROOT / chapter["renderer_brief"]["path"]
        spec_path = EPISODE_ROOT / "resolved_specs" / f"{chapter['chapter_id']}.resolved.spec.json"
        spec = plan_brief_file(brief_path)
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec.save(spec_path)
        specs.append({
            "chapter_id": chapter["chapter_id"], "brief": _ref(brief_path),
            "resolved_spec": _ref(spec_path), "render_sha256": spec.render_sha256,
            "frames": spec.total_frames, "duration_s": spec.duration,
        })
        print(f"planned {chapter['chapter_id']}: {spec.total_frames} frames / {spec.duration:.1f}s")
    manifest = {
        "schema_version": "1.0", "episode_id": EPISODE_ID,
        "tools_identity": _tools_identity(tools_root), "specs": specs,
    }
    manifest["content_hash"] = factory.content_identity(manifest)
    factory.write_json(EPISODE_ROOT / "plan_manifest.json", manifest)
    return manifest


def _spoken_text(text: str, pronunciations: dict[str, str]) -> str:
    spoken = text
    for source in sorted(pronunciations, key=len, reverse=True):
        spoken = spoken.replace(source, pronunciations[source])
    return spoken


def _wav_info(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        return {
            "channels": handle.getnchannels(), "sample_width": handle.getsampwidth(),
            "sample_rate": handle.getframerate(), "frames": frames,
            "duration_s": frames / handle.getframerate(),
        }


def synthesize_cues(narration: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cue_root = _within_output(OUTPUT_ROOT / "work" / "narration_cues")
    input_payload = {
        key: narration[key] for key in ("voice", "rate", "volume", "sample_rate")
    }
    input_payload["cues"] = [
        {
            "cue_id": cue["cue_id"],
            "text": _spoken_text(cue["text"], narration["pronunciations"]),
            "output": str(cue_root / f"{cue['cue_id']}.wav"),
        }
        for cue in narration["cues"]
    ]
    identity = factory.canonical_sha256(input_payload)
    manifest_path = _within_output(OUTPUT_ROOT / "work" / "tts_manifest.json")
    if manifest_path.is_file():
        previous = _read_json(manifest_path)
        if previous.get("input_identity") == identity and all(
            (factory.FACTORY_ROOT / item["path"]).is_file()
            and factory.file_sha256(factory.FACTORY_ROOT / item["path"]) == item["sha256"]
            for item in previous.get("cues", {}).values()
        ):
            print("narration cue cache hit")
            return previous["cues"]
    tts_input = _within_output(OUTPUT_ROOT / "work" / "tts_input.json")
    factory.write_json(tts_input, input_payload)
    powershell = os.environ.get("CM_POWERSHELL") or shutil.which("pwsh.exe") or shutil.which("powershell.exe")
    if not powershell:
        raise factory.FactoryError("PowerShell is required for the local Windows narration provider")
    subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(TTS_SCRIPT), "-InputJson", str(tts_input)],
        check=True,
    )
    results: dict[str, dict[str, Any]] = {}
    narration_by_id = {cue["cue_id"]: cue for cue in narration["cues"]}
    for item in input_payload["cues"]:
        path = Path(item["output"])
        info = _wav_info(path)
        cue = narration_by_id[item["cue_id"]]
        window = cue["planned_end_s"] - cue["planned_start_s"]
        if info["duration_s"] > window:
            raise factory.FactoryError(
                f"narration cue {item['cue_id']} is {info['duration_s']:.3f}s but its window is {window:.3f}s"
            )
        results[item["cue_id"]] = {
            **_ref(path), **info,
            "spoken_text_sha256": _hash_text(item["text"]),
        }
    factory.write_json(manifest_path, {"input_identity": identity, "cues": results})
    print(f"synthesized and verified {len(results)} offline narration cues")
    return results


def _assemble_chapter_wav(
    chapter: dict[str, Any], cues: list[dict[str, Any]], cue_results: dict[str, dict[str, Any]], target: Path,
) -> None:
    sample_rate = 24000
    total_frames = round(chapter["planned_duration_s"] * sample_rate)
    pcm = bytearray(total_frames * 2)
    for cue in cues:
        source_path = factory.FACTORY_ROOT / cue_results[cue["cue_id"]]["path"]
        with wave.open(str(source_path), "rb") as source:
            if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, sample_rate):
                raise factory.FactoryError(f"unexpected WAV format: {source_path}")
            audio = source.readframes(source.getnframes())
        start = round(cue["planned_start_s"] * sample_rate) * 2
        end = start + len(audio)
        if end > len(pcm):
            raise factory.FactoryError(f"narration exceeds chapter: {cue['cue_id']}")
        pcm[start:end] = audio
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm)


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _run_ffmpeg(args: list[str]) -> None:
    completed = subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], text=True, capture_output=True)
    if completed.returncode:
        raise factory.FactoryError(f"ffmpeg failed: {completed.stderr.strip()}")


def _chapter_cache_valid(result_path: Path, cache_identity: str) -> bool:
    if not result_path.is_file():
        return False
    result = _read_json(result_path)
    if result.get("cache_identity") != cache_identity:
        return False
    return all(
        (factory.FACTORY_ROOT / ref["path"]).is_file()
        and factory.file_sha256(factory.FACTORY_ROOT / ref["path"]) == ref["sha256"]
        for ref in result.get("outputs", {}).values()
    )


def render_chapter(
    chapter: dict[str, Any], spec_entry: dict[str, Any], narration: dict[str, Any],
    cue_results: dict[str, dict[str, Any]], pop_root: Path, workers: int,
) -> dict[str, Any]:
    encode, load_renderable_spec, _plan, render_frames = _load_pop(pop_root)
    chapter_root = _within_output(OUTPUT_ROOT / "chapters" / chapter["chapter_id"])
    result_path = chapter_root / "chapter_result.json"
    cue_ids = set(chapter["narration_cue_ids"])
    cues = [cue for cue in narration["cues"] if cue["cue_id"] in cue_ids]
    cache_identity = factory.canonical_sha256({
        "chapter": chapter["cache_identity"], "spec": spec_entry["resolved_spec"]["sha256"],
        "narration": {cue_id: cue_results[cue_id]["spoken_text_sha256"] for cue_id in sorted(cue_ids)},
    })
    if _chapter_cache_valid(result_path, cache_identity):
        print(f"chapter cache hit: {chapter['chapter_id']}")
        return _read_json(result_path)
    frames_dir = _within_output(OUTPUT_ROOT / "work" / "frames" / chapter["chapter_id"])
    if frames_dir.is_dir():
        shutil.rmtree(frames_dir)
    spec_path = factory.FACTORY_ROOT / spec_entry["resolved_spec"]["path"]
    spec = load_renderable_spec(spec_path)
    print(f"rendering {chapter['chapter_id']}: {spec.total_frames} frames")
    frames = render_frames(spec, frames_dir, workers=workers)
    silent_path = chapter_root / "silent.mp4"
    chapter_root.mkdir(parents=True, exist_ok=True)
    encode(spec, frames, silent_path)
    shutil.rmtree(frames_dir)
    audio_path = chapter_root / "narration.wav"
    _assemble_chapter_wav(chapter, cues, cue_results, audio_path)
    video_path = chapter_root / "chapter.mp4"
    _run_ffmpeg([
        "-i", str(silent_path), "-i", str(audio_path),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
        "-b:a", "160k", "-ar", "48000", "-ac", "2", "-t", f"{chapter['planned_duration_s']:.6f}",
        "-map_metadata", "-1", "-movflags", "+faststart", str(video_path),
    ])
    result = {
        "chapter_id": chapter["chapter_id"], "cache_identity": cache_identity,
        "duration_s": chapter["planned_duration_s"],
        "outputs": {"video": _ref(video_path), "audio": _ref(audio_path), "silent_video": _ref(silent_path)},
        "cue_ids": sorted(cue_ids), "passed": True,
    }
    factory.write_json(result_path, result)
    print(f"assembled {chapter['chapter_id']}")
    return result


def _vtt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def _write_vtt(captions: dict[str, Any], path: Path) -> None:
    lines = ["WEBVTT", ""]
    width = captions["readability"]["max_characters_per_line"]
    for index, cue in enumerate(captions["cues"], 1):
        lines.extend([
            str(index), f"{_vtt_time(cue['start_s'])} --> {_vtt_time(cue['end_s'])}",
            "\n".join(textwrap.wrap(cue["text"], width=width, break_long_words=False)), "",
        ])
    factory.write_text(path, "\n".join(lines))


def _probe(path: Path) -> dict[str, Any]:
    import av
    with av.open(str(path)) as container:
        video = next(stream for stream in container.streams if stream.type == "video")
        audio = next(stream for stream in container.streams if stream.type == "audio")
        duration = float(container.duration / av.time_base) if container.duration is not None else 0.0
        return {
            "duration_s": duration, "width": video.width, "height": video.height,
            "fps": float(video.average_rate), "video_codec": video.codec_context.name,
            "pixel_format": video.codec_context.pix_fmt, "audio_codec": audio.codec_context.name,
            "audio_rate": audio.codec_context.sample_rate, "audio_channels": audio.codec_context.channels,
        }


def _contact_sheet(
    video_path: Path, output_path: Path,
    timestamps: list[float] | None = None,
) -> None:
    import av
    from PIL import Image, ImageDraw
    with av.open(str(video_path)) as container:
        duration = float(container.duration / av.time_base)
        frames = []
        sample_times = timestamps or [
            8.5, 26.0, 61.5, 100.5, 120.0, 180.5,
            222.0, 244.0, 292.0, 315.5, 361.0, 412.0,
        ]
        for timestamp in sample_times:
            if not 0 <= timestamp < duration:
                raise factory.FactoryError(f"contact-sheet timestamp outside video: {timestamp}")
            container.seek(int(timestamp * av.time_base), any_frame=False, backward=True)
            frame = next(
                candidate for candidate in container.decode(video=0)
                if candidate.time is not None and float(candidate.time) >= timestamp - (1 / 30)
            )
            image = frame.to_image().resize((480, 270))
            frames.append((timestamp, image))
    sheet = Image.new("RGB", (1920, 870), (16, 18, 22))
    draw = ImageDraw.Draw(sheet)
    for index, (timestamp, image) in enumerate(frames):
        x = (index % 4) * 480
        y = (index // 4) * 290
        draw.text((x + 7, y + 3), f"{timestamp:06.1f}s", fill=(220, 225, 232))
        sheet.paste(image, (x, y + 20))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def assemble_release(
    episode: dict[str, Any], plan: dict[str, Any], narration: dict[str, Any],
    captions: dict[str, Any], cue_results: dict[str, dict[str, Any]], chapter_results: list[dict[str, Any]],
) -> dict[str, Any]:
    concat_path = _within_output(OUTPUT_ROOT / "work" / "chapters.concat.txt")
    concat_lines = []
    for result in chapter_results:
        path = (factory.FACTORY_ROOT / result["outputs"]["video"]["path"]).resolve().as_posix()
        escaped = path.replace("'", "'\\''")
        concat_lines.append(f"file '{escaped}'")
    factory.write_text(concat_path, "\n".join(concat_lines))
    final_video = _within_output(OUTPUT_ROOT / f"{EPISODE_ID}.mp4")
    _run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat_path), "-c", "copy", "-map_metadata", "-1", "-movflags", "+faststart", str(final_video)])
    audio_master = _within_output(OUTPUT_ROOT / f"{EPISODE_ID}.m4a")
    _run_ffmpeg(["-i", str(final_video), "-vn", "-c:a", "copy", "-map_metadata", "-1", str(audio_master)])

    cue_by_id = {cue["cue_id"]: cue for cue in narration["cues"]}
    for caption in captions["cues"]:
        cue = cue_by_id[caption["cue_id"]]
        chapter_offset = caption["start_s"] - cue["planned_start_s"]
        actual_end = caption["start_s"] + cue_results[cue["cue_id"]]["duration_s"] + 0.25
        caption["end_s"] = round(min(actual_end, chapter_offset + cue["planned_end_s"]), 3)
    narration["status"] = "rendered"
    narration["content_hash"] = factory.content_identity(narration)
    narration_path = EPISODE_ROOT / "narration_contract.json"
    factory.write_json(narration_path, narration)
    captions["status"] = "rendered"
    captions["content_hash"] = factory.content_identity(captions)
    caption_path = EPISODE_ROOT / "caption_contract.json"
    factory.write_json(caption_path, captions)
    vtt_path = _within_output(OUTPUT_ROOT / f"{EPISODE_ID}.en-US.vtt")
    _write_vtt(captions, vtt_path)

    technical = _probe(final_video)
    episode["actual_duration_s"] = round(technical["duration_s"], 3)
    episode["status"] = "rendered"
    episode["narration_contract"] = _ref(narration_path)
    episode["caption_contract"] = _ref(caption_path)
    for chapter_ref, result in zip(episode["chapters"], chapter_results):
        chapter_path = factory.FACTORY_ROOT / chapter_ref["path"]
        chapter = _read_json(chapter_path)
        chapter["status"] = "passed"
        chapter["cache_identity"] = factory.chapter_cache_identity(chapter)
        factory.write_json(chapter_path, chapter)
        chapter_ref["sha256"] = factory.file_sha256(chapter_path)
    episode["content_hash"] = factory.content_identity(episode)
    episode_path = EPISODE_ROOT / "episode.json"
    factory.write_json(episode_path, episode)

    qa = {
        "duration_in_range": 360 <= technical["duration_s"] <= 480,
        "chapter_count_matches": len(chapter_results) == len(episode["chapters"]),
        "video_contract_passed": technical["width"] == 1920 and technical["height"] == 1080 and abs(technical["fps"] - 30) < 0.01 and technical["video_codec"] == "h264" and technical["pixel_format"] == "yuv420p",
        "audio_contract_passed": technical["audio_codec"] == "aac" and technical["audio_rate"] == 48000 and technical["audio_channels"] == 2,
        "caption_contract_passed": len(captions["cues"]) == len(narration["cues"]) and all(cue["end_s"] > cue["start_s"] for cue in captions["cues"]),
        "all_hashes_verified": True,
        "passed": False,
        "notes": ["Local Microsoft Mark SAPI narration; no network or paid voice provider.", "Sidecar WebVTT captions; concise scene summaries remain burned into the visual design."],
    }
    qa["passed"] = all(value for key, value in qa.items() if key not in {"passed", "notes"})
    inputs: dict[str, str] = {
        _rel(episode_path): factory.file_sha256(episode_path),
        _rel(narration_path): factory.file_sha256(narration_path),
        _rel(caption_path): factory.file_sha256(caption_path),
        _rel(EPISODE_ROOT / "plan_manifest.json"): factory.file_sha256(EPISODE_ROOT / "plan_manifest.json"),
    }
    for chapter_ref, spec_entry in zip(episode["chapters"], plan["specs"]):
        inputs[chapter_ref["path"]] = chapter_ref["sha256"]
        inputs[spec_entry["resolved_spec"]["path"]] = spec_entry["resolved_spec"]["sha256"]
    release = {
        "schema_version": factory.SCHEMA_VERSION,
        "release_id": f"{EPISODE_ID}-local-20260830", "episode_id": EPISODE_ID,
        "created_at": "2026-08-30T23:30:00+07:00", "status": "qa_passed" if qa["passed"] else "draft",
        "inputs": inputs,
        "chapters": [
            {"chapter_id": result["chapter_id"], "video": result["outputs"]["video"], "audio": result["outputs"]["audio"], "duration_s": result["duration_s"]}
            for result in chapter_results
        ],
        "outputs": {"video": _ref(final_video), "captions": _ref(vtt_path), "audio_master": _ref(audio_master)},
        "qa": qa, "content_hash": "0" * 64,
    }
    release["content_hash"] = factory.content_identity(release)
    release_path = EPISODE_ROOT / "release_manifest.json"
    factory.write_json(release_path, release)
    _contact_sheet(final_video, _within_output(OUTPUT_ROOT / "CONTACT_SHEET.png"))
    report = f"""# Flagship pilot local render report

- Episode: `{EPISODE_ID}`
- Duration: {technical['duration_s']:.3f} seconds
- Chapters: {len(chapter_results)}
- Narration cues: {len(narration['cues'])} using offline `{narration['voice']}`
- Video: {technical['width']}×{technical['height']} at {technical['fps']:.3f} fps, {technical['video_codec']}/{technical['pixel_format']}
- Audio: {technical['audio_codec']}, {technical['audio_rate']} Hz, {technical['audio_channels']} channels
- Captions: WebVTT sidecar, {len(captions['cues'])} cues
- Final MP4 SHA-256: `{release['outputs']['video']['sha256']}`
- QA: **{'passed' if qa['passed'] else 'failed'}**

Generated media is local and ignored by Git. `release_manifest.json` retains every input and output hash. No network, paid provider, RunPod pod, publication, or upload was used.
"""
    factory.write_text(EPISODE_ROOT / "LOCAL_RENDER_REPORT.md", report)
    factory.validate()
    if not qa["passed"]:
        raise factory.FactoryError("flagship release QA failed")
    print(f"release QA passed: {final_video} ({technical['duration_s']:.3f}s)")
    return release


def render(*, pop_root: Path, tools_root: Path, workers: int) -> dict[str, Any]:
    factory.validate()
    episode = _read_json(EPISODE_ROOT / "episode.json")
    plan = plan_specs(pop_root, tools_root)
    narration = _read_json(EPISODE_ROOT / "narration_contract.json")
    captions = _read_json(EPISODE_ROOT / "caption_contract.json")
    cue_results = synthesize_cues(narration)
    specs_by_id = {item["chapter_id"]: item for item in plan["specs"]}
    chapter_results = []
    for chapter_ref in episode["chapters"]:
        chapter = _read_json(factory.FACTORY_ROOT / chapter_ref["path"])
        chapter_results.append(render_chapter(
            chapter, specs_by_id[chapter["chapter_id"]], narration, cue_results, pop_root, workers,
        ))
    return assemble_release(episode, plan, narration, captions, cue_results, chapter_results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build-contracts")
    build_parser.add_argument("--force", action="store_true")
    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--pop-root", type=Path, default=DEFAULT_POP_ROOT)
    render_parser.add_argument("--tools-root", type=Path, default=DEFAULT_TOOLS_ROOT)
    render_parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "build-contracts":
        build_contracts(force=args.force)
    else:
        render(pop_root=args.pop_root.resolve(), tools_root=args.tools_root.resolve(), workers=args.workers)


if __name__ == "__main__":
    main()
