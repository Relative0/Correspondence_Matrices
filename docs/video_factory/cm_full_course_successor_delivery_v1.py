"""Encode the reviewed CM successor without touching frozen deliveries.

Commands:
  preflight  -- report the paid narration scope without reading credentials
  prepare    -- create an additive delivery package and render source frames
  generate   -- synthesize only revised spoken lessons through ElevenLabs
  generate-local -- synthesize revised lessons with the selected installed SAPI voice
  assemble   -- encode successor lesson MP4s from prepared frames/audio
  combine    -- produce refreshed foundation and advanced combined courses
  validate   -- decode, inspect structure, and preserve frozen package hashes

Only ``generate`` reads the existing ElevenLabs key from the root .env.  Its
value is held in memory and is never printed or written to the delivery.
"""
from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256
from pathlib import Path
import base64
import copy
import csv
import json
import math
import re
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
import wave

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE / "deep_series" / "cm_full_course_successor_v1"
OUT = HERE / "deep_series" / "cm_full_course_successor_delivery_v1"
FOUNDATION = HERE / "deep_series" / "foundational_cm_tutorial_series_v2"
ADVANCED = HERE / "deep_series" / "advanced_cm_tutorial_series_v1"
sys.path.insert(0, str(HERE))

import cm_full_course_successor_v1 as successor

VOICE = "Fu3xLoDFv9UvgA2FXCUS"
MODEL = "eleven_multilingual_v2"
SETTINGS = {"stability": 0.85, "similarity_boost": 0.8, "style": 0.0, "use_speaker_boost": True, "speed": 0.95}
LOCAL_VOICE = "Microsoft Zira Desktop"
LOCAL_VOICE_RATE = 0
LOCAL_SYNTH_SCRIPT = HERE / "synthesize_local_voice.ps1"
FPS = 30
REVISED_SPOKEN = {
    "04_symbolic_implication", "07_compound_rule", "10_transpose", "15_lm_factors",
    "16_lm_measurement", "18_larger_operations", "20_public_api", "21_packed_outputs",
}
REUSED_AUDIO = {"17_larger_tensors"}
TARGETS = REVISED_SPOKEN | REUSED_AUDIO


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2))


def sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError("Command failed:\n" + " ".join(args) + "\n" + result.stderr[-4000:])
    return result


def ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def get_lesson(lessons: list[dict], lesson_id: str) -> dict:
    return next(lesson for lesson in lessons if lesson["id"] == lesson_id)


def source_root(lesson_id: str) -> Path:
    return FOUNDATION if int(lesson_id[:2]) < 10 else ADVANCED


def source_version(lesson_id: str) -> str:
    return "v2" if int(lesson_id[:2]) < 10 else "v1"


def source_video(lesson_id: str) -> Path:
    return source_root(lesson_id) / lesson_id / f"{lesson_id}_{source_version(lesson_id)}.mp4"


def source_report(lesson_id: str) -> dict:
    path = source_root(lesson_id) / lesson_id / f"QA_REPORT_{source_version(lesson_id).upper()}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def delivery_lesson_dir(lesson_id: str) -> Path:
    return OUT / "lessons" / lesson_id


def generated_mp4(lesson_id: str) -> Path:
    return delivery_lesson_dir(lesson_id) / f"{lesson_id}_successor_v1.mp4"


def font(size: int, *, mono: bool = False, symbol: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/seguisym.ttf" if symbol else "",
        "C:/Windows/Fonts/consola.ttf" if mono else "",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def draw_wrapped(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, *, width: int, font_value: ImageFont.ImageFont, fill: str, spacing: int = 6) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if draw.textlength(candidate, font=font_value) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font_value, fill=fill)
        y += int(font_value.size * 1.22) + spacing
    return y


def native_frame(spec: dict, target: Path) -> None:
    """Render successor states natively, avoiding an HTML/browser dependency."""
    image = Image.new("RGB", (1280, 720), "#08131b")
    draw = ImageDraw.Draw(image)
    sans = font(31)
    small = font(15)
    equation_font = font(24, mono=True)
    card_title = font(19)
    body = font(19)
    cell = font(22, mono=True)
    draw.rectangle((42, 20, 1238, 98), fill="#0e1e28", outline="#3e6c78", width=2)
    draw.text((42, 25), spec["subtitle"], font=small, fill="#78d8e4")
    draw.text((42, 48), spec["title"], font=sans, fill="#edf7fb")
    equations = spec["equations"]
    draw.rectangle((42, 114, 1238, 114 + max(65, 16 + 33 * len(equations))), fill="#14212e", outline="#b8a5ed", width=2)
    y = 124
    for line in equations:
        draw.text((62, y), line, font=equation_font, fill="#edf7fb")
        y += 31
    cards = spec["cards"]
    card_top, card_bottom = 220, 597
    gap = 18
    card_width = (1196 - gap * (len(cards) - 1)) // len(cards)
    for index, card in enumerate(cards):
        left = 42 + index * (card_width + gap)
        right = left + card_width
        draw.rectangle((left, card_top, right, card_bottom), fill="#10212b", outline="#68d4e1", width=3)
        if card["kind"] == "panel":
            draw.text((left + 12, card_top + 14), card["label"], font=card_title, fill="#87ddeb")
            line_y = card_top + 62
            for line in card["lines"]:
                line_y = draw_wrapped(draw, (left + 13, line_y), line, width=card_width - 26, font_value=body, fill="#edf7fb", spacing=5)
        else:
            draw.text((left + 12, card_top + 12), card["name"], font=card_title, fill="#87ddeb")
            axis_text = f"Rows: {card['row_group']}\nColumns: {card['col_group']}"
            axis_y = card_top + 40
            for line in axis_text.splitlines():
                axis_y = draw_wrapped(draw, (left + 12, axis_y), line, width=card_width - 24, font_value=small, fill="#b7dce5", spacing=2)
            rows, cols, values = card["rows"], card["cols"], card["values"]
            nrows, ncols = len(rows), len(cols)
            table_top = max(axis_y + 6, card_top + 110)
            table_left = left + 15
            table_width = card_width - 30
            label_width = 45 if ncols <= 4 else 33
            cw = (table_width - label_width) / ncols
            ch = min((card_bottom - table_top - 15) / (nrows + 1), 45 if nrows <= 4 else 25)
            header_font = font(17 if ncols <= 4 else 12, mono=True)
            value_font = font(22 if ncols <= 4 else 10, mono=True)
            for j, name in enumerate(cols):
                x = table_left + label_width + j * cw
                draw.text((x + 3, table_top), str(name), font=header_font, fill="#c5e6ed")
            marks = {tuple(mark) for mark in card.get("marks", [])}
            for i, row in enumerate(values):
                top = table_top + ch * (i + 1)
                draw.text((table_left + 2, top + max(1, (ch - header_font.size) / 2)), str(rows[i]), font=header_font, fill="#c5e6ed")
                for j, value in enumerate(row):
                    x = table_left + label_width + j * cw
                    fill = "#42375d" if (i, j) in marks else "#142f3a"
                    outline = "#e0c9ff" if (i, j) in marks else "#456671"
                    draw.rectangle((x, top, x + cw - 3, top + ch - 3), fill=fill, outline=outline, width=3 if (i, j) in marks else 1)
                    value_text = str(value)
                    bbox = draw.textbbox((0, 0), value_text, font=value_font)
                    draw.text((x + max(1, (cw - (bbox[2] - bbox[0])) / 2), top + max(1, (ch - (bbox[3] - bbox[1])) / 2)), value_text, font=value_font, fill="#ffffff")
    draw.rectangle((42, 620, 1238, 670), fill="#182333", outline="#b9a2eb", width=2)
    draw_wrapped(draw, (57, 631), spec["takeaway"], width=1166, font_value=font(18), fill="#edf7fb", spacing=0)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, quality=96)


def extract_source_frame(lesson_id: str, scene_number: int, target: Path) -> None:
    report = source_report(lesson_id)
    timeline = report["timeline"][scene_number - 1]
    start, end = float(timeline["start"]), float(timeline["end"])
    at = min(end - 0.15, max(start + 0.25, 0.25))
    target.parent.mkdir(parents=True, exist_ok=True)
    run([ffmpeg(), "-v", "error", "-y", "-ss", f"{at:.3f}", "-i", str(source_video(lesson_id)), "-frames:v", "1", str(target)])


def full_curricula() -> tuple[list[dict], list[dict]]:
    foundation, advanced, _ = successor.revise_curricula()
    return foundation, advanced


def frame_for(lesson_id: str, scene_number: int) -> Path:
    return delivery_lesson_dir(lesson_id) / "frames" / f"{scene_number:02d}.png"


def preflight() -> None:
    if OUT.exists():
        raise RuntimeError(f"Refusing to use an existing delivery package: {OUT}")
    foundation, advanced = full_curricula()
    lessons = foundation + advanced
    scope = []
    for lesson_id in sorted(REVISED_SPOKEN):
        lesson = get_lesson(lessons, lesson_id)
        text = "\n\n".join(scene["text"] for scene in lesson["scenes"])
        scope.append({"lesson": lesson_id, "characters": len(text), "voice": VOICE, "model": MODEL})
    print(json.dumps({"paid_synthesis_lessons": scope, "total_characters": sum(item["characters"] for item in scope), "reused_audio_lesson": sorted(REUSED_AUDIO), "new_delivery": str(OUT)}, ensure_ascii=False, indent=2))


def prepare() -> None:
    if OUT.exists():
        raise RuntimeError(f"Refusing to overwrite existing delivery package: {OUT}")
    foundation, advanced = full_curricula()
    lessons = foundation + advanced
    specs = successor.visual_specs()
    OUT.mkdir(parents=True)
    for name in ("README.md", "CHANGELOG.md", "COMPANION_CHECKPOINTS.md", "NARRATION_AND_CAPTION_GATE.md"):
        shutil.copy2(SOURCE / name, OUT / name)
    write_json(OUT / "CURRICULUM_DELIVERY_V1.json", {"foundation": foundation, "advanced": advanced})
    write_json(OUT / "DELIVERY_SCOPE_V1.json", {
        "revised_spoken_lessons": sorted(REVISED_SPOKEN), "reused_audio_lessons": sorted(REUSED_AUDIO),
        "unchanged_lessons_in_combined_courses": [lesson["id"] for lesson in lessons if lesson["id"] not in TARGETS],
        "frozen_source_packages": [str(FOUNDATION), str(ADVANCED)],
    })
    for lesson_id in sorted(TARGETS):
        lesson = get_lesson(lessons, lesson_id)
        folder = delivery_lesson_dir(lesson_id)
        (folder / "frames").mkdir(parents=True)
        for scene_number in range(1, len(lesson["scenes"]) + 1):
            target = frame_for(lesson_id, scene_number)
            spec = specs.get(f"{lesson_id}/{scene_number}")
            if spec:
                native_frame(spec, target)
            else:
                extract_source_frame(lesson_id, scene_number, target)
        script = [f"# {lesson_id} successor delivery script", ""]
        for index, item in enumerate(lesson["scenes"], 1):
            script.extend([f"## {index}. {item['title']}", "", item["text"], "", f"Visual: {item['note']}", ""])
        write_text(folder / "SCRIPT_AND_VISUAL_SPEC_SUCCESSOR_V1.md", "\n".join(script))
    write_text(OUT / "README.md", (OUT / "README.md").read_text(encoding="utf-8") + "\n\n## Encoded delivery\n\nThis delivery refreshes L04, L07, L10, L15, L16, L17, L18, L20 and L21. L17 reuses its unchanged narration; the other eight lessons use the local Windows SAPI Microsoft Zira Desktop voice at its default rate. No network or paid speech provider is used. Refreshed combined courses reference frozen MP4s for unchanged lessons and these successor MP4s for revised lessons. Captions for locally synthesized lessons use scene-duration-based word timing and require human review.\n")
    write_json(OUT / "PREPARE_QA_V1.json", {"target_lessons": sorted(TARGETS), "native_visual_states": sorted(specs), "frames": sum(len(get_lesson(lessons, item)["scenes"]) for item in TARGETS), "status": "prepared_no_paid_request"})
    print(json.dumps({"status": "prepared", "lessons": sorted(TARGETS), "frames": sum(len(get_lesson(lessons, item)["scenes"]) for item in TARGETS)}, ensure_ascii=False))


def eleven_key() -> str:
    env = ROOT / ".env"
    for line in env.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*?)\s*$", line)
        if match and "ELEVEN" in match[1].upper() and ("KEY" in match[1].upper() or "TOKEN" in match[1].upper()):
            value = match[2].strip().strip("\"'")
            if value:
                return value
    raise RuntimeError("No ElevenLabs credential found in the authorized root .env")


def eleven_synthesize(payload: dict) -> tuple[dict, dict]:
    request = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128",
        data=json.dumps(payload).encode("utf-8"),
        headers={"xi-api-key": eleven_key(), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            return json.load(response), {"request_id": response.headers.get("request-id"), "character_cost": response.headers.get("character-cost")}
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"ElevenLabs returned HTTP {error.code}; response body withheld") from None
    except urllib.error.URLError:
        raise RuntimeError("ElevenLabs connection failed; credential withheld") from None


def identity_for(text: str) -> str:
    return sha256(json.dumps({"voice_id": VOICE, "text": text, "model_id": MODEL, "voice_settings": SETTINGS, "seed": 15092026}, sort_keys=True).encode("utf-8")).hexdigest()


def generate() -> None:
    if not OUT.is_dir():
        raise RuntimeError("Run prepare before generate.")
    foundation, advanced = full_curricula()
    lessons = foundation + advanced
    receipts = []
    for lesson_id in sorted(TARGETS):
        lesson = get_lesson(lessons, lesson_id)
        folder = delivery_lesson_dir(lesson_id)
        audio = folder / "brian_source_successor_v1.mp3"
        receipt_path = folder / "VOICE_RESPONSE_SUCCESSOR_V1.json"
        text = "\n\n".join(scene["text"] for scene in lesson["scenes"])
        expected_identity = identity_for(text)
        if lesson_id in REUSED_AUDIO:
            original_folder = source_root(lesson_id) / lesson_id
            original_receipt = json.loads((original_folder / f"VOICE_RESPONSE_{source_version(lesson_id).upper()}.json").read_text(encoding="utf-8"))
            if original_receipt["payload"]["text"] != text:
                raise RuntimeError(f"Audio reuse text differs for {lesson_id}")
            shutil.copy2(original_folder / f"brian_source_{source_version(lesson_id)}.mp3", audio)
            original_receipt["reuse_provenance"] = {"lesson": lesson_id, "source_package": str(source_root(lesson_id)), "new_paid_request": False}
            original_receipt["identity"] = expected_identity
            write_json(receipt_path, original_receipt)
            receipts.append({"lesson": lesson_id, "new_paid_request": False, "characters": len(text)})
            continue
        if receipt_path.exists():
            cached = json.loads(receipt_path.read_text(encoding="utf-8"))
            if cached.get("identity") != expected_identity or not audio.is_file():
                raise RuntimeError(f"Saved generation identity differs for {lesson_id}; create a new delivery package.")
            receipts.append({"lesson": lesson_id, "new_paid_request": False, "characters": len(text), "reused_saved_generation": True})
            continue
        marker = folder / "generation.pending"
        if marker.exists():
            raise RuntimeError(f"A prior synthesis request may be uncertain for {lesson_id}; do not retry automatically.")
        payload = {"text": text, "model_id": MODEL, "voice_settings": SETTINGS, "seed": 15092026, "apply_text_normalization": "off"}
        marker.write_text(expected_identity, encoding="utf-8")
        response, headers = eleven_synthesize(payload)
        audio.write_bytes(base64.b64decode(response.pop("audio_base64")))
        response.update(headers)
        response.update({"identity": expected_identity, "voice_id": VOICE, "voice_name": "Brian", "payload": payload, "generated_unix": time.time(), "source_audio_sha256": sha(audio)})
        write_json(receipt_path, response)
        marker.unlink()
        receipts.append({"lesson": lesson_id, "new_paid_request": True, "characters": len(text), "character_cost": headers.get("character_cost")})
        print(json.dumps({"generated": lesson_id, "characters": len(text), "character_cost": headers.get("character_cost")}, ensure_ascii=False), flush=True)
    write_json(OUT / "SYNTHESIS_RECEIPTS_V1.json", receipts)
    print(json.dumps({"status": "synthesis_complete", "lessons": receipts}, ensure_ascii=False))


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def generate_local() -> None:
    """Create source WAVs locally, keeping per-scene timing exact without a cloud service."""
    if not OUT.is_dir():
        raise RuntimeError("Run prepare before generate-local.")
    foundation, advanced = full_curricula()
    lessons = foundation + advanced
    receipts = []
    for lesson_id in sorted(TARGETS):
        lesson = get_lesson(lessons, lesson_id)
        folder = delivery_lesson_dir(lesson_id)
        receipt_path = folder / "VOICE_RESPONSE_SUCCESSOR_V1.json"
        if receipt_path.exists():
            cached = json.loads(receipt_path.read_text(encoding="utf-8"))
            if cached.get("provider") == "Windows SAPI" or cached.get("reuse_provenance"):
                receipts.append({"lesson": lesson_id, "reused_saved_generation": True})
                continue
            raise RuntimeError(f"Existing non-local generation found for {lesson_id}; create a fresh package to switch providers.")
        if lesson_id in REUSED_AUDIO:
            original_folder = source_root(lesson_id) / lesson_id
            original_receipt = json.loads((original_folder / f"VOICE_RESPONSE_{source_version(lesson_id).upper()}.json").read_text(encoding="utf-8"))
            shutil.copy2(original_folder / f"brian_source_{source_version(lesson_id)}.mp3", folder / "brian_source_successor_v1.mp3")
            original_receipt["reuse_provenance"] = {"lesson": lesson_id, "source_package": str(source_root(lesson_id)), "new_paid_request": False}
            original_receipt["identity"] = identity_for("\n\n".join(item["text"] for item in lesson["scenes"]))
            write_json(receipt_path, original_receipt)
            receipts.append({"lesson": lesson_id, "provider": "reused frozen audio"})
            continue
        source_wavs = []
        source_dir = folder / "local_voice_source"
        source_dir.mkdir(exist_ok=True)
        for index, state in enumerate(lesson["scenes"], 1):
            text_path = source_dir / f"scene_{index:02d}.txt"
            wav_path = source_dir / f"scene_{index:02d}.wav"
            write_text(text_path, state["text"])
            run(["C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(LOCAL_SYNTH_SCRIPT), "-TextPath", str(text_path), "-WavePath", str(wav_path), "-Voice", LOCAL_VOICE, "-Rate", str(LOCAL_VOICE_RATE)])
            pcm_path = source_dir / f"scene_{index:02d}_48k.wav"
            run([ffmpeg(), "-v", "error", "-y", "-i", str(wav_path), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(pcm_path)])
            source_wavs.append({"scene": index, "source_wav": pcm_path.name, "duration_s": wav_duration(pcm_path), "sha256": sha(pcm_path)})
        text = "\n\n".join(item["text"] for item in lesson["scenes"])
        write_json(receipt_path, {"provider": "Windows SAPI", "voice_id": LOCAL_VOICE, "voice_name": LOCAL_VOICE, "rate": LOCAL_VOICE_RATE, "identity": identity_for(text), "text": text, "scene_audio": source_wavs, "generated_unix": time.time(), "new_paid_request": False})
        receipts.append({"lesson": lesson_id, "provider": "Windows SAPI", "scenes": len(source_wavs), "characters": len(text)})
        print(json.dumps({"generated_local": lesson_id, "scenes": len(source_wavs), "characters": len(text)}, ensure_ascii=False), flush=True)
    write_json(OUT / "SYNTHESIS_RECEIPTS_V1.json", receipts)
    print(json.dumps({"status": "local_synthesis_complete", "voice": LOCAL_VOICE, "lessons": receipts}, ensure_ascii=False))


def timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole:02d}.{milliseconds:03d}"


def alignment_for(lesson: dict, response: dict, duration: float) -> tuple[list[dict], list[dict], list[tuple[float, float]], float]:
    alignment = response.get("alignment") or response.get("normalized_alignment")
    if not alignment:
        raise RuntimeError(f"No time alignment for {lesson['id']}")
    chars = "".join(alignment["characters"])
    starts, ends = alignment["character_start_times_seconds"], alignment["character_end_times_seconds"]
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for state in lesson["scenes"]:
        pattern = r"\s+".join(re.escape(part) for part in state["text"].split())
        match = re.search(pattern, chars[cursor:])
        if not match:
            raise RuntimeError(f"Synthesis alignment does not match scene: {lesson['id']} / {state['title']}")
        first, last = cursor + match.start(), cursor + match.end() - 1
        offsets.append((first, last))
        cursor = last + 1
    boundaries = [0.0] + [(ends[offsets[i - 1][1]] + starts[offsets[i][0]]) / 2 for i in range(1, len(offsets))] + [duration]
    pauses = [(boundaries[i + 1], state["pause"]) for i, state in enumerate(lesson["scenes"]) if state.get("pause")]

    def shifted(value: float) -> float:
        return value + sum(length for point, length in pauses if point <= value)

    timeline = []
    current = 0.0
    for index, state in enumerate(lesson["scenes"]):
        length = boundaries[index + 1] - boundaries[index]
        timeline.append({"index": index, "title": state["title"], "text": state["text"], "start": current, "speech_end": current + length, "end": current + length + state.get("pause", 0), "pause": state.get("pause", 0)})
        current = timeline[-1]["end"]
    words = []
    for match in re.finditer(r"\S+", chars):
        words.append({"text": match[0], "start": shifted(starts[match.start()]), "end": shifted(ends[match.end() - 1])})
    return timeline, words, pauses, current


def caption_groups(words: list[dict]) -> list[dict]:
    groups: list[list[dict]] = []
    current: list[dict] = []
    for word in words:
        text = " ".join(item["text"] for item in current + [word])
        if current and (len(text) > 76 or len(textwrap.wrap(text, width=42)) > 2 or word["end"] - current[0]["start"] > 5.5 or word["start"] - current[-1]["end"] > 1):
            groups.append(current)
            current = []
        current.append(word)
    if current:
        groups.append(current)
    return [{"start": group[0]["start"], "end": group[-1]["end"], "text": "\n".join(textwrap.wrap(" ".join(item["text"] for item in group), width=42))} for group in groups]


def local_timeline_and_words(lesson: dict, receipt: dict) -> tuple[list[dict], list[dict], float, Path]:
    """Assemble individual local SAPI WAVs and approximate within-scene captions."""
    source_audio = {item["scene"]: item for item in receipt["scene_audio"]}
    timeline, words, pcm = [], [], []
    cursor = 0.0
    for index, state in enumerate(lesson["scenes"], 1):
        item = source_audio[index]
        path = delivery_lesson_dir(lesson["id"]) / "local_voice_source" / item["source_wav"]
        with wave.open(str(path), "rb") as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getframerate() != 48000:
                raise RuntimeError(f"Unexpected local PCM format: {path}")
            data = wav.readframes(wav.getnframes())
        duration = float(item["duration_s"])
        speech_end = cursor + duration
        pause = state.get("pause", 0)
        timeline.append({"index": index - 1, "title": state["title"], "text": state["text"], "start": cursor, "speech_end": speech_end, "end": speech_end + pause, "pause": pause})
        tokens = re.findall(r"\S+", state["text"])
        for word_index, token in enumerate(tokens):
            start = cursor + duration * word_index / len(tokens)
            end = cursor + duration * (word_index + 1) / len(tokens)
            words.append({"text": token, "start": start, "end": end})
        pcm.append(data)
        if pause:
            pcm.append(b"\x00\x00" * round(pause * 48000))
        cursor = speech_end + pause
    narration = delivery_lesson_dir(lesson["id"]) / "brian_narration_successor_v1.wav"
    with wave.open(str(narration), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(b"".join(pcm))
    return timeline, words, cursor, narration


def build_audio(lesson: dict, folder: Path) -> tuple[list[dict], list[dict], float, Path]:
    response = json.loads((folder / "VOICE_RESPONSE_SUCCESSOR_V1.json").read_text(encoding="utf-8"))
    if response.get("provider") == "Windows SAPI":
        timeline, words, total, narration = local_timeline_and_words(lesson, response)
        captions = caption_groups(words)
        for caption in captions:
            caption["end"] = min(caption["end"], total)
        return timeline, captions, total, narration
    decoded = folder / "brian_decoded_successor_v1.wav"
    run([ffmpeg(), "-v", "error", "-y", "-i", str(folder / "brian_source_successor_v1.mp3"), "-ar", "48000", "-ac", "1", str(decoded)])
    with wave.open(str(decoded), "rb") as wav:
        data = wav.readframes(wav.getnframes())
        duration = wav.getnframes() / 48000
    timeline, words, pauses, total = alignment_for(lesson, response, duration)
    chunks: list[bytes] = []
    start = 0
    for point, length in pauses:
        cut = round(point * 48000) * 2
        chunks.extend([data[start:cut], b"\x00\x00" * round(length * 48000)])
        start = cut
    chunks.append(data[start:])
    narration = folder / "brian_narration_successor_v1.wav"
    with wave.open(str(narration), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(b"".join(chunks))
    captions = caption_groups(words)
    for caption in captions:
        caption["end"] = min(caption["end"], total)
    return timeline, captions, total, narration


def write_vtt(path: Path, captions: list[dict]) -> None:
    lines = ["WEBVTT", ""]
    for index, caption in enumerate(captions, 1):
        lines.extend([str(index), f"{timestamp(caption['start'])} --> {timestamp(caption['end'])}", caption["text"], ""])
    write_text(path, "\n".join(lines))


def assemble() -> None:
    if not OUT.is_dir():
        raise RuntimeError("Run prepare and generate before assemble.")
    foundation, advanced = full_curricula()
    lessons = foundation + advanced
    reports = []
    for lesson_id in sorted(TARGETS):
        lesson = get_lesson(lessons, lesson_id)
        folder = delivery_lesson_dir(lesson_id)
        video = generated_mp4(lesson_id)
        if video.exists():
            raise RuntimeError(f"Refusing to overwrite encoded successor video: {video}")
        timeline, captions, total, narration = build_audio(lesson, folder)
        write_vtt(folder / "captions_successor_v1.vtt", captions)
        chapters = [";FFMETADATA1"]
        concat: list[str] = []
        for cue in timeline:
            chapters.extend(["[CHAPTER]", "TIMEBASE=1/1000", f"START={round(cue['start'] * 1000)}", f"END={round(cue['end'] * 1000)}", f"title={cue['title']}"])
            frame = frame_for(lesson_id, cue["index"] + 1).resolve().as_posix()
            concat.extend([f"file '{frame}'", f"duration {cue['end'] - cue['start']:.9f}"])
        concat.append(f"file '{frame_for(lesson_id, len(timeline)).resolve().as_posix()}'")
        concat_path = folder / "visuals.concat.txt"
        chapters_path = folder / "chapters.ffmeta"
        write_text(concat_path, "\n".join(concat))
        write_text(chapters_path, "\n".join(chapters))
        run([ffmpeg(), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-i", str(narration), "-i", str(folder / "captions_successor_v1.vtt"), "-i", str(chapters_path), "-map", "0:v", "-map", "1:a", "-map", "2:s", "-map_metadata", "3", "-map_chapters", "3", "-vf", f"fps={FPS}", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-t", f"{total:.6f}", "-movflags", "+faststart", str(video)])
        run([ffmpeg(), "-v", "error", "-i", str(video), "-map", "0:v", "-map", "0:a", "-f", "null", "-"])
        info = {"lesson": lesson_id, "duration_s": total, "video_sha256": sha(video), "video_bytes": video.stat().st_size, "timeline": timeline, "captions": captions, "status": "technical_decode_passed_human_listening_pending"}
        write_json(folder / "QA_REPORT_SUCCESSOR_V1.json", info)
        reports.append(info)
        print(json.dumps({"encoded": lesson_id, "duration_s": round(total, 3), "bytes": video.stat().st_size}, ensure_ascii=False), flush=True)
    write_json(OUT / "LESSON_QA_SUMMARY_V1.json", reports)


def parse_vtt(path: Path) -> list[dict]:
    result = []
    blocks = path.read_text(encoding="utf-8").split("\n\n")
    for block in blocks:
        match = re.search(r"(\d+:\d+:\d+\.\d+) --> (\d+:\d+:\d+\.\d+)\n(.+)", block, re.S)
        if not match:
            continue
        def seconds(value: str) -> float:
            hours, minutes, sec = value.split(":")
            return int(hours) * 3600 + int(minutes) * 60 + float(sec)
        result.append({"start": seconds(match[1]), "end": seconds(match[2]), "text": match[3]})
    return result


def video_for_combined(lesson_id: str) -> Path:
    return generated_mp4(lesson_id) if lesson_id in TARGETS else source_video(lesson_id)


def captions_for_combined(lesson_id: str) -> list[dict]:
    if lesson_id in TARGETS:
        report = json.loads((delivery_lesson_dir(lesson_id) / "QA_REPORT_SUCCESSOR_V1.json").read_text(encoding="utf-8"))
        return report["captions"]
    return parse_vtt(source_root(lesson_id) / lesson_id / f"captions_{source_version(lesson_id)}.vtt")


def duration_for_combined(lesson_id: str) -> float:
    if lesson_id in TARGETS:
        return float(json.loads((delivery_lesson_dir(lesson_id) / "QA_REPORT_SUCCESSOR_V1.json").read_text(encoding="utf-8"))["duration_s"])
    return float(source_report(lesson_id)["duration_s"])


def combine_group(name: str, lessons: list[dict]) -> dict:
    target = OUT / f"cm_{name}_complete_course_successor_v1.mp4"
    if target.exists():
        raise RuntimeError(f"Refusing to overwrite combined course: {target}")
    concat, chapters, all_captions, cursor = [], [";FFMETADATA1"], [], 0.0
    for lesson in lessons:
        lesson_id = lesson["id"]
        video = video_for_combined(lesson_id).resolve().as_posix()
        duration = duration_for_combined(lesson_id)
        concat.append(f"file '{video}'")
        chapters.extend(["[CHAPTER]", "TIMEBASE=1/1000", f"START={round(cursor * 1000)}", f"END={round((cursor + duration) * 1000)}", f"title={lesson['title']}"])
        all_captions.extend([{**caption, "start": caption["start"] + cursor, "end": caption["end"] + cursor} for caption in captions_for_combined(lesson_id)])
        cursor += duration
    concat_path = OUT / f"{name}_course.concat.txt"
    chapter_path = OUT / f"{name}_course.ffmeta"
    caption_path = OUT / f"{name}_course_captions_successor_v1.vtt"
    write_text(concat_path, "\n".join(concat))
    write_text(chapter_path, "\n".join(chapters))
    write_vtt(caption_path, all_captions)
    run([ffmpeg(), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-i", str(caption_path), "-i", str(chapter_path), "-map", "0:v:0", "-map", "0:a:0", "-map", "1:s:0", "-map_metadata", "2", "-map_chapters", "2", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-movflags", "+faststart", str(target)])
    run([ffmpeg(), "-v", "error", "-i", str(target), "-map", "0:v", "-map", "0:a", "-f", "null", "-"])
    return {"course": name, "video": str(target), "duration_s": cursor, "chapters": len(lessons), "video_sha256": sha(target), "status": "technical_decode_passed_human_listening_pending"}


def combine() -> None:
    if not OUT.is_dir():
        raise RuntimeError("Run prepare, generate and assemble before combine.")
    foundation, advanced = full_curricula()
    result = [combine_group("foundations", foundation), combine_group("advanced", advanced)]
    write_json(OUT / "COMBINED_QA_V1.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def validate() -> None:
    if not OUT.is_dir():
        raise RuntimeError("Run prepare before validate.")
    before = json.loads((SOURCE.parent / "cm_full_course_panel_review_v1" / "evidence" / "production_hashes_before.json").read_text(encoding="utf-8"))
    changed = [path for path, expected in before.items() if not Path(path).is_file() or sha(Path(path)) != expected]
    if changed:
        raise RuntimeError(f"Frozen package mutation detected: {changed[:3]}")
    lesson_reports = []
    for lesson_id in sorted(TARGETS):
        report_path = delivery_lesson_dir(lesson_id) / "QA_REPORT_SUCCESSOR_V1.json"
        if not report_path.is_file():
            raise RuntimeError(f"Missing QA report for {lesson_id}")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        captions = report["captions"]
        assert captions and max(len(line) for caption in captions for line in caption["text"].splitlines()) <= 42
        assert max(len(caption["text"].splitlines()) for caption in captions) <= 2
        lesson_reports.append({"lesson": lesson_id, "duration_s": report["duration_s"], "video_sha256": report["video_sha256"], "captions": len(captions)})
    combined = json.loads((OUT / "COMBINED_QA_V1.json").read_text(encoding="utf-8"))
    for course in combined:
        assert Path(course["video"]).is_file()
    write_json(OUT / "VALIDATION_V1.json", {"status": "pass", "frozen_package_hashes_verified": len(before), "lesson_reports": lesson_reports, "combined_courses": combined, "limitations": ["Human listening, preferred-player caption display, chapter interaction and learner validation remain pending.", "Local SAPI caption words are timed proportionally within each spoken scene; human caption-sync review remains pending.", "Native raster frames were used for successor visual changes; 640×360 human review remains pending."]})
    print(json.dumps({"status": "pass", "frozen_hashes": len(before), "successor_lessons": len(lesson_reports), "combined_courses": len(combined)}, ensure_ascii=False))


if __name__ == "__main__":
    commands = {"preflight": preflight, "prepare": prepare, "generate": generate, "generate-local": generate_local, "assemble": assemble, "combine": combine, "validate": validate}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        raise SystemExit("Use one of: " + ", ".join(commands))
    commands[sys.argv[1]]()
