from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from cm_ir import expr_structural_hash


def _digest_text(*parts: Any) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def expression_digest(expr: Any, structural_identity: Any | None = None) -> str:
    identity = expr_structural_hash(expr) if structural_identity is None else structural_identity
    return _digest_text("cm-expression", identity)


def anonymous_id(kind: str, *parts: Any) -> str:
    return _digest_text(kind, *parts)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return None


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return max(0.0, result) if result == result and result != float("inf") else None


def _should_trace(ctx: Any, stream: str) -> bool:
    sink = ctx.trace_sink
    if not sink.enabled:
        return False
    should_trace = getattr(ctx, "should_trace", None)
    return bool(should_trace(stream)) if callable(should_trace) else True


def _sample_every(ctx: Any) -> int:
    config = getattr(ctx, "config", None)
    try:
        return max(1, int(getattr(config, "cm_trace_sample_every", 1)))
    except (TypeError, ValueError, OverflowError):
        return 1


def _common_expression_payload(expr: Any, row: Mapping[str, Any], *, workload_id: str) -> dict[str, Any]:
    return {
        "workload_id": anonymous_id("workload", workload_id),
        "expression_digest": expression_digest(expr, row.get("expr_structural_hash_if_available")),
        "n_vars": _int_or_none(row.get("n_vars")),
        "semantic_support": _int_or_none(
            row.get("expr_unique_var_count", row.get("cm_live_vars_max", row.get("partial_remaining_var_count_median")))
        ),
        "tree_nodes": _int_or_none(row.get("expr_node_count")),
        "primitive_ops": _int_or_none(row.get("expr_op_count")),
        "output_kind": "packed_complete",
    }


def trace_single_expression_result(ctx: Any, expr: Any, row: Mapping[str, Any], *, workload_id: str) -> None:
    sink = ctx.trace_sink
    if not _should_trace(ctx, "single_expression"):
        return
    common = _common_expression_payload(expr, row, workload_id=workload_id)
    common["sample_every"] = _sample_every(ctx)
    trial = _int_or_none(row.get("trial"))
    cm_total = _float_or_none(row.get("cm_hybrid_no_reinflate_time_s", row.get("cm_time_s")))
    cm_kernel = _float_or_none(
        row.get("cm_hybrid_no_reinflate_exec_only_time_s", row.get("cm_exec_only_time_s"))
    )
    cm_prepare = _float_or_none(row.get("cm_hybrid_no_reinflate_ir_compile_time_s", row.get("cm_ir_compile_time_s")))
    cm_ok = row.get("cm_hybrid_no_reinflate_ok", row.get("cm_ok"))
    sink.emit(
        "evaluation_result",
        **common,
        backend="cm",
        trial=trial,
        prepare_s=cm_prepare,
        kernel_s=cm_kernel,
        total_s=cm_total,
        status="ok" if cm_total is not None else "not_measured",
        exact_ok=bool(cm_ok) if cm_ok is not None else None,
        timing_boundary="complete_output",
    )
    bitset_total = _float_or_none(row.get("bitset_time_s"))
    if bitset_total is not None:
        bitset_ok = row.get("bitset_ok")
        sink.emit(
            "evaluation_result",
            **common,
            backend="bitset",
            trial=trial,
            kernel_s=bitset_total,
            total_s=bitset_total,
            status="ok",
            exact_ok=bool(bitset_ok) if bitset_ok is not None else None,
            timing_boundary="complete_output",
        )


def trace_expression_family_result(
    ctx: Any,
    variants: Sequence[Any],
    row: Mapping[str, Any],
    *,
    family_id: str,
    trial: int,
) -> None:
    sink = ctx.trace_sink
    if not _should_trace(ctx, "expression_family"):
        return
    sample_every = _sample_every(ctx)
    anon_family = anonymous_id("family", family_id)
    workload_id = anonymous_id("workload", "family", row.get("n_vars"), trial)
    family_size = len(variants)
    for index, expr in enumerate(variants):
        sink.emit(
            "family_version",
            workload_id=workload_id,
            family_id=anon_family,
            expression_digest=expression_digest(expr),
            variant_index=index,
            family_size=family_size,
            trial=max(0, int(trial)),
            n_vars=_int_or_none(row.get("n_vars")),
            semantic_support=_int_or_none(row.get("expr_unique_var_count")),
            phase="observed",
            status="ok",
            sample_every=sample_every,
        )
    sink.emit(
        "prepare_result",
        workload_id=workload_id,
        family_id=anon_family,
        backend="cm_cache",
        family_size=family_size,
        trial=max(0, int(trial)),
        n_vars=_int_or_none(row.get("n_vars")),
        prepare_s=_float_or_none(row.get("family_cm_cache_compile_total_s")),
        kernel_s=_float_or_none(row.get("family_cm_cache_eval_total_s")),
        total_s=_float_or_none(row.get("family_cm_cache_total_time_s")),
        cache_hits=_int_or_none(row.get("family_cm_cache_persistent_hits_total")),
        cache_misses=_int_or_none(row.get("family_cm_cache_persistent_misses_total")),
        exact_ok=(
            bool(float(row["family_cm_cache_ok_rate"]) == 1.0)
            if row.get("family_cm_cache_ok_rate") is not None
            else None
        ),
        output_kind="packed_complete",
        timing_boundary="family_total",
        status="ok" if row.get("family_cm_cache_total_time_s") is not None else "not_measured",
        sample_every=sample_every,
    )


def _context_digest(context: Mapping[str, int]) -> str:
    normalized = tuple(sorted((str(key), int(value)) for key, value in context.items()))
    return anonymous_id("context", normalized)


def _context_overlap(previous: Mapping[str, int] | None, current: Mapping[str, int]) -> tuple[float, float]:
    if previous is None:
        return 0.0, 0.0
    left = set(previous)
    right = set(current)
    union = left | right
    overlap = float(len(left & right) / len(union)) if union else 1.0
    shared = left & right
    similarity = float(sum(int(previous[key]) == int(current[key]) for key in shared) / len(shared)) if shared else 0.0
    return overlap, similarity


def trace_partial_context_result(
    ctx: Any,
    expr: Any,
    contexts: Sequence[Mapping[str, int]],
    row: Mapping[str, Any],
    *,
    trial: int,
) -> None:
    sink = ctx.trace_sink
    if not _should_trace(ctx, "partial_context"):
        return
    sample_every = _sample_every(ctx)
    expr_digest = expression_digest(expr)
    workload_id = anonymous_id("workload", "partial", row.get("n_vars"), trial, expr_digest)
    n_vars = _int_or_none(row.get("n_vars"))
    previous: Mapping[str, int] | None = None
    for index, context in enumerate(contexts):
        overlap, similarity = _context_overlap(previous, context)
        fixed_count = len(context)
        sink.emit(
            "context_transition",
            workload_id=workload_id,
            expression_digest=expr_digest,
            context_id=_context_digest(context),
            context_index=index,
            context_count=len(contexts),
            trial=max(0, int(trial)),
            n_vars=n_vars,
            fixed_var_count=fixed_count,
            remaining_support=(max(0, int(n_vars) - fixed_count) if n_vars is not None else None),
            fixed_var_fraction=(float(fixed_count / n_vars) if n_vars else 0.0),
            context_overlap=overlap,
            context_value_similarity=similarity,
            phase="observed",
            status="ok",
            sample_every=sample_every,
        )
        previous = context
    sink.emit(
        "evaluation_result",
        workload_id=workload_id,
        expression_digest=expr_digest,
        backend="cm_cache",
        trial=max(0, int(trial)),
        n_vars=n_vars,
        context_count=len(contexts),
        prepare_s=_float_or_none(row.get("partial_cm_cache_compile_once_s")),
        kernel_s=_float_or_none(row.get("partial_cm_cache_eval_contexts_total_s")),
        total_s=_float_or_none(row.get("partial_cm_cache_total_s")),
        exact_ok=(
            bool(float(row["partial_cm_cache_ok_rate"]) == 1.0)
            if row.get("partial_cm_cache_ok_rate") is not None
            else None
        ),
        output_kind="packed_complete",
        timing_boundary="context_stream_total",
        status="ok" if row.get("partial_cm_cache_total_s") is not None else "not_measured",
        sample_every=sample_every,
    )
