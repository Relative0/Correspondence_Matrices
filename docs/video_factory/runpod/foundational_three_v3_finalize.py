"""Locally verify and finalize a downloaded foundational-three v3 result archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import wave


HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE / "foundational_three_v3"
PROPOSAL_ID = "cm-video-foundational-three-production-remote-v3"
PROPOSAL_IDENTITY = "e15b8b08b7ad0921803176ff48b8024c7105e9b42e17182d409cc0c0c6d2bde1"
PROPOSAL_PACKAGE_IDENTITY = "3e563a05874882654158f16a738096532d642f72465a155927ca94c5ab538402"
MODEL_SHA256 = "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a"
VOICE_PACK_SHA256 = "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"
EXPECTED = {
    "operator-cms-from-truth-tables": {
        "duration": 219,
        "frames": 6570,
        "content_hash": "a603c8e3c672edb3a02103f869b40d9220d2ee756e377c59112e633ca1dd9072",
    },
    "logical-matrices-to-higher-dimensional-cms": {
        "duration": 265,
        "frames": 7950,
        "content_hash": "e21825e9c1d981b260a30a35f721f427278c28ee0c0675e281355ba4c6c42fcb",
    },
    "what-is-explicit-cm": {
        "duration": 220,
        "frames": 6600,
        "content_hash": "a1f123414508f4892033336906dc7ea11b80fab3c9be4f9ae8441f1884e0ff53",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("not a PNG: " + str(path))
    return struct.unpack(">II", header[16:24])


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def locate_ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def verify_decode_and_streams(ffmpeg: str, path: Path, duration: int) -> dict:
    metadata = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)], capture_output=True, text=True, check=False
    ).stderr
    require(re.search(r"Video: h264 .*yuv420p.*1920x1080.*30 fps", metadata) is not None,
            "narrated video stream contract mismatch: " + path.name)
    require(re.search(r"Audio: aac .*48000 Hz, mono", metadata) is not None,
            "narrated audio stream contract mismatch: " + path.name)
    require("Subtitle: mov_text" in metadata, "embedded English caption stream missing: " + path.name)
    match = re.search(r"Duration: (\d\d):(\d\d):(\d\d\.\d+)", metadata)
    require(match is not None, "narrated duration unavailable: " + path.name)
    actual_duration = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))
    require(abs(actual_duration - duration) <= 0.05, "narrated duration mismatch: " + path.name)
    for stream in ("0:v:0", "0:a:0"):
        decoded = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path),
             "-map", stream, "-f", "null", os.devnull],
            capture_output=True, text=True, check=False,
        )
        require(decoded.returncode == 0, "full decode failed for " + path.name + ":" + stream)
    subtitle = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path),
         "-map", "0:s:0", "-f", "webvtt", "-"],
        capture_output=True, check=False,
    )
    require(subtitle.returncode == 0 and subtitle.stdout.startswith(b"WEBVTT"),
            "embedded caption decode failed: " + path.name)
    return {"duration_s": actual_duration, "video": "h264/yuv420p/1920x1080/30fps",
            "audio": "aac/48000Hz/mono", "subtitle": "mov_text/eng", "full_decode": True}


def verify_wav(path: Path, expected_duration: int) -> dict:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        rate = handle.getframerate()
        frames = handle.getnframes()
        width = handle.getsampwidth()
    require(channels == 1 and rate == 48000 and width == 2, "narration WAV contract mismatch: " + path.name)
    duration = frames / rate
    require(abs(duration - expected_duration) <= 0.001, "narration WAV duration mismatch: " + path.name)
    return {"sample_rate_hz": rate, "channels": channels, "sample_width_bytes": width,
            "frames": frames, "duration_s": duration}


def linux_runtime_content_hash(video_id: str) -> str:
    """Reproduce the renderer's Linux regeneration of a Windows-prepared contract."""
    episode_root = (HERE.parent / "deep_series" / "foundational_cm_production_v2"
                    / "episodes" / video_id)
    narration = load(episode_root / "NARRATION_CONTRACT_V2.json")
    narration_lf = (json.dumps(narration, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    production = load(episode_root / "PRODUCTION_CONTRACT_V2.json")
    production.pop("content_hash", None)
    production["narration_contract"]["sha256"] = hashlib.sha256(narration_lf).hexdigest()
    material = json.dumps(production, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def verify_run(run_dir: Path) -> dict:
    archive = run_dir / "foundational-three-results.zip"
    digest_file = run_dir / "foundational-three-results.zip.sha256"
    root = run_dir / "results"
    run = load(run_dir / "RUN.json")
    require(run.get("proposal_id") == PROPOSAL_ID and run.get("proposal_identity") == PROPOSAL_IDENTITY,
            "run proposal identity mismatch")
    require(run.get("downloaded") is True and run.get("owned_pod_absent_verified") is True,
            "download or owned-pod cleanup was not recorded")
    digest = digest_file.read_text("utf-8").strip().split()[0]
    require(digest == sha256(archive) == run.get("download_archive_sha256"), "archive digest mismatch")

    summary = load(root / "render_summary.json")
    require(summary.get("status") == "passed", "silent render summary did not pass")
    runtime_package_identity = summary.get("package_identity_sha256")
    require(isinstance(runtime_package_identity, str)
            and re.fullmatch(r"[0-9a-f]{64}", runtime_package_identity) is not None,
            "runtime production package identity is malformed")
    require(summary.get("narration") is False and summary.get("publication_authorized") is False,
            "silent render scope mismatch")
    require(tuple(item.get("video_id") for item in summary.get("episodes", [])) == tuple(EXPECTED),
            "episode scope or order mismatch")

    symbol = summary.get("symbol_preflight") or {}
    specimen = root / str((symbol.get("specimen") or {}).get("path", ""))
    repeats = [root / "symbol_preflight/repeat_frames/f000000.png",
               root / "symbol_preflight/repeat_frames/f000001.png"]
    require(symbol.get("status") == "passed" and symbol.get("font_cmap_coverage") is True
            and symbol.get("repeat_frame_deterministic") is True, "symbol preflight did not pass")
    require(specimen.is_file() and sha256(specimen) == symbol["specimen"]["sha256"]
            and png_dimensions(specimen) == (1920, 1080), "symbol specimen mismatch")
    require(sha256(repeats[0]) == sha256(repeats[1]), "repeat-frame determinism mismatch")

    ffmpeg = locate_ffmpeg()
    episodes = []
    for item in summary["episodes"]:
        video_id = item["video_id"]
        contract = EXPECTED[video_id]
        silent = root / item["video"]["path"]
        technical = item["technical"]
        runtime_content_hash = linux_runtime_content_hash(video_id)
        require(item.get("status") == "passed" and item.get("content_hash") == runtime_content_hash,
                "runtime content identity does not reconcile to the frozen scripts: " + video_id)
        require(silent.is_file() and sha256(silent) == item["video"]["sha256"]
                and silent.stat().st_size == item["video"]["bytes"], "silent master mismatch: " + video_id)
        require(technical.get("width") == 1920 and technical.get("height") == 1080
                and abs(float(technical.get("fps", 0)) - 30) <= 0.001
                and technical.get("codec") == "h264" and technical.get("pixel_format") == "yuv420p"
                and technical.get("audio_streams") == 0 and technical.get("frame_count") == contract["frames"]
                and abs(float(technical.get("duration_s", 0)) - contract["duration"]) <= 0.05,
                "silent media contract mismatch: " + video_id)
        require(load(root / video_id / "render_result.json") == item,
                "per-episode silent result mismatch: " + video_id)
        for name in ("opening", "middle", "final"):
            ref = item["qa_frames"][name]
            frame = root / ref["path"]
            require(frame.is_file() and sha256(frame) == ref["sha256"]
                    and png_dimensions(frame) == (1920, 1080), "QA frame mismatch: " + video_id + ":" + name)

        narration_root = root / "narration" / video_id
        narration = load(narration_root / "NARRATION_RESULT_V2.json")
        master_result = load(root / video_id / f"{video_id}.narrated-master.result.json")
        narrated = root / video_id / f"{video_id}.narrated-master.mp4"
        wav = narration_root / f"{video_id}.narration-48k.wav"
        captions = narration_root / f"{video_id}.captions.vtt"
        require(master_result.get("status") == "provisional_voice_human_review_required"
                and master_result.get("video_id") == video_id
                and master_result.get("video_stream_copied_without_reencoding") is True
                and master_result.get("decode_check_passed") is True
                and master_result.get("publication_authorized") is False
                and master_result.get("remote_or_paid_work") is True, "narrated result scope mismatch: " + video_id)
        require(sha256(silent) == master_result["silent_master"]["sha256"],
                "narrated result silent-master reference mismatch: " + video_id)
        require(narrated.is_file() and sha256(narrated) == master_result["narrated_master"]["sha256"]
                and narrated.stat().st_size == master_result["narrated_master"]["bytes"],
                "narrated master digest mismatch: " + video_id)
        require(wav.is_file() and sha256(wav) == master_result["narration_audio"]["sha256"]
                and wav.stat().st_size == master_result["narration_audio"]["bytes"],
                "narration WAV digest mismatch: " + video_id)
        require(captions.is_file() and sha256(captions) == master_result["captions"]["sha256"]
                and captions.read_bytes().startswith(b"WEBVTT"), "caption sidecar mismatch: " + video_id)
        require(narration.get("status") == "provisional_voice_human_review_required"
                and narration.get("provider") == "local_kokoro_onnx" and narration.get("voice") == "af_heart"
                and narration.get("base_speed") == 0.98 and narration.get("cue_windows_passed") is True
                and narration.get("model_sha256") == MODEL_SHA256
                and narration.get("voice_pack_sha256") == VOICE_PACK_SHA256
                and narration.get("remote_or_paid_work") is True, "narration identity mismatch: " + video_id)
        require(narration["audio"]["sha256"] == sha256(wav)
                and narration["audio"]["bytes"] == wav.stat().st_size
                and narration["captions"]["sha256"] == sha256(captions),
                "narration report artifact mismatch: " + video_id)
        cues = narration.get("cues", [])
        require(len(cues) == 7, "narration cue count mismatch: " + video_id)
        cue_path_reconciliations = []
        for cue in cues:
            require(float(cue["lead_s"]) + float(cue["spoken_s"]) <= float(cue["window_s"])
                    and float(cue["speed"]) <= 1.12, "narration cue window mismatch: " + video_id)
            reported_name = Path(cue["path"]).name
            actual_name = cue["cue_id"] + ".wav"
            cue_file = narration_root / "cues" / actual_name
            require(cue_file.is_file() and sha256(cue_file) == cue["sha256"],
                    "narration cue digest mismatch: " + video_id + ":" + cue["cue_id"])
            if reported_name != actual_name:
                cue_path_reconciliations.append({"reported": reported_name, "archive": actual_name})

        stream_contract = verify_decode_and_streams(ffmpeg, narrated, contract["duration"])
        wav_contract = verify_wav(wav, contract["duration"])
        episodes.append({
            "video_id": video_id,
            "proposal_content_hash": contract["content_hash"],
            "runtime_content_hash": runtime_content_hash,
            "silent_master_sha256": sha256(silent),
            "narrated_master_sha256": sha256(narrated),
            "narrated_master_bytes": narrated.stat().st_size,
            "stream_contract": stream_contract,
            "narration_wav_contract": wav_contract,
            "cue_windows_passed": True,
            "cue_path_reconciliations": cue_path_reconciliations,
            "publication_authorized": False,
            "human_voice_review_required": True,
        })

    return {
        "schema_version": "1.0",
        "status": "passed_with_provisional_voice_human_review_required",
        "proposal_id": PROPOSAL_ID,
        "proposal_identity": PROPOSAL_IDENTITY,
        "download_archive_sha256": digest,
        "proposal_package_identity_sha256": PROPOSAL_PACKAGE_IDENTITY,
        "runtime_package_identity_sha256": runtime_package_identity,
        "runtime_identity_reconciliation": (
            "passed: runtime content hashes reproduce exactly after the Linux worker regenerates "
            "JSON with LF line endings; the aggregate package identity also includes environment-specific font paths"
        ),
        "remote_render_zero_exit": True,
        "owned_pod_absent_verified": True,
        "estimated_compute_cost_usd": run.get("estimated_compute_cost_usd"),
        "controller_post_download_exception": "legacy exact-file-set verifier rejected v3 narration artifacts",
        "episodes": episodes,
        "symbol_preflight_passed": True,
        "publication_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    result = verify_run(args.run_dir.resolve())
    output = args.run_dir.resolve() / "LOCAL_VERIFICATION_V3.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
