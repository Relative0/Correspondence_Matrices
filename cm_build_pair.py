"""
cm_build_pair.py

Pair-aware compiler for Correspondence Matrices using 4-bit operator tokens.

Strategy:
- Compile binary operators over signed row/column literals into a common
  positive R/C frame using token transpose and row/column swaps.
- Fuse aligned Pair surrogates at inner nodes through constant-size lookup
  tables (cm_token.cm_compose), without materializing large arrays.
- In the hybrid strategy, retabulate four assignments only for a remaining
  two-variable subtree that cannot be assembled structurally.
- Expose pure-structural, hybrid, whole-root-retabulation, and ordinary-
  fallback outcomes separately.
- Otherwise, fall back to the standard builder.

Returns a token or full CM matrix plus typed provenance and diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Set, Tuple, Union

import numpy as np

from cm_build import compile_expr_to_cm
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cm_normalize import lift_cm
from cm_token import TOK, cm_align_signed_operands, cm_compose, cm_not
from cmbench.output_budget import (
    DEFAULT_OUTPUT_BUDGET,
    OutputBudget,
    decide_output_budget,
    estimate_explicit_output,
    require_output_budget,
)


def _vname(v: Var) -> str:
    name = getattr(v, "name", None)
    if isinstance(name, str):
        return name
    return f"x{int(v.i)}"


def _expr_vars(e: Expr) -> List[str]:
    variables, _ = _expr_vars_and_node_count(e)
    return variables


def _validate_pair_layout(R: List[str], C: List[str]) -> None:
    """Require unambiguous, disjoint row and column variable axes."""
    if len(set(R)) != len(R):
        raise ValueError("row layout R contains duplicate variable names")
    if len(set(C)) != len(C):
        raise ValueError("column layout C contains duplicate variable names")
    overlap = sorted(set(R).intersection(C))
    if overlap:
        joined = ", ".join(overlap)
        raise ValueError(
            "pair compilation requires disjoint row and column layouts; "
            f"overlap: {joined}"
        )


def _expr_stats(e: Expr) -> Tuple[List[str], int, int, int]:
    """Return variables, unfolded occurrences, unique nodes, and AST height.

    The postorder traversal itself is iterative.  Occurrence counts are then
    computed over the identity DAG, so a deeply shared expression does not
    need to be unfolded merely to describe its size.
    """
    postorder: List[Expr] = []
    expanded: Set[int] = set()
    stack: List[Tuple[Expr, bool]] = [(e, False)]
    variables: Set[str] = set()

    while stack:
        node, children_seen = stack.pop()
        node_id = id(node)
        if node_id in expanded:
            continue
        if children_seen:
            expanded.add(node_id)
            postorder.append(node)
            if isinstance(node, Var):
                variables.add(_vname(node))
            continue

        stack.append((node, True))
        if isinstance(node, Var):
            continue
        if isinstance(node, Not):
            stack.append((node.a, False))
            continue
        if isinstance(node, (And, Or, Xor, Imp, Eqv)):
            stack.append((node.b, False))
            stack.append((node.a, False))
            continue
        raise TypeError(f"Unknown node {type(node)}")

    occurrences: Dict[int, int] = {}
    heights: Dict[int, int] = {}
    for node in postorder:
        node_id = id(node)
        if isinstance(node, Var):
            occurrences[node_id] = 1
            heights[node_id] = 1
        elif isinstance(node, Not):
            child_id = id(node.a)
            occurrences[node_id] = 1 + occurrences[child_id]
            heights[node_id] = 1 + heights[child_id]
        else:
            left_id = id(node.a)
            right_id = id(node.b)
            occurrences[node_id] = 1 + occurrences[left_id] + occurrences[right_id]
            heights[node_id] = 1 + max(heights[left_id], heights[right_id])

    root_id = id(e)
    return sorted(variables), occurrences[root_id], len(postorder), heights[root_id]


def _expr_vars_and_node_count(e: Expr) -> Tuple[List[str], int]:
    variables, occurrences, _unique_nodes, _height = _expr_stats(e)
    return variables, occurrences


def _eval_expr_bool(e: Expr, env: Dict[str, int], fixed: Dict[str, int]) -> int:
    if isinstance(e, Var):
        name = _vname(e)
        if name in env:
            return int(bool(env[name]))
        if name in fixed:
            return int(bool(fixed[name]))
        raise KeyError(f"missing live/fixed value for variable {name!r}")
    if isinstance(e, Not):
        return 1 - _eval_expr_bool(e.a, env, fixed)
    if isinstance(e, And):
        return _eval_expr_bool(e.a, env, fixed) & _eval_expr_bool(e.b, env, fixed)
    if isinstance(e, Or):
        return _eval_expr_bool(e.a, env, fixed) | _eval_expr_bool(e.b, env, fixed)
    if isinstance(e, Xor):
        return _eval_expr_bool(e.a, env, fixed) ^ _eval_expr_bool(e.b, env, fixed)
    if isinstance(e, Imp):
        a = _eval_expr_bool(e.a, env, fixed)
        b = _eval_expr_bool(e.b, env, fixed)
        return (1 - a) | b
    if isinstance(e, Eqv):
        a = _eval_expr_bool(e.a, env, fixed)
        b = _eval_expr_bool(e.b, env, fixed)
        return 1 - (a ^ b)
    raise TypeError(e)


def _token_from_expr_two_vars(e: Expr, xl: str, xr: str, fixed: Dict[str, int]) -> int:
    # Bit layout: (11)<<3 | (12)<<2 | (21)<<1 | (22)<<0
    bits = 0
    if _eval_expr_bool(e, {xl: 1, xr: 1}, fixed):
        bits |= (1 << 3)
    if _eval_expr_bool(e, {xl: 1, xr: 0}, fixed):
        bits |= (1 << 2)
    if _eval_expr_bool(e, {xl: 0, xr: 1}, fixed):
        bits |= (1 << 1)
    if _eval_expr_bool(e, {xl: 0, xr: 0}, fixed):
        bits |= (1 << 0)
    return bits


def _token_to_matrix(tok: int) -> np.ndarray:
    # Token layout: [b11 b12 b21 b22]. Our 2x2 convention here is:
    # [[b22, b21],
    #  [b12, b11]]
    b11 = (tok >> 3) & 1
    b12 = (tok >> 2) & 1
    b21 = (tok >> 1) & 1
    b22 = tok & 1
    return np.array([[b22, b21], [b12, b11]], dtype=np.uint8)


@dataclass(frozen=True)
class _Pair:
    xl: str
    xr: str
    tok: int
    structural_steps: bool
    retabulated_subtrees: int


@dataclass(frozen=True)
class CompiledPairToken:
    """Public token-only artifact for one canonical row/column variable pair."""

    row_variable: str
    column_variable: str
    token: int


def _signed_literal(
    e: Expr,
    metrics: Optional[Dict[str, int]] = None,
) -> Optional[Tuple[str, bool]]:
    negated = False
    while isinstance(e, Not):
        if metrics is not None:
            metrics["negation_nodes_scanned"] = (
                metrics.get("negation_nodes_scanned", 0) + 1
            )
        negated = not negated
        e = e.a
    if not isinstance(e, Var):
        return None
    return _vname(e), negated


def _binary_op_name(e: Expr) -> Optional[str]:
    if isinstance(e, And):
        return "AND"
    if isinstance(e, Or):
        return "OR"
    if isinstance(e, Xor):
        return "XOR"
    if isinstance(e, Imp):
        return "IMP"
    if isinstance(e, Eqv):
        return "EQV"
    return None


def _signed_operator_pair(
    e: Expr,
    R: List[str],
    C: List[str],
    fixed: Dict[str, int],
    metrics: Dict[str, int],
) -> Optional[Tuple[_Pair, bool]]:
    """Compile ``op(signed literal, signed literal)`` into the R/C frame."""
    op_name = _binary_op_name(e)
    if op_name is None:
        return None
    first = _signed_literal(e.a, metrics)
    second = _signed_literal(e.b, metrics)
    if first is None or second is None:
        return None
    first_name, negate_first = first
    second_name, negate_second = second
    if first_name in fixed or second_name in fixed:
        return None

    if first_name in R and second_name in C:
        row_var, col_var = first_name, second_name
        swapped = False
    elif first_name in C and second_name in R:
        row_var, col_var = second_name, first_name
        swapped = True
    else:
        return None

    transformed = bool(swapped or negate_first or negate_second)
    token = cm_align_signed_operands(
        TOK[op_name],
        swapped=swapped,
        negate_first=negate_first,
        negate_second=negate_second,
    )
    return _Pair(row_var, col_var, token, True, 0), transformed


def _pairable_vars(
    e: Expr,
    R: List[str],
    C: List[str],
    fixed: Dict[str, int],
) -> Optional[Tuple[str, str]]:
    vs = [v for v in _expr_vars(e) if v not in fixed]
    r = [v for v in vs if v in R]
    c = [v for v in vs if v in C]
    if len(r) == 1 and len(c) == 1 and len(vs) <= 2:
        return r[0], c[0]
    return None


def _fallback_compile(
    e: Expr,
    R: List[str],
    C: List[str],
    fixed: Dict[str, int],
    diagnostics: Optional[Dict[str, int]],
    materialize_mode: str,
    hybrid_threshold: int,
) -> np.ndarray:
    return compile_expr_to_cm(
        e,
        R,
        C,
        fixed,
        diagnostics=diagnostics,
        materialize_mode=materialize_mode,
        hybrid_threshold=hybrid_threshold,
        output_budget=None,
    )


def _compile_pair(
    e: Expr,
    R: List[str],
    C: List[str],
    fixed: Dict[str, int],
    metrics: Dict[str, int],
    *,
    allow_local_retabulation: bool,
) -> Optional[_Pair]:
    metrics["compiler_calls"] = metrics.get("compiler_calls", 0) + 1

    signed_operator = _signed_operator_pair(e, R, C, fixed, metrics)
    if signed_operator is not None:
        pair, transformed = signed_operator
        metrics["pair_attempts"] = metrics.get("pair_attempts", 0) + 1
        metrics["pair_collapses"] = metrics.get("pair_collapses", 0) + 1
        metrics["primitive_pair_tokens"] = (
            metrics.get("primitive_pair_tokens", 0) + 1
        )
        if transformed:
            metrics["signed_operand_alignments"] = (
                metrics.get("signed_operand_alignments", 0) + 1
            )
        return pair

    if isinstance(e, Not):
        sub = _compile_pair(
            e.a,
            R,
            C,
            fixed,
            metrics,
            allow_local_retabulation=allow_local_retabulation,
        )
        if sub is not None:
            metrics["pair_collapses"] = metrics.get("pair_collapses", 0) + 1
            metrics["token_negations"] = metrics.get("token_negations", 0) + 1
            return _Pair(
                sub.xl,
                sub.xr,
                cm_not(sub.tok),
                True,
                sub.retabulated_subtrees,
            )

    elif isinstance(e, (And, Or, Xor, Imp, Eqv)):
        a = _compile_pair(
            e.a,
            R,
            C,
            fixed,
            metrics,
            allow_local_retabulation=allow_local_retabulation,
        )
        b = _compile_pair(
            e.b,
            R,
            C,
            fixed,
            metrics,
            allow_local_retabulation=allow_local_retabulation,
        )
        if a is not None and b is not None and a.xl == b.xl and a.xr == b.xr:
            op_name = _binary_op_name(e)
            assert op_name is not None
            metrics["pair_collapses"] = metrics.get("pair_collapses", 0) + 1
            metrics["token_fusions"] = metrics.get("token_fusions", 0) + 1
            return _Pair(
                a.xl,
                a.xr,
                cm_compose(a.tok, b.tok, op_name),
                True,
                a.retabulated_subtrees + b.retabulated_subtrees,
            )

    elif isinstance(e, Var):
        return None

    else:
        raise TypeError(f"Unknown node {type(e)}")

    if not allow_local_retabulation:
        return None

    pv = _pairable_vars(e, R, C, fixed)
    if pv is None:
        return None
    xl, xr = pv
    metrics["pair_attempts"] = metrics.get("pair_attempts", 0) + 1
    metrics["pair_collapses"] = metrics.get("pair_collapses", 0) + 1
    metrics["direct_pair_retabulations"] = (
        metrics.get("direct_pair_retabulations", 0) + 1
    )
    return _Pair(
        xl,
        xr,
        _token_from_expr_two_vars(e, xl, xr, fixed),
        False,
        1,
    )


MetricValue = Union[int, float, str]


def _metric_summary(
    metrics: Dict[str, int],
    root_outcome: str,
) -> Dict[str, MetricValue]:
    attempts = int(metrics.get("pair_attempts", 0))
    collapses = int(metrics.get("pair_collapses", 0))
    calls = int(metrics.get("compiler_calls", 0))
    return {
        "pair_attempts": attempts,
        "pair_collapses": collapses,
        # Legacy fields retained for existing result readers.  Historically,
        # ``nodes_total`` counted compiler calls rather than AST occurrences,
        # and ``pairable_ratio`` used the same denominator.
        "pairable_ratio": (collapses / calls) if calls > 0 else 0.0,
        "nodes_total": calls,
        "ast_occurrences": int(metrics.get("ast_occurrences", 0)),
        "unique_object_nodes": int(metrics.get("unique_object_nodes", 0)),
        "ast_height": int(metrics.get("ast_height", 0)),
        "compiler_calls": calls,
        "negation_nodes_scanned": int(metrics.get("negation_nodes_scanned", 0)),
        "primitive_pair_tokens": int(metrics.get("primitive_pair_tokens", 0)),
        "signed_operand_alignments": int(metrics.get("signed_operand_alignments", 0)),
        "token_negations": int(metrics.get("token_negations", 0)),
        "token_fusions": int(metrics.get("token_fusions", 0)),
        "direct_pair_retabulations": int(metrics.get("direct_pair_retabulations", 0)),
        "retabulation_only_mode": int(metrics.get("retabulation_only_mode", 0)),
        "legacy_strategy_alias": int(metrics.get("legacy_strategy_alias", 0)),
        "root_outcome": root_outcome,
        "root_pure_structural": int(root_outcome == "pure_structural"),
        "root_hybrid_pair": int(root_outcome == "hybrid_pair"),
        "root_full_retabulation": int(root_outcome == "full_retabulation"),
        "root_ordinary_fallback": int(root_outcome == "ordinary_fallback"),
    }


def _compile_pair_by_retabulation(
    e: Expr,
    R: List[str],
    C: List[str],
    fixed: Dict[str, int],
    metrics: Dict[str, int],
) -> Optional[_Pair]:
    """Ablation: discover one R/C pair, then evaluate the full AST four times."""
    variables, _node_count = _expr_vars_and_node_count(e)
    metrics["retabulation_only_mode"] = 1
    metrics["pair_attempts"] = 1
    live = [variable for variable in variables if variable not in fixed]
    row_variables = [variable for variable in live if variable in R]
    column_variables = [variable for variable in live if variable in C]
    if len(row_variables) != 1 or len(column_variables) != 1 or len(live) > 2:
        return None
    row_variable = row_variables[0]
    column_variable = column_variables[0]
    metrics["pair_collapses"] = 1
    metrics["direct_pair_retabulations"] = 1
    return _Pair(
        row_variable,
        column_variable,
        _token_from_expr_two_vars(e, row_variable, column_variable, fixed),
        False,
        1,
    )


def compile_expr_to_cm_pair_token(
    e: Expr,
    R: List[str],
    C: List[str],
    fixed: Dict[str, int],
    *,
    strategy: Literal[
        "pure_structural", "hybrid", "retabulate", "structural"
    ] = "hybrid",
) -> Tuple[Optional[CompiledPairToken], Dict[str, MetricValue]]:
    """Compile to a token-only pair artifact without dense materialization.

    Returns ``None`` when the expression cannot be represented by the current
    one-row-variable/one-column-variable pair path. ``pure_structural`` forbids
    local retabulation, ``hybrid`` permits it and reports the root provenance,
    and ``retabulate`` bypasses structural assembly and evaluates the full
    expression on all four assignments.  The old name ``structural`` remains
    as a compatibility alias for ``hybrid`` and is reported in diagnostics.
    """
    _validate_pair_layout(R, C)
    variables, occurrences, unique_nodes, height = _expr_stats(e)
    metrics: Dict[str, int] = {
        "ast_occurrences": occurrences,
        "unique_object_nodes": unique_nodes,
        "ast_height": height,
    }
    del variables

    effective_strategy = strategy
    if strategy == "structural":
        effective_strategy = "hybrid"
        metrics["legacy_strategy_alias"] = 1

    if effective_strategy == "pure_structural":
        pair = _compile_pair(
            e,
            R,
            C,
            fixed,
            metrics,
            allow_local_retabulation=False,
        )
    elif effective_strategy == "hybrid":
        pair = _compile_pair(
            e,
            R,
            C,
            fixed,
            metrics,
            allow_local_retabulation=True,
        )
    elif effective_strategy == "retabulate":
        pair = _compile_pair_by_retabulation(e, R, C, fixed, metrics)
    else:
        raise ValueError(
            "strategy must be 'pure_structural', 'hybrid', or 'retabulate', "
            f"got {strategy!r}"
        )

    if pair is None:
        root_outcome = "ordinary_fallback"
    elif effective_strategy == "retabulate":
        root_outcome = "full_retabulation"
    elif pair.structural_steps and pair.retabulated_subtrees:
        root_outcome = "hybrid_pair"
    elif pair.retabulated_subtrees:
        root_outcome = "full_retabulation"
    else:
        root_outcome = "pure_structural"
    compiled = (
        None
        if pair is None
        else CompiledPairToken(pair.xl, pair.xr, pair.tok)
    )
    return compiled, _metric_summary(metrics, root_outcome)


def compile_expr_to_cm_pair(
    e: Expr,
    R: List[str],
    C: List[str],
    fixed: Dict[str, int],
    *,
    diagnostics: Optional[Dict[str, int]] = None,
    materialize_mode: str = "partial_hybrid",
    hybrid_threshold: int = 7,
    output_budget: Optional[OutputBudget] = DEFAULT_OUTPUT_BUDGET,
    pair_strategy: Literal[
        "pure_structural", "hybrid", "retabulate", "structural"
    ] = "hybrid",
) -> Tuple[np.ndarray, Dict[str, MetricValue]]:
    require_output_budget(
        decide_output_budget(
            output_budget,
            estimate_explicit_output(len(R) + len(C), "dense_bool"),
            artifact_name="full dense CM output",
        )
    )
    compiled, metrics = compile_expr_to_cm_pair_token(
        e,
        R,
        C,
        fixed,
        strategy=pair_strategy,
    )
    if compiled is not None:
        Ms = _token_to_matrix(compiled.token)
        M = lift_cm(
            Ms,
            vars_rows=[compiled.row_variable],
            vars_cols=[compiled.column_variable],
            R=R,
            C=C,
            fixed=fixed,
        )
    else:
        M = _fallback_compile(
            e,
            R,
            C,
            fixed,
            diagnostics,
            materialize_mode,
            hybrid_threshold,
        )
    return M, metrics


__all__ = [
    "CompiledPairToken",
    "compile_expr_to_cm_pair",
    "compile_expr_to_cm_pair_token",
]

