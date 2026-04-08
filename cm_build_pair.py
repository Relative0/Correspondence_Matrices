"""
cm_build_pair.py

Pair-aware compiler for Correspondence Matrices using 4-bit operator tokens.

Strategy:
- If a sub-expression depends on exactly one row var (from R) and one column
  var (from C), evaluate its 2x2 truth matrix as a single 4-bit token and keep
  it as a Pair surrogate. This enables constant-time composition at inner nodes
  via LUTs (cm_token.cm_compose) without materializing big arrays.
- Otherwise, fall back to the standard builder.

Returns full CM matrix plus metrics (pairable nodes, collapses, ratio).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np

from cm_build import compile_expr_to_cm
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cm_normalize import lift_cm
from cm_token import cm_compose, cm_not


def _vname(v: Var) -> str:
    name = getattr(v, "name", None)
    if isinstance(name, str):
        return name
    return f"x{int(v.i)}"


def _expr_vars(e: Expr) -> List[str]:
    vs: Set[str] = set()

    def rec(z: Expr) -> None:
        if isinstance(z, Var):
            vs.add(_vname(z))
        elif isinstance(z, Not):
            rec(z.a)
        elif isinstance(z, (And, Or, Xor, Imp, Eqv)):
            rec(z.a)
            rec(z.b)
        else:
            raise TypeError(f"Unknown node {type(z)}")

    rec(e)
    return sorted(vs)


def _eval_expr_bool(e: Expr, env: Dict[str, int], fixed: Dict[str, int]) -> int:
    if isinstance(e, Var):
        name = _vname(e)
        return int(env.get(name, fixed.get(name, 0)))
    if isinstance(e, Not):
        return 1 - _eval_expr_bool(e.a, env, fixed)
    if isinstance(e, And):
        return _eval_expr_bool(e.a, env, fixed) & _eval_expr_bool(e.b, env, fixed)
    if isinstance(e, Or):
        return _eval_expr_bool(e.a, env, fixed) | _eval_expr_bool(e.b, env, fixed)
    if isinstance(e, Xor):
        return _eval_expr_bool(e.a, env, fixed) ^ _eval_expr_bool(e.b, env, fixed)
    if isinstance(e, Imp):
        a = _eval_expr_bool(e.a, env, fixed)
        b = _eval_expr_bool(e.b, env, fixed)
        return (1 - a) | b
    if isinstance(e, Eqv):
        a = _eval_expr_bool(e.a, env, fixed)
        b = _eval_expr_bool(e.b, env, fixed)
        return 1 - (a ^ b)
    raise TypeError(e)


def _token_from_expr_two_vars(e: Expr, xl: str, xr: str, fixed: Dict[str, int]) -> int:
    # Bit layout: (11)<<3 | (12)<<2 | (21)<<1 | (22)<<0
    bits = 0
    if _eval_expr_bool(e, {xl: 1, xr: 1}, fixed):
        bits |= (1 << 3)
    if _eval_expr_bool(e, {xl: 1, xr: 0}, fixed):
        bits |= (1 << 2)
    if _eval_expr_bool(e, {xl: 0, xr: 1}, fixed):
        bits |= (1 << 1)
    if _eval_expr_bool(e, {xl: 0, xr: 0}, fixed):
        bits |= (1 << 0)
    return bits


def _token_to_matrix(tok: int) -> np.ndarray:
    # Token layout: [b11 b12 b21 b22]. Our 2x2 convention here is:
    # [[b22, b21],
    #  [b12, b11]]
    b11 = (tok >> 3) & 1
    b12 = (tok >> 2) & 1
    b21 = (tok >> 1) & 1
    b22 = tok & 1
    return np.array([[b22, b21], [b12, b11]], dtype=np.uint8)


@dataclass(frozen=True)
class _Pair:
    xl: str
    xr: str
    tok: int


def _pairable_vars(e: Expr, R: List[str], C: List[str], fixed: Dict[str, int]) -> Optional[Tuple[str, str]]:
    vs = [v for v in _expr_vars(e) if v not in fixed]
    r = [v for v in vs if v in R]
    c = [v for v in vs if v in C]
    if len(r) == 1 and len(c) == 1 and len(vs) <= 2:
        return r[0], c[0]
    return None


def _fallback_compile(
    e: Expr,
    R: List[str],
    C: List[str],
    fixed: Dict[str, int],
    diagnostics: Optional[Dict[str, int]],
    materialize_mode: str,
    hybrid_threshold: int,
) -> np.ndarray:
    return compile_expr_to_cm(
        e,
        R,
        C,
        fixed,
        diagnostics=diagnostics,
        materialize_mode=materialize_mode,
        hybrid_threshold=hybrid_threshold,
    )


def _compile_pair(
    e: Expr,
    R: List[str],
    C: List[str],
    fixed: Dict[str, int],
    metrics: Dict[str, int],
    diagnostics: Optional[Dict[str, int]],
    materialize_mode: str,
    hybrid_threshold: int,
) -> Union[_Pair, np.ndarray]:
    metrics["nodes_total"] = metrics.get("nodes_total", 0) + 1

    pv = _pairable_vars(e, R, C, fixed)
    if pv is not None:
        xl, xr = pv
        metrics["pair_attempts"] = metrics.get("pair_attempts", 0) + 1
        tok = _token_from_expr_two_vars(e, xl, xr, fixed)
        metrics["pair_collapses"] = metrics.get("pair_collapses", 0) + 1
        return _Pair(xl, xr, tok)

    if isinstance(e, Not):
        sub = _compile_pair(e.a, R, C, fixed, metrics, diagnostics, materialize_mode, hybrid_threshold)
        if isinstance(sub, _Pair):
            return _Pair(sub.xl, sub.xr, cm_not(sub.tok))
        return _fallback_compile(e, R, C, fixed, diagnostics, materialize_mode, hybrid_threshold)

    if isinstance(e, (And, Or, Xor, Imp, Eqv)):
        a = _compile_pair(e.a, R, C, fixed, metrics, diagnostics, materialize_mode, hybrid_threshold)
        b = _compile_pair(e.b, R, C, fixed, metrics, diagnostics, materialize_mode, hybrid_threshold)
        if isinstance(a, _Pair) and isinstance(b, _Pair) and a.xl == b.xl and a.xr == b.xr:
            op = (
                "AND"
                if isinstance(e, And)
                else ("OR" if isinstance(e, Or) else ("XOR" if isinstance(e, Xor) else ("IMP" if isinstance(e, Imp) else "EQV")))
            )
            metrics["pair_collapses"] = metrics.get("pair_collapses", 0) + 1
            return _Pair(a.xl, a.xr, cm_compose(a.tok, b.tok, op))
        return _fallback_compile(e, R, C, fixed, diagnostics, materialize_mode, hybrid_threshold)

    if isinstance(e, Var):
        return _fallback_compile(e, R, C, fixed, diagnostics, materialize_mode, hybrid_threshold)

    raise TypeError(f"Unknown node {type(e)}")


def compile_expr_to_cm_pair(
    e: Expr,
    R: List[str],
    C: List[str],
    fixed: Dict[str, int],
    *,
    diagnostics: Optional[Dict[str, int]] = None,
    materialize_mode: str = "partial_hybrid",
    hybrid_threshold: int = 7,
) -> Tuple[np.ndarray, Dict[str, float]]:
    metrics: Dict[str, int] = {}
    res = _compile_pair(
        e,
        R,
        C,
        fixed,
        metrics,
        diagnostics,
        materialize_mode,
        hybrid_threshold,
    )
    if isinstance(res, _Pair):
        Ms = _token_to_matrix(res.tok)
        M = lift_cm(Ms, vars_rows=[res.xl], vars_cols=[res.xr], R=R, C=C, fixed=fixed)
    else:
        M = res
    attempts = int(metrics.get("pair_attempts", 0))
    collapses = int(metrics.get("pair_collapses", 0))
    total = int(metrics.get("nodes_total", 0))
    ratio = (collapses / attempts) if attempts > 0 else 0.0
    return M, {
        "pair_attempts": attempts,
        "pair_collapses": collapses,
        "pairable_ratio": ratio,
        "nodes_total": total,
    }


__all__ = ["compile_expr_to_cm_pair"]

