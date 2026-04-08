"""
cm_render.py

Lightweight LaTeX/HTML renderer for 2x2 Correspondence Matrix computations with bra/ket.

This is a utility module to generate MathJax-rendered HTML pages showing steps like:
  <X| Θ
  Θ |Y>
  <X| Θ |Y>

Dependencies:
- numpy (runtime)
- sympy (only for symbolic rendering helpers)
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple, Union

import numpy as np
import sympy as sp

from cm_lm import bra as make_bra
from cm_lm import bra_times_cm, cm_times_ket, op_to_cm, ket as make_ket, transform_cm


Semiring = Literal["bool", "arith", "xor"]
Basis = Literal["not_first", "x_first"]


def _latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("%", r"\%")
        .replace("#", r"\#")
        .replace("&", r"\&")
        .replace("$", r"\$")
        .replace("{", r"\{")
        .replace("}", r"\}")
    )


def latex_bra(label: str) -> str:
    return rf"\langle {_latex_escape(label)} \rvert"


def latex_ket(label: str) -> str:
    return rf"\lvert {_latex_escape(label)} \rangle"


def latex_row_vec(v: np.ndarray) -> str:
    if not isinstance(v, np.ndarray) or v.shape != (1, 2):
        raise ValueError("Expected a 1x2 numpy array for row vector")
    a, b = int(v[0, 0]), int(v[0, 1])
    return rf"\begin{{bmatrix}} {a} & {b} \end{{bmatrix}}"


def latex_col_vec(v: np.ndarray) -> str:
    if not isinstance(v, np.ndarray) or v.shape != (2, 1):
        raise ValueError("Expected a 2x1 numpy array for column vector")
    a, b = int(v[0, 0]), int(v[1, 0])
    return rf"\begin{{bmatrix}} {a} \\ {b} \end{{bmatrix}}"


def latex_matrix(M: np.ndarray) -> str:
    if not isinstance(M, np.ndarray) or M.shape != (2, 2):
        raise ValueError("Expected a 2x2 numpy array for matrix")
    a11, a12 = int(M[0, 0]), int(M[0, 1])
    a21, a22 = int(M[1, 0]), int(M[1, 1])
    return rf"\begin{{bmatrix}} {a11} & {a12} \\ {a21} & {a22} \end{{bmatrix}}"


def render_bra_times_op(
    bra_label: str,
    bra_vec: np.ndarray,
    op: Union[str, int, np.ndarray],
    *,
    semiring: Semiring = "xor",
    rotate: Optional[str] = None,
) -> Tuple[str, np.ndarray]:
    A = op_to_cm(op)
    res = bra_times_cm(bra_vec, A, rotate=rotate, semiring=semiring)
    expr = rf"{latex_bra(bra_label)}\, {latex_matrix(A)} = {latex_row_vec(res)}"
    return expr, res


def render_op_times_ket(
    ket_label: str,
    op: Union[str, int, np.ndarray],
    ket_vec: np.ndarray,
    *,
    semiring: Semiring = "xor",
    rotate: Optional[str] = None,
) -> Tuple[str, np.ndarray]:
    A = op_to_cm(op)
    res = cm_times_ket(A, ket_vec, rotate=rotate, semiring=semiring)
    expr = rf"{latex_matrix(A)}\, {latex_ket(ket_label)} = {latex_col_vec(res)}"
    return expr, res


def render_bra_op_ket(
    bra_label: str,
    bra_vec: np.ndarray,
    op: Union[str, int, np.ndarray],
    ket_label: str,
    ket_vec: np.ndarray,
    *,
    semiring: Semiring = "xor",
    rotate: Optional[str] = None,
) -> Tuple[str, int]:
    A = op_to_cm(op)
    mid = bra_times_cm(bra_vec, A, rotate=rotate, semiring=semiring)
    if semiring == "arith":
        scalar = int((mid.astype(np.uint8) @ ket_vec.astype(np.uint8))[0, 0])
    elif semiring == "xor":
        scalar = int(((int(mid[0, 0]) & int(ket_vec[0, 0])) ^ (int(mid[0, 1]) & int(ket_vec[1, 0]))) & 1)
    else:
        scalar = int(((int(mid[0, 0]) & int(ket_vec[0, 0])) | (int(mid[0, 1]) & int(ket_vec[1, 0]))) & 1)
    expr = rf"{latex_bra(bra_label)}\, {latex_matrix(A)}\, {latex_ket(ket_label)} = {scalar}"
    return expr, scalar


@dataclass
class PrintOpts:
    xor_symbol: str = "Updownarrow"
    booleans_as_01: bool = True


def _replace_boolean_tokens(latex_str: str, opts: PrintOpts) -> str:
    if not opts.booleans_as_01:
        return latex_str
    return latex_str.replace("\\text{True}", "1").replace("\\text{False}", "0")


def _replace_xor_symbol(latex_str: str, opts: PrintOpts) -> str:
    sym = f"\\{opts.xor_symbol}"
    return latex_str.replace("\\veebar", sym).replace("\\oplus", sym)


def sympy_to_paper_latex(expr: sp.Expr, opts: Optional[PrintOpts] = None) -> str:
    if opts is None:
        opts = PrintOpts()
    try:
        expr = sp.simplify(sp.simplify_logic(expr, form="dnf"))
    except Exception:
        expr = sp.simplify(expr)
    s = sp.latex(expr)
    s = _replace_xor_symbol(s, opts)
    s = _replace_boolean_tokens(s, opts)
    return s


def _html_head(title: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; padding: 24px; max-width: 900px; margin: 0 auto; }}
    h1 {{ font-size: 1.4rem; margin: 0 0 1rem; }}
    .step {{ margin: 0.5rem 0; padding: 0.5rem 0.25rem; border-bottom: 1px dashed #ddd; }}
  </style>
  <script>
    window.MathJax = {{ tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], displayMath: [['$$','$$'], ['\\\\[','\\\\]']] }}, svg: {{ fontCache: 'global' }} }};
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js" id="MathJax-script" async></script>
</head><body>
<h1>{title}</h1>
"""


_HTML_TAIL = "</body></html>\n"


def write_mathjax_html(latex_blocks: Iterable[str], outfile: str, *, title: str = "CM Computations") -> None:
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(_html_head(title))
        for block in latex_blocks:
            f.write(f'<div class="step"><div style="white-space:nowrap; overflow-x:auto;">$$ {block} $$</div></div>\n')
        f.write(_HTML_TAIL)


def main() -> None:
    p = argparse.ArgumentParser(description="Render small CM computations to MathJax HTML")
    p.add_argument("-o", "--output", default="cm_demo.html")
    p.add_argument("--title", default="CM Computations")
    p.add_argument("--semiring", choices=["xor", "bool", "arith"], default="xor")
    p.add_argument("--basis", choices=["x_first", "not_first"], default="x_first")
    args = p.parse_args()

    bx1 = make_bra(1, basis=args.basis)
    ky0 = make_ket(0, basis=args.basis)
    steps = [
        render_bra_times_op("x=1", bx1, "AND", semiring=args.semiring)[0],
        render_op_times_ket("y=0", "OR", ky0, semiring=args.semiring)[0],
        render_bra_op_ket("x=1", bx1, "XOR", "y=0", ky0, semiring=args.semiring)[0],
        render_bra_op_ket("x=1", bx1, "IMP", "y=0", ky0, semiring=args.semiring)[0],
    ]
    write_mathjax_html(steps, args.output, title=args.title)
    print(f"Wrote {args.output}.")


if __name__ == "__main__":
    main()

