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
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FACTORY = ROOT / "docs" / "video_factory"
PACKAGE = FACTORY / "deep_series" / "foundational_cm_feedback_round_v3"
OPERATOR_ROOT = FACTORY / "deep_series/episodes/operator-cms-from-truth-tables/revision_v5"
LOGICAL_ROOT = FACTORY / "deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v6"
REPOSITORY_ROOT = FACTORY / "deep_series/episodes/what-is-explicit-cm/revision_v7"
BASE_MANIFEST = FACTORY / "deep_series/foundational_cm_production_v3/IMPLEMENTATION_MANIFEST_V4.json"
NOTATION_STANDARD = ROOT / "docs/CM_NOTATION_STANDARD_V1.md"
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
    return f'<table class="lm4"><thead><tr><th>row ↓</th>{header}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def mini_matrix(name: str, values: tuple[tuple[str, str], tuple[str, str]]) -> str:
    cells = "".join(f"<i>{html.escape(value)}</i>" for row in values for value in row)
    return f'<div class="named-mini"><b>{name}</b><span>=</span><div class="mini-grid">{cells}</div></div>'


def repository_grid() -> str:
    rows = ("AB 00", "AB 01", "AB 10", "AB 11")
    cols = ("CD 00", "CD 01", "CD 10", "CD 11")
    values = ("0111", "0111", "0111", "1000")
    header = "".join(f'<th data-col-header="{c}">{col}</th>' for c, col in enumerate(cols))
    body = []
    for r, (label, bits) in enumerate(zip(rows, values)):
        cells = "".join(f'<td data-repo-cell="{r},{c}"><span data-output>{bit}</span></td>' for c, bit in enumerate(bits))
        body.append(f'<tr><th data-row-header="{r}">{label}</th>{cells}</tr>')
    return f'<table class="repo4"><thead><tr><th>row ↓ / column →</th>{header}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def logical_body() -> str:
    mwx = mini_matrix("[M<sub>WX</sub>]", (("WX", "W¬X"), ("¬WX", "¬W¬X")))
    myz = mini_matrix("[M<sub>YZ</sub>]", (("YZ", "Y¬Z"), ("¬YZ", "¬Y¬Z")))
    return (
        '<div class="logical-stack">'
        f'<div class="source-equation">{mwx}<b class="tensor">⊗</b>{myz}</div>'
        '<div class="tensor-equation" data-show-at=".16">[[M<sub>WX</sub>] ⊗ [M<sub>YZ</sub>]] = [M<sub>WXYZ</sub>]</div>'
        '<div class="axis-label" data-show-at=".28"><span>row components: (W,Y)</span><span>column components: (X,Z)</span></div>'
        f'<div class="full-lm" data-show-at=".28">{logical_matrix_4x4()}</div>'
        '<div class="block-note" data-show-at=".66">top-left entry of [M<sub>WX</sub>] is WX · WX × [M<sub>YZ</sub>] fills this 2×2 block</div>'
        '<div class="measurement" data-show-at=".82"><span>paper measurement:</span> ⟨Y|⟨W|[M<sub>WXYZ</sub>]|X⟩|Z⟩ <b>· selected cell: WY·XZ = W∧Y∧X∧Z</b></div>'
        '</div>'
    )


def repository_body() -> str:
    return (
        '<div class="repo-layout">'
        '<div class="repo-rule"><b>F=(A∧B)⇕(C∨D)</b><span class="split-line">split assignment as <strong>AB | CD</strong></span><span class="index-key">00₂→0 · 01₂→1 · 10₂→2 · 11₂→3</span><div class="question">1110 → row? column? output?</div><div class="trace" data-step=".30"><strong>1 · split</strong><span>1110 → AB=11 | CD=10</span></div><div class="trace" data-step=".42"><strong>2 · index</strong><span>AB=11₂ → row 3</span><span>CD=10₂ → column 2</span></div><div class="trace" data-step=".54"><strong>3 · evaluate</strong><span>A∧B=1 · C∨D=1</span><span>1⇕1=0 → cell (3,2)</span></div></div>'
        f'<div class="repo-matrix">{repository_grid()}</div>'
        '<div class="examples">'
        '<div class="example" data-example=".70"><b>1011</b><span>AB=10₂ → row 2 · CD=11₂ → column 3</span><strong>(2,3): 0⇕1=1</strong></div>'
        '<div class="example" data-example=".85"><b>0100</b><span>AB=01₂ → row 1 · CD=00₂ → column 0</span><strong>(1,0): 0⇕0=0</strong></div>'
        '</div></div>'
    )


def css(sans: str, mono: str) -> str:
    return f'''@font-face{{font-family:D;src:url(data:font/ttf;base64,{sans})}}@font-face{{font-family:DM;src:url(data:font/ttf;base64,{mono})}}*{{box-sizing:border-box}}html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#081018;color:#eef5f7;font-family:D}}body{{--a:#f1b65c;--c:#57d4e8;--v:#a990ff;--s:#111d27;--line:#38505e}}.stage{{width:960px;height:540px;padding:22px 38px 45px;background:radial-gradient(circle at 80% 2%,#15303c,transparent 42%),#081018;position:relative}}header{{color:var(--a);font:700 10px DM;letter-spacing:.12em}}h1{{font-size:25px;margin:5px 0 7px}}footer{{position:absolute;bottom:13px;left:38px;right:38px;display:flex;justify-content:space-between;color:#bac7ce;font:600 10px DM}}.logical-stack{{display:flex;flex-direction:column;align-items:center;gap:4px}}.source-equation{{display:flex;align-items:center;justify-content:center;gap:20px;width:100%}}.named-mini{{display:flex;align-items:center;gap:9px;background:var(--s);border-top:3px solid var(--c);padding:5px 10px}}.named-mini>b,.named-mini>span{{font:700 17px DM}}.mini-grid{{display:grid;grid-template-columns:repeat(2,88px);grid-template-rows:repeat(2,22px);border:2px solid #dce8ed;padding:2px}}.mini-grid i{{display:grid;place-items:center;border:1px solid var(--line);font:700 13px DM;font-style:normal}}.tensor{{font:700 23px DM}}.tensor-equation{{font:700 19px DM;color:var(--c);min-height:24px}}.axis-label{{width:790px;display:flex;justify-content:space-between;color:#bac7ce;font:700 11px DM;min-height:15px}}.full-lm{{width:100%;display:grid;place-items:center}}table{{border-collapse:collapse}}.lm4{{width:790px;table-layout:fixed;font:700 12px DM}}.lm4 th{{color:var(--c);height:22px}}.lm4 tbody th{{color:var(--a);width:105px}}.lm4 td{{height:33px;text-align:center;background:#101c25;border:1px solid var(--line)}}.lm4 td.block-on{{background:#17313c;outline:2px solid var(--a);outline-offset:-2px;color:#fff}}.block-note{{border:2px solid var(--v);padding:4px 10px;font:700 12px DM;min-height:26px}}.measurement{{font:700 11px DM;color:#dce8ed;min-height:19px}}.measurement>span{{color:var(--a)}}.measurement>b{{color:var(--c)}}.repo-layout{{display:grid;grid-template-columns:310px 1fr;grid-template-rows:300px 102px;gap:9px 14px}}.repo-rule{{background:var(--s);border-top:4px solid var(--c);padding:10px 12px;display:flex;flex-direction:column;gap:5px;font:700 12px DM}}.repo-rule>b{{font-size:18px}}.repo-rule strong{{color:var(--a)}}.repo-rule .split-line{{white-space:nowrap}}.index-key{{font-size:10px;color:#bac7ce}}.question{{border:2px solid var(--v);padding:6px 7px;font:700 13px DM;margin-top:2px}}.trace{{display:flex;flex-direction:column;border-left:3px solid var(--c);padding:3px 7px;gap:1px;font:700 11px DM;opacity:0}}.repo-matrix{{display:grid;place-items:center}}.repo4{{width:560px;table-layout:fixed;font:700 12px DM}}.repo4 th{{height:31px;color:var(--c)}}.repo4 tbody th{{color:var(--a);width:115px}}.repo4 td{{height:54px;text-align:center;background:#101c25;border:1px solid var(--line);font:700 21px DM}}.repo4 td.active{{outline:4px solid var(--a);outline-offset:-4px;color:var(--c)}}.repo4 th.active-header{{background:#26323a;color:#fff;outline:3px solid var(--a);outline-offset:-3px}}.examples{{grid-column:1/3;display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}.example{{background:var(--s);border-top:3px solid var(--c);padding:8px 12px;display:flex;flex-direction:column;gap:3px;font:700 12px DM}}.example b{{color:var(--a);font-size:18px}}.example strong{{color:var(--c);font-size:14px}}[data-show-at],[data-example]{{opacity:0}}'''


def page(key: str, sans: str, mono: str) -> str:
    if key == "logical_block_v3":
        title, content = "Two complete LMs make one 4×4 tensor", logical_body()
    elif key == "repository_retrieval_v3":
        title, content = "Split the bits, index the cell, evaluate the rule", repository_body()
    else:
        raise FeedbackError(f"unknown visual: {key}")
    script = f'''window.__seek=function(p){{document.querySelectorAll('[data-show-at]').forEach(e=>e.style.opacity=p>=parseFloat(e.dataset.showAt)?1:0);document.querySelectorAll('[data-step]').forEach(e=>e.style.opacity=p>=parseFloat(e.dataset.step)?1:0);document.querySelectorAll('[data-example]').forEach(e=>e.style.opacity=p>=parseFloat(e.dataset.example)?1:0);if('{key}'==='logical_block_v3'){{document.querySelectorAll('.block-cell').forEach(e=>e.classList.toggle('block-on',p>=.66))}}if('{key}'==='repository_retrieval_v3'){{document.querySelectorAll('[data-output]').forEach(e=>e.style.opacity=p>=.54?1:0);let row=p<.42?null:p<.70?'3':p<.85?'2':'1';let col=p<.42?null:p<.70?'2':p<.85?'3':'0';let target=p<.54?null:p<.70?'3,2':p<.85?'2,3':'1,0';document.querySelectorAll('[data-row-header]').forEach(e=>e.classList.toggle('active-header',e.dataset.rowHeader===row));document.querySelectorAll('[data-col-header]').forEach(e=>e.classList.toggle('active-header',e.dataset.colHeader===col));document.querySelectorAll('[data-repo-cell]').forEach(e=>e.classList.toggle('active',e.dataset.repoCell===target))}}}};window.__seek(0)'''
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css(sans,mono)}</style></head><body><div class="stage"><header>CM FOUNDATIONS · FEEDBACK CORRECTION</header><h1>{title}</h1>{content}<footer><span>silent local review</span><span>960×540 · feedback v3</span></footer></div><script>{script}</script></body></html>'


STILLS = [
    ("logical_source_equations", "logical_block_v3", .12),
    ("logical_full_4x4", "logical_block_v3", .52),
    ("logical_top_left_block", "logical_block_v3", .90),
    ("repository_question", "repository_retrieval_v3", .24),
    ("repository_split_1110", "repository_retrieval_v3", .35),
    ("repository_index_1110", "repository_retrieval_v3", .47),
    ("repository_answer_1110", "repository_retrieval_v3", .60),
    ("repository_example_1011", "repository_retrieval_v3", .77),
    ("repository_example_0100", "repository_retrieval_v3", .93),
]
CLIPS = [
    ("logical_valuation_and_block_v3", "logical_block_v3", 14),
    ("repository_retrieval_v3", "repository_retrieval_v3", 14),
]


def build_contract() -> dict[str, Any]:
    inputs = [
        OPERATOR_ROOT / "SCRIPT_V5.md",
        OPERATOR_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V5.md",
        LOGICAL_ROOT / "SCRIPT_V6.md",
        LOGICAL_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V6.md",
        REPOSITORY_ROOT / "SCRIPT_V7.md",
        REPOSITORY_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V7.md",
        NOTATION_STANDARD,
        BASE_MANIFEST,
    ]
    contract = {
        "schema_version": "3.0",
        "status": "focused_silent_local_feedback_preview_only",
        "supersedes_clips": [
            "foundational_cm_feedback_round_v2/clips/logical_valuation_and_block_v2.mp4",
            "foundational_cm_feedback_round_v2/clips/repository_retrieval_v2.mp4",
        ],
        "inputs": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p)} for p in inputs],
        "preview_scope": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "stills": 9, "clips": 2, "clip_seconds": 28},
        "requirements": {
            "notation": ["logical XOR uses ⇕ (LaTeX \\Updownarrow)", "no circled-plus substitution in successor mathematical displays"],
            "logical": ["visible matrix equals signs", "whole [M_WX] tensor [M_YZ] construction", "complete 4x4 LM", "top-left entry versus 2x2 block distinction", "separate row and column labels", "paper measurement line"],
            "repository": ["four-second question state", "progressive split/index/evaluate trace", "matching header and cell highlights", "worked 1011 comparison", "worked 0100 comparison", "persistent 4x4 grid"],
        },
        "audio_generated": False,
        "full_episode_or_master_rendered": False,
        "remote_or_paid_work_performed": False,
        "publication_authorized": False,
    }
    contract["contract_identity_sha256"] = canonical_hash(contract)
    write_new_json(PACKAGE / "FEEDBACK_CONTRACT_V3.json", contract)
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
    write_new_json(PACKAGE / "STILL_FRAME_MANIFEST_V3.json", manifest)
    result = subprocess.run([node, str(BASE.FRAME_DRIVER), str(PACKAGE / "STILL_FRAME_MANIFEST_V3.json"), str(frames), str(workers)], cwd=BASE.POP_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
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
    sheet_rows = (len(STILLS) + 1) // 2
    sheet = Image.new("RGB", (WIDTH * 2, HEIGHT * sheet_rows), "#081018")
    draw = ImageDraw.Draw(sheet)
    for i, (_, _, _) in enumerate(STILLS):
        target = still_root / f"{STILLS[i][0]}.png"
        x, y = (i % 2) * WIDTH, (i // 2) * HEIGHT
        sheet.paste(Image.open(target).convert("RGB"), (x, y))
        draw.rectangle((x, y, x + 330, y + 21), fill="#081018")
        draw.text((x + 5, y + 4), STILLS[i][0], fill="#f1b65c")
    contact = PACKAGE / "FEEDBACK_CONTACT_SHEET_V3.png"
    sheet.save(contact)
    clip_frames = PACKAGE / "clip_frames"
    clip_frames.mkdir(exist_ok=True)
    scenes, offset, total = [], 0, 0
    for name, key, duration in CLIPS:
        count = duration * FPS
        scenes.append({"id": name, "kind": "cm_feedback", "startIndex": offset, "progress": [(i + .5) / count for i in range(count)], "html": page(key, sans, mono)})
        offset += count
        total += duration
    write_new_json(PACKAGE / "CLIP_FRAME_MANIFEST_V3.json", {"width": WIDTH, "height": HEIGHT, "fps": FPS, "scenes": scenes})
    result = subprocess.run([node, str(BASE.FRAME_DRIVER), str(PACKAGE / "CLIP_FRAME_MANIFEST_V3.json"), str(clip_frames), str(workers)], cwd=BASE.POP_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
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
    report = {"schema_version": "3.0", "status": "focused_feedback_preview_complete_human_review_required", "contract_identity_sha256": contract["contract_identity_sha256"], "width": WIDTH, "height": HEIGHT, "fps": FPS, "stills": still_records, "clips": clip_records, "totals": {"stills": len(still_records), "clips": len(clip_records), "clip_seconds": total, "clip_frames": total * FPS}, "contact_sheet": {"path": contact.relative_to(ROOT).as_posix(), "sha256": sha256(contact)}, "supersedes_feedback_package": "foundational_cm_feedback_round_v2 (retained as frozen review evidence)", "audio_generated": False, "full_episode_or_master_rendered": False, "remote_or_paid_work_performed": False, "publication_authorized": False}
    write_new_json(PACKAGE / "FEEDBACK_PREVIEW_REPORT_V3.json", report)
    return report


def validate() -> dict[str, Any]:
    import imageio_ffmpeg

    contract = build_contract()
    report_path = PACKAGE / "FEEDBACK_PREVIEW_REPORT_V3.json"
    if not report_path.is_file():
        raise FeedbackError("render before validation")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    checks = []
    def add(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
    logical = logical_body()
    add("logical notation", all(x in logical for x in ("[M<sub>WX</sub>]", "[M<sub>YZ</sub>]", "[M<sub>WXYZ</sub>]", "⊗", "=")), "bracketed named matrices and tensor equation")
    add("complete logical matrix", logical.count("data-lm-cell=") == 16 and logical.count("block-cell") == 4, {"cells": logical.count("data-lm-cell="), "highlighted": logical.count("block-cell")})
    add("logical labels", all(x in logical for x in ("row components: (W,Y)", "column components: (X,Z)", "top-left entry of [M<sub>WX</sub>] is WX", "paper measurement:")) and "╲" not in logical and "\\(X,Z)" not in logical, "separate axes, scalar block factor, and paper measurement")
    repository = repository_body()
    add("repository examples", all(x in repository for x in ("1110", "1⇕1=0", "1011", "(2,3): 0⇕1=1", "0100", "(1,0): 0⇕0=0")), "three verified examples")
    add("progressive retrieval", repository.count("data-step=") == 3 and all(x in repository for x in ("1 · split", "2 · index", "3 · evaluate")), "three staged explanation steps")
    candidate_text = "\n".join(path.read_text(encoding="utf-8") for path in (
        OPERATOR_ROOT / "SCRIPT_V5.md",
        OPERATOR_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V5.md",
        LOGICAL_ROOT / "SCRIPT_V6.md",
        LOGICAL_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V6.md",
        REPOSITORY_ROOT / "SCRIPT_V7.md",
        REPOSITORY_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V7.md",
    ))
    add("successor XOR glyph", "⊕" not in candidate_text and "\\oplus" not in candidate_text and "⇕" in candidate_text and "⊕" not in repository, "⇕ only in successor mathematical displays")
    add("scope", report["totals"] == {"stills": 9, "clips": 2, "clip_seconds": 28, "clip_frames": 420}, report["totals"])
    add("media hashes", all(sha256(ROOT / item["path"]) == item["sha256"] for item in report["stills"] + report["clips"]), 11)
    decode = []
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    for clip in report["clips"]:
        path = ROOT / clip["path"]
        run = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"], capture_output=True)
        frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(path))
        decode.append({"id": clip["id"], "returncode": run.returncode, "frames": frames, "seconds": round(seconds, 3)})
    add("full clip decode", all(x["returncode"] == 0 and x["frames"] == 210 and x["seconds"] == 14 for x in decode), decode)
    result = {"schema_version": "3.0", "status": "passed" if all(x["passed"] for x in checks) else "failed", "contract_identity_sha256": contract["contract_identity_sha256"], "checks": checks, "remote_or_paid_work_performed": False}
    write_new_json(PACKAGE / "VALIDATION_V3.json", result)
    if result["status"] != "passed":
        raise FeedbackError(str([x for x in checks if not x["passed"]]))
    return result


def freeze() -> dict[str, Any]:
    validation = PACKAGE / "VALIDATION_V3.json"
    if not validation.is_file():
        raise FeedbackError("validate before freezing")
    files = {
        Path(__file__).resolve(),
        FACTORY / "tests/test_foundational_cm_feedback_corrections_v2.py",
        ROOT / "docs/AGENTS.md",
        NOTATION_STANDARD,
        OPERATOR_ROOT / "SCRIPT_V5.md",
        OPERATOR_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V5.md",
        LOGICAL_ROOT / "SCRIPT_V6.md",
        LOGICAL_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V6.md",
        REPOSITORY_ROOT / "SCRIPT_V7.md",
        REPOSITORY_ROOT / "VISUAL_AND_PRODUCTION_SPEC_V7.md",
        BASE_MANIFEST,
    }
    files.update(path for path in PACKAGE.rglob("*") if path.is_file() and "FEEDBACK_MANIFEST_V3" not in path.name)
    artifacts = [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size} for path in sorted(files, key=lambda p: p.as_posix())]
    manifest = {"schema_version": "3.0", "revision_id": "foundational-cm-feedback-round-v3", "date": "2026-09-12", "status": "local_human_review_ready", "artifacts": artifacts, "artifact_identity_sha256": canonical_hash(artifacts), "audio_generated": False, "full_episode_or_master_rendered": False, "remote_or_paid_work_performed": False, "publication_performed": False, "commit_or_push_performed": False}
    path = PACKAGE / "FEEDBACK_MANIFEST_V3.json"
    write_new_json(path, manifest)
    write_new_text(PACKAGE / "FEEDBACK_MANIFEST_V3.sha256", sha256(path) + "  FEEDBACK_MANIFEST_V3.json\n")
    return manifest


def verify() -> dict[str, Any]:
    path = PACKAGE / "FEEDBACK_MANIFEST_V3.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    failures = [item["path"] for item in manifest["artifacts"] if not (ROOT / item["path"]).is_file() or sha256(ROOT / item["path"]) != item["sha256"] or (ROOT / item["path"]).stat().st_size != item["bytes"]]
    expected = (PACKAGE / "FEEDBACK_MANIFEST_V3.sha256").read_text(encoding="utf-8").split()[0]
    if sha256(path) != expected:
        failures.append(path.relative_to(ROOT).as_posix())
    result = {"schema_version": "3.0", "status": "passed" if not failures else "failed", "artifact_count": len(manifest["artifacts"]), "artifact_identity_sha256": manifest["artifact_identity_sha256"], "manifest_sha256": sha256(path), "failures": failures}
    if failures:
        raise FeedbackError(str(result))
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
