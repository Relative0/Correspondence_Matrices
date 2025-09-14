
"""
cm_build.py
Compile cm_exprlib expressions into canonical correspondence matrices using cm_normalize.
"""
from typing import Tuple, Dict, List, Set
import numpy as np

from cm_normalize import canonical_layout, lift_cm, combine_pointwise
from cm_exprlib import Var, Not, And, Or, Xor, Imp, Eqv


def _var_name(v: Var) -> str:
    # Support Var with .name (string) or .i (index -> x{i})
    if hasattr(v, "name") and isinstance(getattr(v, "name"), str):
        return getattr(v, "name")
    if hasattr(v, "i"):
        vi = getattr(v, "i")
        if isinstance(vi, int):
            return f"x{vi}"
        if isinstance(vi, str):
            return vi if vi.startswith("x") else f"x{vi}"
    raise AttributeError("Var node must have .name or .i")


def expr_vars(e) -> List[str]:
    vs: Set[str] = set()
    def rec(z):
        if isinstance(z, Var):
            vs.add(_var_name(z))
        elif isinstance(z, Not):
            rec(z.a)
        elif isinstance(z, (And, Or, Xor, Imp, Eqv)):
            rec(z.a); rec(z.b)
        else:
            raise TypeError(f"Unknown node {type(z)}")
    rec(e)
    return sorted(vs)


def _compile_leaf_var(vname: str, R: List[str], C: List[str], fixed: Dict[str,int]) -> np.ndarray:
    if vname in R and vname in C: raise ValueError(f"Variable {vname} cannot be in both R and C")
    if vname in R:
        # rows indexed as [v=0, v=1] so index matches bit value
        Ms = np.array([[0],[1]], dtype=np.uint8)
        return lift_cm(Ms, vars_rows=[vname], vars_cols=[], R=R, C=C, fixed=fixed)
    elif vname in C:
        # cols indexed as [v=0, v=1] so index matches bit value
        Ms = np.array([[0,1]], dtype=np.uint8)
        return lift_cm(Ms, vars_rows=[], vars_cols=[vname], R=R, C=C, fixed=fixed)
    else:
        b = fixed.get(vname, 1)
        Ms = np.array([[b]], dtype=np.uint8)      # 1x1 constant
        return lift_cm(Ms, vars_rows=[], vars_cols=[], R=R, C=C, fixed=fixed)


def _compile(e, R: List[str], C: List[str], fixed: Dict[str,int]) -> np.ndarray:
    if isinstance(e, Var):
        return _compile_leaf_var(_var_name(e), R, C, fixed)
    if isinstance(e, Not):
        return (1 - _compile(e.a, R, C, fixed)).astype(np.uint8)
    if isinstance(e, (And, Or, Xor, Imp, Eqv)):
        M1 = _compile(e.a, R, C, fixed); M2 = _compile(e.b, R, C, fixed)
        if isinstance(e, And): return combine_pointwise(M1, M2, "AND")
        if isinstance(e, Or):  return combine_pointwise(M1, M2, "OR")
        if isinstance(e, Xor): return combine_pointwise(M1, M2, "XOR")
        if isinstance(e, Imp): return combine_pointwise(M1, M2, "IMP")
        if isinstance(e, Eqv): return combine_pointwise(M1, M2, "EQV")
    raise TypeError(f"Unknown node {type(e)}")


def compile_expr_to_cm(e, R: List[str], C: List[str], fixed: Dict[str,int]) -> np.ndarray:
    return _compile(e, R, C, fixed)


def eval_cm_boolean(M: np.ndarray, R: List[str], C: List[str], assignment: Dict[str,int], fixed: Dict[str,int]) -> int:
    r = 0
    for v in R:
        b = assignment.get(v, fixed.get(v, 0))
        r = (r<<1) | int(b)
    c = 0
    for v in C:
        b = assignment.get(v, fixed.get(v, 0))
        c = (c<<1) | int(b)
    return int(M[r, c] & 1)
