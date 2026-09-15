"""Lightweight static checks for the CM LaTeX working draft.

This does not replace a TeX compilation. It catches notation regressions,
missing citations/references, duplicate labels, and mismatched environments.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEX = ROOT / "main.tex"
APPENDIX = ROOT / "appendix_proofs.tex"
BIB = ROOT / "references.bib"
FIGURE_ROOT = ROOT.parent / "04_figures"
PROTOCOL_V3 = ROOT.parent / "01_audit" / "EVALUATION_PROTOCOL_V3.md"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def check_braces(name: str, source: str) -> None:
    depth = 0
    for offset, character in enumerate(source):
        if character not in "{}":
            continue
        preceding = 0
        cursor = offset - 1
        while cursor >= 0 and source[cursor] == "\\":
            preceding += 1
            cursor -= 1
        if preceding % 2:
            continue
        depth += 1 if character == "{" else -1
        if depth < 0:
            fail(f"unexpected closing brace in {name} at character {offset}")
    if depth:
        fail(f"unbalanced braces in {name}: final depth {depth}")


def main() -> None:
    tex = TEX.read_text(encoding="utf-8")
    appendix = APPENDIX.read_text(encoding="utf-8")
    full_tex = f"{tex}\n{appendix}"
    bib = BIB.read_text(encoding="utf-8")
    figure_sources = {
        path.name: path.read_text(encoding="utf-8")
        for path in FIGURE_ROOT.glob("figure_*.svg")
    }

    if r"\author{Brian Theory}" not in tex:
        fail("new manuscript byline must be Brian Theory")
    if r"\input{appendix_proofs}" not in tex or not APPENDIX.is_file():
        fail("main.tex must include the local appendix proof file")
    if not PROTOCOL_V3.is_file():
        fail("evaluation protocol v3 is required for the revised manuscript")

    numeric_map = FIGURE_ROOT / "figure_02_numeric_representation_map.svg"
    numeric_preview = FIGURE_ROOT / "figure_02_numeric_representation_map_preview.png"
    if not numeric_map.is_file() or not numeric_preview.is_file():
        fail("the split numeric representation map and preview are required")
    if "figure_02_numeric_representation_map_preview.png" not in tex:
        fail("main.tex must use the split numeric representation map")

    lm_call = tex.rfind(r"\logicalmatrixsection")
    experiment_start = tex.find(r"\section{Experimental method}")
    if lm_call < 0 or experiment_start < 0 or lm_call > experiment_start:
        fail("the LM section must precede the empirical sequence")

    required_revision_tokens = {
        r"\texttt{pure\_structural}": "pure structural compiler arm",
        r"\texttt{hybrid\_pair}": "hybrid root outcome",
        r"\texttt{full\_retabulation}": "whole-root retabulation outcome",
        r"\texttt{ordinary\_fallback}": "ordinary fallback outcome",
        r"\texttt{cm\_token\_value}": "shared token-query endpoint",
    }
    for token, description in required_revision_tokens.items():
        if token not in tex:
            fail(f"missing {description}: {token}")

    check_braces(TEX.name, tex)
    check_braces(APPENDIX.name, appendix)

    forbidden = {
        r"\\oplus": r"use \Updownarrow rather than \oplus for XOR",
        "θ": "use uppercase Θ throughout current paper material",
        r"\\theta": r"use \Theta rather than \theta",
        "[Θ]_f": "use the generic whole-matrix notation [Θ]",
        "t_f": "write vec([Θ]) directly in the representation map",
    }
    for pattern, message in forbidden.items():
        if re.search(pattern, full_tex):
            fail(message)

    for name, source in figure_sources.items():
        if "θ" in source or r"\theta" in source:
            fail(f"{name}: use uppercase Θ throughout")
    rule_figure = figure_sources.get("figure_03_operand_alignment_and_fusion.svg", "")
    if "⟨X|[Θ]|Y⟩<tspan baseline-shift=\"super\"" in rule_figure:
        fail("Figure 3 must transpose the operator, not the scalar result")
    for name in (
        "figure_02_representation_map.svg",
        "figure_04_lm_valuation_and_pairing.svg",
    ):
        if "Θ<tspan baseline-shift=\"sub\" font-size=\"13\">ij</tspan>" in figure_sources.get(name, ""):
            fail(f"{name}: use c_ij for LM position coefficients")

    env_tokens = re.findall(r"\\(begin|end)\{([^{}]+)\}", full_tex)
    stack: list[str] = []
    for action, name in env_tokens:
        if action == "begin":
            stack.append(name)
        elif not stack or stack.pop() != name:
            fail(f"mismatched LaTeX environment near {action}{{{name}}}")
    if stack:
        fail(f"unclosed LaTeX environments: {stack}")

    labels = re.findall(r"\\label\{([^{}]+)\}", full_tex)
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        fail(f"duplicate labels: {duplicates}")

    references = set(
        re.findall(r"\\(?:ref|eqref|cref|Cref)\{([^{}]+)\}", full_tex)
    )
    missing_references = sorted(references - set(labels))
    if missing_references:
        fail(f"references without labels: {missing_references}")

    cited: set[str] = set()
    for group in re.findall(r"\\cite[pt]?\{([^{}]+)\}", full_tex):
        cited.update(key.strip() for key in group.split(","))
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    missing_citations = sorted(cited - bib_keys)
    if missing_citations:
        fail(f"citation keys absent from references.bib: {missing_citations}")

    print(
        "Manuscript static checks passed: "
        f"{len(labels)} labels, {len(cited)} cited sources, "
        f"{len(full_tex.split())} whitespace-delimited tokens."
    )


if __name__ == "__main__":
    main()
