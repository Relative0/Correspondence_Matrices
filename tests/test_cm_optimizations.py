import unittest

import numpy as np

from cm_build import compile_expr_to_cm
from cm_exprlib import And, Eqv, Imp, Or, Var, Xor, eval_expr_tt, random_expr
from cm_ir import compile_expr_to_cm_ir, materialize_cm
from cm_normalize import canonical_layout
from cm_parallel import compile_expr_to_cm_parallel

try:
    from cm_build_lazy import (
        clear_lazy_align_cache,
        compile_expr_to_cm_lazy,
        lazy_align_cache_stats,
    )

    HAS_LAZY = True
except Exception:
    HAS_LAZY = False
    compile_expr_to_cm_lazy = None  # type: ignore[assignment]
    clear_lazy_align_cache = None  # type: ignore[assignment]
    lazy_align_cache_stats = None  # type: ignore[assignment]


def _cm_matrix_to_tt(M_cm: np.ndarray, R, C, n_vars: int) -> np.ndarray:
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


class CMOptimizationTests(unittest.TestCase):
    def test_balanced_and_legacy_square_layouts_are_correct(self) -> None:
        rng = np.random.default_rng(77)
        for n in (5, 12):
            expr = random_expr(n, rng, max_depth=5, p_unary=0.25)
            tt_ref = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)
            for mode in ("balanced", "legacy_square"):
                R, C = canonical_layout([f"x{i}" for i in range(n)], mode=mode)
                mat = compile_expr_to_cm(expr, R, C, fixed={})
                tt = _cm_matrix_to_tt(mat, R, C, n)
                self.assertTrue(np.array_equal(tt_ref, tt), msg=f"layout mode failed: {mode} at n={n}")

    def test_memoization_reuse_eager_and_lazy(self) -> None:
        n = 8
        R, C = canonical_layout([f"x{i}" for i in range(n)])
        sub = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))
        expr = Eqv(sub, sub)

        eager_diag = {}
        M_eager = compile_expr_to_cm(expr, R, C, fixed={}, diagnostics=eager_diag)
        self.assertGreater(eager_diag.get("subtree_cache_hits", 0), 0)

        tt_ref = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)
        tt_eager = _cm_matrix_to_tt(M_eager, R, C, n)
        self.assertTrue(np.array_equal(tt_ref, tt_eager))

        if HAS_LAZY:
            lazy_diag = {}
            M_lazy = compile_expr_to_cm_lazy(expr, R, C, fixed={}, diagnostics=lazy_diag)
            self.assertGreater(lazy_diag.get("subtree_cache_hits", 0), 0)
            tt_lazy = _cm_matrix_to_tt(M_lazy, R, C, n)
            self.assertTrue(np.array_equal(tt_ref, tt_lazy))

    def test_canonical_cse_reuses_reordered_operands(self) -> None:
        n = 6
        R, C = canonical_layout([f"x{i}" for i in range(n)])
        left = And(Var(0), Var(1))
        right = And(Var(1), Var(0))
        expr = Or(left, right)

        diag = {}
        M = compile_expr_to_cm(expr, R, C, fixed={}, diagnostics=diag)
        tt_ref = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)
        tt = _cm_matrix_to_tt(M, R, C, n)
        self.assertTrue(np.array_equal(tt_ref, tt))
        self.assertGreater(diag.get("canonical_rewrites", 0), 0)
        self.assertGreater(diag.get("subtree_cache_hits", 0), 0)

    def test_pruning_short_circuit_is_correct(self) -> None:
        n = 8
        R, C = canonical_layout([f"x{i}" for i in range(n)])
        heavy = Or(And(Var(1), Var(2)), Eqv(Var(3), Imp(Var(4), Var(5))))
        expr = And(Xor(Var(0), Var(0)), heavy)
        tt_ref = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)

        eager_diag = {}
        M_eager = compile_expr_to_cm(expr, R, C, fixed={}, diagnostics=eager_diag)
        self.assertGreater(eager_diag.get("pruned_branches", 0), 0)
        tt_eager = _cm_matrix_to_tt(M_eager, R, C, n)
        self.assertTrue(np.array_equal(tt_ref, tt_eager))

        if HAS_LAZY:
            lazy_diag = {}
            M_lazy = compile_expr_to_cm_lazy(expr, R, C, fixed={}, diagnostics=lazy_diag)
            self.assertGreater(lazy_diag.get("pruned_branches", 0), 0)
            tt_lazy = _cm_matrix_to_tt(M_lazy, R, C, n)
            self.assertTrue(np.array_equal(tt_ref, tt_lazy))

        par_diag = {}
        M_par = compile_expr_to_cm_parallel(
            expr,
            R,
            C,
            fixed={},
            use_lazy=False,
            workers=2,
            min_n=1,
            min_nodes=1,
            chunk_rows=32,
            use_shared_memory=False,
            diagnostics=par_diag,
        )
        self.assertEqual(par_diag.get("parallel_activated"), 1)
        self.assertGreater(par_diag.get("pruned_branches", 0), 0)
        tt_par = _cm_matrix_to_tt(M_par, R, C, n)
        self.assertTrue(np.array_equal(tt_ref, tt_par))

    def test_compile_ir_does_not_materialize(self) -> None:
        diag_compile = {}
        node = compile_expr_to_cm_ir(Or(And(Var(0), Var(1)), Xor(Var(2), Var(3))), diagnostics=diag_compile)
        self.assertNotIn("materializations", diag_compile)
        self.assertEqual(node.kind, "binary")

        diag_materialize = {}
        R, C = canonical_layout([f"x{i}" for i in range(4)])
        M = materialize_cm(node, R, C, fixed={}, diagnostics=diag_materialize)
        self.assertEqual(M.shape, (1 << len(R), 1 << len(C)))
        self.assertGreater(diag_materialize.get("materializations", 0), 0)

    def test_fixed_variables_reduce_live_dimensions_before_materialization(self) -> None:
        expr = And(Or(Var(0), Var(1)), Eqv(Var(2), Var(3)))
        node = compile_expr_to_cm_ir(expr)
        R, C = canonical_layout([f"x{i}" for i in range(4)])

        diag = {}
        _ = materialize_cm(node, R, C, fixed={"x0": 1, "x3": 0}, diagnostics=diag)
        self.assertLess(diag.get("live_vars_max", 99), len(node.vars))

    def test_default_cm_materialization_mode_is_partial_hybrid(self) -> None:
        expr = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))
        R, C = canonical_layout([f"x{i}" for i in range(4)])
        diag = {}
        _ = compile_expr_to_cm(expr, R, C, fixed={}, diagnostics=diag)
        self.assertGreaterEqual(diag.get("bitset_materializations", 0), 2)
        self.assertGreaterEqual(diag.get("numpy_materializations", 0), 1)
        self.assertEqual(diag.get("full_collapse_occurred", 0), 0)

    def test_hybrid_dispatch_uses_bitset_for_small_live_var_subproblems(self) -> None:
        expr = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))
        node = compile_expr_to_cm_ir(expr)
        R, C = canonical_layout([f"x{i}" for i in range(4)])

        hybrid_diag = {}
        numpy_diag = {}
        mat_hybrid = materialize_cm(
            node,
            R,
            C,
            fixed={},
            diagnostics=hybrid_diag,
            materialize_mode="hybrid",
            hybrid_threshold=4,
        )
        mat_numpy = materialize_cm(
            node,
            R,
            C,
            fixed={},
            diagnostics=numpy_diag,
            materialize_mode="numpy",
        )

        self.assertTrue(np.array_equal(mat_hybrid, mat_numpy))
        self.assertGreater(hybrid_diag.get("bitset_materializations", 0), 0)
        self.assertEqual(hybrid_diag.get("numpy_materializations", 0), 0)
        self.assertEqual(hybrid_diag.get("full_collapse_occurred", 0), 1)
        self.assertEqual(hybrid_diag.get("hybrid_depth_max", -1), 0)

    def test_partial_hybrid_preserves_root_combination_and_mixes_backends(self) -> None:
        expr = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))
        node = compile_expr_to_cm_ir(expr)
        R, C = canonical_layout([f"x{i}" for i in range(4)])

        partial_diag = {}
        numpy_diag = {}
        mat_partial = materialize_cm(
            node,
            R,
            C,
            fixed={},
            diagnostics=partial_diag,
            materialize_mode="partial_hybrid",
            hybrid_threshold=2,
        )
        mat_numpy = materialize_cm(
            node,
            R,
            C,
            fixed={},
            diagnostics=numpy_diag,
            materialize_mode="numpy",
        )

        self.assertTrue(np.array_equal(mat_partial, mat_numpy))
        self.assertGreaterEqual(partial_diag.get("bitset_materializations", 0), 2)
        self.assertGreaterEqual(partial_diag.get("numpy_materializations", 0), 1)
        self.assertEqual(partial_diag.get("full_collapse_occurred", 0), 0)
        self.assertGreaterEqual(partial_diag.get("hybrid_depth_max", 0), 1)

    def test_hybrid_dispatch_can_be_forced_to_numpy_only(self) -> None:
        expr = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))
        node = compile_expr_to_cm_ir(expr)
        R, C = canonical_layout([f"x{i}" for i in range(4)])

        diag = {}
        _ = materialize_cm(
            node,
            R,
            C,
            fixed={},
            diagnostics=diag,
            materialize_mode="hybrid",
            hybrid_threshold=0,
        )
        self.assertGreater(diag.get("numpy_materializations", 0), 0)
        self.assertEqual(diag.get("bitset_materializations", 0), 0)

    def test_fixed_variables_can_drop_subproblem_under_hybrid_threshold(self) -> None:
        expr = And(Or(Var(0), Var(1)), Eqv(Var(2), Var(3)))
        node = compile_expr_to_cm_ir(expr)
        R, C = canonical_layout([f"x{i}" for i in range(4)])
        fixed = {"x0": 1, "x3": 0}

        hybrid_diag = {}
        numpy_diag = {}
        mat_hybrid = materialize_cm(
            node,
            R,
            C,
            fixed=fixed,
            diagnostics=hybrid_diag,
            materialize_mode="hybrid",
            hybrid_threshold=2,
        )
        mat_numpy = materialize_cm(
            node,
            R,
            C,
            fixed=fixed,
            diagnostics=numpy_diag,
            materialize_mode="numpy",
        )

        self.assertTrue(np.array_equal(mat_hybrid, mat_numpy))
        self.assertGreater(hybrid_diag.get("bitset_materializations", 0), 0)
        self.assertEqual(hybrid_diag.get("numpy_materializations", 0), 0)

    def test_partial_hybrid_respects_fixed_vars_without_full_collapse(self) -> None:
        expr = And(Or(Var(0), Var(1)), Eqv(Var(2), Var(3)))
        node = compile_expr_to_cm_ir(expr)
        R, C = canonical_layout([f"x{i}" for i in range(4)])
        fixed = {"x0": 1, "x3": 0}

        partial_diag = {}
        numpy_diag = {}
        mat_partial = materialize_cm(
            node,
            R,
            C,
            fixed=fixed,
            diagnostics=partial_diag,
            materialize_mode="partial_hybrid",
            hybrid_threshold=1,
        )
        mat_numpy = materialize_cm(
            node,
            R,
            C,
            fixed=fixed,
            diagnostics=numpy_diag,
            materialize_mode="numpy",
        )

        self.assertTrue(np.array_equal(mat_partial, mat_numpy))
        self.assertGreaterEqual(partial_diag.get("bitset_materializations", 0), 2)
        self.assertGreaterEqual(partial_diag.get("numpy_materializations", 0), 1)
        self.assertEqual(partial_diag.get("full_collapse_occurred", 0), 0)

    def test_cache_reuse_stats_are_observable(self) -> None:
        n = 8
        R, C = canonical_layout([f"x{i}" for i in range(n)])
        expr = And(Var(0), Var(4))

        if HAS_LAZY and callable(clear_lazy_align_cache):
            clear_lazy_align_cache()

        if HAS_LAZY and callable(lazy_align_cache_stats):
            compile_expr_to_cm(expr, R, C, fixed={})
            compile_expr_to_cm_lazy(expr, R, C, fixed={})
            lazy_first = lazy_align_cache_stats()
            compile_expr_to_cm(expr, R, C, fixed={})
            compile_expr_to_cm_lazy(expr, R, C, fixed={})
            lazy_second = lazy_align_cache_stats()
            self.assertGreater(lazy_second["align_plan_hits"], lazy_first["align_plan_hits"])

    def test_parallel_diagnostics_and_determinism(self) -> None:
        rng = np.random.default_rng(101)
        n = 8
        expr = random_expr(n, rng, max_depth=6, p_unary=0.25)
        R, C = canonical_layout([f"x{i}" for i in range(n)])

        d1 = {}
        m1 = compile_expr_to_cm_parallel(
            expr,
            R,
            C,
            fixed={},
            use_lazy=False,
            workers=2,
            min_n=1,
            min_nodes=1,
            chunk_rows=32,
            use_shared_memory=False,
            diagnostics=d1,
        )
        d2 = {}
        m2 = compile_expr_to_cm_parallel(
            expr,
            R,
            C,
            fixed={},
            use_lazy=False,
            workers=2,
            min_n=1,
            min_nodes=1,
            chunk_rows=32,
            use_shared_memory=False,
            diagnostics=d2,
        )

        self.assertTrue(np.array_equal(m1.reshape(-1).view(np.uint8), m2.reshape(-1).view(np.uint8)))
        self.assertEqual(d1.get("parallel_activated"), 1)
        self.assertGreaterEqual(d1.get("materializations", 0), 1)

        tt_ref = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)
        tt_par = _cm_matrix_to_tt(m1, R, C, n)
        self.assertTrue(np.array_equal(tt_ref, tt_par))


if __name__ == "__main__":
    unittest.main()
