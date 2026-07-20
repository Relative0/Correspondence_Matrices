from __future__ import annotations

import time
from typing import Any, Dict, Optional

from bitset_backend import build_bitset_env, eval_expr_bitset


def bitset_equivalence_check(expr_f: Any, expr_g: Any, n: int, *, expected: Optional[bool] = None) -> Dict[str, Any]:
    try:
        env = build_bitset_env([f"x{i}" for i in range(n)])
        t0 = time.perf_counter()
        bits_f = eval_expr_bitset(expr_f, env)
        eval_f = time.perf_counter() - t0
        t1 = time.perf_counter()
        bits_g = eval_expr_bitset(expr_g, env)
        eval_g = time.perf_counter() - t1
        t2 = time.perf_counter()
        result = int(bits_f) == int(bits_g)
        compare_time = time.perf_counter() - t2
        total_eval = eval_f + eval_g
        return {
            "bitset_equiv_eval_f_time_s": eval_f,
            "bitset_equiv_eval_g_time_s": eval_g,
            "bitset_equiv_eval_total_time_s": total_eval,
            "bitset_equiv_compare_time_s": compare_time,
            "bitset_equiv_total_time_s": total_eval + compare_time,
            "bitset_equiv_result": bool(result),
            "bitset_equiv_ok": (bool(result) == bool(expected)) if expected is not None else None,
            "bitset_equiv_status": "ok",
            "bitset_equiv_error": None,
        }
    except Exception as exc:
        return {
            "bitset_equiv_eval_f_time_s": None,
            "bitset_equiv_eval_g_time_s": None,
            "bitset_equiv_eval_total_time_s": None,
            "bitset_equiv_compare_time_s": None,
            "bitset_equiv_total_time_s": None,
            "bitset_equiv_result": None,
            "bitset_equiv_ok": None,
            "bitset_equiv_status": "error",
            "bitset_equiv_error": repr(exc),
        }
