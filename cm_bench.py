#!/usr/bin/env python3
import argparse
import time
from typing import Any, Dict, List, Mapping, Optional

import numpy as np


def try_import(name: str):
    try:
        return __import__(name)
    except Exception:
        return None


dd = try_import("dd")
pyeda = try_import("pyeda")

from bitset_backend import build_bitset_env, eval_expr_bitset, bitset_to_bool_array
from cm_build import compile_expr_to_cm
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, eval_expr_tt, random_expr
from cm_normalize import canonical_layout, cm_normalize_cache_stats
from cm_parallel import compile_expr_to_cm_parallel, count_expr_nodes
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


args = None

_GRID_CACHE: Dict[int, np.ndarray] = {}


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


def time_backends_on_expr(
    n: int,
    expr,
    use_dd: bool,
    use_espresso: bool,
    verbose: bool,
    bit_env: Optional[Mapping[str, int]] = None,
) -> Dict[str, Any]:
    build_tt = n <= 16
    run_sympy = n <= 16
    run_espresso = use_espresso and (n <= 16)
    use_lazy_builder = HAS_LAZY and args.cm_lazy

    tt = None
    tt_ref = None
    t_cm = None
    cm_tt_extract_time = None
    cm_ok = None
    cm_hybrid_time = None
    cm_hybrid_tt_extract_time = None
    cm_hybrid_ok = None
    cm_partial_hybrid_time = None
    cm_partial_hybrid_tt_extract_time = None
    cm_partial_hybrid_ok = None
    cm_parallel_time = None
    cm_parallel_tt_extract_time = None
    cm_parallel_ok = None
    node_count = count_expr_nodes(expr)
    bitset_extract_time = None

    cm_diag: Dict[str, int] = {}
    cm_hybrid_diag: Dict[str, int] = {}
    cm_partial_hybrid_diag: Dict[str, int] = {}
    cm_parallel_diag: Dict[str, int] = {}
    norm_before = cm_normalize_cache_stats() if args.cm_debug_stats else None
    lazy_before = (
        lazy_align_cache_stats() if (args.cm_debug_stats and HAS_LAZY and callable(lazy_align_cache_stats)) else None
    )

    if build_tt:
        if verbose:
            print(f"[n={n}] CM compile ...")
        R, C = canonical_layout([f"x{i}" for i in range(n)], mode=args.cm_layout)

        def run_cm(materialize_mode: str, diag: Dict[str, int]) -> np.ndarray:
            if use_lazy_builder:
                return compile_expr_to_cm_lazy(
                    expr,
                    R,
                    C,
                    fixed={},
                    diagnostics=diag,
                    materialize_mode=materialize_mode,
                    hybrid_threshold=args.cm_hybrid_threshold,
                )
            return compile_expr_to_cm(
                expr,
                R,
                C,
                fixed={},
                diagnostics=diag,
                materialize_mode=materialize_mode,
                hybrid_threshold=args.cm_hybrid_threshold,
            )

        cm_mode = "numpy" if args.cm_compare_hybrid else "partial_hybrid"
        t0 = time.perf_counter()
        M_cm = run_cm(cm_mode, cm_diag)
        t_cm = time.perf_counter() - t0
        ttt0 = time.perf_counter()
        tt = cm_matrix_to_tt(M_cm, R, C, n)
        cm_tt_extract_time = time.perf_counter() - ttt0
        try:
            tt_ref = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)
            cm_ok = bool(np.array_equal(tt, tt_ref))
        except Exception:
            cm_ok = False

        if args.cm_compare_hybrid:
            if verbose:
                print(f"[n={n}] CM hybrid compile ...")
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

        if args.cm_parallel:
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
                    workers=args.cm_parallel_workers if args.cm_parallel_workers > 0 else None,
                    min_n=args.cm_parallel_min_n,
                    min_nodes=args.cm_parallel_min_nodes,
                    chunk_rows=args.cm_parallel_chunk_rows,
                    reuse_pool=not args.cm_parallel_no_reuse_pool,
                    use_shared_memory=not args.cm_parallel_no_shared_memory,
                    shared_min_cells=args.cm_parallel_shared_min_cells,
                    diagnostics=cm_parallel_diag,
                    materialize_mode="partial_hybrid",
                    hybrid_threshold=args.cm_hybrid_threshold,
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

    bdd_time = None
    bdd_nodes = None
    robdd_ok = None
    if build_tt and (not args.no_robdd):
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
    if use_dd and (not args.no_dd):
        try:
            if verbose:
                print(f"[n={n}] dd.autoref from AST ...")
            from dd import autoref as _dd

            mgr2 = _dd.BDD()
            names = [f"x{i}" for i in range(n)]
            mgr2.declare(*names)

            def rec(z):
                if isinstance(z, Var):
                    return mgr2.var(names[z.i])
                if isinstance(z, Not):
                    return ~rec(z.a)
                if isinstance(z, And):
                    return rec(z.a) & rec(z.b)
                if isinstance(z, Or):
                    return rec(z.a) | rec(z.b)
                if isinstance(z, Xor):
                    return rec(z.a) ^ rec(z.b)
                if isinstance(z, Imp):
                    return (~rec(z.a)) | rec(z.b)
                if isinstance(z, Eqv):
                    return ~(rec(z.a) ^ rec(z.b))
                raise TypeError(z)

            t2 = time.perf_counter()
            _ = rec(expr)
            dd_time = time.perf_counter() - t2
            dd_nodes = mgr2.size
        except Exception:
            dd_time = None
            dd_nodes = None

    sympy_time = None
    sympy_ok = None
    bdd_sop_time = None
    bdd_sop_ok = None
    espresso_time = None
    espresso_ok = None
    bitset_time = None
    bitset_ok = None
    numba_time = None
    numba_ok = None
    numba_compile_time = None

    if build_tt and (not args.no_bitset):
        try:
            if verbose:
                print(f"[n={n}] Bitset eval ...")
            local_bit_env = bit_env if bit_env is not None else build_bitset_env([f"x{i}" for i in range(n)])
            t7 = time.perf_counter()
            bitset_tt = eval_expr_bitset(expr, local_bit_env)
            bitset_time = time.perf_counter() - t7
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

    if build_tt and (not args.no_numba):
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

            if run_sympy and (not args.no_sympy):
                if verbose:
                    print(f"[n={n}] Sympy simplify_logic (DNF) ...")
                t4 = time.perf_counter()
                simp = simplify_via_sympy(expr, n, form="dnf")
                sympy_time = time.perf_counter() - t4
                xs = [sp.symbols(f"x{i}") for i in range(n)]
                f = sp.lambdify(xs, simp, "numpy")
                A = get_eval_grid(n)
                tt_sympy = np.array(f(*[A[:, i] for i in range(n)])).astype(np.uint8).reshape(-1)
                sympy_ok = bool(np.array_equal(tt, tt_sympy))
        except Exception:
            sympy_time = None
            sympy_ok = False

        try:
            if run_espresso and (not args.no_espresso) and (pyeda is not None):
                if verbose:
                    print(f"[n={n}] Espresso (pyeda) simplify ...")
                from pyeda.inter import espresso_exprs, truthtable, ttvars
                import sympy as sp

                t6 = time.perf_counter()
                xs = ttvars("x", n)
                ones_idx = np.flatnonzero(tt)
                T = truthtable(xs, ones_idx.tolist())
                (f_simplified,) = espresso_exprs(T.to_expr())
                espresso_time = time.perf_counter() - t6
                esp_expr = sp.sympify(str(f_simplified), evaluate=False)
                f3 = sp.lambdify([sp.symbols(f"x{i}") for i in range(n)], esp_expr, "numpy")
                A = get_eval_grid(n)
                tt_esp = np.array(f3(*[A[:, i] for i in range(n)])).astype(np.uint8).reshape(-1)
                espresso_ok = bool(np.array_equal(tt, tt_esp))
        except Exception:
            espresso_time = None
            espresso_ok = False

        try:
            if (not args.no_bdd_sop) and (n <= 8):
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
                bdd_sop_ok = bool(np.array_equal(tt, tt_sop))
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
    )
    for field in diag_fields:
        debug_row[f"cm_{field}"] = int(cm_diag.get(field, 0))
        debug_row[f"cm_hybrid_{field}"] = int(cm_hybrid_diag.get(field, 0))
        debug_row[f"cm_partial_hybrid_{field}"] = int(cm_partial_hybrid_diag.get(field, 0))
        debug_row[f"cm_parallel_{field}"] = int(cm_parallel_diag.get(field, 0))
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
    if args.cm_debug_stats:
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
            debug_row[f"cm_diag_{k}"] = int(v)
        for k, v in cm_hybrid_diag.items():
            debug_row[f"cm_hybrid_diag_{k}"] = int(v)
        for k, v in cm_partial_hybrid_diag.items():
            debug_row[f"cm_partial_hybrid_diag_{k}"] = int(v)
        for k, v in cm_parallel_diag.items():
            debug_row[f"cm_parallel_diag_{k}"] = int(v)

    return {
        "cm_time_s": t_cm,
        "cm_tt_extract_time_s": cm_tt_extract_time,
        "cm_ok": cm_ok,
        "cm_nodes": node_count,
        "cm_hybrid_time_s": cm_hybrid_time,
        "cm_hybrid_tt_extract_time_s": cm_hybrid_tt_extract_time,
        "cm_hybrid_ok": cm_hybrid_ok,
        "cm_partial_hybrid_time_s": cm_partial_hybrid_time,
        "cm_partial_hybrid_tt_extract_time_s": cm_partial_hybrid_tt_extract_time,
        "cm_partial_hybrid_ok": cm_partial_hybrid_ok,
        "cm_parallel_time_s": cm_parallel_time,
        "cm_parallel_tt_extract_time_s": cm_parallel_tt_extract_time,
        "cm_parallel_ok": cm_parallel_ok,
        "bitset_time_s": bitset_time,
        "bitset_extract_time_s": bitset_extract_time,
        "bitset_ok": bitset_ok,
        "cm_time_excludes_tt_extract": True,
        "cm_hybrid_time_excludes_tt_extract": True,
        "cm_partial_hybrid_time_excludes_tt_extract": True,
        "cm_parallel_time_excludes_tt_extract": True,
        "bitset_time_excludes_tt_extract": True,
        "numba_compile_time_s": numba_compile_time,
        "numba_time_s": numba_time,
        "numba_ok": numba_ok,
        "bdd_time_s": bdd_time,
        "bdd_nodes": bdd_nodes,
        "dd_time_s": dd_time,
        "dd_nodes": dd_nodes,
        "sympy_time_s": sympy_time,
        "sympy_ok": sympy_ok,
        "bdd_sop_time_s": bdd_sop_time,
        "bdd_sop_ok": bdd_sop_ok,
        "espresso_time_s": espresso_time,
        "espresso_ok": espresso_ok,
        "robdd_ok": robdd_ok,
        "cm_layout": args.cm_layout,
        "cm_compare_hybrid": bool(args.cm_compare_hybrid),
        "cm_hybrid_threshold": int(args.cm_hybrid_threshold),
        **debug_row,
    }


def run_bench(sizes: List[int], trials: int, seed: int, max_depth: int, verbose: bool):
    import pandas as pd

    rng = np.random.default_rng(seed)
    use_dd = dd is not None and hasattr(dd, "autoref")
    use_espresso = pyeda is not None
    rows = []

    # Ensure bitset env is prepared once per variable set and reused per trial.
    bit_env_by_n: Dict[int, Mapping[str, int]] = {}
    if not args.no_bitset:
        for n in sizes:
            if n <= 16:
                bit_env_by_n[n] = build_bitset_env([f"x{i}" for i in range(n)])

    for n in sizes:
        if verbose:
            print(f"\n=== n = {n} ===")
            if n > 16:
                print("[info] n>16: skipping Sympy/Espresso/TT")
        exprs = [random_expr(n, rng, max_depth=max_depth, p_unary=0.25) for _ in range(trials)]
        for t, expr in enumerate(exprs):
            if verbose:
                print(f"  Trial {t + 1}/{trials}")
            res = time_backends_on_expr(
                n,
                expr,
                use_dd=use_dd,
                use_espresso=use_espresso,
                verbose=verbose,
                bit_env=bit_env_by_n.get(n),
            )
            res["n_vars"] = n
            res["trial"] = t
            rows.append(res)

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

    agg = (
        df.groupby("n_vars")
        .agg(
            cm_time_s_median=("cm_time_s", safe_median),
            cm_tt_extract_time_s_median=("cm_tt_extract_time_s", safe_median),
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
            sympy_time_s_median=("sympy_time_s", safe_median),
            bdd_nodes_median=("bdd_nodes", safe_median),
            dd_nodes_median=("dd_nodes", safe_median),
            cm_nodes_median=("cm_nodes", safe_median),
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
            espresso_time_s_median=("espresso_time_s", safe_median),
            cm_ok_all=("cm_ok", safe_all),
            cm_hybrid_ok_all=("cm_hybrid_ok", safe_all),
            cm_partial_hybrid_ok_all=("cm_partial_hybrid_ok", safe_all),
            cm_parallel_ok_all=("cm_parallel_ok", safe_all),
            bitset_ok_all=("bitset_ok", safe_all),
            numba_ok_all=("numba_ok", safe_all),
            sympy_ok_all=("sympy_ok", safe_all),
            robdd_ok_all=("robdd_ok", safe_all),
            sympy_ok_count=("sympy_ok", count_true),
            bdd_sop_time_s_median=("bdd_sop_time_s", safe_median),
            bdd_sop_ok_all=("bdd_sop_ok", safe_all),
            espresso_ok_all=("espresso_ok", safe_all),
            trials=("trial", "count"),
        )
        .reset_index()
    )

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

    agg["backend_robdd"] = not args.no_robdd
    agg["backend_dd"] = use_dd and (not args.no_dd)
    agg["backend_espresso"] = use_espresso and (not args.no_espresso)
    agg["backend_bitset"] = not args.no_bitset
    agg["backend_numba"] = (not args.no_numba) and HAS_NUMBA
    agg["backend_cm_parallel"] = bool(args.cm_parallel)
    agg["backend_cm_compare_hybrid"] = bool(args.cm_compare_hybrid)
    agg["cm_hybrid_threshold"] = int(args.cm_hybrid_threshold)
    agg["cm_default_materialize_mode"] = "numpy" if args.cm_compare_hybrid else "partial_hybrid"
    agg["cm_layout"] = args.cm_layout
    return df, agg


def print_summary_table(agg):
    print("\n=== Summary (per n_vars) ===")
    if "cm_layout" in agg.columns and not agg.empty:
        print(f"CM layout mode: {agg.iloc[0]['cm_layout']}")
    has_hybrid_compare = "cm_hybrid_time_s_median" in agg.columns and agg["cm_hybrid_time_s_median"].notna().any()
    has_partial_compare = (
        "cm_partial_hybrid_time_s_median" in agg.columns and agg["cm_partial_hybrid_time_s_median"].notna().any()
    )
    has_parallel = "cm_parallel_time_s_median" in agg.columns and agg["cm_parallel_time_s_median"].notna().any()
    print(
        "Timing policy: `cm_time_s`, `cm_hybrid_time_s`, `cm_partial_hybrid_time_s`, `cm_parallel_time_s`, "
        "and `bitset_time_s` are backend compute-only (TT extraction/conversion is excluded and reported separately)."
    )
    if has_hybrid_compare or has_partial_compare:
        print(
            "Columns: n | CM_med_s | CM_hybrid_med_s | CM_partial_hybrid_med_s | CM_parallel_med_s | Bitset_med_s | "
            "CM_hybrid/CM | CM_hybrid/Bitset | CM_partial_hybrid/CM | CM_partial_hybrid/Bitset | "
            "CM_parallel/CM | CM_parallel/Bitset | "
            "Numba_compile_med_s | Numba_med_s | ROBDD_med_s | dd_med_s | "
            "Sympy_simpl_med_s | BDD_SOP_med_s | Espresso_med_s | ROBDD_nodes_med | "
            "dd_nodes_med | CM_nodes_med | CM_OK | CM_hybrid_OK | CM_partial_hybrid_OK | CM_parallel_OK | Bitset_OK | "
            "Numba_OK | Sympy_OK | Sympy_OK_count/trials | ROBDD_OK | BDD_SOP_OK | Espresso_OK | trials"
        )
    else:
        print(
            "Columns: n | CM_med_s | CM_parallel_med_s | Bitset_med_s | "
            "CM_parallel/CM | CM_parallel/Bitset | "
            "Numba_compile_med_s | Numba_med_s | ROBDD_med_s | dd_med_s | "
            "Sympy_simpl_med_s | BDD_SOP_med_s | Espresso_med_s | ROBDD_nodes_med | "
            "dd_nodes_med | CM_nodes_med | CM_OK | CM_parallel_OK | Bitset_OK | "
            "Numba_OK | Sympy_OK | Sympy_OK_count/trials | ROBDD_OK | BDD_SOP_OK | Espresso_OK | trials"
        )
    for _, row in agg.sort_values("n_vars").iterrows():
        fnum = (
            lambda x: f"{x:>10.6f}"
            if isinstance(x, float) and not (x != x)
            else f"{'nan':>10}"
        )
        fint = lambda x: 0 if (x is None or (isinstance(x, float) and (x != x))) else int(x)
        fbool = lambda x: "OK" if x is True else ("--" if x is None else "NO")
        trials = int(row["trials"] or 0)
        okc = int(row.get("sympy_ok_count") or 0)
        if has_hybrid_compare or has_partial_compare:
            print(
                f"{int(row['n_vars']):>2} | {fnum(row['cm_time_s_median'])} | {fnum(row['cm_hybrid_time_s_median'])} | "
                f"{fnum(row['cm_partial_hybrid_time_s_median'])} | {fnum(row['cm_parallel_time_s_median'])} | "
                f"{fnum(row['bitset_time_s_median'])} | "
                f"{fnum(row['ratio_cm_hybrid_over_cm'])} | {fnum(row['ratio_cm_hybrid_over_bitset'])} | "
                f"{fnum(row['ratio_cm_partial_hybrid_over_cm'])} | {fnum(row['ratio_cm_partial_hybrid_over_bitset'])} | "
                f"{fnum(row['ratio_cm_parallel_over_cm'])} | {fnum(row['ratio_cm_parallel_over_bitset'])} | "
                f"{fnum(row['numba_compile_time_s_median'])} | {fnum(row['numba_time_s_median'])} | "
                f"{fnum(row['bdd_time_s_median'])} | {fnum(row['dd_time_s_median'])} | {fnum(row['sympy_time_s_median'])} | "
                f"{fnum(row['bdd_sop_time_s_median'])} | {fnum(row['espresso_time_s_median'])} | "
                f"{fint(row['bdd_nodes_median']):>15} | {fint(row['dd_nodes_median']):>12} | {fint(row['cm_nodes_median']):>12} | "
                f"{fbool(row.get('cm_ok_all')):>5} | {fbool(row.get('cm_hybrid_ok_all')):>12} | "
                f"{fbool(row.get('cm_partial_hybrid_ok_all')):>20} | {fbool(row.get('cm_parallel_ok_all')):>14} | "
                f"{fbool(row.get('bitset_ok_all')):>9} | "
                f"{fbool(row.get('numba_ok_all')):>8} | {fbool(row['sympy_ok_all']):>7} | {okc}/{trials:>5} | "
                f"{fbool(row.get('robdd_ok_all')):>9} | {fbool(row['bdd_sop_ok_all']):>11} | "
                f"{fbool(row['espresso_ok_all']):>11} | {trials:>6}"
            )
        else:
            print(
                f"{int(row['n_vars']):>2} | {fnum(row['cm_time_s_median'])} | {fnum(row['cm_parallel_time_s_median'])} | "
                f"{fnum(row['bitset_time_s_median'])} | {fnum(row['ratio_cm_parallel_over_cm'])} | "
                f"{fnum(row['ratio_cm_parallel_over_bitset'])} | {fnum(row['numba_compile_time_s_median'])} | "
                f"{fnum(row['numba_time_s_median'])} | {fnum(row['bdd_time_s_median'])} | {fnum(row['dd_time_s_median'])} | "
                f"{fnum(row['sympy_time_s_median'])} | {fnum(row['bdd_sop_time_s_median'])} | {fnum(row['espresso_time_s_median'])} | "
                f"{fint(row['bdd_nodes_median']):>15} | {fint(row['dd_nodes_median']):>12} | {fint(row['cm_nodes_median']):>12} | "
                f"{fbool(row.get('cm_ok_all')):>5} | {fbool(row.get('cm_parallel_ok_all')):>14} | "
                f"{fbool(row.get('bitset_ok_all')):>9} | {fbool(row.get('numba_ok_all')):>8} | {fbool(row['sympy_ok_all']):>7} | "
                f"{okc}/{trials:>5} | {fbool(row.get('robdd_ok_all')):>9} | {fbool(row['bdd_sop_ok_all']):>11} | "
                f"{fbool(row['espresso_ok_all']):>11} | {trials:>6}"
            )


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
    ap.add_argument("--depth-sweep", type=str, default="")
    ap.add_argument("--out-prefix", type=str, default="bench_random_ops")
    ap.add_argument("--print-summary", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--no-robdd", action="store_true")
    ap.add_argument("--no-espresso", action="store_true")
    ap.add_argument("--no-bdd-sop", action="store_true")
    ap.add_argument("--no-sympy", action="store_true")
    ap.add_argument("--no-dd", action="store_true")
    ap.add_argument("--no-bitset", action="store_true")
    ap.add_argument("--no-numba", action="store_true")
    ap.add_argument("--cm-lazy", action="store_true")
    ap.add_argument("--cm-layout", type=str, default="balanced", choices=["balanced", "legacy_square"])
    ap.add_argument("--cm-hybrid-threshold", type=int, default=7)
    ap.add_argument("--cm-compare-hybrid", action="store_true")
    ap.add_argument("--cm-parallel", action="store_true")
    ap.add_argument("--cm-parallel-workers", type=int, default=0)
    ap.add_argument("--cm-parallel-min-n", type=int, default=8)
    ap.add_argument("--cm-parallel-min-nodes", type=int, default=40)
    ap.add_argument("--cm-parallel-chunk-rows", type=int, default=1024)
    ap.add_argument("--cm-parallel-no-reuse-pool", action="store_true")
    ap.add_argument("--cm-parallel-no-shared-memory", action="store_true")
    ap.add_argument("--cm-parallel-shared-min-cells", type=int, default=(1 << 20))
    ap.add_argument("--cm-debug-stats", action="store_true")
    ap.add_argument("--experiment", type=str, default="none", choices=["none", "cm_vs_bitset"])
    ap.add_argument("--html", type=str, default="")

    global args
    args = ap.parse_args()

    if args.experiment == "cm_vs_bitset":
        # Force apples-to-apples experiment collection.
        args.cm_parallel = True
        args.no_bitset = False
    if args.cm_compare_hybrid:
        args.no_bitset = False

    sizes = [int(s) for s in args.sizes.split(",") if s]
    depths = [int(d) for d in args.depth_sweep.split(",") if d] if args.depth_sweep else [args.max_depth]
    agg_all = []
    for d in depths:
        df_raw, df_agg = run_bench(sizes, args.trials, args.seed, d, args.verbose)
        df_agg["max_depth"] = d
        agg_all.append(df_agg)
        raw_path = f"{args.out_prefix}_d{d}_raw.csv" if len(depths) > 1 else f"{args.out_prefix}_raw.csv"
        agg_path = (
            f"{args.out_prefix}_d{d}_summary.csv" if len(depths) > 1 else f"{args.out_prefix}_summary.csv"
        )
        df_raw.to_csv(raw_path, index=False)
        df_agg.to_csv(agg_path, index=False)
        print("Wrote", raw_path, "and", agg_path)
        if args.print_summary:
            print_summary_table(df_agg)

    if args.html:
        agg_cat = pd.concat(agg_all, ignore_index=True) if len(agg_all) > 1 else agg_all[0]
        write_html_report(args.html, agg_cat, depths, sizes, args.trials)


if __name__ == "__main__":
    main()
