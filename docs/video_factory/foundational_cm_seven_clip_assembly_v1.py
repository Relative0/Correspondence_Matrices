"""Build the seven-clip foundational CM review reel locally.

This additive successor preserves every earlier preview and manifest. It renders
seven notation-consistent silent clips, assembles them in teaching order, and
performs no network, paid, publication, narration, commit, or push operation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FACTORY = ROOT / "docs/video_factory"
PACKAGE = FACTORY / "deep_series/foundational_cm_seven_clip_assembly_v1"
BASE_MANIFEST = FACTORY / "deep_series/foundational_cm_production_v3/IMPLEMENTATION_MANIFEST_V4.json"
FEEDBACK_MANIFEST = FACTORY / "deep_series/foundational_cm_feedback_round_v3/FEEDBACK_MANIFEST_V3.json"
OPERATOR_ROOT = FACTORY / "deep_series/episodes/operator-cms-from-truth-tables/revision_v5"
LOGICAL_ROOT = FACTORY / "deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v7"
REPOSITORY_ROOT = FACTORY / "deep_series/episodes/what-is-explicit-cm/revision_v7"
NOTATION_STANDARD = ROOT / "docs/CM_NOTATION_STANDARD_V1.md"
WIDTH, HEIGHT, FPS = 960, 540, 15


class AssemblyError(RuntimeError):
    pass


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise AssemblyError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_module("foundational_cm_corrections_v3", FACTORY / "foundational_cm_corrections_v3.py")
FEEDBACK = load_module("foundational_cm_feedback_corrections_v2", FACTORY / "foundational_cm_feedback_corrections_v2.py")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_new_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise AssemblyError(f"refusing to overwrite different assembly artifact: {path}")
        return
    path.write_text(text, encoding="utf-8", newline="\n")


def write_new_json(path: Path, value: Any) -> None:
    write_new_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


CLIPS = [
    {"order": 1, "id": "operator_outer_product_and_zero_move", "source": "base", "visual": "o_dyad_implication", "duration_s": 10, "chapter": "Operator matrices: outer product and operand order"},
    {"order": 2, "id": "operator_retrieval", "source": "base", "visual": "o_retrieval", "duration_s": 8, "chapter": "Operator matrices: retrieval"},
    {"order": 3, "id": "logical_valuation_and_block", "source": "logical", "visual": "logical_block_v3", "duration_s": 14, "chapter": "Logical matrices: complete 4×4 tensor"},
    {"order": 4, "id": "logical_order_and_modifier", "source": "base", "visual": "l_modifier", "duration_s": 12, "chapter": "Logical matrices: compound rule"},
    {"order": 5, "id": "logical_retrieval", "source": "base", "visual": "l_retrieval", "duration_s": 8, "chapter": "Logical matrices: retrieval"},
    {"order": 6, "id": "repository_retrieval", "source": "repository", "visual": "repository_retrieval_v3", "duration_s": 14, "chapter": "Repository layout: split, index, evaluate"},
    {"order": 7, "id": "repository_repartition", "source": "base", "visual": "r_repartition", "duration_s": 12, "chapter": "Repository layout: repartition"},
]


def corrected_page(clip: dict[str, Any], sans: str, mono: str) -> str:
    if clip["source"] == "logical":
        page = FEEDBACK.page("logical_block_v3", sans, mono)
        page = re.sub(r'<div class="block-note" data-show-at="\.66">.*?</div>', "", page, count=1)
    elif clip["source"] == "repository":
        page = FEEDBACK.page("repository_retrieval_v3", sans, mono)
    else:
        page = BASE.page(clip["visual"], sans, mono)
    page = page.replace("⊕", "⇕")
    page = page.replace("CORRECTED LOCAL PREVIEW", "SEVEN-CLIP ASSEMBLY")
    page = page.replace("FEEDBACK CORRECTION", "SEVEN-CLIP ASSEMBLY")
    page = page.replace("v3 local review", "assembly v1")
    page = page.replace("feedback v3", "assembly v1")
    return page


def input_paths() -> list[Path]:
    return [
        OPERATOR_ROOT / "SCRIPT_V5.md",
        OPERATOR_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V5.md",
        LOGICAL_ROOT / "SCRIPT_V7.md",
        LOGICAL_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V7.md",
        REPOSITORY_ROOT / "SCRIPT_V7.md",
        REPOSITORY_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V7.md",
        NOTATION_STANDARD,
        BASE_MANIFEST,
        FEEDBACK_MANIFEST,
    ]


def build_contract() -> dict[str, Any]:
    cursor = 0
    timeline = []
    for clip in CLIPS:
        start = cursor
        cursor += clip["duration_s"]
        timeline.append({**clip, "start_s": start, "end_s": cursor, "frames": clip["duration_s"] * FPS})
    contract = {
        "schema_version": "1.0",
        "status": "local_silent_seven_clip_assembly_authorized",
        "format": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "duration_s": cursor, "frames": cursor * FPS},
        "timeline": timeline,
        "requirements": {
            "logical_tensor_callout_removed": True,
            "exclusive_or_display": "⇕ (LaTeX \\Updownarrow)",
            "repository_retrieval": "progressive split, index, and evaluate trace with synchronized highlights",
            "preserve_prior_versions": True,
        },
        "inputs": [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)} for path in input_paths()],
        "audio_generated": False,
        "remote_or_paid_work_performed": False,
        "publication_authorized": False,
    }
    contract["contract_identity_sha256"] = canonical_hash(contract)
    write_new_json(PACKAGE / "ASSEMBLY_CONTRACT_V1.json", contract)
    return contract


def chapters_text(timeline: list[dict[str, Any]]) -> str:
    lines = [";FFMETADATA1"]
    for item in timeline:
        lines.extend([
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={item['start_s'] * 1000}",
            f"END={item['end_s'] * 1000}",
            f"title={item['order']}. {item['chapter']}",
        ])
    return "\n".join(lines) + "\n"


def render(workers: int = 2) -> dict[str, Any]:
    contract = build_contract()
    node = shutil.which("node")
    if not node or not BASE.FRAME_DRIVER.is_file():
        raise AssemblyError("existing local frame pipeline unavailable")
    from PIL import Image, ImageDraw
    import imageio_ffmpeg

    sans, mono = BASE.font_data()
    frames_root = PACKAGE / "frames"
    frames_root.mkdir(parents=True, exist_ok=True)
    scenes = []
    offset = 0
    rendered_pages = []
    for clip in CLIPS:
        count = clip["duration_s"] * FPS
        page = corrected_page(clip, sans, mono)
        rendered_pages.append(page)
        scenes.append({
            "id": clip["id"],
            "kind": "foundational_cm_seven_clip_assembly",
            "startIndex": offset,
            "progress": [(i + 0.5) / count for i in range(count)],
            "html": page,
        })
        offset += count
    if any("⊕" in page or "\\oplus" in page for page in rendered_pages):
        raise AssemblyError("legacy exclusive-or glyph remains in rendered HTML")
    if "top-left entry of [M<sub>WX</sub>] is WX" in rendered_pages[2] or "class=\"block-note\"" in rendered_pages[2]:
        raise AssemblyError("removed tensor callout remains in logical clip")

    frame_manifest = {"width": WIDTH, "height": HEIGHT, "fps": FPS, "scenes": scenes}
    write_new_json(PACKAGE / "ASSEMBLY_FRAME_MANIFEST_V1.json", frame_manifest)
    run = subprocess.run(
        [node, str(BASE.FRAME_DRIVER), str(PACKAGE / "ASSEMBLY_FRAME_MANIFEST_V1.json"), str(frames_root), str(workers)],
        cwd=BASE.POP_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if run.returncode:
        raise AssemblyError(run.stderr[-1800:])
    total_frames = contract["format"]["frames"]
    if len(list(frames_root.glob("f*.png"))) != total_frames:
        raise AssemblyError("assembly frame count mismatch")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    clip_root = PACKAGE / "clips"
    clip_root.mkdir(exist_ok=True)
    clip_records = []
    start_frame = 0
    pattern = frames_root / "f%06d.png"
    for clip in CLIPS:
        target = clip_root / f"{clip['order']:02d}_{clip['id']}_v1.mp4"
        command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-n", "-framerate", str(FPS), "-start_number", str(start_frame), "-i", str(pattern), "-frames:v", str(clip["duration_s"] * FPS), "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target)]
        encoded = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if encoded.returncode and "already exists" not in encoded.stderr:
            raise AssemblyError(encoded.stderr[-1200:])
        clip_records.append({"order": clip["order"], "id": clip["id"], "duration_s": clip["duration_s"], "frames": clip["duration_s"] * FPS, "path": target.relative_to(ROOT).as_posix(), "sha256": sha256(target)})
        start_frame += clip["duration_s"] * FPS

    chapter_path = PACKAGE / "ASSEMBLY_CHAPTERS_V1.ffmeta"
    write_new_text(chapter_path, chapters_text(contract["timeline"]))
    assembly_path = PACKAGE / "foundational_cm_seven_clip_review_v1.mp4"
    assembly_command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-n", "-framerate", str(FPS), "-start_number", "0", "-i", str(pattern), "-i", str(chapter_path), "-frames:v", str(total_frames), "-map", "0:v:0", "-map_metadata", "1", "-map_chapters", "1", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(assembly_path)]
    encoded = subprocess.run(assembly_command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if encoded.returncode and "already exists" not in encoded.stderr:
        raise AssemblyError(encoded.stderr[-1200:])

    still_root = PACKAGE / "stills"
    still_root.mkdir(exist_ok=True)
    sheet = Image.new("RGB", (WIDTH * 2, HEIGHT * 4), "#081018")
    draw = ImageDraw.Draw(sheet)
    still_records = []
    cursor = 0
    for index, clip in enumerate(CLIPS):
        count = clip["duration_s"] * FPS
        source_index = cursor + min(count - 1, int(count * 0.88))
        source = frames_root / f"f{source_index:06d}.png"
        target = still_root / f"{clip['order']:02d}_{clip['id']}.png"
        shutil.copyfile(source, target)
        x, y = (index % 2) * WIDTH, (index // 2) * HEIGHT
        sheet.paste(Image.open(target).convert("RGB"), (x, y))
        draw.rectangle((x, y, x + 470, y + 22), fill="#081018")
        draw.text((x + 5, y + 4), f"{clip['order']:02d} {clip['id']}", fill="#f1b65c")
        still_records.append({"order": clip["order"], "id": clip["id"], "path": target.relative_to(ROOT).as_posix(), "sha256": sha256(target)})
        cursor += count
    contact = PACKAGE / "SEVEN_CLIP_CONTACT_SHEET_V1.png"
    sheet.save(contact)
    shutil.rmtree(frames_root)

    report = {
        "schema_version": "1.0",
        "status": "local_silent_seven_clip_review_video_complete_human_review_required",
        "contract_identity_sha256": contract["contract_identity_sha256"],
        "format": contract["format"],
        "clips": clip_records,
        "assembly": {"path": assembly_path.relative_to(ROOT).as_posix(), "sha256": sha256(assembly_path), "chapters": chapter_path.relative_to(ROOT).as_posix()},
        "stills": still_records,
        "contact_sheet": {"path": contact.relative_to(ROOT).as_posix(), "sha256": sha256(contact)},
        "audio_generated": False,
        "remote_or_paid_work_performed": False,
        "publication_authorized": False,
    }
    write_new_json(PACKAGE / "ASSEMBLY_REPORT_V1.json", report)
    return report


def validate() -> dict[str, Any]:
    import imageio_ffmpeg

    contract = build_contract()
    report_path = PACKAGE / "ASSEMBLY_REPORT_V1.json"
    if not report_path.is_file():
        raise AssemblyError("render before validation")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    checks = []

    def add(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    sans, mono = BASE.font_data()
    pages = [corrected_page(clip, sans, mono) for clip in CLIPS]
    add("seven ordered clips", len(report["clips"]) == 7 and [x["order"] for x in report["clips"]] == list(range(1, 8)), [x["id"] for x in report["clips"]])
    add("tensor callout removed", "class=\"block-note\"" not in pages[2] and "top-left entry of [M<sub>WX</sub>] is WX" not in pages[2], "highlight retained; requested text box absent")
    add("exclusive-or notation", all("⊕" not in page and "\\oplus" not in page for page in pages) and any("⇕" in page for page in pages), "all rendered mathematical exclusive-or symbols use ⇕")
    add("progressive repository trace", all(token in pages[5] for token in ("1 · split", "2 · index", "3 · evaluate", "data-row-header", "data-col-header")), "split/index/evaluate with header highlighting")
    add("assembly scope", report["format"] == {"width": 960, "height": 540, "fps": 15, "duration_s": 78, "frames": 1170}, report["format"])
    all_media = report["clips"] + [report["assembly"]] + report["stills"] + [report["contact_sheet"]]
    add("media hashes", all(sha256(ROOT / item["path"]) == item["sha256"] for item in all_media), len(all_media))

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    decode = []
    for item in report["clips"] + [report["assembly"]]:
        path = ROOT / item["path"]
        run = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"], capture_output=True)
        frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(path))
        expected_frames = item.get("frames", contract["format"]["frames"])
        expected_seconds = item.get("duration_s", contract["format"]["duration_s"])
        decode.append({"id": item.get("id", "assembly"), "returncode": run.returncode, "frames": frames, "seconds": round(seconds, 3), "expected_frames": expected_frames, "expected_seconds": expected_seconds})
    add("full video decode", all(x["returncode"] == 0 and x["frames"] == x["expected_frames"] and abs(x["seconds"] - x["expected_seconds"]) <= 1 / FPS for x in decode), decode)
    result = {"schema_version": "1.0", "status": "passed" if all(x["passed"] for x in checks) else "failed", "checks": checks, "remote_or_paid_work_performed": False}
    write_new_json(PACKAGE / "VALIDATION_V1.json", result)
    if result["status"] != "passed":
        raise AssemblyError(str([x for x in checks if not x["passed"]]))
    return result


def freeze() -> dict[str, Any]:
    validation = PACKAGE / "VALIDATION_V1.json"
    if not validation.is_file():
        raise AssemblyError("validate before freezing")
    files = set(input_paths() + [Path(__file__).resolve(), FACTORY / "tests/test_foundational_cm_seven_clip_assembly_v1.py"])
    files.update(path for path in PACKAGE.rglob("*") if path.is_file() and "ASSEMBLY_MANIFEST_V1" not in path.name)
    artifacts = [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size} for path in sorted(files, key=lambda item: item.as_posix())]
    manifest = {
        "schema_version": "1.0",
        "revision_id": "foundational-cm-seven-clip-assembly-v1",
        "date": "2026-09-12",
        "status": "local_silent_review_video_ready",
        "artifacts": artifacts,
        "artifact_identity_sha256": canonical_hash(artifacts),
        "audio_generated": False,
        "remote_or_paid_work_performed": False,
        "publication_performed": False,
        "commit_or_push_performed": False,
    }
    manifest_path = PACKAGE / "ASSEMBLY_MANIFEST_V1.json"
    write_new_json(manifest_path, manifest)
    write_new_text(PACKAGE / "ASSEMBLY_MANIFEST_V1.sha256", sha256(manifest_path) + "  ASSEMBLY_MANIFEST_V1.json\n")
    return manifest


def verify() -> dict[str, Any]:
    manifest_path = PACKAGE / "ASSEMBLY_MANIFEST_V1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    for item in manifest["artifacts"]:
        path = ROOT / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            failures.append(item["path"])
    expected = (PACKAGE / "ASSEMBLY_MANIFEST_V1.sha256").read_text(encoding="utf-8").split()[0]
    if sha256(manifest_path) != expected:
        failures.append(manifest_path.relative_to(ROOT).as_posix())
    result = {"schema_version": "1.0", "status": "passed" if not failures else "failed", "artifact_count": len(manifest["artifacts"]), "artifact_identity_sha256": manifest["artifact_identity_sha256"], "manifest_sha256": sha256(manifest_path), "failures": failures}
    if failures:
        raise AssemblyError(str(result))
    return result


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build-contract", "render", "validate", "freeze", "verify"))
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    actions = {"build-contract": build_contract, "render": lambda: render(args.workers), "validate": validate, "freeze": freeze, "verify": verify}
    print(json.dumps(actions[args.command](), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
