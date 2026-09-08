"""Create offline-neural narration, captions, and narrated review animatics.

The model and voice pack must already exist in the ignored video-factory temp
directory. This tool never calls a network service and never publishes media.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs" / "video_factory" / "deep_series" / "foundational_cm_production_v2"
MODEL = ROOT / "docs" / "video_factory" / "tmp" / "kokoro" / "kokoro-v1.0.onnx"
VOICES = ROOT / "docs" / "video_factory" / "tmp" / "kokoro" / "voices-v1.0.bin"
AUDITION_VOICES = ("af_heart", "af_bella", "bf_emma")
DEFAULT_VOICE = "af_heart"
REMOTE_OR_PAID = os.environ.get("CM_REMOTE_WORK") == "1"
AUDITION_TEXT = (
    "The paper writes the true state as ket one, a column vector one-zero, "
    "and false as ket zero, zero-one. Transposing a ket gives a bra, which is "
    "a row vector. Take a ket times a bra as an outer product. The four "
    "possible pairs produce four two-by-two matrices, each with exactly one "
    "active cell. These are the four basis dyads."
)


class NarrationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recorded_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_ffmpeg() -> str:
    direct = shutil.which("ffmpeg")
    if direct:
        return direct
    candidates = sorted(
        Path.home().glob("AppData/Local/Programs/Python/Python*/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-*.exe")
    )
    if candidates:
        return str(candidates[-1])
    raise NarrationError("ffmpeg was not found")


def require_models() -> None:
    missing = [str(path) for path in (MODEL, VOICES) if not path.is_file()]
    if missing:
        raise NarrationError(f"offline Kokoro files are missing: {missing}")


def audio_facts(path: Path) -> dict[str, Any]:
    info = sf.info(path)
    samples, _ = sf.read(path, dtype="float32", always_2d=False)
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
    return {
        "path": recorded_path(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "sample_rate_hz": info.samplerate,
        "channels": info.channels,
        "duration_s": round(info.duration, 6),
        "peak_dbfs": round(20 * math.log10(max(peak, 1e-12)), 3),
    }


def make_auditions(kokoro: Kokoro) -> dict[str, Any]:
    root = PACKAGE / "narration" / "auditions"
    root.mkdir(parents=True, exist_ok=True)
    results = []
    for voice in AUDITION_VOICES:
        samples, sample_rate = kokoro.create(
            AUDITION_TEXT, voice=voice, speed=0.98, lang="en-us", sentence_pause=0.32, clause_pause=0.12
        )
        target = root / f"{voice}.wav"
        sf.write(target, samples, sample_rate, subtype="PCM_16")
        results.append({"voice": voice, **audio_facts(target)})
    manifest = {
        "schema_version": "1.0",
        "status": "human_voice_selection_required",
        "provider": "local_kokoro_onnx",
        "voices": results,
        "shared_text": AUDITION_TEXT,
        "model_sha256": sha256(MODEL),
        "voice_pack_sha256": sha256(VOICES),
        "remote_or_paid_work": REMOTE_OR_PAID,
    }
    write_json(root / "AUDITION_MANIFEST_V2.json", manifest)
    return manifest


def silence(seconds: float, sample_rate: int) -> np.ndarray:
    return np.zeros(int(round(seconds * sample_rate)), dtype=np.float32)


def synthesize_segments(
    kokoro: Kokoro, segments: list[dict[str, Any]], voice: str, speed: float
) -> tuple[np.ndarray, int, list[dict[str, Any]]]:
    pieces: list[np.ndarray] = []
    timing: list[dict[str, Any]] = []
    sample_rate = 24000
    cursor = 0
    for segment in segments:
        if segment["kind"] == "pause":
            samples = silence(float(segment["duration_s"]), sample_rate)
            pieces.append(samples)
            timing.append({"kind": "pause", "start_sample": cursor, "end_sample": cursor + len(samples)})
            cursor += len(samples)
            continue
        text = str(segment["text"]).strip()
        samples, actual_rate = kokoro.create(
            text, voice=voice, speed=speed, lang="en-us", sentence_pause=0.32, clause_pause=0.12
        )
        if actual_rate != sample_rate:
            raise NarrationError(f"unexpected Kokoro sample rate: {actual_rate}")
        samples = np.asarray(samples, dtype=np.float32)
        pieces.append(samples)
        timing.append({
            "kind": "speech", "text": text, "start_sample": cursor, "end_sample": cursor + len(samples)
        })
        cursor += len(samples)
    return np.concatenate(pieces) if pieces else silence(0, sample_rate), sample_rate, timing


def caption_text(text: str) -> str:
    replacements = (
        ("C Ms", "CMs"), ("L Ms", "LMs"), ("C M", "CM"), ("L M", "LM"),
        ("V sub T", "V_T"), ("exclusive-or", "XOR"),
    )
    for spoken, display in replacements:
        text = text.replace(spoken, display)
    return " ".join(text.split())


def vtt_time(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def write_vtt(path: Path, captions: list[dict[str, Any]]) -> None:
    lines = ["WEBVTT", ""]
    for index, cue in enumerate(captions, 1):
        lines.extend([
            str(index),
            f"{vtt_time(cue['start_s'])} --> {vtt_time(cue['end_s'])}",
            caption_text(cue["text"]),
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")


def synthesize_episode(kokoro: Kokoro, video_id: str, voice: str, speed: float = 0.98) -> dict[str, Any]:
    contract_path = PACKAGE / "episodes" / video_id / "NARRATION_CONTRACT_V2.json"
    if not contract_path.is_file():
        raise NarrationError(f"narration contract not found: {contract_path}")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    duration_s = max(float(cue["end_s"]) for cue in contract["cues"])
    sample_rate = 24000
    master = silence(duration_s, sample_rate)
    cue_root = PACKAGE / "narration" / video_id / "cues"
    cue_root.mkdir(parents=True, exist_ok=True)
    captions: list[dict[str, Any]] = []
    cue_results = []
    for cue in contract["cues"]:
        cue_speed = speed
        samples, actual_rate, timing = synthesize_segments(kokoro, cue["segments"], voice, cue_speed)
        window_s = float(cue["window_s"])
        available_s = max(0.1, window_s - 1.0)
        if len(samples) / actual_rate > available_s:
            requested = cue_speed * (len(samples) / actual_rate) / available_s
            cue_speed = min(1.12, requested)
            samples, actual_rate, timing = synthesize_segments(kokoro, cue["segments"], voice, cue_speed)
        spoken_s = len(samples) / actual_rate
        if spoken_s > window_s - 0.25:
            raise NarrationError(
                f"{video_id} {cue['cue_id']} narration {spoken_s:.2f}s exceeds {window_s:.2f}s window"
            )
        lead_s = min(0.65, max(0.25, (window_s - spoken_s) * 0.28))
        start_sample = int(round((float(cue["start_s"]) + lead_s) * sample_rate))
        end_sample = start_sample + len(samples)
        master[start_sample:end_sample] += samples
        cue_path = cue_root / f"{cue['cue_id']}.wav"
        sf.write(cue_path, samples, sample_rate, subtype="PCM_16")
        for item in timing:
            if item["kind"] != "speech":
                continue
            captions.append({
                "start_s": start_sample / sample_rate + item["start_sample"] / sample_rate,
                "end_s": start_sample / sample_rate + item["end_sample"] / sample_rate,
                "text": item["text"],
            })
        cue_results.append({
            "cue_id": cue["cue_id"], "window_s": window_s, "lead_s": round(lead_s, 3),
            "spoken_s": round(spoken_s, 3), "speed": round(cue_speed, 4),
            "path": recorded_path(cue_path), "sha256": sha256(cue_path),
        })
    peak = float(np.max(np.abs(master))) if len(master) else 0.0
    if peak > 0:
        master *= (10 ** (-3.0 / 20)) / peak
    output_root = PACKAGE / "narration" / video_id
    premaster = output_root / f"{video_id}.narration-premaster.wav"
    final = output_root / f"{video_id}.narration-48k.wav"
    captions_path = output_root / f"{video_id}.captions.vtt"
    sf.write(premaster, master, sample_rate, subtype="PCM_16")
    ffmpeg = find_ffmpeg()
    completed = subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(premaster),
        "-af", "loudnorm=I=-18:LRA=7:TP=-1.5", "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(final),
    ], text=True, capture_output=True, encoding="utf-8", errors="replace")
    if completed.returncode:
        raise NarrationError(f"audio normalization failed: {completed.stderr[-1200:]}")
    write_vtt(captions_path, captions)
    result = {
        "schema_version": "1.0", "status": "provisional_voice_human_review_required",
        "video_id": video_id, "provider": "local_kokoro_onnx", "voice": voice,
        "base_speed": speed, "audio": audio_facts(final),
        "captions": {"path": recorded_path(captions_path), "sha256": sha256(captions_path)},
        "cues": cue_results, "cue_windows_passed": True,
        "model_sha256": sha256(MODEL), "voice_pack_sha256": sha256(VOICES),
        "remote_or_paid_work": REMOTE_OR_PAID,
    }
    write_json(output_root / "NARRATION_RESULT_V2.json", result)
    return result


def make_review_animatic(video_id: str, narration: dict[str, Any]) -> dict[str, Any]:
    contract = json.loads(
        (PACKAGE / "episodes" / video_id / "PRODUCTION_CONTRACT_V2.json").read_text(encoding="utf-8")
    )
    preview_root = PACKAGE / "episodes" / video_id / "previews"
    frame_root = preview_root / "settled_frames"
    frames = sorted(frame_root.glob("f*.png"))
    if len(frames) != len(contract["scenes"]):
        raise NarrationError(f"settled frame count mismatch for {video_id}")
    work_root = PACKAGE / "narration" / video_id / "review"
    work_root.mkdir(parents=True, exist_ok=True)
    concat_path = work_root / "timed_frames.concat.txt"
    lines = []
    for frame, scene in zip(frames, contract["scenes"]):
        escaped = frame.resolve().as_posix().replace("'", "'\\''")
        lines.extend([f"file '{escaped}'", f"duration {float(scene['duration_s']):.6f}"])
    escaped = frames[-1].resolve().as_posix().replace("'", "'\\''")
    lines.append(f"file '{escaped}'")
    concat_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    audio = ROOT / narration["audio"]["path"]
    captions = ROOT / narration["captions"]["path"]
    output = work_root / f"{video_id}.narrated-review.mp4"
    ffmpeg = find_ffmpeg()
    completed = subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_path), "-i", str(audio), "-i", str(captions),
        "-map", "0:v:0", "-map", "1:a:0", "-map", "2:0", "-vf", "fps=30,format=yuv420p",
        "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-c:s", "mov_text",
        "-metadata:s:s:0", "language=eng", "-movflags", "+faststart", str(output),
    ], text=True, capture_output=True, encoding="utf-8", errors="replace")
    if completed.returncode:
        raise NarrationError(f"review animatic mux failed: {completed.stderr[-1200:]}")
    result = {
        "status": "provisional_voice_human_review_required", "video_id": video_id,
        "video": {"path": recorded_path(output), "sha256": sha256(output), "bytes": output.stat().st_size},
        "narration_result": "NARRATION_RESULT_V2.json", "remote_or_paid_work": REMOTE_OR_PAID,
    }
    write_json(work_root / "REVIEW_ANIMATIC_RESULT_V2.json", result)
    return result


def mux_master(video_id: str, narration: dict[str, Any], silent_master: Path) -> dict[str, Any]:
    if not silent_master.is_file():
        raise NarrationError(f"silent master not found: {silent_master}")
    audio = ROOT / narration["audio"]["path"]
    captions = ROOT / narration["captions"]["path"]
    output = silent_master.with_name(f"{video_id}.narrated-master.mp4")
    ffmpeg = find_ffmpeg()
    completed = subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(silent_master),
        "-i", str(audio), "-i", str(captions), "-map", "0:v:0", "-map", "1:a:0", "-map", "2:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "1",
        "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-map_metadata", "-1",
        "-movflags", "+faststart", str(output),
    ], text=True, capture_output=True, encoding="utf-8", errors="replace")
    if completed.returncode:
        raise NarrationError(f"master mux failed: {completed.stderr[-1200:]}")
    decoded = subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(output), "-f", "null", "-"
    ], text=True, capture_output=True, encoding="utf-8", errors="replace")
    if decoded.returncode:
        raise NarrationError(f"narrated master decode failed: {decoded.stderr[-1200:]}")
    result = {
        "schema_version": "1.0", "status": "provisional_voice_human_review_required",
        "video_id": video_id,
        "silent_master": {"path": recorded_path(silent_master), "sha256": sha256(silent_master)},
        "narrated_master": {
            "path": recorded_path(output), "sha256": sha256(output), "bytes": output.stat().st_size
        },
        "narration_audio": narration["audio"], "captions": narration["captions"],
        "video_stream_copied_without_reencoding": True, "decode_check_passed": True,
        "publication_authorized": False, "remote_or_paid_work": REMOTE_OR_PAID,
    }
    write_json(output.with_suffix(".result.json"), result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audition", "synthesize", "review-animatic", "mux-master"))
    parser.add_argument("--video-id")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--speed", type=float, default=0.98)
    parser.add_argument("--silent-master", type=Path)
    args = parser.parse_args()
    require_models()
    kokoro = Kokoro(str(MODEL), str(VOICES))
    if args.command == "audition":
        result = make_auditions(kokoro)
    else:
        if not args.video_id:
            parser.error("--video-id is required")
        result = synthesize_episode(kokoro, args.video_id, args.voice, args.speed)
        if args.command == "review-animatic":
            result = make_review_animatic(args.video_id, result)
        elif args.command == "mux-master":
            if not args.silent_master:
                parser.error("--silent-master is required for mux-master")
            result = mux_master(args.video_id, result, args.silent_master.resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
