"""Build corrected foundational-CM contracts and bounded local previews.

This module is additive. It reads accepted local review candidates and produces
new v3 contracts/previews only. It never synthesizes speech, renders a master,
uses a network service, reads credentials, or authorizes production.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FACTORY = ROOT / "docs" / "video_factory"
PACKAGE = FACTORY / "deep_series" / "foundational_cm_production_v3"
REVIEW = FACTORY / "deep_series" / "foundational_visuals_pipeline_review_v1"
POP_ROOT = ROOT.parent / "PoP" / "Tools" / "POP-Video-Creator"
FRAME_DRIVER = POP_ROOT / "pop_video" / "render" / "frame_driver.js"
WIDTH, HEIGHT, FPS = 960, 540, 15

SCRIPT_PATHS = {
    "operator-cms-from-truth-tables": FACTORY / "deep_series/episodes/operator-cms-from-truth-tables/revision_v4/SCRIPT_V4.md",
    "logical-matrices-to-higher-dimensional-cms": FACTORY / "deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v4/SCRIPT_V4.md",
    "what-is-explicit-cm": FACTORY / "deep_series/episodes/what-is-explicit-cm/revision_v5/SCRIPT_V5.md",
}
SPEC_PATHS = {
    "operator-cms-from-truth-tables": FACTORY / "deep_series/episodes/operator-cms-from-truth-tables/revision_v4/VISUAL_AND_PRODUCTION_SPEC_V4.md",
    "logical-matrices-to-higher-dimensional-cms": FACTORY / "deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v4/VISUAL_AND_PRODUCTION_SPEC_V4.md",
    "what-is-explicit-cm": FACTORY / "deep_series/episodes/what-is-explicit-cm/revision_v5/VISUAL_AND_PRODUCTION_SPEC_V5.md",
}

class CorrectionError(RuntimeError):
    pass

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()

def write_new_json(path: Path, value: Any) -> None:
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != payload:
            raise CorrectionError(f"refusing to overwrite different v3 artifact: {path}")
        return
    path.write_text(payload, encoding="utf-8", newline="\n")

def write_new_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != value:
            raise CorrectionError(f"refusing to overwrite different v3 artifact: {path}")
        return
    path.write_text(value, encoding="utf-8", newline="\n")

def load_legacy_helpers():
    spec = importlib.util.spec_from_file_location("foundational_v2_helpers", FACTORY / "foundational_cm_production.py")
    if not spec or not spec.loader:
        raise CorrectionError("could not load v2 parsing/font helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

LEGACY = load_legacy_helpers()

def split_script_cues(path: Path, scenes: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    source = path.read_text(encoding="utf-8")
    blocks = re.findall(r"\*\*Voiceover\*\*\n\n(.*?)\n\n\*\*Visual\*\*", source, re.S)
    if len(blocks) != len(scenes):
        raise CorrectionError(f"voice block mismatch: {path}")
    result = []
    for scene, block in zip(scenes, blocks):
        raw: list[dict[str, Any]] = []
        for paragraph in re.split(r"\n\s*\n", block.strip()):
            if "Four-second retrieval pause" in paragraph:
                raw.append({"kind": "pause", "duration_s": 4.0})
                continue
            text = " ".join(paragraph.split())
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                if sentence:
                    raw.append({"kind": "speech", "text": sentence})
        speech_items = [x for x in raw if x["kind"] == "speech"]
        speech_weight = sum(max(1, len(x["text"].split())) for x in speech_items)
        pause_s = sum(x.get("duration_s", 0) for x in raw if x["kind"] == "pause")
        available = scene["duration_s"] - pause_s
        if available <= 0 or not speech_weight:
            raise CorrectionError(f"invalid cue window: {path}:{scene['scene_id']}")
        minimums = {id(x): max(1.0, len(x["text"]) / 20.0) for x in speech_items}
        slack = available - sum(minimums.values())
        if slack < -0.01:
            raise CorrectionError(f"speech/caption minimums exceed scene: {path}:{scene['scene_id']}")
        cursor = float(scene["start_s"])
        cues = []
        for item in raw:
            start = cursor
            if item["kind"] == "pause":
                duration = float(item["duration_s"])
            else:
                duration = minimums[id(item)] + max(0.0, slack) * max(1, len(item["text"].split())) / speech_weight
            cursor += duration
            cues.append({**item, "start_s": round(start, 3), "end_s": round(cursor, 3)})
        cues[-1]["end_s"] = float(scene["end_s"])
        result.append(cues)
    return result

def wrap_caption(text: str, limit: int = 42) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if len(candidate) <= limit:
            current = candidate
        else:
            if not current or len(word) > limit:
                raise CorrectionError(f"caption token exceeds {limit} chars: {word}")
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def caption_phrases(text: str) -> list[str]:
    chunks = [x.strip() for x in re.split(r"(?<=[,;:])\s+|\s+(?=(?:and|but|so)\s)", text) if x.strip()]
    phrases: list[str] = []
    for chunk in chunks:
        lines = wrap_caption(chunk)
        for i in range(0, len(lines), 2):
            phrases.append("\n".join(lines[i:i+2]))
    return phrases

def vtt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000)); hours, ms = divmod(ms, 3_600_000); minutes, ms = divmod(ms, 60_000); sec, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{sec:02d}.{ms:03d}"

def build_contracts() -> dict[str, Any]:
    claims = json.loads((REVIEW / "CLAIM_BINDINGS_V1.json").read_text(encoding="utf-8"))
    claim_by_scene = {(x["video_id"], x["scene_id"]): x["claim_ids"] for x in claims["scene_bindings"]}
    math_path = REVIEW / "MATH_RECOMPUTATION_V1.json"
    episodes = []
    artifacts: list[Path] = []
    for video_id, script_path in SCRIPT_PATHS.items():
        scenes = LEGACY.parse_script(script_path)
        cue_groups = split_script_cues(script_path, scenes)
        narration_cues=[]; caption_cues=[]; vtt=["WEBVTT", ""]
        storyboard=[]; caption_number=1
        for scene, cues in zip(scenes, cue_groups):
            scene_claims = claim_by_scene[(video_id, scene["scene_id"])]
            scene_beats=[]
            for ci, cue in enumerate(cues, 1):
                cue_id=f"{scene['scene_id']}-c{ci:02d}"
                record={"cue_id":cue_id,"scene_id":scene["scene_id"],**cue}
                if cue["kind"]=="speech":
                    record.update({"text_sha256":hashlib.sha256(cue["text"].encode()).hexdigest(),"claim_ids":scene_claims,"timing_status":"editorial_preview_requires_audio_alignment"})
                    phrases=caption_phrases(cue["text"])
                    weights=[max(1,len(p.replace("\n"," "))) for p in phrases]
                    required=[max(1.0,w/17.0) for w in weights]
                    total_window=cue["end_s"]-cue["start_s"]
                    needed=sum(required)
                    if needed>total_window+0.01:
                        raise CorrectionError(f"caption speed overflow: {video_id}:{cue_id}")
                    cursor=cue["start_s"]
                    for phrase,min_duration in zip(phrases,required):
                        remaining=cue["end_s"]-cursor
                        duration=min(6.0,max(min_duration,remaining/len(phrases)))
                        end=min(cue["end_s"],cursor+duration)
                        flat=phrase.replace("\n"," ")
                        cc={"caption_id":f"cap-{caption_number:03d}","cue_id":cue_id,"start_s":round(cursor,3),"end_s":round(end,3),"text":phrase,"characters":len(flat),"characters_per_second":round(len(flat)/(end-cursor),2)}
                        if len(phrase.split("\n"))>2 or any(len(x)>42 for x in phrase.split("\n")) or end-cursor>6.001 or cc["characters_per_second"]>20:
                            raise CorrectionError(f"caption gate failed: {video_id}:{cc}")
                        caption_cues.append(cc);vtt += [str(caption_number),f"{vtt_time(cursor)} --> {vtt_time(end)}",phrase,""]
                        caption_number += 1;cursor=end
                narration_cues.append(record)
                scene_beats.append({"cue_id":cue_id,"kind":cue["kind"],"start_s":cue["start_s"],"end_s":cue["end_s"],"claim_ids":scene_claims,"action":"pause with answer hidden" if cue["kind"]=="pause" else "execute the scene's named visual construction step"})
            storyboard.append({"scene_id":scene["scene_id"],"title":scene["title"],"start_s":scene["start_s"],"end_s":scene["end_s"],"visual_direction":scene["visual_direction"],"claim_ids":scene_claims,"beats":scene_beats})
        episode_root=PACKAGE/"episodes"/video_id
        narration={"schema_version":"3.0","status":"editorial_timing_no_audio_generated","video_id":video_id,"script":{"path":script_path.relative_to(ROOT).as_posix(),"sha256":sha256(script_path)},"cues":narration_cues,"pronunciations":{"CM":"C M","LM":"L M","XOR":"exclusive-or","V_T":"V sub T","ket":"ket","bra":"bra","dyad":"die-ad","Kronecker":"crow-neck-er","MSB":"most significant bit"},"voice":{"provider":"local_kokoro_onnx","candidate":"af_heart","status":"provisional_human_listening_required"},"audio_generated":False}
        captions={"schema_version":"3.0","status":"phrase_timing_preview_requires_audio_alignment","video_id":video_id,"limits":{"max_lines":2,"max_characters_per_line":42,"max_duration_s":6,"max_characters_per_second":20},"answer_timing":"retrieval answer captions begin only after explicit four-second pause","cues":caption_cues}
        production={"schema_version":"3.0","status":"bounded_local_preview_ready_full_render_not_authorized","video_id":video_id,"duration_s":scenes[-1]["end_s"],"script":{"path":script_path.relative_to(ROOT).as_posix(),"sha256":sha256(script_path)},"visual_spec":{"path":SPEC_PATHS[video_id].relative_to(ROOT).as_posix(),"sha256":sha256(SPEC_PATHS[video_id])},"math_verification":{"path":math_path.relative_to(ROOT).as_posix(),"sha256":sha256(math_path)},"storyboard":storyboard,"render_route":"bounded local 960x540/15fps previews only","full_render_authorized":False,"remote_or_paid_authorized":False,"publication_authorized":False}
        production["content_hash"]=canonical_hash({k:v for k,v in production.items() if k!="content_hash"})
        paths={"narration":episode_root/"NARRATION_CONTRACT_V3.json","captions":episode_root/"CAPTION_CONTRACT_V3.json","vtt":episode_root/f"{video_id}.editorial-preview.vtt","storyboard":episode_root/"STORYBOARD_V3.json","production":episode_root/"PRODUCTION_CONTRACT_V3.json"}
        write_new_json(paths["narration"],narration);write_new_json(paths["captions"],captions);write_new_text(paths["vtt"],"\n".join(vtt));write_new_json(paths["storyboard"],{"schema_version":"3.0","video_id":video_id,"scenes":storyboard});write_new_json(paths["production"],production)
        artifacts.extend(paths.values());episodes.append({"video_id":video_id,"content_hash":production["content_hash"],"duration_s":production["duration_s"],"speech_cues":sum(x["kind"]=="speech" for x in narration_cues),"pause_cues":sum(x["kind"]=="pause" for x in narration_cues),"caption_phrases":len(caption_cues)})
    manifest={"schema_version":"3.0","status":"bounded_local_preview_ready_full_render_not_authorized","revision_id":"foundational-cm-production-v3","source_review_manifest_sha256":sha256(REVIEW/"REVIEW_MANIFEST_V1.json"),"episodes":episodes,"limits":{"width":WIDTH,"height":HEIGHT,"fps":FPS,"stills":22,"clips":7,"clip_seconds":70,"workers":2},"artifacts":[{"path":p.relative_to(ROOT).as_posix(),"sha256":sha256(p),"bytes":p.stat().st_size} for p in artifacts],"audio_generated":False,"remote_or_paid_work_performed":False,"publication_authorized":False}
    manifest["package_identity_sha256"]=canonical_hash(manifest["artifacts"])
    write_new_json(PACKAGE/"PRODUCTION_MANIFEST_V3.json",manifest)
    return manifest

def font_data() -> tuple[str,str]:
    sans,mono=LEGACY.locate_fonts()
    return base64.b64encode(sans.read_bytes()).decode(),base64.b64encode(mono.read_bytes()).decode()

def matrix(rows: list[str], row_labels: list[str], col_labels: list[str], *, selected: tuple[int,int]|None=None, cls: str="") -> str:
    cells=[]
    for r,row in enumerate(rows):
        for c,value in enumerate(row):
            active=" selected" if selected==(r,c) else ""
            cells.append(f'<i class="bit{active}" data-assignment="{html.escape(row_labels[r]+col_labels[c])}">{value}</i>')
    return f'<div class="matrix {cls}" style="--nr:{len(rows)};--nc:{len(col_labels)}"><div class="cols">{"".join(f"<b>{html.escape(x)}</b>" for x in col_labels)}</div><div class="rows">{"".join(f"<b>{html.escape(x)}</b>" for x in row_labels)}</div><div class="brackets"><div class="cells">{"".join(cells)}</div></div></div>'

def operator_table() -> str:
    entries=[("true","1111"),("false","0000"),("equiv","1001"),("XOR","0110"),("AND","1000"),("NOR","0001"),("X∧¬Y","0100"),("¬X∧Y","0010"),("X→Y","1011"),("Y→X","1101"),("OR","1110"),("NAND","0111"),("Y","1010"),("¬Y","0101"),("X","1100"),("¬X","0011")]
    return '<div class="optable">'+''.join(f'<div><b>{n}</b><span>{p[:2]}<br>{p[2:]}</span></div>' for n,p in entries)+'</div>'

def common_css(sans: str, mono: str) -> str:
    return f'''@font-face{{font-family:D;src:url(data:font/ttf;base64,{sans})}}@font-face{{font-family:DM;src:url(data:font/ttf;base64,{mono})}}*{{box-sizing:border-box}}html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#081018;color:#eef5f7;font-family:D}}body{{--a:#f1b65c;--c:#57d4e8;--v:#a990ff;--m:#bac7ce;--s:#111d27}}.stage{{width:960px;height:540px;padding:28px 42px 54px;background:radial-gradient(circle at 78% 5%,#15303c,transparent 40%),#081018;position:relative}}h1{{font-size:27px;margin:7px 0 9px}}header{{color:var(--a);font:700 10px DM;letter-spacing:.12em}}.badge{{display:inline-block;border:2px solid var(--v);color:#e9e1ff;padding:5px 9px;font:700 12px DM}}.panel{{background:var(--s);border-top:4px solid var(--c);padding:14px}}.formula{{font:700 20px DM}}.note{{color:var(--m);font:600 13px DM}}.row{{display:flex;align-items:center;justify-content:center;gap:18px}}.stack{{display:flex;flex-direction:column;gap:10px}}.matrix{{display:grid;grid-template-columns:64px auto;grid-template-rows:30px auto;align-items:stretch}}.cols{{grid-column:2;display:grid;grid-template-columns:repeat(var(--nc),1fr);place-items:center;color:var(--c);font:700 13px DM}}.rows{{grid-row:2;display:grid;grid-template-rows:repeat(var(--nr),1fr);place-items:center;color:var(--a);font:700 13px DM}}.brackets{{grid-column:2;grid-row:2;border:4px solid #dce8ed;border-top-width:3px;border-bottom-width:3px;padding:5px}}.cells{{display:grid;grid-template-columns:repeat(var(--nc),1fr);height:260px;min-width:280px}}.bit{{display:grid;place-items:center;background:#101c25;border:1px solid #38505e;color:#eef5f7;font:700 23px DM;font-style:normal}}.selected{{outline:4px solid var(--a);outline-offset:-4px;color:var(--c)}}.small .cells{{height:155px;min-width:170px}}.small .bit{{font-size:18px}}.wide .cells{{height:160px;min-width:620px}}.tall .cells{{height:330px;min-width:190px}}.repartition-stage{{height:320px;display:grid;place-items:center}}.repartition-stage>[data-show]{{grid-area:1/1}}.repartition-stage .tall .cells{{height:280px}}.operator-clip-stage{{height:330px;display:grid;place-items:center}}.operator-clip-stage>[data-segment]{{grid-area:1/1;width:100%}}.optable{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}}.optable div{{background:var(--s);border:1px solid #38505e;padding:5px;display:flex;align-items:center;justify-content:space-between}}.optable b{{font-size:13px}}.optable span{{white-space:nowrap;color:#eef5f7;font:700 17px DM}}.stresscompact{{gap:4px}}.stresscompact .optable{{gap:3px}}.stresscompact .optable div{{padding:2px 5px}}.stresscompact .wide .cells{{height:125px}}[data-show]{{opacity:0;transform:translateY(8px)}}.phase{{transition:none}}footer{{position:absolute;bottom:16px;left:42px;right:42px;display:flex;justify-content:space-between;color:#bac7ce;font:600 10px DM}}'''

def body(key: str) -> tuple[str,str]:
    base=matrix(["1100","1110","0011","1011"],["WY 11","WY 10","WY 01","WY 00"],["XZ 11","XZ 10","XZ 01","XZ 00"],selected=(2,0))
    bodies={
      "l_order":("Component order stays attached",f'<div class="row">{base}<div class="panel stack"><b class="formula">WXYZ=0111</b><span>left=1 · right=0</span><strong data-show=".45">implication = 0</strong><span class="note" data-show=".65">row WY=01 · column XZ=11</span><span class="badge" data-show=".78">paper notation: ⟨Y|⟨W| M |X⟩|Z⟩</span><span class="note" data-show=".9">components: [WY,W¬Y,¬WY,¬W¬Y]</span></div></div>'),
      "l_modifier":("Three accepted implication cases",f'<div class="stack"><div class="row"><div class="panel formula">A=01/10</div><div class="panel formula">B=00/10</div><span class="note">A = W⊕X · B = ¬Y∧Z</span></div><div class="row"><div class="panel" data-show=".18">A⊗B<br><b>0000/0010/0000/1000</b></div><div class="panel" data-show=".38">¬A⊗B<br><b>0000/1000/0000/0010</b></div><div class="panel" data-show=".58">¬A⊗¬B<br><b>1100/0100/0011/0001</b></div></div><div data-show=".76" class="row"><span class="formula">XOR sum →</span>{base}</div></div>'),
      "l_valuation":("Value expressions in place",'<div class="stack"><div class="panel formula">positive assignment: X=Y=1 · ¬X=¬Y=0</div><div class="row"><div class="panel formula">[X∧Y  X∧¬Y]<br>[¬X∧Y ¬X∧¬Y]</div><span class="formula">V<sub>T</sub> →</span>'+matrix(["10","00"],["X","¬X"],["Y","¬Y"],cls="small")+'</div><div data-show=".65" class="row"><span class="badge">named equivalence LM</span><span class="formula">[X↔Y X⊕Y; X⊕Y X↔Y] → 10/01</span></div></div>'),
      "l_block":("One tensor entry fills one block",'<div class="stack"><div class="row"><div class="panel formula">M<sub>WX</sub><br><b>WX</b> · W¬X<br>¬WX · ¬W¬X</div><span class="formula">⊗</span><div class="panel formula">M<sub>YZ</sub><br>YZ · Y¬Z<br>¬YZ · ¬Y¬Z</div></div><div data-show=".25" class="panel formula">WX × M<sub>YZ</sub></div><div data-show=".48" class="optable"><div>WXYZ</div><div>WXY¬Z</div><div>WX¬YZ</div><div>WX¬Y¬Z</div></div><div data-show=".8" class="badge">top-left block of the 4×4 expression grid</div></div>'),
      "r_repartition":("Repartition; preserve all assignment outputs",'<div class="stack"><div class="panel formula">F=(A∧B)⊕(C∨D) · tracked 1011 ↦ 1</div><div class="repartition-stage"><div data-show="0">'+matrix(["0111","0111","0111","1000"],["AB 00","AB 01","AB 10","AB 11"],["CD 00","CD 01","CD 10","CD 11"],selected=(2,3),cls="small")+'</div><div data-show=".33">'+matrix(["01110111","01111000"],["A 0","A 1"],[f"BCD {x}" for x in ("000","001","010","011","100","101","110","111")],selected=(1,3),cls="wide")+'</div><div data-show=".67">'+matrix(["01","11","01","11","01","11","10","00"],[f"ABC {x}" for x in ("000","001","010","011","100","101","110","111")],["D 0","D 1"],selected=(5,1),cls="tall")+'</div></div><div class="note">same 16 assignment-output pairs · coordinates (2,3) → (1,3) → (5,1)</div></div>'),
      "r_dense":("Dense means every requested cell is present",'<div class="row">'+matrix(["01","11","01","11","01","11","10","00"],[f"ABC {x}" for x in ("000","001","010","011","100","101","110","111")],["D 0","D 1"],selected=(5,1),cls="tall")+'<div class="panel stack"><b class="formula">8 rows × 2 columns</b><strong data-show=".5" class="formula">= 16 filled cells</strong><span class="note">1011 stays output 1</span></div></div>'),
      "o_retrieval":("Read the complete rule",'<div class="row">'+matrix(["01","10"],["X","¬X"],["Y","¬Y"],cls="small")+'<div class="panel stack"><span class="formula">one when inputs differ</span><b data-show=".72" class="formula">XOR</b><span data-show=".82">|1⟩⟨0| ⊕ |0⟩⟨1|</span></div></div>'),
      "l_retrieval":("Entry type decides the object",'<div class="row"><div class="panel stack"><b class="formula">¬A<sub>L</sub> ⊗ B<sub>L</sub></b><span>selected cell: ¬(W⊕X) ∧ ¬Y ∧ Z</span><span class="badge">expression visible · answer hidden</span></div><div data-show=".72" class="panel stack"><b>WXYZ=0011</b><span>1 ∧ 0 ∧ 1</span><strong class="formula">0 · LM → CM bit</strong></div></div>'),
      "r_retrieval":("Map one assignment yourself",'<div class="stack"><div class="panel formula">F=(A∧B)⊕(C∨D) · R=[A,B] · C=[C,D] · MSB-first</div><div class="row"><b class="formula">1110</b><span>row?</span><span>column?</span><span>output?</span><div data-show=".72" class="badge">(3,2) · 0</div></div></div>'),
      "o_dyad":("A numerical outer product selects one cell",'<div class="row"><div class="panel formula">|1⟩=[1,0]ᵀ</div><span class="formula">×</span><div class="panel formula">⟨0|=[0,1]</div><span class="formula">→</span><div data-show=".35">'+matrix(["01","00"],["1","0"],["1","0"],selected=(0,1),cls="small")+'</div></div><div data-show=".75" class="row"><span class="badge">|1⟩⊗⟨0| = |1⟩⟨0|</span><span>four scalar products · one active position</span></div>'),
      "o_table":("All sixteen complete functions",'<div class="stack"><div class="formula">2×2×2×2 = 2⁴ = 16 · axes X:1,0 / Y:1,0</div>'+operator_table()+'<div class="note">dyadic sums move to a large focus panel; this overview carries names and bits</div></div>'),
      "o_implication":("Operand order moves the failing case",'<div class="row"><div class="stack"><b class="formula">X→Y</b>'+matrix(["10","11"],["X","¬X"],["Y","¬Y"],selected=(0,1),cls="small")+'<span>fails at XY=10</span></div><span class="formula">swap operands →</span><div data-show=".5" class="stack"><b class="formula">Y→X</b>'+matrix(["11","01"],["X","¬X"],["Y","¬Y"],selected=(1,0),cls="small")+'<span>fails at XY=01</span></div></div>'),
      "o_dyad_implication":("Outer product, then operand reversal",'<div class="operator-clip-stage"><div data-segment="dyad" class="row"><div class="panel formula">|1⟩=[1,0]ᵀ</div><span class="formula">×</span><div class="panel formula">⟨0|=[0,1]</div><span class="formula">→</span>'+matrix(["01","00"],["1","0"],["1","0"],selected=(0,1),cls="small")+'<span class="badge">|1⟩⟨0|</span></div><div data-segment="implication" class="row"><div class="stack"><b class="formula">X→Y</b>'+matrix(["10","11"],["X","¬X"],["Y","¬Y"],selected=(0,1),cls="small")+'<span>zero at XY=10</span></div><span class="formula">swap operands →</span><div class="stack"><b class="formula">Y→X</b>'+matrix(["11","01"],["X","¬X"],["Y","¬Y"],selected=(1,0),cls="small")+'<span>zero moves to XY=01</span></div></div></div>'),
      "r_index":("Bits construct the coordinate",'<div class="stack"><div class="formula">1011 ↦ 1 · R=[A,B] · C=[C,D]</div><div class="row"><div class="panel">AB=10₂<br><b class="formula">1×2 + 0×1 = 2</b></div><div class="panel">CD=11₂<br><b class="formula">1×2 + 1×1 = 3</b></div><div data-show=".55">'+matrix(["····","····","···1","····"],["00 (0)","01 (1)","10 (2)","11 (3)"],["00 (0)","01 (1)","10 (2)","11 (3)"],selected=(2,3),cls="small")+'</div></div></div>'),
      "r_first":("Place the tracked value first",'<div class="row"><div class="panel stack"><b class="formula">1011 ↦ (2,3)</b><span>A∧B=0</span><span>C∨D=1</span><strong>0⊕1 = 1</strong></div>'+matrix(["····","····","···1","····"],["AB 00","AB 01","AB 10","AB 11"],["CD 00","CD 01","CD 10","CD 11"],selected=(2,3))+'</div><div data-show=".7" class="note">only after the selected placement do the remaining 15 identified assignments fill</div>'),
      "stress_math":("Typography stress · minimum teaching sizes",'<div class="stack"><div class="panel formula">¬X ∧ Y · X ∨ Y · X ⊕ Y · X → Y · X ↔ Y</div><div class="panel formula">|1⟩ ⊗ ⟨0| = |1⟩⟨0| · V<sub>T</sub>(M<sub>XY</sub>) · 2⁴</div><div class="row">'+matrix(["10","01"],["X","¬X"],["Y","¬Y"],cls="small")+'<div class="panel"><b>Caption safe area below</b><br><span class="note">Essential text ≥ project minimum · zero digits full contrast</span></div></div></div>'),
      "stress_layout":("Layout stress · overview and rectangle headers",'<div class="stack stresscompact">'+operator_table()+'<div class="row">'+matrix(["01110111","01111000"],["A 0","A 1"],[f"BCD {x}" for x in ("000","001","010","011","100","101","110","111")],selected=(1,3),cls="wide")+'</div></div>'),
    }
    return bodies[key]

def page(key: str, sans: str, mono: str) -> str:
    title,content=body(key)
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{common_css(sans,mono)}</style></head><body><div class="stage"><header>CM FOUNDATIONS · CORRECTED LOCAL PREVIEW</header><h1>{html.escape(title)}</h1>{content}<footer><span>conceptual teaching preview</span><span>960×540 · v3 local review</span></footer></div><script>window.__seek=function(p){{document.querySelectorAll('[data-show]').forEach(e=>{{const a=parseFloat(e.dataset.show||0),t=Math.max(0,Math.min(1,(p-a)/.08));e.style.opacity=t;e.style.transform='translateY('+((1-t)*8)+'px)'}});if('{key}'==='r_repartition'){{let v=[...document.querySelectorAll('[data-show]')];v.forEach((e,i)=>{{let a=parseFloat(e.dataset.show||0),next=i+1<v.length?parseFloat(v[i+1].dataset.show||2):2;e.style.opacity=(p>=a&&p<next)?1:0}})}}if('{key}'==='o_dyad_implication'){{let v=[...document.querySelectorAll('[data-segment]')];v.forEach((e,i)=>e.style.opacity=(i===0?p<.48:p>=.48)?1:0)}}}};window.__seek(0)</script></body></html>'''

STILLS=[("l_order_key","l_order",.2),("l_order_counterexample","l_order",.7),("l_modifier_result","l_modifier",.98),("l_positive_assignment","l_valuation",.35),("l_equivalence_valuation","l_valuation",.95),("l_first_tensor_block","l_block",.93),("r_layout_4x4","r_repartition",.15),("r_layout_2x8","r_repartition",.48),("r_layout_8x2","r_repartition",.92),("o_retrieval_question","o_retrieval",.35),("o_retrieval_answer","o_retrieval",.95),("l_retrieval_question","l_retrieval",.35),("l_retrieval_answer","l_retrieval",.95),("r_retrieval_question","r_retrieval",.35),("r_retrieval_answer","r_retrieval",.95),("o_outer_product","o_dyad",.9),("o_named_table","o_table",.98),("o_implication_swap","o_implication",.95),("r_msb_weights","r_index",.9),("r_tracked_first","r_first",.92),("shared_math_stress","stress_math",.98),("shared_layout_stress","stress_layout",.98)]
CLIPS=[("logical_order_and_modifier","l_modifier",12),("logical_valuation_and_block","l_block",12),("repository_repartition","r_repartition",12),("operator_retrieval","o_retrieval",8),("logical_retrieval","l_retrieval",8),("repository_retrieval","r_retrieval",8),("operator_outer_product_and_zero_move","o_dyad_implication",10)]

def render_previews(workers: int=2) -> dict[str,Any]:
    manifest=build_contracts()
    if not FRAME_DRIVER.is_file() or not (POP_ROOT/"node_modules/playwright").is_dir(): raise CorrectionError("existing POP frame driver/Playwright not available")
    node=shutil.which("node")
    if not node: raise CorrectionError("node not found")
    from PIL import Image,ImageDraw
    import imageio_ffmpeg
    sans,mono=font_data();out=PACKAGE/"bounded_previews_v6";frames=out/"frames";frames.mkdir(parents=True,exist_ok=True)
    still_manifest={"width":WIDTH,"height":HEIGHT,"fps":FPS,"scenes":[{"id":name,"kind":"foundational_cm","startIndex":i,"progress":[p],"html":page(key,sans,mono)} for i,(name,key,p) in enumerate(STILLS)]}
    write_new_json(out/"STILL_FRAME_MANIFEST_V6.json",still_manifest)
    run=subprocess.run([node,str(FRAME_DRIVER),str(out/"STILL_FRAME_MANIFEST_V6.json"),str(frames),str(workers)],cwd=POP_ROOT,text=True,capture_output=True,encoding="utf-8",errors="replace")
    if run.returncode: raise CorrectionError(run.stderr[-1600:])
    rendered=sorted(frames.glob("f*.png"));
    if len(rendered)!=22: raise CorrectionError(f"expected 22 stills, got {len(rendered)}")
    still_root=out/"stills";still_root.mkdir(exist_ok=True);still_records=[]
    for source,(name,key,p) in zip(rendered,STILLS):
        target=still_root/f"{name}.png"
        if target.exists() and sha256(target)!=sha256(source): raise CorrectionError(f"refusing to overwrite changed still {target}")
        if not target.exists(): shutil.copyfile(source,target)
        still_records.append({"id":name,"visual":key,"progress":p,"path":target.relative_to(ROOT).as_posix(),"sha256":sha256(target)})
    sheet=Image.new("RGB",(WIDTH*2,HEIGHT*11),"#081018");draw=ImageDraw.Draw(sheet)
    for i,target in enumerate(still_root/f"{x[0]}.png" for x in STILLS):
        image=Image.open(target).convert("RGB");x=(i%2)*WIDTH;y=(i//2)*HEIGHT;sheet.paste(image,(x,y));draw.rectangle((x,y,x+270,y+21),fill="#081018");draw.text((x+5,y+4),STILLS[i][0],fill="#f1b65c")
    contact=out/"BOUNDED_CONTACT_SHEET_V6.png";sheet.save(contact)
    total=0;clip_records=[];clip_root=out/"clips";clip_root.mkdir(exist_ok=True);offset=0;all_scenes=[]
    for name,key,duration in CLIPS:
        count=duration*FPS;all_scenes.append({"id":name,"kind":"foundational_cm","startIndex":offset,"progress":[(i+.5)/count for i in range(count)],"html":page(key,sans,mono)});offset+=count;total+=duration
    clip_manifest={"width":WIDTH,"height":HEIGHT,"fps":FPS,"scenes":all_scenes};write_new_json(out/"CLIP_FRAME_MANIFEST_V6.json",clip_manifest)
    clip_frames=out/"clip_frames";clip_frames.mkdir(exist_ok=True)
    run=subprocess.run([node,str(FRAME_DRIVER),str(out/"CLIP_FRAME_MANIFEST_V6.json"),str(clip_frames),str(workers)],cwd=POP_ROOT,text=True,capture_output=True,encoding="utf-8",errors="replace")
    if run.returncode: raise CorrectionError(run.stderr[-1600:])
    if len(list(clip_frames.glob("f*.png")))!=70*FPS: raise CorrectionError("clip frame ceiling mismatch")
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe();start=0
    for name,key,duration in CLIPS:
        target=clip_root/f"{name}.mp4";pattern=clip_frames/f"f%06d.png"
        command=[ffmpeg,"-hide_banner","-loglevel","error","-n","-framerate",str(FPS),"-start_number",str(start),"-i",str(pattern),"-frames:v",str(duration*FPS),"-c:v","libx264","-crf","22","-pix_fmt","yuv420p","-movflags","+faststart",str(target)]
        encoded=subprocess.run(command,text=True,capture_output=True,encoding="utf-8",errors="replace")
        if encoded.returncode and "already exists" not in encoded.stderr: raise CorrectionError(encoded.stderr[-1000:])
        clip_records.append({"id":name,"visual":key,"duration_s":duration,"frames":duration*FPS,"path":target.relative_to(ROOT).as_posix(),"sha256":sha256(target)})
        start+=duration*FPS
    shutil.rmtree(frames);shutil.rmtree(clip_frames)
    report={"schema_version":"3.0","preview_revision":"v6","status":"bounded_local_preview_complete_human_review_required","production_identity":manifest["package_identity_sha256"],"width":WIDTH,"height":HEIGHT,"fps":FPS,"stills":still_records,"clips":clip_records,"totals":{"stills":len(still_records),"clips":len(clip_records),"clip_seconds":total,"clip_frames":total*FPS},"contact_sheet":{"path":contact.relative_to(ROOT).as_posix(),"sha256":sha256(contact)},"supersedes_preview":"bounded_previews_v5 (retained after scope QA found the operator motion clip omitted its outer-product beat)","audio_generated":False,"full_episode_or_master_rendered":False,"remote_or_paid_work_performed":False,"publication_authorized":False}
    write_new_json(out/"BOUNDED_PREVIEW_REPORT_V6.json",report)
    return report

def validate() -> dict[str,Any]:
    manifest=build_contracts();checks=[]
    def add(name,passed,detail):checks.append({"name":name,"passed":bool(passed),"detail":detail})
    add("three episodes",len(manifest["episodes"])==3,len(manifest["episodes"]))
    add("review identity",manifest["source_review_manifest_sha256"]==sha256(REVIEW/"REVIEW_MANIFEST_V1.json"),manifest["source_review_manifest_sha256"])
    add("caption phrase count",all(e["caption_phrases"]>e["speech_cues"] for e in manifest["episodes"]),manifest["episodes"])
    for e in manifest["episodes"]:
        root=PACKAGE/"episodes"/e["video_id"];captions=json.loads((root/"CAPTION_CONTRACT_V3.json").read_text(encoding="utf-8"));narration=json.loads((root/"NARRATION_CONTRACT_V3.json").read_text(encoding="utf-8"))
        add(f"caption limits:{e['video_id']}",all(len(c["text"].split("\n"))<=2 and max(map(len,c["text"].split("\n")))<=42 and c["end_s"]-c["start_s"]<=6.001 and c["characters_per_second"]<=20 for c in captions["cues"]),len(captions["cues"]))
        pauses=[c for c in narration["cues"] if c["kind"]=="pause"]
        add(f"retrieval pause:{e['video_id']}",len(pauses)==1 and abs(pauses[0]["end_s"]-pauses[0]["start_s"]-4)<.01,pauses)
    preview=PACKAGE/"bounded_previews_v6/BOUNDED_PREVIEW_REPORT_V6.json"
    if preview.exists():
        import imageio_ffmpeg
        p=json.loads(preview.read_text(encoding="utf-8"));add("bounded previews",p["totals"]=={"stills":22,"clips":7,"clip_seconds":70,"clip_frames":1050},p["totals"]);add("preview hashes",all(sha256(ROOT/x["path"])==x["sha256"] for x in p["stills"]+p["clips"]),29)
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe();decode_results=[]
        for clip in p["clips"]:
            clip_path=ROOT/clip["path"]
            decoded=subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-i",str(clip_path),"-map","0:v:0","-f","null","-"],capture_output=True)
            frame_count,duration=imageio_ffmpeg.count_frames_and_secs(str(clip_path))
            decode_results.append({"id":clip["id"],"returncode":decoded.returncode,"decoded_frames":frame_count,"duration_s":round(duration,3),"expected_frames":clip["frames"],"expected_duration_s":clip["duration_s"]})
        add("full clip decode",all(x["returncode"]==0 and x["decoded_frames"]==x["expected_frames"] and abs(x["duration_s"]-x["expected_duration_s"])<=1/FPS for x in decode_results),decode_results)
    result={"schema_version":"3.0","status":"passed" if all(x["passed"] for x in checks) else "failed","checks":checks,"remote_or_paid_work_performed":False}
    validation_name="VALIDATION_WITH_PREVIEWS_V4.json" if preview.exists() else "VALIDATION_V3.json"
    write_new_json(PACKAGE/validation_name,result)
    if result["status"]!="passed":raise CorrectionError(str([x for x in checks if not x["passed"]]))
    return result

def freeze_package() -> dict[str,Any]:
    validation=PACKAGE/"VALIDATION_WITH_PREVIEWS_V4.json"
    if not validation.is_file(): raise CorrectionError("run validate after the final bounded preview before freezing")
    candidates=list(SCRIPT_PATHS.values())+list(SPEC_PATHS.values())
    roots=[ROOT/"docs/video_factory/deep_series/foundational_cm_revision_v5",PACKAGE/"episodes",PACKAGE/"bounded_previews_v6"]
    files=set(candidates+[ROOT/"docs/video_factory/foundational_cm_corrections_v3.py",ROOT/"docs/video_factory/tests/test_foundational_cm_corrections_v3.py",REVIEW/"REVIEW_MANIFEST_V1.json",PACKAGE/"PRODUCTION_MANIFEST_V3.json",PACKAGE/"VALIDATION_V3.json",validation,PACKAGE/"IMPLEMENTATION_REPORT_V4.md"])
    for artifact_root in roots:
        files.update(path for path in artifact_root.rglob("*") if path.is_file())
    artifacts=[{"path":path.relative_to(ROOT).as_posix(),"sha256":sha256(path),"bytes":path.stat().st_size} for path in sorted(files,key=lambda x:x.as_posix())]
    superseded=[]
    for relative,reason in (("bounded_previews/BOUNDED_PREVIEW_REPORT_V3.json","8x2 grid clipped off right edge"),("bounded_previews_v4/BOUNDED_PREVIEW_REPORT_V4.json","8x2 bottom label entered footer safe area"),("bounded_previews_v5/BOUNDED_PREVIEW_REPORT_V5.json","operator motion clip omitted its planned outer-product beat")):
        path=PACKAGE/relative
        if path.is_file(): superseded.append({"path":path.relative_to(ROOT).as_posix(),"sha256":sha256(path),"reason":reason,"retained":True})
    manifest={"schema_version":"4.0","revision_id":"foundational-cm-correction-implementation-v4","date":"2026-09-12","status":"local_domain_editorial_review_ready_human_visual_and_future_listening_review_required","source_review_manifest":{"path":(REVIEW/"REVIEW_MANIFEST_V1.json").relative_to(ROOT).as_posix(),"sha256":sha256(REVIEW/"REVIEW_MANIFEST_V1.json")},"current_preview":"docs/video_factory/deep_series/foundational_cm_production_v3/bounded_previews_v6/BOUNDED_PREVIEW_REPORT_V6.json","superseded_previews":superseded,"artifacts":artifacts,"artifact_identity_sha256":canonical_hash(artifacts),"audio_generated":False,"full_episode_or_master_rendered":False,"remote_or_paid_work_performed":False,"publication_performed":False,"commit_or_push_performed":False,"shared_bible_or_generated_catalog_modified":False}
    manifest_path=PACKAGE/"IMPLEMENTATION_MANIFEST_V4.json";write_new_json(manifest_path,manifest)
    write_new_text(PACKAGE/"IMPLEMENTATION_MANIFEST_V4.sha256",sha256(manifest_path)+"  IMPLEMENTATION_MANIFEST_V4.json\n")
    return manifest

def verify_frozen_package() -> dict[str,Any]:
    manifest_path=PACKAGE/"IMPLEMENTATION_MANIFEST_V4.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    failures=[]
    for item in manifest["artifacts"]:
        path=ROOT/item["path"]
        if not path.is_file() or sha256(path)!=item["sha256"] or path.stat().st_size!=item["bytes"]: failures.append(item["path"])
    expected=(PACKAGE/"IMPLEMENTATION_MANIFEST_V4.sha256").read_text(encoding="utf-8").split()[0]
    if sha256(manifest_path)!=expected: failures.append(manifest_path.relative_to(ROOT).as_posix())
    result={"schema_version":"3.0","status":"passed" if not failures else "failed","artifact_count":len(manifest["artifacts"]),"artifact_identity_sha256":manifest["artifact_identity_sha256"],"manifest_sha256":sha256(manifest_path),"failures":failures}
    if failures: raise CorrectionError(str(result))
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument("command",choices=("build-contracts","render-bounded-previews","validate","freeze-package","verify-package"));parser.add_argument("--workers",type=int,default=2);args=parser.parse_args()
    value=build_contracts() if args.command=="build-contracts" else render_previews(args.workers) if args.command=="render-bounded-previews" else validate() if args.command=="validate" else freeze_package() if args.command=="freeze-package" else verify_frozen_package()
    print(json.dumps(value,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
