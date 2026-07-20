from __future__ import annotations

import statistics
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

from bitset_backend import bitset_to_bool_array
from cmbench.expr.eval import eval_expr_assignment
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor


def generate_partial_contexts(
    n_vars: int,
    rng: np.random.Generator,
    *,
    context_count: int,
    fixed_var_count: Optional[int] = None,
    fixed_var_fraction: Optional[float] = None,
    style: str = "random_fixed",
) -> List[Dict[str, int]]:
    if style not in ("random_fixed", "block_fixed", "sliding_window", "manufacturing_modes"):
        raise ValueError(f"unknown partial context style: {style!r}")
    count = max(1, int(context_count))
    if fixed_var_count is None:
        frac = 0.5 if fixed_var_fraction is None else float(fixed_var_fraction)
        k = int(round(max(0.0, min(1.0, frac)) * n_vars))
    else:
        k = int(fixed_var_count)
    k = max(0, min(int(n_vars), k))
    names = [f"x{i}" for i in range(n_vars)]
    contexts: List[Dict[str, int]] = []

    if style == "random_fixed":
        for _ in range(count):
            chosen = rng.choice(np.arange(n_vars), size=k, replace=False) if k > 0 else []
            contexts.append({f"x{int(v)}": int(rng.integers(0, 2)) for v in chosen})
        return contexts

    if style == "block_fixed":
        block = max(1, k)
        for i in range(count):
            start = 0 if n_vars == 0 else int((i * block) % max(1, n_vars))
            idxs = [int((start + j) % n_vars) for j in range(k)] if n_vars > 0 else []
            contexts.append({f"x{idx}": int((i + j) % 2) for j, idx in enumerate(idxs)})
        return contexts

    if style == "sliding_window":
        for i in range(count):
            idxs = [int((i + j) % n_vars) for j in range(k)] if n_vars > 0 else []
            contexts.append({f"x{idx}": int(((i // max(1, k)) + j) % 2) for j, idx in enumerate(idxs)})
        return contexts

    # Synthetic manufacturing modes:
    # x0..x(mode_end-1) are mode/configuration variables reused across several contexts;
    # the remaining fixed slots are drawn from sensor/fault/safety variables.
    mode_k = min(k, max(1, n_vars // 4)) if n_vars > 0 and k > 0 else 0
    mode_names = names[:mode_k]
    rest_names = names[mode_k:]
    modes = max(2, min(8, count))
    for i in range(count):
        mode_id = i % modes
        ctx = {name: int((mode_id >> j) & 1) for j, name in enumerate(mode_names)}
        need = max(0, k - len(ctx))
        if need > 0 and rest_names:
            start = (i * max(1, need)) % len(rest_names)
            chosen = [rest_names[(start + j) % len(rest_names)] for j in range(min(need, len(rest_names)))]
            for j, name in enumerate(chosen):
                ctx[name] = int(rng.integers(0, 2) if j % 3 else ((i + j) & 1))
        contexts.append(ctx)
    return contexts

def partial_context_diagnostics(contexts: List[Mapping[str, int]], n_vars: int, style: str) -> Dict[str, Any]:
    fixed_counts = [len(c) for c in contexts]
    remaining = [max(0, int(n_vars) - len(c)) for c in contexts]
    unique_keys = {tuple(sorted((str(k), int(v)) for k, v in c.items())) for c in contexts}
    overlaps: List[float] = []
    for a, b in zip(contexts, contexts[1:]):
        sa = set(a.keys())
        sb = set(b.keys())
        denom = len(sa | sb)
        overlaps.append(float(len(sa & sb) / denom) if denom else 1.0)
    fixed_med = float(statistics.median(fixed_counts)) if fixed_counts else 0.0
    return {
        "partial_context_count": int(len(contexts)),
        "partial_fixed_var_count_median": fixed_med,
        "partial_fixed_var_fraction_median": float(fixed_med / n_vars) if n_vars else 0.0,
        "partial_context_style": style,
        "partial_unique_contexts": int(len(unique_keys)),
        "partial_repeated_contexts": int(len(contexts) - len(unique_keys)),
        "partial_remaining_var_count_median": float(statistics.median(remaining)) if remaining else 0.0,
        "partial_context_overlap_ratio": float(statistics.mean(overlaps)) if overlaps else None,
    }

def _partial_output_vars(n_vars: int, context: Mapping[str, int], output_mode: str) -> List[str]:
    all_vars = [f"x{i}" for i in range(n_vars)]
    if output_mode == "remaining-vars":
        return [v for v in all_vars if v not in context]
    if output_mode == "full-vars":
        return all_vars
    raise ValueError(f"unknown partial output mode: {output_mode!r}")

def _partial_reference_array(expr: Any, n_vars: int, context: Mapping[str, int], output_vars: Sequence[str]) -> np.ndarray:
    out = np.empty(1 << len(output_vars), dtype=np.uint8)
    for idx in range(out.size):
        assignment = {f"x{i}": int(context.get(f"x{i}", 0)) for i in range(n_vars)}
        for j, name in enumerate(output_vars):
            assignment[name] = (idx >> (len(output_vars) - 1 - j)) & 1
        out[idx] = eval_expr_assignment(expr, assignment)
    return out

def _result_to_partial_array(res: Any) -> Optional[np.ndarray]:
    if res is None:
        return None
    if getattr(res, "bits", None) is not None:
        return bitset_to_bool_array(int(res.bits), len(tuple(res.output_vars)))
    tt = getattr(res, "tt", None)
    if tt is not None:
        return np.asarray(tt, dtype=np.uint8).reshape(-1)
    return None

def _eval_expr_bitset_fixed(expr: Any, env: Mapping[str, int], fixed: Mapping[str, int]) -> int:
    n_rows = 1 << len(env)
    full_mask = (1 << n_rows) - 1

    def rec(e: Any) -> int:
        if isinstance(e, Var):
            name = f"x{e.i}"
            if name in fixed:
                return full_mask if int(bool(fixed[name])) else 0
            return int(env[name])
        if isinstance(e, Not):
            return (~rec(e.a)) & full_mask
        if isinstance(e, And):
            return rec(e.a) & rec(e.b)
        if isinstance(e, Or):
            return rec(e.a) | rec(e.b)
        if isinstance(e, Xor):
            return rec(e.a) ^ rec(e.b)
        if isinstance(e, Imp):
            return ((~rec(e.a)) | rec(e.b)) & full_mask
        if isinstance(e, Eqv):
            return (~(rec(e.a) ^ rec(e.b))) & full_mask
        raise TypeError(e)

    return rec(expr)
