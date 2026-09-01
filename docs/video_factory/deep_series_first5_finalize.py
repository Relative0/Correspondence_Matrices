"""Create five narrated local episode masters from approved RunPod chapter masters."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
import uuid
import wave


FACTORY = Path(__file__).resolve().parent
REPO = FACTORY.parents[1]
DEEP_ROOT = FACTORY / "deep_series"
EPISODES_ROOT = DEEP_ROOT / "episodes"
RUN_ROOT = FACTORY / "runpod" / "deep_series_first5_v1"
TTS_SCRIPT = FACTORY / "synthesize_narration.ps1"
FIRST_FIVE = (
    "conceptual-vs-measured",
    "why-boolean-computation",
    "expression-truth-function",
    "live-support-ambient",
    "what-is-explicit-cm",
)
VOICE = "Microsoft Mark"
VOICE_RATE = 1
VOICE_VOLUME = 100
SAMPLE_RATE = 24000


class FinalizeError(RuntimeError):
    """Raised when a local narration, mux, or QA contract fails."""


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


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".pending-" + uuid.uuid4().hex)
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def artifact(path: Path) -> dict[str, Any]:
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def spoken_text(cue: dict[str, Any]) -> str:
    value = cue["text"]
    pronunciations = cue.get("pronunciation") or {}
    for source in sorted(pronunciations, key=len, reverse=True):
        value = value.replace(source, pronunciations[source])
    return value


def wav_info(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        return {
            "channels": handle.getnchannels(),
            "sample_width": handle.getsampwidth(),
            "sample_rate": handle.getframerate(),
            "frames": frames,
            "duration_s": frames / handle.getframerate(),
        }


def powershell() -> str:
    result = (
        os.environ.get("CM_POWERSHELL")
        or shutil.which("pwsh.exe")
        or shutil.which("powershell.exe")
    )
    if not result:
        raise FinalizeError("PowerShell is required for offline Windows SAPI")
    return result


def prepare_narration(video_id: str) -> dict[str, Any]:
    episode_root = EPISODES_ROOT / video_id
    output_root = episode_root / "output"
    cue_root = output_root / "work" / "narration_cues"
    narration = load(episode_root / "narration_contract.json")
    captions = load(episode_root / "caption_contract.json")
    caption_by_id = {item["cue_id"]: item for item in captions["cues"]}
    spoken_cues = [item for item in narration["cues"] if item["spoken"]]
    if set(caption_by_id) != {item["cue_id"] for item in spoken_cues}:
        raise FinalizeError(f"narration/caption cue mismatch: {video_id}")
    payload = {
        "voice": VOICE,
        "rate": VOICE_RATE,
        "volume": VOICE_VOLUME,
        "sample_rate": SAMPLE_RATE,
        "cues": [
            {
                "cue_id": cue["cue_id"],
                "text": spoken_text(cue),
                "output": str((cue_root / f"{cue['cue_id']}.wav").resolve()),
                "rate": VOICE_RATE,
            }
            for cue in spoken_cues
        ],
    }
    identity = canonical_sha256(payload)
    manifest_path = output_root / "work" / "narration_manifest.json"
    if manifest_path.is_file():
        prior = load(manifest_path)
        if prior.get("input_identity") == identity and all(
            (REPO / item["path"]).is_file()
            and sha256(REPO / item["path"]) == item["sha256"]
            for item in prior.get("cues", {}).values()
        ):
            return prior
    cue_root.mkdir(parents=True, exist_ok=True)
    input_path = output_root / "work" / "narration_input.json"
    atomic_json(input_path, payload)
    subprocess.run(
        [
            powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(TTS_SCRIPT),
            "-InputJson",
            str(input_path),
        ],
        check=True,
    )
    cue_by_id = {item["cue_id"]: item for item in payload["cues"]}
    for _retry in range(8):
        overlong = []
        for cue_id, item in cue_by_id.items():
            info = wav_info(Path(item["output"]))
            window = (
                caption_by_id[cue_id]["end_s"]
                - caption_by_id[cue_id]["start_s"]
            )
            if info["duration_s"] > window + 0.001:
                overlong.append(item)
        if not overlong:
            break
        for item in overlong:
            item["rate"] += 1
        retry_payload = {
            "voice": VOICE,
            "rate": VOICE_RATE,
            "volume": VOICE_VOLUME,
            "sample_rate": SAMPLE_RATE,
            "cues": overlong,
        }
        retry_path = output_root / "work" / "narration_retry_input.json"
        atomic_json(retry_path, retry_payload)
        subprocess.run(
            [
                powershell(),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(TTS_SCRIPT),
                "-InputJson",
                str(retry_path),
            ],
            check=True,
        )
    results: dict[str, Any] = {}
    for item in payload["cues"]:
        cue_id = item["cue_id"]
        path = Path(item["output"])
        info = wav_info(path)
        window = caption_by_id[cue_id]["end_s"] - caption_by_id[cue_id]["start_s"]
        if (
            (info["channels"], info["sample_width"], info["sample_rate"])
            != (1, 2, SAMPLE_RATE)
            or info["duration_s"] > window + 0.001
        ):
            raise FinalizeError(
                f"cue does not fit its declared window: {video_id}/{cue_id} "
                f"{info['duration_s']:.3f}s > {window:.3f}s"
            )
        results[cue_id] = {
            **artifact(path),
            **info,
            "window_s": round(window, 3),
            "synthesis_rate": item["rate"],
            "spoken_text_sha256": hashlib.sha256(
                item["text"].encode("utf-8")
            ).hexdigest(),
        }
    manifest = {
        "schema_version": "1.0",
        "status": "passed",
        "video_id": video_id,
        "provider": "offline_windows_sapi",
        "voice": VOICE,
        "rate": VOICE_RATE,
        "sample_rate": SAMPLE_RATE,
        "input_identity": identity,
        "cue_count": len(results),
        "cues": results,
        "remote_or_paid_work": False,
    }
    atomic_json(manifest_path, manifest)
    return manifest


def chapter_contracts(video_id: str) -> list[dict[str, Any]]:
    episode = load(EPISODES_ROOT / video_id / "episode.json")
    contracts = [
        load(
            EPISODES_ROOT
            / video_id
            / "chapters"
            / chapter_id
            / "executable_render_contract.json"
        )
        for chapter_id in episode["chapter_ids"]
    ]
    if [item["chapter_id"] for item in contracts] != episode["chapter_ids"]:
        raise FinalizeError(f"chapter order mismatch: {video_id}")
    return contracts


def assemble_chapter_wav(
    video_id: str,
    contract: dict[str, Any],
    narration_manifest: dict[str, Any],
    target: Path,
) -> None:
    episode_root = EPISODES_ROOT / video_id
    narration = load(episode_root / "narration_contract.json")
    captions = load(episode_root / "caption_contract.json")
    caption_by_id = {item["cue_id"]: item for item in captions["cues"]}
    frame_contract = contract["frame_contract"]
    chapter_start_sample = round(
        frame_contract["chapter_start_frame"]
        / frame_contract["fps"]
        * SAMPLE_RATE
    )
    chapter_end_sample = round(
        frame_contract["chapter_end_frame"]
        / frame_contract["fps"]
        * SAMPLE_RATE
    )
    total_frames = round(
        frame_contract["duration_frames"] / frame_contract["fps"] * SAMPLE_RATE
    )
    if chapter_end_sample - chapter_start_sample != total_frames:
        raise FinalizeError(f"non-integral chapter audio boundary: {video_id}")
    pcm = bytearray(total_frames * 2)
    for cue in narration["cues"]:
        if not cue["spoken"]:
            continue
        caption = caption_by_id[cue["cue_id"]]
        source_path = REPO / narration_manifest["cues"][cue["cue_id"]]["path"]
        with wave.open(str(source_path), "rb") as source:
            audio = source.readframes(source.getnframes())
        cue_start_sample = round(caption["start_s"] * SAMPLE_RATE)
        cue_end_sample = cue_start_sample + len(audio) // 2
        overlap_start = max(cue_start_sample, chapter_start_sample)
        overlap_end = min(cue_end_sample, chapter_end_sample)
        if overlap_start >= overlap_end:
            continue
        source_start = (overlap_start - cue_start_sample) * 2
        source_end = source_start + (overlap_end - overlap_start) * 2
        target_start = (overlap_start - chapter_start_sample) * 2
        target_end = target_start + (overlap_end - overlap_start) * 2
        pcm[target_start:target_end] = audio[source_start:source_end]
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm)


def ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(args: list[str]) -> None:
    completed = subprocess.run(
        [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args],
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise FinalizeError("ffmpeg failed: " + completed.stderr.strip())


def probe(path: Path) -> dict[str, Any]:
    import av

    with av.open(str(path)) as container:
        video = next(stream for stream in container.streams if stream.type == "video")
        audio = next(
            (stream for stream in container.streams if stream.type == "audio"), None
        )
        subtitles = [stream for stream in container.streams if stream.type == "subtitle"]
        duration = (
            float(container.duration / av.time_base)
            if container.duration is not None
            else 0.0
        )
        return {
            "duration_s": duration,
            "width": video.width,
            "height": video.height,
            "fps": float(video.average_rate),
            "video_codec": video.codec_context.name,
            "pixel_format": video.codec_context.pix_fmt,
            "audio_codec": audio.codec_context.name if audio else None,
            "audio_rate": audio.codec_context.sample_rate if audio else None,
            "audio_channels": audio.codec_context.channels if audio else None,
            "subtitle_codecs": [stream.codec_context.name for stream in subtitles],
        }


def verified_remote_attempt() -> Path:
    candidates = sorted(RUN_ROOT.glob("remote/*/attempt-*/LOCAL_VERIFICATION.json"))
    for verification_path in reversed(candidates):
        verification = load(verification_path)
        if verification.get("status") == "passed" and verification.get("jobs") == 17:
            attempt_root = verification_path.parent
            run_summary = attempt_root.parent / "RUN_SUMMARY.json"
            if run_summary.is_file() and load(run_summary).get("passed") is True:
                return attempt_root
    raise FinalizeError("no passed 17-job RunPod attempt is available")


def remote_video(attempt_root: Path, video_id: str, chapter_id: str) -> Path:
    job_id = f"{video_id}-{chapter_id}-production"
    root = attempt_root / "extracted" / "results" / job_id
    result = load(root / "render_result.json")
    video = root / f"{job_id}.mp4"
    if (
        result.get("passed") is not True
        or result.get("job_id") != job_id
        or not video.is_file()
        or sha256(video) != result["outputs"]["video_sha256"]
    ):
        raise FinalizeError(f"remote chapter identity mismatch: {job_id}")
    return video


def write_contact_sheet(video: Path, output: Path) -> None:
    import av
    from PIL import Image, ImageDraw

    with av.open(str(video)) as container:
        duration = float(container.duration / av.time_base)
        samples = [duration * (index + 1) / 13 for index in range(12)]
        frames = []
        for timestamp in samples:
            container.seek(int(timestamp * av.time_base), any_frame=False, backward=True)
            frame = next(
                candidate
                for candidate in container.decode(video=0)
                if candidate.time is not None
                and float(candidate.time) >= timestamp - (1 / 30)
            )
            frames.append((timestamp, frame.to_image().resize((480, 270))))
    sheet = Image.new("RGB", (1920, 870), (16, 18, 22))
    draw = ImageDraw.Draw(sheet)
    for index, (timestamp, frame) in enumerate(frames):
        x = index % 4 * 480
        y = index // 4 * 290
        draw.text((x + 7, y + 3), f"{timestamp:06.1f}s", fill=(220, 225, 232))
        sheet.paste(frame, (x, y + 20))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def finalize_episode(video_id: str, attempt_root: Path) -> dict[str, Any]:
    episode_root = EPISODES_ROOT / video_id
    output_root = episode_root / "output"
    chapter_output_root = output_root / "chapters"
    narration_manifest = prepare_narration(video_id)
    contracts = chapter_contracts(video_id)
    chapter_results = []
    for contract in contracts:
        chapter_id = contract["chapter_id"]
        silent = remote_video(attempt_root, video_id, chapter_id)
        chapter_root = chapter_output_root / chapter_id
        audio = chapter_root / "narration.wav"
        assembled = chapter_root / f"{video_id}-{chapter_id}.mp4"
        assemble_chapter_wav(video_id, contract, narration_manifest, audio)
        duration = contract["frame_contract"]["duration_frames"] / 30
        run_ffmpeg(
            [
                "-i",
                str(silent),
                "-i",
                str(audio),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-t",
                f"{duration:.6f}",
                "-map_metadata",
                "-1",
                "-movflags",
                "+faststart",
                str(assembled),
            ]
        )
        technical = probe(assembled)
        if (
            technical["audio_codec"] != "aac"
            or technical["audio_rate"] != 48000
            or technical["audio_channels"] != 2
            or abs(technical["duration_s"] - duration) > 0.1
        ):
            raise FinalizeError(f"chapter mux QA failed: {video_id}/{chapter_id}")
        chapter_results.append(
            {
                "chapter_id": chapter_id,
                "duration_s": round(duration, 3),
                "silent_video": artifact(silent),
                "narration": artifact(audio),
                "video": artifact(assembled),
                "technical": technical,
            }
        )

    concat = output_root / "work" / "chapters.concat.txt"
    concat.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for result in chapter_results:
        path = (REPO / result["video"]["path"]).resolve().as_posix()
        lines.append("file '" + path.replace("'", "'\\''") + "'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    joined = output_root / "work" / f"{video_id}.joined.mp4"
    run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat),
            "-c",
            "copy",
            "-map_metadata",
            "-1",
            "-movflags",
            "+faststart",
            str(joined),
        ]
    )
    sidecar = output_root / f"{video_id}.en-US.vtt"
    shutil.copyfile(episode_root / "captions.vtt", sidecar)
    final_video = output_root / f"{video_id}.mp4"
    run_ffmpeg(
        [
            "-i",
            str(joined),
            "-i",
            str(sidecar),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-map",
            "1:0",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            "language=eng",
            "-map_metadata",
            "-1",
            "-movflags",
            "+faststart",
            str(final_video),
        ]
    )
    audio_master = output_root / f"{video_id}.m4a"
    run_ffmpeg(
        [
            "-i",
            str(final_video),
            "-vn",
            "-c:a",
            "copy",
            "-map_metadata",
            "-1",
            str(audio_master),
        ]
    )
    contact_sheet = output_root / "CONTACT_SHEET.png"
    write_contact_sheet(final_video, contact_sheet)
    technical = probe(final_video)
    expected_duration = sum(
        item["frame_contract"]["duration_frames"] for item in contracts
    ) / 30
    qa = {
        "chapter_count_matches": len(chapter_results) == len(contracts),
        "duration_matches": abs(technical["duration_s"] - expected_duration) <= 0.15,
        "video_contract_passed": technical["width"] == 1920
        and technical["height"] == 1080
        and abs(technical["fps"] - 30) < 0.01
        and technical["video_codec"] == "h264"
        and technical["pixel_format"] == "yuv420p",
        "audio_contract_passed": technical["audio_codec"] == "aac"
        and technical["audio_rate"] == 48000
        and technical["audio_channels"] == 2,
        "embedded_caption_contract_passed": "mov_text"
        in technical["subtitle_codecs"],
        "sidecar_caption_present": sidecar.is_file() and sidecar.stat().st_size > 0,
        "decoded_contact_sheet_present": contact_sheet.is_file()
        and contact_sheet.stat().st_size > 0,
        "all_remote_chapter_hashes_verified": True,
    }
    qa["passed"] = all(qa.values())
    release = {
        "schema_version": "1.0",
        "status": "qa_passed" if qa["passed"] else "qa_failed",
        "video_id": video_id,
        "source_run": relative(attempt_root),
        "bible_content_hash": load(
            DEEP_ROOT / "first_five_review" / "approval.json"
        )["bible_content_hash"],
        "review_manifest_sha256": load(
            DEEP_ROOT / "first_five_review" / "approval.json"
        )["review_manifest_sha256"],
        "proposal_identity": load(RUN_ROOT / "authorization.json")[
            "proposal_identity"
        ],
        "narration_manifest": artifact(
            output_root / "work" / "narration_manifest.json"
        ),
        "chapters": chapter_results,
        "outputs": {
            "video": artifact(final_video),
            "audio_master": artifact(audio_master),
            "captions": artifact(sidecar),
            "contact_sheet": artifact(contact_sheet),
        },
        "technical": technical,
        "qa": qa,
        "publication_authorized": False,
        "content_hash": "0" * 64,
    }
    release["content_hash"] = canonical_sha256(
        {key: value for key, value in release.items() if key != "content_hash"}
    )
    atomic_json(output_root / "release_manifest.json", release)
    if not qa["passed"]:
        raise FinalizeError(f"episode QA failed: {video_id}")
    return release


def finalize_all() -> dict[str, Any]:
    attempt_root = verified_remote_attempt()
    releases = [finalize_episode(video_id, attempt_root) for video_id in FIRST_FIVE]
    summary = {
        "schema_version": "1.0",
        "status": "qa_passed",
        "episode_count": len(releases),
        "episodes": [
            {
                "video_id": item["video_id"],
                "video": item["outputs"]["video"],
                "duration_s": item["technical"]["duration_s"],
                "release_manifest": artifact(
                    EPISODES_ROOT / item["video_id"] / "output" / "release_manifest.json"
                ),
            }
            for item in releases
        ],
        "source_run": relative(attempt_root),
        "publication_authorized": False,
    }
    atomic_json(DEEP_ROOT / "first_five_release_manifest.json", summary)
    return summary


def verify_artifact(reference: dict[str, Any]) -> Path:
    path = REPO / reference["path"]
    if (
        not path.is_file()
        or path.stat().st_size != reference["bytes"]
        or sha256(path) != reference["sha256"]
    ):
        raise FinalizeError(f"release artifact mismatch: {reference['path']}")
    return path


def validate_release() -> dict[str, Any]:
    summary_path = DEEP_ROOT / "first_five_release_manifest.json"
    summary = load(summary_path)
    if (
        summary.get("status") != "qa_passed"
        or summary.get("episode_count") != 5
        or summary.get("publication_authorized") is not False
        or [item["video_id"] for item in summary.get("episodes", [])]
        != list(FIRST_FIVE)
    ):
        raise FinalizeError("first-five release summary is incomplete")
    attempt_root = REPO / summary["source_run"]
    run_summary = load(attempt_root.parent / "RUN_SUMMARY.json")
    postflight = load(attempt_root / "RUNPOD_POSTFLIGHT.json")
    if (
        run_summary.get("passed") is not True
        or run_summary.get("owned_pod_absent_verified") is not True
        or postflight.get("owned_pod_absent_verified") is not True
        or postflight.get("credential_value_recorded") is not False
    ):
        raise FinalizeError("remote production postflight is incomplete")
    durations = []
    for entry in summary["episodes"]:
        video = verify_artifact(entry["video"])
        release_path = verify_artifact(entry["release_manifest"])
        release = load(release_path)
        expected_identity = canonical_sha256(
            {key: value for key, value in release.items() if key != "content_hash"}
        )
        if (
            release.get("status") != "qa_passed"
            or release.get("video_id") != entry["video_id"]
            or release.get("content_hash") != expected_identity
            or release.get("qa", {}).get("passed") is not True
            or release.get("publication_authorized") is not False
            or len(release.get("chapters", []))
            != len(chapter_contracts(entry["video_id"]))
        ):
            raise FinalizeError(f"release manifest mismatch: {entry['video_id']}")
        for reference in release["outputs"].values():
            verify_artifact(reference)
        for chapter in release["chapters"]:
            verify_artifact(chapter["silent_video"])
            verify_artifact(chapter["narration"])
            verify_artifact(chapter["video"])
        narration_manifest = load(verify_artifact(release["narration_manifest"]))
        if narration_manifest.get("status") != "passed":
            raise FinalizeError(f"narration manifest failed: {entry['video_id']}")
        for cue in narration_manifest["cues"].values():
            verify_artifact(cue)
            if cue["duration_s"] > cue["window_s"] + 0.001:
                raise FinalizeError(f"narration cue exceeds window: {entry['video_id']}")
        current_technical = probe(video)
        if (
            current_technical["width"] != 1920
            or current_technical["height"] != 1080
            or abs(current_technical["fps"] - 30) >= 0.01
            or current_technical["video_codec"] != "h264"
            or current_technical["audio_codec"] != "aac"
            or "mov_text" not in current_technical["subtitle_codecs"]
        ):
            raise FinalizeError(f"final media contract failed: {entry['video_id']}")
        durations.append(current_technical["duration_s"])
    return {
        "status": "passed",
        "episodes": len(summary["episodes"]),
        "chapters": 17,
        "duration_s": round(sum(durations), 3),
        "controller_estimated_cost_usd": run_summary["estimated_compute_cost_usd"],
        "billed_amount_usd_visible": postflight["billed_amount_usd_visible"],
        "owned_pod_absent_verified": True,
    }


def validate_timing() -> dict[str, Any]:
    total_cues = 0
    total_chapters = 0
    total_frames = 0
    for video_id in FIRST_FIVE:
        narration = load(EPISODES_ROOT / video_id / "narration_contract.json")
        captions = load(EPISODES_ROOT / video_id / "caption_contract.json")
        contracts = chapter_contracts(video_id)
        caption_by_id = {item["cue_id"]: item for item in captions["cues"]}
        spoken_cues = [item for item in narration["cues"] if item["spoken"]]
        if set(caption_by_id) != {item["cue_id"] for item in spoken_cues}:
            raise FinalizeError(f"cue topology mismatch: {video_id}")
        episode_end = contracts[-1]["frame_contract"]["chapter_end_frame"] / 30
        for cue in spoken_cues:
            caption = caption_by_id[cue["cue_id"]]
            if (
                caption["start_s"] < 0
                or caption["end_s"] <= caption["start_s"]
                or caption["end_s"] > episode_end + (1 / 30) + 0.001
                or abs(
                    caption["end_s"]
                    - caption["start_s"]
                    - cue["timing_target_s"]
                )
                > 0.002
            ):
                raise FinalizeError(f"invalid episode timing: {video_id}/{cue['cue_id']}")
        total_cues += len(spoken_cues)
        total_chapters += len(contracts)
        total_frames += sum(
            item["frame_contract"]["duration_frames"] for item in contracts
        )
    if (total_chapters, total_frames) != (17, 68399):
        raise FinalizeError("first-five timing scope changed")
    return {
        "status": "passed",
        "episodes": 5,
        "chapters": total_chapters,
        "cues": total_cues,
        "frames": total_frames,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("validate", "prepare-narration", "finalize", "validate-release"),
    )
    args = parser.parse_args()
    if args.command == "validate":
        print(json.dumps(validate_timing(), indent=2))
    elif args.command == "prepare-narration":
        validate_timing()
        results = [prepare_narration(video_id) for video_id in FIRST_FIVE]
        print(
            json.dumps(
                {
                    "status": "passed",
                    "episodes": len(results),
                    "cues": sum(item["cue_count"] for item in results),
                    "remote_or_paid_work": False,
                },
                indent=2,
            )
        )
    elif args.command == "finalize":
        validate_timing()
        print(json.dumps(finalize_all(), indent=2))
    else:
        validate_timing()
        print(json.dumps(validate_release(), indent=2))


if __name__ == "__main__":
    main()
