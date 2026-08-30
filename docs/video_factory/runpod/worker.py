"""Offline render worker for one immutable CM video job."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
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


class Progress:
    def __init__(self, path: Path):
        self.path = path
        self.sequence = 0

    def emit(self, event: str, **fields: Any) -> None:
        self.sequence += 1
        record = {"schema_version": "1.0", "sequence": self.sequence, "event": event, **fields}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()


def verify_bundle(root: Path) -> dict[str, Any]:
    manifest_path = root / "package_manifest.json"
    manifest = json.loads(manifest_path.read_text("utf-8"))
    for entry in manifest["files"]:
        path = root / entry["path"]
        if not path.is_file() or path.stat().st_size != entry["size"] or sha256(path) != entry["sha256"]:
            raise ValueError(f"bundle file mismatch: {entry['path']}")
    payload = hashlib.sha256(canonical_bytes(manifest["files"])).hexdigest()
    if payload != manifest["payload_sha256"]:
        raise ValueError("bundle payload identity mismatch")
    return manifest


def probe(video: Path) -> dict[str, Any]:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    data = json.loads(proc.stdout)
    stream = next(item for item in data["streams"] if item["codec_type"] == "video")
    rate_n, rate_d = stream["avg_frame_rate"].split("/", 1)
    return {
        "width": int(stream["width"]), "height": int(stream["height"]),
        "fps": float(rate_n) / float(rate_d), "codec": stream["codec_name"],
        "pixel_format": stream.get("pix_fmt"), "duration_s": float(data["format"]["duration"]),
        "has_audio": any(item["codec_type"] == "audio" for item in data["streams"]),
    }


def preview_frames(video: Path, directory: Path, duration_s: float) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    samples = {
        "opening": min(0.2, duration_s / 20), "early": duration_s * 0.25,
        "middle": duration_s * 0.5, "settled": duration_s * 0.8,
        "final": max(0.0, duration_s - 0.1),
    }
    hashes = {}
    for name, timestamp in samples.items():
        output = directory / f"{name}.png"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{timestamp:.6f}", "-i", str(video),
             "-frames:v", "1", str(output)], check=True,
        )
        hashes[name] = sha256(output)
    return hashes


def job_for_id(batch: dict[str, Any], job_path: Path) -> dict[str, Any]:
    job = json.loads(job_path.read_text("utf-8"))
    expected = batch["job_hashes"].get(job["job_id"])
    if expected is None or sha256(job_path) != expected:
        raise ValueError("job is absent from, or does not match, the batch manifest")
    return job


def render(job_path: Path, output_root: Path, *, bundle_root: Path = BUNDLE_ROOT) -> Path:
    job_preview = json.loads(job_path.read_text("utf-8"))
    output = output_root / job_preview["job_id"]
    progress = Progress(output / "progress.jsonl")
    result_path = output / "render_result.json"
    progress.emit("worker_started")
    try:
        package = verify_bundle(bundle_root)
        batch = json.loads((bundle_root / "cm" / "batch_manifest.json").read_text("utf-8"))
        job = job_for_id(batch, job_path)
        progress.emit("inputs_verified", job_id=job["job_id"], cache_identity=job["cache_identity"])

        proof = bundle_root / "cm" / "proofs" / job["video_id"]
        spec_path = proof / "resolved.spec.json"
        if sha256(spec_path) != job["resolved_spec_hash"]:
            raise ValueError("resolved spec hash does not match render job")
        assembly = json.loads((proof / "assembly.spec.json").read_text("utf-8"))
        request = assembly["slots"][0]["source"]["request"]
        request["spec"] = str(spec_path)
        request["spec_sha256"] = sha256(spec_path)
        runtime_spec = output / "runtime.assembly.spec.json"
        atomic_json(runtime_spec, assembly)

        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join((str(bundle_root / "ivc" / "src"), str(bundle_root / "pop"))),
            "IVC_VIDEO_SPEC_ROOTS": str(bundle_root / "cm"),
            "IVC_DATA": str(output / "cache"),
            "IVC_LIBRARY": str(output / "unused-library"),
            "POP_VIDEO_CREATOR_DIR": str(bundle_root / "pop"),
            "POP_VIDEO_CREATOR_PYTHON": sys.executable,
            "POP_VIDEO_FFMPEG": os.environ.get("POP_VIDEO_FFMPEG", "/usr/bin/ffmpeg"),
            "PYTHONIOENCODING": "utf-8",
        }
        run_root = output / "ivc-output"
        progress.emit("render_started")
        proc = subprocess.run(
            [sys.executable, "-m", "ivc.cli", "render", str(runtime_spec), "--out", str(run_root), "--json"],
            env=env, cwd=bundle_root / "ivc", capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "IVC render failed")[-2000:])
        videos = sorted(run_root.glob("*/*-16x9.mp4"))
        if len(videos) != 1:
            raise RuntimeError(f"expected one encoded output, found {len(videos)}")
        video = videos[0]
        run_dir = video.parent
        technical = probe(video)
        expected = job["format"]
        if (technical["width"], technical["height"], round(technical["fps"])) != (
            expected["width"], expected["height"], expected["fps"]
        ) or technical["codec"] != "h264" or technical["has_audio"]:
            raise RuntimeError(f"encoded media contract mismatch: {technical}")
        previews = preview_frames(video, output / "previews", technical["duration_s"])
        outputs = {
            "video": sha256(video), "provenance": sha256(run_dir / "provenance.json"),
            "gap_report": sha256(run_dir / "gap_report.json"),
            "cadence_report": sha256(run_dir / "cadence_report.json"),
        }
        result = {
            "schema_version": "1.0", "job_id": job["job_id"],
            "cache_identity": job["cache_identity"], "status": "passed",
            "outputs": outputs,
            "technical_observations": {**technical, "bundle_payload_sha256": package["payload_sha256"]},
            "preview_frame_hashes": previews, "warnings": [], "passed": True,
        }
        atomic_json(result_path, result)
        progress.emit("result_committed", render_result_sha256=sha256(result_path))
        return result_path
    except Exception as exc:
        atomic_json(result_path, {
            "schema_version": "1.0", "job_id": job_preview["job_id"],
            "cache_identity": job_preview["cache_identity"], "status": "failed",
            "outputs": {},
            "technical_observations": {"error_type": type(exc).__name__},
            "preview_frame_hashes": {}, "warnings": [str(exc)], "passed": False,
        })
        progress.emit("worker_failed", error_type=type(exc).__name__)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("/workspace/results"))
    parser.add_argument("--bundle-root", type=Path, default=BUNDLE_ROOT)
    args = parser.parse_args()
    print(render(args.job.resolve(), args.output_root.resolve(), bundle_root=args.bundle_root.resolve()))


if __name__ == "__main__":
    main()
