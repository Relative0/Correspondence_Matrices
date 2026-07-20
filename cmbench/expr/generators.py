from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np

from cmbench.config import BenchmarkConfig
from cmbench.expr.diagnostics import expr_complexity_diagnostics, truth_table_diagnostics
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, eval_expr_tt, random_expr


def _default_config(n_vars: int, max_depth: int) -> BenchmarkConfig:
    return BenchmarkConfig(sizes=(int(n_vars),), trials=1, seed=0, max_depth=int(max_depth))


def random_expr_broad(n_vars: int, rng: np.random.Generator, max_depth: int = 3) -> Any:
    """Generate a broader tree with more distinct leaves before reuse."""
    counter = [0]

    def leaf() -> Var:
        i = counter[0] % n_vars
        counter[0] += 1
        return Var(i)

    def rec(depth: int):
        if depth <= 0:
            return leaf()
        op = rng.choice((And, Or, Xor, Imp, Eqv))
        left = rec(depth - 1)
        right = rec(depth - 1)
        if rng.random() < 0.15:
            left = Not(left)
        if rng.random() < 0.15:
            right = Not(right)
        return op(left, right)

    return rec(max_depth)

def random_expr_low_reuse(n_vars: int, rng: np.random.Generator, max_depth: int = 3) -> Any:
    """Generate a low-reuse tree with shuffled variable order and mostly non-idempotent ops."""
    leaves = list(range(n_vars))
    rng.shuffle(leaves)
    pos = [0]

    def leaf() -> Var:
        v = leaves[pos[0] % len(leaves)]
        pos[0] += 1
        return Var(int(v))

    def rec(depth: int):
        if depth <= 0:
            return leaf()
        op = rng.choice((Xor, Imp, Eqv, And, Or), p=(0.26, 0.24, 0.24, 0.13, 0.13))
        a = rec(depth - 1)
        b = rec(depth - 1)
        if rng.random() < 0.25:
            a = Not(a)
        return op(a, b)

    return rec(max_depth)

def _maybe_not(expr, rng: np.random.Generator, p: float = 0.15):
    return Not(expr) if rng.random() < p else expr

def random_expr_balanced_all_vars(n_vars: int, rng: np.random.Generator, max_depth: int = 3) -> Any:
    """Generate a balanced tree that includes every variable at least once."""
    leaves = [Var(i) for i in range(n_vars)]
    target_leaves = max(n_vars, 1 << max(0, min(max_depth, 12)))
    while len(leaves) < target_leaves:
        leaves.append(Var(int(rng.integers(0, n_vars))))
    rng.shuffle(leaves)
    level: List[Any] = [_maybe_not(e, rng, 0.10) for e in leaves]
    ops = (And, Or, Xor, Imp, Eqv)
    while len(level) > 1:
        next_level: List[Any] = []
        for i in range(0, len(level), 2):
            if i + 1 >= len(level):
                next_level.append(level[i])
                continue
            op = rng.choice(ops)
            next_level.append(op(level[i], level[i + 1]))
        level = next_level
    return level[0]

def random_expr_xor_heavy(n_vars: int, rng: np.random.Generator, max_depth: int = 3) -> Any:
    leaves = list(range(n_vars))
    rng.shuffle(leaves)
    pos = [0]

    def leaf() -> Var:
        v = leaves[pos[0] % len(leaves)]
        pos[0] += 1
        return Var(int(v))

    def rec(depth: int):
        if depth <= 0:
            return _maybe_not(leaf(), rng, 0.08)
        op = rng.choice((Xor, Eqv, And, Or), p=(0.62, 0.18, 0.10, 0.10))
        return op(rec(depth - 1), rec(depth - 1))

    return rec(max_depth)

def random_expr_and_or_not(n_vars: int, rng: np.random.Generator, max_depth: int = 3) -> Any:
    def rec(depth: int):
        if depth <= 0:
            return Var(int(rng.integers(0, n_vars)))
        if rng.random() < 0.22:
            return Not(rec(depth - 1))
        op = rng.choice((And, Or))
        return op(rec(depth - 1), rec(depth - 1))

    return rec(max_depth)

def random_expr_implication_heavy(n_vars: int, rng: np.random.Generator, max_depth: int = 3) -> Any:
    leaves = list(range(n_vars))
    rng.shuffle(leaves)
    pos = [0]

    def leaf() -> Var:
        if pos[0] < len(leaves):
            v = leaves[pos[0]]
        else:
            v = int(rng.integers(0, n_vars))
        pos[0] += 1
        return Var(int(v))

    def rec(depth: int):
        if depth <= 0:
            return _maybe_not(leaf(), rng, 0.10)
        op = rng.choice((Imp, And, Or, Eqv, Xor), p=(0.55, 0.17, 0.17, 0.08, 0.03))
        left = rec(depth - 1)
        right = rec(depth - 1)
        if rng.random() < 0.18:
            left = Not(left)
        return op(left, right)

    return rec(max_depth)

def random_expr_mixed_no_constants(n_vars: int, rng: np.random.Generator, max_depth: int = 3) -> Any:
    leaves = list(range(n_vars))
    rng.shuffle(leaves)
    pos = [0]

    def leaf() -> Var:
        if pos[0] < len(leaves):
            v = leaves[pos[0]]
        else:
            v = int(rng.integers(0, n_vars))
        pos[0] += 1
        return Var(int(v))

    def rec(depth: int):
        if depth <= 0:
            return _maybe_not(leaf(), rng, 0.12)
        op = rng.choice((And, Or, Xor, Imp, Eqv))
        return op(rec(depth - 1), rec(depth - 1))

    return rec(max_depth)

def random_expr_for_style(n_vars: int, rng: np.random.Generator, max_depth: int, style: str):
    if style == "ordinary":
        return random_expr(n_vars, rng, max_depth=max_depth, p_unary=0.25)
    if style == "broad":
        return random_expr_broad(n_vars, rng, max_depth=max_depth)
    if style == "low-reuse":
        return random_expr_low_reuse(n_vars, rng, max_depth=max_depth)
    if style == "anti-reduction":
        return random_expr_low_reuse(n_vars, rng, max_depth=max_depth)
    if style == "balanced_all_vars":
        return random_expr_balanced_all_vars(n_vars, rng, max_depth=max_depth)
    if style == "xor_heavy":
        return random_expr_xor_heavy(n_vars, rng, max_depth=max_depth)
    if style == "and_or_not":
        return random_expr_and_or_not(n_vars, rng, max_depth=max_depth)
    if style == "implication_heavy":
        return random_expr_implication_heavy(n_vars, rng, max_depth=max_depth)
    if style == "mixed_no_constants":
        return random_expr_mixed_no_constants(n_vars, rng, max_depth=max_depth)
    if style == "transform_pairs":
        return random_expr_implication_heavy(n_vars, rng, max_depth=max_depth)
    raise ValueError(f"unknown expression style: {style!r}")

def expression_filter_reason(
    expr_diag: Mapping[str, Any],
    tt_diag: Mapping[str, Any],
    n_vars: int,
    max_depth: int,
    config: Optional[BenchmarkConfig] = None,
) -> str:
    config = config or _default_config(n_vars, max_depth)
    min_used = float(config.min_used_var_fraction if config is not None else 0.75)
    min_density = float(config.min_tt_density if config is not None else 0.05)
    max_density = float(config.max_tt_density if config is not None else 0.95)
    used_fraction = float(expr_diag.get("expr_unique_var_count") or 0) / float(max(1, n_vars))
    if used_fraction < min_used:
        return "too_few_vars"
    shallow_threshold = max(1, min(max_depth, 3))
    if int(expr_diag.get("expr_depth_actual") or 0) < shallow_threshold:
        return "too_shallow"
    tt_is_constant = tt_diag.get("tt_is_constant")
    if tt_is_constant is True:
        return "constant_tt"
    density = tt_diag.get("tt_density")
    if density is not None:
        try:
            d = float(density)
            if d < min_density:
                return "tt_density_too_low"
            if d > max_density:
                return "tt_density_too_high"
        except Exception:
            pass
    return ""

def generate_benchmark_expr(
    n_vars: int,
    rng: np.random.Generator,
    max_depth: int,
    style: str,
    build_tt: bool,
    config: Optional[BenchmarkConfig] = None,
    return_tt_ref: bool = False,
) -> Tuple[Any, Dict[str, Any]] | Tuple[Any, Dict[str, Any], Optional[np.ndarray]]:
    config = config or _default_config(n_vars, max_depth)
    attempts_limit = max(
        1,
        int(config.max_expr_regeneration_attempts if config is not None else 100),
    )
    require_nontrivial = bool(config.require_nontrivial_expr if config is not None else False)
    attempts = 0
    last_reason = ""
    while True:
        attempts += 1
        expr = random_expr_for_style(n_vars, rng, max_depth=max_depth, style=style)
        expr_diag = expr_complexity_diagnostics(expr, n_vars)
        tt_ref = eval_expr_tt(expr, n_vars).astype(np.uint8).reshape(-1) if build_tt else None
        tt_diag = truth_table_diagnostics(tt_ref)
        if tt_ref is not None:
            expr_diag["expr_simplified_const_if_available"] = tt_diag["tt_is_constant"]
        reason = expression_filter_reason(expr_diag, tt_diag, n_vars, max_depth, config=config) if require_nontrivial else ""
        last_reason = reason
        if (not require_nontrivial) or reason == "" or attempts >= attempts_limit:
            diag = {
                **expr_diag,
                **tt_diag,
                "expr_regeneration_attempts": int(attempts - 1),
                "expr_filter_reason": reason,
            }
            if require_nontrivial and reason != "" and attempts >= attempts_limit:
                diag["expr_filter_reason"] = f"max_attempts:{last_reason}"
            if return_tt_ref:
                return expr, diag, tt_ref
            return expr, diag
