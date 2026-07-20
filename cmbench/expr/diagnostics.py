from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import expr_structural_hash


def expr_complexity_diagnostics(expr, n_vars: int) -> Dict[str, Any]:
    counts = {
        "var": 0,
        "const": 0,
        "not": 0,
        "and": 0,
        "or": 0,
        "xor": 0,
        "imp": 0,
        "eqv": 0,
    }
    used = set()

    def rec(e) -> Tuple[int, int, int]:
        if isinstance(e, Var):
            counts["var"] += 1
            used.add(int(e.i))
            return 1, 1, 1
        if isinstance(e, Not):
            counts["not"] += 1
            child_depth, child_nodes, child_leaves = rec(e.a)
            return child_depth + 1, child_nodes + 1, child_leaves
        if isinstance(e, (And, Or, Xor, Imp, Eqv)):
            if isinstance(e, And):
                counts["and"] += 1
            elif isinstance(e, Or):
                counts["or"] += 1
            elif isinstance(e, Xor):
                counts["xor"] += 1
            elif isinstance(e, Imp):
                counts["imp"] += 1
            else:
                counts["eqv"] += 1
            da, na, la = rec(e.a)
            db, nb, lb = rec(e.b)
            return max(da, db) + 1, na + nb + 1, la + lb
        raise TypeError(e)

    depth, nodes, leaves = rec(expr)
    used_list = [f"x{i}" for i in sorted(used)]
    op_count = counts["not"] + counts["and"] + counts["or"] + counts["xor"] + counts["imp"] + counts["eqv"]
    try:
        structural_hash = expr_structural_hash(expr)
    except Exception:
        structural_hash = hashlib.sha256(repr(expr).encode("utf-8")).hexdigest()
    return {
        "expr_depth_actual": int(depth),
        "expr_node_count": int(nodes),
        "expr_leaf_count": int(leaves),
        "expr_op_count": int(op_count),
        "expr_unique_var_count": int(len(used)),
        "expr_vars_used": ";".join(used_list),
        "expr_vars_used_count": int(len(used)),
        "expr_vars_used_list": ";".join(used_list),
        "expr_uses_all_vars": bool(len(used) == n_vars),
        "expr_const_count": int(counts["const"]),
        "expr_not_count": int(counts["not"]),
        "expr_and_count": int(counts["and"]),
        "expr_or_count": int(counts["or"]),
        "expr_xor_count": int(counts["xor"]),
        "expr_imp_count": int(counts["imp"]),
        "expr_eqv_count": int(counts["eqv"]),
        "expr_simplified_const_if_available": None,
        "expr_structural_hash_if_available": structural_hash,
    }

def truth_table_diagnostics(tt_ref: Optional[np.ndarray]) -> Dict[str, Any]:
    if tt_ref is None:
        return {
            "tt_true_count": None,
            "tt_false_count": None,
            "tt_density": None,
            "tt_is_constant": None,
            "tt_is_balancedish": None,
        }
    total = int(tt_ref.size)
    true_count = int(np.count_nonzero(tt_ref))
    false_count = total - true_count
    density = float(true_count / total) if total else None
    is_constant = bool(true_count == 0 or true_count == total)
    return {
        "tt_true_count": true_count,
        "tt_false_count": false_count,
        "tt_density": density,
        "tt_is_constant": is_constant,
        "tt_is_balancedish": bool(density is not None and 0.25 <= density <= 0.75),
    }

def _expr_used_indices(expr) -> List[int]:
    used = set()

    def rec(e) -> None:
        if isinstance(e, Var):
            used.add(int(e.i))
            return
        if isinstance(e, Not):
            rec(e.a)
            return
        if isinstance(e, (And, Or, Xor, Imp, Eqv)):
            rec(e.a)
            rec(e.b)
            return
        raise TypeError(e)

    rec(expr)
    return sorted(used)
