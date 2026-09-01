"""Build and validate the local-light first-five CM deep-series pilot.

This module renders one settled 1080p frame per authored composition for human
review.  It does not render full video, synthesize narration, use a credential,
contact a network service, or authorize paid work.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
import datetime as dt
from typing import Any

from PIL import Image, ImageStat

import deep_series_authoring as authoring
import deep_series_chapter_compiler as compiler


FACTORY_ROOT = Path(__file__).resolve().parent
DEEP_ROOT = FACTORY_ROOT / "deep_series"
EPISODES_ROOT = DEEP_ROOT / "episodes"
PILOT_ROOT = DEEP_ROOT / "pilot_first_five"
PILOT_VIDEO_IDS = (
    "conceptual-vs-measured",
    "why-boolean-computation",
    "expression-truth-function",
    "live-support-ambient",
    "what-is-explicit-cm",
)
EXPECTED_PRIMITIVES = {
    "transform_compare",
    "boundary",
    "result",
    "expression_matrix",
    "representation_compare",
}


class PilotError(RuntimeError):
    """Raised when the bounded pilot is incomplete or visually invalid."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    authoring.write_json(path, value)


def diverse_frames(
    paths: list[Path], resolved: list[dict[str, Any]], count: int = 6
) -> list[Path]:
    if len(paths) != len(resolved):
        raise PilotError("preview frame/scene alignment failed")
    selected: set[int] = set()
    for primitive in dict.fromkeys(scene["primitive"] for scene in resolved):
        selected.add(next(
            index for index, scene in enumerate(resolved)
            if scene["primitive"] == primitive
        ))
    if len(paths) > 1:
        for slot in range(count):
            selected.add(round(slot * (len(paths) - 1) / (count - 1)))
            if len(selected) >= count:
                break
    for index in range(len(paths)):
        if len(selected) >= count:
            break
        selected.add(index)
    return [paths[index] for index in sorted(selected)[:count]]


def frame_metrics(path: Path) -> dict[str, Any]:
    with Image.open(path) as source:
        image = source.convert("RGB")
        if image.size != (1920, 1080):
            raise PilotError(f"wrong preview dimensions: {path}:{image.size}")
        sample = image.resize((192, 108), Image.Resampling.BILINEAR)
        background = sample.getpixel((0, 0))
        occupied = sum(
            1
            for pixel in sample.getdata()
            if max(abs(pixel[channel] - background[channel]) for channel in range(3)) >= 12
        )
        occupied_ratio = occupied / (sample.width * sample.height)
        luminance = sample.convert("L")
        deviation = ImageStat.Stat(luminance).stddev[0]
        entropy = luminance.entropy()
    return {
        "path": path.as_posix(),
        "sha256": authoring.file_sha256(path),
        "occupied_ratio": round(occupied_ratio, 5),
        "luminance_stddev": round(deviation, 3),
        "entropy": round(entropy, 3),
        "passed": occupied_ratio >= 0.055 and deviation >= 12 and entropy >= 1.5,
    }


def episode_brief(video_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    chapter_root = EPISODES_ROOT / video_id / "chapters"
    contracts = [
        load_json(path / "executable_render_contract.json")
        for path in sorted(item for item in chapter_root.iterdir() if item.is_dir())
    ]
    if not contracts:
        raise PilotError(f"no compiled chapters for {video_id}")
    brief = copy.deepcopy(contracts[0]["pop_video_brief"])
    brief["title"] = f"{video_id} · pilot visual review"
    brief["purpose"] = "Sparse settled-frame visual review; not a production render."
    brief["scenes"] = [
        copy.deepcopy(scene["pop_scene"])
        for contract in contracts
        for scene in contract["resolved_scenes"]
    ]
    resolved = [scene for contract in contracts for scene in contract["resolved_scenes"]]
    return brief, resolved


def refresh_episode_assets(episode: dict[str, Any]) -> None:
    episode_dir = EPISODES_ROOT / episode["video_id"]
    example_path = DEEP_ROOT / "examples" / f"{episode['worked_example_id']}.json"
    assets = authoring.build_asset_manifest(episode, example_path, episode_dir)
    write_json(episode_dir / "asset_manifest.json", assets)
    contract = load_json(episode_dir / "episode.json")
    contract["artifact_hashes"]["asset_manifest"] = assets["content_hash"]
    contract["artifact_hashes"]["contact_sheet"] = authoring.file_sha256(
        episode_dir / "previews" / "contact_sheet.png"
    )
    contract["artifact_hashes"]["animatic"] = authoring.file_sha256(
        episode_dir / "previews" / "animatic.gif"
    )
    contract = authoring.finalize(
        {key: value for key, value in contract.items() if key != "contract_hash"},
        "contract_hash",
    )
    write_json(episode_dir / "episode.json", contract)


def build_previews(pop_root: Path, workers: int = 2) -> None:
    compiler.validate(pop_root)
    pop_root = pop_root.resolve()
    if str(pop_root) not in sys.path:
        sys.path.insert(0, str(pop_root))
    from pop_video.contracts import VideoBrief  # type: ignore
    from pop_video.planning import plan_brief  # type: ignore

    bible = load_json(DEEP_ROOT / "episode_content_bible.json")
    episodes = {item["video_id"]: item for item in bible["episodes"]}
    if tuple(item["video_id"] for item in bible["episodes"][:5]) != PILOT_VIDEO_IDS:
        raise PilotError("the pilot IDs no longer match the first five bible episodes")

    reports = []
    for video_id in PILOT_VIDEO_IDS:
        brief, resolved = episode_brief(video_id)
        primitives = {scene["primitive"] for scene in resolved}
        expected = (
            {"transform_compare", "boundary", "result"}
            if video_id == "conceptual-vs-measured"
            else {"expression_matrix", "representation_compare", "boundary"}
        )
        if primitives != expected:
            raise PilotError(f"{video_id}:unexpected primitive coverage:{sorted(primitives)}")
        spec = plan_brief(VideoBrief.model_validate(brief))
        with tempfile.TemporaryDirectory(prefix=f"cm-pilot-{video_id}-") as temporary:
            frame_paths = authoring.render_progress_frames(
                spec, Path(temporary) / "frames", [0.98], workers
            )
            if len(frame_paths) != len(resolved):
                raise PilotError(
                    f"{video_id}:rendered {len(frame_paths)} frames for {len(resolved)} scenes"
                )
            metrics = [frame_metrics(path) for path in frame_paths]
            preview_dir = EPISODES_ROOT / video_id / "previews"
            authoring.make_contact_sheet(
                diverse_frames(frame_paths, resolved), episodes[video_id]["title"],
                preview_dir / "contact_sheet.png",
            )
            frames = [
                Image.open(path)
                .convert("RGB")
                .resize((640, 360), Image.Resampling.LANCZOS)
                .convert("P", palette=Image.Palette.ADAPTIVE)
                for path in frame_paths
            ]
            frames[0].save(
                preview_dir / "animatic.gif",
                save_all=True,
                append_images=frames[1:],
                duration=450,
                loop=0,
                optimize=False,
            )
            for frame in frames:
                frame.close()
        if not all(item["passed"] for item in metrics):
            failed = [item["path"] for item in metrics if not item["passed"]]
            raise PilotError(f"{video_id}:low-information preview frames:{failed}")
        refresh_episode_assets(episodes[video_id])
        reports.append({
            "video_id": video_id,
            "scene_count": len(resolved),
            "primitives": sorted(primitives),
            "unique_frame_hashes": len({item["sha256"] for item in metrics}),
            "minimum_occupied_ratio": min(item["occupied_ratio"] for item in metrics),
            "minimum_luminance_stddev": min(item["luminance_stddev"] for item in metrics),
            "minimum_entropy": min(item["entropy"] for item in metrics),
            "all_frames_passed": True,
            "contact_sheet_sha256": authoring.file_sha256(
                EPISODES_ROOT / video_id / "previews" / "contact_sheet.png"
            ),
            "animatic_sha256": authoring.file_sha256(
                EPISODES_ROOT / video_id / "previews" / "animatic.gif"
            ),
        })

    episode_hashes = {
        episode["video_id"]: load_json(
            EPISODES_ROOT / episode["video_id"] / "episode.json"
        )["contract_hash"]
        for episode in bible["episodes"]
    }
    authoring.build_global_reports(bible, episode_hashes)
    report = authoring.finalize({
        "schema_version": "2.0",
        "status": "first_five_sparse_visual_preflight_passed",
        "bible_content_hash": bible["content_hash"],
        "wp1_manifest_hash": load_json(
            compiler.WP1_ROOT / "chapter_render_contract_manifest.json"
        )["content_hash"],
        "remote_or_paid_work_authorized": False,
        "render_scope": "one settled 1080p frame per composition",
        "video_count": len(reports),
        "scene_count": sum(item["scene_count"] for item in reports),
        "primitive_coverage": sorted(
            {primitive for item in reports for primitive in item["primitives"]}
        ),
        "episodes": reports,
    })
    write_json(PILOT_ROOT / "sparse_visual_preflight.json", report)
    validate()


def validate() -> None:
    report_path = PILOT_ROOT / "sparse_visual_preflight.json"
    if not report_path.is_file():
        raise PilotError("sparse pilot visual preflight is missing")
    report = load_json(report_path)
    expected = authoring.canonical_sha256(
        {key: value for key, value in report.items() if key != "content_hash"}
    )
    if report["content_hash"] != expected:
        raise PilotError("sparse pilot visual preflight hash is stale")
    bible = load_json(DEEP_ROOT / "episode_content_bible.json")
    wp1 = load_json(compiler.WP1_ROOT / "chapter_render_contract_manifest.json")
    if report["bible_content_hash"] != bible["content_hash"]:
        raise PilotError("pilot preflight bible identity is stale")
    if report["wp1_manifest_hash"] != wp1["content_hash"]:
        raise PilotError("pilot preflight WP1 identity is stale")
    if report["video_count"] != 5 or report["scene_count"] != 93:
        raise PilotError("pilot preview coverage is incomplete")
    if set(report["primitive_coverage"]) != EXPECTED_PRIMITIVES:
        raise PilotError("pilot primitive coverage is incomplete")
    if report["remote_or_paid_work_authorized"] is not False:
        raise PilotError("pilot preflight authorizes remote work")
    for item in report["episodes"]:
        if not item["all_frames_passed"]:
            raise PilotError(f"pilot preview failed: {item['video_id']}")
        episode_dir = EPISODES_ROOT / item["video_id"] / "previews"
        if authoring.file_sha256(episode_dir / "contact_sheet.png") != item["contact_sheet_sha256"]:
            raise PilotError(f"stale contact sheet: {item['video_id']}")
        if authoring.file_sha256(episode_dir / "animatic.gif") != item["animatic_sha256"]:
            raise PilotError(f"stale animatic: {item['video_id']}")


def rebind_current_identity(prior_bible_hash: str, basis_request: Path) -> None:
    """Rebind unchanged reviewed pixels after a bibliography-only Bible transition.

    This operation never renders.  It is permitted only when the five saved
    media hashes still match, the first-five episode/scene/primitive coverage
    remains complete, and the supplied historical request binds the report's
    prior Bible identity.
    """
    report_path = PILOT_ROOT / "sparse_visual_preflight.json"
    report = load_json(report_path)
    request = load_json(basis_request.resolve())
    if report["bible_content_hash"] != prior_bible_hash:
        raise PilotError("prior Bible hash does not match the rendered report")
    if request["bible_content_hash"] != prior_bible_hash:
        raise PilotError("basis request does not bind the prior Bible hash")
    bible = load_json(DEEP_ROOT / "episode_content_bible.json")
    episodes = {item["video_id"]: item for item in bible["episodes"]}
    current_scene_count = 0
    current_primitives: set[str] = set()
    for item in report["episodes"]:
        video_id = item["video_id"]
        if video_id not in PILOT_VIDEO_IDS:
            raise PilotError(f"unexpected rebound episode: {video_id}")
        _, resolved = episode_brief(video_id)
        primitives = sorted({scene["primitive"] for scene in resolved})
        if len(resolved) != item["scene_count"] or primitives != item["primitives"]:
            raise PilotError(f"visual topology changed after render: {video_id}")
        preview_dir = EPISODES_ROOT / video_id / "previews"
        if authoring.file_sha256(preview_dir / "contact_sheet.png") != item["contact_sheet_sha256"]:
            raise PilotError(f"contact sheet changed after render: {video_id}")
        if authoring.file_sha256(preview_dir / "animatic.gif") != item["animatic_sha256"]:
            raise PilotError(f"animatic changed after render: {video_id}")
        current_scene_count += len(resolved)
        current_primitives.update(primitives)
    if current_scene_count != 93 or current_primitives != EXPECTED_PRIMITIVES:
        raise PilotError("first-five rebound coverage changed")
    report["bible_content_hash"] = bible["content_hash"]
    report["wp1_manifest_hash"] = load_json(
        compiler.WP1_ROOT / "chapter_render_contract_manifest.json"
    )["content_hash"]
    report["identity_rebind"] = {
        "rebound_at": dt.datetime.now().astimezone().isoformat(),
        "prior_bible_content_hash": prior_bible_hash,
        "current_bible_content_hash": bible["content_hash"],
        "basis_review_manifest_sha256": request["review_manifest_sha256"],
        "reason": "The current-source transition changed later recognition episodes; the first-five episode content, visual topology, and saved pixel hashes remained unchanged.",
        "pixels_rerendered": False,
        "remote_or_paid_work_authorized": False,
    }
    report = authoring.finalize(
        {key: value for key, value in report.items() if key != "content_hash"}
    )
    write_json(report_path, report)
    validate()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build-previews", "rebind", "validate"))
    parser.add_argument("--pop-root", type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--prior-bible-hash")
    parser.add_argument("--basis-request", type=Path)
    args = parser.parse_args()
    if args.command == "build-previews":
        if args.pop_root is None:
            parser.error("build-previews requires --pop-root")
        build_previews(args.pop_root, workers=args.workers)
    elif args.command == "rebind":
        if not args.prior_bible_hash or args.basis_request is None:
            parser.error("rebind requires --prior-bible-hash and --basis-request")
        rebind_current_identity(args.prior_bible_hash, args.basis_request)
    else:
        validate()


if __name__ == "__main__":
    main()
