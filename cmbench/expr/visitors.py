from __future__ import annotations

import hashlib
from typing import Any

from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import expr_structural_hash


def expr_children(expr: Any) -> tuple[Any, ...]:
    if isinstance(expr, Var):
        return ()
    if isinstance(expr, Not):
        return (expr.a,)
    if isinstance(expr, (And, Or, Xor, Imp, Eqv)):
        return (expr.a, expr.b)
    raise TypeError(expr)


def _hash_expr(expr: Any) -> str:
    try:
        return expr_structural_hash(expr)
    except Exception:
        return hashlib.sha256(repr(expr).encode("utf-8")).hexdigest()


def collect_subtree_hashes_fast(expr: Any) -> list[str]:
    hashes: list[str] = []

    def rec(cur: Any) -> None:
        hashes.append(_hash_expr(cur))
        for child in expr_children(cur):
            rec(child)

    rec(expr)
    return hashes

