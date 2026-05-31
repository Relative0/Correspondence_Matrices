import unittest

import numpy as np

from cm_exprlib import And, Or, Var, Xor, eval_expr_tt, random_expr
from cm_ir import clear_cm_ir_compile_cache, compile_expr_to_cm_ir
from cm_normalize import canonical_layout
from cm_ir import materialize_hybrid_no_reinflate


class CMIRCostDiagnosticsTests(unittest.TestCase):
    def test_ir_compile_timing_fields_exist_when_enabled(self) -> None:
        diag = {"ir_timing_enabled": 1}
        expr = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))
        _ = compile_expr_to_cm_ir(expr, diagnostics=diag)
        self.assertIn("ir_compile_time_s", diag)
        self.assertIsInstance(diag.get("ir_compile_time_s"), float)
        # A few stage keys should exist (may be zero, but must be numeric if present).
        for k in ("ir_intern_time_s", "ir_canonicalize_time_s", "ir_rewrite_time_s", "ir_live_vars_time_s"):
            if k in diag:
                self.assertIsInstance(diag[k], float)

    def test_compiled_ir_cache_hit_counters(self) -> None:
        clear_cm_ir_compile_cache()
        expr = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))

        diag1 = {"ir_timing_enabled": 1}
        _ = compile_expr_to_cm_ir(expr, diagnostics=diag1, reuse_cache=True)
        self.assertEqual(int(diag1.get("ir_compile_cache_hit", -1)), 0)
        self.assertGreaterEqual(int(diag1.get("ir_compile_cache_misses", 0)), 1)

        diag2 = {"ir_timing_enabled": 1}
        _ = compile_expr_to_cm_ir(expr, diagnostics=diag2, reuse_cache=True)
        self.assertEqual(int(diag2.get("ir_compile_cache_hit", -1)), 1)
        self.assertGreaterEqual(int(diag2.get("ir_compile_cache_hits", 0)), 1)

    def test_cached_ir_path_preserves_correctness_for_no_reinflate(self) -> None:
        rng = np.random.default_rng(2026)
        n = 8
        expr = random_expr(n, rng, max_depth=5, p_unary=0.25)
        clear_cm_ir_compile_cache()

        diag = {"ir_timing_enabled": 1}
        node = compile_expr_to_cm_ir(expr, diagnostics=diag, reuse_cache=True)
        res = materialize_hybrid_no_reinflate(
            node,
            [f"x{i}" for i in range(n)],
            fixed={},
            diagnostics={"ir_timing_enabled": 1},
            hybrid_threshold=7,
        )
        if res.bits is not None:
            # bitset_backend already tests ordering; here just validate end-to-end correctness.
            from bitset_backend import bitset_to_bool_array

            tt = bitset_to_bool_array(int(res.bits), n)
        else:
            tt = res.tt
        tt_ref = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)
        self.assertTrue(tt is not None and np.array_equal(tt, tt_ref))


if __name__ == "__main__":
    unittest.main()

