"""Build local-only CM deep-series production-readiness and routing artifacts.

This planner consumes the exact content approval and frozen review packet.  It
does not contact a network service, read credentials, create an executable
remote batch, or authorize paid work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

import deep_series_authoring


REPO_ROOT = Path(__file__).resolve().parents[2]
FACTORY_ROOT = REPO_ROOT / "docs" / "video_factory"
DEEP_ROOT = FACTORY_ROOT / "deep_series"
EPISODES_ROOT = DEEP_ROOT / "episodes"
WP1_ROOT = DEEP_ROOT / "wp1"
PLANNING_ROOT = DEEP_ROOT / "production_planning"
REVIEW_ROOT = DEEP_ROOT / "content_review_packet"

SCHEMA_VERSION = "2.0"
PLANNER_VERSION = "1.0.0"
REPRESENTATIVE_SAMPLES = (
    ("what-is-explicit-cm", "truth-layout-and-matrix"),
    ("instruction-operations-memory", "repeated-dag-and-lowering"),
    ("configuration-models", "feature-model"),
    ("circuits", "circuit-cone"),
    ("policy-rule-systems", "policy-and-rule-revision"),
    ("recognition-c12-c16", "recognition-evidence-graph"),
)


class PlanningError(RuntimeError):
    """Raised when the approved planning inputs are inconsistent."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finalize(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result["content_hash"] = canonical_sha256(result)
    return result


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def approval_context() -> dict[str, Any]:
    deep_series_authoring.validate()
    approval_path = PLANNING_ROOT / "content_approval.json"
    if not approval_path.is_file():
        raise PlanningError("content approval record is missing")
    approval = load_json(approval_path)
    bible = load_json(DEEP_ROOT / "episode_content_bible.json")
    request = load_json(DEEP_ROOT / "content_review_request.json")
    manifest = load_json(REVIEW_ROOT / "manifest.json")
    if approval.get("status") != "approved":
        raise PlanningError("content approval is not approved")
    if approval.get("scope") != "production_planning_only":
        raise PlanningError("content approval has an unexpected scope")
    if approval.get("content_approval_authorizes_remote_or_paid_work") is not False:
        raise PlanningError("content approval must not authorize remote or paid work")
    if bible["approval_gate"]["status"] != "approved":
        raise PlanningError("content bible approval gate is not approved")
    if any(
        value != approval["bible_content_hash"]
        for value in (
            bible["content_hash"],
            request["bible_content_hash"],
            manifest["bible_content_hash"],
        )
    ):
        raise PlanningError("approved bible identity does not match the frozen packet")
    if any(
        value != approval["review_manifest_sha256"]
        for value in (
            request["review_manifest_sha256"],
            manifest["review_manifest_sha256"],
            bible["approval_gate"]["review_manifest_sha256"],
        )
    ):
        raise PlanningError("approved review-manifest identity does not match")
    if bible["approval_gate"]["approval_identity"] != approval["approval_identity"]:
        raise PlanningError("approval identity does not match the bible gate")
    return {
        "approval": approval,
        "bible": bible,
        "request": request,
        "manifest": manifest,
    }


def source_drift() -> list[dict[str, Any]]:
    registry = load_json(FACTORY_ROOT / "source_registry.json")
    drift: list[dict[str, Any]] = []
    for source in registry["sources"]:
        path = REPO_ROOT / source["path"]
        actual = file_sha256(path) if path.is_file() else None
        if actual != source["sha256"]:
            drift.append({
                "source_id": source["id"],
                "path": source["path"],
                "registered_sha256": source["sha256"],
                "current_sha256": actual,
                "effect": (
                    "The approved review packet remains frozen to the registered "
                    "identity; refresh or reconcile this live source before compiling "
                    "new render claims."
                ),
            })
    return drift


def chapter_inventory(video_id: str) -> list[dict[str, Any]]:
    chapter_root = EPISODES_ROOT / video_id / "chapters"
    results: list[dict[str, Any]] = []
    for chapter_dir in sorted(path for path in chapter_root.iterdir() if path.is_dir()):
        chapter_path = chapter_dir / "chapter.json"
        renderer_path = chapter_dir / "renderer_brief.json"
        executable_path = chapter_dir / "executable_render_contract.json"
        chapter = load_json(chapter_path)
        renderer = load_json(renderer_path)
        executable_contract = (
            load_json(executable_path) if executable_path.is_file() else None
        )
        executable = bool(
            executable_contract
            and all(
                key in executable_contract
                for key in (
                    "resolved_scenes",
                    "frame_contract",
                    "input_artifact_hashes",
                    "expected_output_contract",
                    "pop_video_brief",
                )
            )
        )
        results.append({
            "chapter_id": chapter["chapter_id"],
            "cache_identity": chapter["cache_identity"],
            "scene_ids": chapter["scene_ids"],
            "scene_count": len(chapter["scene_ids"]),
            "chapter_contract_path": relative(chapter_path),
            "chapter_contract_sha256": file_sha256(chapter_path),
            "renderer_brief_path": relative(renderer_path),
            "renderer_brief_sha256": file_sha256(renderer_path),
            "renderer_brief_status": renderer["status"],
            "executable_render_payload": executable,
            "executable_render_contract_path": (
                relative(executable_path) if executable else None
            ),
            "executable_render_contract_sha256": (
                file_sha256(executable_path) if executable else None
            ),
        })
    return results


def supporting_input_allowlist(ordered_ids: list[str]) -> list[dict[str, str]]:
    paths = [
        DEEP_ROOT / "episode_content_bible.json",
        DEEP_ROOT / "series_manifest.json",
        DEEP_ROOT / "content_review_request.json",
        REVIEW_ROOT / "manifest.json",
        PLANNING_ROOT / "content_approval.json",
        FACTORY_ROOT / "claim_registry.json",
        FACTORY_ROOT / "source_registry.json",
        FACTORY_ROOT / "glossary.json",
    ]
    for video_id in ordered_ids:
        episode_dir = EPISODES_ROOT / video_id
        paths.extend(
            episode_dir / name
            for name in (
                "episode.json",
                "narration_contract.json",
                "caption_contract.json",
                "storyboard.json",
                "claim_map.json",
                "asset_manifest.json",
                "production_plan.json",
                "preview.renderer_brief.json",
            )
        )
        for chapter_dir in sorted(
            path for path in (episode_dir / "chapters").iterdir() if path.is_dir()
        ):
            paths.extend(
                (chapter_dir / "chapter.json", chapter_dir / "renderer_brief.json")
            )
            executable_path = chapter_dir / "executable_render_contract.json"
            if executable_path.is_file():
                paths.append(executable_path)
    for path in (
        WP1_ROOT / "chapter_render_contract_manifest.json",
        FACTORY_ROOT / "schemas" / "deep_executable_chapter_render.schema.json",
    ):
        if path.is_file():
            paths.append(path)
    unique = sorted(set(paths), key=relative)
    missing = [relative(path) for path in unique if not path.is_file()]
    if missing:
        raise PlanningError(f"allowlist inputs are missing: {missing}")
    return [
        {"path": relative(path), "sha256": file_sha256(path)} for path in unique
    ]


def markdown_summary(
    approval: dict[str, Any], routing: dict[str, Any], audit: dict[str, Any]
) -> str:
    counts = routing["route_counts"]
    lines = [
        "# CM deep-series v2 production planning",
        "",
        "Status: **local planning complete; production qualification remains local and incomplete**",
        "",
        f"Approved Bible: `{approval['bible_content_hash']}`",
        "",
        f"Approved review manifest: `{approval['review_manifest_sha256']}`",
        "",
        f"Approval identity: `{approval['approval_identity']}`",
        "",
        "This package authorizes no RunPod call, upload, paid service, resource creation, or publication.",
        "",
        "## Routing result",
        "",
        f"- {routing['episode_count']} approved episodes",
        f"- {routing['chapter_count']} independently cached chapters",
        f"- {routing['storyboard_composition_count']} storyboard compositions",
        f"- {counts['local_frame_render_candidates']} focused episodes intended for local frame rendering after smoke qualification",
        f"- {counts['remote_frame_render_candidates']} core/deep episodes intended as deterministic CPU remote candidates only after qualification and separate authorization",
        "- All authoring, validation, planning, offline narration, assembly, mux, and QA remain local",
        "",
        "## Blocking infrastructure",
        "",
        (
            f"WP1 has compiled {routing['executable_chapter_render_payload_count']} of "
            f"{routing['chapter_count']} chapter render contracts. Specialized visual "
            "primitives, full-chapter smokes, narration, and mux/QA integration remain "
            "local qualification work."
        ),
        "",
        "Build and validate these local work packages in order:",
        "",
    ]
    for package in audit["work_packages"]:
        lines.append(
            f"{package['order']}. **{package['work_package_id']} — {package['title']}.** "
            f"{package['outcome']}"
        )
    lines.extend([
        "",
        "## Current readiness warnings",
        "",
    ])
    for blocker in audit["blocking_findings"]:
        lines.append(f"- {blocker}")
    smoke_path = PLANNING_ROOT / "renderer_primitive_smoke_results.json"
    if smoke_path.is_file():
        smoke = load_json(smoke_path)
        lines.extend([
            "",
            "## Local renderer diagnostic",
            "",
            (
                f"The existing POP primitives rendered {smoke['total_rendered_frames']} "
                f"full-resolution diagnostic frames across {smoke['sample_count']} "
                f"archetypes in {smoke['total_elapsed_seconds']:.2f} seconds."
            ),
            "",
            (
                "Repeated identical progress states produced identical hashes. This "
                "is a primitive diagnostic, not a full-chapter workload or a remote "
                "cost estimate."
            ),
        ])
    lines.extend([
        "",
        "## Remote gate",
        "",
        "No executable bundle or batch manifest has been created. A later proposal must include a current public price quote, exact resource shape, exact ordered jobs, bundle and batch hashes, cost/create/retry ceilings, cleanup behavior, and a new explicit authorization.",
        "",
    ])
    return "\n".join(lines)


def build() -> None:
    context = approval_context()
    approval = context["approval"]
    bible = context["bible"]
    series = load_json(DEEP_ROOT / "series_manifest.json")
    ordered_ids = series["ordered_episode_ids"]
    episodes_by_id = {item["video_id"]: item for item in bible["episodes"]}
    drift = source_drift()
    drift_ids = {item["source_id"] for item in drift}

    routed_episodes: list[dict[str, Any]] = []
    chapter_count = 0
    composition_count = 0
    local_candidates = 0
    remote_candidates = 0
    executable_chapters = 0
    for video_id in ordered_ids:
        episode = episodes_by_id[video_id]
        episode_dir = EPISODES_ROOT / video_id
        storyboard_path = episode_dir / "storyboard.json"
        narration_path = episode_dir / "narration_contract.json"
        captions_path = episode_dir / "caption_contract.json"
        storyboard = load_json(storyboard_path)
        chapters = chapter_inventory(video_id)
        chapter_count += len(chapters)
        composition_count += len(storyboard["scenes"])
        executable_chapters += sum(
            item["executable_render_payload"] for item in chapters
        )
        if episode["duration_tier"] == "focused_explainer":
            intended = "local_candidate_pending_full_chapter_smoke"
            local_candidates += 1
        else:
            intended = (
                "runpod_candidate_pending_full_chapter_smoke_current_quote_"
                "and_separate_exact_authorization"
            )
            remote_candidates += 1
        routed_episodes.append(finalize({
            "video_id": video_id,
            "episode_order": episode["order"],
            "duration_tier": episode["duration_tier"],
            "duration_seconds": storyboard["duration_s"],
            "fps": storyboard["frame_contract"]["fps"],
            "frame_count": round(
                storyboard["duration_s"] * storyboard["frame_contract"]["fps"]
            ),
            "episode_content_hash": episode["content_hash"],
            "episode_contract_hash": series["episode_contract_hashes"][video_id],
            "storyboard_sha256": file_sha256(storyboard_path),
            "narration_contract_sha256": file_sha256(narration_path),
            "caption_contract_sha256": file_sha256(captions_path),
            "local_support_route": [
                "schema and frozen-evidence validation",
                "render-contract compilation",
                "offline narration after voice decision",
                "chapter assembly and caption mux",
                "encoded-media and editorial QA",
            ],
            "current_frame_render_route": (
                "blocked_pending_executable_chapter_render_contracts"
            ),
            "intended_frame_render_route_after_qualification": intended,
            "live_source_drift_ids": sorted(
                set(episode["source_ids"]) & drift_ids
            ),
            "chapters": chapters,
        }))

    routing = finalize({
        "schema_version": SCHEMA_VERSION,
        "planner_version": PLANNER_VERSION,
        "status": "planning_complete_execution_blocked",
        "scope": "local_production_planning_only",
        "bible_content_hash": approval["bible_content_hash"],
        "review_manifest_sha256": approval["review_manifest_sha256"],
        "content_approval_identity": approval["approval_identity"],
        "remote_or_paid_work_authorized": False,
        "episode_count": len(routed_episodes),
        "chapter_count": chapter_count,
        "storyboard_composition_count": composition_count,
        "executable_chapter_render_payload_count": executable_chapters,
        "route_counts": {
            "local_frame_render_candidates": local_candidates,
            "remote_frame_render_candidates": remote_candidates,
        },
        "episodes": routed_episodes,
    })

    benchmark_plan = finalize({
        "schema_version": SCHEMA_VERSION,
        "planner_version": PLANNER_VERSION,
        "status": "blocked_until_executable_chapter_render_contracts",
        "purpose": (
            "Measure actual full-resolution chapter throughput and determinism; "
            "do not use preview-frame timing as a production cost estimate."
        ),
        "remote_or_paid_work_authorized": False,
        "sample_contract": {
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "frame_interval": "half-open",
            "clock": "frame-derived",
            "worker_counts": [1, 4],
            "repeat_identical_frame_for_determinism": True,
            "retain": [
                "timing JSON",
                "input and output hashes",
                "representative contact sheet",
                "encoded chapter master",
                "decoded-frame QA report",
            ],
        },
        "samples": [
            {
                "video_id": video_id,
                "archetype": archetype,
                "chapter_id": "select_after_compiler_by_visual_coverage",
            }
            for video_id, archetype in REPRESENTATIVE_SAMPLES
        ],
        "required_metrics": [
            "render wall seconds",
            "frames and pixels rendered",
            "frames per second by worker count",
            "worker-equivalent CPU hours",
            "peak memory",
            "encoded bytes and encode wall seconds",
            "repeated-frame hash equality",
            "decoded first/middle/last frame hashes",
        ],
        "cost_model_rule": (
            "Only project series cost from these full-chapter samples and a "
            "current quoted resource rate collected immediately before proposal."
        ),
    })

    work_packages = [
        {
            "order": 1,
            "work_package_id": "WP1",
            "title": "Executable chapter render contract",
            "outcome": (
                "A strict schema and compiler resolves all storyboard "
                "scenes, beats, claims, assets, durations, and frame spans into "
                "deterministic POP payloads."
            ),
            "status": (
                "complete_local_review_required"
                if executable_chapters == chapter_count
                else "incomplete"
            ),
            "acceptance": [
                f"{executable_chapters}/{chapter_count} chapter payloads schema-valid",
                f"{composition_count}/{composition_count} storyboard compositions resolved",
                "every narration cue maps to an explicit timed visual state",
                "no unsupported primitive silently falls back to generic boxes",
            ],
        },
        {
            "order": 2,
            "work_package_id": "WP2",
            "title": "Visual primitive completion and preflight",
            "outcome": (
                "Implement any missing matrix, DAG, circuit, feature-model, policy, "
                "evidence, and recognition primitives plus text-fit/safe-zone checks."
            ),
            "acceptance": [
                "all required asset kinds have an executable primitive",
                "no clipping, placeholder, passive three-box opening, or unexplained empty field",
                "evidence status remains visible without relying only on color",
            ],
        },
        {
            "order": 3,
            "work_package_id": "WP3",
            "title": "Six full-resolution archetype chapter smokes",
            "outcome": (
                "Render and encode one local 1080p chapter for each representative "
                "visual archetype, then measure throughput and determinism."
            ),
            "acceptance": [
                "six encoded chapter masters",
                "deterministic repeated-frame hashes",
                "timing and decoded-frame QA reports",
                "human contact-sheet review",
            ],
        },
        {
            "order": 4,
            "work_package_id": "WP4",
            "title": "Narration and audio realization",
            "outcome": (
                "Select an explicitly licensed local/offline voice or human recording "
                "route and bind cue audio to the existing narration contracts."
            ),
            "acceptance": [
                "voice and license decision recorded",
                "cue-aligned WAV stems with hashes",
                "no paid voice call without separate approval",
                "loudness, silence, and duration checks pass",
            ],
        },
        {
            "order": 5,
            "work_package_id": "WP5",
            "title": "Assembly, captions, and encoded-media QA",
            "outcome": (
                "Add resumable chapter assembly, audio/caption mux, stream inspection, "
                "decoded-frame sampling, and final provenance manifests."
            ),
            "acceptance": [
                "chapter joins are frame-exact",
                "caption identity and timing match the approved contracts",
                "audio/video durations agree within the declared tolerance",
                "final masters remain production candidates, never auto-published",
            ],
        },
        {
            "order": 6,
            "work_package_id": "WP6",
            "title": "Immutable bundle and exact remote proposal",
            "outcome": (
                "After the local smokes pass, construct the normalized allowlisted "
                "bundle, exact ordered chapter jobs, cost model, and approval request."
            ),
            "acceptance": [
                "bundle and batch hashes reproduce",
                "current resource quote and quote time recorded",
                "cost/create/retry/timeout/cleanup ceilings explicit",
                "no credential value enters any artifact",
            ],
        },
    ]
    blocking_findings = []
    if executable_chapters != chapter_count:
        blocking_findings.append(
            f"{chapter_count - executable_chapters} of {chapter_count} chapters lack "
            "executable resolved render contracts."
        )
    blocking_findings.extend([
        (
            "No representative full-resolution chapter master exists yet; current "
            "contact sheets, GIFs, and archetype PNGs are editorial previews."
        ),
        (
            "Narration text/timing contracts exist, but no local voice identity, "
            "license decision, or cue-audio realization is bound."
        ),
        (
            "The episode contracts are not yet integrated with chapter encode, audio/"
            "caption mux, decoded-frame QA, and final release manifests."
        ),
        (
            f"{len(drift)} live source-registry entr{'y is' if len(drift) == 1 else 'ies are'} "
            "currently hash-drifted from the frozen registry."
        ),
        (
            "A current RunPod resource quote was intentionally not collected under "
            "this local-only approval."
        ),
    ])
    audit = finalize({
        "schema_version": SCHEMA_VERSION,
        "planner_version": PLANNER_VERSION,
        "status": "blocked_before_executable_remote_proposal",
        "bible_content_hash": approval["bible_content_hash"],
        "review_manifest_sha256": approval["review_manifest_sha256"],
        "content_approval_identity": approval["approval_identity"],
        "remote_or_paid_work_authorized": False,
        "verified_counts": {
            "episodes": len(routed_episodes),
            "chapters": chapter_count,
            "storyboard_compositions": composition_count,
            "executable_chapter_payloads": executable_chapters,
        },
        "live_source_drift": drift,
        "blocking_findings": blocking_findings,
        "work_packages": work_packages,
    })

    allowlist = supporting_input_allowlist(ordered_ids)
    allowlist_draft = finalize({
        "schema_version": SCHEMA_VERSION,
        "planner_version": PLANNER_VERSION,
        "status": (
            "draft_non_executable_wp1_complete"
            if executable_chapters == chapter_count
            else "draft_non_executable_missing_compiled_render_contracts"
        ),
        "bible_content_hash": approval["bible_content_hash"],
        "content_approval_identity": approval["approval_identity"],
        "remote_or_paid_work_authorized": False,
        "normalization": (
            "UTF-8 text, forward-slash relative paths, lexical path order, "
            "no timestamps in bundle identity"
        ),
        "inputs": allowlist,
        "excluded": [
            "all .env* and credentials",
            "RUNPOD_API_KEY value",
            "unrelated recognition corpora and experiments",
            "caches, temporary frames, logs, and prior outputs",
            "unapproved generative or licensed third-party assets",
        ],
        "missing_before_bundle": [
            "qualified renderer/runtime lock",
            "audio realization decision and hashed stems",
            "exact worker entrypoint and output contract",
        ],
    })

    proposal_status = finalize({
        "schema_version": SCHEMA_VERSION,
        "planner_version": PLANNER_VERSION,
        "proposal_id": "cm-video-deep-series-v2-remote-pending-v1",
        "status": "not_ready_for_authorization",
        "bible_content_hash": approval["bible_content_hash"],
        "review_manifest_sha256": approval["review_manifest_sha256"],
        "content_approval_identity": approval["approval_identity"],
        "remote_or_paid_work_authorized": False,
        "executable_bundle_created": False,
        "executable_batch_manifest_created": False,
        "current_price_quote_collected": False,
        "missing_exact_authorization_fields": [
            "ordered qualified chapter-job list",
            "bundle SHA-256",
            "batch-manifest SHA-256",
            "image digest and resource shape",
            "current hourly rate, source, and quote time",
            "maximum spend, creates, and parallel pods",
            "timeouts, retries, and no-progress watchdog",
            "transport and output verification",
            "delete-on-terminal and owned-inventory reconciliation",
        ],
        "next_gate": (
            "Complete WP1-WP5 locally, reconcile live source drift, run the six "
            "full-chapter samples, then prepare a new exact proposal for approval."
        ),
    })

    write_json(PLANNING_ROOT / "routing_manifest.json", routing)
    write_json(PLANNING_ROOT / "render_benchmark_plan.json", benchmark_plan)
    write_json(PLANNING_ROOT / "production_readiness_audit.json", audit)
    write_json(PLANNING_ROOT / "bundle_allowlist_draft.json", allowlist_draft)
    write_json(PLANNING_ROOT / "runpod_proposal_status.json", proposal_status)
    (PLANNING_ROOT / "PRODUCTION_PLANNING.md").write_text(
        markdown_summary(approval, routing, audit), encoding="utf-8"
    )
    validate()


def primitive_smoke(pop_root: Path, workers: int) -> None:
    """Time existing preview primitives without treating them as chapter costs."""
    context = approval_context()
    approval = context["approval"]
    pop_root = pop_root.resolve()
    if not (pop_root / "pop_video").is_dir():
        raise PlanningError(f"POP package is missing under {pop_root}")
    if workers < 1:
        raise PlanningError("workers must be positive")
    sys.path.insert(0, str(pop_root))
    from pop_video.contracts import VideoBrief  # type: ignore
    from pop_video.planning import plan_brief  # type: ignore

    progress_values = [0.10, 0.35, 0.50, 0.50, 0.75, 0.95]
    samples: list[dict[str, Any]] = []
    total_frames = 0
    total_elapsed = 0.0
    for video_id, archetype in REPRESENTATIVE_SAMPLES:
        brief_path = EPISODES_ROOT / video_id / "preview.renderer_brief.json"
        brief = load_json(brief_path)
        brief["width"] = 1920
        brief["height"] = 1080
        spec = plan_brief(VideoBrief.model_validate(brief))
        with tempfile.TemporaryDirectory(prefix=f"cm-{video_id}-primitive-") as tmp:
            started = time.perf_counter()
            frames = deep_series_authoring.render_progress_frames(
                spec, Path(tmp), progress_values, workers
            )
            elapsed = time.perf_counter() - started
            frame_hashes = [file_sha256(path) for path in frames]
        stride = len(progress_values)
        repeated_pairs = [
            {
                "scene_id": scene.id,
                "first_sha256": frame_hashes[index * stride + 2],
                "second_sha256": frame_hashes[index * stride + 3],
                "equal": (
                    frame_hashes[index * stride + 2]
                    == frame_hashes[index * stride + 3]
                ),
            }
            for index, scene in enumerate(spec.scenes)
        ]
        count = len(frames)
        total_frames += count
        total_elapsed += elapsed
        samples.append({
            "video_id": video_id,
            "archetype": archetype,
            "input_brief_path": relative(brief_path),
            "input_brief_sha256": file_sha256(brief_path),
            "scene_count": len(spec.scenes),
            "progress_samples_per_scene": len(progress_values),
            "rendered_frame_count": count,
            "elapsed_seconds": round(elapsed, 6),
            "throughput_frames_per_second": round(count / elapsed, 6),
            "wall_seconds_per_frame": round(elapsed / count, 6),
            "ordered_output_hash_set_sha256": canonical_sha256(frame_hashes),
            "repeated_progress_determinism": repeated_pairs,
        })
    result = finalize({
        "schema_version": SCHEMA_VERSION,
        "planner_version": PLANNER_VERSION,
        "status": "diagnostic_only_not_cost_authoritative",
        "purpose": (
            "Confirm the checked-in POP cm_science primitives render at 1080p and "
            "repeat an identical progress state deterministically. This is not a "
            "full-chapter workload and must not drive a remote cost proposal."
        ),
        "bible_content_hash": approval["bible_content_hash"],
        "review_manifest_sha256": approval["review_manifest_sha256"],
        "content_approval_identity": approval["approval_identity"],
        "remote_or_paid_work_authorized": False,
        "runtime": {
            "renderer": "POP-Video-Creator/cm_science@1.0.0",
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "workers": workers,
            "logical_processors": os.cpu_count(),
            "progress_values": progress_values,
        },
        "sample_count": len(samples),
        "total_rendered_frames": total_frames,
        "total_elapsed_seconds": round(total_elapsed, 6),
        "aggregate_throughput_frames_per_second": round(
            total_frames / total_elapsed, 6
        ),
        "all_repeated_progress_hashes_equal": all(
            pair["equal"]
            for sample in samples
            for pair in sample["repeated_progress_determinism"]
        ),
        "samples": samples,
        "next_measurement": (
            "After WP1-WP2, render the six selected full chapters at worker counts "
            "1 and 4 and use those results for the production cost model."
        ),
    })
    write_json(PLANNING_ROOT / "renderer_primitive_smoke_results.json", result)
    validate()


def validate() -> None:
    context = approval_context()
    approval = context["approval"]
    required = (
        "routing_manifest.json",
        "render_benchmark_plan.json",
        "production_readiness_audit.json",
        "bundle_allowlist_draft.json",
        "runpod_proposal_status.json",
    )
    artifacts = {name: load_json(PLANNING_ROOT / name) for name in required}
    for name, artifact in artifacts.items():
        expected = canonical_sha256(
            {key: value for key, value in artifact.items() if key != "content_hash"}
        )
        if artifact.get("content_hash") != expected:
            raise PlanningError(f"stale planning artifact hash: {name}")
        if artifact.get("remote_or_paid_work_authorized") is not False:
            raise PlanningError(f"planning artifact authorizes remote work: {name}")
        if artifact.get("content_approval_identity") not in (
            None,
            approval["approval_identity"],
        ):
            raise PlanningError(f"planning artifact approval mismatch: {name}")
    bible = context["bible"]
    expected_episodes = len(bible["episodes"])
    expected_chapters = sum(len(item["chapter_plan"]) for item in bible["episodes"])
    expected_compositions = sum(
        load_json(EPISODES_ROOT / item["video_id"] / "storyboard.json")[
            "composition_count"
        ]
        for item in bible["episodes"]
    )
    routing = artifacts["routing_manifest.json"]
    if (
        routing["episode_count"] != expected_episodes
        or len(routing["episodes"]) != expected_episodes
    ):
        raise PlanningError(
            f"routing manifest must contain {expected_episodes} episodes"
        )
    if routing["chapter_count"] != expected_chapters:
        raise PlanningError(
            f"routing manifest must contain {expected_chapters} chapters"
        )
    if routing["storyboard_composition_count"] != expected_compositions:
        raise PlanningError(
            f"routing manifest must contain {expected_compositions} compositions"
        )
    if routing["executable_chapter_render_payload_count"] != expected_chapters:
        raise PlanningError("WP1 executable chapter coverage is incomplete")
    if (
        sum(len(item["chapters"]) for item in routing["episodes"])
        != expected_chapters
    ):
        raise PlanningError("chapter routing coverage is incomplete")
    allowlist = artifacts["bundle_allowlist_draft.json"]
    for item in allowlist["inputs"]:
        path = REPO_ROOT / item["path"]
        if not path.is_file() or file_sha256(path) != item["sha256"]:
            raise PlanningError(f"stale draft allowlist input: {item['path']}")
    if not (PLANNING_ROOT / "PRODUCTION_PLANNING.md").is_file():
        raise PlanningError("production-planning summary is missing")
    smoke_path = PLANNING_ROOT / "renderer_primitive_smoke_results.json"
    if smoke_path.is_file():
        smoke = load_json(smoke_path)
        expected = canonical_sha256(
            {key: value for key, value in smoke.items() if key != "content_hash"}
        )
        if smoke.get("content_hash") != expected:
            raise PlanningError("stale renderer primitive smoke hash")
        if smoke.get("remote_or_paid_work_authorized") is not False:
            raise PlanningError("renderer primitive smoke authorizes remote work")
        if smoke.get("status") != "diagnostic_only_not_cost_authoritative":
            raise PlanningError("renderer primitive smoke has an unsafe status")
        if smoke.get("sample_count") != len(REPRESENTATIVE_SAMPLES):
            raise PlanningError("renderer primitive smoke coverage is incomplete")
        if smoke.get("all_repeated_progress_hashes_equal") is not True:
            raise PlanningError("renderer primitive smoke is nondeterministic")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "primitive-smoke", "validate"))
    parser.add_argument("--pop-root", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "build":
        build()
    elif args.command == "primitive-smoke":
        if args.pop_root is None:
            parser.error("primitive-smoke requires --pop-root")
        primitive_smoke(args.pop_root, args.workers)
    else:
        validate()


if __name__ == "__main__":
    main()
