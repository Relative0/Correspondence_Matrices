from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from bitset_backend import bitset_to_bool_array
from cmbench.expr.diagnostics import _expr_used_indices, expr_complexity_diagnostics
from cmbench.expr.generators import random_expr_for_style
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor


def _rewrite_equiv_expr(expr, rng: np.random.Generator):
    if isinstance(expr, Var):
        return Not(Not(expr))
    if isinstance(expr, Not):
        return Not(_rewrite_equiv_expr(expr.a, rng))
    if isinstance(expr, And):
        a = _rewrite_equiv_expr(expr.a, rng)
        b = _rewrite_equiv_expr(expr.b, rng)
        return And(b, a) if rng.random() < 0.5 else And(a, b)
    if isinstance(expr, Or):
        a = _rewrite_equiv_expr(expr.a, rng)
        b = _rewrite_equiv_expr(expr.b, rng)
        return Or(b, a) if rng.random() < 0.5 else Or(a, b)
    if isinstance(expr, Xor):
        a = _rewrite_equiv_expr(expr.a, rng)
        b = _rewrite_equiv_expr(expr.b, rng)
        return Xor(b, a) if rng.random() < 0.5 else Xor(a, b)
    if isinstance(expr, Eqv):
        a = _rewrite_equiv_expr(expr.a, rng)
        b = _rewrite_equiv_expr(expr.b, rng)
        return Eqv(b, a) if rng.random() < 0.5 else Eqv(a, b)
    if isinstance(expr, Imp):
        return Or(Not(_rewrite_equiv_expr(expr.a, rng)), _rewrite_equiv_expr(expr.b, rng))
    raise TypeError(expr)

def generate_equiv_pair(expr_f, n_vars: int, rng: np.random.Generator, max_depth: int, expr_style: str, pair_style: str):
    if pair_style == "identical":
        return expr_f, True
    if pair_style == "rewritten_equiv":
        return _rewrite_equiv_expr(expr_f, rng), True
    if pair_style == "semantic_equiv":
        h = Var(int(rng.integers(0, max(1, n_vars))))
        return Or(And(expr_f, h), And(expr_f, Not(h))), True
    if pair_style == "near_miss":
        used = _expr_used_indices(expr_f)
        idx = used[0] if used else int(rng.integers(0, max(1, n_vars)))
        return Xor(expr_f, Var(idx)), False
    if pair_style == "random_independent":
        return random_expr_for_style(n_vars, rng, max_depth=max_depth, style=expr_style), None
    raise ValueError(f"unknown equivalence pair style: {pair_style!r}")

def pair_diagnostics(expr_f, expr_g, n_vars: int, pair_style: str, expected: Optional[bool]) -> Dict[str, Any]:
    diag_f = expr_complexity_diagnostics(expr_f, n_vars)
    diag_g = expr_complexity_diagnostics(expr_g, n_vars)
    used = set(_expr_used_indices(expr_f)) | set(_expr_used_indices(expr_g))
    out: Dict[str, Any] = {
        "equiv_pair_style": pair_style,
        "equiv_expected": expected,
        "expr_pair_unique_var_count": int(len(used)),
        "expr_pair_uses_all_vars": bool(len(used) == n_vars),
    }
    for src, prefix in ((diag_f, "expr_f"), (diag_g, "expr_g")):
        out[f"{prefix}_depth"] = src["expr_depth_actual"]
        out[f"{prefix}_node_count"] = src["expr_node_count"]
        out[f"{prefix}_unique_var_count"] = src["expr_unique_var_count"]
        out[f"{prefix}_structural_hash_if_available"] = src["expr_structural_hash_if_available"]
    return out

def _no_reinflate_payload_equal(res_f, res_g) -> bool:
    if tuple(res_f.output_vars) != tuple(res_g.output_vars):
        raise ValueError("cannot compare CM no-reinflate results with different output variable orders")
    if res_f.bits is not None and res_g.bits is not None:
        return int(res_f.bits) == int(res_g.bits)
    if res_f.tt is not None and res_g.tt is not None:
        return bool(np.array_equal(res_f.tt, res_g.tt))
    if res_f.bits is not None and res_g.tt is not None:
        return bool(np.array_equal(bitset_to_bool_array(int(res_f.bits), len(res_f.output_vars)), res_g.tt))
    if res_f.tt is not None and res_g.bits is not None:
        return bool(np.array_equal(res_f.tt, bitset_to_bool_array(int(res_g.bits), len(res_g.output_vars))))
    raise ValueError("missing CM no-reinflate payload")
