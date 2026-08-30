"""Independently verify downloaded RunPod proof media and preview artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import av
from PIL import Image, ImageStat


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def probe(path: Path) -> dict[str, object]:
    with av.open(str(path)) as container:
        videos = [stream for stream in container.streams if stream.type == "video"]
        audios = [stream for stream in container.streams if stream.type == "audio"]
        if len(videos) != 1:
            raise RuntimeError(f"expected one video stream in {path}")
        stream = videos[0]
        rate = float(stream.average_rate)
        duration = float(container.duration or 0) / float(av.time_base)
        return {
            "width": stream.codec_context.width,
            "height": stream.codec_context.height,
            "fps": rate,
            "codec": stream.codec_context.name,
            "pixel_format": stream.codec_context.format.name,
            "duration_s": duration,
            "has_audio": bool(audios),
        }


def verify(run_dir: Path) -> dict[str, object]:
    record = json.loads((run_dir / "RUN.json").read_text("utf-8"))
    if record.get("status") != "passed" or record.get("owned_pod_absent_verified") is not True:
        raise RuntimeError("controller record is not passed and reconciled")
    jobs = []
    for media in record["verification"]["media"]:
        video = Path(media["video"])
        job_root = video.parents[2]
        result_path = job_root / "render_result.json"
        result = json.loads(result_path.read_text("utf-8"))
        technical = probe(video)
        expected = result["technical_observations"]
        checks = {
            "downloaded_video_hash": sha256(video) == media["video_sha256"] == result["outputs"]["video"],
            "dimensions": (technical["width"], technical["height"]) == (1920, 1080),
            "fps": abs(float(technical["fps"]) - 30.0) < 0.001,
            "codec": technical["codec"] == "h264",
            "pixel_format": technical["pixel_format"] == "yuv420p",
            "duration": abs(float(technical["duration_s"]) - float(expected["duration_s"])) < 0.01,
            "silent": technical["has_audio"] is False,
            "bundle_payload": expected["bundle_payload_sha256"] == record["verification"]["bundle_payload_sha256"],
        }
        preview_checks = {}
        for name, expected_hash in result["preview_frame_hashes"].items():
            preview = job_root / "previews" / f"{name}.png"
            with Image.open(preview) as image:
                extrema = ImageStat.Stat(image.convert("RGB")).extrema
                nontrivial = any(high - low >= 12 for low, high in extrema)
                dimensions = image.size == (1920, 1080)
            preview_checks[name] = {
                "sha256_matches": sha256(preview) == expected_hash,
                "dimensions": dimensions,
                "nontrivial_pixels": nontrivial,
            }
        if not all(checks.values()) or not all(
            all(values.values()) for values in preview_checks.values()
        ):
            raise RuntimeError(f"post-run QA failed for {result['job_id']}")
        jobs.append({
            "job_id": result["job_id"],
            "video": str(video),
            "video_sha256": sha256(video),
            "technical": technical,
            "checks": checks,
            "preview_checks": preview_checks,
            "status": "passed",
        })
    report = {
        "schema_version": "1.0",
        "status": "passed",
        "proposal_id": record["proposal_id"],
        "pod_id": record["pod_id"],
        "owned_pod_absent_verified": True,
        "jobs": jobs,
    }
    atomic_json(run_dir / "POST_RUN_QA.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.run_dir.resolve())
    print(json.dumps({"status": report["status"], "jobs": len(report["jobs"])}, indent=2))


if __name__ == "__main__":
    main()
