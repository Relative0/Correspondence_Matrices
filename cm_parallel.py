from __future__ import annotations

import atexit
import os
import threading
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import shared_memory
from typing import Dict, Optional, Tuple

import numpy as np

from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir, materialize_cm
from cm_normalize import combine_pointwise


_BIN_NODES = (And, Or, Xor, Imp, Eqv)
_POOL_LOCK = threading.Lock()
_POOL_CACHE: Dict[int, ProcessPoolExecutor] = {}


def _bump(diag: Optional[Dict[str, int]], key: str, inc: int = 1) -> None:
    if diag is None:
        return
    diag[key] = int(diag.get(key, 0)) + inc


def _get_process_pool(max_workers: int, reuse_pool: bool) -> Tuple[ProcessPoolExecutor, bool]:
    if not reuse_pool:
        return ProcessPoolExecutor(max_workers=max_workers), True
    with _POOL_LOCK:
        pool = _POOL_CACHE.get(max_workers)
        if pool is None:
            pool = ProcessPoolExecutor(max_workers=max_workers)
            _POOL_CACHE[max_workers] = pool
        return pool, False


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


def _combine_chunk_worker_shared(
    op: str,
    left_name: str,
    right_name: str,
    out_name: str,
    shape: Tuple[int, ...],
    dtype_str: str,
    start_row: int,
    end_row: int,
) -> int:
    dtype = np.dtype(dtype_str)
    left_shm = shared_memory.SharedMemory(name=left_name)
    right_shm = shared_memory.SharedMemory(name=right_name)
    out_shm = shared_memory.SharedMemory(name=out_name)
    try:
        left = np.ndarray(shape, dtype=dtype, buffer=left_shm.buf)
        right = np.ndarray(shape, dtype=dtype, buffer=right_shm.buf)
        out = np.ndarray(shape, dtype=dtype, buffer=out_shm.buf)
        out[start_row:end_row, ...] = combine_pointwise(left[start_row:end_row, ...], right[start_row:end_row, ...], op)
        return end_row - start_row
    finally:
        left_shm.close()
        right_shm.close()
        out_shm.close()


def _combine_parallel_shared(
    left: np.ndarray,
    right: np.ndarray,
    op: str,
    executor: ProcessPoolExecutor,
    chunk_rows: int,
    diagnostics: Optional[Dict[str, int]],
) -> np.ndarray:
    shape = tuple(int(s) for s in left.shape)
    dtype = left.dtype
    left_shm = shared_memory.SharedMemory(create=True, size=left.nbytes)
    right_shm = shared_memory.SharedMemory(create=True, size=right.nbytes)
    out_shm = shared_memory.SharedMemory(create=True, size=left.nbytes)
    try:
        left_view = np.ndarray(shape, dtype=dtype, buffer=left_shm.buf)
        right_view = np.ndarray(shape, dtype=dtype, buffer=right_shm.buf)
        out_view = np.ndarray(shape, dtype=dtype, buffer=out_shm.buf)
        left_view[...] = left
        right_view[...] = right
        futures = []
        for start in range(0, shape[0], chunk_rows):
            end = min(shape[0], start + chunk_rows)
            futures.append(
                executor.submit(
                    _combine_chunk_worker_shared,
                    op,
                    left_shm.name,
                    right_shm.name,
                    out_shm.name,
                    shape,
                    dtype.str,
                    start,
                    end,
                )
            )
        _bump(diagnostics, "worker_tasks_spawned", len(futures))
        _bump(diagnostics, "combine_chunk_tasks", len(futures))
        for fut in futures:
            fut.result()
        return out_view.copy()
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
    chunk_rows: int = 1024,
    min_chunk_cells: int = 1 << 18,
    reuse_pool: bool = True,
    use_shared_memory: bool = True,
    shared_min_cells: int = 1 << 20,
    diagnostics: Optional[Dict[str, int]] = None,
    materialize_mode: str = "partial_hybrid",
    hybrid_threshold: int = 7,
) -> np.ndarray:
    fixed_map = fixed or {}
    node_count = count_expr_nodes(expr)
    max_workers = workers if (workers is not None and workers > 0) else (os.cpu_count() or 1)

    if diagnostics is not None:
        diagnostics["parallel_workers"] = int(max_workers)
        diagnostics["chunk_rows_used"] = int(chunk_rows)
        diagnostics["min_chunk_cells"] = int(min_chunk_cells)
        diagnostics["shared_min_cells"] = int(shared_min_cells)
        diagnostics["shared_ir_pipeline"] = 1
        diagnostics["use_lazy_requested"] = int(bool(use_lazy))

    node = compile_expr_to_cm_ir(expr, diagnostics=diagnostics)
    if max_workers < 2 or (len(R) + len(C)) < min_n or node_count < min_nodes:
        if diagnostics is not None:
            diagnostics["parallel_activated"] = 0
            diagnostics["parallel_threshold_fallback"] = 1
        return materialize_cm(
            node,
            R,
            C,
            fixed_map,
            diagnostics=diagnostics,
            materialize_mode=materialize_mode,
            hybrid_threshold=hybrid_threshold,
        )

    executor, should_shutdown = _get_process_pool(max_workers=max_workers, reuse_pool=reuse_pool)
    try:
        if diagnostics is not None:
            diagnostics["parallel_activated"] = 1

        def combine_fn(left: np.ndarray, right: np.ndarray, op: str, diag: Optional[Dict[str, int]]) -> np.ndarray:
            if left.shape != right.shape:
                left, right = np.broadcast_arrays(left, right)
            if chunk_rows <= 0:
                _bump(diag, "combine_serial_fallback")
                return combine_pointwise(left, right, op)
            total_cells = int(left.size)
            if left.shape[0] <= chunk_rows or total_cells < min_chunk_cells:
                _bump(diag, "combine_serial_fallback")
                return combine_pointwise(left, right, op)
            _bump(diag, "combine_parallel_activations")
            if use_shared_memory and total_cells >= shared_min_cells:
                _bump(diag, "shared_memory_combine_activations")
                return _combine_parallel_shared(
                    left,
                    right,
                    op,
                    executor,
                    chunk_rows=chunk_rows,
                    diagnostics=diag,
                )
            futures = []
            for start in range(0, left.shape[0], chunk_rows):
                end = min(left.shape[0], start + chunk_rows)
                futures.append(executor.submit(_combine_chunk_worker, op, left[start:end, ...], right[start:end, ...]))
            _bump(diag, "worker_tasks_spawned", len(futures))
            _bump(diag, "combine_chunk_tasks", len(futures))
            chunks = [fut.result() for fut in futures]
            return np.concatenate(chunks, axis=0)

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
        if should_shutdown:
            try:
                executor.shutdown(wait=True, cancel_futures=True)
            except TypeError:
                executor.shutdown(wait=True)
