"""Render the focused tensor/retrieval feedback corrections locally.

This additive module preserves the frozen foundational production-v3 package.
It creates two silent review clips and related stills; it performs no network,
paid, publication, narration, master-render, commit, or push operation.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FACTORY = ROOT / "docs" / "video_factory"
PACKAGE = FACTORY / "deep_series" / "foundational_cm_feedback_round_v2"
LOGICAL_ROOT = FACTORY / "deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v5"
REPOSITORY_ROOT = FACTORY / "deep_series/episodes/what-is-explicit-cm/revision_v6"
BASE_MANIFEST = FACTORY / "deep_series/foundational_cm_production_v3/IMPLEMENTATION_MANIFEST_V4.json"
WIDTH, HEIGHT, FPS = 960, 540, 15


class FeedbackError(RuntimeError):
    pass


def load_base():
    path = FACTORY / "foundational_cm_corrections_v3.py"
    spec = importlib.util.spec_from_file_location("foundational_cm_corrections_v3", path)
    if not spec or not spec.loader:
        raise FeedbackError("could not load foundational v3 helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_base()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_new_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise FeedbackError(f"refusing to overwrite different feedback artifact: {path}")
        return
    path.write_text(text, encoding="utf-8", newline="\n")


def write_new_json(path: Path, value: Any) -> None:
    write_new_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def logical_matrix_4x4() -> str:
    rows = ("WY", "W¬Y", "¬WY", "¬W¬Y")
    cols = ("XZ", "X¬Z", "¬XZ", "¬X¬Z")
    header = "".join(f"<th>{html.escape(col)}</th>" for col in cols)
    body = []
    for r, row in enumerate(rows):
        cells = []
        for c, col in enumerate(cols):
            block = " block-cell" if r < 2 and c < 2 else ""
            cells.append(f'<td class="{block.strip()}" data-lm-cell="{r},{c}">{html.escape(row)}·{html.escape(col)}</td>')
        body.append(f"<tr><th>{html.escape(row)}</th>{''.join(cells)}</tr>")
    return f'<table class="lm4"><thead><tr><th>(W,Y)╲(X,Z)</th>{header}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def mini_matrix(name: str, values: tuple[tuple[str, str], tuple[str, str]]) -> str:
    cells = "".join(f"<i>{html.escape(value)}</i>" for row in values for value in row)
    return f'<div class="named-mini"><b>{name}</b><span>=</span><div class="mini-grid">{cells}</div></div>'


def repository_grid() -> str:
    rows = ("AB 00", "AB 01", "AB 10", "AB 11")
    cols = ("CD 00", "CD 01", "CD 10", "CD 11")
    values = ("0111", "0111", "0111", "1000")
    header = "".join(f"<th>{col}</th>" for col in cols)
    body = []
    for r, (label, bits) in enumerate(zip(rows, values)):
        cells = "".join(f'<td data-repo-cell="{r},{c}"><span data-output>{bit}</span></td>' for c, bit in enumerate(bits))
        body.append(f"<tr><th>{label}</th>{cells}</tr>")
    return f'<table class="repo4"><thead><tr><th>row ↓ / column →</th>{header}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def logical_body() -> str:
    mwx = mini_matrix("M<sub>WX</sub>", (("WX", "W¬X"), ("¬WX", "¬W¬X")))
    myz = mini_matrix("M<sub>YZ</sub>", (("YZ", "Y¬Z"), ("¬YZ", "¬Y¬Z")))
    return (
        '<div class="logical-stack">'
        f'<div class="source-equation">{mwx}<b class="tensor">⊗</b>{myz}</div>'
        '<div class="tensor-equation" data-show-at=".18">M<sub>WX</sub> ⊗ M<sub>YZ</sub> = M<sub>WXYZ</sub></div>'
        f'<div class="full-lm" data-show-at=".35">{logical_matrix_4x4()}</div>'
        '<div class="block-note" data-show-at=".68">WX × M<sub>YZ</sub> fills the highlighted 2×2 block · WY·XZ = W∧Y∧X∧Z</div>'
        '</div>'
    )


def repository_body() -> str:
    return (
        '<div class="repo-layout">'
        '<div class="repo-rule"><b>F=(A∧B)⊕(C∨D)</b><span class="split-line">split assignment as <strong>AB | CD</strong></span><span>00₂→0 · 01₂→1 · 10₂→2 · 11₂→3</span></div>'
        f'<div class="repo-matrix">{repository_grid()}</div>'
        '<div class="examples">'
        '<div class="example primary"><b>1110</b><span>AB=11₂ → row?</span><span>CD=10₂ → column?</span><span>F(1110) → output?</span><strong data-answer>(3,2): 1⊕1=0</strong></div>'
        '<div class="example" data-example=".68"><b>1011</b><span>AB=10₂ → row 2</span><span>CD=11₂ → column 3</span><strong>(2,3): 0⊕1=1</strong></div>'
        '<div class="example" data-example=".84"><b>0100</b><span>AB=01₂ → row 1</span><span>CD=00₂ → column 0</span><strong>(1,0): 0⊕0=0</strong></div>'
        '</div></div>'
    )


def css(sans: str, mono: str) -> str:
    return f'''@font-face{{font-family:D;src:url(data:font/ttf;base64,{sans})}}@font-face{{font-family:DM;src:url(data:font/ttf;base64,{mono})}}*{{box-sizing:border-box}}html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#081018;color:#eef5f7;font-family:D}}body{{--a:#f1b65c;--c:#57d4e8;--v:#a990ff;--s:#111d27;--line:#38505e}}.stage{{width:960px;height:540px;padding:25px 38px 48px;background:radial-gradient(circle at 80% 2%,#15303c,transparent 42%),#081018;position:relative}}header{{color:var(--a);font:700 10px DM;letter-spacing:.12em}}h1{{font-size:26px;margin:6px 0 8px}}footer{{position:absolute;bottom:14px;left:38px;right:38px;display:flex;justify-content:space-between;color:#bac7ce;font:600 10px DM}}.logical-stack{{display:flex;flex-direction:column;align-items:center;gap:6px}}.source-equation{{display:flex;align-items:center;justify-content:center;gap:22px;width:100%}}.named-mini{{display:flex;align-items:center;gap:10px;background:var(--s);border-top:3px solid var(--c);padding:6px 12px}}.named-mini>b,.named-mini>span{{font:700 19px DM}}.mini-grid{{display:grid;grid-template-columns:repeat(2,92px);grid-template-rows:repeat(2,25px);border:2px solid #dce8ed;padding:2px}}.mini-grid i{{display:grid;place-items:center;border:1px solid var(--line);font:700 14px DM;font-style:normal}}.tensor{{font:700 24px DM}}.tensor-equation{{font:700 21px DM;color:var(--c);min-height:27px}}.full-lm{{width:100%;display:grid;place-items:center}}table{{border-collapse:collapse}}.lm4{{width:790px;table-layout:fixed;font:700 13px DM}}.lm4 th{{color:var(--c);height:25px}}.lm4 tbody th{{color:var(--a);width:105px}}.lm4 td{{height:38px;text-align:center;background:#101c25;border:1px solid var(--line)}}.lm4 td.block-on{{background:#17313c;outline:2px solid var(--a);outline-offset:-2px;color:#fff}}.block-note{{border:2px solid var(--v);padding:5px 12px;font:700 13px DM;min-height:29px}}.repo-layout{{display:grid;grid-template-columns:270px 1fr;grid-template-rows:285px 125px;gap:10px 18px}}.repo-rule{{background:var(--s);border-top:4px solid var(--c);padding:14px;display:flex;flex-direction:column;gap:18px;font:700 15px DM}}.repo-rule b{{font-size:19px}}.repo-rule strong{{color:var(--a)}}.repo-rule .split-line{{white-space:nowrap}}.repo-matrix{{display:grid;place-items:center}}.repo4{{width:590px;table-layout:fixed;font:700 13px DM}}.repo4 th{{height:31px;color:var(--c)}}.repo4 tbody th{{color:var(--a);width:126px}}.repo4 td{{height:54px;text-align:center;background:#101c25;border:1px solid var(--line);font:700 22px DM}}.repo4 td.active{{outline:4px solid var(--a);outline-offset:-4px;color:var(--c)}}.examples{{grid-column:1/3;display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.example{{background:var(--s);border-top:3px solid var(--c);padding:8px 11px;display:flex;flex-direction:column;gap:2px;font:700 12px DM}}.example b{{color:var(--a);font-size:18px}}.example strong{{color:var(--c);font-size:14px}}[data-show-at],[data-example],[data-answer]{{opacity:0}}'''


def page(key: str, sans: str, mono: str) -> str:
    if key == "logical_block_v2":
        title, content = "Two complete LMs make one 4×4 tensor", logical_body()
    elif key == "repository_retrieval_v2":
        title, content = "Split the bits, index the cell, evaluate the rule", repository_body()
    else:
        raise FeedbackError(f"unknown visual: {key}")
    script = f'''window.__seek=function(p){{document.querySelectorAll('[data-show-at]').forEach(e=>e.style.opacity=p>=parseFloat(e.dataset.showAt)?1:0);document.querySelectorAll('[data-example]').forEach(e=>e.style.opacity=p>=parseFloat(e.dataset.example)?1:0);document.querySelectorAll('[data-answer]').forEach(e=>e.style.opacity=p>=.5?1:0);if('{key}'==='logical_block_v2'){{document.querySelectorAll('.block-cell').forEach(e=>e.classList.toggle('block-on',p>=.68))}}if('{key}'==='repository_retrieval_v2'){{document.querySelectorAll('[data-output]').forEach(e=>e.style.opacity=p>=.5?1:0);let target=p<.5?null:p<.68?'3,2':p<.84?'2,3':'1,0';document.querySelectorAll('[data-repo-cell]').forEach(e=>e.classList.toggle('active',e.dataset.repoCell===target))}}}};window.__seek(0)'''
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css(sans,mono)}</style></head><body><div class="stage"><header>CM FOUNDATIONS · FEEDBACK CORRECTION</header><h1>{title}</h1>{content}<footer><span>silent local review</span><span>960×540 · feedback v2</span></footer></div><script>{script}</script></body></html>'


STILLS = [
    ("logical_source_equations", "logical_block_v2", .12),
    ("logical_full_4x4", "logical_block_v2", .52),
    ("logical_top_left_block", "logical_block_v2", .90),
    ("repository_question", "repository_retrieval_v2", .30),
    ("repository_answer_1110", "repository_retrieval_v2", .58),
    ("repository_example_1011", "repository_retrieval_v2", .76),
    ("repository_example_0100", "repository_retrieval_v2", .94),
]
CLIPS = [
    ("logical_valuation_and_block_v2", "logical_block_v2", 14),
    ("repository_retrieval_v2", "repository_retrieval_v2", 14),
]


def build_contract() -> dict[str, Any]:
    inputs = [
        LOGICAL_ROOT / "SCRIPT_V5.md",
        LOGICAL_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V5.md",
        REPOSITORY_ROOT / "SCRIPT_V6.md",
        REPOSITORY_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V6.md",
        BASE_MANIFEST,
    ]
    contract = {
        "schema_version": "2.0",
        "status": "focused_silent_local_feedback_preview_only",
        "supersedes_clips": [
            "foundational_cm_production_v3/bounded_previews_v6/clips/logical_valuation_and_block.mp4",
            "foundational_cm_production_v3/bounded_previews_v6/clips/repository_retrieval.mp4",
        ],
        "inputs": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p)} for p in inputs],
        "preview_scope": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "stills": 7, "clips": 2, "clip_seconds": 28},
        "requirements": {
            "logical": ["visible equals signs", "M_WX tensor M_YZ", "complete 4x4 LM", "top-left 2x2 block highlight"],
            "repository": ["AB/CD split guide", "delayed 1110 answer", "worked 1011 comparison", "worked 0100 comparison", "persistent 4x4 grid"],
        },
        "audio_generated": False,
        "full_episode_or_master_rendered": False,
        "remote_or_paid_work_performed": False,
        "publication_authorized": False,
    }
    contract["contract_identity_sha256"] = canonical_hash(contract)
    write_new_json(PACKAGE / "FEEDBACK_CONTRACT_V2.json", contract)
    return contract


def render(workers: int = 2) -> dict[str, Any]:
    contract = build_contract()
    node = shutil.which("node")
    if not node or not BASE.FRAME_DRIVER.is_file():
        raise FeedbackError("existing local POP frame pipeline unavailable")
    from PIL import Image, ImageDraw
    import imageio_ffmpeg

    sans, mono = BASE.font_data()
    frames = PACKAGE / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    manifest = {"width": WIDTH, "height": HEIGHT, "fps": FPS, "scenes": [{"id": name, "kind": "cm_feedback", "startIndex": i, "progress": [p], "html": page(key, sans, mono)} for i, (name, key, p) in enumerate(STILLS)]}
    write_new_json(PACKAGE / "STILL_FRAME_MANIFEST_V2.json", manifest)
    result = subprocess.run([node, str(BASE.FRAME_DRIVER), str(PACKAGE / "STILL_FRAME_MANIFEST_V2.json"), str(frames), str(workers)], cwd=BASE.POP_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise FeedbackError(result.stderr[-1600:])
    rendered = sorted(frames.glob("f*.png"))
    if len(rendered) != len(STILLS):
        raise FeedbackError(f"expected {len(STILLS)} stills, got {len(rendered)}")
    still_root = PACKAGE / "stills"
    still_root.mkdir(exist_ok=True)
    still_records = []
    for source, (name, key, progress) in zip(rendered, STILLS):
        target = still_root / f"{name}.png"
        if target.exists() and sha256(target) != sha256(source):
            raise FeedbackError(f"refusing to overwrite changed still: {target}")
        if not target.exists():
            shutil.copyfile(source, target)
        still_records.append({"id": name, "visual": key, "progress": progress, "path": target.relative_to(ROOT).as_posix(), "sha256": sha256(target)})
    sheet = Image.new("RGB", (WIDTH * 2, HEIGHT * 4), "#081018")
    draw = ImageDraw.Draw(sheet)
    for i, (_, _, _) in enumerate(STILLS):
        target = still_root / f"{STILLS[i][0]}.png"
        x, y = (i % 2) * WIDTH, (i // 2) * HEIGHT
        sheet.paste(Image.open(target).convert("RGB"), (x, y))
        draw.rectangle((x, y, x + 330, y + 21), fill="#081018")
        draw.text((x + 5, y + 4), STILLS[i][0], fill="#f1b65c")
    contact = PACKAGE / "FEEDBACK_CONTACT_SHEET_V2.png"
    sheet.save(contact)
    clip_frames = PACKAGE / "clip_frames"
    clip_frames.mkdir(exist_ok=True)
    scenes, offset, total = [], 0, 0
    for name, key, duration in CLIPS:
        count = duration * FPS
        scenes.append({"id": name, "kind": "cm_feedback", "startIndex": offset, "progress": [(i + .5) / count for i in range(count)], "html": page(key, sans, mono)})
        offset += count
        total += duration
    write_new_json(PACKAGE / "CLIP_FRAME_MANIFEST_V2.json", {"width": WIDTH, "height": HEIGHT, "fps": FPS, "scenes": scenes})
    result = subprocess.run([node, str(BASE.FRAME_DRIVER), str(PACKAGE / "CLIP_FRAME_MANIFEST_V2.json"), str(clip_frames), str(workers)], cwd=BASE.POP_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise FeedbackError(result.stderr[-1600:])
    if len(list(clip_frames.glob("f*.png"))) != total * FPS:
        raise FeedbackError("clip frame count mismatch")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    clip_root = PACKAGE / "clips"
    clip_root.mkdir(exist_ok=True)
    clip_records, start = [], 0
    for name, key, duration in CLIPS:
        target = clip_root / f"{name}.mp4"
        command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-n", "-framerate", str(FPS), "-start_number", str(start), "-i", str(clip_frames / "f%06d.png"), "-frames:v", str(duration * FPS), "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target)]
        encoded = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if encoded.returncode and "already exists" not in encoded.stderr:
            raise FeedbackError(encoded.stderr[-1000:])
        clip_records.append({"id": name, "visual": key, "duration_s": duration, "frames": duration * FPS, "path": target.relative_to(ROOT).as_posix(), "sha256": sha256(target)})
        start += duration * FPS
    shutil.rmtree(frames)
    shutil.rmtree(clip_frames)
    report = {"schema_version": "2.0", "status": "focused_feedback_preview_complete_human_review_required", "contract_identity_sha256": contract["contract_identity_sha256"], "width": WIDTH, "height": HEIGHT, "fps": FPS, "stills": still_records, "clips": clip_records, "totals": {"stills": len(still_records), "clips": len(clip_records), "clip_seconds": total, "clip_frames": total * FPS}, "contact_sheet": {"path": contact.relative_to(ROOT).as_posix(), "sha256": sha256(contact)}, "supersedes_feedback_package": "foundational_cm_feedback_round_v1 (retained after QA found a wrapped split label and incomplete question card)", "audio_generated": False, "full_episode_or_master_rendered": False, "remote_or_paid_work_performed": False, "publication_authorized": False}
    write_new_json(PACKAGE / "FEEDBACK_PREVIEW_REPORT_V2.json", report)
    return report


def validate() -> dict[str, Any]:
    import imageio_ffmpeg

    contract = build_contract()
    report_path = PACKAGE / "FEEDBACK_PREVIEW_REPORT_V2.json"
    if not report_path.is_file():
        raise FeedbackError("render before validation")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    checks = []
    def add(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
    logical = logical_body()
    add("logical notation", all(x in logical for x in ("M<sub>WX</sub>", "M<sub>YZ</sub>", "M<sub>WXYZ</sub>", "⊗", "=")), "named matrices and tensor equation")
    add("complete logical matrix", logical.count("data-lm-cell=") == 16 and logical.count("block-cell") == 4, {"cells": logical.count("data-lm-cell="), "highlighted": logical.count("block-cell")})
    repository = repository_body()
    add("repository examples", all(x in repository for x in ("1110", "(3,2): 1⊕1=0", "1011", "(2,3): 0⊕1=1", "0100", "(1,0): 0⊕0=0")), "three verified examples")
    add("scope", report["totals"] == {"stills": 7, "clips": 2, "clip_seconds": 28, "clip_frames": 420}, report["totals"])
    add("media hashes", all(sha256(ROOT / item["path"]) == item["sha256"] for item in report["stills"] + report["clips"]), 9)
    decode = []
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    for clip in report["clips"]:
        path = ROOT / clip["path"]
        run = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"], capture_output=True)
        frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(path))
        decode.append({"id": clip["id"], "returncode": run.returncode, "frames": frames, "seconds": round(seconds, 3)})
    add("full clip decode", all(x["returncode"] == 0 and x["frames"] == 210 and x["seconds"] == 14 for x in decode), decode)
    result = {"schema_version": "2.0", "status": "passed" if all(x["passed"] for x in checks) else "failed", "contract_identity_sha256": contract["contract_identity_sha256"], "checks": checks, "remote_or_paid_work_performed": False}
    write_new_json(PACKAGE / "VALIDATION_V2.json", result)
    if result["status"] != "passed":
        raise FeedbackError(str([x for x in checks if not x["passed"]]))
    return result


def freeze() -> dict[str, Any]:
    validation = PACKAGE / "VALIDATION_V2.json"
    if not validation.is_file():
        raise FeedbackError("validate before freezing")
    files = {
        Path(__file__).resolve(),
        FACTORY / "tests/test_foundational_cm_feedback_corrections_v1.py",
        LOGICAL_ROOT / "SCRIPT_V5.md",
        LOGICAL_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V5.md",
        REPOSITORY_ROOT / "SCRIPT_V6.md",
        REPOSITORY_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V6.md",
        BASE_MANIFEST,
    }
    files.update(path for path in PACKAGE.rglob("*") if path.is_file() and "FEEDBACK_MANIFEST_V2" not in path.name)
    artifacts = [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size} for path in sorted(files, key=lambda p: p.as_posix())]
    manifest = {"schema_version": "2.0", "revision_id": "foundational-cm-feedback-round-v2", "date": "2026-09-12", "status": "local_human_review_ready", "artifacts": artifacts, "artifact_identity_sha256": canonical_hash(artifacts), "audio_generated": False, "full_episode_or_master_rendered": False, "remote_or_paid_work_performed": False, "publication_performed": False, "commit_or_push_performed": False}
    path = PACKAGE / "FEEDBACK_MANIFEST_V2.json"
    write_new_json(path, manifest)
    write_new_text(PACKAGE / "FEEDBACK_MANIFEST_V2.sha256", sha256(path) + "  FEEDBACK_MANIFEST_V2.json\n")
    return manifest


def verify() -> dict[str, Any]:
    path = PACKAGE / "FEEDBACK_MANIFEST_V2.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    failures = [item["path"] for item in manifest["artifacts"] if not (ROOT / item["path"]).is_file() or sha256(ROOT / item["path"]) != item["sha256"] or (ROOT / item["path"]).stat().st_size != item["bytes"]]
    expected = (PACKAGE / "FEEDBACK_MANIFEST_V2.sha256").read_text(encoding="utf-8").split()[0]
    if sha256(path) != expected:
        failures.append(path.relative_to(ROOT).as_posix())
    result = {"schema_version": "2.0", "status": "passed" if not failures else "failed", "artifact_count": len(manifest["artifacts"]), "artifact_identity_sha256": manifest["artifact_identity_sha256"], "manifest_sha256": sha256(path), "failures": failures}
    if failures:
        raise FeedbackError(str(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build-contract", "render", "validate", "freeze", "verify"))
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    actions = {"build-contract": build_contract, "render": lambda: render(args.workers), "validate": validate, "freeze": freeze, "verify": verify}
    print(json.dumps(actions[args.command](), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
