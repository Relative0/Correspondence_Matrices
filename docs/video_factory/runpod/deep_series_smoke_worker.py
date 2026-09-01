"""Offline worker for one hash-bound CM deep-series chapter smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
from typing import Any


BUNDLE_ROOT = Path(os.environ.get("CM_VIDEO_BUNDLE_ROOT", Path(__file__).resolve().parents[1])).resolve()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def verify_bundle(root: Path) -> dict[str, Any]:
    manifest = json.loads((root / "package_manifest.json").read_text("utf-8"))
    for entry in manifest["files"]:
        path = root / entry["path"]
        if not path.is_file() or path.stat().st_size != entry["size"] or sha256(path) != entry["sha256"]:
            raise ValueError(f"bundle file mismatch: {entry['path']}")
    payload = hashlib.sha256(canonical_bytes(manifest["files"])).hexdigest()
    if payload != manifest["payload_sha256"]:
        raise ValueError("bundle payload identity mismatch")
    return manifest


def load_job(root: Path, path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    batch = json.loads((root / "cm" / "batch_manifest.json").read_text("utf-8"))
    job = json.loads(path.read_text("utf-8"))
    expected = batch["job_hashes"].get(job["job_id"])
    if expected is None or sha256(path) != expected:
        raise ValueError("job is absent from, or does not match, the batch manifest")
    contract_path = root / job["contract_path"]
    if sha256(contract_path) != job["contract_sha256"]:
        raise ValueError("chapter contract identity mismatch")
    contract = json.loads(contract_path.read_text("utf-8"))
    if (
        contract["video_id"] != job["video_id"]
        or contract["chapter_id"] != job["chapter_id"]
        or contract["chapter_cache_identity"] != job["cache_identity"]
        or contract["frame_contract"] != job["frame_contract"]
    ):
        raise ValueError("job and chapter contract disagree")
    primitives = sorted({scene["primitive"] for scene in contract["resolved_scenes"]})
    if primitives != job["expected_primitives"]:
        raise ValueError("chapter primitive coverage changed")
    return job, contract


def probe(video: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    data = json.loads(completed.stdout)
    stream = next(item for item in data["streams"] if item["codec_type"] == "video")
    numerator, denominator = stream["avg_frame_rate"].split("/", 1)
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": float(numerator) / float(denominator),
        "codec": stream["codec_name"],
        "pixel_format": stream.get("pix_fmt"),
        "duration_s": float(data["format"]["duration"]),
        "has_audio": any(item["codec_type"] == "audio" for item in data["streams"]),
    }


def extract_previews(video: Path, directory: Path, duration_s: float) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    samples = {
        "opening": min(0.2, duration_s / 20),
        "middle": duration_s * 0.5,
        "final": max(0.0, duration_s - 0.1),
    }
    hashes = {}
    for name, timestamp in samples.items():
        output = directory / f"{name}.png"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{timestamp:.6f}", "-i", str(video),
             "-frames:v", "1", str(output)],
            check=True,
        )
        hashes[name] = sha256(output)
    return hashes


def repeat_frame_check(spec: Any, directory: Path, workers: int) -> dict[str, Any]:
    from pop_video.render.dispatch import scene_html  # type: ignore
    from pop_video.render.frames import DRIVER, PROJECT_ROOT, _preflight  # type: ignore

    node = _preflight()
    scene = spec.scenes[0]
    manifest = {
        "width": spec.width,
        "height": spec.height,
        "fps": spec.fps,
        "scenes": [{
            "id": scene.id,
            "kind": scene.kind,
            "startIndex": 0,
            "progress": [0.875, 0.875],
            "html": scene_html(scene, spec),
        }],
    }
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory.parent / "repeat-frame.manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    completed = subprocess.run(
        [node, str(DRIVER), str(manifest_path), str(directory), str(workers)],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    manifest_path.unlink(missing_ok=True)
    if completed.returncode:
        raise RuntimeError("repeat-frame render failed: " + completed.stderr[-1000:])
    frames = sorted(directory.glob("f*.png"))
    if len(frames) != 2:
        raise RuntimeError("repeat-frame render did not write exactly two frames")
    hashes = [sha256(path) for path in frames]
    return {"progress": 0.875, "hashes": hashes, "identical": hashes[0] == hashes[1]}


def render(job_path: Path, output_root: Path, bundle_root: Path = BUNDLE_ROOT) -> Path:
    preview = json.loads(job_path.read_text("utf-8"))
    output = output_root / preview["job_id"]
    result_path = output / "render_result.json"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        package = verify_bundle(bundle_root)
        job, contract = load_job(bundle_root, job_path)
        sys.path.insert(0, str(bundle_root / "pop"))
        from pop_video.contracts import VideoBrief  # type: ignore
        from pop_video.encode.ffmpeg import encode  # type: ignore
        from pop_video.planning import plan_brief  # type: ignore
        from pop_video.render.frames import render_frames  # type: ignore

        spec = plan_brief(VideoBrief.model_validate(contract["pop_video_brief"]))
        if spec.total_frames != job["frame_contract"]["duration_frames"]:
            raise ValueError("resolved POP frame count differs from the chapter contract")
        frames_dir = output / "frames"
        render_started = time.perf_counter()
        frames = render_frames(spec, frames_dir, workers=job["render_workers"])
        render_seconds = time.perf_counter() - render_started
        video = output / f"{job['job_id']}.mp4"
        encode_started = time.perf_counter()
        encode_manifest = encode(spec, frames, video)
        encode_seconds = time.perf_counter() - encode_started
        technical = probe(video)
        expected = job["frame_contract"]
        expected_duration = expected["duration_frames"] / expected["fps"]
        if (
            technical["width"] != expected["width"]
            or technical["height"] != expected["height"]
            or round(technical["fps"]) != expected["fps"]
            or technical["codec"] != "h264"
            or technical["has_audio"]
            or abs(technical["duration_s"] - expected_duration) > (2 / expected["fps"] + 0.01)
        ):
            raise RuntimeError(f"encoded media contract mismatch: {technical}")
        preview_hashes = extract_previews(video, output / "previews", technical["duration_s"])
        repeated = repeat_frame_check(spec, output / "repeat-frame", min(2, job["render_workers"]))
        if not repeated["identical"]:
            raise RuntimeError("identical renderer inputs produced different PNGs")
        shutil.rmtree(frames_dir)
        child_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        result = {
            "schema_version": "1.0",
            "job_id": job["job_id"],
            "video_id": job["video_id"],
            "chapter_id": job["chapter_id"],
            "cache_identity": job["cache_identity"],
            "status": "passed",
            "passed": True,
            "bundle_payload_sha256": package["payload_sha256"],
            "contract_sha256": job["contract_sha256"],
            "technical_observations": technical,
            "timing": {
                "render_wall_seconds": round(render_seconds, 3),
                "encode_wall_seconds": round(encode_seconds, 3),
                "total_wall_seconds": round(time.perf_counter() - started, 3),
                "frames_per_second": round(frames.count / render_seconds, 4),
                "frames": frames.count,
                "pixels": frames.count * spec.width * spec.height,
                "child_peak_rss_kib": child_usage.ru_maxrss,
            },
            "outputs": {
                "video_sha256": sha256(video),
                "encode_manifest_sha256": sha256(video.with_suffix(".manifest.json")),
                "video_bytes": video.stat().st_size,
            },
            "preview_frame_hashes": preview_hashes,
            "repeat_frame_determinism": repeated,
            "resolved_render_sha256": spec.render_sha256,
            "encode_manifest_output_sha256": encode_manifest["output"]["sha256"],
            "warnings": [],
        }
        atomic_json(result_path, result)
        return result_path
    except Exception as exc:
        atomic_json(result_path, {
            "schema_version": "1.0",
            "job_id": preview.get("job_id"),
            "status": "failed",
            "passed": False,
            "error_type": type(exc).__name__,
            "warnings": [str(exc)],
        })
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("/workspace/results"))
    parser.add_argument("--bundle-root", type=Path, default=BUNDLE_ROOT)
    args = parser.parse_args()
    print(render(args.job.resolve(), args.output_root.resolve(), args.bundle_root.resolve()))


if __name__ == "__main__":
    main()
