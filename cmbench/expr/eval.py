from __future__ import annotations

from typing import Any, Dict, Mapping

import numpy as np

from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor


def eval_expr_assignment(expr, assignment: Mapping[str, int]) -> int:
    if isinstance(expr, Var):
        return int(bool(assignment[f"x{expr.i}"]))
    if isinstance(expr, Not):
        return 1 - eval_expr_assignment(expr.a, assignment)
    if isinstance(expr, And):
        return eval_expr_assignment(expr.a, assignment) & eval_expr_assignment(expr.b, assignment)
    if isinstance(expr, Or):
        return eval_expr_assignment(expr.a, assignment) | eval_expr_assignment(expr.b, assignment)
    if isinstance(expr, Xor):
        return eval_expr_assignment(expr.a, assignment) ^ eval_expr_assignment(expr.b, assignment)
    if isinstance(expr, Imp):
        return (1 - eval_expr_assignment(expr.a, assignment)) | eval_expr_assignment(expr.b, assignment)
    if isinstance(expr, Eqv):
        return 1 - (eval_expr_assignment(expr.a, assignment) ^ eval_expr_assignment(expr.b, assignment))
    raise TypeError(expr)

def result_value_for_assignment(res, assignment: Mapping[str, int]) -> int:
    idx = 0
    for name in res.output_vars:
        idx = (idx << 1) | int(bool(assignment[name]))
    if res.bits is not None:
        return (int(res.bits) >> idx) & 1
    if res.tt is not None:
        return int(res.tt[idx])
    raise ValueError("no result payload available for sampled correctness")

def sampled_correctness_check(expr, res, n: int, samples: int, rng: np.random.Generator) -> Dict[str, Any]:
    if samples <= 0:
        return {
            "sampled_correctness_samples": 0,
            "sampled_correctness_mismatches": None,
            "sampled_correctness_mismatch_rate": None,
        }
    mismatches = 0
    names = [f"x{i}" for i in range(n)]
    for _ in range(samples):
        vals = rng.integers(0, 2, size=n, dtype=np.uint8)
        assignment = {name: int(vals[i]) for i, name in enumerate(names)}
        expected = eval_expr_assignment(expr, assignment)
        actual = result_value_for_assignment(res, assignment)
        if expected != actual:
            mismatches += 1
    return {
        "sampled_correctness_samples": int(samples),
        "sampled_correctness_mismatches": int(mismatches),
        "sampled_correctness_mismatch_rate": float(mismatches / samples),
    }
