from __future__ import annotations

import atexit
import math
import os
import threading
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import shared_memory
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir, materialize_cm
from cm_normalize import combine_pointwise


_BIN_NODES = (And, Or, Xor, Imp, Eqv)
_POOL_LOCK = threading.Lock()
_POOL_CACHE: Dict[int, ProcessPoolExecutor] = {}


def _bump(diag: Optional[Dict[str, Any]], key: str, inc: int = 1) -> None:
    if diag is None:
        return
    cur = diag.get(key, 0)
    if isinstance(cur, (int, np.integer)):
        base = int(cur)
    else:
        base = 0
    diag[key] = base + int(inc)


def _get_process_pool(max_workers: int, reuse_pool: bool) -> Tuple[ProcessPoolExecutor, bool, bool]:
    if not reuse_pool:
        return ProcessPoolExecutor(max_workers=max_workers), True, True
    with _POOL_LOCK:
        pool = _POOL_CACHE.get(max_workers)
        if pool is None:
            pool = ProcessPoolExecutor(max_workers=max_workers)
            _POOL_CACHE[max_workers] = pool
            return pool, False, True
        return pool, False, False


def shutdown_parallel_pools() -> None:
    with _POOL_LOCK:
        pools = list(_POOL_CACHE.values())
        _POOL_CACHE.clear()
    for pool in pools:
        try:
            pool.shutdown(wait=True, cancel_futures=True)
        except TypeError:
            pool.shutdown(wait=True)


def parallel_pool_stats() -> Dict[str, int]:
    with _POOL_LOCK:
        return {
            "cached_pools": int(len(_POOL_CACHE)),
            "cached_worker_slots": int(sum(_POOL_CACHE.keys())),
        }


atexit.register(shutdown_parallel_pools)


def count_expr_nodes(expr: Expr) -> int:
    if isinstance(expr, Var):
        return 1
    if isinstance(expr, Not):
        return 1 + count_expr_nodes(expr.a)
    if isinstance(expr, _BIN_NODES):
        return 1 + count_expr_nodes(expr.a) + count_expr_nodes(expr.b)
    raise TypeError(expr)


def _combine_chunk_worker(op: str, left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return combine_pointwise(left, right, op)


def _apply_op_inplace(out: np.ndarray, left: np.ndarray, right: np.ndarray, op: str) -> None:
    if op == "AND":
        np.bitwise_and(left, right, out=out)
    elif op == "OR":
        np.bitwise_or(left, right, out=out)
    elif op == "XOR":
        np.bitwise_xor(left, right, out=out)
    elif op == "IMP":
        np.bitwise_not(left, out=out)
        np.bitwise_or(out, right, out=out)
    elif op == "EQV":
        np.bitwise_xor(left, right, out=out)
        np.bitwise_not(out, out=out)
    elif op == "NAND":
        np.bitwise_and(left, right, out=out)
        np.bitwise_not(out, out=out)
    elif op == "NOR":
        np.bitwise_or(left, right, out=out)
        np.bitwise_not(out, out=out)
    else:
        raise ValueError(op)


def _combine_chunk_worker_flat(op: str, left: np.ndarray, right: np.ndarray) -> np.ndarray:
    out = np.empty_like(left, dtype=bool)
    _apply_op_inplace(out, left.astype(bool, copy=False), right.astype(bool, copy=False), op)
    return out


def _combine_chunk_worker_shared(
    op: str,
    left_name: str,
    right_name: str,
    out_name: str,
    dtype_str: str,
    n_elems: int,
    start_elem: int,
    end_elem: int,
) -> int:
    dtype = np.dtype(dtype_str)
    left_shm = shared_memory.SharedMemory(name=left_name)
    right_shm = shared_memory.SharedMemory(name=right_name)
    out_shm = shared_memory.SharedMemory(name=out_name)
    try:
        left = np.ndarray((n_elems,), dtype=dtype, buffer=left_shm.buf)
        right = np.ndarray((n_elems,), dtype=dtype, buffer=right_shm.buf)
        out = np.ndarray((n_elems,), dtype=dtype, buffer=out_shm.buf)
        _apply_op_inplace(out[start_elem:end_elem], left[start_elem:end_elem], right[start_elem:end_elem], op)
        return end_elem - start_elem
    finally:
        left_shm.close()
        right_shm.close()
        out_shm.close()


def _combine_parallel_shared(
    left: np.ndarray,
    right: np.ndarray,
    op: str,
    executor: ProcessPoolExecutor,
    *,
    chunk_ranges: List[Tuple[int, int]],
    out_shape: Tuple[int, ...],
    diagnostics: Optional[Dict[str, Any]],
) -> np.ndarray:
    out_shape = tuple(int(s) for s in out_shape)
    dtype = np.dtype(bool)
    n_elems = int(left.size)
    if right.size != n_elems:
        raise ValueError("shared parallel combine requires equal-sized arrays")
    nbytes = int(n_elems * dtype.itemsize)
    left_shm = shared_memory.SharedMemory(create=True, size=nbytes)
    right_shm = shared_memory.SharedMemory(create=True, size=nbytes)
    out_shm = shared_memory.SharedMemory(create=True, size=nbytes)
    try:
        left_flat = np.ndarray((n_elems,), dtype=dtype, buffer=left_shm.buf)
        right_flat = np.ndarray((n_elems,), dtype=dtype, buffer=right_shm.buf)
        out_flat = np.ndarray((n_elems,), dtype=dtype, buffer=out_shm.buf)
        np.copyto(left_flat.reshape(out_shape), left.astype(bool, copy=False))
        np.copyto(right_flat.reshape(out_shape), right.astype(bool, copy=False))
        futures = []
        for start, end in chunk_ranges:
            futures.append(
                executor.submit(
                    _combine_chunk_worker_shared,
                    op,
                    left_shm.name,
                    right_shm.name,
                    out_shm.name,
                    dtype.str,
                    n_elems,
                    start,
                    end,
                )
            )
        _bump(diagnostics, "worker_tasks_spawned", len(futures))
        _bump(diagnostics, "combine_chunk_tasks", len(futures))
        for fut in futures:
            fut.result()
        return out_flat.reshape(out_shape).copy()
    finally:
        left_shm.close()
        right_shm.close()
        out_shm.close()
        left_shm.unlink()
        right_shm.unlink()
        out_shm.unlink()


def compile_expr_to_cm_parallel(
    expr: Expr,
    R: list[str],
    C: list[str],
    fixed: Optional[Dict[str, int]] = None,
    *,
    use_lazy: bool = False,
    workers: Optional[int] = None,
    min_n: int = 8,
    min_nodes: int = 40,
    chunk_rows: int = 1024,  # legacy compatibility knob (no longer used for scheduling)
    chunk_elems: int = 1 << 17,
    min_chunk_cells: int = 1 << 18,  # legacy alias for `min_parallel_work_elems`
    min_parallel_work_elems: Optional[int] = None,
    reuse_pool: bool = True,
    use_shared_memory: bool = True,
    shared_min_cells: int = 1 << 20,  # legacy (ignored; shared memory is all-or-nothing)
    diagnostics: Optional[Dict[str, Any]] = None,
    materialize_mode: str = "partial_hybrid",
    hybrid_threshold: int = 7,
) -> np.ndarray:
    fixed_map = fixed or {}
    node_count = count_expr_nodes(expr)
    max_workers = workers if (workers is not None and workers > 0) else (os.cpu_count() or 1)
    executor: Optional[ProcessPoolExecutor] = None
    should_shutdown = False

    if diagnostics is not None:
        diagnostics["parallel_workers"] = int(max_workers)
        diagnostics["chunk_rows_used"] = int(chunk_rows)
        diagnostics["chunk_elems_used"] = int(chunk_elems)
        diagnostics["min_chunk_cells"] = int(min_chunk_cells)
        diagnostics["shared_min_cells"] = int(shared_min_cells)
        diagnostics["min_parallel_work_elems"] = int(
            min_chunk_cells if min_parallel_work_elems is None else min_parallel_work_elems
        )
        diagnostics["shared_ir_pipeline"] = 1
        diagnostics["use_lazy_requested"] = int(bool(use_lazy))
        diagnostics.setdefault("parallel_pool_starts", 0)
        diagnostics.setdefault("parallel_combine_activations", 0)
        diagnostics.setdefault("parallel_work_elements", 0)
        diagnostics.setdefault("number_of_chunks", 0)
        diagnostics.setdefault("chunk_size_min", 0)
        diagnostics.setdefault("chunk_size_max", 0)
        diagnostics.setdefault("chunk_size_avg", 0.0)
        diagnostics.setdefault("parallel_speedup_estimate", 0.0)

    node = compile_expr_to_cm_ir(expr, diagnostics=diagnostics)
    if max_workers < 2 or (len(R) + len(C)) < min_n or node_count < min_nodes:
        if diagnostics is not None:
            diagnostics["parallel_activated"] = 0
            diagnostics["parallel_threshold_fallback"] = 1
            diagnostics["fallback_reason"] = "serial_requested" if max_workers < 2 else "expr_threshold"
        return materialize_cm(
            node,
            R,
            C,
            fixed_map,
            diagnostics=diagnostics,
            materialize_mode=materialize_mode,
            hybrid_threshold=hybrid_threshold,
        )

    try:
        if diagnostics is not None:
            diagnostics["parallel_activated"] = 1

        def combine_fn(left: np.ndarray, right: np.ndarray, op: str, diag: Optional[Dict[str, Any]]) -> np.ndarray:
            nonlocal executor, should_shutdown
            if left.shape != right.shape:
                left, right = np.broadcast_arrays(left, right)

            # Element-based eligibility and flat chunk scheduling (not axis-0 rows).
            total_elements = int(left.size)
            min_work = int(min_chunk_cells if min_parallel_work_elems is None else min_parallel_work_elems)
            if max_workers < 2:
                if diag is not None:
                    diag["fallback_reason"] = "serial_requested"
                _bump(diag, "combine_serial_fallback")
                return combine_pointwise(left, right, op)
            if total_elements < min_work:
                if diag is not None:
                    diag["fallback_reason"] = "small_total_work"
                _bump(diag, "combine_serial_fallback")
                return combine_pointwise(left, right, op)
            if chunk_elems <= 0:
                if diag is not None:
                    diag["fallback_reason"] = "serial_requested"
                _bump(diag, "combine_serial_fallback")
                return combine_pointwise(left, right, op)

            block_elems = int(chunk_elems)
            max_chunks_by_size = int(math.ceil(total_elements / block_elems))
            number_of_chunks = int(min(max_workers, max_chunks_by_size))
            if number_of_chunks < 2:
                if diag is not None:
                    diag["fallback_reason"] = "single_chunk"
                _bump(diag, "combine_serial_fallback")
                return combine_pointwise(left, right, op)
            if number_of_chunks < max_chunks_by_size:
                block_elems = int(math.ceil(total_elements / number_of_chunks))

            chunk_ranges: List[Tuple[int, int]] = []
            chunk_sizes: List[int] = []
            for start in range(0, total_elements, block_elems):
                end = min(total_elements, start + block_elems)
                chunk_ranges.append((int(start), int(end)))
                chunk_sizes.append(int(end - start))

            if len(chunk_ranges) < 2:
                if diag is not None:
                    diag["fallback_reason"] = "single_chunk"
                _bump(diag, "combine_serial_fallback")
                return combine_pointwise(left, right, op)

            # If shared memory is disabled, avoid starting the pool unless we are
            # confident this won't be dominated by IPC copies.
            if not use_shared_memory:
                non_shared_min = 1 << 22
                if total_elements < non_shared_min:
                    if diag is not None:
                        diag["fallback_reason"] = "copy_overhead"
                    _bump(diag, "combine_serial_fallback")
                    return combine_pointwise(left, right, op)

            if diag is not None:
                diag["parallel_work_elements"] = int(total_elements)
                diag["number_of_chunks"] = int(len(chunk_ranges))
                diag["chunk_size_min"] = int(min(chunk_sizes))
                diag["chunk_size_max"] = int(max(chunk_sizes))
                diag["chunk_size_avg"] = float(total_elements / len(chunk_ranges))
                diag["chunk_sizes"] = ",".join(str(s) for s in chunk_sizes)
                diag["parallel_speedup_estimate"] = float(
                    min(max_workers, float(total_elements) / float(diag["chunk_size_max"]))
                )
                diag["fallback_reason"] = ""

            # Confirm parallelism before creating the pool.
            _bump(diag, "parallel_combine_activations")
            if executor is None:
                executor, should_shutdown, created = _get_process_pool(max_workers=max_workers, reuse_pool=reuse_pool)
                if created:
                    _bump(diag, "parallel_pool_starts")

            out_shape = tuple(int(s) for s in left.shape)
            if use_shared_memory:
                _bump(diag, "shared_memory_combine_activations")
                return _combine_parallel_shared(
                    left,
                    right,
                    op,
                    executor,
                    chunk_ranges=chunk_ranges,
                    out_shape=out_shape,
                    diagnostics=diag,
                )

            # Non-shared-memory fallback: only enable for very large chunks; otherwise, the
            # extra IPC copies tend to dominate bool ufunc work.
            if diag is not None:
                diag["fallback_reason"] = "shared_memory_disabled"
            left_flat = np.empty(total_elements, dtype=bool)
            right_flat = np.empty(total_elements, dtype=bool)
            np.copyto(left_flat.reshape(out_shape), left.astype(bool, copy=False))
            np.copyto(right_flat.reshape(out_shape), right.astype(bool, copy=False))

            futures = []
            for start, end in chunk_ranges:
                futures.append(
                    executor.submit(_combine_chunk_worker_flat, op, left_flat[start:end], right_flat[start:end])
                )
            _bump(diag, "worker_tasks_spawned", len(futures))
            _bump(diag, "combine_chunk_tasks", len(futures))
            out_flat = np.empty(total_elements, dtype=bool)
            offset = 0
            for fut in futures:
                chunk = fut.result()
                out_flat[offset : offset + int(chunk.size)] = chunk
                offset += int(chunk.size)
            return out_flat.reshape(out_shape)

        return materialize_cm(
            node,
            R,
            C,
            fixed_map,
            diagnostics=diagnostics,
            combine_fn=combine_fn,
            materialize_mode=materialize_mode,
            hybrid_threshold=hybrid_threshold,
        )
    finally:
        if executor is not None and should_shutdown:
            try:
                executor.shutdown(wait=True, cancel_futures=True)
            except TypeError:
                executor.shutdown(wait=True)
