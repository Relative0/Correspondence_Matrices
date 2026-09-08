"""Build symbol-safe production contracts and lightweight previews for three CM lessons.

This is a deterministic, local preparation tool.  It never reads credentials,
uses a network service, synthesizes narration, or creates a paid resource.
Full-frame rendering is available for a separately authorized remote worker;
the default preview renders one settled frame per scene.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FACTORY = ROOT / "docs" / "video_factory"
PACKAGE = FACTORY / "deep_series" / "foundational_cm_production_v2"
POP_ROOT = Path(os.environ.get("CM_POP_ROOT", str(ROOT.parent / "PoP" / "Tools" / "POP-Video-Creator"))).resolve()
FRAME_DRIVER = POP_ROOT / "pop_video" / "render" / "frame_driver.js"
FPS = 30

SCRIPT_PATHS = {
    "operator-cms-from-truth-tables": FACTORY / "deep_series" / "episodes" / "operator-cms-from-truth-tables" / "revision_v3" / "SCRIPT_V3.md",
    "logical-matrices-to-higher-dimensional-cms": FACTORY / "deep_series" / "episodes" / "logical-matrices-to-higher-dimensional-cms" / "revision_v3" / "SCRIPT_V3.md",
    "what-is-explicit-cm": FACTORY / "deep_series" / "episodes" / "what-is-explicit-cm" / "revision_v4" / "SCRIPT_V4.md",
}

SYMBOLS = {
    "multiplication": "×",
    "negation": "¬",
    "conjunction": "∧",
    "disjunction": "∨",
    "exclusive_or": "⊕",
    "implication": "→",
    "equivalence": "↔",
    "maps_to": "↦",
    "subscript_two": "₂",
    "superscript_four": "⁴",
    "left_angle_bracket": "⟨",
    "right_angle_bracket": "⟩",
    "tensor_product": "⊗",
    "transpose": "ᵀ",
}
REQUIRED_TEXT = "".join(SYMBOLS.values()) + "VTMWXYZABCD0123456789[]=(),./-+"


class ProductionError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def parse_time(value: str) -> float:
    minute, second = value.split(":")
    return int(minute) * 60 + int(second)


def parse_script(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    sections = []
    pattern = re.compile(
        r"^## (\d+:\d+)–(\d+:\d+) — (.*?)\n\n\*\*Voiceover\*\*\n\n(.*?)\n\n\*\*Visual\*\*\n\n(.*?)(?=\n## |\Z)",
        re.M | re.S,
    )
    for index, match in enumerate(pattern.finditer(text), 1):
        start, end, title, voice, visual = match.groups()
        pause_marker = "*[Four-second retrieval pause.]*"
        if pause_marker in voice:
            before, after = voice.split(pause_marker, 1)
            voice_segments = [
                {"kind": "speech", "text": before.strip()},
                {"kind": "pause", "duration_s": 4.0},
                {"kind": "speech", "text": after.strip()},
            ]
        else:
            voice_segments = [{"kind": "speech", "text": voice.strip()}]
        sections.append({
            "scene_id": f"s{index:02d}",
            "title": title.strip(),
            "start_s": parse_time(start),
            "end_s": parse_time(end),
            "duration_s": parse_time(end) - parse_time(start),
            "voiceover": re.sub(r"\*\[.*?\]\*", "", voice, flags=re.S).strip(),
            "voice_segments": voice_segments,
            "visual_direction": visual.strip(),
        })
    if not sections or sections[0]["start_s"] != 0:
        raise ProductionError(f"could not parse timestamped sections: {path}")
    if any(a["end_s"] != b["start_s"] for a, b in zip(sections, sections[1:])):
        raise ProductionError(f"non-contiguous sections: {path}")
    return sections


def locate_fonts() -> tuple[Path, Path]:
    candidates: list[tuple[Path, Path]] = []
    env_dir = os.environ.get("CM_MATH_FONT_DIR")
    if env_dir:
        base = Path(env_dir)
        candidates.append((base / "DejaVuSans.ttf", base / "DejaVuSansMono.ttf"))
    candidates.extend([
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")),
        (Path(sys.prefix) / "Lib" / "site-packages" / "matplotlib" / "mpl-data" / "fonts" / "ttf" / "DejaVuSans.ttf",
         Path(sys.prefix) / "Lib" / "site-packages" / "matplotlib" / "mpl-data" / "fonts" / "ttf" / "DejaVuSansMono.ttf"),
    ])
    try:
        from matplotlib import font_manager
        candidates.insert(0, (Path(font_manager.findfont("DejaVu Sans")), Path(font_manager.findfont("DejaVu Sans Mono"))))
    except Exception:
        pass
    for sans, mono in candidates:
        if sans.is_file() and mono.is_file():
            return sans.resolve(), mono.resolve()
    raise ProductionError("DejaVu Sans and DejaVu Sans Mono were not found")


def font_codepoints(path: Path) -> set[int]:
    try:
        from fontTools.ttLib import TTFont
    except ImportError as exc:
        raise ProductionError("fontTools is required for glyph coverage validation") from exc
    font = TTFont(path, lazy=True)
    try:
        points: set[int] = set()
        for table in font["cmap"].tables:
            points.update(table.cmap)
        return points
    finally:
        font.close()


def font_contract() -> dict[str, Any]:
    sans, mono = locate_fonts()
    sans_points = font_codepoints(sans)
    mono_points = font_codepoints(mono)
    coverage = []
    for name, glyph in SYMBOLS.items():
        cp = ord(glyph)
        coverage.append({
            "name": name,
            "glyph": glyph,
            "codepoint": f"U+{cp:04X}",
            "sans": cp in sans_points,
            "mono": cp in mono_points,
        })
    missing = [item for item in coverage if not item["sans"]]
    if missing:
        raise ProductionError(f"required glyphs missing from DejaVu Sans: {missing}")
    return {
        "schema_version": "1.0",
        "status": "passed",
        "font_policy": {
            "display_and_math": "Embedded DejaVu Sans",
            "indices_and_bits": "Embedded DejaVu Sans Mono",
            "docker_packages": ["fonts-dejavu-core", "fonts-liberation"],
            "matrix_brackets": "drawn geometry; never bracket-font dependent",
            "subscripts": "HTML <sub> markup except the explicitly tested ₂ glyph",
            "superscripts": "HTML <sup> markup except the explicitly tested ⁴ glyph",
            "xor": "⊕ for displayed algebra; XOR in narration",
        },
        "fonts": {
            "sans": {"path": str(sans), "sha256": sha256(sans), "bytes": sans.stat().st_size},
            "mono": {"path": str(mono), "sha256": sha256(mono), "bytes": mono.stat().st_size},
        },
        "coverage": coverage,
        "remote_requirement": "RunPod image must install fonts-dejavu-core and pass the same cmap audit before rendering.",
    }


def b64_font(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def matrix(bits: str, rows: int, columns: int, *, row_labels: list[str] | None = None,
           column_labels: list[str] | None = None, cell_labels: list[str] | None = None,
           active: set[int] | None = None, css_class: str = "") -> str:
    row_labels = row_labels or []
    column_labels = column_labels or []
    active = active or set()
    cells = []
    for i, bit in enumerate(bits):
        label = cell_labels[i] if cell_labels else ""
        cells.append(
            f'<div class="cell {"on" if bit == "1" else "off"} {"active" if i in active else ""}" data-at="{0.08 + i * 0.035:.3f}">'
            f'<span>{html.escape(bit)}</span><small>{html.escape(label)}</small></div>'
        )
    cols = "".join(f"<b>{html.escape(x)}</b>" for x in column_labels)
    rows_html = "".join(f"<b>{html.escape(x)}</b>" for x in row_labels)
    return f'''<div class="matrix-wrap {css_class}">
      <div class="col-labels" style="--cols:{columns}">{cols}</div>
      <div class="row-labels" style="--rows:{rows}">{rows_html}</div>
      <div class="bracket left"></div><div class="grid" style="--cols:{columns}">{''.join(cells)}</div><div class="bracket right"></div>
    </div>'''


def mini_matrix(bits: str, label: str = "", highlight: bool = False) -> str:
    cells = "".join(f'<i class="{"one" if b == "1" else "zero"}">{b}</i>' for b in bits)
    return f'<div class="mini {"highlight" if highlight else ""}"><div class="mini-grid">{cells}</div><span>{html.escape(label)}</span></div>'


DYADS = ("|1⟩⟨1|", "|1⟩⟨0|", "|0⟩⟨1|", "|0⟩⟨0|")


def dyad_expression(bits: str) -> str:
    terms = [term for bit, term in zip(bits, DYADS) if bit == "1"]
    return " ⊕ ".join(terms) if terms else "0"


def operator_tile(bits: str, label: str, *, highlight: bool = False) -> str:
    cells = "".join(f'<i class="{"one" if bit == "1" else "zero"}">{bit}</i>' for bit in bits)
    return (
        f'<div class="operator-tile {"highlight" if highlight else ""}">'
        f'<b>{html.escape(label)}</b><div class="operator-matrix">{cells}</div>'
        f'<span>{html.escape(dyad_expression(bits))}</span></div>'
    )


def operator_table_html() -> str:
    operators = (
        ("1111", "true"), ("0000", "false"), ("1001", "equivalence"), ("0110", "XOR"),
        ("1000", "AND"), ("0001", "NOR"), ("0100", "X∧¬Y"), ("0010", "¬X∧Y"),
        ("1011", "X→Y"), ("1101", "Y→X"), ("1110", "OR"), ("0111", "NAND"),
        ("1010", "Y"), ("0101", "¬Y"), ("1100", "X"), ("0011", "¬X"),
    )
    highlighted = {"1000", "1001", "0110", "1110"}
    return '<div class="operator-table">' + "".join(
        operator_tile(bits, label, highlight=bits in highlighted) for bits, label in operators
    ) + "</div>"


def basis_dyads_html() -> str:
    items = (
        ("1000", "|1⟩⟨1|"), ("0100", "|1⟩⟨0|"),
        ("0010", "|0⟩⟨1|"), ("0001", "|0⟩⟨0|"),
    )
    cards = "".join(
        f'<div class="dyad-card"><b>{html.escape(label)}</b>{mini_matrix(bits)}</div>'
        for bits, label in items
    )
    return (
        '<div class="state-vectors"><span>|1⟩ = [1,0]ᵀ</span><span>|0⟩ = [0,1]ᵀ</span>'
        '<strong>|i⟩ ⊗ ⟨j| = |i⟩⟨j|</strong></div>'
        f'<div class="dyad-grid">{cards}</div><div class="basis-caption">four basis dyads · one active cell each</div>'
    )


def scene_body(video_id: str, index: int) -> tuple[str, str]:
    if video_id == "operator-cms-from-truth-tables":
        bodies = [
            ("One rule · four cases", f'''<div class="switches"><div class="switch amber">X</div><div class="switch cyan">Y</div></div>
             {matrix("····",2,2,row_labels=["X","¬X"],column_labels=["Y","¬Y"],cell_labels=["11","10","01","00"])}'''),
            ("Build AND from its cases", f'''<div class="case-stack"><p><b>1 ∧ 1 = 1</b><span>both true</span></p><p>1 ∧ 0 = 0</p><p>0 ∧ 1 = 0</p><p>0 ∧ 0 = 0</p></div><div class="and-build">{matrix("1000",2,2,row_labels=["X","¬X"],column_labels=["Y","¬Y"],cell_labels=["11","10","01","00"],active={0})}<strong data-at=".74">AND = |1⟩⟨1|</strong></div>'''),
            ("Four one-entry basis dyads", basis_dyads_html()),
            ("Four choices · sixteen complete rules", f'''<div class="table-count">2 × 2 × 2 × 2 = <strong>2⁴ = 16</strong></div>{operator_table_html()}'''),
            ("Patterns encode complete behavior", f'''<div class="behavior-gallery">{mini_matrix('0000','false')}{mini_matrix('1110','OR',True)}{mini_matrix('1001','equivalence')}{mini_matrix('1111','true')}</div><div class="implication-pair"><div><b>X → Y</b>{mini_matrix('1011','zero at 10',True)}</div><span>swap operands ↦ zero moves</span><div><b>Y → X</b>{mini_matrix('1101','zero at 01',True)}</div></div>'''),
            ("Read before naming", f'''<div class="retrieval"><div class="prompt">true when the inputs <strong>disagree</strong></div>{matrix("0110",2,2,row_labels=["X","¬X"],column_labels=["Y","¬Y"],active={1,2})}<div class="answer" data-at=".68">XOR · exclusive-or<small>|1⟩⟨0| ⊕ |0⟩⟨1|</small></div></div>'''),
            ("The unit of representation", f'''<div class="summary-flow"><div>4 ordered input cases</div><span>→</span><div>1 complete two-input rule</div><span>→</span><div>1 operator CM</div></div><div class="language-check"><b>16 functions</b><span>not 16 cases of one function</span></div>'''),
        ]
    elif video_id == "logical-matrices-to-higher-dimensional-cms":
        expr_cells = ["X∧Y", "X∧¬Y", "¬X∧Y", "¬X∧¬Y"]
        equivalence = ["X↔Y", "X⊕Y", "X⊕Y", "X↔Y"]
        bodies = [
            ("An outer product creates a base LM", f'''<div class="outer-product-scene"><div class="vector-pair"><span>|X⟩ = [X, ¬X]ᵀ</span><span>⟨Y| = [Y, ¬Y]</span><strong>|X⟩ ⊗ ⟨Y| = |X⟩⟨Y| = M<sub>XY</sub></strong></div><div class="expression-grid compact-expressions">{''.join(f'<div data-at="{.1+i*.12:.2f}">{x}</div>' for i,x in enumerate(expr_cells))}</div><div class="badge">LM · expression-valued</div></div>'''),
            ("Positive valuation produces bits", f'''<div class="valuation"><div class="expression-grid small">{''.join(f'<div>{x}</div>' for x in equivalence)}</div><div class="vt">V<sub>T</sub> →</div>{matrix("1001",2,2,row_labels=["X","¬X"],column_labels=["Y","¬Y"],active={0,3})}</div><div class="rail">LM expressions <span>→ V<sub>T</sub> →</span> CM bits</div>'''),
            ("Tensor two smaller logical matrices", '''<div class="tensor-build"><div class="tensor-inputs"><span>|W⟩⟨X|<small>2×2 LM</small></span><b>⊗</b><span>|Y⟩⟨Z|<small>2×2 LM</small></span></div><div class="tensor-equivalence">(|W⟩⟨X|) ⊗ (|Y⟩⟨Z|)<strong>=</strong>(|W⟩ ⊗ |Y⟩)(⟨X| ⊗ ⟨Z|)</div><div class="size-rail"><span>2×2</span><b>⊗</b><span>2×2</span><strong>→ 4×4 LM</strong></div></div>'''),
            ("Four components on each side", '''<div class="compound-states"><div class="measurement">⟨Y|⟨W| <strong>M</strong> |X⟩|Z⟩</div><div class="state-expansions"><span><b>rows · ⟨Y,W|</b>[YW, Y¬W, ¬YW, ¬Y¬W]</span><span><b>columns · |X,Z⟩</b>[XZ, X¬Z, ¬XZ, ¬X¬Z]ᵀ</span></div><div class="worked-cross">row Y¬W × column ¬XZ <strong>→ Y¬W¬XZ</strong></div><small>4 components per side · 4 variables across both sides</small></div>'''),
            ("One compound four-variable example", f'''<div class="modules"><div><small>left</small>W ⊕ X</div><span>→</span><div><small>right</small>¬Y ∧ Z</div><strong>implication</strong></div>{matrix("1100111000111011",4,4,row_labels=["YW 11","YW 10","YW 01","YW 00"],column_labels=["XZ 11","XZ 10","XZ 01","XZ 00"],active={2,3,7,8,9,13})}'''),
            ("Entry type decides the name", '''<div class="retrieval split"><div><b>before V<sub>T</sub></b><span class="formula">¬X ∧ Y</span><strong>LM entry</strong></div><div data-at=".7"><b>after V<sub>T</sub></b><span class="formula">0 or 1</span><strong>CM entry</strong></div></div>'''),
            ("Paper construction and repository layout", '''<div class="two-rails"><div><b>paper construction</b><span>2×2 → 4×4 → 8×8</span><small>outer products · tensor construction · V<sub>T</sub></small></div><div><b>repository layout</b><span>4×4 · 2×8 · 8×2</span><small>ordered row/column materialization</small></div></div><div class="rail">outer product → tensor LM → V<sub>T</sub> → CM</div>'''),
        ]
    else:
        grid = matrix("0111011101111000",4,4,row_labels=["AB 00","AB 01","AB 10","AB 11"],column_labels=["CD 00","CD 01","CD 10","CD 11"],active={11})
        bodies = [
            ("Give every output a coordinate", '''<div class="function-card"><b>F(A,B,C,D)</b><span>=(A ∧ B) ⊕ (C ∨ D)</span></div><div class="tracked">1011 <span>↦</span> 1</div>'''),
            ("The ordered layout contract", '''<div class="tracked">1011 ↦ 1</div><div class="split-bits"><div><b>R=[A,B]</b><span>10₂ → row 2</span></div><div><b>C=[C,D]</b><span>11₂ → column 3</span></div></div><div class="convention">MSB-first</div>'''),
            ("Materialize the 4×4 layout", f'''<div class="function-card compact">F=(A ∧ B) ⊕ (C ∨ D)</div>{grid}<div class="coordinate">M[2,3] = 1</div>'''),
            ("A coordinate needs its key", '''<div class="coordinate huge">(2,3)</div><div class="key-grid"><span data-at=".22">R=[A,B]</span><span data-at=".38">C=[C,D]</span><span data-at=".54">MSB-first</span><strong data-at=".72">10 · 11 ↦ 1011</strong></div>'''),
            ("Map one yourself", f'''<div class="tracked">1110 ↦ ?</div><div class="quiz"><span>row?</span><span>column?</span><span>output?</span></div><div class="answer" data-at=".7">row 3 · column 2 · M[3,2]=0</div>'''),
            ("Repartition; preserve the mapping", '''<div class="tracked fixed">1011 ↦ 1</div><div class="layouts"><div><b>AB / CD</b><span>4×4</span><strong>(2,3)</strong></div><div><b>A / BCD</b><span>2×8</span><strong>(1,3)</strong></div><div><b>ABC / D</b><span>8×2</span><strong>(5,1)</strong></div></div>'''),
            ("Dense means every requested cell", '''<div class="dense-shapes"><div class="shape s44">4×4</div><div class="shape s28">2×8</div><div class="shape s82">8×2</div></div><div class="rail">same 16 assignment-output pairs · different coordinates</div>'''),
        ]
    return bodies[index]


def css(sans_b64: str, mono_b64: str, width: int, height: int) -> str:
    scale = width / 1920
    return f'''
@font-face{{font-family:CMDejaVu;src:url(data:font/ttf;base64,{sans_b64}) format("truetype");font-display:block}}
@font-face{{font-family:CMDejaVuMono;src:url(data:font/ttf;base64,{mono_b64}) format("truetype");font-display:block}}
*{{box-sizing:border-box}}html,body{{width:100%;height:100%;margin:0;overflow:hidden;background:#081018;color:#eef5f7;font-family:CMDejaVu,sans-serif}}
body{{--amber:#f1b65c;--cyan:#57d4e8;--violet:#a990ff;--muted:#9fb0bc;--surface:#111d27;--rule:#2b3c48;--s:{scale};}}
.stage{{width:{width}px;height:{height}px;padding:calc(70px*var(--s)) calc(84px*var(--s)) calc(94px*var(--s));background:radial-gradient(circle at 78% 10%,#142b38 0,transparent 38%),#081018;position:relative}}
header small{{font:700 calc(18px*var(--s))/1 CMDejaVuMono;color:var(--amber);letter-spacing:.12em}}header h1{{margin:calc(12px*var(--s)) 0 0;font-size:calc(52px*var(--s));line-height:1.08;max-width:calc(1500px*var(--s))}}
.content{{height:calc(720px*var(--s));display:flex;align-items:center;justify-content:center;gap:calc(46px*var(--s));margin-top:calc(36px*var(--s))}}
footer{{position:absolute;left:calc(84px*var(--s));right:calc(84px*var(--s));bottom:calc(34px*var(--s));display:flex;justify-content:space-between;color:var(--muted);font:500 calc(16px*var(--s))/1.3 CMDejaVuMono}}
[data-at]{{opacity:0;transform:translateY(calc(18px*var(--s)))}}.matrix-wrap{{display:grid;grid-template-columns:calc(120px*var(--s)) calc(16px*var(--s)) minmax(calc(320px*var(--s)),calc(580px*var(--s))) calc(16px*var(--s));grid-template-rows:calc(62px*var(--s)) minmax(calc(320px*var(--s)),calc(580px*var(--s)));align-items:stretch}}
.col-labels{{grid-column:3;display:grid;grid-template-columns:repeat(var(--cols),1fr);place-items:center;color:var(--cyan);font:700 calc(22px*var(--s))/1 CMDejaVuMono}}.row-labels{{grid-row:2;display:grid;grid-template-rows:repeat(var(--rows),1fr);place-items:center;color:var(--amber);font:700 calc(22px*var(--s))/1 CMDejaVuMono}}
.grid{{grid-column:3;grid-row:2;display:grid;grid-template-columns:repeat(var(--cols),1fr);gap:calc(8px*var(--s));padding:calc(12px*var(--s))}}.cell{{min-width:0;min-height:0;border:2px solid var(--rule);background:#0e1821;display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:calc(8px*var(--s))}}.cell span{{font:700 calc(36px*var(--s))/1 CMDejaVuMono}}.cell small{{margin-top:calc(7px*var(--s));color:var(--muted);font:600 calc(15px*var(--s))/1 CMDejaVuMono}}.cell.on{{border-color:#2c8291;color:var(--cyan)}}.cell.active{{outline:calc(5px*var(--s)) solid var(--amber);outline-offset:calc(2px*var(--s))}}
.bracket{{grid-row:2;border-top:calc(5px*var(--s)) solid #dbe8ec;border-bottom:calc(5px*var(--s)) solid #dbe8ec}}.bracket.left{{grid-column:2;border-left:calc(5px*var(--s)) solid #dbe8ec}}.bracket.right{{grid-column:4;border-right:calc(5px*var(--s)) solid #dbe8ec}}
.switches{{display:flex;gap:calc(25px*var(--s))}}.switch{{width:calc(170px*var(--s));height:calc(170px*var(--s));display:grid;place-items:center;border:3px solid;border-radius:50%;font-size:calc(66px*var(--s));font-weight:700}}.amber{{color:var(--amber)}}.cyan{{color:var(--cyan)}}
.case-stack{{display:grid;gap:calc(18px*var(--s));width:calc(420px*var(--s))}}.case-stack p{{margin:0;padding:calc(19px*var(--s));border-left:5px solid var(--amber);background:var(--surface);font:600 calc(28px*var(--s))/1.2 CMDejaVuMono}}.case-stack p span{{display:block;color:var(--muted);font-size:.62em;margin-top:.5em}}
.equation{{display:flex;align-items:center;gap:calc(18px*var(--s));font:700 calc(48px*var(--s))/1 CMDejaVuMono}}.equation strong{{color:var(--amber);font-size:1.45em}}.hero-math{{position:absolute;top:calc(230px*var(--s))}}
.gallery{{display:grid;grid-template-columns:repeat(8,1fr);gap:calc(18px*var(--s));width:100%;margin-top:calc(180px*var(--s))}}.mini{{display:flex;flex-direction:column;align-items:center;gap:calc(8px*var(--s))}}.mini-grid{{display:grid;grid-template-columns:repeat(2,calc(28px*var(--s)));gap:calc(3px*var(--s));padding:calc(7px*var(--s));border-left:3px solid #dbe8ec;border-right:3px solid #dbe8ec}}.mini i{{height:calc(28px*var(--s));display:grid;place-items:center;font:700 calc(17px*var(--s))/1 CMDejaVuMono;font-style:normal}}.mini i.one{{color:var(--cyan)}}.mini i.zero{{color:#5d6b75}}.mini>span{{color:var(--muted);font-size:calc(15px*var(--s))}}.mini.highlight .mini-grid{{box-shadow:0 0 0 3px var(--amber)}}
.and-build{{display:flex;flex-direction:column;align-items:center;gap:calc(14px*var(--s))}}.and-build strong{{color:var(--violet);font:700 calc(27px*var(--s))/1 CMDejaVu}}
.state-vectors{{position:absolute;top:calc(205px*var(--s));display:flex;align-items:center;gap:calc(42px*var(--s));font:700 calc(27px*var(--s))/1 CMDejaVu}}.state-vectors span{{padding:calc(14px*var(--s)) calc(22px*var(--s));background:var(--surface);border-bottom:3px solid var(--cyan)}}.state-vectors strong{{color:var(--amber);font-size:calc(30px*var(--s))}}
.dyad-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:calc(30px*var(--s));width:100%;margin-top:calc(75px*var(--s))}}.dyad-card{{padding:calc(24px*var(--s));background:var(--surface);border-top:5px solid var(--violet);display:flex;flex-direction:column;align-items:center;gap:calc(15px*var(--s))}}.dyad-card b{{font:700 calc(26px*var(--s))/1 CMDejaVu}}.dyad-card .mini-grid{{grid-template-columns:repeat(2,calc(48px*var(--s)))}}.dyad-card .mini i{{height:calc(48px*var(--s));font-size:calc(25px*var(--s))}}.basis-caption{{position:absolute;bottom:calc(120px*var(--s));color:var(--muted);font:700 calc(20px*var(--s))/1 CMDejaVuMono}}
.table-count{{position:absolute;top:calc(185px*var(--s));font:700 calc(28px*var(--s))/1 CMDejaVuMono}}.table-count strong{{color:var(--amber);font-size:1.2em}}.operator-table{{display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:repeat(4,1fr);gap:calc(10px*var(--s));width:100%;height:calc(650px*var(--s));margin-top:calc(40px*var(--s))}}.operator-tile{{min-width:0;padding:calc(8px*var(--s)) calc(12px*var(--s));background:var(--surface);border:2px solid var(--rule);display:grid;grid-template-columns:calc(105px*var(--s)) 1fr;grid-template-rows:auto 1fr;align-items:center;column-gap:calc(12px*var(--s))}}.operator-tile.highlight{{border-color:var(--amber);box-shadow:inset 0 0 0 1px var(--amber)}}.operator-tile>b{{grid-column:1/-1;text-align:center;font:700 calc(19px*var(--s))/1.05 CMDejaVu;color:#eef5f7}}.operator-matrix{{display:grid;grid-template-columns:repeat(2,calc(30px*var(--s)));gap:calc(2px*var(--s));padding:calc(5px*var(--s));border-left:3px solid #dbe8ec;border-right:3px solid #dbe8ec;justify-self:center}}.operator-matrix i{{height:calc(25px*var(--s));display:grid;place-items:center;font:700 calc(18px*var(--s))/1 CMDejaVuMono;font-style:normal}}.operator-matrix i.one{{color:var(--cyan)}}.operator-matrix i.zero{{color:#687782}}.operator-tile>span{{min-width:0;text-align:center;color:#d9ceff;font:600 calc(15px*var(--s))/1.22 CMDejaVu;overflow-wrap:anywhere}}
.behavior-gallery{{display:grid;grid-template-columns:repeat(4,1fr);gap:calc(45px*var(--s));width:100%;align-self:flex-start;margin-top:calc(40px*var(--s))}}.behavior-gallery .mini-grid{{grid-template-columns:repeat(2,calc(48px*var(--s)))}}.behavior-gallery .mini i{{height:calc(48px*var(--s));font-size:calc(25px*var(--s))}}.behavior-gallery .mini>span{{font-size:calc(20px*var(--s));color:#eef5f7}}.implication-pair{{position:absolute;bottom:calc(105px*var(--s));display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:calc(38px*var(--s));width:calc(1120px*var(--s))}}.implication-pair>div{{display:flex;align-items:center;justify-content:center;gap:calc(18px*var(--s));padding:calc(14px*var(--s));background:var(--surface)}}.implication-pair b{{font:700 calc(25px*var(--s))/1 CMDejaVu}}.implication-pair>span{{color:var(--muted);font:700 calc(18px*var(--s))/1.2 CMDejaVuMono;text-align:center}}.answer small{{display:block;margin-top:calc(12px*var(--s));color:#d9ceff;font:600 calc(19px*var(--s))/1 CMDejaVu}}
.named-gallery{{display:grid;grid-template-columns:repeat(6,1fr);gap:calc(35px*var(--s));width:100%}}.named-gallery .mini-grid{{grid-template-columns:repeat(2,calc(54px*var(--s)))}}.named-gallery .mini i{{height:calc(54px*var(--s));font-size:calc(27px*var(--s))}}.named-gallery .mini>span{{font-size:calc(20px*var(--s));color:#e5edf0}}.implication{{position:absolute;bottom:calc(130px*var(--s));display:flex;align-items:center;gap:calc(25px*var(--s));font:700 calc(25px*var(--s))/1 CMDejaVuMono}}.swap{{color:var(--muted)}}
.retrieval{{display:flex;align-items:center;gap:calc(70px*var(--s));width:100%;justify-content:center}}.prompt{{max-width:calc(420px*var(--s));font-size:calc(36px*var(--s));line-height:1.25}}.prompt strong{{color:var(--cyan)}}.answer{{padding:calc(24px*var(--s));border:3px solid var(--amber);color:var(--amber);font-size:calc(30px*var(--s));font-weight:700}}
.summary-flow,.construction{{display:flex;align-items:stretch;gap:calc(20px*var(--s));width:100%}}.summary-flow div,.construction div{{flex:1;background:var(--surface);border-top:5px solid var(--cyan);padding:calc(32px*var(--s));font-size:calc(26px*var(--s));font-weight:700;text-align:center}}.summary-flow span,.construction i{{align-self:center;color:var(--amber);font-size:calc(40px*var(--s));font-style:normal}}.language-check{{position:absolute;bottom:calc(150px*var(--s));display:flex;gap:calc(25px*var(--s));align-items:center}}.language-check b{{color:var(--amber);font-size:calc(30px*var(--s))}}.language-check span{{color:var(--muted)}}
.expression-grid{{display:grid;grid-template-columns:repeat(2,calc(380px*var(--s)));gap:calc(12px*var(--s));padding:calc(20px*var(--s));border-left:5px solid #dbe8ec;border-right:5px solid #dbe8ec}}.expression-grid div{{padding:calc(42px*var(--s));background:var(--surface);color:#e9e1ff;text-align:center;font:700 calc(38px*var(--s))/1 CMDejaVu}}.expression-grid.small{{grid-template-columns:repeat(2,calc(260px*var(--s)))}}.expression-grid.small div{{padding:calc(28px*var(--s));font-size:calc(30px*var(--s))}}.badge,.convention{{padding:calc(18px*var(--s));border:2px solid var(--violet);color:var(--violet);font:700 calc(22px*var(--s))/1 CMDejaVuMono}}
.outer-product-scene{{display:grid;grid-template-columns:auto auto;align-items:center;gap:calc(35px*var(--s));width:100%}}.vector-pair{{display:flex;flex-direction:column;gap:calc(24px*var(--s));padding:calc(30px*var(--s));background:var(--surface);border-top:5px solid var(--cyan);font:700 calc(27px*var(--s))/1.15 CMDejaVu}}.vector-pair strong{{color:var(--amber);font-size:calc(29px*var(--s));margin-top:calc(10px*var(--s))}}.compact-expressions{{grid-template-columns:repeat(2,calc(285px*var(--s)))}}.compact-expressions div{{padding:calc(32px*var(--s));font-size:calc(31px*var(--s))}}.outer-product-scene .badge{{grid-column:1/-1;justify-self:center}}
.tensor-build{{display:flex;flex-direction:column;align-items:center;gap:calc(34px*var(--s));width:100%}}.tensor-inputs{{display:flex;align-items:center;gap:calc(30px*var(--s));font:700 calc(38px*var(--s))/1 CMDejaVu}}.tensor-inputs span{{padding:calc(24px*var(--s)) calc(45px*var(--s));background:var(--surface);border-top:5px solid var(--violet);text-align:center}}.tensor-inputs small{{display:block;color:var(--muted);font:600 calc(16px*var(--s))/1 CMDejaVuMono;margin-top:calc(14px*var(--s))}}.tensor-inputs>b{{color:var(--amber);font-size:calc(48px*var(--s))}}.tensor-equivalence{{padding:calc(26px*var(--s));border:2px solid var(--rule);font:700 calc(31px*var(--s))/1.2 CMDejaVu}}.tensor-equivalence strong{{color:var(--amber);padding:0 calc(22px*var(--s))}}.size-rail{{display:flex;align-items:center;gap:calc(22px*var(--s));font:700 calc(25px*var(--s))/1 CMDejaVuMono}}.size-rail strong{{color:var(--cyan)}}
.compound-states{{display:flex;flex-direction:column;align-items:center;gap:calc(26px*var(--s));width:100%}}.measurement{{font:700 calc(48px*var(--s))/1 CMDejaVu;color:#e9e1ff}}.measurement strong{{color:var(--amber)}}.state-expansions{{display:grid;grid-template-columns:1fr 1fr;gap:calc(28px*var(--s));width:100%}}.state-expansions span{{display:flex;flex-direction:column;gap:calc(14px*var(--s));padding:calc(25px*var(--s));background:var(--surface);font:700 calc(25px*var(--s))/1.2 CMDejaVu}}.state-expansions b{{color:var(--cyan);font-size:calc(18px*var(--s));font-family:CMDejaVuMono}}.state-expansions span:first-child b{{color:var(--amber)}}.worked-cross{{padding:calc(20px*var(--s)) calc(35px*var(--s));border:2px solid var(--violet);font:700 calc(25px*var(--s))/1 CMDejaVu}}.worked-cross strong{{color:var(--cyan);margin-left:calc(20px*var(--s))}}.compound-states>small{{color:var(--muted);font:700 calc(18px*var(--s))/1 CMDejaVuMono}}
.valuation{{display:flex;align-items:center;gap:calc(36px*var(--s))}}.valuation .matrix-wrap{{transform:scale(.78)}}.vt{{color:var(--amber);font:700 calc(40px*var(--s))/1 CMDejaVu}}.rail{{position:absolute;bottom:calc(125px*var(--s));padding:calc(18px*var(--s)) calc(30px*var(--s));border-left:5px solid var(--cyan);background:var(--surface);font:700 calc(25px*var(--s))/1.2 CMDejaVuMono}}.rail span{{color:var(--amber)}}
.construction div{{display:flex;flex-direction:column;gap:calc(15px*var(--s));font-size:calc(24px*var(--s))}}.construction div span{{color:var(--muted);font-size:.72em;font-weight:500}}.construction div:nth-of-type(2){{border-color:var(--violet)}}.construction div:nth-of-type(3){{border-color:var(--amber)}}
.modules{{display:grid;grid-template-columns:1fr auto 1fr;gap:calc(15px*var(--s));align-items:center;width:calc(600px*var(--s))}}.modules div{{background:var(--surface);border-top:5px solid var(--violet);padding:calc(26px*var(--s));font:700 calc(34px*var(--s))/1.2 CMDejaVu;text-align:center}}.modules small{{display:block;color:var(--muted);font:600 calc(16px*var(--s))/1 CMDejaVuMono;margin-bottom:calc(12px*var(--s))}}.modules>span{{font-size:calc(42px*var(--s));color:var(--amber)}}.modules strong{{grid-column:1/-1;text-align:center;color:var(--amber);font:700 calc(24px*var(--s))/1 CMDejaVuMono}}.modules+.matrix-wrap{{transform:scale(.78)}}
.split>div{{min-width:calc(520px*var(--s));min-height:calc(340px*var(--s));padding:calc(42px*var(--s));background:var(--surface);border-top:5px solid var(--violet);display:flex;flex-direction:column;gap:calc(34px*var(--s));align-items:center}}.split b{{color:var(--muted);font:700 calc(20px*var(--s))/1 CMDejaVuMono}}.formula{{font:700 calc(50px*var(--s))/1 CMDejaVu}}.split strong{{color:var(--cyan);font-size:calc(30px*var(--s))}}
.two-rails{{display:grid;grid-template-columns:1fr 1fr;gap:calc(45px*var(--s));width:100%}}.two-rails>div{{background:var(--surface);padding:calc(42px*var(--s));border-top:6px solid var(--violet);display:flex;flex-direction:column;gap:calc(30px*var(--s))}}.two-rails>div+div{{border-color:var(--cyan)}}.two-rails b{{font-size:calc(27px*var(--s))}}.two-rails span{{font:700 calc(40px*var(--s))/1 CMDejaVuMono}}.two-rails small{{color:var(--muted);font-size:calc(20px*var(--s))}}
.function-card{{padding:calc(50px*var(--s));background:var(--surface);border-top:6px solid var(--amber);display:flex;flex-direction:column;gap:calc(20px*var(--s));font:700 calc(43px*var(--s))/1.2 CMDejaVu}}.function-card span{{color:var(--cyan)}}.function-card.compact{{font-size:calc(28px*var(--s));padding:calc(30px*var(--s))}}.tracked{{padding:calc(40px*var(--s));border:4px solid var(--cyan);font:700 calc(56px*var(--s))/1 CMDejaVuMono}}.tracked span{{color:var(--amber)}}
.split-bits{{display:grid;grid-template-columns:1fr 1fr;gap:calc(35px*var(--s));width:calc(900px*var(--s))}}.split-bits>div{{padding:calc(35px*var(--s));background:var(--surface);border-top:5px solid var(--amber);display:flex;flex-direction:column;gap:calc(18px*var(--s));font-size:calc(27px*var(--s))}}.split-bits>div+div{{border-color:var(--cyan)}}.split-bits span{{font-family:CMDejaVuMono;color:var(--muted)}}.coordinate{{color:var(--amber);font:700 calc(32px*var(--s))/1 CMDejaVuMono}}.coordinate.huge{{font-size:calc(90px*var(--s))}}
.key-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:calc(24px*var(--s));width:calc(1050px*var(--s))}}.key-grid span,.key-grid strong{{padding:calc(28px*var(--s));background:var(--surface);text-align:center;font:700 calc(25px*var(--s))/1 CMDejaVuMono}}.key-grid strong{{grid-column:1/-1;color:var(--cyan);font-size:calc(34px*var(--s))}}.quiz{{display:flex;gap:calc(25px*var(--s))}}.quiz span{{padding:calc(30px*var(--s)) calc(60px*var(--s));background:var(--surface);color:var(--muted);font-size:calc(28px*var(--s))}}
.layouts{{display:grid;grid-template-columns:repeat(3,1fr);gap:calc(32px*var(--s));width:100%}}.layouts>div{{padding:calc(38px*var(--s));background:var(--surface);border-top:6px solid var(--amber);display:flex;flex-direction:column;gap:calc(20px*var(--s));text-align:center}}.layouts>div:nth-child(2){{border-color:var(--cyan)}}.layouts>div:nth-child(3){{border-color:var(--violet)}}.layouts b{{font:700 calc(27px*var(--s))/1 CMDejaVuMono}}.layouts span{{font-size:calc(46px*var(--s))}}.layouts strong{{color:var(--cyan);font:700 calc(32px*var(--s))/1 CMDejaVuMono}}
.dense-shapes{{display:flex;align-items:center;gap:calc(50px*var(--s))}}.shape{{display:grid;place-items:center;border:4px solid var(--cyan);background:repeating-linear-gradient(90deg,transparent 0 22%,#263b47 23% 25%),repeating-linear-gradient(0deg,transparent 0 22%,#263b47 23% 25%);font:700 calc(36px*var(--s))/1 CMDejaVuMono}}.s44{{width:calc(320px*var(--s));height:calc(320px*var(--s))}}.s28{{width:calc(500px*var(--s));height:calc(160px*var(--s))}}.s82{{width:calc(160px*var(--s));height:calc(500px*var(--s))}}
'''


def html_scene(video_id: str, scene: dict[str, Any], index: int, sans_b64: str, mono_b64: str,
               width: int, height: int) -> str:
    title, body = scene_body(video_id, index)
    safe_title = html.escape(title)
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{css(sans_b64,mono_b64,width,height)}</style></head>
<body><div class="stage"><header><small>CM FOUNDATIONS · {index+1:02d}</small><h1>{safe_title}</h1></header>
<main class="content">{body}</main><footer><span>{html.escape(video_id)}</span><span>symbol-safe preview · DejaVu embedded</span></footer></div>
<script>window.__seek=function(p){{document.querySelectorAll('[data-at]').forEach(function(e){{var a=parseFloat(e.dataset.at||0),t=Math.max(0,Math.min(1,(p-a)/.12));t=t*t*(3-2*t);e.style.opacity=t;e.style.transform='translateY('+((1-t)*18)+'px)'}})}};window.__seek(0);</script></body></html>'''


def symbol_stress_html(sans_b64: str, mono_b64: str, width: int, height: int) -> str:
    cards = "".join(
        f'<div data-at="{0.04 + i * 0.045:.3f}"><strong>{html.escape(glyph)}</strong><span>{html.escape(name.replace("_", " "))}</span><small>U+{ord(glyph):04X}</small></div>'
        for i, (name, glyph) in enumerate(SYMBOLS.items())
    )
    specimen = f'''<div class="symbol-cards">{cards}</div>
    <div class="formula-lines">
      <span>¬X ∧ Y</span><span>X ∨ Y</span><span>X ⊕ Y</span><span>X → Y</span><span>X ↔ Y</span>
      <span>|1⟩ ⊗ ⟨0| = |1⟩⟨0|</span><span>|X⟩⟨Y| = M<sub>XY</sub></span><span>1011 ↦ M[2,3]</span>
      <span>2 × 2 × 2 × 2 = 2⁴ = 16</span><span>V<sub>T</sub>(M<sub>XY</sub>)</span>
    </div>
    {matrix("1001",2,2,row_labels=["X","¬X"],column_labels=["Y","¬Y"])}'''
    extra = '''
.symbol-cards{display:grid;grid-template-columns:repeat(6,1fr);gap:calc(14px*var(--s));width:100%;align-self:flex-start}.symbol-cards div{padding:calc(15px*var(--s));background:var(--surface);border-top:4px solid var(--violet);display:flex;align-items:center;gap:calc(10px*var(--s))}.symbol-cards strong{font-size:calc(34px*var(--s));color:var(--cyan)}.symbol-cards span{font-size:calc(15px*var(--s))}.symbol-cards small{margin-left:auto;color:var(--muted);font:600 calc(11px*var(--s))/1 CMDejaVuMono}.formula-lines{position:absolute;left:calc(90px*var(--s));bottom:calc(155px*var(--s));display:grid;grid-template-columns:repeat(4,auto);gap:calc(16px*var(--s)) calc(28px*var(--s));font:700 calc(23px*var(--s))/1 CMDejaVu}.formula-lines span{padding:calc(10px*var(--s));border-bottom:2px solid var(--amber)}.formula-lines+.matrix-wrap{position:absolute;right:calc(90px*var(--s));bottom:calc(110px*var(--s));transform:scale(.45);transform-origin:bottom right}
'''
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{css(sans_b64,mono_b64,width,height)}{extra}</style></head>
<body><div class="stage"><header><small>CM FOUNDATIONS · PREFLIGHT</small><h1>Mathematical symbol specimen</h1></header><main class="content">{specimen}</main>
<footer><span>glyph coverage + rendered specimen</span><span>matrix brackets are drawn geometry</span></footer></div>
<script>window.__seek=function(p){{document.querySelectorAll('[data-at]').forEach(function(e){{var a=parseFloat(e.dataset.at||0),t=Math.max(0,Math.min(1,(p-a)/.12));t=t*t*(3-2*t);e.style.opacity=t;e.style.transform='translateY('+((1-t)*18)+'px)'}})}};window.__seek(0);</script></body></html>'''


def production_contracts() -> dict[str, Any]:
    font = font_contract()
    artifacts = []
    episode_records = []
    for video_id, script_path in SCRIPT_PATHS.items():
        scenes = parse_script(script_path)
        expected_count = 7
        if len(scenes) != expected_count:
            raise ProductionError(f"unexpected scene count for {video_id}: {len(scenes)}")
        record = {
            "schema_version": "1.0",
            "status": "preview_ready_final_render_not_authorized",
            "video_id": video_id,
            "script": {"path": script_path.relative_to(ROOT).as_posix(), "sha256": sha256(script_path)},
            "format": {"width": 1920, "height": 1080, "fps": FPS, "video_codec": "h264", "pixel_format": "yuv420p"},
            "duration_s": scenes[-1]["end_s"],
            "scenes": scenes,
            "math_typography_contract": "docs/video_factory/deep_series/foundational_cm_production_v2/MATH_TYPOGRAPHY_CONTRACT_V2.json",
            "narration": {"status": "offline_neural_audition_pending", "scratch_tts_allowed": True, "final_mechanical_tts_forbidden": True},
            "remote_or_paid_authorized": False,
        }
        narration = {
            "schema_version": "1.0",
            "status": "offline_neural_audition_pending",
            "video_id": video_id,
            "sample_rate_hz": 48000,
            "channels": 1,
            "cues": [
                {
                    "cue_id": f"n{index:02d}",
                    "scene_id": scene["scene_id"],
                    "start_s": scene["start_s"],
                    "end_s": scene["end_s"],
                    "window_s": scene["duration_s"],
                    "text": scene["voiceover"],
                    "segments": scene["voice_segments"],
                }
                for index, scene in enumerate(scenes, 1)
            ],
            "pronunciation_policy": {
                "CM": "C M",
                "LM": "L M",
                "XOR": "exclusive-or",
                "V_T": "V sub T",
                "M[2,3]": "M of two comma three",
                "2^4": "two to the fourth power",
                "MSB": "most significant bit",
            },
            "quality_gate": "A final offline neural voice must sound conversational and pass human audition. Windows SAPI may be used only for timing and must not be released as final narration.",
            "candidate_provider": "local_kokoro_onnx",
            "remote_or_paid_authorized": False,
        }
        narration_path = PACKAGE / "episodes" / video_id / "NARRATION_CONTRACT_V2.json"
        write_json(narration_path, narration)
        record["narration_contract"] = {
            "path": narration_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(narration_path),
        }
        record["content_hash"] = hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        out = PACKAGE / "episodes" / video_id / "PRODUCTION_CONTRACT_V2.json"
        write_json(out, record)
        episode_records.append(record)
        artifacts.extend([out, narration_path])
    write_json(PACKAGE / "MATH_TYPOGRAPHY_CONTRACT_V2.json", font)
    artifacts.append(PACKAGE / "MATH_TYPOGRAPHY_CONTRACT_V2.json")
    manifest = {
        "schema_version": "1.0",
        "status": "preview_ready_final_render_not_authorized",
        "revision_id": "foundational-cm-production-v2",
        "episodes": [{"video_id": x["video_id"], "content_hash": x["content_hash"], "duration_s": x["duration_s"]} for x in episode_records],
        "symbol_coverage_passed": True,
        "total_duration_s": sum(x["duration_s"] for x in episode_records),
        "remote_or_paid_work_performed": False,
        "artifacts": [],
    }
    for path in artifacts:
        manifest["artifacts"].append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size})
    manifest["package_identity_sha256"] = hashlib.sha256(json.dumps(manifest["artifacts"], sort_keys=True).encode("utf-8")).hexdigest()
    write_json(PACKAGE / "PRODUCTION_MANIFEST_V2.json", manifest)
    return manifest


def render_previews(*, width: int = 960, height: int = 540, workers: int = 2) -> dict[str, Any]:
    production_contracts()
    if not FRAME_DRIVER.is_file():
        raise ProductionError(f"POP frame driver not found: {FRAME_DRIVER}")
    if not (POP_ROOT / "node_modules" / "playwright").is_dir():
        raise ProductionError("POP Playwright installation not found")
    node = shutil.which("node")
    if not node:
        raise ProductionError("node is not on PATH")
    sans, mono = locate_fonts()
    sans_b64, mono_b64 = b64_font(sans), b64_font(mono)
    episode_results = []
    from PIL import Image, ImageDraw
    import imageio_ffmpeg

    symbol_root = PACKAGE / "symbol_preflight"
    symbol_frames = symbol_root / "frames"
    symbol_html = symbol_stress_html(sans_b64, mono_b64, width, height)
    symbol_manifest = {
        "width": width, "height": height, "fps": FPS,
        "scenes": [
            {"id": "symbols-a", "kind": "foundational_cm", "startIndex": 0, "progress": [0.985], "html": symbol_html},
            {"id": "symbols-b", "kind": "foundational_cm", "startIndex": 1, "progress": [0.985], "html": symbol_html},
        ],
    }
    symbol_manifest_path = symbol_root / "symbol_stress_manifest.json"
    write_json(symbol_manifest_path, symbol_manifest)
    symbol_frames.mkdir(parents=True, exist_ok=True)
    for old in symbol_frames.glob("f*.png"):
        old.unlink()
    symbol_run = subprocess.run(
        [node, str(FRAME_DRIVER), str(symbol_manifest_path), str(symbol_frames), "1"],
        cwd=str(POP_ROOT), text=True, capture_output=True, encoding="utf-8", errors="replace",
    )
    if symbol_run.returncode:
        raise ProductionError(f"symbol-stress render failed: {symbol_run.stderr[-1500:]}")
    symbol_a, symbol_b = symbol_frames / "f000000.png", symbol_frames / "f000001.png"
    if not symbol_a.is_file() or not symbol_b.is_file() or sha256(symbol_a) != sha256(symbol_b):
        raise ProductionError("repeated symbol-stress frames were not deterministic")

    for video_id, script_path in SCRIPT_PATHS.items():
        scenes = parse_script(script_path)
        out_root = PACKAGE / "episodes" / video_id / "previews"
        frames_dir = out_root / "settled_frames"
        manifest_scenes = []
        for index, scene in enumerate(scenes):
            manifest_scenes.append({
                "id": scene["scene_id"], "kind": "foundational_cm", "startIndex": index,
                "progress": [0.985],
                "html": html_scene(video_id, scene, index, sans_b64, mono_b64, width, height),
            })
        render_manifest = {"width": width, "height": height, "fps": FPS, "scenes": manifest_scenes}
        manifest_path = out_root / "settled_frame_manifest.json"
        write_json(manifest_path, render_manifest)
        frames_dir.mkdir(parents=True, exist_ok=True)
        for old in frames_dir.glob("f*.png"):
            old.unlink()
        completed = subprocess.run(
            [node, str(FRAME_DRIVER), str(manifest_path), str(frames_dir), str(workers)],
            cwd=str(POP_ROOT), text=True, capture_output=True, encoding="utf-8", errors="replace",
        )
        if completed.returncode:
            raise ProductionError(f"preview render failed for {video_id}: {completed.stderr[-1500:]}")
        frames = sorted(frames_dir.glob("f*.png"))
        if len(frames) != len(scenes):
            raise ProductionError(f"preview frame count mismatch for {video_id}")
        thumb_w, thumb_h = width // 2, height // 2
        cols = 2
        rows = (len(frames) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), "#050a0f")
        draw = ImageDraw.Draw(sheet)
        for i, path in enumerate(frames):
            with Image.open(path) as im:
                im = im.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                x, y = (i % cols) * thumb_w, (i // cols) * thumb_h
                sheet.paste(im, (x, y))
                draw.rectangle((x, y, x + 54, y + 24), fill="#050a0f")
                draw.text((x + 7, y + 5), f"{i+1:02d}", fill="#f1b65c")
        contact = out_root / "CONTACT_SHEET.png"
        sheet.save(contact)

        concat = out_root / "animatic.concat.txt"
        concat_lines = []
        for path in frames:
            escaped = path.resolve().as_posix().replace("'", "'\\''")
            concat_lines.extend([f"file '{escaped}'", "duration 2.5"])
        escaped = frames[-1].resolve().as_posix().replace("'", "'\\''")
        concat_lines.append(f"file '{escaped}'")
        write_text(concat, "\n".join(concat_lines) + "\n")
        animatic = out_root / f"{video_id}.silent-animatic.mp4"
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        encoded = subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat), "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-crf", "20",
            "-movflags", "+faststart", str(animatic),
        ], text=True, capture_output=True)
        if encoded.returncode:
            raise ProductionError(f"animatic encode failed for {video_id}: {encoded.stderr[-1000:]}")
        episode_results.append({
            "video_id": video_id,
            "settled_frames": len(frames),
            "contact_sheet": {"path": contact.relative_to(ROOT).as_posix(), "sha256": sha256(contact)},
            "silent_animatic": {"path": animatic.relative_to(ROOT).as_posix(), "sha256": sha256(animatic)},
        })
    report = {
        "schema_version": "1.0", "status": "passed", "width": width, "height": height,
        "font_embedded": True, "symbol_coverage_passed": True,
        "symbol_specimen": {"path": symbol_a.relative_to(ROOT).as_posix(), "sha256": sha256(symbol_a)},
        "repeat_frame_deterministic": True, "episodes": episode_results,
        "remote_or_paid_work_performed": False,
    }
    write_json(PACKAGE / "PREVIEW_REPORT_V2.json", report)
    return report


def ffmpeg_tools() -> tuple[str, str]:
    encoder = shutil.which("ffmpeg")
    probe = shutil.which("ffprobe")
    if encoder and probe:
        return encoder, probe
    try:
        import imageio_ffmpeg
        encoder = imageio_ffmpeg.get_ffmpeg_exe()
        sibling = Path(encoder).with_name("ffprobe" + Path(encoder).suffix)
        if sibling.is_file():
            return encoder, str(sibling)
    except Exception:
        pass
    raise ProductionError("ffmpeg and ffprobe are required for full rendering")


def probe_video(path: Path, ffprobe: str) -> dict[str, Any]:
    completed = subprocess.run([
        ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ], text=True, capture_output=True, encoding="utf-8", errors="replace")
    if completed.returncode:
        raise ProductionError(f"ffprobe failed: {completed.stderr[-1000:]}")
    raw = json.loads(completed.stdout)
    video = next((x for x in raw.get("streams", []) if x.get("codec_type") == "video"), None)
    audio = [x for x in raw.get("streams", []) if x.get("codec_type") == "audio"]
    if video is None:
        raise ProductionError(f"no video stream: {path}")
    num, den = (video.get("avg_frame_rate") or "0/1").split("/")
    return {
        "width": int(video["width"]), "height": int(video["height"]),
        "fps": float(num) / float(den), "codec": video.get("codec_name"),
        "pixel_format": video.get("pix_fmt"), "frame_count": int(video.get("nb_frames") or 0),
        "duration_s": float(raw.get("format", {}).get("duration") or 0),
        "audio_streams": len(audio),
    }


def render_full(*, output_root: Path, width: int = 1920, height: int = 1080,
                workers: int = 4, keep_frames: bool = False) -> dict[str, Any]:
    """Render three silent masters. Intended for a separately authorized worker."""
    manifest = production_contracts()
    if not FRAME_DRIVER.is_file() or not (POP_ROOT / "node_modules" / "playwright").is_dir():
        raise ProductionError("POP frame driver or Playwright installation is missing")
    node = shutil.which("node")
    if not node:
        raise ProductionError("node is not on PATH")
    ffmpeg, ffprobe = ffmpeg_tools()
    sans, mono = locate_fonts()
    sans_b64, mono_b64 = b64_font(sans), b64_font(mono)
    output_root.mkdir(parents=True, exist_ok=True)
    symbol_root = output_root / "symbol_preflight"
    symbol_frames = symbol_root / "repeat_frames"
    symbol_frames.mkdir(parents=True, exist_ok=True)
    for old in symbol_frames.glob("f*.png"):
        old.unlink()
    symbol_html = symbol_stress_html(sans_b64, mono_b64, width, height)
    symbol_manifest = {
        "width": width, "height": height, "fps": FPS,
        "scenes": [
            {"id": "symbols-a", "kind": "foundational_cm", "startIndex": 0, "progress": [0.985], "html": symbol_html},
            {"id": "symbols-b", "kind": "foundational_cm", "startIndex": 1, "progress": [0.985], "html": symbol_html},
        ],
    }
    symbol_manifest_path = symbol_root / "symbol_stress_manifest.json"
    write_json(symbol_manifest_path, symbol_manifest)
    symbol_run = subprocess.run(
        [node, str(FRAME_DRIVER), str(symbol_manifest_path), str(symbol_frames), "1"],
        cwd=str(POP_ROOT), text=True, capture_output=True, encoding="utf-8", errors="replace",
    )
    if symbol_run.returncode:
        raise ProductionError(f"remote symbol preflight failed: {symbol_run.stderr[-1500:]}")
    symbol_a, symbol_b = symbol_frames / "f000000.png", symbol_frames / "f000001.png"
    if not symbol_a.is_file() or not symbol_b.is_file() or sha256(symbol_a) != sha256(symbol_b):
        raise ProductionError("remote repeated symbol frames differ")
    symbol_specimen = symbol_root / "symbol_specimen.png"
    shutil.copy2(symbol_a, symbol_specimen)
    results = []
    for video_id, script_path in SCRIPT_PATHS.items():
        scenes = parse_script(script_path)
        episode_root = output_root / video_id
        frames_dir = episode_root / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        for old in frames_dir.glob("f*.png"):
            old.unlink()
        rendered_scenes = []
        start_index = 0
        for index, scene in enumerate(scenes):
            count = int(round(scene["duration_s"] * FPS))
            rendered_scenes.append({
                "id": scene["scene_id"], "kind": "foundational_cm", "startIndex": start_index,
                "progress": [(i + 0.5) / count for i in range(count)],
                "html": html_scene(video_id, scene, index, sans_b64, mono_b64, width, height),
            })
            start_index += count
        frame_manifest = {"width": width, "height": height, "fps": FPS, "scenes": rendered_scenes}
        frame_manifest_path = episode_root / "frame_manifest.json"
        write_json(frame_manifest_path, frame_manifest)
        rendered = subprocess.run(
            [node, str(FRAME_DRIVER), str(frame_manifest_path), str(frames_dir), str(workers)],
            cwd=str(POP_ROOT), text=True, capture_output=True, encoding="utf-8", errors="replace",
        )
        if rendered.returncode:
            raise ProductionError(f"full render failed for {video_id}: {rendered.stderr[-1800:]}")
        frame_paths = sorted(frames_dir.glob("f*.png"))
        if len(frame_paths) != start_index:
            raise ProductionError(f"frame count mismatch for {video_id}: {len(frame_paths)} != {start_index}")
        qa_root = episode_root / "qa_frames"
        qa_root.mkdir(parents=True, exist_ok=True)
        selected = {"opening": frame_paths[0], "middle": frame_paths[len(frame_paths)//2], "final": frame_paths[-1]}
        qa_refs = {}
        for name, source in selected.items():
            target = qa_root / f"{name}.png"
            shutil.copy2(source, target)
            qa_refs[name] = {"path": target.relative_to(output_root).as_posix(), "sha256": sha256(target)}
        video = episode_root / f"{video_id}.silent-master.mp4"
        encoded = subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FPS),
            "-i", str(frames_dir / "f%06d.png"), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-map_metadata", "-1", "-movflags", "+faststart", str(video),
        ], text=True, capture_output=True, encoding="utf-8", errors="replace")
        if encoded.returncode:
            raise ProductionError(f"encode failed for {video_id}: {encoded.stderr[-1200:]}")
        technical = probe_video(video, ffprobe)
        expected_duration = scenes[-1]["end_s"]
        if (
            technical["width"] != width or technical["height"] != height
            or abs(technical["fps"] - FPS) > 0.001 or technical["codec"] != "h264"
            or technical["pixel_format"] != "yuv420p" or technical["audio_streams"] != 0
            or technical["frame_count"] != start_index or abs(technical["duration_s"] - expected_duration) > 0.05
        ):
            raise ProductionError(f"media contract failed for {video_id}: {technical}")
        result = {
            "video_id": video_id, "status": "passed", "content_hash": next(x["content_hash"] for x in manifest["episodes"] if x["video_id"] == video_id),
            "video": {"path": video.relative_to(output_root).as_posix(), "sha256": sha256(video), "bytes": video.stat().st_size},
            "technical": technical, "qa_frames": qa_refs,
        }
        write_json(episode_root / "render_result.json", result)
        results.append(result)
        if not keep_frames:
            shutil.rmtree(frames_dir)
    final = {
        "schema_version": "1.0", "status": "passed", "revision_id": "foundational-cm-production-v2",
        "package_identity_sha256": manifest["package_identity_sha256"], "episodes": results,
        "symbol_preflight": {
            "status": "passed", "font_cmap_coverage": True, "repeat_frame_deterministic": True,
            "specimen": {"path": symbol_specimen.relative_to(output_root).as_posix(), "sha256": sha256(symbol_specimen)},
        },
        "narration": False, "publication_authorized": False,
    }
    write_json(output_root / "render_summary.json", final)
    return final


def validate() -> dict[str, Any]:
    manifest = production_contracts()
    font = json.loads((PACKAGE / "MATH_TYPOGRAPHY_CONTRACT_V2.json").read_text(encoding="utf-8"))
    checks = []

    def check(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("font-coverage", all(x["sans"] for x in font["coverage"]), font["coverage"])
    check("three-episodes", len(manifest["episodes"]) == 3, len(manifest["episodes"]))
    check("total-duration", manifest["total_duration_s"] == 704, manifest["total_duration_s"])
    for video_id, path in SCRIPT_PATHS.items():
        sections = parse_script(path)
        check(f"contiguous:{video_id}", all(a["end_s"] == b["start_s"] for a, b in zip(sections, sections[1:])), len(sections))
        title_body = [scene_body(video_id, i) for i in range(len(sections))]
        check(f"visual-count:{video_id}", len(title_body) == len(sections), len(title_body))
    preview_path = PACKAGE / "PREVIEW_REPORT_V2.json"
    if preview_path.is_file():
        preview = json.loads(preview_path.read_text(encoding="utf-8"))
        for item in preview["episodes"]:
            for key in ("contact_sheet", "silent_animatic"):
                path = ROOT / item[key]["path"]
                check(f"preview:{item['video_id']}:{key}", path.is_file() and sha256(path) == item[key]["sha256"], item[key])
    failed = [item for item in checks if not item["passed"]]
    result = {"status": "pass" if not failed else "fail", "check_count": len(checks), "passed_count": len(checks)-len(failed), "failed_count": len(failed), "failed": failed, "checks": checks}
    write_json(PACKAGE / "VALIDATION_REPORT_V2.json", result)
    return result


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build-contracts", "render-previews", "render-full", "validate"))
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--output-root", type=Path, default=PACKAGE / "full_render_output")
    parser.add_argument("--keep-frames", action="store_true")
    args = parser.parse_args()
    if args.command == "build-contracts":
        result = production_contracts()
    elif args.command == "render-previews":
        result = render_previews(width=args.width, height=args.height, workers=args.workers)
    elif args.command == "render-full":
        result = render_full(output_root=args.output_root.resolve(), width=args.width, height=args.height,
                             workers=args.workers, keep_frames=args.keep_frames)
    else:
        result = validate()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
