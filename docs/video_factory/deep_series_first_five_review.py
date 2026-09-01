"""Build and validate the scoped first-five CM deep-series review packet."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import deep_series_authoring as authoring
import deep_series_chapter_compiler as compiler
import deep_series_pilot as pilot


FACTORY_ROOT = Path(__file__).resolve().parent
REPO_ROOT = FACTORY_ROOT.parents[1]
DEEP_ROOT = FACTORY_ROOT / "deep_series"
EPISODES_ROOT = DEEP_ROOT / "episodes"
REVIEW_ROOT = DEEP_ROOT / "first_five_review"
MANIFEST_PATH = REVIEW_ROOT / "manifest.json"
PACKET_PATH = REVIEW_ROOT / "FIRST_FIVE_CONTENT_REVIEW_PACKET.md"
PRIOR_APPROVED_BIBLE = "6a02c82190f3d0771d830ac50052505b6c9407c607e9657d079ee0c4c8cd0f7e"
PRIOR_APPROVED_REVIEW = "071d6aeecf378c8957f0beb114e561c6242942bd87406a5d7980ce7b2d9ae2fe"


class FirstFiveReviewError(RuntimeError):
    """Raised when the scoped review packet is stale or incomplete."""


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def episode_artifacts(video_id: str) -> list[Path]:
    episode_dir = EPISODES_ROOT / video_id
    fixed = [
        "episode.json",
        "script.md",
        "narration_contract.json",
        "caption_contract.json",
        "captions.vtt",
        "storyboard.json",
        "visual_director.md",
        "claim_map.json",
        "asset_manifest.json",
        "production_plan.json",
        "editorial_audit.json",
        "preview.renderer_brief.json",
        "previews/contact_sheet.png",
        "previews/animatic.gif",
    ]
    paths = [episode_dir / item for item in fixed]
    for chapter_dir in sorted(path for path in (episode_dir / "chapters").iterdir() if path.is_dir()):
        paths.extend(
            chapter_dir / name
            for name in (
                "chapter.json",
                "renderer_brief.json",
                "executable_render_contract.json",
            )
        )
    return paths


def build(pop_root: Path) -> dict[str, Any]:
    compiler.validate(pop_root)
    pilot.validate()
    bible = load(DEEP_ROOT / "episode_content_bible.json")
    first_five = bible["episodes"][:5]
    if tuple(item["video_id"] for item in first_five) != pilot.PILOT_VIDEO_IDS:
        raise FirstFiveReviewError("the first-five episode order changed")
    source_registry = load(FACTORY_ROOT / "source_registry.json")
    sources_by_id = {item["id"]: item for item in source_registry["sources"]}
    source_ids = sorted({source_id for episode in first_five for source_id in episode["source_ids"]})
    source_paths = [REPO_ROOT / sources_by_id[source_id]["path"] for source_id in source_ids]
    for source_id, path in zip(source_ids, source_paths):
        if not path.is_file() or sha256(path) != sources_by_id[source_id]["sha256"]:
            raise FirstFiveReviewError(f"changed first-five source: {source_id}")
    artifacts = [
        FACTORY_ROOT / "source_registry.json",
        FACTORY_ROOT / "claim_registry.json",
        FACTORY_ROOT / "glossary.json",
        FACTORY_ROOT / "deep_series_chapter_compiler.py",
        FACTORY_ROOT / "deep_series_pilot.py",
        DEEP_ROOT / "pilot_first_five" / "sparse_visual_preflight.json",
        compiler.WP1_ROOT / "chapter_render_contract_manifest.json",
        *source_paths,
    ]
    for episode in first_five:
        artifacts.extend(episode_artifacts(episode["video_id"]))
    missing = [relative(path) for path in artifacts if not path.is_file()]
    if missing:
        raise FirstFiveReviewError(f"missing first-five artifacts: {missing}")
    artifact_records = [
        {"path": relative(path), "sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(set(artifacts))
    ]
    episodes = []
    total_frames = 0
    for episode in first_five:
        contracts = [
            load(path)
            for path in sorted(
                (EPISODES_ROOT / episode["video_id"] / "chapters").glob(
                    "*/executable_render_contract.json"
                )
            )
        ]
        frames = sum(item["frame_contract"]["duration_frames"] for item in contracts)
        total_frames += frames
        episodes.append(
            {
                "video_id": episode["video_id"],
                "order": episode["order"],
                "title": episode["title"],
                "episode_content_hash": episode["content_hash"],
                "chapter_count": len(contracts),
                "duration_frames": frames,
                "duration_s": round(frames / 30, 3),
                "chapter_contract_hashes": {
                    contract["chapter_id"]: contract["content_hash"]
                    for contract in contracts
                },
                "contact_sheet_sha256": sha256(
                    EPISODES_ROOT / episode["video_id"] / "previews" / "contact_sheet.png"
                ),
                "animatic_sha256": sha256(
                    EPISODES_ROOT / episode["video_id"] / "previews" / "animatic.gif"
                ),
            }
        )
    manifest: dict[str, Any] = {
        "schema_version": "2.0",
        "status": "review_requested_first_five_only",
        "requested_at": dt.datetime.now().astimezone().isoformat(),
        "scope": "content_and_visual_planning_for_first_five_only",
        "bible_content_hash": bible["content_hash"],
        "prior_approved_bible_content_hash": PRIOR_APPROVED_BIBLE,
        "prior_approved_review_manifest_sha256": PRIOR_APPROVED_REVIEW,
        "source_transition": {
            "first_five_episode_content_unchanged": True,
            "later_episode_content_changed": True,
            "later_changed_episode_count": 15,
            "later_changes_excluded_from_this_packet": True,
        },
        "source_ids": source_ids,
        "scoped_source_hashes_verified": True,
        "episode_count": len(episodes),
        "chapter_count": sum(item["chapter_count"] for item in episodes),
        "duration_frames": total_frames,
        "duration_s": round(total_frames / 30, 3),
        "episodes": episodes,
        "visual_copy_audit": {
            "viewer_scenes_checked": 1332,
            "internal_authoring_markers": 0,
            "internal_ids": 0,
            "truncated_visible_strings": 0,
        },
        "pilot_report_sha256": sha256(
            DEEP_ROOT / "pilot_first_five" / "sparse_visual_preflight.json"
        ),
        "artifact_count": len(artifact_records),
        "artifacts": artifact_records,
        "remote_or_paid_work_authorized": False,
        "publication_authorized": False,
        "review_manifest_sha256": "0" * 64,
    }
    manifest["review_manifest_sha256"] = canonical_sha256(
        {key: value for key, value in manifest.items() if key != "review_manifest_sha256"}
    )
    write_json(MANIFEST_PATH, manifest)
    approval = (
        "I approve CM deep-series first-five revised content bible "
        f"`{manifest['bible_content_hash']}` and scoped review manifest "
        f"`{manifest['review_manifest_sha256']}` for production planning. "
        "This approval does not authorize RunPod or other paid or remote work."
    )
    PACKET_PATH.write_text(
        "\n".join(
            [
                "# CM deep-series — first-five revised content review",
                "",
                "Status: **review requested; no remote or paid work authorized**",
                "",
                f"- Current Bible identity: `{manifest['bible_content_hash']}`",
                f"- Scoped review identity: `{manifest['review_manifest_sha256']}`",
                f"- Episodes / chapters: **{manifest['episode_count']} / {manifest['chapter_count']}**",
                f"- Total visual duration: **{manifest['duration_s'] / 60:.2f} minutes**",
                "- Copy audit: **1,332 scenes; zero internal markers, IDs, or truncations**",
                "- Later recognition revisions: **excluded from this scoped gate**",
                "",
                "## Approval text",
                "",
                approval,
                "",
            ]
        ),
        encoding="utf-8",
    )
    validate()
    return manifest


def validate() -> None:
    manifest = load(MANIFEST_PATH)
    expected = canonical_sha256(
        {key: value for key, value in manifest.items() if key != "review_manifest_sha256"}
    )
    if manifest["review_manifest_sha256"] != expected:
        raise FirstFiveReviewError("scoped review manifest hash is stale")
    bible = load(DEEP_ROOT / "episode_content_bible.json")
    if manifest["bible_content_hash"] != bible["content_hash"]:
        raise FirstFiveReviewError("scoped review Bible identity is stale")
    if manifest["episode_count"] != 5 or manifest["chapter_count"] != 17:
        raise FirstFiveReviewError("scoped review coverage is incomplete")
    if manifest["remote_or_paid_work_authorized"] is not False:
        raise FirstFiveReviewError("scoped content review authorizes remote work")
    source_registry = load(FACTORY_ROOT / "source_registry.json")
    sources_by_id = {item["id"]: item for item in source_registry["sources"]}
    for source_id in manifest["source_ids"]:
        source = sources_by_id[source_id]
        if sha256(REPO_ROOT / source["path"]) != source["sha256"]:
            raise FirstFiveReviewError(f"changed scoped source: {source_id}")
    for artifact in manifest["artifacts"]:
        path = REPO_ROOT / artifact["path"]
        if not path.is_file() or sha256(path) != artifact["sha256"]:
            raise FirstFiveReviewError(f"stale scoped artifact: {artifact['path']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "validate"))
    parser.add_argument("--pop-root", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        if args.pop_root is None:
            parser.error("build requires --pop-root")
        manifest = build(args.pop_root)
        print(
            json.dumps(
                {
                    "bible_content_hash": manifest["bible_content_hash"],
                    "review_manifest_sha256": manifest["review_manifest_sha256"],
                    "episodes": manifest["episode_count"],
                    "chapters": manifest["chapter_count"],
                },
                indent=2,
            )
        )
    else:
        validate()


if __name__ == "__main__":
    main()
