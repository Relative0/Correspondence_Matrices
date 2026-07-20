from __future__ import annotations

import hashlib
import statistics
from typing import Any, Dict, List, Mapping, Tuple

import numpy as np

from cmbench.expr.diagnostics import expr_complexity_diagnostics
from cmbench.expr.generators import random_expr_for_style
from cmbench.expr.visitors import collect_subtree_hashes_fast
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import expr_structural_hash


def _expr_children(expr: Any) -> Tuple[Any, ...]:
    if isinstance(expr, Var):
        return ()
    if isinstance(expr, Not):
        return (expr.a,)
    if isinstance(expr, (And, Or, Xor, Imp, Eqv)):
        return (expr.a, expr.b)
    raise TypeError(expr)

def _expr_with_children(expr: Any, children: Tuple[Any, ...]) -> Any:
    if isinstance(expr, Var):
        return expr
    if isinstance(expr, Not):
        return Not(children[0])
    if isinstance(expr, And):
        return And(children[0], children[1])
    if isinstance(expr, Or):
        return Or(children[0], children[1])
    if isinstance(expr, Xor):
        return Xor(children[0], children[1])
    if isinstance(expr, Imp):
        return Imp(children[0], children[1])
    if isinstance(expr, Eqv):
        return Eqv(children[0], children[1])
    raise TypeError(expr)

def _expr_paths(expr: Any) -> List[Tuple[int, ...]]:
    paths: List[Tuple[int, ...]] = []

    def rec(e: Any, path: Tuple[int, ...]) -> None:
        paths.append(path)
        for i, child in enumerate(_expr_children(e)):
            rec(child, path + (i,))

    rec(expr, ())
    return paths

def _expr_get_subtree(expr: Any, path: Tuple[int, ...]) -> Any:
    cur = expr
    for idx in path:
        cur = _expr_children(cur)[idx]
    return cur

def _expr_replace_subtree(expr: Any, path: Tuple[int, ...], replacement: Any) -> Any:
    if not path:
        return replacement
    children = list(_expr_children(expr))
    idx = path[0]
    children[idx] = _expr_replace_subtree(children[idx], path[1:], replacement)
    return _expr_with_children(expr, tuple(children))

def _const_expr(n_vars: int, value: int) -> Any:
    v = Var(0 if n_vars <= 0 else int(n_vars - 1))
    return Or(v, Not(v)) if int(value) else And(v, Not(v))

def substitute_variables_with_constants(expr: Any, n_vars: int, fixed: Mapping[int, int]) -> Any:
    if isinstance(expr, Var):
        if int(expr.i) in fixed:
            return _const_expr(n_vars, int(fixed[int(expr.i)]))
        return expr
    children = tuple(substitute_variables_with_constants(c, n_vars, fixed) for c in _expr_children(expr))
    return _expr_with_children(expr, children)

def collect_subtree_hashes(expr: Any) -> List[str]:
    hashes: List[str] = []
    for path in _expr_paths(expr):
        try:
            hashes.append(expr_structural_hash(_expr_get_subtree(expr, path)))
        except Exception:
            hashes.append(hashlib.sha256(repr(_expr_get_subtree(expr, path)).encode("utf-8")).hexdigest())
    return hashes

def _family_op_for_index(i: int):
    return (And, Or, Xor, Imp, Eqv)[int(i) % 5]

def _small_random_subtree(n_vars: int, rng: np.random.Generator, max_depth: int, style: str) -> Any:
    return random_expr_for_style(n_vars, rng, max_depth=max(0, min(2, int(max_depth))), style=style)

def generate_expression_family(
    n_vars: int,
    rng: np.random.Generator,
    max_depth: int,
    expr_style: str,
    *,
    family_size: int = 50,
    variant_style: str = "composition_mix",
    shared_blocks: int = 4,
    mutation_rate: float = 0.15,
    force_shared_substructure: bool = False,
) -> Dict[str, Any]:
    size = max(1, int(family_size))
    base_depth = max(1, int(max_depth))
    base_expr = random_expr_for_style(n_vars, rng, max_depth=base_depth, style=expr_style)
    block_depth = max(1, base_depth - 1)
    block_count = max(1, int(shared_blocks))
    blocks = [random_expr_for_style(n_vars, rng, max_depth=block_depth, style=expr_style) for _ in range(block_count)]
    if force_shared_substructure:
        seed_block = blocks[0]
        base_expr = And(base_expr, seed_block)

    def subtree_mutation(i: int) -> Any:
        expr = base_expr
        initial_paths = [p for p in _expr_paths(expr) if p]
        n_changes = max(1, int(round(max(0.0, float(mutation_rate)) * max(1, len(initial_paths)))))
        for _ in range(max(1, n_changes)):
            paths = [p for p in _expr_paths(expr) if p]
            if not paths:
                break
            path = paths[int(rng.integers(0, len(paths)))]
            replacement = _small_random_subtree(n_vars, rng, base_depth, expr_style)
            if force_shared_substructure and rng.random() < 0.7:
                replacement = blocks[int(rng.integers(0, len(blocks)))]
            expr = _expr_replace_subtree(expr, path, replacement)
        return expr

    def subtree_wrap(i: int) -> Any:
        h = _small_random_subtree(n_vars, rng, base_depth, expr_style)
        mode = i % 4
        if mode == 0:
            return And(base_expr, h)
        if mode == 1:
            return Or(base_expr, h)
        if mode == 2:
            return Xor(base_expr, h)
        return Or(And(base_expr, h), And(base_expr, Not(h)))

    def partial_substitution(i: int) -> Any:
        k = max(1, min(n_vars, int(round(max(0.0, float(mutation_rate)) * max(1, n_vars)))))
        vars_fixed = rng.choice(np.arange(n_vars), size=k, replace=False) if n_vars > 0 else []
        fixed = {int(v): int((i + j) % 2) for j, v in enumerate(vars_fixed)}
        return substitute_variables_with_constants(base_expr, n_vars, fixed)

    def shared_block_mix(i: int) -> Any:
        b0 = blocks[i % len(blocks)]
        b1 = blocks[(i + 1) % len(blocks)]
        b2 = blocks[(i + 2) % len(blocks)]
        b3 = blocks[(i + 3) % len(blocks)]
        h = _small_random_subtree(n_vars, rng, base_depth, expr_style)
        mode = i % 4
        if mode == 0:
            return Or(And(b0, h), Xor(b1, b2))
        if mode == 1:
            return Or(And(b0, b3), h)
        if mode == 2:
            return Xor(b2, And(b1, h))
        return _family_op_for_index(i)(And(base_expr, b0), Or(b1, h))

    builders = {
        "subtree_mutation": subtree_mutation,
        "subtree_wrap": subtree_wrap,
        "partial_substitution": partial_substitution,
        "shared_block_mix": shared_block_mix,
    }
    variants: List[Any] = []
    for i in range(size):
        if i == 0:
            variants.append(base_expr)
            continue
        style_i = variant_style
        if variant_style == "composition_mix":
            style_i = ("subtree_mutation", "subtree_wrap", "partial_substitution", "shared_block_mix")[i % 4]
        if style_i not in builders:
            raise ValueError(f"unknown family variant style: {variant_style!r}")
        variants.append(builders[style_i](i))
    return {"base_expr": base_expr, "variants": variants, "shared_blocks": blocks}

def expression_family_diagnostics(
    family: Dict[str, Any],
    n_vars: int,
    *,
    family_id: str,
    variant_style: str,
    mutation_rate: float,
) -> Dict[str, Any]:
    base_expr = family["base_expr"]
    variants = list(family["variants"])
    base_diag = expr_complexity_diagnostics(base_expr, n_vars)
    all_hashes: List[str] = []
    repeated_against_base = 0
    base_hashes = set(collect_subtree_hashes_fast(base_expr))
    variant_node_counts: List[int] = []
    variant_var_counts: List[int] = []
    variant_hashes: List[str] = []
    for expr in variants:
        diag = expr_complexity_diagnostics(expr, n_vars)
        variant_node_counts.append(int(diag["expr_node_count"]))
        variant_var_counts.append(int(diag["expr_unique_var_count"]))
        variant_hashes.append(str(diag["expr_structural_hash_if_available"]))
        hs = collect_subtree_hashes_fast(expr)
        all_hashes.extend(hs)
        repeated_against_base += sum(1 for h in hs if h in base_hashes)
    counts: Dict[str, int] = {}
    for h in all_hashes:
        counts[h] = counts.get(h, 0) + 1
    total = len(all_hashes)
    unique = len(counts)
    repeated = sum(1 for v in counts.values() if v > 1)
    return {
        "family_id": family_id,
        "family_size": int(len(variants)),
        "family_variant_style": variant_style,
        "family_base_expr_node_count": int(base_diag["expr_node_count"]),
        "family_variant_expr_node_count_median": float(statistics.median(variant_node_counts)) if variant_node_counts else None,
        "family_variant_expr_node_count_max": int(max(variant_node_counts)) if variant_node_counts else None,
        "family_base_unique_var_count": int(base_diag["expr_unique_var_count"]),
        "family_variant_unique_var_count_median": float(statistics.median(variant_var_counts)) if variant_var_counts else None,
        "family_pair_structural_similarity_estimate": float(repeated_against_base / total) if total else None,
        "family_variant_structural_hashes": ";".join(variant_hashes),
        "family_base_structural_hash": str(base_diag["expr_structural_hash_if_available"]),
        "family_shared_block_count": int(len(family.get("shared_blocks", []))),
        "family_mutation_rate": float(mutation_rate),
        "family_expected_shared_structure_level": (
            "high" if variant_style in ("shared_block_mix", "composition_mix") else "medium"
        ),
        "family_total_subtree_hashes": int(total),
        "family_unique_subtree_hashes": int(unique),
        "family_reuse_ratio": float((total - unique) / total) if total else None,
        "family_repeated_subtree_hash_count": int(repeated),
        "family_max_subtree_reuse_count": int(max(counts.values())) if counts else 0,
    }
