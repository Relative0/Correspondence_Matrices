#!/usr/bin/env python3
import argparse
import hashlib
import importlib
import importlib.metadata
import random
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np


def try_import(name: str):
    try:
        return __import__(name)
    except Exception:
        return None


dd = try_import("dd")
pyeda = try_import("pyeda")

from bitset_backend import (
    bitset_to_bool_array,
    build_bitset_env,
    eval_cm_node_bitset,
    eval_expr_bitset,
    eval_expr_flat_bitset,
    eval_expr_words_bitset,
)
from cm_build import compile_expr_to_cm
from cmbench.availability import detect_backends
from cmbench.backends.bitset_utils import bitset_equivalence_check
from cmbench.config import BenchmarkConfig, config_from_args
from cmbench.context import BenchmarkRunContext, make_context
from cmbench.backends.robdd_dd import (
    _dd_cudd_available,
    _empty_robdd_dd_result,
    _empty_robdd_equiv_result,
    _try_collect_garbage,
    bdd_backend_identity,
    bdd_function_value,
    compact_order_repr,
    expr_to_dd_bdd,
    expr_vars_first_occurrence,
    extract_dd_bdd_truth_table,
    maybe_extract_dd_bdd_truth_table,
    maybe_reorder_dd,
    robdd_equivalence_check,
    robdd_variable_order,
    run_robdd_dd_backend,
    safe_bdd_node_count,
    select_dd_module,
    validate_dd_bdd_correctness,
)
from cmbench.cli import build_config_and_context, parse_depth_sweep
from cmbench.expr.diagnostics import _expr_used_indices, expr_complexity_diagnostics, truth_table_diagnostics
from cmbench.expr.equivalence import (
    _no_reinflate_payload_equal,
    _rewrite_equiv_expr,
    generate_equiv_pair,
    pair_diagnostics,
)
from cmbench.expr.eval import eval_expr_assignment, result_value_for_assignment, sampled_correctness_check
from cmbench.expr.families import (
    _const_expr,
    _expr_children,
    _expr_get_subtree,
    _expr_paths,
    _expr_replace_subtree,
    _expr_with_children,
    _family_op_for_index,
    _small_random_subtree,
    collect_subtree_hashes,
    expression_family_diagnostics,
    generate_expression_family,
    substitute_variables_with_constants,
)
from cmbench.expr.generators import (
    _maybe_not,
    expression_filter_reason,
    generate_benchmark_expr,
    random_expr_and_or_not,
    random_expr_balanced_all_vars,
    random_expr_broad,
    random_expr_for_style,
    random_expr_implication_heavy,
    random_expr_low_reuse,
    random_expr_mixed_no_constants,
    random_expr_xor_heavy,
)
from cmbench.expr.partial_contexts import (
    _eval_expr_bitset_fixed,
    _partial_output_vars,
    _partial_reference_array,
    _result_to_partial_array,
    generate_partial_contexts,
    partial_context_diagnostics,
)
from cmbench.expr.visitors import collect_subtree_hashes_fast
from cmbench.results.equivalence import skipped_equiv_result
from cmbench.results.expression_family import skipped_family_backend
from cmbench.results.partial_context import skipped_partial_backend
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, eval_expr_tt, random_expr
from cm_ir import (
    clear_cm_ir_persistent_cache,
    cm_ir_persistent_cache_stats,
    compile_expr,
    compile_expr_to_cm_ir,
    evaluate_compiled,
    expr_structural_hash,
    materialize_cm,
    materialize_hybrid_no_reinflate,
)
from cm_normalize import canonical_layout, cm_normalize_cache_stats
from cm_operator_difference import (
    CM_2X2,
    cm_2x2_name,
    cm_2x2_transform_correct,
    cm_complement,
    cm_feature_counts,
    cm_overlap,
    cm_quotient,
    cm_rotate90,
    cm_rotate180,
    cm_rotate270,
    cm_symmetric_delta,
    cm_transform_negate_both_operands,
    cm_transform_negate_expression,
    cm_transform_negate_left_operand,
    cm_transform_negate_right_operand,
    cm_transform_swap_operands,
    cm_transpose,
)
from cm_parallel import compile_expr_to_cm_parallel, count_expr_nodes
from cm_remote_executor import LocalMockCMRemoteExecutor, RunPodCMRemoteExecutor, build_remote_request
from cm_runpod_client import CMRunPodClient
from cm_runpod_config import load_runpod_config
from expr_simplify import bdd_sop, simplify_via_sympy
from numba_backend import HAS_NUMBA, eval_expr_numba, flatten_expr_numba

try:
    from cm_build_lazy import clear_lazy_align_cache, compile_expr_to_cm_lazy, lazy_align_cache_stats

    HAS_LAZY = True
except Exception:
    HAS_LAZY = False
    compile_expr_to_cm_lazy = None  # type: ignore[assignment]
    lazy_align_cache_stats = None  # type: ignore[assignment]
    clear_lazy_align_cache = None  # type: ignore[assignment]

try:
    from cm_build_pair import compile_expr_to_cm_pair

    HAS_PAIR = True
except Exception:
    HAS_PAIR = False
    compile_expr_to_cm_pair = None  # type: ignore[assignment]


args = None
_ACTIVE_CONFIG: Optional[BenchmarkConfig] = None

_GRID_CACHE: Dict[int, np.ndarray] = {}


def _current_config() -> BenchmarkConfig:
    if _ACTIVE_CONFIG is not None:
        return _ACTIVE_CONFIG
    if args is not None:
        return config_from_args(args)
    return BenchmarkConfig(sizes=(), trials=1, seed=0, max_depth=3)


def remote_response_matches_tt(response, tt_ref: Optional[np.ndarray], n: int) -> Optional[bool]:
    if not response.ok or tt_ref is None or not response.result:
        return False if not response.ok else None
    if response.result_repr == "packed_bitset" and "bits_hex" in response.result:
        tt_remote = bitset_to_bool_array(int(str(response.result["bits_hex"]), 16), n)
        return bool(np.array_equal(tt_remote, tt_ref))
    if response.result_repr == "truth_table" and "tt" in response.result:
        tt_remote = np.asarray(response.result["tt"], dtype=np.uint8).reshape(-1)
        return bool(np.array_equal(tt_remote, tt_ref))
    return None


def _check_remote_words_provenance(result, words_requested: bool):
    """Refuse to record a words-provenance row for a remote run without words.

    A worker that predates the ``words_eval`` request field silently ignores it
    and never echoes ``remote_words_eval`` in its diagnostics; recording such a
    run would claim cm_words_eval=True while the pod evaluated without words.
    """
    if words_requested and result.response.ok and not bool(result.response.diagnostics.get("remote_words_eval")):
        raise RuntimeError(
            "remote worker did not confirm words_eval; refusing to record a words run "
            "against a worker that evaluated without words (redeploy the worker or "
            "drop --cm-words-eval)"
        )
    return result


def execute_remote_cm(expr, n: int, *, large_n_safe: bool):
    bench_config = _current_config()
    words_requested = bool(bench_config.cm_words_eval)
    request = build_remote_request(
        expr,
        n,
        hybrid_threshold=int(bench_config.cm_hybrid_threshold),
        use_persistent_cache=bool(bench_config.cm_use_persistent_cache),
        eval_repeat=int(bench_config.cm_eval_repeat),
        large_n_safe=large_n_safe,
        max_full_output_vars=int(bench_config.cm_max_full_output_vars),
        words_eval=words_requested,
    )
    if bool(bench_config.cm_runpod_local_mock):
        return _check_remote_words_provenance(LocalMockCMRemoteExecutor().execute(request), words_requested)
    config = load_runpod_config()
    executor = RunPodCMRemoteExecutor(config)
    stop_after_run = True if bool(bench_config.cm_runpod_stop_after_run) else None
    return _check_remote_words_provenance(
        executor.execute(request, stop_after_run=stop_after_run), words_requested
    )


def cm_equivalence_check(expr_f, expr_g, n: int, *, expected: Optional[bool] = None) -> Dict[str, Any]:
    vars_all = [f"x{i}" for i in range(n)]
    diag_f: Dict[str, Any] = {}
    diag_g: Dict[str, Any] = {}
    bench_config = _current_config()
    try:
        t0 = time.perf_counter()
        compiled_f = compile_expr(expr_f, diagnostics=diag_f, use_persistent_cache=bool(bench_config.cm_use_persistent_cache))
        compile_f = time.perf_counter() - t0
        t1 = time.perf_counter()
        compiled_g = compile_expr(expr_g, diagnostics=diag_g, use_persistent_cache=bool(bench_config.cm_use_persistent_cache))
        compile_g = time.perf_counter() - t1
        t2 = time.perf_counter()
        res_f = evaluate_compiled(
            compiled_f,
            mode="hybrid_no_reinflate",
            vars_all=vars_all,
            diagnostics=diag_f,
            hybrid_threshold=int(bench_config.cm_hybrid_threshold),
        )
        eval_f = time.perf_counter() - t2
        t3 = time.perf_counter()
        res_g = evaluate_compiled(
            compiled_g,
            mode="hybrid_no_reinflate",
            vars_all=vars_all,
            diagnostics=diag_g,
            hybrid_threshold=int(bench_config.cm_hybrid_threshold),
        )
        eval_g = time.perf_counter() - t3
        t4 = time.perf_counter()
        result = _no_reinflate_payload_equal(res_f, res_g)
        compare_time = time.perf_counter() - t4
        compile_total = compile_f + compile_g
        eval_total = eval_f + eval_g
        return {
            "cm_equiv_compile_f_time_s": compile_f,
            "cm_equiv_compile_g_time_s": compile_g,
            "cm_equiv_compile_total_time_s": compile_total,
            "cm_equiv_eval_f_time_s": eval_f,
            "cm_equiv_eval_g_time_s": eval_g,
            "cm_equiv_eval_total_time_s": eval_total,
            "cm_equiv_compare_time_s": compare_time,
            "cm_equiv_total_time_s": compile_total + eval_total + compare_time,
            "cm_equiv_result": bool(result),
            "cm_equiv_ok": (bool(result) == bool(expected)) if expected is not None else None,
            "cm_equiv_status": "ok",
            "cm_equiv_error": None,
            "cm_equiv_final_repr_f": getattr(res_f, "final_output_representation_code", None),
            "cm_equiv_final_repr_g": getattr(res_g, "final_output_representation_code", None),
            "cm_equiv_final_cm_materialized_f": int(diag_f.get("final_cm_materialization_performed", 0)),
            "cm_equiv_final_cm_materialized_g": int(diag_g.get("final_cm_materialization_performed", 0)),
            "cm_equiv_live_vars_max_f": int(diag_f.get("live_vars_max", len(getattr(compiled_f.node, "vars", ())))),
            "cm_equiv_live_vars_max_g": int(diag_g.get("live_vars_max", len(getattr(compiled_g.node, "vars", ())))),
            "cm_equiv_structural_same": bool(compiled_f.node == compiled_g.node),
        }
    except Exception as e:
        return {
            "cm_equiv_compile_f_time_s": None,
            "cm_equiv_compile_g_time_s": None,
            "cm_equiv_compile_total_time_s": None,
            "cm_equiv_eval_f_time_s": None,
            "cm_equiv_eval_g_time_s": None,
            "cm_equiv_eval_total_time_s": None,
            "cm_equiv_compare_time_s": None,
            "cm_equiv_total_time_s": None,
            "cm_equiv_result": None,
            "cm_equiv_ok": None,
            "cm_equiv_status": "error",
            "cm_equiv_error": repr(e),
            "cm_equiv_final_repr_f": None,
            "cm_equiv_final_repr_g": None,
            "cm_equiv_final_cm_materialized_f": None,
            "cm_equiv_final_cm_materialized_g": None,
            "cm_equiv_live_vars_max_f": None,
            "cm_equiv_live_vars_max_g": None,
            "cm_equiv_structural_same": None,
        }


def sympy_equivalence_check(expr_f, expr_g, n: int, *, expected: Optional[bool] = None) -> Dict[str, Any]:
    try:
        from expr_simplify import _to_sympy
        import sympy as sp

        t0 = time.perf_counter()
        result = sp.simplify_logic(sp.Xor(_to_sympy(expr_f, n), _to_sympy(expr_g, n), evaluate=False)) == False
        elapsed = time.perf_counter() - t0
        return {
            "sympy_equiv_time_s": elapsed,
            "sympy_equiv_result": bool(result),
            "sympy_equiv_ok": (bool(result) == bool(expected)) if expected is not None else None,
            "sympy_equiv_status": "ok",
            "sympy_equiv_error": None,
        }
    except Exception as e:
        return {
            "sympy_equiv_time_s": None,
            "sympy_equiv_result": None,
            "sympy_equiv_ok": None,
            "sympy_equiv_status": "error",
            "sympy_equiv_error": repr(e),
        }


def _median_or_none(values: List[Optional[float]]) -> Optional[float]:
    vals = [float(v) for v in values if v is not None]
    return float(statistics.median(vals)) if vals else None


def _mean_or_none(values: List[Optional[float]]) -> Optional[float]:
    vals = [float(v) for v in values if v is not None]
    return float(sum(vals) / len(vals)) if vals else None


def _ok_rate(values: List[Any]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return float(sum(1 for v in vals if bool(v)) / len(vals))


def _ratio_or_none(a: Any, b: Any) -> Optional[float]:
    try:
        if a is None or b is None or float(b) == 0.0:
            return None
        return float(a) / float(b)
    except Exception:
        return None


def _cm_partial_workload(
    expr: Any,
    n_vars: int,
    contexts: List[Mapping[str, int]],
    *,
    output_mode: str,
    persistent_cache: bool,
    reuse_compiled_ir: bool,
    reference_arrays: List[Optional[np.ndarray]],
    sample_rng: np.random.Generator,
    config: BenchmarkConfig,
) -> Dict[str, Any]:
    clear_cm_ir_persistent_cache()
    prefix = "partial_cm_cache" if persistent_cache else "partial_cm_no_cache"
    compile_times: List[float] = []
    eval_times: List[float] = []
    per_context: List[float] = []
    live_vars: List[Optional[float]] = []
    oks: List[Any] = []
    hits = 0
    misses = 0
    compiled = None
    compile_once_s: Optional[float] = None
    if persistent_cache and reuse_compiled_ir:
        diag: Dict[str, Any] = {"ir_timing_enabled": 1}
        t0 = time.perf_counter()
        compiled = compile_expr(expr, diagnostics=diag, use_persistent_cache=True, reuse_cache=False)
        compile_once_s = time.perf_counter() - t0
        hits += int(diag.get("ir_persistent_cache_hits", 0) or 0)
        misses += int(diag.get("ir_persistent_cache_misses", 0) or 0)
    total0 = time.perf_counter()
    for i, context in enumerate(contexts):
        context_map = {str(k): int(v) for k, v in context.items()}
        out_vars = _partial_output_vars(n_vars, context_map, output_mode)
        diag = {"ir_timing_enabled": 1}
        t_context = time.perf_counter()
        if compiled is None:
            c0 = time.perf_counter()
            node = compile_expr_to_cm_ir(expr, diagnostics=diag, persistent_cache=persistent_cache, reuse_cache=False)
            compile_times.append(time.perf_counter() - c0)
        else:
            node = compiled.node
            compile_times.append(0.0)
        e0 = time.perf_counter()
        res = materialize_hybrid_no_reinflate(
            node,
            out_vars,
            fixed=context_map,
            diagnostics=diag,
            hybrid_threshold=config.cm_hybrid_threshold,
            words_eval=config.cm_words_eval,
            allow_reduced_output=True,
            max_full_output_vars=config.cm_max_full_output_vars,
        )
        eval_times.append(time.perf_counter() - e0)
        per_context.append(time.perf_counter() - t_context)
        hits += int(diag.get("ir_persistent_cache_hits", 0) or 0)
        misses += int(diag.get("ir_persistent_cache_misses", 0) or 0)
        live_vars.append(float(len(tuple(res.output_vars))))
        ref = reference_arrays[i] if i < len(reference_arrays) else None
        actual = _result_to_partial_array(res)
        if ref is not None:
            oks.append(bool(actual is not None and np.array_equal(actual, ref)))
        elif int(config.sampled_correctness or 0) > 0:
            ok = True
            names = [f"x{i}" for i in range(n_vars)]
            for _ in range(int(config.sampled_correctness)):
                vals = sample_rng.integers(0, 2, size=n_vars, dtype=np.uint8)
                assignment = {name: int(vals[j]) for j, name in enumerate(names)}
                assignment.update(context_map)
                expected = eval_expr_assignment(expr, assignment)
                projected = {name: assignment[name] for name in tuple(res.output_vars)}
                actual_bit = result_value_for_assignment(res, projected)
                if expected != actual_bit:
                    ok = False
                    break
            oks.append(ok)
        else:
            oks.append(None)
    total_s = time.perf_counter() - total0
    if prefix == "partial_cm_cache":
        return {
            "partial_cm_cache_compile_once_s": compile_once_s if compile_once_s is not None else float(sum(compile_times)),
            "partial_cm_cache_eval_contexts_total_s": float(sum(eval_times)),
            "partial_cm_cache_total_s": float(total_s + (compile_once_s or 0.0)),
            "partial_cm_cache_per_context_median_s": _median_or_none(per_context),
            "partial_cm_cache_live_vars_median": _median_or_none(live_vars),
            "partial_cm_cache_live_vars_max": max((v for v in live_vars if v is not None), default=None),
            "partial_cm_cache_persistent_hits_total": int(hits),
            "partial_cm_cache_persistent_misses_total": int(misses),
            "partial_cm_cache_ok_rate": _ok_rate(oks),
        }
    return {
        "partial_cm_no_cache_total_s": float(total_s),
        "partial_cm_no_cache_compile_total_s": float(sum(compile_times)),
        "partial_cm_no_cache_eval_total_s": float(sum(eval_times)),
        "partial_cm_no_cache_per_context_median_s": _median_or_none(per_context),
        "partial_cm_no_cache_live_vars_median": _median_or_none(live_vars),
        "partial_cm_no_cache_live_vars_max": max((v for v in live_vars if v is not None), default=None),
        "partial_cm_no_cache_ok_rate": _ok_rate(oks),
    }


def _robdd_partial_context_workload(
    expr: Any,
    n_vars: int,
    contexts: List[Mapping[str, int]],
    *,
    output_mode: str,
    reference_arrays: List[Optional[np.ndarray]],
    sample_rng: np.random.Generator,
    order_seed: Optional[int],
    config: Optional[BenchmarkConfig] = None,
) -> Dict[str, Any]:
    config = config or (config_from_args(args) if args is not None else None)
    if config is None:
        raise ValueError("config is required when global args is not initialized")
    backend = str(config.robdd_dd_backend)
    dd_module, error = select_dd_module(backend)
    empty = {
        "partial_robdd_backend": backend,
        "partial_robdd_build_once_s": None,
        "partial_robdd_restrict_contexts_total_s": None,
        "partial_robdd_total_s": None,
        "partial_robdd_restrict_per_context_median_s": None,
        "partial_robdd_nodes_base": None,
        "partial_robdd_restricted_nodes_median": None,
        "partial_robdd_ok_rate": None,
        "partial_robdd_status": "unavailable",
        "partial_robdd_error": error,
        "partial_robdd_extract_total_s": None,
        "partial_robdd_build_restrict_extract_total_s": None,
    }
    if dd_module is None:
        return empty
    try:
        names = [f"x{i}" for i in range(n_vars)]
        order_policy = str(config.robdd_order_policy)
        sweeps = max(1, int(config.robdd_order_sweeps)) if order_policy == "best-of-k" else 1
        base_seed = 0 if order_seed is None else int(order_seed)
        candidates: List[Dict[str, Any]] = []
        for sweep in range(sweeps):
            effective_policy = "random" if order_policy == "best-of-k" else order_policy
            effective_seed = base_seed + sweep if effective_policy == "random" else order_seed
            manager_i = dd_module.BDD()
            order = robdd_variable_order(expr, n_vars, effective_policy, effective_seed)
            _declare_dd_vars(manager_i, order)
            t0 = time.perf_counter()
            root_i = expr_to_dd_bdd(expr, manager_i, {name: name for name in names})
            build_i = time.perf_counter() - t0
            candidates.append(
                {
                    "manager": manager_i,
                    "root": root_i,
                    "build_s": build_i,
                    "nodes": safe_bdd_node_count(manager_i, root_i),
                }
            )
        best = min(candidates, key=lambda c: (float(c["nodes"] or 10**30), float(c["build_s"])))
        manager = best["manager"]
        root = best["root"]
        build_s = float(best["build_s"])
        base_nodes = safe_bdd_node_count(manager, root)
        restrict_times: List[float] = []
        extract_times: List[float] = []
        restricted_nodes: List[Optional[float]] = []
        oks: List[Any] = []
        for i, context in enumerate(contexts):
            context_map = {str(k): int(v) for k, v in context.items()}
            bool_context = {k: bool(v) for k, v in context_map.items()}
            r0 = time.perf_counter()
            restricted = manager.let(bool_context, root)
            restrict_times.append(time.perf_counter() - r0)
            restricted_nodes.append(safe_bdd_node_count(manager, restricted))
            out_vars = _partial_output_vars(n_vars, context_map, output_mode)
            ref = reference_arrays[i] if i < len(reference_arrays) else None
            if ref is not None:
                ok = True
                measure_extract = bool(config.partial_robdd_measure_extract)
                e0 = time.perf_counter()
                for idx, bit in enumerate(ref.tolist()):
                    assignment = {name: (idx >> (len(out_vars) - 1 - j)) & 1 for j, name in enumerate(out_vars)}
                    if bdd_function_value(manager, restricted, assignment) != int(bit):
                        ok = False
                        break
                if measure_extract:
                    extract_times.append(time.perf_counter() - e0)
                oks.append(ok)
            elif int(config.sampled_correctness or 0) > 0:
                ok = True
                for _ in range(int(config.sampled_correctness)):
                    assignment = {name: int(sample_rng.integers(0, 2)) for name in out_vars}
                    full_assignment = {name: int(context_map.get(name, assignment.get(name, 0))) for name in names}
                    expected = eval_expr_assignment(expr, full_assignment)
                    if bdd_function_value(manager, restricted, assignment) != expected:
                        ok = False
                        break
                oks.append(ok)
            else:
                oks.append(None)
        restrict_total = float(sum(restrict_times))
        extract_total = float(sum(extract_times)) if extract_times else None
        ident = bdd_backend_identity(manager)
        backend_name = "dd.cudd" if ident.get("is_cudd") else ("dd.autoref" if ident.get("is_autoref") else ident.get("module"))
        return {
            "partial_robdd_backend": backend_name,
            "partial_robdd_build_once_s": float(build_s),
            "partial_robdd_restrict_contexts_total_s": restrict_total,
            "partial_robdd_total_s": float(build_s + restrict_total),
            "partial_robdd_restrict_per_context_median_s": _median_or_none(restrict_times),
            "partial_robdd_nodes_base": base_nodes,
            "partial_robdd_restricted_nodes_median": _median_or_none(restricted_nodes),
            "partial_robdd_ok_rate": _ok_rate(oks),
            "partial_robdd_status": "ok",
            "partial_robdd_error": None,
            "partial_robdd_extract_total_s": extract_total,
            "partial_robdd_build_restrict_extract_total_s": (
                float(build_s + restrict_total + extract_total) if extract_total is not None else None
            ),
        }
    except Exception as exc:
        out = dict(empty)
        out["partial_robdd_status"] = "error"
        out["partial_robdd_error"] = repr(exc)
        return out


def time_partial_context_workload(
    n_vars: int,
    expr: Any,
    contexts: List[Mapping[str, int]],
    *,
    trial: int,
    expr_style: str,
    bit_env: Optional[Mapping[str, int]],
    sample_rng: np.random.Generator,
    robdd_order_seed: Optional[int],
    config: Optional[BenchmarkConfig] = None,
) -> Dict[str, Any]:
    config = config or (config_from_args(args) if args is not None else None)
    if config is None:
        raise ValueError("config is required when global args is not initialized")
    output_mode = str(config.partial_output_mode)
    full_tt_max_n = int(config.full_tt_max_n)
    build_refs = n_vars <= full_tt_max_n
    reference_arrays = [
        _partial_reference_array(expr, n_vars, c, _partial_output_vars(n_vars, c, output_mode)) if build_refs else None
        for c in contexts
    ]
    row: Dict[str, Any] = {
        "n_vars": int(n_vars),
        "trial": int(trial),
        "expr_style": expr_style,
        "partial_output_mode": output_mode,
        "partial_reference_arrays_available_count": int(sum(ref is not None for ref in reference_arrays)),
        "partial_reference_source": "eval_expr_tt" if build_refs else "not_built",
        "partial_correctness_reference": (
            "eval_expr_tt"
            if build_refs
            else ("sampled_assignments" if int(config.sampled_correctness or 0) > 0 else "skipped_large_n")
        ),
        **partial_context_diagnostics(contexts, n_vars, str(config.partial_context_style)),
    }
    if not bool(config.no_bitset):
        # Same engine precedence as the single-expression control: words > flat >
        # recursive.  The engine changes with the CM-side flags; the scope of each
        # control (full recompute vs restricted) does not.
        names_full = tuple(f"x{i}" for i in range(n_vars))
        use_words_bitset = bool(config.cm_words_eval)
        use_flat_bitset = bool(config.cm_flat_eval or use_words_bitset)
        partial_bitset_baseline_kind = (
            "raw_ast_words" if use_words_bitset else "raw_ast_flat" if use_flat_bitset else "raw_ast_recursive"
        )
        env_full = None
        if not use_flat_bitset:
            env_full = bit_env if bit_env is not None else build_bitset_env(list(names_full))
        times_full: List[float] = []
        oks_full: List[Any] = []
        total0 = time.perf_counter()
        for i, context in enumerate(contexts):
            t0 = time.perf_counter()
            if use_words_bitset:
                _ = eval_expr_words_bitset(expr, names_full)
            elif use_flat_bitset:
                _ = eval_expr_flat_bitset(expr, names_full)
            else:
                _ = eval_expr_bitset(expr, env_full)
            times_full.append(time.perf_counter() - t0)
            if reference_arrays[i] is not None:
                oks_full.append(True)
            else:
                oks_full.append(None)
        full_total = time.perf_counter() - total0
        restricted_times: List[float] = []
        restricted_oks: List[Any] = []
        restricted_total0 = time.perf_counter()
        for i, context in enumerate(contexts):
            out_vars = _partial_output_vars(n_vars, context, output_mode)
            if use_flat_bitset:
                fixed_map = {str(k): int(v) for k, v in context.items()}
                t0 = time.perf_counter()
                bits = (
                    eval_expr_words_bitset(expr, tuple(out_vars), fixed=fixed_map)
                    if use_words_bitset
                    else eval_expr_flat_bitset(expr, tuple(out_vars), fixed=fixed_map)
                )
            else:
                env = build_bitset_env(out_vars)
                t0 = time.perf_counter()
                bits = _eval_expr_bitset_fixed(expr, env, context)
            restricted_times.append(time.perf_counter() - t0)
            ref = reference_arrays[i]
            if ref is not None:
                restricted_oks.append(bool(np.array_equal(bitset_to_bool_array(int(bits), len(out_vars)), ref)))
            else:
                restricted_oks.append(None)
        row.update(
            {
                "partial_bitset_baseline_kind": partial_bitset_baseline_kind,
                "partial_bitset_full_recompute_total_s": float(full_total),
                "partial_bitset_full_recompute_per_context_median_s": _median_or_none(times_full),
                "partial_bitset_ok_rate": _ok_rate(oks_full),
                "partial_bitset_restricted_total_s": float(time.perf_counter() - restricted_total0),
                "partial_bitset_restricted_per_context_median_s": _median_or_none(restricted_times),
                "partial_bitset_restricted_ok_rate": _ok_rate(restricted_oks),
            }
        )
    else:
        row.update(
            {
                "partial_bitset_baseline_kind": None,
                "partial_bitset_full_recompute_total_s": None,
                "partial_bitset_full_recompute_per_context_median_s": None,
                "partial_bitset_ok_rate": None,
                "partial_bitset_restricted_total_s": None,
                "partial_bitset_restricted_per_context_median_s": None,
                "partial_bitset_restricted_ok_rate": None,
            }
        )
    row.update(
        _cm_partial_workload(
            expr,
            n_vars,
            contexts,
            output_mode=output_mode,
            persistent_cache=False,
            reuse_compiled_ir=False,
            reference_arrays=reference_arrays,
            sample_rng=sample_rng,
            config=config,
        )
    )
    row.update(
        _cm_partial_workload(
            expr,
            n_vars,
            contexts,
            output_mode=output_mode,
            persistent_cache=True,
            reuse_compiled_ir=bool(config.partial_reuse_compiled_ir),
            reference_arrays=reference_arrays,
            sample_rng=sample_rng,
            config=config,
        )
    )
    if (not bool(config.no_dd)) and (not bool(config.no_robdd_dd)):
        row.update(
            _robdd_partial_context_workload(
                expr,
                n_vars,
                contexts,
                output_mode=output_mode,
                reference_arrays=reference_arrays,
                sample_rng=sample_rng,
                order_seed=robdd_order_seed,
                config=config,
            )
        )
    else:
        skipped = skipped_partial_backend("partial_robdd", reason="disabled")
        skipped["partial_robdd_backend"] = str(config.robdd_dd_backend)
        row.update(skipped)
    ratio = _ratio_or_none(row.get("partial_cm_cache_total_s"), row.get("partial_cm_no_cache_total_s"))
    row["speedup_cm_cache_vs_cm_no_cache"] = (1.0 / ratio) if ratio and ratio > 0 else None
    row["ratio_cm_cache_over_bitset_full_recompute"] = _ratio_or_none(
        row.get("partial_cm_cache_total_s"), row.get("partial_bitset_full_recompute_total_s")
    )
    row["ratio_cm_cache_over_bitset_restricted"] = _ratio_or_none(
        row.get("partial_cm_cache_total_s"), row.get("partial_bitset_restricted_total_s")
    )
    row["ratio_cm_cache_over_robdd_restrict"] = _ratio_or_none(
        row.get("partial_cm_cache_total_s"), row.get("partial_robdd_total_s")
    )
    return row


def run_partial_context_bench(
    sizes: List[int],
    trials: int,
    seed: int,
    max_depth: int,
    verbose: bool,
    config: Optional[BenchmarkConfig] = None,
    ctx: Optional[BenchmarkRunContext] = None,
):
    import pandas as pd

    config = config or (config_from_args(args) if args is not None else None)
    if config is None:
        raise ValueError("config is required when global args is not initialized")
    ctx = ctx or make_context(config, detect_backends())
    rng = np.random.default_rng(seed)
    sample_rng = np.random.default_rng(seed + 3_000_003)
    expr_style = config.expr_style
    rows: List[Dict[str, Any]] = []
    bit_env_by_n: Dict[int, Mapping[str, int]] = {}
    if not config.no_bitset:
        for n in sizes:
            if n <= config.full_tt_max_n:
                bit_env_by_n[n] = build_bitset_env([f"x{i}" for i in range(n)])
    for n in sizes:
        if verbose:
            print(f"\n=== partial contexts n = {n} ===")
        for t in range(trials):
            expr, expr_diag = generate_benchmark_expr(
                n,
                rng,
                max_depth=max_depth,
                style=expr_style,
                build_tt=n <= config.full_tt_max_n,
                config=config,
            )
            contexts = generate_partial_contexts(
                n,
                rng,
                context_count=config.partial_contexts,
                fixed_var_count=config.partial_fixed_var_count,
                fixed_var_fraction=float(config.partial_fixed_var_fraction),
                style=config.partial_context_style,
            )
            row = time_partial_context_workload(
                n,
                expr,
                contexts,
                trial=t,
                expr_style=expr_style,
                bit_env=bit_env_by_n.get(n),
                sample_rng=sample_rng,
                robdd_order_seed=(
                    int(config.robdd_order_seed)
                    if config.robdd_order_seed is not None
                    else int(seed + n * 1009 + t * 9176)
                ),
                config=config,
            )
            row.update(expr_diag)
            rows.append(row)
    df = pd.DataFrame(rows)

    def safe_median(s):
        try:
            return float(s.dropna().median())
        except Exception:
            return None

    def safe_first(s):
        try:
            vals = s.dropna().tolist()
            return vals[0] if vals else None
        except Exception:
            return None

    group_cols = ["n_vars", "expr_style", "partial_context_style", "partial_context_count", "partial_output_mode"]
    median_cols = [
        "partial_fixed_var_count_median",
        "partial_fixed_var_fraction_median",
        "partial_remaining_var_count_median",
        "partial_unique_contexts",
        "partial_repeated_contexts",
        "partial_context_overlap_ratio",
        "partial_bitset_full_recompute_total_s",
        "partial_bitset_restricted_total_s",
        "partial_cm_no_cache_total_s",
        "partial_cm_cache_total_s",
        "partial_robdd_total_s",
        "partial_cm_cache_compile_once_s",
        "partial_cm_cache_eval_contexts_total_s",
        "partial_robdd_build_once_s",
        "partial_robdd_restrict_contexts_total_s",
        "speedup_cm_cache_vs_cm_no_cache",
        "ratio_cm_cache_over_bitset_full_recompute",
        "ratio_cm_cache_over_bitset_restricted",
        "ratio_cm_cache_over_robdd_restrict",
        "partial_cm_cache_live_vars_median",
        "partial_cm_cache_live_vars_max",
        "partial_cm_no_cache_live_vars_median",
        "partial_cm_no_cache_live_vars_max",
        "partial_robdd_restricted_nodes_median",
        "partial_bitset_ok_rate",
        "partial_bitset_restricted_ok_rate",
        "partial_cm_no_cache_ok_rate",
        "partial_cm_cache_ok_rate",
        "partial_robdd_ok_rate",
    ]
    agg_spec: Dict[str, Any] = {f"{c}_median": (c, safe_median) for c in median_cols if c in df.columns}
    if "partial_robdd_backend" in df.columns:
        agg_spec["partial_robdd_backend"] = ("partial_robdd_backend", safe_first)
    agg_spec["trials"] = ("trial", "count")
    df_agg = df.groupby(group_cols).agg(**agg_spec).reset_index() if rows else pd.DataFrame()
    return df, df_agg


def print_partial_context_summary_table(df_agg):
    from cmbench.reporting.summary_tables import print_partial_context_summary_table as _print_partial_context_summary_table

    return _print_partial_context_summary_table(df_agg)


def _cm_family_workload(
    variants: List[Any],
    n_vars: int,
    *,
    persistent_cache: bool,
    tt_refs: List[Optional[np.ndarray]],
    sample_rng: np.random.Generator,
    config: BenchmarkConfig,
) -> Dict[str, Any]:
    clear_cm_ir_persistent_cache()
    vars_all = [f"x{i}" for i in range(n_vars)]
    total_t0 = time.perf_counter()
    per_variant: List[float] = []
    compile_times: List[float] = []
    eval_times: List[float] = []
    oks: List[Any] = []
    hits = 0
    misses = 0
    materializations: List[Optional[float]] = []
    live_vars_max: List[Optional[float]] = []
    for expr, tt_ref in zip(variants, tt_refs):
        diag: Dict[str, Any] = {"ir_timing_enabled": 1}
        t0 = time.perf_counter()
        c0 = time.perf_counter()
        node = compile_expr_to_cm_ir(expr, diagnostics=diag, persistent_cache=persistent_cache, reuse_cache=False)
        compile_wall = time.perf_counter() - c0
        e0 = time.perf_counter()
        res = materialize_hybrid_no_reinflate(
            node,
            vars_all,
            fixed={},
            diagnostics=diag,
            hybrid_threshold=config.cm_hybrid_threshold,
            words_eval=config.cm_words_eval,
            allow_reduced_output=bool(n_vars > config.cm_max_full_output_vars),
            max_full_output_vars=config.cm_max_full_output_vars,
        )
        eval_wall = time.perf_counter() - e0
        per_variant.append(time.perf_counter() - t0)
        compile_times.append(compile_wall)
        eval_times.append(eval_wall)
        hits += int(diag.get("ir_persistent_cache_hits", 0) or 0)
        misses += int(diag.get("ir_persistent_cache_misses", 0) or 0)
        materializations.append(float(diag.get("materializations", diag.get("cm_materializations", 0)) or 0))
        live_vars_max.append(float(diag.get("live_vars_max", diag.get("cm_live_vars_max", 0)) or 0))
        if tt_ref is not None:
            actual = bitset_to_bool_array(int(res.bits), n_vars) if res.bits is not None else res.tt
            oks.append(bool(actual is not None and np.array_equal(actual, tt_ref)))
        elif int(config.sampled_correctness or 0) > 0:
            check = sampled_correctness_check(expr, res, n_vars, int(config.sampled_correctness), sample_rng)
            oks.append(int(check.get("sampled_correctness_mismatches") or 0) == 0)
        else:
            oks.append(None)
    prefix = "family_cm_cache" if persistent_cache else "family_cm_no_cache"
    stats = cm_ir_persistent_cache_stats() if persistent_cache else {"ir_persistent_cache_size": 0}
    return {
        f"{prefix}_total_time_s": float(time.perf_counter() - total_t0),
        f"{prefix}_per_variant_median_s": _median_or_none(per_variant),
        f"{prefix}_per_variant_mean_s": _mean_or_none(per_variant),
        f"{prefix}_compile_total_s": float(sum(compile_times)),
        f"{prefix}_eval_total_s": float(sum(eval_times)),
        f"{prefix}_ok_rate": _ok_rate(oks),
        f"{prefix}_materializations_total": float(sum(v for v in materializations if v is not None)),
        f"{prefix}_live_vars_max_median": _median_or_none(live_vars_max),
        **(
            {
                "family_cm_cache_persistent_hits_total": int(hits),
                "family_cm_cache_persistent_misses_total": int(misses),
                "family_cm_cache_cache_size_final": int(stats.get("ir_persistent_cache_size", 0)),
            }
            if persistent_cache
            else {}
        ),
    }


def _robdd_family_shared_manager(
    variants: List[Any],
    n_vars: int,
    *,
    backend: str,
    order_policy: str,
    order_seed: Optional[int],
) -> Dict[str, Any]:
    dd_module, error = select_dd_module(backend)
    if dd_module is None:
        return {
            "family_robdd_shared_manager_total_time_s": None,
            "family_robdd_shared_manager_node_count_final": None,
            "family_robdd_shared_manager_status": "unavailable",
            "family_robdd_shared_manager_error": error,
        }
    try:
        manager = dd_module.BDD()
        order = robdd_variable_order(variants[0], n_vars, order_policy if order_policy != "best-of-k" else "fixed", order_seed)
        _declare_dd_vars(manager, order)
        names = [f"x{i}" for i in range(n_vars)]
        roots = []
        t0 = time.perf_counter()
        for expr in variants:
            roots.append(expr_to_dd_bdd(expr, manager, {name: name for name in names}))
        total = time.perf_counter() - t0
        root = roots[-1] if roots else None
        return {
            "family_robdd_shared_manager_total_time_s": float(total),
            "family_robdd_shared_manager_node_count_final": safe_bdd_node_count(manager, root) if root is not None else None,
            "family_robdd_shared_manager_status": "ok",
            "family_robdd_shared_manager_error": None,
        }
    except Exception as exc:
        return {
            "family_robdd_shared_manager_total_time_s": None,
            "family_robdd_shared_manager_node_count_final": None,
            "family_robdd_shared_manager_status": "error",
            "family_robdd_shared_manager_error": repr(exc),
        }


def time_expression_family_workload(
    n_vars: int,
    family: Dict[str, Any],
    *,
    family_id: str,
    trial: int,
    expr_style: str,
    variant_style: str,
    mutation_rate: float,
    bit_env: Optional[Mapping[str, int]],
    sample_rng: np.random.Generator,
    robdd_order_seed: Optional[int],
    config: Optional[BenchmarkConfig] = None,
) -> Dict[str, Any]:
    config = config or (config_from_args(args) if args is not None else None)
    if config is None:
        raise ValueError("config is required when global args is not initialized")
    variants = list(family["variants"])
    full_tt_max_n = int(config.full_tt_max_n)
    build_tt = n_vars <= full_tt_max_n
    tt_refs = [eval_expr_tt(expr, n_vars).astype(np.uint8).reshape(-1) if build_tt else None for expr in variants]
    row = {
        "n_vars": int(n_vars),
        "trial": int(trial),
        "expr_style": expr_style,
        "family_tt_refs_available_count": int(sum(ref is not None for ref in tt_refs)),
        "family_tt_ref_source": "eval_expr_tt" if build_tt else "not_built",
        "family_correctness_reference": (
            "eval_expr_tt"
            if build_tt
            else ("sampled_assignments" if int(config.sampled_correctness or 0) > 0 else "skipped_large_n")
        ),
        **expression_family_diagnostics(
            family,
            n_vars,
            family_id=family_id,
            variant_style=variant_style,
            mutation_rate=mutation_rate,
        ),
    }

    if not bool(config.no_bitset):
        # Same engine precedence as the single-expression control: words > flat >
        # recursive, so the family control matches the engine the CM side gets.
        names = tuple(f"x{i}" for i in range(n_vars))
        use_words_bitset = bool(config.cm_words_eval)
        use_flat_bitset = bool(config.cm_flat_eval or use_words_bitset)
        family_bitset_baseline_kind = (
            "raw_ast_words" if use_words_bitset else "raw_ast_flat" if use_flat_bitset else "raw_ast_recursive"
        )
        env = None
        if not use_flat_bitset:
            env = bit_env if bit_env is not None else build_bitset_env(list(names))
        times: List[float] = []
        oks: List[Any] = []
        total0 = time.perf_counter()
        for expr, tt_ref in zip(variants, tt_refs):
            t0 = time.perf_counter()
            if use_words_bitset:
                bits = eval_expr_words_bitset(expr, names)
            elif use_flat_bitset:
                bits = eval_expr_flat_bitset(expr, names)
            else:
                bits = eval_expr_bitset(expr, env)
            times.append(time.perf_counter() - t0)
            if tt_ref is not None:
                oks.append(bool(np.array_equal(bitset_to_bool_array(int(bits), n_vars), tt_ref)))
            else:
                oks.append(None)
        row.update(
            {
                "family_bitset_baseline_kind": family_bitset_baseline_kind,
                "family_bitset_total_time_s": float(time.perf_counter() - total0),
                "family_bitset_per_variant_median_s": _median_or_none(times),
                "family_bitset_per_variant_mean_s": _mean_or_none(times),
                "family_bitset_ok_rate": _ok_rate(oks),
            }
        )
    else:
        row.update(
            {
                "family_bitset_baseline_kind": None,
                "family_bitset_total_time_s": None,
                "family_bitset_per_variant_median_s": None,
                "family_bitset_per_variant_mean_s": None,
                "family_bitset_ok_rate": None,
            }
        )

    row.update(
        _cm_family_workload(
            variants,
            n_vars,
            persistent_cache=False,
            tt_refs=tt_refs,
            sample_rng=sample_rng,
            config=config,
        )
    )
    if bool(config.cm_use_persistent_cache):
        row.update(
            _cm_family_workload(
                variants,
                n_vars,
                persistent_cache=True,
                tt_refs=tt_refs,
                sample_rng=sample_rng,
                config=config,
            )
        )
    else:
        row.update(skipped_family_backend("family_cm_cache", reason="disabled"))

    if (
        (not bool(config.family_no_robdd))
        and (not bool(config.no_dd))
        and (not bool(config.no_robdd_dd))
    ):
        robdd_times: List[Optional[float]] = []
        robdd_nodes: List[Optional[float]] = []
        robdd_oks: List[Any] = []
        robdd_backend = None
        total0 = time.perf_counter()
        for i, (expr, tt_ref) in enumerate(zip(variants, tt_refs)):
            res = run_robdd_dd_backend(
                expr,
                n_vars,
                backend_preference=str(config.robdd_dd_backend),
                order_policy=str(config.robdd_order_policy),
                dynamic_reordering=bool(config.robdd_dynamic_reordering),
                reorder_method=str(config.robdd_reorder_method),
                order_seed=(None if robdd_order_seed is None else int(robdd_order_seed + i)),
                order_sweeps=int(config.robdd_order_sweeps),
                tt_ref=tt_ref,
                correctness_rng=sample_rng,
                correctness_samples=int(config.sampled_correctness or (0 if build_tt else 256)),
                measure_tt_extract=False,
            )
            robdd_times.append(res.get("robdd_build_time_s"))
            robdd_nodes.append(res.get("robdd_node_count"))
            robdd_oks.append(res.get("robdd_ok"))
            robdd_backend = robdd_backend or res.get("robdd_backend") or res.get("robdd_backend_preference")
        row.update(
            {
                "family_robdd_backend": robdd_backend or str(config.robdd_dd_backend),
                "family_robdd_build_total_time_s": float(sum(float(v) for v in robdd_times if v is not None)),
                "family_robdd_build_wall_time_s": float(time.perf_counter() - total0),
                "family_robdd_build_per_variant_median_s": _median_or_none(robdd_times),
                "family_robdd_nodes_median": _median_or_none(robdd_nodes),
                "family_robdd_nodes_total_or_manager_if_shared": float(sum(float(v) for v in robdd_nodes if v is not None)),
                "family_robdd_ok_rate": _ok_rate(robdd_oks),
            }
        )
        if bool(config.family_robdd_shared_manager):
            row.update(
                _robdd_family_shared_manager(
                    variants,
                    n_vars,
                    backend=str(config.robdd_dd_backend),
                    order_policy=str(config.robdd_order_policy),
                    order_seed=robdd_order_seed,
                )
            )
    else:
        skipped = skipped_family_backend(
            "family_robdd",
            reason="skipped" if bool(config.family_no_robdd) else "disabled",
        )
        skipped["family_robdd_backend"] = str(config.robdd_dd_backend)
        row.update(skipped)

    row["ratio_cm_cache_over_cm_no_cache"] = _ratio_or_none(
        row.get("family_cm_cache_total_time_s"), row.get("family_cm_no_cache_total_time_s")
    )
    ratio = row["ratio_cm_cache_over_cm_no_cache"]
    row["speedup_cm_cache_vs_cm_no_cache"] = (1.0 / ratio) if ratio and ratio > 0 else None
    row["ratio_cm_cache_over_bitset"] = _ratio_or_none(row.get("family_cm_cache_total_time_s"), row.get("family_bitset_total_time_s"))
    row["ratio_cm_no_cache_over_bitset"] = _ratio_or_none(
        row.get("family_cm_no_cache_total_time_s"), row.get("family_bitset_total_time_s")
    )
    return row


def run_expression_family_bench(
    sizes: List[int],
    trials: int,
    seed: int,
    max_depth: int,
    verbose: bool,
    config: Optional[BenchmarkConfig] = None,
    ctx: Optional[BenchmarkRunContext] = None,
):
    import pandas as pd

    config = config or (config_from_args(args) if args is not None else None)
    if config is None:
        raise ValueError("config is required when global args is not initialized")
    ctx = ctx or make_context(config, detect_backends())
    family_seed = int(config.family_seed or seed)
    rng = np.random.default_rng(family_seed)
    sample_rng = np.random.default_rng(seed + 2_000_003)
    expr_style = config.expr_style
    bit_env_by_n: Dict[int, Mapping[str, int]] = {}
    if not config.no_bitset:
        for n in sizes:
            bit_env_by_n[n] = build_bitset_env([f"x{i}" for i in range(n)])

    rows: List[Dict[str, Any]] = []
    for n in sizes:
        if verbose:
            print(f"\n=== expression family n = {n} ===")
        for t in range(trials):
            family_id = f"family_n{n}_t{t}_seed{family_seed}"
            family = generate_expression_family(
                n,
                rng,
                max_depth,
                expr_style,
                family_size=config.family_size,
                variant_style=config.family_variant_style,
                shared_blocks=config.family_shared_blocks,
                mutation_rate=config.family_mutation_rate,
                force_shared_substructure=config.family_force_shared_substructure,
            )
            if verbose:
                print(f"  Trial {t + 1}/{trials}: {len(family['variants'])} variants")
            row = time_expression_family_workload(
                n,
                family,
                family_id=family_id,
                trial=t,
                expr_style=expr_style,
                variant_style=config.family_variant_style,
                mutation_rate=config.family_mutation_rate,
                bit_env=bit_env_by_n.get(n),
                sample_rng=sample_rng,
                robdd_order_seed=(
                    int(config.robdd_order_seed)
                    if config.robdd_order_seed is not None
                    else int(seed + n * 1009 + t * 9176)
                ),
                config=config,
            )
            rows.append(row)

    df = pd.DataFrame(rows)

    def safe_median(s):
        try:
            return float(s.dropna().median())
        except Exception:
            return None

    def safe_first(s):
        try:
            vals = s.dropna().tolist()
            return vals[0] if vals else None
        except Exception:
            return None

    group_cols = ["n_vars", "expr_style", "family_variant_style", "family_size"]
    median_cols = [
        "family_reuse_ratio",
        "family_unique_subtree_hashes",
        "family_repeated_subtree_hash_count",
        "family_max_subtree_reuse_count",
        "family_bitset_total_time_s",
        "family_cm_no_cache_total_time_s",
        "family_cm_cache_total_time_s",
        "family_robdd_build_total_time_s",
        "speedup_cm_cache_vs_cm_no_cache",
        "ratio_cm_cache_over_bitset",
        "ratio_cm_no_cache_over_bitset",
        "family_cm_cache_persistent_hits_total",
        "family_cm_cache_persistent_misses_total",
        "family_bitset_ok_rate",
        "family_cm_no_cache_ok_rate",
        "family_cm_cache_ok_rate",
        "family_robdd_ok_rate",
    ]
    agg_spec: Dict[str, Any] = {f"{c}_median": (c, safe_median) for c in median_cols if c in df.columns}
    if "family_robdd_backend" in df.columns:
        agg_spec["family_robdd_backend"] = ("family_robdd_backend", safe_first)
    agg_spec["trials"] = ("trial", "count")
    df_agg = df.groupby(group_cols).agg(**agg_spec).reset_index() if rows else pd.DataFrame()
    return df, df_agg


def print_expression_family_summary_table(df_agg):
    from cmbench.reporting.summary_tables import print_expression_family_summary_table as _print_expression_family_summary_table

    return _print_expression_family_summary_table(df_agg)


def get_eval_grid(n: int) -> np.ndarray:
    G = _GRID_CACHE.get(n)
    if G is not None:
        return G
    L = 1 << n
    A = np.zeros((L, n), dtype=np.uint8)
    for v in range(n):
        block = 1 << (n - 1 - v)
        pattern = np.concatenate([np.zeros(block, dtype=np.uint8), np.ones(block, dtype=np.uint8)])
        reps = L // (2 * block)
        A[:, v] = np.tile(pattern, reps)
    _GRID_CACHE[n] = A
    return A


def cm_matrix_to_tt(M_cm: np.ndarray, R: List[str], C: List[str], n_vars: int) -> np.ndarray:
    """Project padded CM matrix back to TT over x0..x{n-1} in eval_expr_tt order."""
    vars_all = list(R) + list(C)
    arr = M_cm.reshape((2,) * len(vars_all))

    for axis in range(len(vars_all) - 1, -1, -1):
        if vars_all[axis].startswith("__pad"):
            arr = np.take(arr, 0, axis=axis)
            vars_all.pop(axis)

    expected_vars = [f"x{i}" for i in range(n_vars)]
    if vars_all != expected_vars:
        perm = [vars_all.index(v) for v in expected_vars]
        arr = np.transpose(arr, axes=perm)
    return arr.reshape(-1).astype(np.uint8, copy=False)


def _bit_reverse(i: int, nbits: int) -> int:
    x = 0
    for k in range(nbits):
        x = (x << 1) | ((int(i) >> k) & 1)
    return x


@dataclass(frozen=True)
class SingleExprOptions:
    full_tt_max_n: int
    build_tt: bool
    large_n_safe: bool
    eval_repeat: int
    run_sympy: bool
    run_espresso: bool
    use_lazy_builder: bool
    cm_exec_target: str
    use_remote_no_reinflate: bool


def _single_expr_options(n: int, use_espresso: bool, config: BenchmarkConfig) -> SingleExprOptions:
    full_tt_max_n = int(config.full_tt_max_n)
    build_tt = n <= full_tt_max_n
    eval_repeat = int(config.cm_eval_repeat)
    if eval_repeat < 1:
        raise ValueError("--cm-eval-repeat must be >= 1")
    cm_exec_target = str(config.cm_exec_target)
    return SingleExprOptions(
        full_tt_max_n=full_tt_max_n,
        build_tt=build_tt,
        large_n_safe=bool(config.large_n_safe) and (not build_tt) and bool(config.cm_compare_no_reinflate),
        eval_repeat=eval_repeat,
        run_sympy=build_tt,
        run_espresso=bool(use_espresso) and build_tt,
        use_lazy_builder=bool(HAS_LAZY and config.cm_lazy),
        cm_exec_target=cm_exec_target,
        use_remote_no_reinflate=cm_exec_target == "runpod" and bool(config.cm_compare_no_reinflate),
    )


def _init_single_expr_diagnostics(config: BenchmarkConfig) -> Dict[str, Dict[str, Any]]:
    diagnostics: Dict[str, Dict[str, Any]] = {
        "cm": {},
        "cm_hybrid": {},
        "cm_partial_hybrid": {},
        "cm_hybrid_no_reinflate": {},
        "cm_parallel": {},
    }
    if bool(config.cm_report_ir_breakdown or config.cm_compile_once_per_expression):
        for diag in diagnostics.values():
            diag["ir_timing_enabled"] = 1
    return diagnostics


def _ensure_tt_ref(expr, n: int, build_tt: bool, tt_ref: Optional[np.ndarray]) -> Tuple[Optional[np.ndarray], str]:
    if tt_ref is not None:
        return tt_ref, "generate_benchmark_expr"
    if build_tt:
        return eval_expr_tt(expr, n).astype(np.uint8).reshape(-1), "computed_in_time_backends"
    return None, "not_built"


def time_backends_on_expr(
    n: int,
    expr,
    use_dd: bool,
    use_espresso: bool,
    verbose: bool,
    bit_env: Optional[Mapping[str, int]] = None,
    sample_rng: Optional[np.random.Generator] = None,
    robdd_order_seed: Optional[int] = None,
    tt_ref: Optional[np.ndarray] = None,
    config: Optional[BenchmarkConfig] = None,
    ctx: Optional[BenchmarkRunContext] = None,
) -> Dict[str, Any]:
    config = config or (config_from_args(args) if args is not None else None)
    if config is None:
        raise ValueError("config is required when global args is not initialized")
    ctx = ctx or make_context(config, detect_backends())
    options = _single_expr_options(n, use_espresso, config)
    full_tt_max_n = options.full_tt_max_n
    build_tt = options.build_tt
    tt_ref_source = "generate_benchmark_expr" if tt_ref is not None else "not_built"
    large_n_safe = options.large_n_safe
    eval_repeat = options.eval_repeat
    run_sympy = options.run_sympy
    run_espresso = options.run_espresso
    use_lazy_builder = options.use_lazy_builder

    tt = None
    t_cm = None
    cm_tt_extract_time = None
    cm_ok = None
    cm_exec_only_time = None
    cm_hybrid_time = None
    cm_hybrid_tt_extract_time = None
    cm_hybrid_ok = None
    cm_hybrid_exec_only_time = None
    cm_partial_hybrid_time = None
    cm_partial_hybrid_tt_extract_time = None
    cm_partial_hybrid_ok = None
    cm_partial_hybrid_exec_only_time = None
    cm_hybrid_no_reinflate_time = None
    cm_hybrid_no_reinflate_tt_extract_time = None
    cm_hybrid_no_reinflate_ok = None
    cm_hybrid_no_reinflate_declined = False if config.cm_compare_no_reinflate else None
    cm_hybrid_no_reinflate_exec_only_time = None
    cm_hybrid_no_reinflate_cached_exec_only_time = None
    cm_runpod_pod_started = None
    cm_runpod_ready_wait_time_s = None
    cm_runpod_request_time_s = None
    cm_runpod_remote_exec_time_s = None
    cm_runpod_total_wall_time_s = None
    cm_runpod_result_repr = None
    cm_runpod_final_cm_materialized = None
    cm_runpod_fallback_local = False
    cm_runpod_status = None
    cm_runpod_error = None
    bitset_baseline_kind = "raw_ast_recursive"
    sampled_correctness_samples = 0
    sampled_correctness_mismatches = None
    sampled_correctness_mismatch_rate = None
    cm_parallel_time = None
    cm_parallel_tt_extract_time = None
    cm_parallel_ok = None
    node_count = count_expr_nodes(expr)
    bitset_extract_time = None
    bitset_cached_exec_only_time = None
    bitset_time = None
    bitset_ok = None
    numba_time = None
    numba_ok = None
    numba_compile_time = None
    sympy_time = None
    sympy_ok = None
    bdd_sop_time = None
    bdd_sop_ok = None
    espresso_time = None
    espresso_ok = None
    pair_attempts: Optional[int] = None
    pair_collapses: Optional[int] = None
    pair_ratio: Optional[float] = None
    pair_nodes_total: Optional[int] = None

    diagnostics = _init_single_expr_diagnostics(config)
    cm_diag = diagnostics["cm"]
    cm_hybrid_diag = diagnostics["cm_hybrid"]
    cm_partial_hybrid_diag = diagnostics["cm_partial_hybrid"]
    cm_hybrid_no_reinflate_diag = diagnostics["cm_hybrid_no_reinflate"]
    cm_parallel_diag = diagnostics["cm_parallel"]
    norm_before = cm_normalize_cache_stats() if config.cm_debug_stats else None
    lazy_before = (
        lazy_align_cache_stats() if (config.cm_debug_stats and HAS_LAZY and callable(lazy_align_cache_stats)) else None
    )
    enable_ir_timing = bool(config.cm_report_ir_breakdown or config.cm_compile_once_per_expression)

    def _enable_ir(diag: Dict[str, Any]) -> None:
        if enable_ir_timing:
            diag["ir_timing_enabled"] = 1

    cm_exec_target = options.cm_exec_target
    use_remote_no_reinflate = options.use_remote_no_reinflate

    if build_tt:
        if verbose:
            print(f"[n={n}] CM compile ...")
        R, C = ctx.canonical_layout(n, config.cm_layout)

        use_compile_once = bool(config.cm_compile_once_per_expression) and (not bool(config.cm_pair))
        reuse_compiled_ir = bool(config.cm_reuse_compiled_ir)
        use_persistent_cache = bool(config.cm_use_persistent_cache)

        def run_cm(materialize_mode: str, diag: Dict[str, Any], *, use_pair_backend: bool = False) -> np.ndarray:
            if use_pair_backend and HAS_PAIR and callable(compile_expr_to_cm_pair):
                M_pair, pm = compile_expr_to_cm_pair(
                    expr,
                    R,
                    C,
                    fixed={},
                    diagnostics=diag,
                    materialize_mode=materialize_mode,
                    hybrid_threshold=config.cm_hybrid_threshold,
                )
                # Record metrics only once; we run this function multiple times in compare modes.
                nonlocal pair_attempts, pair_collapses, pair_ratio, pair_nodes_total
                if pair_attempts is None:
                    pair_attempts = int(pm.get("pair_attempts", 0))
                    pair_collapses = int(pm.get("pair_collapses", 0))
                    pair_ratio = float(pm.get("pairable_ratio", 0.0))
                    pair_nodes_total = int(pm.get("nodes_total", 0))
                return M_pair
            if use_lazy_builder:
                return compile_expr_to_cm_lazy(
                    expr,
                    R,
                    C,
                    fixed={},
                    diagnostics=diag,
                    materialize_mode=materialize_mode,
                    hybrid_threshold=config.cm_hybrid_threshold,
                    reuse_compiled_ir=reuse_compiled_ir,
                    use_persistent_cache=use_persistent_cache,
                )
            return compile_expr_to_cm(
                expr,
                R,
                C,
                fixed={},
                diagnostics=diag,
                materialize_mode=materialize_mode,
                hybrid_threshold=config.cm_hybrid_threshold,
                reuse_compiled_ir=reuse_compiled_ir,
                use_persistent_cache=use_persistent_cache,
            )

        cm_mode = "numpy" if config.cm_compare_hybrid else "partial_hybrid"

        if use_compile_once:
            if verbose:
                print(f"[n={n}] CM IR compile-once enabled")
            compile_diag: Dict[str, Any] = {}
            _enable_ir(compile_diag)
            node = compile_expr_to_cm_ir(
                expr,
                diagnostics=compile_diag,
                reuse_cache=reuse_compiled_ir,
                persistent_cache=use_persistent_cache,
            )
            ir_compile_time = float(compile_diag.get("ir_compile_time_s", 0.0))

            def _stamp_compile_reuse(diag: Dict[str, Any]) -> None:
                if enable_ir_timing:
                    for k, v in compile_diag.items():
                        if isinstance(k, str) and k.startswith("ir_"):
                            diag[k] = v
                    diag["ir_compile_calls_per_expr"] = 1
                    diag["ir_compile_reused_for_mode"] = 1

            _stamp_compile_reuse(cm_diag)
            t_exec0 = time.perf_counter()
            M_cm = materialize_cm(
                node,
                R,
                C,
                fixed={},
                diagnostics=cm_diag,
                materialize_mode=cm_mode,
                hybrid_threshold=config.cm_hybrid_threshold,
            )
            cm_exec_only_time = time.perf_counter() - t_exec0
            t_cm = ir_compile_time + cm_exec_only_time
        else:
            t0 = time.perf_counter()
            M_cm = run_cm(cm_mode, cm_diag, use_pair_backend=bool(config.cm_pair))
            t_cm = time.perf_counter() - t0

        ttt0 = time.perf_counter()
        tt = cm_matrix_to_tt(M_cm, R, C, n)
        cm_tt_extract_time = time.perf_counter() - ttt0
        try:
            tt_ref, tt_ref_source = _ensure_tt_ref(expr, n, build_tt, tt_ref)
            cm_ok = bool(np.array_equal(tt, tt_ref))
        except Exception:
            cm_ok = False

        if config.cm_compare_no_reinflate and not use_remote_no_reinflate:
            if verbose:
                print(f"[n={n}] CM hybrid (no reinflate) compile ...")
            vars_all = [f"x{i}" for i in range(n)]
            if use_compile_once:
                _stamp_compile_reuse(cm_hybrid_no_reinflate_diag)
                t_exec0 = time.perf_counter()
                res_nr = materialize_hybrid_no_reinflate(
                    node,
                    vars_all,
                    fixed={},
                    diagnostics=cm_hybrid_no_reinflate_diag,
                    hybrid_threshold=config.cm_hybrid_threshold,
                    words_eval=config.cm_words_eval,
                )
                cm_hybrid_no_reinflate_exec_only_time = time.perf_counter() - t_exec0
                cm_hybrid_no_reinflate_time = ir_compile_time + cm_hybrid_no_reinflate_exec_only_time
            else:
                t0nr = time.perf_counter()
                node_nr = compile_expr_to_cm_ir(
                    expr,
                    diagnostics=cm_hybrid_no_reinflate_diag,
                    reuse_cache=reuse_compiled_ir,
                    persistent_cache=use_persistent_cache,
                )
                res_nr = materialize_hybrid_no_reinflate(
                    node_nr,
                    vars_all,
                    fixed={},
                    diagnostics=cm_hybrid_no_reinflate_diag,
                    hybrid_threshold=config.cm_hybrid_threshold,
                    words_eval=config.cm_words_eval,
                )
                cm_hybrid_no_reinflate_time = time.perf_counter() - t0nr
            cm_hybrid_no_reinflate_tt_extract_time = 0.0
            if tt_ref is not None:
                if res_nr.bits is not None:
                    tt_nr = bitset_to_bool_array(int(res_nr.bits), n)
                else:
                    tt_nr = res_nr.tt
                cm_hybrid_no_reinflate_ok = bool(tt_nr is not None and np.array_equal(tt_nr, tt_ref))
            else:
                cm_hybrid_no_reinflate_ok = False

            sampled_k = int(config.sampled_correctness)
            if sampled_k > 0:
                check = sampled_correctness_check(
                    expr,
                    res_nr,
                    n,
                    sampled_k,
                    sample_rng if sample_rng is not None else np.random.default_rng(0),
                )
                sampled_correctness_samples = check["sampled_correctness_samples"]
                sampled_correctness_mismatches = check["sampled_correctness_mismatches"]
                sampled_correctness_mismatch_rate = check["sampled_correctness_mismatch_rate"]

            if eval_repeat > 1:
                node_repeat = node if use_compile_once else node_nr
                profile_diag: Optional[Dict[str, Any]]
                profile_diag = (
                    {"cached_exec_profile_enabled": 1}
                    if bool(config.cm_profile_cached_exec)
                    else None
                )
                t_rep0 = time.perf_counter()
                for _ in range(eval_repeat):
                    _ = materialize_hybrid_no_reinflate(
                        node_repeat,
                        vars_all,
                        fixed={},
                        diagnostics=profile_diag,
                        hybrid_threshold=config.cm_hybrid_threshold,
                        words_eval=config.cm_words_eval,
                    )
                cm_hybrid_no_reinflate_cached_exec_only_time = (time.perf_counter() - t_rep0) / float(eval_repeat)
                if profile_diag is not None:
                    for k, v in profile_diag.items():
                        if k.startswith("cached_exec_"):
                            cm_hybrid_no_reinflate_diag[k] = v

        if config.cm_compare_hybrid:
            if verbose:
                print(f"[n={n}] CM hybrid compile ...")
            if use_compile_once:
                _stamp_compile_reuse(cm_hybrid_diag)
                t_exec0 = time.perf_counter()
                M_cmh = materialize_cm(
                    node,
                    R,
                    C,
                    fixed={},
                    diagnostics=cm_hybrid_diag,
                    materialize_mode="hybrid",
                    hybrid_threshold=config.cm_hybrid_threshold,
                )
                cm_hybrid_exec_only_time = time.perf_counter() - t_exec0
                cm_hybrid_time = ir_compile_time + cm_hybrid_exec_only_time
            else:
                t0h = time.perf_counter()
                M_cmh = run_cm("hybrid", cm_hybrid_diag)
                cm_hybrid_time = time.perf_counter() - t0h
            thtt0 = time.perf_counter()
            tt_cmh = cm_matrix_to_tt(M_cmh, R, C, n)
            cm_hybrid_tt_extract_time = time.perf_counter() - thtt0
            if tt_ref is not None:
                cm_hybrid_ok = bool(np.array_equal(tt_cmh, tt_ref))
            else:
                cm_hybrid_ok = False

            if verbose:
                print(f"[n={n}] CM partial hybrid compile ...")
            if use_compile_once:
                _stamp_compile_reuse(cm_partial_hybrid_diag)
                t_exec0 = time.perf_counter()
                M_cmph = materialize_cm(
                    node,
                    R,
                    C,
                    fixed={},
                    diagnostics=cm_partial_hybrid_diag,
                    materialize_mode="partial_hybrid",
                    hybrid_threshold=config.cm_hybrid_threshold,
                )
                cm_partial_hybrid_exec_only_time = time.perf_counter() - t_exec0
                cm_partial_hybrid_time = ir_compile_time + cm_partial_hybrid_exec_only_time
            else:
                t0ph = time.perf_counter()
                M_cmph = run_cm("partial_hybrid", cm_partial_hybrid_diag)
                cm_partial_hybrid_time = time.perf_counter() - t0ph
            tph_tt0 = time.perf_counter()
            tt_cmph = cm_matrix_to_tt(M_cmph, R, C, n)
            cm_partial_hybrid_tt_extract_time = time.perf_counter() - tph_tt0
            if tt_ref is not None:
                cm_partial_hybrid_ok = bool(np.array_equal(tt_cmph, tt_ref))
            else:
                cm_partial_hybrid_ok = False

        if config.cm_parallel:
            try:
                if verbose:
                    print(f"[n={n}] CM parallel compile ...")
                t0p = time.perf_counter()
                M_cmp = compile_expr_to_cm_parallel(
                    expr,
                    R,
                    C,
                    fixed={},
                    use_lazy=use_lazy_builder,
                    workers=config.cm_parallel_workers if config.cm_parallel_workers > 0 else None,
                    min_n=config.cm_parallel_min_n,
                    min_nodes=config.cm_parallel_min_nodes,
                    chunk_rows=config.cm_parallel_chunk_rows,
                    chunk_elems=config.cm_parallel_chunk_elems,
                    min_parallel_work_elems=config.cm_parallel_min_work_elems,
                    reuse_pool=not config.cm_parallel_no_reuse_pool,
                    use_shared_memory=not config.cm_parallel_no_shared_memory,
                    shared_min_cells=config.cm_parallel_shared_min_cells,
                    diagnostics=cm_parallel_diag,
                    materialize_mode="partial_hybrid",
                    hybrid_threshold=config.cm_hybrid_threshold,
                    reuse_compiled_ir=reuse_compiled_ir,
                    use_persistent_cache=use_persistent_cache,
                )
                cm_parallel_time = time.perf_counter() - t0p
                tptt0 = time.perf_counter()
                tt_cmp = cm_matrix_to_tt(M_cmp, R, C, n)
                cm_parallel_tt_extract_time = time.perf_counter() - tptt0
                if tt_ref is not None:
                    cm_parallel_ok = bool(np.array_equal(tt_cmp, tt_ref))
                else:
                    cm_parallel_ok = False
            except Exception:
                cm_parallel_time = None
                cm_parallel_tt_extract_time = None
                cm_parallel_ok = False

    if use_remote_no_reinflate and (build_tt or large_n_safe):
        if verbose:
            print(f"[n={n}] CM hybrid (no reinflate, RunPod) request ...")
        try:
            remote = execute_remote_cm(expr, n, large_n_safe=large_n_safe)
            response = remote.response
            cm_runpod_pod_started = int(bool(remote.pod_started))
            cm_runpod_ready_wait_time_s = float(remote.ready_wait_time_s)
            cm_runpod_request_time_s = float(remote.request_time_s)
            cm_runpod_total_wall_time_s = float(remote.total_wall_time_s)
            cm_runpod_remote_exec_time_s = float(response.timing.get("remote_exec_time_s", 0.0))
            cm_runpod_result_repr = response.result_repr
            cm_runpod_status = remote.status
            cm_runpod_error = response.error
            cm_runpod_final_cm_materialized = int(response.diagnostics.get("final_cm_materialization_performed", 0))
            cm_hybrid_no_reinflate_time = float(response.timing.get("remote_compile_time_s", 0.0)) + float(
                response.timing.get("remote_exec_time_s", 0.0)
            )
            cm_hybrid_no_reinflate_exec_only_time = float(response.timing.get("remote_exec_time_s", 0.0))
            cm_hybrid_no_reinflate_tt_extract_time = 0.0
            cm_hybrid_no_reinflate_ok = remote_response_matches_tt(response, tt_ref, n)
            for k, v in response.diagnostics.items():
                cm_hybrid_no_reinflate_diag[k] = v
        except Exception as exc:
            cm_runpod_status = "offline"
            cm_runpod_error = str(exc)
            if bool(config.cm_runpod_fallback_local):
                cm_runpod_fallback_local = True
                if verbose:
                    print(f"RunPod execution requested, but pod is unavailable/offline. Falling back to local: {exc}")
            else:
                if verbose:
                    print(f"RunPod execution requested, but pod is unavailable/offline. {exc}")

        if cm_runpod_fallback_local:
            vars_all = [f"x{i}" for i in range(n)]
            use_persistent_cache = bool(config.cm_use_persistent_cache)
            reuse_compiled_ir = bool(config.cm_reuse_compiled_ir)
            try:
                t0nr = time.perf_counter()
                node_nr = compile_expr_to_cm_ir(
                    expr,
                    diagnostics=cm_hybrid_no_reinflate_diag,
                    reuse_cache=reuse_compiled_ir,
                    persistent_cache=use_persistent_cache,
                )
                res_nr = materialize_hybrid_no_reinflate(
                    node_nr,
                    vars_all,
                    fixed={},
                    diagnostics=cm_hybrid_no_reinflate_diag,
                    hybrid_threshold=config.cm_hybrid_threshold,
                    words_eval=config.cm_words_eval,
                    allow_reduced_output=large_n_safe,
                    max_full_output_vars=int(config.cm_max_full_output_vars),
                )
                cm_hybrid_no_reinflate_time = time.perf_counter() - t0nr
                cm_hybrid_no_reinflate_exec_only_time = cm_hybrid_no_reinflate_time
                cm_hybrid_no_reinflate_tt_extract_time = 0.0
                if tt_ref is not None and res_nr.bits is not None:
                    cm_hybrid_no_reinflate_ok = bool(np.array_equal(bitset_to_bool_array(int(res_nr.bits), n), tt_ref))
                elif tt_ref is not None and res_nr.tt is not None:
                    cm_hybrid_no_reinflate_ok = bool(np.array_equal(res_nr.tt, tt_ref))
                else:
                    cm_hybrid_no_reinflate_ok = True if large_n_safe else None
            except Exception as fallback_exc:
                cm_hybrid_no_reinflate_declined = isinstance(fallback_exc, ValueError) and str(
                    fallback_exc
                ).startswith("refusing to materialize reduced no-reinflate output")
                cm_runpod_status = "fallback_error"
                cm_runpod_error = f"{cm_runpod_error}; fallback failed: {fallback_exc}"
                cm_hybrid_no_reinflate_ok = False

    if large_n_safe and not use_remote_no_reinflate:
        if verbose:
            print(f"[n={n}] CM hybrid (no reinflate, large-n safe) compile ...")
        vars_all = [f"x{i}" for i in range(n)]
        use_persistent_cache = bool(config.cm_use_persistent_cache)
        reuse_compiled_ir = bool(config.cm_reuse_compiled_ir)
        max_full_output_vars = int(config.cm_max_full_output_vars)
        try:
            t0nr = time.perf_counter()
            node_nr = compile_expr_to_cm_ir(
                expr,
                diagnostics=cm_hybrid_no_reinflate_diag,
                reuse_cache=reuse_compiled_ir,
                persistent_cache=use_persistent_cache,
            )
            res_nr = materialize_hybrid_no_reinflate(
                node_nr,
                vars_all,
                fixed={},
                diagnostics=cm_hybrid_no_reinflate_diag,
                hybrid_threshold=config.cm_hybrid_threshold,
                words_eval=config.cm_words_eval,
                allow_reduced_output=True,
                max_full_output_vars=max_full_output_vars,
            )
            cm_hybrid_no_reinflate_time = time.perf_counter() - t0nr
            cm_hybrid_no_reinflate_tt_extract_time = 0.0

            output_vars = tuple(res_nr.output_vars)
            if not config.no_bitset:
                # Fair matched-scope control: flatten the original Expr, not the already
                # canonicalized CM DAG. Variables proven irrelevant by CM are fixed to an
                # arbitrary value; invariance is checked against the CM result below.
                raw_fixed = {name: 0 for name in vars_all if name not in output_vars}
                use_words_bitset = bool(config.cm_words_eval)
                bitset_baseline_kind = (
                    "raw_ast_words_matched_scope"
                    if use_words_bitset
                    else "raw_ast_flat_matched_scope"
                )
                t7 = time.perf_counter()
                bitset_tt = (
                    eval_expr_words_bitset(expr, output_vars, fixed=raw_fixed)
                    if use_words_bitset
                    else eval_expr_flat_bitset(expr, output_vars, fixed=raw_fixed)
                )
                bitset_time = time.perf_counter() - t7
                if res_nr.bits is not None:
                    cm_hybrid_no_reinflate_ok = bool(int(res_nr.bits) == int(bitset_tt))
                elif res_nr.tt is not None and len(output_vars) <= full_tt_max_n:
                    tt_bitset = bitset_to_bool_array(bitset_tt, len(output_vars))
                    cm_hybrid_no_reinflate_ok = bool(np.array_equal(res_nr.tt, tt_bitset))
                else:
                    cm_hybrid_no_reinflate_ok = True
                bitset_ok = True

                if eval_repeat > 1:
                    t7r = time.perf_counter()
                    for _ in range(eval_repeat):
                        if use_words_bitset:
                            _ = eval_expr_words_bitset(expr, output_vars, fixed=raw_fixed)
                        else:
                            _ = eval_expr_flat_bitset(expr, output_vars, fixed=raw_fixed)
                    bitset_cached_exec_only_time = (time.perf_counter() - t7r) / float(eval_repeat)
            else:
                cm_hybrid_no_reinflate_ok = True

            sampled_k = int(config.sampled_correctness)
            if sampled_k > 0:
                check = sampled_correctness_check(
                    expr,
                    res_nr,
                    n,
                    sampled_k,
                    sample_rng if sample_rng is not None else np.random.default_rng(0),
                )
                sampled_correctness_samples = check["sampled_correctness_samples"]
                sampled_correctness_mismatches = check["sampled_correctness_mismatches"]
                sampled_correctness_mismatch_rate = check["sampled_correctness_mismatch_rate"]

            if eval_repeat > 1:
                profile_diag: Optional[Dict[str, Any]]
                profile_diag = (
                    {"cached_exec_profile_enabled": 1}
                    if bool(config.cm_profile_cached_exec)
                    else None
                )
                t_rep0 = time.perf_counter()
                for _ in range(eval_repeat):
                    _ = materialize_hybrid_no_reinflate(
                        node_nr,
                        vars_all,
                        fixed={},
                        diagnostics=profile_diag,
                        hybrid_threshold=config.cm_hybrid_threshold,
                        words_eval=config.cm_words_eval,
                        allow_reduced_output=True,
                        max_full_output_vars=max_full_output_vars,
                    )
                cm_hybrid_no_reinflate_cached_exec_only_time = (time.perf_counter() - t_rep0) / float(eval_repeat)
                if profile_diag is not None:
                    for k, v in profile_diag.items():
                        if k.startswith("cached_exec_"):
                            cm_hybrid_no_reinflate_diag[k] = v
        except Exception as exc:
            cm_hybrid_no_reinflate_declined = isinstance(exc, ValueError) and str(exc).startswith(
                "refusing to materialize reduced no-reinflate output"
            )
            cm_hybrid_no_reinflate_time = None
            cm_hybrid_no_reinflate_tt_extract_time = None
            cm_hybrid_no_reinflate_ok = False

    bdd_time = None
    bdd_nodes = None
    robdd_ok = None
    if build_tt and (not config.no_robdd):
        if verbose:
            print(f"[n={n}] ROBDD (Python) from TT ...")

        class BDDTT:
            def __init__(self, n_vars):
                self.n = n_vars
                self.t = 1
                self.f = 0
                self.unique = {}
                self.nodes = [(-1, -1, -1), (-1, -1, -1)]
                self.cache = {}

            def mk(self, var, low, high):
                if low == high:
                    return low
                key = (var, low, high)
                u = self.unique.get(key)
                if u is None:
                    u = len(self.nodes)
                    self.nodes.append((var, low, high))
                    self.unique[key] = u
                return u

            def build(self, tt_local):
                assert tt_local.size == (1 << self.n)

                def rec(v, s, l):
                    seg = tt_local[s : s + l]
                    key = (v, s, hash(seg.tobytes()))
                    if key in self.cache:
                        return self.cache[key]
                    if l == 1:
                        u_local = self.t if seg[0] == 1 else self.f
                        self.cache[key] = u_local
                        return u_local
                    half = l // 2
                    lo = rec(v + 1, s, half)
                    hi = rec(v + 1, s + half, half)
                    u_local = self.mk(v, lo, hi)
                    self.cache[key] = u_local
                    return u_local

                return rec(0, 0, tt_local.size)

            def size(self, root):
                seen = set()

                def dfs(u):
                    if u in (self.f, self.t) or u in seen:
                        return
                    seen.add(u)
                    _, lo, hi = self.nodes[u]
                    dfs(lo)
                    dfs(hi)

                dfs(root)
                return len(seen) + 2

        bdd_mgr = BDDTT(n)
        t1 = time.perf_counter()
        root = bdd_mgr.build(tt)
        bdd_time = time.perf_counter() - t1
        bdd_nodes = bdd_mgr.size(root)
        robdd_ok = True

    dd_time = None
    dd_nodes = None
    if use_dd and (not config.no_dd):
        try:
            if verbose:
                print(f"[n={n}] dd.autoref from AST ...")
            from dd import autoref as _dd

            mgr2 = _dd.BDD()
            names = [f"x{i}" for i in range(n)]
            mgr2.declare(*names)

            t2 = time.perf_counter()
            root2 = expr_to_dd_bdd(expr, mgr2, {name: name for name in names})
            dd_time = time.perf_counter() - t2
            dd_nodes = safe_bdd_node_count(mgr2, root2)
        except Exception:
            if dd_time is None:
                dd_time = None
            dd_nodes = None

    if (not config.no_dd) and (not config.no_robdd_dd):
        if verbose:
            print(f"[n={n}] ROBDD/dd from AST ...")
        correctness_samples = int(config.sampled_correctness or 0)
        if correctness_samples <= 0 and not build_tt:
            correctness_samples = 256
        robdd_dd_result = run_robdd_dd_backend(
            expr,
            n,
            backend_preference=config.robdd_dd_backend,
            order_policy=config.robdd_order_policy,
            dynamic_reordering=config.robdd_dynamic_reordering,
            reorder_method=config.robdd_reorder_method,
            order_seed=robdd_order_seed,
            order_sweeps=config.robdd_order_sweeps,
            tt_ref=tt_ref,
            correctness_rng=sample_rng,
            correctness_samples=correctness_samples,
            measure_tt_extract=config.robdd_measure_tt_extract,
            tt_extract_method=config.robdd_tt_extract_method,
            tt_extract_max_n=config.robdd_tt_extract_max_n,
        )
    else:
        robdd_dd_result = _empty_robdd_dd_result(
            backend_preference=config.robdd_dd_backend,
            order_policy=config.robdd_order_policy,
            order_seed=robdd_order_seed,
            order_sweeps=config.robdd_order_sweeps,
            dynamic_reordering=config.robdd_dynamic_reordering,
            reorder_method=config.robdd_reorder_method,
            status="disabled",
            error=None,
        )

    def _derived_ratio(a: Any, b: Any) -> Optional[float]:
        try:
            if a is None or b is None:
                return None
            af = float(a)
            bf = float(b)
            if af != af or bf != bf or bf == 0.0:
                return None
            return float(af / bf)
        except Exception:
            return None

    robdd_dd_result["robdd_timeout_or_error"] = bool(
        robdd_dd_result.get("robdd_status") not in ("ok", None)
        or bool(robdd_dd_result.get("robdd_error"))
    )
    robdd_dd_result["robdd_nodes_per_expr_node"] = _derived_ratio(
        robdd_dd_result.get("robdd_node_count"),
        node_count,
    )
    robdd_dd_result["robdd_nodes_per_used_var"] = None
    robdd_nodes = robdd_dd_result.get("robdd_node_count")
    try:
        robdd_dd_result["robdd_log2_nodes"] = float(np.log2(float(robdd_nodes))) if robdd_nodes else None
    except Exception:
        robdd_dd_result["robdd_log2_nodes"] = None

    if build_tt and (not config.no_bitset):
        try:
            if verbose:
                print(f"[n={n}] Bitset eval ...")
            bitset_vars = tuple(f"x{i}" for i in range(n))
            use_words_bitset = bool(config.cm_words_eval)
            use_flat_bitset = bool(config.cm_flat_eval or use_words_bitset)
            # The full bigint environment feeds only the recursive engine; skip
            # building it when the flat/words branch below will never use it.
            local_bit_env = None
            if not use_flat_bitset:
                local_bit_env = bit_env if bit_env is not None else build_bitset_env([f"x{i}" for i in range(n)])
            if use_words_bitset:
                bitset_baseline_kind = "raw_ast_words"
            elif use_flat_bitset:
                bitset_baseline_kind = "raw_ast_flat"
            t7 = time.perf_counter()
            bitset_tt = (
                eval_expr_words_bitset(expr, bitset_vars)
                if use_words_bitset
                else eval_expr_flat_bitset(expr, bitset_vars)
                if use_flat_bitset
                else eval_expr_bitset(expr, local_bit_env)
            )
            bitset_time = time.perf_counter() - t7
            if eval_repeat > 1:
                t7r = time.perf_counter()
                for _ in range(eval_repeat):
                    if use_words_bitset:
                        _ = eval_expr_words_bitset(expr, bitset_vars)
                    elif use_flat_bitset:
                        _ = eval_expr_flat_bitset(expr, bitset_vars)
                    else:
                        _ = eval_expr_bitset(expr, local_bit_env)
                bitset_cached_exec_only_time = (time.perf_counter() - t7r) / float(eval_repeat)
            if tt_ref is not None:
                t7x = time.perf_counter()
                tt_bitset = bitset_to_bool_array(bitset_tt, n)
                bitset_extract_time = time.perf_counter() - t7x
                bitset_ok = bool(np.array_equal(tt_ref, tt_bitset))
            else:
                bitset_ok = False
        except Exception:
            bitset_time = None
            bitset_extract_time = None
            bitset_ok = False

    if build_tt and (not config.no_numba):
        if HAS_NUMBA:
            try:
                if verbose:
                    print(f"[n={n}] Numba eval ...")
                A = get_eval_grid(n)
                t8 = time.perf_counter()
                expr_struct = flatten_expr_numba(expr)
                _ = eval_expr_numba(expr_struct, A[:1, :])
                numba_compile_time = time.perf_counter() - t8
                t9 = time.perf_counter()
                tt_numba = eval_expr_numba(expr_struct, A)
                numba_time = time.perf_counter() - t9
                if tt_ref is not None:
                    numba_ok = bool(np.array_equal(tt_ref, tt_numba.reshape(-1).astype(np.uint8)))
                else:
                    numba_ok = False
            except Exception:
                numba_time = None
                numba_ok = False
                numba_compile_time = None
        else:
            numba_time = None
            numba_ok = None
            numba_compile_time = None

    if build_tt:
        try:
            import sympy as sp

            if run_sympy and (not config.no_sympy):
                if verbose:
                    print(f"[n={n}] Sympy simplify_logic (DNF) ...")
                t4 = time.perf_counter()
                simp = simplify_via_sympy(expr, n, form="dnf")
                sympy_time = time.perf_counter() - t4
                xs = [sp.symbols(f"x{i}") for i in range(n)]
                f = sp.lambdify(xs, simp, "numpy")
                A = get_eval_grid(n)
                tt_sympy = np.array(f(*[A[:, i] for i in range(n)])).astype(np.uint8).reshape(-1)
                sympy_ok = bool(np.array_equal(tt_ref if tt_ref is not None else tt, tt_sympy))
        except Exception:
            sympy_time = None
            sympy_ok = False

        try:
            if run_espresso and (not config.no_espresso) and (pyeda is not None):
                if verbose:
                    print(f"[n={n}] Espresso (pyeda) simplify ...")
                from pyeda.inter import espresso_exprs, truthtable, truthtable2expr, ttvars

                t6 = time.perf_counter()
                xs = ttvars("x", n)
                A = get_eval_grid(n)
                espresso_ref = tt_ref if tt_ref is not None else tt
                if np.all(espresso_ref == 0):
                    espresso_time = time.perf_counter() - t6
                    tt_esp = np.zeros_like(espresso_ref)
                elif np.all(espresso_ref == 1):
                    espresso_time = time.perf_counter() - t6
                    tt_esp = np.ones_like(espresso_ref)
                else:
                    # PyEDA interprets truth-table strings in the opposite variable-significance
                    # order from our x0-slowest TT, so we bit-reverse the full output vector.
                    tt_str = "".join("1" if int(espresso_ref[_bit_reverse(i, n)]) else "0" for i in range(1 << n))
                    T = truthtable(xs, tt_str)
                    (f_simplified,) = espresso_exprs(truthtable2expr(T))
                    espresso_time = time.perf_counter() - t6

                    support_map = {str(v): v for v in f_simplified.support}
                    support_items = []
                    for name, var in support_map.items():
                        if name.startswith("x[") and name.endswith("]") and name[2:-1].isdigit():
                            support_items.append((int(name[2:-1]), var))
                    support_items.sort()

                    tt_esp = np.empty(1 << n, dtype=np.uint8)
                    for k in range(1 << n):
                        point = {var: int(A[k, idx]) for idx, var in support_items}
                        tt_esp[k] = int(f_simplified.restrict(point).is_one())
                espresso_ok = bool(np.array_equal(espresso_ref, tt_esp))
                if verbose and (not espresso_ok):
                    mismatch_indices = np.flatnonzero(espresso_ref != tt_esp)
                    if mismatch_indices.size:
                        k = int(mismatch_indices[0])
                        print(
                            f"[espresso-debug] first mismatch at idx={k}, "
                            f"ref={int(espresso_ref[k])}, espresso={int(tt_esp[k])}, expr={expr}"
                        )
        except Exception:
            espresso_time = None
            espresso_ok = False

        try:
            if (not config.no_bdd_sop) and (n <= 8):
                if verbose:
                    print(f"[n={n}] BDD->SOP extraction ...")
                import sympy as sp

                t5 = time.perf_counter()
                sop_str = bdd_sop(expr, n)
                bdd_sop_time = time.perf_counter() - t5
                xs = [sp.symbols(f"x{i}") for i in range(n)]
                sop_expr = sp.sympify(sop_str, evaluate=False)
                f2 = sp.lambdify(xs, sop_expr, "numpy")
                A = get_eval_grid(n)
                tt_sop = np.array(f2(*[A[:, i] for i in range(n)])).astype(np.uint8).reshape(-1)
                bdd_sop_ok = bool(np.array_equal(tt_ref if tt_ref is not None else tt, tt_sop))
        except Exception:
            bdd_sop_time = None
            bdd_sop_ok = False

    debug_row: Dict[str, Any] = {}
    diag_fields = (
        "subtree_cache_hits",
        "subtree_cache_misses",
        "canonical_rewrites",
        "pruned_branches",
        "materializations",
        "live_vars_max",
        "bitset_materializations",
        "numpy_materializations",
        "bitset_nodes",
        "numpy_nodes",
        "materialization_live_vars_total",
        "hybrid_depth_max",
        "full_collapse_occurred",
        "decision_bitset_k_le_threshold",
        "decision_numpy_k_gt_threshold",
        "decision_numpy_root_forced",
        "decision_numpy_mode_forced",
        "decision_bitset_fixed_var_reduction_helped",
        "decision_cache_hit",
        "final_cm_materialization_performed",
        "final_bitset_returned",
        "final_output_elements",
        "final_output_nominal_elements",
        "final_output_vars_count",
        "final_output_reduced",
        "large_n_output_guard_triggered",
        "final_output_representation_code",
    )
    boundary_float_fields = (
        "boundary_bitset_eval_time_s",
        "boundary_bitset_to_hypercube_time_s",
        "boundary_align_time_s",
        "boundary_dispatch_time_s",
        "final_cm_materialization_time_s",
        "final_truth_table_materialization_time_s",
    )
    boundary_int_fields = (
        "boundary_bitset_eval_calls",
        "boundary_bitset_to_hypercube_calls",
        "boundary_elements_converted",
        "boundary_align_calls",
        "boundary_align_transpose_calls",
        "boundary_align_insert_axes_total",
        "boundary_bitset_const_fastpath_calls",
    )
    def _int_diag(diag: Mapping[str, Any], key: str, default: int = 0) -> int:
        try:
            return int(diag.get(key, default))
        except Exception:
            return int(default)

    def _float_diag(diag: Mapping[str, Any], key: str, default: float = 0.0) -> float:
        try:
            return float(diag.get(key, default))
        except Exception:
            return float(default)

    for field in diag_fields:
        default = -1 if field == "final_output_representation_code" else 0
        debug_row[f"cm_{field}"] = _int_diag(cm_diag, field, default)
        debug_row[f"cm_hybrid_{field}"] = _int_diag(cm_hybrid_diag, field, default)
        debug_row[f"cm_partial_hybrid_{field}"] = _int_diag(cm_partial_hybrid_diag, field, default)
        debug_row[f"cm_parallel_{field}"] = _int_diag(cm_parallel_diag, field, default)
        if config.cm_compare_no_reinflate:
            debug_row[f"cm_hybrid_no_reinflate_{field}"] = _int_diag(cm_hybrid_no_reinflate_diag, field, default)
    for field in boundary_int_fields:
        debug_row[f"cm_{field}"] = _int_diag(cm_diag, field, 0)
        debug_row[f"cm_hybrid_{field}"] = _int_diag(cm_hybrid_diag, field, 0)
        debug_row[f"cm_partial_hybrid_{field}"] = _int_diag(cm_partial_hybrid_diag, field, 0)
        debug_row[f"cm_parallel_{field}"] = _int_diag(cm_parallel_diag, field, 0)
        if config.cm_compare_no_reinflate:
            debug_row[f"cm_hybrid_no_reinflate_{field}"] = _int_diag(cm_hybrid_no_reinflate_diag, field, 0)
    for field in boundary_float_fields:
        debug_row[f"cm_{field}"] = _float_diag(cm_diag, field, 0.0)
        debug_row[f"cm_hybrid_{field}"] = _float_diag(cm_hybrid_diag, field, 0.0)
        debug_row[f"cm_partial_hybrid_{field}"] = _float_diag(cm_partial_hybrid_diag, field, 0.0)
        debug_row[f"cm_parallel_{field}"] = _float_diag(cm_parallel_diag, field, 0.0)
        if config.cm_compare_no_reinflate:
            debug_row[f"cm_hybrid_no_reinflate_{field}"] = _float_diag(cm_hybrid_no_reinflate_diag, field, 0.0)
    for prefix, diag_map in (
        ("cm", cm_diag),
        ("cm_hybrid", cm_hybrid_diag),
        ("cm_partial_hybrid", cm_partial_hybrid_diag),
        ("cm_parallel", cm_parallel_diag),
    ):
        materializations = int(diag_map.get("materializations", 0))
        live_total = int(diag_map.get("materialization_live_vars_total", 0))
        debug_row[f"{prefix}_materialization_avg_k"] = (
            float(live_total / materializations) if materializations > 0 else None
        )
    if config.cm_report_ir_breakdown:
        ir_int_fields = (
            "ir_intern_calls",
            "ir_canonicalize_calls",
            "ir_rewrite_calls",
            "ir_live_vars_calls",
            "ir_live_vars_total_inputs",
            "ir_compile_cache_hit",
            "ir_compile_cache_hits",
            "ir_compile_cache_misses",
            "ir_persistent_cache_hits",
            "ir_persistent_cache_misses",
            "ir_persistent_cache_size",
            "ir_compile_calls_per_expr",
            "ir_compile_reused_for_mode",
        )
        ir_float_fields = (
            "ir_compile_time_s",
            "ir_intern_time_s",
            "ir_canonicalize_time_s",
            "ir_rewrite_time_s",
            "ir_live_vars_time_s",
        )
        nr_int_fields = ("nr_bitset_eval_calls",)
        nr_float_fields = (
            "nr_bitset_eval_time_s",
            "nr_fallback_materialize_ir_time_s",
            "nr_tt_vector_build_time_s",
        )

        diag_sets: List[Tuple[str, Mapping[str, Any]]] = [
            ("cm", cm_diag),
            ("cm_hybrid", cm_hybrid_diag),
            ("cm_partial_hybrid", cm_partial_hybrid_diag),
            ("cm_parallel", cm_parallel_diag),
        ]
        if config.cm_compare_no_reinflate:
            diag_sets.append(("cm_hybrid_no_reinflate", cm_hybrid_no_reinflate_diag))

        for prefix, diag_map in diag_sets:
            for field in ir_int_fields:
                debug_row[f"{prefix}_{field}"] = _int_diag(diag_map, field, 0)
            for field in ir_float_fields:
                debug_row[f"{prefix}_{field}"] = _float_diag(diag_map, field, 0.0)

            other = max(
                0.0,
                _float_diag(diag_map, "ir_compile_time_s", 0.0)
                - (
                    _float_diag(diag_map, "ir_intern_time_s", 0.0)
                    + _float_diag(diag_map, "ir_canonicalize_time_s", 0.0)
                    + _float_diag(diag_map, "ir_rewrite_time_s", 0.0)
                    + _float_diag(diag_map, "ir_live_vars_time_s", 0.0)
                ),
            )
            debug_row[f"{prefix}_ir_other_time_s"] = float(other)

        if config.cm_compare_no_reinflate:
            for field in nr_int_fields:
                debug_row[f"cm_hybrid_no_reinflate_{field}"] = _int_diag(cm_hybrid_no_reinflate_diag, field, 0)
            for field in nr_float_fields:
                debug_row[f"cm_hybrid_no_reinflate_{field}"] = _float_diag(cm_hybrid_no_reinflate_diag, field, 0.0)
    if config.cm_profile_cached_exec and config.cm_compare_no_reinflate:
        cached_exec_int_fields = (
            "cached_exec_evaluations",
            "cached_exec_bitset_eval_calls",
            "cached_exec_result_wrap_count",
            "cached_exec_fallback_to_tt_vector_count",
            "cached_exec_packed_bitset_return_count",
            "cached_exec_reduced_output_count",
        )
        cached_exec_float_fields = (
            "cached_exec_total_time_s",
            "cached_exec_dispatch_time_s",
            "cached_exec_var_order_time_s",
            "cached_exec_fixed_handling_time_s",
            "cached_exec_bitset_eval_time_s",
            "cached_exec_result_wrap_time_s",
            "cached_exec_correctness_or_extract_time_s",
            "cached_exec_other_time_s",
        )
        for field in cached_exec_int_fields:
            debug_row[f"cm_hybrid_no_reinflate_{field}"] = _int_diag(cm_hybrid_no_reinflate_diag, field, 0)
        for field in cached_exec_float_fields:
            debug_row[f"cm_hybrid_no_reinflate_{field}"] = _float_diag(cm_hybrid_no_reinflate_diag, field, 0.0)
    if config.cm_debug_stats:
        def _coerce_diag_value(v: Any) -> Any:
            if v is None:
                return None
            if isinstance(v, (bool, int, np.integer)):
                return int(v)
            if isinstance(v, (float, np.floating)):
                return float(v)
            return str(v)

        norm_after = cm_normalize_cache_stats()
        for k, v in norm_after.items():
            before = int(norm_before.get(k, 0)) if norm_before is not None else 0
            debug_row[f"cm_norm_{k}_delta"] = int(v) - before

        if HAS_LAZY and callable(lazy_align_cache_stats):
            lazy_after = lazy_align_cache_stats()
            lazy_before_map = lazy_before or {}
            for k, v in lazy_after.items():
                debug_row[f"cm_lazy_{k}_delta"] = int(v) - int(lazy_before_map.get(k, 0))

        for k, v in cm_diag.items():
            debug_row[f"cm_diag_{k}"] = _coerce_diag_value(v)
        for k, v in cm_hybrid_diag.items():
            debug_row[f"cm_hybrid_diag_{k}"] = _coerce_diag_value(v)
        for k, v in cm_partial_hybrid_diag.items():
            debug_row[f"cm_partial_hybrid_diag_{k}"] = _coerce_diag_value(v)
        for k, v in cm_parallel_diag.items():
            debug_row[f"cm_parallel_diag_{k}"] = _coerce_diag_value(v)
        if config.cm_compare_no_reinflate:
            for k, v in cm_hybrid_no_reinflate_diag.items():
                debug_row[f"cm_hybrid_no_reinflate_diag_{k}"] = _coerce_diag_value(v)

    robdd_dd_result["ratio_robdd_build_over_bitset"] = _derived_ratio(
        robdd_dd_result.get("robdd_build_time_s"),
        bitset_time,
    )
    robdd_dd_result["ratio_robdd_build_extract_over_bitset"] = _derived_ratio(
        robdd_dd_result.get("robdd_total_build_plus_extract_time_s"),
        bitset_time,
    )
    robdd_dd_result["ratio_robdd_build_over_cm_no_reinflate"] = _derived_ratio(
        robdd_dd_result.get("robdd_build_time_s"),
        cm_hybrid_no_reinflate_time,
    )
    robdd_dd_result["ratio_robdd_build_extract_over_cm_no_reinflate"] = _derived_ratio(
        robdd_dd_result.get("robdd_total_build_plus_extract_time_s"),
        cm_hybrid_no_reinflate_time,
    )
    robdd_dd_result["ratio_robdd_build_over_cm_cached_exec"] = _derived_ratio(
        robdd_dd_result.get("robdd_build_time_s"),
        cm_hybrid_no_reinflate_cached_exec_only_time,
    )
    robdd_dd_result["ratio_robdd_build_extract_over_cm_cached_exec"] = _derived_ratio(
        robdd_dd_result.get("robdd_total_build_plus_extract_time_s"),
        cm_hybrid_no_reinflate_cached_exec_only_time,
    )

    return {
        "cm_time_s": t_cm,
        **(
            {
                "cm_exec_only_time_s": cm_exec_only_time,
                "cm_hybrid_exec_only_time_s": cm_hybrid_exec_only_time,
                "cm_partial_hybrid_exec_only_time_s": cm_partial_hybrid_exec_only_time,
                "cm_hybrid_no_reinflate_exec_only_time_s": cm_hybrid_no_reinflate_exec_only_time,
            }
            if bool(config.cm_compile_once_per_expression)
            else {}
        ),
        "cm_tt_extract_time_s": cm_tt_extract_time,
        **(
            {
                "cm_eval_repeat": eval_repeat,
                "bitset_cached_exec_only_time_s": bitset_cached_exec_only_time,
            }
            if ((build_tt or large_n_safe) and eval_repeat > 1)
            else {}
        ),
        **(
            {"cm_hybrid_no_reinflate_cached_exec_only_time_s": cm_hybrid_no_reinflate_cached_exec_only_time}
            if ((build_tt or large_n_safe) and eval_repeat > 1 and config.cm_compare_no_reinflate)
            else {}
        ),
        **(
            {
                "cm_no_reinflate_time_s": cm_hybrid_no_reinflate_time,
                "cm_persistent_cache_no_reinflate_time_s": (
                    cm_hybrid_no_reinflate_time
                    if bool(config.cm_use_persistent_cache)
                    else None
                ),
                "cm_cached_exec_s_per_eval": cm_hybrid_no_reinflate_cached_exec_only_time,
            }
            if config.cm_compare_no_reinflate
            else {}
        ),
        "cm_ok": cm_ok,
        "correctness_reference": (
            "eval_expr_tt"
            if tt_ref is not None
            else ("sampled_assignments" if int(config.sampled_correctness or 0) > 0 else "skipped")
        ),
        "tt_ref_available": bool(tt_ref is not None),
        "tt_ref_source": tt_ref_source if tt_ref is not None else "not_built",
        "cm_nodes": node_count,
        "pair_attempts": pair_attempts,
        "pair_collapses": pair_collapses,
        "pairable_ratio": pair_ratio,
        "pair_nodes_total": pair_nodes_total,
        "cm_hybrid_time_s": cm_hybrid_time,
        "cm_hybrid_tt_extract_time_s": cm_hybrid_tt_extract_time,
        "cm_hybrid_ok": cm_hybrid_ok,
        "cm_partial_hybrid_time_s": cm_partial_hybrid_time,
        "cm_partial_hybrid_tt_extract_time_s": cm_partial_hybrid_tt_extract_time,
        "cm_partial_hybrid_ok": cm_partial_hybrid_ok,
        **(
            {
                "cm_hybrid_no_reinflate_time_s": cm_hybrid_no_reinflate_time,
                "cm_hybrid_no_reinflate_tt_extract_time_s": cm_hybrid_no_reinflate_tt_extract_time,
                "cm_hybrid_no_reinflate_ok": cm_hybrid_no_reinflate_ok,
                "cm_hybrid_no_reinflate_declined": cm_hybrid_no_reinflate_declined,
            }
            if config.cm_compare_no_reinflate
            else {}
        ),
        "cm_parallel_time_s": cm_parallel_time,
        "cm_parallel_tt_extract_time_s": cm_parallel_tt_extract_time,
        "cm_parallel_ok": cm_parallel_ok,
        "bitset_time_s": bitset_time,
        "bitset_extract_time_s": bitset_extract_time,
        "bitset_ok": bitset_ok,
        "bitset_baseline_kind": bitset_baseline_kind,
        "cm_words_eval": bool(config.cm_words_eval),
        "cm_time_excludes_tt_extract": True,
        "cm_hybrid_time_excludes_tt_extract": True,
        "cm_partial_hybrid_time_excludes_tt_extract": True,
        **(
            {"cm_hybrid_no_reinflate_time_excludes_tt_extract": True}
            if config.cm_compare_no_reinflate
            else {}
        ),
        "cm_parallel_time_excludes_tt_extract": True,
        "bitset_time_excludes_tt_extract": True,
        "numba_compile_time_s": numba_compile_time,
        "numba_time_s": numba_time,
        "numba_ok": numba_ok,
        "bdd_time_s": bdd_time,
        "bdd_nodes": bdd_nodes,
        "custom_tt_robdd_time_s": bdd_time,
        "custom_tt_robdd_nodes": bdd_nodes,
        "custom_tt_robdd_ok": robdd_ok,
        "dd_time_s": dd_time,
        "dd_nodes": dd_nodes,
        **robdd_dd_result,
        "sympy_time_s": sympy_time,
        "sympy_ok": sympy_ok,
        "bdd_sop_time_s": bdd_sop_time,
        "bdd_sop_ok": bdd_sop_ok,
        "espresso_time_s": espresso_time,
        "espresso_ok": espresso_ok,
        "cm_layout": config.cm_layout,
        "cm_compare_hybrid": bool(config.cm_compare_hybrid),
        "cm_compare_no_reinflate": bool(config.cm_compare_no_reinflate),
        "cm_use_persistent_cache": bool(config.cm_use_persistent_cache),
        "cm_exec_target": cm_exec_target,
        "cm_report_ir_breakdown": bool(config.cm_report_ir_breakdown),
        "cm_compile_once_per_expression": bool(config.cm_compile_once_per_expression),
        "cm_reuse_compiled_ir": bool(config.cm_reuse_compiled_ir),
        "cm_hybrid_threshold": int(config.cm_hybrid_threshold),
        **(
            {
                "cm_runpod_pod_started": cm_runpod_pod_started,
                "cm_runpod_ready_wait_time_s": cm_runpod_ready_wait_time_s,
                "cm_runpod_request_time_s": cm_runpod_request_time_s,
                "cm_runpod_remote_exec_time_s": cm_runpod_remote_exec_time_s,
                "cm_runpod_total_wall_time_s": cm_runpod_total_wall_time_s,
                "cm_runpod_result_repr": cm_runpod_result_repr,
                "cm_runpod_final_cm_materialized": cm_runpod_final_cm_materialized,
                "cm_runpod_fallback_local": cm_runpod_fallback_local,
                "cm_runpod_status": cm_runpod_status,
                "cm_runpod_error": cm_runpod_error,
            }
            if cm_exec_target == "runpod"
            else {}
        ),
        "sampled_correctness_samples": sampled_correctness_samples,
        "sampled_correctness_mismatches": sampled_correctness_mismatches,
        "sampled_correctness_mismatch_rate": sampled_correctness_mismatch_rate,
        "cm_live_vars_max": debug_row.get("cm_hybrid_no_reinflate_live_vars_max", debug_row.get("cm_live_vars_max")),
        "cm_materializations": debug_row.get(
            "cm_hybrid_no_reinflate_materializations",
            debug_row.get("cm_materializations"),
        ),
        "cm_final_repr": debug_row.get(
            "cm_hybrid_no_reinflate_final_output_representation_code",
            debug_row.get("cm_final_output_representation_code"),
        ),
        "cm_final_cm_materialized": debug_row.get(
            "cm_hybrid_no_reinflate_final_cm_materialization_performed",
            debug_row.get("cm_final_cm_materialization_performed"),
        ),
        **debug_row,
    }


def _prepare_single_expr_bitset_envs(sizes: Sequence[int], config: BenchmarkConfig) -> Dict[int, Mapping[str, int]]:
    bit_env_by_n: Dict[int, Mapping[str, int]] = {}
    if not config.no_bitset:
        for n in sizes:
            n_int = int(n)
            if n_int <= int(config.full_tt_max_n):
                bit_env_by_n[n_int] = build_bitset_env([f"x{i}" for i in range(n_int)])
    return bit_env_by_n


def _generate_single_expr_trial(
    n: int,
    rng: np.random.Generator,
    max_depth: int,
    expr_style: str,
    config: BenchmarkConfig,
):
    return generate_benchmark_expr(
        n,
        rng,
        max_depth=max_depth,
        style=expr_style,
        build_tt=n <= int(config.full_tt_max_n),
        config=config,
        return_tt_ref=True,
    )


def _run_single_expr_trial(
    n: int,
    trial: int,
    expr,
    expr_diag: Dict[str, Any],
    tt_ref: Optional[np.ndarray],
    *,
    seed: int,
    expr_style: str,
    use_dd: bool,
    use_espresso: bool,
    verbose: bool,
    bit_env: Optional[Mapping[str, int]],
    sample_rng: np.random.Generator,
    config: BenchmarkConfig,
    ctx: BenchmarkRunContext,
) -> Dict[str, Any]:
    res = time_backends_on_expr(
        n,
        expr,
        use_dd=use_dd,
        use_espresso=use_espresso,
        verbose=verbose,
        bit_env=bit_env,
        sample_rng=sample_rng,
        robdd_order_seed=(
            int(config.robdd_order_seed)
            if config.robdd_order_seed is not None
            else int(seed + n * 1009 + trial * 9176)
        ),
        tt_ref=tt_ref,
        config=config,
        ctx=ctx,
    )
    res["n_vars"] = n
    res["trial"] = trial
    res["expr_style"] = expr_style
    res.update(expr_diag)
    res["robdd_nodes_per_used_var"] = (
        float(res["robdd_node_count"] / res["expr_unique_var_count"])
        if res.get("robdd_node_count") is not None and int(res.get("expr_unique_var_count") or 0) > 0
        else None
    )
    return res


def run_bench(
    sizes: List[int],
    trials: int,
    seed: int,
    max_depth: int,
    verbose: bool,
    config: Optional[BenchmarkConfig] = None,
    ctx: Optional[BenchmarkRunContext] = None,
):
    import pandas as pd

    config = config or (config_from_args(args) if args is not None else None)
    if config is None:
        raise ValueError("config is required when global args is not initialized")
    ctx = ctx or make_context(config, detect_backends())
    rng = np.random.default_rng(seed)
    sample_rng = np.random.default_rng(seed + 1_000_003)
    expr_style = config.expr_style
    use_dd = select_dd_module("autoref")[0] is not None
    use_espresso = pyeda is not None
    rows = []

    bit_env_by_n = _prepare_single_expr_bitset_envs(sizes, config)
    full_tt_max_n = config.full_tt_max_n

    for n in sizes:
        if verbose:
            print(f"\n=== n = {n} ===")
            if n > full_tt_max_n:
                print("[info] n>16: skipping Sympy/Espresso/TT")
        for t in range(trials):
            expr, expr_diag, tt_ref = _generate_single_expr_trial(n, rng, max_depth, expr_style, config)
            if verbose:
                print(f"  Trial {t + 1}/{trials}")
            rows.append(_run_single_expr_trial(
                n,
                t,
                expr,
                expr_diag,
                tt_ref,
                seed=seed,
                expr_style=expr_style,
                use_dd=use_dd,
                use_espresso=use_espresso,
                verbose=verbose,
                bit_env=bit_env_by_n.get(n),
                sample_rng=sample_rng,
                config=config,
                ctx=ctx,
            ))

    df = pd.DataFrame(rows)

    def safe_median(s):
        try:
            return float(s.dropna().median())
        except Exception:
            return None

    def safe_all(s):
        try:
            x = s.dropna().tolist()
            return all(x) if x else None
        except Exception:
            return None

    def count_true(s):
        try:
            x = s.dropna().tolist()
            return sum(1 for v in x if v is True)
        except Exception:
            return 0

    def safe_bool_rate(s):
        try:
            x = s.dropna().tolist()
            if not x:
                return None
            return float(sum(1 for v in x if bool(v)) / len(x))
        except Exception:
            return None

    def safe_first(s):
        try:
            x = s.dropna().tolist()
            return x[0] if x else None
        except Exception:
            return None

    agg = (
        df.groupby("n_vars")
        .agg(
            cm_time_s_median=("cm_time_s", safe_median),
            cm_tt_extract_time_s_median=("cm_tt_extract_time_s", safe_median),
            pair_attempts_median=("pair_attempts", safe_median),
            pair_collapses_median=("pair_collapses", safe_median),
            pairable_ratio_median=("pairable_ratio", safe_median),
            pair_nodes_total_median=("pair_nodes_total", safe_median),
            cm_hybrid_time_s_median=("cm_hybrid_time_s", safe_median),
            cm_hybrid_tt_extract_time_s_median=("cm_hybrid_tt_extract_time_s", safe_median),
            cm_partial_hybrid_time_s_median=("cm_partial_hybrid_time_s", safe_median),
            cm_partial_hybrid_tt_extract_time_s_median=("cm_partial_hybrid_tt_extract_time_s", safe_median),
            cm_parallel_time_s_median=("cm_parallel_time_s", safe_median),
            cm_parallel_tt_extract_time_s_median=("cm_parallel_tt_extract_time_s", safe_median),
            bitset_time_s_median=("bitset_time_s", safe_median),
            bitset_extract_time_s_median=("bitset_extract_time_s", safe_median),
            numba_compile_time_s_median=("numba_compile_time_s", safe_median),
            numba_time_s_median=("numba_time_s", safe_median),
            bdd_time_s_median=("bdd_time_s", safe_median),
            dd_time_s_median=("dd_time_s", safe_median),
            robdd_build_time_s_median=("robdd_build_time_s", safe_median),
            robdd_reorder_time_s_median=("robdd_reorder_time_s", safe_median),
            robdd_total_build_plus_reorder_time_s_median=("robdd_total_build_plus_reorder_time_s", safe_median),
            robdd_tt_extract_time_s_median=("robdd_tt_extract_time_s", safe_median),
            robdd_tt_extract_elements_median=("robdd_tt_extract_elements", safe_median),
            robdd_total_build_plus_extract_time_s_median=("robdd_total_build_plus_extract_time_s", safe_median),
            sympy_time_s_median=("sympy_time_s", safe_median),
            bdd_nodes_median=("bdd_nodes", safe_median),
            dd_nodes_median=("dd_nodes", safe_median),
            custom_tt_robdd_time_s_median=("custom_tt_robdd_time_s", safe_median),
            custom_tt_robdd_nodes_median=("custom_tt_robdd_nodes", safe_median),
            robdd_node_count_median=("robdd_node_count", safe_median),
            robdd_best_time_s_median=("robdd_best_time_s", safe_median),
            robdd_median_time_s_median=("robdd_median_time_s", safe_median),
            robdd_worst_time_s_median=("robdd_worst_time_s", safe_median),
            robdd_best_nodes_median=("robdd_best_nodes", safe_median),
            robdd_median_nodes_median=("robdd_median_nodes", safe_median),
            robdd_worst_nodes_median=("robdd_worst_nodes", safe_median),
            robdd_nodes_before_reorder_median=("robdd_nodes_before_reorder", safe_median),
            robdd_nodes_after_reorder_median=("robdd_nodes_after_reorder", safe_median),
            robdd_nodes_per_expr_node_median=("robdd_nodes_per_expr_node", safe_median),
            robdd_nodes_per_used_var_median=("robdd_nodes_per_used_var", safe_median),
            robdd_log2_nodes_median=("robdd_log2_nodes", safe_median),
            robdd_timeout_or_error_rate=("robdd_timeout_or_error", safe_bool_rate),
            cm_nodes_median=("cm_nodes", safe_median),
            expr_depth_actual_median=("expr_depth_actual", safe_median),
            expr_node_count_median=("expr_node_count", safe_median),
            expr_leaf_count_median=("expr_leaf_count", safe_median),
            expr_op_count_median=("expr_op_count", safe_median),
            expr_unique_var_count_median=("expr_unique_var_count", safe_median),
            expr_vars_used_count_median=("expr_vars_used_count", safe_median),
            expr_uses_all_vars_rate=("expr_uses_all_vars", safe_bool_rate),
            pct_uses_all_vars=("expr_uses_all_vars", safe_bool_rate),
            expr_const_count_median=("expr_const_count", safe_median),
            expr_not_count_median=("expr_not_count", safe_median),
            expr_and_count_median=("expr_and_count", safe_median),
            expr_or_count_median=("expr_or_count", safe_median),
            expr_xor_count_median=("expr_xor_count", safe_median),
            expr_imp_count_median=("expr_imp_count", safe_median),
            expr_eqv_count_median=("expr_eqv_count", safe_median),
            tt_true_count_median=("tt_true_count", safe_median),
            tt_false_count_median=("tt_false_count", safe_median),
            tt_density_median=("tt_density", safe_median),
            median_tt_density=("tt_density", safe_median),
            tt_is_constant_rate=("tt_is_constant", safe_bool_rate),
            pct_constant_tt=("tt_is_constant", safe_bool_rate),
            tt_is_balancedish_rate=("tt_is_balancedish", safe_bool_rate),
            expr_regeneration_attempts_median=("expr_regeneration_attempts", safe_median),
            expr_filter_reason=("expr_filter_reason", safe_first),
            cm_subtree_cache_hits_median=("cm_subtree_cache_hits", safe_median),
            cm_canonical_rewrites_median=("cm_canonical_rewrites", safe_median),
            cm_pruned_branches_median=("cm_pruned_branches", safe_median),
            cm_materializations_median=("cm_materializations", safe_median),
            cm_live_vars_max_median=("cm_live_vars_max", safe_median),
            cm_bitset_materializations_median=("cm_bitset_materializations", safe_median),
            cm_numpy_materializations_median=("cm_numpy_materializations", safe_median),
            cm_bitset_nodes_median=("cm_bitset_nodes", safe_median),
            cm_numpy_nodes_median=("cm_numpy_nodes", safe_median),
            cm_materialization_live_vars_total_median=("cm_materialization_live_vars_total", safe_median),
            cm_materialization_avg_k_median=("cm_materialization_avg_k", safe_median),
            cm_hybrid_depth_max_median=("cm_hybrid_depth_max", safe_median),
            cm_full_collapse_occurred_median=("cm_full_collapse_occurred", safe_median),
            cm_decision_bitset_k_le_threshold_median=("cm_decision_bitset_k_le_threshold", safe_median),
            cm_decision_numpy_k_gt_threshold_median=("cm_decision_numpy_k_gt_threshold", safe_median),
            cm_decision_numpy_root_forced_median=("cm_decision_numpy_root_forced", safe_median),
            cm_decision_numpy_mode_forced_median=("cm_decision_numpy_mode_forced", safe_median),
            cm_decision_bitset_fixed_var_reduction_helped_median=(
                "cm_decision_bitset_fixed_var_reduction_helped",
                safe_median,
            ),
            cm_decision_cache_hit_median=("cm_decision_cache_hit", safe_median),
            cm_boundary_bitset_eval_time_s_median=("cm_boundary_bitset_eval_time_s", safe_median),
            cm_boundary_bitset_to_hypercube_time_s_median=("cm_boundary_bitset_to_hypercube_time_s", safe_median),
            cm_boundary_align_time_s_median=("cm_boundary_align_time_s", safe_median),
            cm_boundary_dispatch_time_s_median=("cm_boundary_dispatch_time_s", safe_median),
            cm_boundary_bitset_eval_calls_median=("cm_boundary_bitset_eval_calls", safe_median),
            cm_boundary_bitset_to_hypercube_calls_median=("cm_boundary_bitset_to_hypercube_calls", safe_median),
            cm_boundary_elements_converted_median=("cm_boundary_elements_converted", safe_median),
            cm_boundary_align_calls_median=("cm_boundary_align_calls", safe_median),
            cm_boundary_align_transpose_calls_median=("cm_boundary_align_transpose_calls", safe_median),
            cm_boundary_align_insert_axes_total_median=("cm_boundary_align_insert_axes_total", safe_median),
            cm_boundary_bitset_const_fastpath_calls_median=("cm_boundary_bitset_const_fastpath_calls", safe_median),
            cm_hybrid_subtree_cache_hits_median=("cm_hybrid_subtree_cache_hits", safe_median),
            cm_hybrid_canonical_rewrites_median=("cm_hybrid_canonical_rewrites", safe_median),
            cm_hybrid_pruned_branches_median=("cm_hybrid_pruned_branches", safe_median),
            cm_hybrid_materializations_median=("cm_hybrid_materializations", safe_median),
            cm_hybrid_live_vars_max_median=("cm_hybrid_live_vars_max", safe_median),
            cm_hybrid_bitset_materializations_median=("cm_hybrid_bitset_materializations", safe_median),
            cm_hybrid_numpy_materializations_median=("cm_hybrid_numpy_materializations", safe_median),
            cm_hybrid_bitset_nodes_median=("cm_hybrid_bitset_nodes", safe_median),
            cm_hybrid_numpy_nodes_median=("cm_hybrid_numpy_nodes", safe_median),
            cm_hybrid_materialization_live_vars_total_median=("cm_hybrid_materialization_live_vars_total", safe_median),
            cm_hybrid_materialization_avg_k_median=("cm_hybrid_materialization_avg_k", safe_median),
            cm_hybrid_hybrid_depth_max_median=("cm_hybrid_hybrid_depth_max", safe_median),
            cm_hybrid_full_collapse_occurred_median=("cm_hybrid_full_collapse_occurred", safe_median),
            cm_hybrid_decision_bitset_k_le_threshold_median=("cm_hybrid_decision_bitset_k_le_threshold", safe_median),
            cm_hybrid_decision_numpy_k_gt_threshold_median=("cm_hybrid_decision_numpy_k_gt_threshold", safe_median),
            cm_hybrid_decision_numpy_root_forced_median=("cm_hybrid_decision_numpy_root_forced", safe_median),
            cm_hybrid_decision_numpy_mode_forced_median=("cm_hybrid_decision_numpy_mode_forced", safe_median),
            cm_hybrid_decision_bitset_fixed_var_reduction_helped_median=(
                "cm_hybrid_decision_bitset_fixed_var_reduction_helped",
                safe_median,
            ),
            cm_hybrid_decision_cache_hit_median=("cm_hybrid_decision_cache_hit", safe_median),
            cm_hybrid_boundary_bitset_eval_time_s_median=("cm_hybrid_boundary_bitset_eval_time_s", safe_median),
            cm_hybrid_boundary_bitset_to_hypercube_time_s_median=(
                "cm_hybrid_boundary_bitset_to_hypercube_time_s",
                safe_median,
            ),
            cm_hybrid_boundary_align_time_s_median=("cm_hybrid_boundary_align_time_s", safe_median),
            cm_hybrid_boundary_dispatch_time_s_median=("cm_hybrid_boundary_dispatch_time_s", safe_median),
            cm_hybrid_boundary_bitset_eval_calls_median=("cm_hybrid_boundary_bitset_eval_calls", safe_median),
            cm_hybrid_boundary_bitset_to_hypercube_calls_median=("cm_hybrid_boundary_bitset_to_hypercube_calls", safe_median),
            cm_hybrid_boundary_elements_converted_median=("cm_hybrid_boundary_elements_converted", safe_median),
            cm_hybrid_boundary_align_calls_median=("cm_hybrid_boundary_align_calls", safe_median),
            cm_hybrid_boundary_align_transpose_calls_median=("cm_hybrid_boundary_align_transpose_calls", safe_median),
            cm_hybrid_boundary_align_insert_axes_total_median=("cm_hybrid_boundary_align_insert_axes_total", safe_median),
            cm_hybrid_boundary_bitset_const_fastpath_calls_median=(
                "cm_hybrid_boundary_bitset_const_fastpath_calls",
                safe_median,
            ),
            cm_partial_hybrid_subtree_cache_hits_median=("cm_partial_hybrid_subtree_cache_hits", safe_median),
            cm_partial_hybrid_canonical_rewrites_median=("cm_partial_hybrid_canonical_rewrites", safe_median),
            cm_partial_hybrid_pruned_branches_median=("cm_partial_hybrid_pruned_branches", safe_median),
            cm_partial_hybrid_materializations_median=("cm_partial_hybrid_materializations", safe_median),
            cm_partial_hybrid_live_vars_max_median=("cm_partial_hybrid_live_vars_max", safe_median),
            cm_partial_hybrid_bitset_materializations_median=("cm_partial_hybrid_bitset_materializations", safe_median),
            cm_partial_hybrid_numpy_materializations_median=("cm_partial_hybrid_numpy_materializations", safe_median),
            cm_partial_hybrid_bitset_nodes_median=("cm_partial_hybrid_bitset_nodes", safe_median),
            cm_partial_hybrid_numpy_nodes_median=("cm_partial_hybrid_numpy_nodes", safe_median),
            cm_partial_hybrid_materialization_live_vars_total_median=(
                "cm_partial_hybrid_materialization_live_vars_total",
                safe_median,
            ),
            cm_partial_hybrid_materialization_avg_k_median=("cm_partial_hybrid_materialization_avg_k", safe_median),
            cm_partial_hybrid_hybrid_depth_max_median=("cm_partial_hybrid_hybrid_depth_max", safe_median),
            cm_partial_hybrid_full_collapse_occurred_median=(
                "cm_partial_hybrid_full_collapse_occurred",
                safe_median,
            ),
            cm_partial_hybrid_decision_bitset_k_le_threshold_median=(
                "cm_partial_hybrid_decision_bitset_k_le_threshold",
                safe_median,
            ),
            cm_partial_hybrid_decision_numpy_k_gt_threshold_median=(
                "cm_partial_hybrid_decision_numpy_k_gt_threshold",
                safe_median,
            ),
            cm_partial_hybrid_decision_numpy_root_forced_median=(
                "cm_partial_hybrid_decision_numpy_root_forced",
                safe_median,
            ),
            cm_partial_hybrid_decision_numpy_mode_forced_median=(
                "cm_partial_hybrid_decision_numpy_mode_forced",
                safe_median,
            ),
            cm_partial_hybrid_decision_bitset_fixed_var_reduction_helped_median=(
                "cm_partial_hybrid_decision_bitset_fixed_var_reduction_helped",
                safe_median,
            ),
            cm_partial_hybrid_decision_cache_hit_median=("cm_partial_hybrid_decision_cache_hit", safe_median),
            cm_partial_hybrid_boundary_bitset_eval_time_s_median=(
                "cm_partial_hybrid_boundary_bitset_eval_time_s",
                safe_median,
            ),
            cm_partial_hybrid_boundary_bitset_to_hypercube_time_s_median=(
                "cm_partial_hybrid_boundary_bitset_to_hypercube_time_s",
                safe_median,
            ),
            cm_partial_hybrid_boundary_align_time_s_median=("cm_partial_hybrid_boundary_align_time_s", safe_median),
            cm_partial_hybrid_boundary_dispatch_time_s_median=(
                "cm_partial_hybrid_boundary_dispatch_time_s",
                safe_median,
            ),
            cm_partial_hybrid_boundary_bitset_eval_calls_median=("cm_partial_hybrid_boundary_bitset_eval_calls", safe_median),
            cm_partial_hybrid_boundary_bitset_to_hypercube_calls_median=(
                "cm_partial_hybrid_boundary_bitset_to_hypercube_calls",
                safe_median,
            ),
            cm_partial_hybrid_boundary_elements_converted_median=("cm_partial_hybrid_boundary_elements_converted", safe_median),
            cm_partial_hybrid_boundary_align_calls_median=("cm_partial_hybrid_boundary_align_calls", safe_median),
            cm_partial_hybrid_boundary_align_transpose_calls_median=(
                "cm_partial_hybrid_boundary_align_transpose_calls",
                safe_median,
            ),
            cm_partial_hybrid_boundary_align_insert_axes_total_median=(
                "cm_partial_hybrid_boundary_align_insert_axes_total",
                safe_median,
            ),
            cm_partial_hybrid_boundary_bitset_const_fastpath_calls_median=(
                "cm_partial_hybrid_boundary_bitset_const_fastpath_calls",
                safe_median,
            ),
            cm_parallel_subtree_cache_hits_median=("cm_parallel_subtree_cache_hits", safe_median),
            cm_parallel_canonical_rewrites_median=("cm_parallel_canonical_rewrites", safe_median),
            cm_parallel_pruned_branches_median=("cm_parallel_pruned_branches", safe_median),
            cm_parallel_materializations_median=("cm_parallel_materializations", safe_median),
            cm_parallel_live_vars_max_median=("cm_parallel_live_vars_max", safe_median),
            cm_parallel_bitset_materializations_median=("cm_parallel_bitset_materializations", safe_median),
            cm_parallel_numpy_materializations_median=("cm_parallel_numpy_materializations", safe_median),
            cm_parallel_bitset_nodes_median=("cm_parallel_bitset_nodes", safe_median),
            cm_parallel_numpy_nodes_median=("cm_parallel_numpy_nodes", safe_median),
            cm_parallel_materialization_live_vars_total_median=("cm_parallel_materialization_live_vars_total", safe_median),
            cm_parallel_materialization_avg_k_median=("cm_parallel_materialization_avg_k", safe_median),
            cm_parallel_hybrid_depth_max_median=("cm_parallel_hybrid_depth_max", safe_median),
            cm_parallel_full_collapse_occurred_median=("cm_parallel_full_collapse_occurred", safe_median),
            cm_parallel_decision_bitset_k_le_threshold_median=("cm_parallel_decision_bitset_k_le_threshold", safe_median),
            cm_parallel_decision_numpy_k_gt_threshold_median=("cm_parallel_decision_numpy_k_gt_threshold", safe_median),
            cm_parallel_decision_numpy_root_forced_median=("cm_parallel_decision_numpy_root_forced", safe_median),
            cm_parallel_decision_numpy_mode_forced_median=("cm_parallel_decision_numpy_mode_forced", safe_median),
            cm_parallel_decision_bitset_fixed_var_reduction_helped_median=(
                "cm_parallel_decision_bitset_fixed_var_reduction_helped",
                safe_median,
            ),
            cm_parallel_decision_cache_hit_median=("cm_parallel_decision_cache_hit", safe_median),
            cm_parallel_boundary_bitset_eval_time_s_median=("cm_parallel_boundary_bitset_eval_time_s", safe_median),
            cm_parallel_boundary_bitset_to_hypercube_time_s_median=(
                "cm_parallel_boundary_bitset_to_hypercube_time_s",
                safe_median,
            ),
            cm_parallel_boundary_align_time_s_median=("cm_parallel_boundary_align_time_s", safe_median),
            cm_parallel_boundary_dispatch_time_s_median=("cm_parallel_boundary_dispatch_time_s", safe_median),
            cm_parallel_boundary_bitset_eval_calls_median=("cm_parallel_boundary_bitset_eval_calls", safe_median),
            cm_parallel_boundary_bitset_to_hypercube_calls_median=(
                "cm_parallel_boundary_bitset_to_hypercube_calls",
                safe_median,
            ),
            cm_parallel_boundary_elements_converted_median=("cm_parallel_boundary_elements_converted", safe_median),
            cm_parallel_boundary_align_calls_median=("cm_parallel_boundary_align_calls", safe_median),
            cm_parallel_boundary_align_transpose_calls_median=("cm_parallel_boundary_align_transpose_calls", safe_median),
            cm_parallel_boundary_align_insert_axes_total_median=(
                "cm_parallel_boundary_align_insert_axes_total",
                safe_median,
            ),
            cm_parallel_boundary_bitset_const_fastpath_calls_median=(
                "cm_parallel_boundary_bitset_const_fastpath_calls",
                safe_median,
            ),
            espresso_time_s_median=("espresso_time_s", safe_median),
            cm_ok_all=("cm_ok", safe_all),
            cm_hybrid_ok_all=("cm_hybrid_ok", safe_all),
            cm_partial_hybrid_ok_all=("cm_partial_hybrid_ok", safe_all),
            cm_parallel_ok_all=("cm_parallel_ok", safe_all),
            bitset_ok_all=("bitset_ok", safe_all),
            numba_ok_all=("numba_ok", safe_all),
            sympy_ok_all=("sympy_ok", safe_all),
            custom_tt_robdd_ok_all=("custom_tt_robdd_ok", safe_all),
            robdd_ok_all=("robdd_ok", safe_all),
            robdd_backend=("robdd_backend", safe_first),
            robdd_backend_module=("robdd_backend_module", safe_first),
            robdd_backend_class=("robdd_backend_class", safe_first),
            robdd_is_cudd_all=("robdd_is_cudd", safe_all),
            robdd_is_autoref_all=("robdd_is_autoref", safe_all),
            robdd_cudd_available_all=("robdd_cudd_available", safe_all),
            robdd_backend_preference=("robdd_backend_preference", safe_first),
            robdd_order_policy=("robdd_order_policy", safe_first),
            robdd_order_seed_median=("robdd_order_seed", safe_median),
            robdd_order_sweeps_median=("robdd_order_sweeps", safe_median),
            robdd_order_used=("robdd_order_used", safe_first),
            robdd_dynamic_reordering_requested_all=("robdd_dynamic_reordering_requested", safe_all),
            robdd_dynamic_reordering_available_all=("robdd_dynamic_reordering_available", safe_all),
            robdd_dynamic_reordering_used_all=("robdd_dynamic_reordering_used", safe_all),
            robdd_reorder_method=("robdd_reorder_method", safe_first),
            robdd_status=("robdd_status", safe_first),
            robdd_error=("robdd_error", safe_first),
            robdd_tt_extract_ok_all=("robdd_tt_extract_ok", safe_all),
            robdd_tt_extract_status=("robdd_tt_extract_status", safe_first),
            robdd_extract_method=("robdd_extract_method", safe_first),
            robdd_tt_extract_error=("robdd_tt_extract_error", safe_first),
            robdd_correctness_mode=("robdd_correctness_mode", safe_first),
            sympy_ok_count=("sympy_ok", count_true),
            bdd_sop_time_s_median=("bdd_sop_time_s", safe_median),
            bdd_sop_ok_all=("bdd_sop_ok", safe_all),
            espresso_ok_all=("espresso_ok", safe_all),
            sampled_correctness_samples_median=("sampled_correctness_samples", safe_median),
            sampled_correctness_mismatches_median=("sampled_correctness_mismatches", safe_median),
            sampled_correctness_mismatch_rate_median=("sampled_correctness_mismatch_rate", safe_median),
            trials=("trial", "count"),
        )
        .reset_index()
    )

    # Optional additional aggregates: no-reinflate mode + final-output diagnostics.
    def _maybe_merge_group_medians(extra_spec: Dict[str, Any]) -> None:
        nonlocal agg
        if not extra_spec:
            return
        extra = df.groupby("n_vars").agg(**extra_spec).reset_index()
        agg = agg.merge(extra, on="n_vars", how="left")

    if config.cm_compare_no_reinflate and "cm_hybrid_no_reinflate_time_s" in df.columns:
        _maybe_merge_group_medians(
            {
                "cm_hybrid_no_reinflate_time_s_median": ("cm_hybrid_no_reinflate_time_s", safe_median),
                "cm_no_reinflate_time_s_median": ("cm_no_reinflate_time_s", safe_median),
                "cm_persistent_cache_no_reinflate_time_s_median": (
                    "cm_persistent_cache_no_reinflate_time_s",
                    safe_median,
                ),
                "cm_hybrid_no_reinflate_tt_extract_time_s_median": (
                    "cm_hybrid_no_reinflate_tt_extract_time_s",
                    safe_median,
                ),
                "cm_hybrid_no_reinflate_ok_all": ("cm_hybrid_no_reinflate_ok", safe_all),
                "cm_hybrid_no_reinflate_declined_count": (
                    "cm_hybrid_no_reinflate_declined",
                    count_true,
                ),
                "cm_materializations_median_alias": ("cm_materializations", safe_median),
                "cm_final_repr_median": ("cm_final_repr", safe_median),
                "cm_final_cm_materialized_median": ("cm_final_cm_materialized", safe_median),
            }
        )

    if str(config.cm_exec_target) == "runpod" and "cm_runpod_request_time_s" in df.columns:
        _maybe_merge_group_medians(
            {
                "cm_runpod_pod_started_median": ("cm_runpod_pod_started", safe_median),
                "cm_runpod_ready_wait_time_s_median": ("cm_runpod_ready_wait_time_s", safe_median),
                "cm_runpod_request_time_s_median": ("cm_runpod_request_time_s", safe_median),
                "cm_runpod_remote_exec_time_s_median": ("cm_runpod_remote_exec_time_s", safe_median),
                "cm_runpod_total_wall_time_s_median": ("cm_runpod_total_wall_time_s", safe_median),
                "cm_runpod_final_cm_materialized_median": ("cm_runpod_final_cm_materialized", safe_median),
            }
        )
        agg["cm_exec_target"] = "runpod"
        if "cm_runpod_result_repr" in df.columns:
            result_repr = df.groupby("n_vars")["cm_runpod_result_repr"].first().reset_index()
            agg = agg.merge(result_repr, on="n_vars", how="left")
        if "cm_runpod_status" in df.columns:
            status = df.groupby("n_vars")["cm_runpod_status"].first().reset_index()
            agg = agg.merge(status, on="n_vars", how="left")
    else:
        agg["cm_exec_target"] = "local"

    if bool(config.cm_compile_once_per_expression) and "cm_exec_only_time_s" in df.columns:
        _maybe_merge_group_medians(
            {
                "cm_exec_only_time_s_median": ("cm_exec_only_time_s", safe_median),
                "cm_hybrid_exec_only_time_s_median": ("cm_hybrid_exec_only_time_s", safe_median),
                "cm_partial_hybrid_exec_only_time_s_median": ("cm_partial_hybrid_exec_only_time_s", safe_median),
                "cm_hybrid_no_reinflate_exec_only_time_s_median": (
                    "cm_hybrid_no_reinflate_exec_only_time_s",
                    safe_median,
                ),
            }
        )

    if "cm_hybrid_no_reinflate_cached_exec_only_time_s" in df.columns:
        _maybe_merge_group_medians(
            {
                "cm_eval_repeat_median": ("cm_eval_repeat", safe_median),
                "cm_hybrid_no_reinflate_cached_exec_only_time_s_median": (
                    "cm_hybrid_no_reinflate_cached_exec_only_time_s",
                    safe_median,
                ),
                "cm_cached_exec_s_per_eval_median": ("cm_cached_exec_s_per_eval", safe_median),
                "bitset_cached_exec_only_time_s_median": ("bitset_cached_exec_only_time_s", safe_median),
            }
        )

    final_fields_median = (
        "final_cm_materialization_performed",
        "final_cm_materialization_time_s",
        "final_truth_table_materialization_time_s",
        "final_bitset_returned",
        "final_output_elements",
        "final_output_nominal_elements",
        "final_output_vars_count",
        "final_output_reduced",
        "large_n_output_guard_triggered",
        "final_output_representation_code",
    )
    extra_spec: Dict[str, Any] = {}
    prefixes = ["cm", "cm_hybrid", "cm_partial_hybrid", "cm_parallel"]
    if config.cm_compare_no_reinflate and "cm_hybrid_no_reinflate_time_s" in df.columns:
        prefixes.append("cm_hybrid_no_reinflate")
    for prefix in prefixes:
        for field in final_fields_median:
            col = f"{prefix}_{field}"
            if col in df.columns:
                extra_spec[f"{col}_median"] = (col, safe_median)
    _maybe_merge_group_medians(extra_spec)

    if config.cm_report_ir_breakdown:
        ir_int_fields = (
            "ir_intern_calls",
            "ir_canonicalize_calls",
            "ir_rewrite_calls",
            "ir_live_vars_calls",
            "ir_live_vars_total_inputs",
            "ir_compile_cache_hit",
            "ir_compile_cache_hits",
            "ir_compile_cache_misses",
            "ir_persistent_cache_hits",
            "ir_persistent_cache_misses",
            "ir_persistent_cache_size",
            "ir_compile_calls_per_expr",
            "ir_compile_reused_for_mode",
        )
        ir_float_fields = (
            "ir_compile_time_s",
            "ir_intern_time_s",
            "ir_canonicalize_time_s",
            "ir_rewrite_time_s",
            "ir_live_vars_time_s",
            "ir_other_time_s",
        )
        nr_int_fields = ("nr_bitset_eval_calls",)
        nr_float_fields = (
            "nr_bitset_eval_time_s",
            "nr_fallback_materialize_ir_time_s",
            "nr_tt_vector_build_time_s",
        )

        extra_spec = {}
        prefixes = ["cm", "cm_hybrid", "cm_partial_hybrid", "cm_parallel"]
        if config.cm_compare_no_reinflate and "cm_hybrid_no_reinflate_time_s" in df.columns:
            prefixes.append("cm_hybrid_no_reinflate")

        for prefix in prefixes:
            for field in ir_int_fields:
                col = f"{prefix}_{field}"
                if col in df.columns:
                    extra_spec[f"{col}_median"] = (col, safe_median)
            for field in ir_float_fields:
                col = f"{prefix}_{field}"
                if col in df.columns:
                    extra_spec[f"{col}_median"] = (col, safe_median)

        # No-reinflate-only execute/output stage breakdown.
        if "cm_hybrid_no_reinflate_nr_bitset_eval_time_s" in df.columns:
            for field in nr_int_fields:
                col = f"cm_hybrid_no_reinflate_{field}"
                if col in df.columns:
                    extra_spec[f"{col}_median"] = (col, safe_median)
            for field in nr_float_fields:
                col = f"cm_hybrid_no_reinflate_{field}"
                if col in df.columns:
                    extra_spec[f"{col}_median"] = (col, safe_median)

        # A few IR-compile structural counters for no-reinflate (useful for reports).
        for col in (
            "cm_hybrid_no_reinflate_subtree_cache_hits",
            "cm_hybrid_no_reinflate_subtree_cache_misses",
            "cm_hybrid_no_reinflate_canonical_rewrites",
            "cm_hybrid_no_reinflate_pruned_branches",
        ):
            if col in df.columns:
                extra_spec[f"{col}_median"] = (col, safe_median)

        _maybe_merge_group_medians(extra_spec)

    if config.cm_profile_cached_exec:
        cached_exec_fields = (
            "cached_exec_evaluations",
            "cached_exec_bitset_eval_calls",
            "cached_exec_result_wrap_count",
            "cached_exec_fallback_to_tt_vector_count",
            "cached_exec_packed_bitset_return_count",
            "cached_exec_reduced_output_count",
            "cached_exec_total_time_s",
            "cached_exec_dispatch_time_s",
            "cached_exec_var_order_time_s",
            "cached_exec_fixed_handling_time_s",
            "cached_exec_bitset_eval_time_s",
            "cached_exec_result_wrap_time_s",
            "cached_exec_correctness_or_extract_time_s",
            "cached_exec_other_time_s",
        )
        extra_spec = {}
        for field in cached_exec_fields:
            col = f"cm_hybrid_no_reinflate_{field}"
            if col in df.columns:
                extra_spec[f"{col}_median"] = (col, safe_median)
        _maybe_merge_group_medians(extra_spec)

    def ratio(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        if isinstance(a, float) and (a != a):
            return None
        if isinstance(b, float) and (b != b):
            return None
        if b == 0:
            return None
        return float(a / b)

    agg["ratio_cm_parallel_over_cm"] = agg.apply(
        lambda r: ratio(r["cm_parallel_time_s_median"], r["cm_time_s_median"]), axis=1
    )
    agg["ratio_cm_parallel_over_bitset"] = agg.apply(
        lambda r: ratio(r["cm_parallel_time_s_median"], r["bitset_time_s_median"]), axis=1
    )
    agg["ratio_cm_hybrid_over_cm"] = agg.apply(
        lambda r: ratio(r["cm_hybrid_time_s_median"], r["cm_time_s_median"]), axis=1
    )
    agg["ratio_cm_hybrid_over_bitset"] = agg.apply(
        lambda r: ratio(r["cm_hybrid_time_s_median"], r["bitset_time_s_median"]), axis=1
    )
    agg["ratio_cm_partial_hybrid_over_cm"] = agg.apply(
        lambda r: ratio(r["cm_partial_hybrid_time_s_median"], r["cm_time_s_median"]), axis=1
    )
    agg["ratio_cm_partial_hybrid_over_bitset"] = agg.apply(
        lambda r: ratio(r["cm_partial_hybrid_time_s_median"], r["bitset_time_s_median"]), axis=1
    )
    agg["ratio_robdd_build_over_bitset"] = agg.apply(
        lambda r: ratio(r["robdd_build_time_s_median"], r["bitset_time_s_median"]), axis=1
    )
    agg["ratio_robdd_build_extract_over_bitset"] = agg.apply(
        lambda r: ratio(r["robdd_total_build_plus_extract_time_s_median"], r["bitset_time_s_median"]), axis=1
    )
    if "cm_hybrid_no_reinflate_time_s_median" in agg.columns:
        agg["ratio_cm_hybrid_no_reinflate_over_cm"] = agg.apply(
            lambda r: ratio(r["cm_hybrid_no_reinflate_time_s_median"], r["cm_time_s_median"]), axis=1
        )
        agg["ratio_cm_hybrid_no_reinflate_over_cm_hybrid"] = agg.apply(
            lambda r: ratio(r["cm_hybrid_no_reinflate_time_s_median"], r["cm_hybrid_time_s_median"]), axis=1
        )
        agg["ratio_cm_hybrid_no_reinflate_over_bitset"] = agg.apply(
            lambda r: ratio(r["cm_hybrid_no_reinflate_time_s_median"], r["bitset_time_s_median"]), axis=1
        )
        agg["ratio_robdd_build_over_cm_no_reinflate"] = agg.apply(
            lambda r: ratio(r["robdd_build_time_s_median"], r["cm_hybrid_no_reinflate_time_s_median"]), axis=1
        )
        agg["ratio_robdd_build_extract_over_cm_no_reinflate"] = agg.apply(
            lambda r: ratio(
                r["robdd_total_build_plus_extract_time_s_median"],
                r["cm_hybrid_no_reinflate_time_s_median"],
            ),
            axis=1,
        )
    if (
        "cm_hybrid_no_reinflate_cached_exec_only_time_s_median" in agg.columns
        and "bitset_cached_exec_only_time_s_median" in agg.columns
    ):
        agg["ratio_cm_hybrid_no_reinflate_cached_over_bitset_cached"] = agg.apply(
            lambda r: ratio(
                r["cm_hybrid_no_reinflate_cached_exec_only_time_s_median"],
                r["bitset_cached_exec_only_time_s_median"],
            ),
            axis=1,
        )
    if "cm_cached_exec_s_per_eval_median" in agg.columns:
        agg["ratio_robdd_build_over_cm_cached_exec"] = agg.apply(
            lambda r: ratio(r["robdd_build_time_s_median"], r["cm_cached_exec_s_per_eval_median"]), axis=1
        )
        agg["ratio_robdd_build_extract_over_cm_cached_exec"] = agg.apply(
            lambda r: ratio(
                r["robdd_total_build_plus_extract_time_s_median"],
                r["cm_cached_exec_s_per_eval_median"],
            ),
            axis=1,
        )
    agg["ratio_cm_plus_extract_over_bitset_plus_extract"] = agg.apply(
        lambda r: ratio(
            (
                (r["cm_time_s_median"] if r["cm_time_s_median"] == r["cm_time_s_median"] else 0.0)
                + (
                    r["cm_tt_extract_time_s_median"]
                    if r["cm_tt_extract_time_s_median"] == r["cm_tt_extract_time_s_median"]
                    else 0.0
                )
            ),
            (
                (r["bitset_time_s_median"] if r["bitset_time_s_median"] == r["bitset_time_s_median"] else 0.0)
                + (
                    r["bitset_extract_time_s_median"]
                    if r["bitset_extract_time_s_median"] == r["bitset_extract_time_s_median"]
                    else 0.0
                )
            ),
        ),
        axis=1,
    )

    agg["backend_robdd"] = not config.no_robdd
    agg["backend_dd"] = use_dd and (not config.no_dd)
    agg["backend_robdd_dd"] = use_dd and (not config.no_dd) and (not config.no_robdd_dd)
    agg["backend_espresso"] = use_espresso and (not config.no_espresso)
    agg["backend_bitset"] = not config.no_bitset
    agg["backend_numba"] = (not config.no_numba) and HAS_NUMBA
    agg["backend_cm_parallel"] = bool(config.cm_parallel)
    agg["backend_cm_compare_hybrid"] = bool(config.cm_compare_hybrid)
    agg["backend_cm_compare_no_reinflate"] = bool(config.cm_compare_no_reinflate)
    agg["cm_hybrid_threshold"] = int(config.cm_hybrid_threshold)
    agg["cm_words_eval"] = bool(config.cm_words_eval)
    agg["cm_default_materialize_mode"] = "numpy" if config.cm_compare_hybrid else "partial_hybrid"
    agg["cm_layout"] = config.cm_layout
    agg["expr_style"] = expr_style
    return df, agg


def _matrix_literal(a: np.ndarray) -> str:
    return ";".join("".join("1" if bool(v) else "0" for v in row) for row in np.asarray(a, dtype=bool))


def operator_quotient_2x2_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for name_a, mat_a in CM_2X2.items():
        for name_b, mat_b in CM_2X2.items():
            q_ab = cm_quotient(mat_a, mat_b)
            q_ba = cm_quotient(mat_b, mat_a)
            sym = cm_symmetric_delta(mat_a, mat_b)
            overlap = cm_overlap(mat_a, mat_b)
            counts = cm_feature_counts(mat_a, mat_b)
            rows.append(
                {
                    "n_vars": 2,
                    "trial": len(rows),
                    "expr_style": "operator_table_2x2",
                    "operator_pair_style": "operator_table_2x2",
                    "operator_diff_mode": "cm_quotient",
                    "operator_a": name_a,
                    "operator_b": name_b,
                    "quotient_a_minus_b_name": cm_2x2_name(q_ab),
                    "quotient_b_minus_a_name": cm_2x2_name(q_ba),
                    "symmetric_delta_name": cm_2x2_name(sym),
                    "overlap_name": cm_2x2_name(overlap),
                    "same_operator": bool(name_a == name_b),
                    "basis_vars": "X,Y",
                    "row_vars": "X,!X",
                    "col_vars": "Y,!Y",
                    "basis_aligned": True,
                    "basis_alignment_note": "2x2 canonical rows X,!X and columns Y,!Y",
                    "dense_shape": "2x2",
                    "dense_elements": 4,
                    "quotient_a_minus_b_matrix": _matrix_literal(q_ab),
                    "quotient_b_minus_a_matrix": _matrix_literal(q_ba),
                    "symmetric_delta_matrix": _matrix_literal(sym),
                    "cm_quotient_a_minus_b_time_s": 0.0,
                    "cm_quotient_b_minus_a_time_s": 0.0,
                    "cm_symmetric_delta_time_s": 0.0,
                    "cm_quotient_total_time_s": 0.0,
                    **counts,
                    "semantic_delta_density": None,
                    "semantic_equivalent": bool(name_a == name_b),
                    "structural_same": bool(name_a == name_b),
                    "opdiff_semantic_equivalent": bool(name_a == name_b),
                    "opdiff_structural_same": bool(name_a == name_b),
                }
            )
    return rows


def write_operator_quotient_2x2_table(path: str = "operator_quotient_2x2_table.csv") -> None:
    import pandas as pd

    pd.DataFrame(operator_quotient_2x2_rows()).to_csv(path, index=False)


def cm_transform_2x2_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for name, mat in CM_2X2.items():
        transpose = cm_transpose(mat)
        complement = cm_complement(mat)
        rotate90 = cm_rotate90(mat)
        rotate180 = cm_rotate180(mat)
        rotate270 = cm_rotate270(mat)
        negate_left = cm_transform_negate_left_operand(mat)
        negate_right = cm_transform_negate_right_operand(mat)
        negate_both = cm_transform_negate_both_operands(mat)
        swap = cm_transform_swap_operands(mat)
        negate_expr = cm_transform_negate_expression(mat)
        rows.append(
            {
                "operator": name,
                "matrix": _matrix_literal(mat),
                "transpose_name": cm_2x2_name(transpose),
                "complement_name": cm_2x2_name(complement),
                "rotate90_name": cm_2x2_name(rotate90),
                "rotate180_name": cm_2x2_name(rotate180),
                "rotate270_name": cm_2x2_name(rotate270),
                "negate_left_operand_name": cm_2x2_name(negate_left),
                "negate_right_operand_name": cm_2x2_name(negate_right),
                "negate_both_operands_name": cm_2x2_name(negate_both),
                "swap_operands_name": cm_2x2_name(swap),
                "negate_expression_name": cm_2x2_name(negate_expr),
                "transpose_correct": cm_2x2_transform_correct(mat, cm_transform_swap_operands, "transpose"),
                "complement_correct": cm_2x2_transform_correct(mat, cm_transform_negate_expression, "complement"),
                "negate_left_correct": cm_2x2_transform_correct(
                    mat, cm_transform_negate_left_operand, "negate_left_operand"
                ),
                "negate_right_correct": cm_2x2_transform_correct(
                    mat, cm_transform_negate_right_operand, "negate_right_operand"
                ),
                "negate_both_correct": cm_2x2_transform_correct(
                    mat, cm_transform_negate_both_operands, "negate_both_operands"
                ),
            }
        )
    return rows


def write_cm_transform_2x2_table(path: str = "cm_transform_2x2_table.csv") -> None:
    import pandas as pd

    pd.DataFrame(cm_transform_2x2_rows()).to_csv(path, index=False)


def run_cm_transformation_bench():
    import pandas as pd

    kind = str(_current_config().cm_transform_kind)
    rows = cm_transform_2x2_rows()
    if kind != "all":
        name_col = {
            "complement": "complement_name",
            "transpose": "transpose_name",
            "rotate90": "rotate90_name",
            "rotate180": "rotate180_name",
            "rotate270": "rotate270_name",
            "negate_left_operand": "negate_left_operand_name",
            "negate_right_operand": "negate_right_operand_name",
            "negate_both_operands": "negate_both_operands_name",
        }[kind]
        correct_col = {
            "complement": "complement_correct",
            "transpose": "transpose_correct",
            "negate_left_operand": "negate_left_correct",
            "negate_right_operand": "negate_right_correct",
            "negate_both_operands": "negate_both_correct",
        }.get(kind)
        rows = [
            {
                "operator": row["operator"],
                "matrix": row["matrix"],
                "cm_transform_kind": kind,
                "result_name": row[name_col],
                "correct": row[correct_col] if correct_col else None,
            }
            for row in rows
        ]
    df = pd.DataFrame(rows)
    write_cm_transform_2x2_table()
    bool_cols = [c for c in df.columns if c.endswith("_correct") or c == "correct"]
    agg = pd.DataFrame(
        [
            {
                "cm_transform_kind": kind,
                "operators": int(len(df)),
                "valid_lookup_names": bool(
                    all(
                        str(v) != "UNKNOWN"
                        for c in df.columns
                        if c.endswith("_name") or c == "result_name"
                        for v in df[c].dropna().tolist()
                    )
                ),
                **{f"{c}_all": bool(df[c].dropna().astype(bool).all()) for c in bool_cols},
            }
        ]
    )
    return df, agg


def generate_operator_pair(
    n_vars: int,
    rng: np.random.Generator,
    max_depth: int,
    expr_style: str,
    pair_style: str,
) -> Tuple[Any, Any, Optional[bool]]:
    if pair_style == "related_variant":
        expr_a = random_expr_for_style(n_vars, rng, max_depth=max_depth, style=expr_style)
        paths = [p for p in _expr_paths(expr_a) if p]
        if paths:
            path = paths[int(rng.integers(0, len(paths)))]
            replacement = _small_random_subtree(n_vars, rng, max_depth, expr_style)
            expr_b = _expr_replace_subtree(expr_a, path, replacement)
        else:
            expr_b = Not(expr_a)
        return expr_a, expr_b, None
    if pair_style == "equivalent_rewrite":
        expr_a = random_expr_for_style(n_vars, rng, max_depth=max_depth, style=expr_style)
        return expr_a, _rewrite_equiv_expr(expr_a, rng), True
    if pair_style == "near_miss":
        expr_a = random_expr_for_style(n_vars, rng, max_depth=max_depth, style=expr_style)
        used = _expr_used_indices(expr_a)
        idx = used[0] if used else int(rng.integers(0, max(1, n_vars)))
        return expr_a, Xor(expr_a, Var(idx)), False
    if pair_style == "shared_blocks":
        block_count = max(2, int(_current_config().family_shared_blocks))
        blocks = [
            random_expr_for_style(n_vars, rng, max_depth=max(1, max_depth - 1), style=expr_style)
            for _ in range(block_count)
        ]
        h_a = _small_random_subtree(n_vars, rng, max_depth, expr_style)
        h_b = _small_random_subtree(n_vars, rng, max_depth, expr_style)
        expr_a = Or(And(blocks[0], h_a), Xor(blocks[1], blocks[2 % block_count]))
        expr_b = Or(And(blocks[0], h_b), Xor(blocks[1], blocks[3 % block_count]))
        return expr_a, expr_b, None
    if pair_style == "independent":
        return (
            random_expr_for_style(n_vars, rng, max_depth=max_depth, style=expr_style),
            random_expr_for_style(n_vars, rng, max_depth=max_depth, style=expr_style),
            None,
        )
    if pair_style == "containment_pair":
        return Or(Var(0), Var(1 if n_vars > 1 else 0)), And(Var(0), Var(1 if n_vars > 1 else 0)), False
    if pair_style == "transform_pairs":
        left = random_expr_for_style(n_vars, rng, max_depth=max(1, max_depth - 1), style=expr_style)
        right = random_expr_for_style(n_vars, rng, max_depth=max(1, max_depth - 1), style=expr_style)
        op = rng.choice((And, Or, Xor, Imp, Eqv))
        expr_a = op(left, right)
        transform = int(rng.integers(0, 5))
        if transform == 0:
            expr_b = op(right, left)
        elif transform == 1:
            expr_b = Not(expr_a)
        elif transform == 2:
            expr_b = op(Not(left), right)
        elif transform == 3:
            expr_b = op(left, Not(right))
        else:
            expr_b = op(Not(left), Not(right))
        return expr_a, expr_b, None
    raise ValueError(f"unknown operator pair style: {pair_style!r}")


def structural_hash_delta(expr_a: Any, expr_b: Any) -> Dict[str, Any]:
    t0 = time.perf_counter()
    ca = Counter(collect_subtree_hashes(expr_a))
    cb = Counter(collect_subtree_hashes(expr_b))
    shared = ca & cb
    added = cb - ca
    removed = ca - cb
    union = ca | cb
    elapsed = time.perf_counter() - t0
    shared_count = int(sum(shared.values()))
    union_count = int(sum(union.values()))
    return {
        "opdiff_cm_struct_features_a": int(sum(ca.values())),
        "opdiff_cm_struct_features_b": int(sum(cb.values())),
        "opdiff_cm_struct_shared_features": shared_count,
        "opdiff_cm_struct_added_features": int(sum(added.values())),
        "opdiff_cm_struct_removed_features": int(sum(removed.values())),
        "opdiff_cm_struct_jaccard": float(shared_count / union_count) if union_count else 1.0,
        "opdiff_cm_struct_delta_time_s": elapsed,
        "opdiff_cm_struct_status": "prototype_feature_multiset_delta",
    }


def bitset_truth_delta(expr_a: Any, expr_b: Any, n_vars: int) -> Dict[str, Any]:
    env = build_bitset_env([f"x{i}" for i in range(n_vars)])
    try:
        t0 = time.perf_counter()
        bits_a = eval_expr_bitset(expr_a, env)
        eval_a = time.perf_counter() - t0
        t1 = time.perf_counter()
        bits_b = eval_expr_bitset(expr_b, env)
        eval_b = time.perf_counter() - t1
        t2 = time.perf_counter()
        delta = int(bits_a) ^ int(bits_b)
        delta_time = time.perf_counter() - t2
        total = eval_a + eval_b + delta_time
        true_count = int(delta.bit_count())
        denom = 1 << n_vars
        equiv = bool(delta == 0)
        return {
            "opdiff_bitset_eval_a_time_s": eval_a,
            "opdiff_bitset_eval_b_time_s": eval_b,
            "opdiff_bitset_delta_time_s": delta_time,
            "opdiff_bitset_total_time_s": total,
            "opdiff_bitset_delta_density": float(true_count / denom),
            "opdiff_bitset_delta_true_count": true_count,
            "opdiff_bitset_equivalent": equiv,
            "opdiff_bitset_ok": True,
            "bitset_eval_a_time_s": eval_a,
            "bitset_eval_b_time_s": eval_b,
            "bitset_delta_time_s": delta_time,
            "bitset_total_time_s": total,
            "semantic_delta_true_count": true_count,
            "semantic_delta_density": float(true_count / denom),
            "semantic_equivalent": equiv,
            "opdiff_semantic_equivalent": equiv,
        }
    except Exception as exc:
        return {
            "opdiff_bitset_eval_a_time_s": None,
            "opdiff_bitset_eval_b_time_s": None,
            "opdiff_bitset_delta_time_s": None,
            "opdiff_bitset_total_time_s": None,
            "opdiff_bitset_delta_density": None,
            "opdiff_bitset_delta_true_count": None,
            "opdiff_bitset_equivalent": None,
            "opdiff_bitset_ok": False,
            "opdiff_bitset_error": repr(exc),
            "semantic_delta_density": None,
            "semantic_equivalent": None,
            "opdiff_semantic_equivalent": None,
        }


def _dd_xor(manager, a, b):
    try:
        return a ^ b
    except TypeError:
        return manager.apply("xor", a, b)


def robdd_symbolic_delta(expr_a: Any, expr_b: Any, n_vars: int, seed: int) -> Dict[str, Any]:
    bench_config = _current_config()
    backend = str(bench_config.robdd_dd_backend)
    order_policy = str(bench_config.robdd_order_policy)
    sweeps = max(1, int(bench_config.robdd_order_sweeps)) if order_policy == "best-of-k" else 1
    dd_module, error = select_dd_module(backend)
    if dd_module is None:
        return {
            "opdiff_robdd_backend": backend,
            "opdiff_robdd_build_a_time_s": None,
            "opdiff_robdd_build_b_time_s": None,
            "opdiff_robdd_delta_time_s": None,
            "opdiff_robdd_total_time_s": None,
            "opdiff_robdd_nodes_a": None,
            "opdiff_robdd_nodes_b": None,
            "opdiff_robdd_nodes_delta": None,
            "opdiff_robdd_equivalent": None,
            "opdiff_robdd_ok": None,
            "opdiff_robdd_status": "unavailable",
            "opdiff_robdd_error": error,
        }
    names = [f"x{i}" for i in range(n_vars)]
    var_name_map = {name: name for name in names}
    combined = And(expr_a, expr_b)
    trials_out: List[Dict[str, Any]] = []
    for sweep in range(sweeps):
        effective_policy = "random" if order_policy == "best-of-k" else order_policy
        effective_seed = int(seed) + sweep if effective_policy == "random" else seed
        order = robdd_variable_order(combined, n_vars, effective_policy, effective_seed)
        try:
            manager = dd_module.BDD()
            _declare_dd_vars(manager, order)
            t0 = time.perf_counter()
            root_a = expr_to_dd_bdd(expr_a, manager, var_name_map)
            build_a = time.perf_counter() - t0
            nodes_a = safe_bdd_node_count(manager, root_a)
            t1 = time.perf_counter()
            root_b = expr_to_dd_bdd(expr_b, manager, var_name_map)
            build_b = time.perf_counter() - t1
            nodes_b = safe_bdd_node_count(manager, root_b)
            t2 = time.perf_counter()
            root_delta = _dd_xor(manager, root_a, root_b)
            equivalent = bool(root_delta == manager.false)
            delta_time = time.perf_counter() - t2
            nodes_delta = safe_bdd_node_count(manager, root_delta)
            ident = bdd_backend_identity(manager)
            trials_out.append(
                {
                    "backend": "dd.cudd" if ident.get("is_cudd") else ("dd.autoref" if ident.get("is_autoref") else ident.get("module")),
                    "build_a": build_a,
                    "build_b": build_b,
                    "delta": delta_time,
                    "nodes_a": nodes_a,
                    "nodes_b": nodes_b,
                    "nodes_delta": nodes_delta,
                    "equivalent": equivalent,
                    "total": build_a + build_b + delta_time,
                    "status": "ok",
                    "error": None,
                }
            )
        except Exception as exc:
            trials_out.append({"status": "error", "error": repr(exc)})
    ok = [r for r in trials_out if r.get("status") == "ok"]
    if not ok:
        return {
            "opdiff_robdd_backend": backend,
            "opdiff_robdd_build_a_time_s": None,
            "opdiff_robdd_build_b_time_s": None,
            "opdiff_robdd_delta_time_s": None,
            "opdiff_robdd_total_time_s": None,
            "opdiff_robdd_nodes_a": None,
            "opdiff_robdd_nodes_b": None,
            "opdiff_robdd_nodes_delta": None,
            "opdiff_robdd_equivalent": None,
            "opdiff_robdd_ok": None,
            "opdiff_robdd_status": "error",
            "opdiff_robdd_error": next((r.get("error") for r in trials_out if r.get("error")), None),
        }
    best = min(ok, key=lambda r: (float(r.get("nodes_delta") or 10**30), float(r.get("total") or 10**30)))
    return {
        "opdiff_robdd_backend": best["backend"],
        "opdiff_robdd_build_a_time_s": best["build_a"],
        "opdiff_robdd_build_b_time_s": best["build_b"],
        "opdiff_robdd_delta_time_s": best["delta"],
        "opdiff_robdd_total_time_s": best["total"],
        "opdiff_robdd_nodes_a": best["nodes_a"],
        "opdiff_robdd_nodes_b": best["nodes_b"],
        "opdiff_robdd_nodes_delta": best["nodes_delta"],
        "opdiff_robdd_equivalent": best["equivalent"],
        "opdiff_robdd_ok": True,
        "opdiff_robdd_status": "ok",
        "opdiff_robdd_error": None,
        "robdd_backend": best["backend"],
        "robdd_build_a_time_s": best["build_a"],
        "robdd_build_b_time_s": best["build_b"],
        "robdd_delta_time_s": best["delta"],
        "robdd_total_time_s": best["total"],
        "robdd_nodes_a": best["nodes_a"],
        "robdd_nodes_b": best["nodes_b"],
        "robdd_nodes_delta": best["nodes_delta"],
        "robdd_semantic_equivalent": best["equivalent"],
    }


def cm_no_reinflate_truth_delta(expr_a: Any, expr_b: Any, n_vars: int) -> Dict[str, Any]:
    vars_all = [f"x{i}" for i in range(n_vars)]
    diag_a: Dict[str, Any] = {}
    diag_b: Dict[str, Any] = {}
    bench_config = _current_config()
    try:
        t0 = time.perf_counter()
        node_a = compile_expr_to_cm_ir(
            expr_a,
            diagnostics=diag_a,
            persistent_cache=bool(bench_config.cm_use_persistent_cache),
        )
        compile_a = time.perf_counter() - t0
        t1 = time.perf_counter()
        node_b = compile_expr_to_cm_ir(
            expr_b,
            diagnostics=diag_b,
            persistent_cache=bool(bench_config.cm_use_persistent_cache),
        )
        compile_b = time.perf_counter() - t1
        t2 = time.perf_counter()
        res_a = materialize_hybrid_no_reinflate(
            node_a,
            vars_all,
            fixed={},
            diagnostics=diag_a,
            hybrid_threshold=int(bench_config.cm_hybrid_threshold),
            words_eval=bool(bench_config.cm_words_eval),
        )
        eval_a = time.perf_counter() - t2
        t3 = time.perf_counter()
        res_b = materialize_hybrid_no_reinflate(
            node_b,
            vars_all,
            fixed={},
            diagnostics=diag_b,
            hybrid_threshold=int(bench_config.cm_hybrid_threshold),
            words_eval=bool(bench_config.cm_words_eval),
        )
        eval_b = time.perf_counter() - t3
        t4 = time.perf_counter()
        if tuple(res_a.output_vars) != tuple(res_b.output_vars):
            raise ValueError("no-reinflate outputs use different variable orders")
        if res_a.bits is not None and res_b.bits is not None:
            delta_bits = int(res_a.bits) ^ int(res_b.bits)
            true_count = int(delta_bits.bit_count())
            width = len(res_a.output_vars)
        else:
            tt_a = bitset_to_bool_array(int(res_a.bits), len(res_a.output_vars)) if res_a.bits is not None else res_a.tt
            tt_b = bitset_to_bool_array(int(res_b.bits), len(res_b.output_vars)) if res_b.bits is not None else res_b.tt
            if tt_a is None or tt_b is None:
                raise ValueError("missing no-reinflate payload")
            delta_arr = np.logical_xor(tt_a.astype(bool), tt_b.astype(bool))
            true_count = int(np.count_nonzero(delta_arr))
            width = len(res_a.output_vars)
        delta_time = time.perf_counter() - t4
        denom = 1 << width
        total = compile_a + compile_b + eval_a + eval_b + delta_time
        return {
            "opdiff_cm_nr_compile_a_time_s": compile_a,
            "opdiff_cm_nr_compile_b_time_s": compile_b,
            "opdiff_cm_nr_eval_a_time_s": eval_a,
            "opdiff_cm_nr_eval_b_time_s": eval_b,
            "opdiff_cm_nr_delta_time_s": delta_time,
            "opdiff_cm_nr_total_time_s": total,
            "opdiff_cm_nr_delta_density": float(true_count / denom),
            "opdiff_cm_nr_equivalent": bool(true_count == 0),
            "opdiff_cm_nr_ok": True,
        }
    except Exception as exc:
        return {
            "opdiff_cm_nr_compile_a_time_s": None,
            "opdiff_cm_nr_compile_b_time_s": None,
            "opdiff_cm_nr_eval_a_time_s": None,
            "opdiff_cm_nr_eval_b_time_s": None,
            "opdiff_cm_nr_delta_time_s": None,
            "opdiff_cm_nr_total_time_s": None,
            "opdiff_cm_nr_delta_density": None,
            "opdiff_cm_nr_equivalent": None,
            "opdiff_cm_nr_ok": False,
            "opdiff_cm_nr_error": repr(exc),
        }


def dense_cm_quotient_delta(expr_a: Any, expr_b: Any, n_vars: int) -> Dict[str, Any]:
    bench_config = _current_config()
    max_dense_n = int(bench_config.operator_quotient_max_dense_n)
    vars_all = [f"x{i}" for i in range(n_vars)]
    R, C = canonical_layout(vars_all, mode=str(bench_config.cm_layout))
    out: Dict[str, Any] = {
        "basis_vars": ",".join(vars_all),
        "row_vars": ",".join(R),
        "col_vars": ",".join(C),
        "basis_aligned": True,
        "basis_alignment_note": "same canonical_layout basis used for both dense CM artifacts",
    }
    if n_vars > max_dense_n:
        out.update(
            {
                "cm_dense_status": "skipped_dense_n_limit",
                "cm_quotient_status": "skipped_dense_n_limit",
                "dense_quotient_status": "skipped_limit",
                "dense_shape": None,
                "dense_elements": None,
                "opdiff_cm_dense_ok": None,
            }
        )
        return out
    try:
        diag_a: Dict[str, Any] = {}
        diag_b: Dict[str, Any] = {}
        t0 = time.perf_counter()
        node_a = compile_expr_to_cm_ir(
            expr_a,
            diagnostics=diag_a,
            persistent_cache=bool(bench_config.cm_use_persistent_cache),
        )
        mat_a = materialize_cm(
            node_a,
            R,
            C,
            fixed={},
            diagnostics=diag_a,
            materialize_mode="partial_hybrid",
            hybrid_threshold=int(bench_config.cm_hybrid_threshold),
        )
        dense_a = time.perf_counter() - t0
        t1 = time.perf_counter()
        node_b = compile_expr_to_cm_ir(
            expr_b,
            diagnostics=diag_b,
            persistent_cache=bool(bench_config.cm_use_persistent_cache),
        )
        mat_b = materialize_cm(
            node_b,
            R,
            C,
            fixed={},
            diagnostics=diag_b,
            materialize_mode="partial_hybrid",
            hybrid_threshold=int(bench_config.cm_hybrid_threshold),
        )
        dense_b = time.perf_counter() - t1
        bool_a = np.asarray(mat_a, dtype=bool)
        bool_b = np.asarray(mat_b, dtype=bool)
        t2 = time.perf_counter()
        q_ab = cm_quotient(bool_a, bool_b)
        q_ab_time = time.perf_counter() - t2
        t3 = time.perf_counter()
        q_ba = cm_quotient(bool_b, bool_a)
        q_ba_time = time.perf_counter() - t3
        t4 = time.perf_counter()
        sym = cm_symmetric_delta(bool_a, bool_b)
        sym_time = time.perf_counter() - t4
        counts = cm_feature_counts(bool_a, bool_b)
        total = dense_a + dense_b + q_ab_time + q_ba_time + sym_time
        out.update(
            {
                "cm_dense_status": "ok",
                "cm_quotient_status": "ok",
                "dense_quotient_status": "ok",
                "dense_shape": "x".join(str(v) for v in bool_a.shape),
                "dense_elements": int(bool_a.size),
                "cm_dense_a_time_s": dense_a,
                "cm_dense_b_time_s": dense_b,
                "cm_quotient_a_minus_b_time_s": q_ab_time,
                "cm_quotient_b_minus_a_time_s": q_ba_time,
                "cm_symmetric_delta_time_s": sym_time,
                "cm_quotient_total_time_s": total,
                "opdiff_cm_dense_a_time_s": dense_a,
                "opdiff_cm_dense_b_time_s": dense_b,
                "opdiff_cm_dense_delta_time_s": sym_time,
                "opdiff_cm_dense_total_time_s": total,
                "opdiff_cm_dense_matrix_elements": int(bool_a.size),
                "opdiff_cm_dense_delta_density": float(np.count_nonzero(sym) / max(1, sym.size)),
                "opdiff_cm_dense_ok": True,
                **counts,
            }
        )
        if bool(bench_config.operator_quotient_report_matrix) and bool_a.size <= 256:
            out["quotient_a_minus_b_matrix"] = _matrix_literal(q_ab)
            out["quotient_b_minus_a_matrix"] = _matrix_literal(q_ba)
            out["symmetric_delta_matrix"] = _matrix_literal(sym)
        return out
    except Exception as exc:
        out.update(
            {
                "cm_dense_status": "error",
                "cm_quotient_status": "error",
                "dense_quotient_status": "error",
                "cm_quotient_error": repr(exc),
                "opdiff_cm_dense_ok": False,
            }
        )
        return out


def _operator_modes(mode: str) -> set:
    if mode == "cm_transform":
        return {"cm_transform"}
    if mode == "all":
        return {"truth_delta", "cm_quotient", "cm_symmetric_delta", "cm_dense_delta", "cm_structural_hash_delta"}
    return {mode}


def operator_pair_diagnostics(expr_a: Any, expr_b: Any, n_vars: int, pair_style: str, expected: Optional[bool]) -> Dict[str, Any]:
    hashes_a = collect_subtree_hashes(expr_a)
    hashes_b = collect_subtree_hashes(expr_b)
    ca = Counter(hashes_a)
    cb = Counter(hashes_b)
    shared = int(sum((ca & cb).values()))
    total = int(sum((ca | cb).values()))
    used = set(_expr_used_indices(expr_a)) | set(_expr_used_indices(expr_b))
    truth_density = None
    if n_vars <= int(_current_config().full_tt_max_n):
        tt_a = eval_expr_tt(expr_a, n_vars).astype(np.uint8).reshape(-1)
        tt_b = eval_expr_tt(expr_b, n_vars).astype(np.uint8).reshape(-1)
        truth_density = float(np.count_nonzero(np.logical_xor(tt_a, tt_b)) / max(1, tt_a.size))
    return {
        "operator_pair_style": pair_style,
        "operator_expected_equivalent": expected,
        "opdiff_expected_equivalent": expected,
        "operator_pair_shared_subtree_ratio": float(shared / total) if total else 1.0,
        "operator_pair_structural_hash_same": bool(expr_structural_hash(expr_a) == expr_structural_hash(expr_b)),
        "operator_pair_truth_delta_density": truth_density,
        "operator_pair_unique_vars": int(len(used)),
        "opdiff_structural_same": bool(expr_structural_hash(expr_a) == expr_structural_hash(expr_b)),
    }


def run_operator_difference_bench(sizes: List[int], trials: int, seed: int, max_depth: int, verbose: bool):
    import pandas as pd

    bench_config = _current_config()
    mode = str(bench_config.operator_diff_mode)
    modes = _operator_modes(mode)
    pair_style = str(bench_config.operator_pair_style)
    expr_style = str(bench_config.expr_style)
    rows: List[Dict[str, Any]] = []

    if mode == "cm_transform":
        return run_cm_transformation_bench()
    if pair_style == "operator_table_2x2":
        rows = operator_quotient_2x2_rows()
        write_operator_quotient_2x2_table()
    else:
        rng = np.random.default_rng(seed)
        for n in sizes:
            if verbose:
                print(f"\n=== operator difference n = {n} ===")
            for t in range(trials):
                expr_a, expr_b, expected = generate_operator_pair(n, rng, max_depth, expr_style, pair_style)
                row: Dict[str, Any] = {
                    "n_vars": n,
                    "trial": t,
                    "expr_style": expr_style,
                    "operator_diff_mode": mode,
                    **operator_pair_diagnostics(expr_a, expr_b, n, pair_style, expected),
                }
                if "truth_delta" in modes and (not bench_config.no_bitset):
                    row.update(bitset_truth_delta(expr_a, expr_b, n))
                if (not bench_config.no_dd) and (not bench_config.no_robdd_dd):
                    row.update(robdd_symbolic_delta(expr_a, expr_b, n, int(seed + n * 1009 + t * 9176)))
                if bool(bench_config.cm_compare_no_reinflate):
                    row.update(cm_no_reinflate_truth_delta(expr_a, expr_b, n))
                if modes & {"cm_quotient", "cm_symmetric_delta", "cm_dense_delta"}:
                    row.update(dense_cm_quotient_delta(expr_a, expr_b, n))
                if "cm_structural_hash_delta" in modes:
                    row.update(structural_hash_delta(expr_a, expr_b))
                row["ratio_cm_struct_over_bitset_delta"] = _ratio_or_none(
                    row.get("opdiff_cm_struct_delta_time_s"), row.get("opdiff_bitset_delta_time_s")
                )
                row["ratio_cm_nr_over_bitset_delta"] = _ratio_or_none(
                    row.get("opdiff_cm_nr_total_time_s"), row.get("opdiff_bitset_total_time_s")
                )
                row["ratio_robdd_over_bitset_delta"] = _ratio_or_none(
                    row.get("opdiff_robdd_total_time_s"), row.get("opdiff_bitset_total_time_s")
                )
                row["ratio_cm_dense_over_bitset_delta"] = _ratio_or_none(
                    row.get("opdiff_cm_dense_total_time_s"), row.get("opdiff_bitset_total_time_s")
                )
                rows.append(row)

    df = pd.DataFrame(rows)

    def safe_median(s):
        try:
            return float(s.dropna().median())
        except Exception:
            return None

    def safe_first(s):
        try:
            x = s.dropna().tolist()
            return x[0] if x else None
        except Exception:
            return None

    def safe_all(s):
        try:
            x = s.dropna().tolist()
            return all(bool(v) for v in x) if x else None
        except Exception:
            return None

    group_cols = ["n_vars", "expr_style", "operator_pair_style", "operator_diff_mode"]
    agg_spec: Dict[str, Any] = {"trials": ("trial", "count")}
    for c in [
        "opdiff_bitset_total_time_s",
        "opdiff_robdd_total_time_s",
        "opdiff_cm_nr_total_time_s",
        "opdiff_cm_dense_total_time_s",
        "cm_quotient_total_time_s",
        "cm_symmetric_delta_time_s",
        "opdiff_cm_struct_delta_time_s",
        "opdiff_bitset_delta_density",
        "opdiff_robdd_nodes_delta",
        "opdiff_cm_dense_delta_density",
        "opdiff_cm_struct_jaccard",
        "a_minus_b_features",
        "b_minus_a_features",
        "symmetric_delta_features",
        "overlap_features",
        "jaccard_features",
        "ratio_cm_struct_over_bitset_delta",
        "ratio_cm_nr_over_bitset_delta",
        "ratio_robdd_over_bitset_delta",
        "ratio_cm_dense_over_bitset_delta",
    ]:
        if c in df.columns:
            agg_spec[f"{c}_median"] = (c, safe_median)
    for c in ["opdiff_semantic_equivalent", "opdiff_structural_same", "a_contains_b", "b_contains_a", "basis_aligned"]:
        if c in df.columns:
            agg_spec[f"{c}_all"] = (c, safe_all)
    for c in ["opdiff_robdd_backend", "cm_quotient_status", "cm_dense_status", "basis_alignment_note"]:
        if c in df.columns:
            agg_spec[c] = (c, safe_first)
    if rows:
        df_agg = df.groupby(group_cols).agg(**agg_spec).reset_index()
    else:
        df_agg = pd.DataFrame()
    return df, df_agg


def print_operator_difference_summary_table(df_agg):
    from cmbench.reporting.summary_tables import print_operator_difference_summary_table as _print_operator_difference_summary_table

    return _print_operator_difference_summary_table(df_agg)


def run_equivalence_bench(
    sizes: List[int],
    trials: int,
    seed: int,
    max_depth: int,
    verbose: bool,
    config: Optional[BenchmarkConfig] = None,
    ctx: Optional[BenchmarkRunContext] = None,
):
    import pandas as pd

    config = config or (config_from_args(args) if args is not None else None)
    if config is None:
        raise ValueError("config is required when global args is not initialized")
    ctx = ctx or make_context(config, detect_backends())
    rng = np.random.default_rng(seed)
    expr_style = config.expr_style
    pair_style = config.equiv_pair_style
    backend_text = config.equiv_backends
    backends = {"robdd", "bitset", "cm", "sympy"} if backend_text == "all" else set(backend_text.split(","))
    full_tt_max_n = config.full_tt_max_n
    rows: List[Dict[str, Any]] = []

    for n in sizes:
        if verbose:
            print(f"\n=== equivalence n = {n} ===")
        for t in range(trials):
            build_tt_for_diag = n <= full_tt_max_n
            expr_f, base_diag, tt_f = generate_benchmark_expr(
                n,
                rng,
                max_depth=max_depth,
                style=expr_style,
                build_tt=build_tt_for_diag,
                config=config,
                return_tt_ref=True,
            )
            expr_g, expected = generate_equiv_pair(expr_f, n, rng, max_depth, expr_style, pair_style)
            row: Dict[str, Any] = {
                "n_vars": n,
                "trial": t,
                "expr_style": expr_style,
                **pair_diagnostics(expr_f, expr_g, n, pair_style, expected),
            }
            if build_tt_for_diag:
                tt_g = eval_expr_tt(expr_g, n).astype(np.uint8).reshape(-1)
                exact = bool(tt_f is not None and np.array_equal(tt_f, tt_g))
                row["tt_f_density"] = truth_table_diagnostics(tt_f)["tt_density"]
                row["tt_g_density"] = truth_table_diagnostics(tt_g)["tt_density"]
                row["equiv_reference_result"] = exact
                row["equiv_correctness_reference"] = "eval_expr_tt"
                row["equiv_tt_f_available"] = bool(tt_f is not None)
                row["equiv_tt_g_available"] = True
                row["equiv_tt_source"] = "eval_expr_tt"
                if expected is None:
                    expected = exact
                    row["equiv_expected"] = exact
            else:
                row["tt_f_density"] = None
                row["tt_g_density"] = None
                row["equiv_reference_result"] = None
                row["equiv_correctness_reference"] = "skipped_large_n"
                row["equiv_tt_f_available"] = False
                row["equiv_tt_g_available"] = False
                row["equiv_tt_source"] = "not_built"
            if verbose:
                print(f"  Trial {t + 1}/{trials}: expected={expected}")

            if "robdd" in backends and (not config.no_dd) and (not config.no_robdd_dd):
                row.update(
                    robdd_equivalence_check(
                        expr_f,
                        expr_g,
                        n,
                        backend=config.robdd_dd_backend,
                        order_policy=config.robdd_order_policy,
                        dynamic_reordering=config.robdd_dynamic_reordering,
                        reorder_method=config.robdd_reorder_method,
                        order_seed=(
                            int(config.robdd_order_seed)
                            if config.robdd_order_seed is not None
                            else int(seed + n * 1009 + t * 9176)
                        ),
                        order_sweeps=config.robdd_order_sweeps,
                        compare_repeat=config.equiv_compare_repeat,
                        expected=expected,
                    )
                )
            else:
                row.update(
                    _empty_robdd_equiv_result(
                        backend_preference=config.robdd_dd_backend,
                        order_policy=config.robdd_order_policy,
                        order_seed=config.robdd_order_seed,
                        order_sweeps=config.robdd_order_sweeps,
                        dynamic_reordering=config.robdd_dynamic_reordering,
                        reorder_method=config.robdd_reorder_method,
                        compare_repeat=config.equiv_compare_repeat,
                        status="skipped",
                        error=None,
                    )
                )

            if "bitset" in backends and (not config.no_bitset) and n <= full_tt_max_n:
                row.update(bitset_equivalence_check(expr_f, expr_g, n, expected=expected))
            else:
                row.update(skipped_equiv_result("bitset_equiv"))

            if "cm" in backends:
                row.update(cm_equivalence_check(expr_f, expr_g, n, expected=expected))
            else:
                row.update(skipped_equiv_result("cm_equiv"))

            if "sympy" in backends and (not config.no_sympy) and n <= full_tt_max_n:
                row.update(sympy_equivalence_check(expr_f, expr_g, n, expected=expected))
            else:
                row.update(skipped_equiv_result("sympy_equiv"))

            row["expr_depth_actual"] = base_diag.get("expr_depth_actual")
            row["expr_node_count"] = base_diag.get("expr_node_count")
            rows.append(row)

    df = pd.DataFrame(rows)

    def safe_median(s):
        try:
            return float(s.dropna().median())
        except Exception:
            return None

    def safe_all(s):
        try:
            x = s.dropna().tolist()
            return all(x) if x else None
        except Exception:
            return None

    def safe_first(s):
        try:
            x = s.dropna().tolist()
            return x[0] if x else None
        except Exception:
            return None

    agg = (
        df.groupby("n_vars")
        .agg(
            equiv_pair_style=("equiv_pair_style", safe_first),
            equiv_expected=("equiv_expected", safe_first),
            expr_f_depth_median=("expr_f_depth", safe_median),
            expr_g_depth_median=("expr_g_depth", safe_median),
            expr_f_node_count_median=("expr_f_node_count", safe_median),
            expr_g_node_count_median=("expr_g_node_count", safe_median),
            expr_f_unique_var_count_median=("expr_f_unique_var_count", safe_median),
            expr_g_unique_var_count_median=("expr_g_unique_var_count", safe_median),
            expr_pair_unique_var_count_median=("expr_pair_unique_var_count", safe_median),
            expr_pair_uses_all_vars_all=("expr_pair_uses_all_vars", safe_all),
            tt_f_density_median=("tt_f_density", safe_median),
            tt_g_density_median=("tt_g_density", safe_median),
            robdd_equiv_build_f_time_s_median=("robdd_equiv_build_f_time_s", safe_median),
            robdd_equiv_build_g_time_s_median=("robdd_equiv_build_g_time_s", safe_median),
            robdd_equiv_build_total_time_s_median=("robdd_equiv_build_total_time_s", safe_median),
            robdd_equiv_compare_per_call_time_s_median=("robdd_equiv_compare_per_call_time_s", safe_median),
            robdd_equiv_total_time_s_median=("robdd_equiv_total_time_s", safe_median),
            robdd_equiv_nodes_f_median=("robdd_equiv_nodes_f", safe_median),
            robdd_equiv_nodes_g_median=("robdd_equiv_nodes_g", safe_median),
            robdd_equiv_nodes_manager_median=("robdd_equiv_nodes_manager", safe_median),
            robdd_equiv_ok_all=("robdd_equiv_ok", safe_all),
            robdd_equiv_status=("robdd_equiv_status", safe_first),
            robdd_equiv_backend=("robdd_equiv_backend", safe_first),
            bitset_equiv_eval_total_time_s_median=("bitset_equiv_eval_total_time_s", safe_median),
            bitset_equiv_compare_time_s_median=("bitset_equiv_compare_time_s", safe_median),
            bitset_equiv_total_time_s_median=("bitset_equiv_total_time_s", safe_median),
            bitset_equiv_ok_all=("bitset_equiv_ok", safe_all),
            bitset_equiv_status=("bitset_equiv_status", safe_first),
            cm_equiv_compile_total_time_s_median=("cm_equiv_compile_total_time_s", safe_median),
            cm_equiv_eval_total_time_s_median=("cm_equiv_eval_total_time_s", safe_median),
            cm_equiv_compare_time_s_median=("cm_equiv_compare_time_s", safe_median),
            cm_equiv_total_time_s_median=("cm_equiv_total_time_s", safe_median),
            cm_equiv_ok_all=("cm_equiv_ok", safe_all),
            cm_equiv_status=("cm_equiv_status", safe_first),
            sympy_equiv_time_s_median=("sympy_equiv_time_s", safe_median),
            sympy_equiv_ok_all=("sympy_equiv_ok", safe_all),
            sympy_equiv_status=("sympy_equiv_status", safe_first),
            trials=("trial", "count"),
        )
        .reset_index()
    )
    agg["backend_robdd_equiv"] = "robdd" in backends
    agg["backend_bitset_equiv"] = "bitset" in backends
    agg["backend_cm_equiv"] = "cm" in backends
    agg["backend_sympy_equiv"] = "sympy" in backends
    agg["expr_style"] = expr_style
    agg["max_depth"] = max_depth
    return df, agg


def print_summary_table(agg):
    from cmbench.reporting.summary_tables import print_summary_table as _print_summary_table

    return _print_summary_table(agg)


def write_html_report(html_path: str, agg_all: "pd.DataFrame", depths: List[int], sizes: List[int], trials: int):
    import pandas as pd

    css = """
    <style>
    body { font-family: Segoe UI, Roboto, Arial, sans-serif; padding: 20px; color: #222; }
    h1 { margin: 0 0 8px 0; font-size: 22px; }
    h2 { margin: 16px 0 8px 0; font-size: 18px; }
    .sub { color: #666; margin-bottom: 16px; }
    table { border-collapse: collapse; width: 100%; margin: 16px 0; }
    th, td { border: 1px solid #ddd; padding: 8px 10px; text-align: right; }
    th { background: #f7f7f9; font-weight: 600; }
    td:first-child, th:first-child { text-align: left; }
    .ok { color: #0a7f16; font-weight: 600; }
    .no { color: #b00020; font-weight: 600; }
    .dash { color: #888; }
    </style>
    """

    def fmt_bool(x):
        if x is True:
            return '<span class="ok">OK</span>'
        if x is None:
            return '<span class="dash">--</span>'
        return '<span class="no">NO</span>'

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(f"<html><head><meta charset='utf-8'>{css}</head><body>")
        f.write("<h1>Boolean Backends Benchmark</h1>")
        f.write(f"<div class='sub'>sizes={sizes}, depths={depths}, trials={trials}</div>")
        for d in depths:
            section = agg_all[agg_all["max_depth"] == d].copy()
            for col in [
                "cm_ok_all",
                "cm_hybrid_ok_all",
                "cm_hybrid_no_reinflate_ok_all",
                "cm_partial_hybrid_ok_all",
                "cm_parallel_ok_all",
                "bitset_ok_all",
                "numba_ok_all",
                "sympy_ok_all",
                "robdd_ok_all",
                "bdd_sop_ok_all",
                "espresso_ok_all",
            ]:
                if col in section.columns:
                    section[col] = section[col].map(lambda v: fmt_bool(v))
            for col in [
                "pair_attempts_median",
                "pair_collapses_median",
                "pairable_ratio_median",
                "pair_nodes_total_median",
            ]:
                if col in section.columns and section[col].isna().all():
                    section = section.drop(columns=[col])
            preferred = [
                "n_vars",
                "cm_time_s_median",
                "cm_hybrid_no_reinflate_time_s_median",
                "cm_parallel_time_s_median",
                "bitset_time_s_median",
                "pair_attempts_median",
                "pair_collapses_median",
                "pairable_ratio_median",
                "pair_nodes_total_median",
                "cm_ok_all",
                "cm_hybrid_no_reinflate_ok_all",
                "cm_parallel_ok_all",
                "bitset_ok_all",
                "sympy_ok_all",
                "espresso_ok_all",
                "trials",
            ]
            ordered = [c for c in preferred if c in section.columns] + [c for c in section.columns if c not in preferred]
            section = section[ordered]
            f.write(f"<h2>max_depth = {d}</h2>")
            f.write(section.to_html(index=False, escape=False))
        f.write("</body></html>")
    print("Wrote HTML:", html_path)


def main():
    import pandas as pd

    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=str, default="4,8,16")
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument(
        "--expr-style",
        type=str,
        default="ordinary",
        choices=[
            "ordinary",
            "broad",
            "low-reuse",
            "anti-reduction",
            "balanced_all_vars",
            "xor_heavy",
            "and_or_not",
            "implication_heavy",
            "mixed_no_constants",
            "transform_pairs",
        ],
        help="Random expression generator style for robustness and stress runs.",
    )
    ap.add_argument("--depth-sweep", type=str, default="")
    ap.add_argument("--out-prefix", type=str, default="bench_random_ops")
    ap.add_argument("--print-summary", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--bench-equivalence", action="store_true")
    ap.add_argument("--bench-expression-family", action="store_true")
    ap.add_argument("--bench-partial-contexts", action="store_true")
    ap.add_argument("--bench-operator-difference", action="store_true")
    ap.add_argument("--bench-cm-transformations", action="store_true")
    ap.add_argument(
        "--operator-diff-mode",
        choices=[
            "truth_delta",
            "cm_quotient",
            "cm_symmetric_delta",
            "cm_dense_delta",
            "cm_structural_hash_delta",
            "cm_transform",
            "all",
        ],
        default="all",
    )
    ap.add_argument(
        "--operator-pair-style",
        choices=[
            "operator_table_2x2",
            "related_variant",
            "equivalent_rewrite",
            "near_miss",
            "shared_blocks",
            "independent",
            "containment_pair",
            "transform_pairs",
        ],
        default="related_variant",
    )
    ap.add_argument(
        "--cm-transform-kind",
        choices=[
            "complement",
            "transpose",
            "rotate90",
            "rotate180",
            "rotate270",
            "negate_left_operand",
            "negate_right_operand",
            "negate_both_operands",
            "all",
        ],
        default="all",
    )
    ap.add_argument("--operator-quotient-direction", choices=["a_minus_b", "b_minus_a", "both"], default="both")
    ap.add_argument("--operator-quotient-validate", action="store_true", default=True)
    ap.add_argument("--operator-quotient-report-matrix", action="store_true")
    ap.add_argument("--operator-quotient-max-dense-n", type=int, default=16)
    ap.add_argument(
        "--equiv-pair-style",
        choices=["identical", "rewritten_equiv", "semantic_equiv", "near_miss", "random_independent"],
        default="rewritten_equiv",
    )
    ap.add_argument("--equiv-compare-repeat", type=int, default=1000)
    ap.add_argument(
        "--equiv-backends",
        type=str,
        default="all",
        help="Comma-separated equivalence backends from robdd,bitset,cm,sympy, or all.",
    )
    ap.add_argument("--no-robdd", action="store_true")
    ap.add_argument("--no-espresso", action="store_true")
    ap.add_argument("--no-bdd-sop", action="store_true")
    ap.add_argument("--no-sympy", action="store_true")
    ap.add_argument("--no-dd", action="store_true")
    ap.add_argument("--robdd-dd-backend", choices=["auto", "cudd", "autoref"], default="auto")
    ap.add_argument("--no-robdd-dd", action="store_true")
    ap.add_argument("--robdd-order-policy", choices=["fixed", "expr", "random", "best-of-k"], default="fixed")
    ap.add_argument("--robdd-order-seed", type=int, default=None)
    ap.add_argument("--robdd-order-sweeps", type=int, default=1)
    ap.add_argument("--robdd-dynamic-reordering", action="store_true")
    ap.add_argument("--robdd-reorder-method", type=str, default="sift")
    ap.add_argument("--robdd-measure-tt-extract", dest="robdd_measure_tt_extract", action="store_true")
    ap.add_argument(
        "--robdd-tt-extract-method",
        choices=["all-assignments", "vectorized-if-available"],
        default="all-assignments",
    )
    ap.add_argument("--robdd-tt-extract-max-n", type=int, default=16)
    ap.add_argument(
        "--compare-robdd-cm",
        action="store_true",
        help="Convenience preset: include bitset, CM no-reinflate, persistent CM cache, and dd-backed ROBDD.",
    )
    ap.add_argument("--family-size", type=int, default=50)
    ap.add_argument(
        "--family-variant-style",
        choices=[
            "subtree_mutation",
            "subtree_wrap",
            "partial_substitution",
            "shared_block_mix",
            "composition_mix",
        ],
        default="composition_mix",
    )
    ap.add_argument("--family-shared-blocks", type=int, default=4)
    ap.add_argument("--family-mutation-rate", type=float, default=0.15)
    ap.add_argument("--family-seed", type=int, default=None)
    ap.add_argument("--family-force-shared-substructure", action="store_true")
    ap.add_argument("--family-report-hashes", action="store_true")
    ap.add_argument("--family-no-robdd", action="store_true")
    ap.add_argument("--family-robdd-shared-manager", action="store_true")
    ap.add_argument("--partial-contexts", type=int, default=100)
    ap.add_argument("--partial-fixed-var-count", type=int, default=None)
    ap.add_argument("--partial-fixed-var-fraction", type=float, default=0.5)
    ap.add_argument(
        "--partial-context-style",
        choices=["random_fixed", "block_fixed", "sliding_window", "manufacturing_modes"],
        default="random_fixed",
    )
    ap.add_argument("--partial-output-mode", choices=["remaining-vars", "full-vars"], default="remaining-vars")
    ap.add_argument("--partial-reuse-compiled-ir", action="store_true", default=True)
    ap.add_argument("--partial-report-live-vars", action="store_true")
    ap.add_argument("--partial-robdd-measure-extract", action="store_true")
    ap.add_argument("--require-nontrivial-expr", action="store_true")
    ap.add_argument("--min-used-var-fraction", type=float, default=0.75)
    ap.add_argument("--min-tt-density", type=float, default=0.05)
    ap.add_argument("--max-tt-density", type=float, default=0.95)
    ap.add_argument("--max-expr-regeneration-attempts", type=int, default=100)
    ap.add_argument("--no-bitset", action="store_true")
    ap.add_argument("--no-numba", action="store_true")
    ap.add_argument("--cm-lazy", action="store_true")
    ap.add_argument("--cm-pair", action="store_true", help="Use pair-aware token backend when applicable (experimental)")
    ap.add_argument("--cm-layout", type=str, default="balanced", choices=["balanced", "legacy_square"])
    ap.add_argument("--cm-hybrid-threshold", type=int, default=16)
    ap.add_argument("--cm-compare-hybrid", action="store_true")
    ap.add_argument("--cm-compare-no-reinflate", dest="cm_compare_no_reinflate", action="store_true")
    ap.add_argument("--cm-report-ir-breakdown", action="store_true")
    ap.add_argument("--cm-compile-once-per-expression", dest="cm_compile_once_per_expression", action="store_true")
    ap.add_argument("--cm-reuse-compiled-ir", dest="cm_reuse_compiled_ir", action="store_true")
    ap.add_argument("--cm-use-persistent-cache", dest="cm_use_persistent_cache", action="store_true")
    ap.add_argument("--cm-eval-repeat", dest="cm_eval_repeat", type=int, default=1)
    ap.add_argument("--cm-profile-cached-exec", dest="cm_profile_cached_exec", action="store_true")
    ap.add_argument("--cm-exec-target", choices=["local", "runpod"], default="local")
    ap.add_argument("--cm-runpod-smoke-test", action="store_true")
    ap.add_argument("--cm-runpod-start", action="store_true")
    ap.add_argument("--cm-runpod-stop", action="store_true")
    ap.add_argument("--cm-runpod-stop-after-run", action="store_true")
    ap.add_argument("--cm-runpod-fallback-local", action="store_true")
    ap.add_argument("--cm-runpod-local-mock", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--large-n-safe", dest="large_n_safe", action="store_true")
    ap.add_argument(
        "--sampled-correctness",
        dest="sampled_correctness",
        type=int,
        default=0,
        help="Sample K full assignments and compare original AST evaluation with no-reinflate output projection.",
    )
    ap.add_argument("--full-tt-max-n", dest="full_tt_max_n", type=int, default=16)
    ap.add_argument("--cm-max-full-output-vars", dest="cm_max_full_output_vars", type=int, default=16)
    ap.add_argument(
        "--cm-flat-eval",
        dest="cm_flat_eval",
        action="store_true",
        help="Use the C1a flat (linearized) evaluator for the no-reinflate bitset branch.",
    )
    ap.add_argument(
        "--cm-words-eval",
        dest="cm_words_eval",
        action="store_true",
        help="Use the numpy-uint64 words evaluator for CM and the matched raw-AST Bitset.",
    )
    ap.add_argument("--cm-parallel", action="store_true")
    ap.add_argument("--cm-parallel-workers", type=int, default=0)
    ap.add_argument("--cm-parallel-min-n", type=int, default=8)
    ap.add_argument("--cm-parallel-min-nodes", type=int, default=40)
    ap.add_argument("--cm-parallel-chunk-rows", type=int, default=1024, help="Legacy (no longer used for scheduling).")
    ap.add_argument("--cm-parallel-chunk-elems", type=int, default=(1 << 17))
    ap.add_argument("--cm-parallel-min-work-elems", dest="cm_parallel_min_work_elems", type=int, default=(1 << 18))
    ap.add_argument(
        "--cm-parallel-min-chunk-cells",
        dest="cm_parallel_min_work_elems",
        type=int,
        default=argparse.SUPPRESS,
        help="Legacy alias for --cm-parallel-min-work-elems.",
    )
    ap.add_argument("--cm-parallel-no-reuse-pool", action="store_true")
    ap.add_argument("--cm-parallel-no-shared-memory", action="store_true")
    ap.add_argument("--cm-parallel-shared-min-cells", type=int, default=(1 << 20))
    ap.add_argument("--cm-debug-stats", action="store_true")
    ap.add_argument("--experiment", type=str, default="none", choices=["none", "cm_vs_bitset"])
    ap.add_argument("--html", type=str, default="")

    global args, _ACTIVE_CONFIG
    args = ap.parse_args()
    config, _ctx = build_config_and_context(args)
    _ACTIVE_CONFIG = config
    if config.cm_flat_eval:
        from cm_ir import set_flat_eval_default

        set_flat_eval_default(True)
    if config.cm_words_eval:
        from cm_ir import set_words_eval_default

        set_words_eval_default(True)

    if config.cm_runpod_smoke_test:
        from cm_runpod_smoke_test import run_smoke_test

        raise SystemExit(run_smoke_test(local_mock=bool(config.cm_runpod_local_mock)))

    if config.cm_runpod_start or config.cm_runpod_stop:
        client = CMRunPodClient(load_runpod_config())
        if config.cm_runpod_start:
            status, _, wait_s = client.wait_for_pod_ready(start_if_stopped=True)
            print(
                "RunPod pod ready: "
                f"desired={status.desired_status or 'unknown'} runtime={status.runtime_status or 'unknown'} "
                f"wait_s={wait_s:.1f}"
            )
        if config.cm_runpod_stop:
            status = client.stop_pod()
            print(
                "RunPod pod stop requested: "
                f"desired={status.desired_status or 'unknown'} runtime={status.runtime_status or 'unknown'}"
        )
        return

    sizes = list(config.sizes)
    depths = parse_depth_sweep(config)
    bench_cm_transformations = bool(config.bench_cm_transformations)
    bench_operator_difference = bool(config.bench_operator_difference)
    bench_expression_family = bool(config.bench_expression_family)
    bench_partial_contexts = bool(config.bench_partial_contexts)
    bench_equivalence = bool(config.bench_equivalence)
    agg_all = []
    for d in depths:
        if bench_cm_transformations:
            df_raw, df_agg = run_cm_transformation_bench()
        elif bench_operator_difference:
            df_raw, df_agg = run_operator_difference_bench(sizes, config.trials, config.seed, d, config.verbose)
        elif bench_expression_family:
            df_raw, df_agg = run_expression_family_bench(
                sizes, config.trials, config.seed, d, config.verbose, config=config, ctx=_ctx
            )
        elif bench_partial_contexts:
            df_raw, df_agg = run_partial_context_bench(
                sizes, config.trials, config.seed, d, config.verbose, config=config, ctx=_ctx
            )
        elif bench_equivalence:
            df_raw, df_agg = run_equivalence_bench(
                sizes, config.trials, config.seed, d, config.verbose, config=config, ctx=_ctx
            )
        else:
            df_raw, df_agg = run_bench(sizes, config.trials, config.seed, d, config.verbose, config=config, ctx=_ctx)
        df_agg["max_depth"] = d
        agg_all.append(df_agg)
        raw_path = f"{config.out_prefix}_d{d}_raw.csv" if len(depths) > 1 else f"{config.out_prefix}_raw.csv"
        agg_path = (
            f"{config.out_prefix}_d{d}_summary.csv" if len(depths) > 1 else f"{config.out_prefix}_summary.csv"
        )
        df_raw.to_csv(raw_path, index=False)
        df_agg.to_csv(agg_path, index=False)
        print("Wrote", raw_path, "and", agg_path)
        if config.print_summary:
            if bench_cm_transformations:
                print(df_agg.to_string(index=False))
            elif bench_operator_difference:
                print_operator_difference_summary_table(df_agg)
            elif bench_expression_family:
                print_expression_family_summary_table(df_agg)
            elif bench_partial_contexts:
                print_partial_context_summary_table(df_agg)
            else:
                print_summary_table(df_agg)

    if config.html:
        agg_cat = pd.concat(agg_all, ignore_index=True) if len(agg_all) > 1 else agg_all[0]
        write_html_report(config.html, agg_cat, depths, sizes, config.trials)


if __name__ == "__main__":
    main()
