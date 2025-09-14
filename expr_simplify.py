#!/usr/bin/env python3
from typing import Any, List
import numpy as np

# Import AST types from cm_exprlib
from cm_exprlib import Var, Not, And, Or, Xor, Imp, Eqv, Expr, eval_expr_tt

# ------------------------------
# SymPy-based simplification
# ------------------------------

def _to_sympy(expr: Expr, n_vars: int):
    import sympy as sp
    xs = [sp.symbols(f"x{i}") for i in range(n_vars)]

    def rec(e: Expr):
        if isinstance(e, Var):
            return xs[e.i]
        if isinstance(e, Not):
            return ~rec(e.a)
        if isinstance(e, And):
            return rec(e.a) & rec(e.b)
        if isinstance(e, Or):
            return rec(e.a) | rec(e.b)
        if isinstance(e, Xor):
            return sp.Xor(rec(e.a), rec(e.b), evaluate=False)
        if isinstance(e, Imp):
            a = rec(e.a); b = rec(e.b)
            return (~a) | b
        if isinstance(e, Eqv):
            a = rec(e.a); b = rec(e.b)
            # equivalence is ~(a ^ b)
            return ~(sp.Xor(a, b, evaluate=False))
        raise TypeError(e)

    return rec(expr)


def simplify_via_sympy(expr: Expr, n_vars: int, form: str = "dnf"):
    """Convert AST to SymPy, run simplify_logic, and return the SymPy expression."""
    import sympy as sp
    sp_expr = _to_sympy(expr, n_vars)
    return sp.simplify_logic(sp_expr, form=form)

# ------------------------------
# BDD→SOP (DNF) baseline (via truth table)
# ------------------------------

def bdd_sop(expr: Expr, n_vars: int) -> str:
    """Produce a DNF (sum-of-products) string equivalent to the expr using its truth table.
    This enumerates on-assignments and renders a canonical (non-minimized) DNF.
    """
    # Evaluate full truth table (vector of length 2^n, dtype uint8)
    tt = eval_expr_tt(expr, n_vars)
    if tt.size == 0:
        return "False"

    # Build minterms for each assignment where function is 1
    cubes: List[str] = []
    for idx, bit in enumerate(tt.tolist()):
        if bit == 0:
            continue
        terms: List[str] = []
        for v in range(n_vars):
            b = (idx >> (n_vars - 1 - v)) & 1
            if b == 1:
                terms.append(f"x{v}")
            else:
                terms.append(f"~x{v}")
        cubes.append(" & ".join(terms))

    if not cubes:
        return "False"
    # Join minterms with OR
    return " | ".join(cubes)
