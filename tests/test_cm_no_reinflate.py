import unittest

import numpy as np

from bitset_backend import bitset_to_bool_array
from cm_exprlib import And, Or, Var, Xor, eval_expr_tt, random_expr
from cm_ir import compile_expr_to_cm_ir, materialize_cm, materialize_hybrid_no_reinflate
from cm_normalize import canonical_layout


class CMNoReinflateTests(unittest.TestCase):
    def test_no_reinflate_returns_packed_bitset_and_matches_eval_expr_tt(self) -> None:
        n = 4
        expr = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))
        node = compile_expr_to_cm_ir(expr)
        diag = {}
        res = materialize_hybrid_no_reinflate(
            node,
            [f"x{i}" for i in range(n)],
            fixed={},
            diagnostics=diag,
            hybrid_threshold=7,
        )
        self.assertEqual(res.final_output_representation_code, 2)
        self.assertIsNotNone(res.bits)
        self.assertIsNone(res.tt)
        self.assertEqual(int(diag.get("final_cm_materialization_performed", -1)), 0)
        self.assertEqual(int(diag.get("final_bitset_returned", -1)), 1)
        self.assertEqual(int(diag.get("final_output_representation_code", -1)), 2)

        tt_ref = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)
        tt_bits = bitset_to_bool_array(int(res.bits), n)
        self.assertTrue(np.array_equal(tt_ref, tt_bits))

    def test_large_n_guard_requires_reduced_output_opt_in(self) -> None:
        n = 20
        expr = Or(Var(0), Var(19))
        node = compile_expr_to_cm_ir(expr)

        with self.assertRaises(ValueError):
            materialize_hybrid_no_reinflate(
                node,
                [f"x{i}" for i in range(n)],
                fixed={},
                hybrid_threshold=7,
                max_full_output_vars=16,
            )

        diag = {}
        res = materialize_hybrid_no_reinflate(
            node,
            [f"x{i}" for i in range(n)],
            fixed={},
            diagnostics=diag,
            hybrid_threshold=7,
            allow_reduced_output=True,
            max_full_output_vars=16,
        )
        self.assertEqual(res.final_output_representation_code, 3)
        self.assertEqual(res.output_vars, ("x0", "x19"))
        self.assertIsNotNone(res.bits)
        self.assertEqual(int(diag.get("final_output_reduced", -1)), 1)
        self.assertEqual(int(diag.get("large_n_output_guard_triggered", -1)), 1)
        self.assertEqual(int(diag.get("final_output_vars_count", -1)), 2)
        self.assertEqual(int(diag.get("final_output_elements", -1)), 4)

    def test_large_n_guard_rejects_too_many_reduced_live_vars(self) -> None:
        n = 20
        expr = Var(0)
        for i in range(1, 17):
            expr = Xor(expr, Var(i))
        node = compile_expr_to_cm_ir(expr)

        with self.assertRaises(ValueError):
            materialize_hybrid_no_reinflate(
                node,
                [f"x{i}" for i in range(n)],
                fixed={},
                hybrid_threshold=7,
                allow_reduced_output=True,
                max_full_output_vars=16,
            )

    def test_no_reinflate_fallback_returns_tt_vector_and_avoids_cm_matrix(self) -> None:
        rng = np.random.default_rng(2026)
        n = 8
        expr = random_expr(n, rng, max_depth=5, p_unary=0.25)
        node = compile_expr_to_cm_ir(expr)
        diag = {}
        res = materialize_hybrid_no_reinflate(
            node,
            [f"x{i}" for i in range(n)],
            fixed={},
            diagnostics=diag,
            hybrid_threshold=4,
        )
        self.assertEqual(res.final_output_representation_code, 1)
        self.assertIsNone(res.bits)
        self.assertIsNotNone(res.tt)
        self.assertEqual(int(diag.get("final_cm_materialization_performed", -1)), 0)
        self.assertEqual(int(diag.get("final_bitset_returned", -1)), 0)
        self.assertEqual(int(diag.get("final_output_representation_code", -1)), 1)

        tt_ref = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)
        self.assertTrue(np.array_equal(tt_ref, res.tt))

    def test_existing_materialize_cm_still_performs_dense_cm_output_contract(self) -> None:
        n = 4
        expr = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))
        node = compile_expr_to_cm_ir(expr)
        R, C = canonical_layout([f"x{i}" for i in range(n)])
        diag = {}
        mat = materialize_cm(
            node,
            R,
            C,
            fixed={},
            diagnostics=diag,
            materialize_mode="hybrid",
            hybrid_threshold=7,
        )
        self.assertEqual(mat.ndim, 2)
        self.assertEqual(int(diag.get("final_cm_materialization_performed", -1)), 1)
        self.assertEqual(int(diag.get("final_output_representation_code", -1)), 0)
        self.assertGreaterEqual(float(diag.get("final_cm_materialization_time_s", 0.0)), 0.0)


if __name__ == "__main__":
    unittest.main()
