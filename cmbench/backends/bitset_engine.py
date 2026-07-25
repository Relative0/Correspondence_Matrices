from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from bitset_backend import (
    build_bitset_env,
    eval_cm_node_bitset,
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_bitset,
    eval_expr_flat_bitset,
    eval_expr_words_bitset,
)


@dataclass(frozen=True)
class EngineSelection:
    kind: str
    live_k: int
    timing_class: str
    requires_bigint_env: bool
    supports_fixed: bool
    evaluator: Callable

    def evaluate_expr(
        self,
        expr,
        output_vars: Sequence[str],
        *,
        fixed: Mapping[str, int] | None = None,
        bigint_env: Mapping[str, int] | None = None,
    ) -> int:
        if self.requires_bigint_env:
            if fixed:
                raise ValueError("recursive engine fixed evaluation requires the partial-context helper")
            env = bigint_env if bigint_env is not None else build_bitset_env(output_vars)
            return int(self.evaluator(expr, env))
        return int(self.evaluator(expr, tuple(output_vars), fixed=fixed or {}))


@dataclass(frozen=True)
class CMNodeEngineSelection:
    kind: str
    live_k: int
    timing_class: str
    evaluator: Callable

    def evaluate_node(
        self,
        node,
        output_vars: Sequence[str],
        *,
        fixed: Mapping[str, int] | None = None,
    ) -> int:
        return int(self.evaluator(node, tuple(output_vars), fixed=fixed or {}))


def select_raw_ast_engine(
    *,
    live_k: int,
    words_requested: bool,
    flat_requested: bool,
) -> EngineSelection:
    """Select the raw-expression evaluator from actual output width.

    Words is used only at six or more live/output variables. A words request at
    a narrower width truthfully selects the flat bigint kernel used by the
    existing words evaluator's compatibility fallback.
    """
    k = int(live_k)
    if k < 0:
        raise ValueError("live_k must be non-negative")
    if words_requested and k >= 6:
        return EngineSelection(
            "raw_ast_words", k, "packed_execute", False, True, eval_expr_words_bitset
        )
    if flat_requested or words_requested:
        return EngineSelection(
            "raw_ast_flat", k, "packed_execute", False, True, eval_expr_flat_bitset
        )
    return EngineSelection(
        "raw_ast_recursive", k, "packed_execute", True, False, eval_expr_bitset
    )


def select_cm_node_engine(
    *,
    live_k: int,
    words_requested: bool,
    flat_requested: bool,
) -> CMNodeEngineSelection:
    raw = select_raw_ast_engine(
        live_k=live_k,
        words_requested=words_requested,
        flat_requested=flat_requested,
    )
    evaluator = (
        eval_cm_node_words
        if raw.kind == "raw_ast_words"
        else eval_cm_node_flat
        if raw.kind == "raw_ast_flat"
        else eval_cm_node_bitset
    )
    return CMNodeEngineSelection(
        kind=raw.kind.replace("raw_ast_", "cm_node_"),
        live_k=raw.live_k,
        timing_class=raw.timing_class,
        evaluator=evaluator,
    )
