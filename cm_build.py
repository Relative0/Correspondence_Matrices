"""
cm_build.py
Compile cm_exprlib expressions into correspondence matrices through the shared CM IR.
"""
from typing import Dict, List

import numpy as np

from cm_exprlib import Var
from cm_ir import compile_expr_to_cm_ir, expr_vars, materialize_cm


def _var_name(v: Var) -> str:
    if hasattr(v, "name") and isinstance(getattr(v, "name"), str):
        return getattr(v, "name")
    if hasattr(v, "i"):
        vi = getattr(v, "i")
        if isinstance(vi, int):
            return f"x{vi}"
        if isinstance(vi, str):
            return vi if vi.startswith("x") else f"x{vi}"
    raise AttributeError("Var node must have .name or .i")


def compile_expr_to_cm(
    e,
    R: List[str],
    C: List[str],
    fixed: Dict[str, int],
    *,
    diagnostics=None,
    materialize_mode: str = "partial_hybrid",
    hybrid_threshold: int = 7,
) -> np.ndarray:
    node = compile_expr_to_cm_ir(e, diagnostics=diagnostics)
    return materialize_cm(
        node,
        R,
        C,
        fixed,
        diagnostics=diagnostics,
        materialize_mode=materialize_mode,
        hybrid_threshold=hybrid_threshold,
    )


def eval_cm_boolean(M: np.ndarray, R: List[str], C: List[str], assignment: Dict[str, int], fixed: Dict[str, int]) -> int:
    r = 0
    for v in R:
        b = assignment.get(v, fixed.get(v, 0))
        r = (r << 1) | int(b)
    c = 0
    for v in C:
        b = assignment.get(v, fixed.get(v, 0))
        c = (c << 1) | int(b)
    return int(M[r, c] & 1)
