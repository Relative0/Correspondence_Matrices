import unittest

import numpy as np

from bitset_backend import (
    bitset_to_bool_hypercube,
    bitset_env_cache_stats,
    bitset_to_bool_array,
    build_bitset_env,
    clear_bitset_env_cache,
    eval_cm_node_bitset,
    eval_expr_bitset,
)
from cm_exprlib import Eqv, Imp, Not, Or, Var, Xor, eval_expr_tt, random_expr
from cm_ir import compile_expr_to_cm_ir


class BitsetBackendTests(unittest.TestCase):
    def test_truth_table_ordering_matches_eval_expr_tt_random(self) -> None:
        rng = np.random.default_rng(1234)
        for n in range(1, 17):
            env = build_bitset_env([f"x{i}" for i in range(n)])
            for _ in range(8):
                expr = random_expr(n, rng, max_depth=5, p_unary=0.25)
                tt_ref = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)
                tt_bits = eval_expr_bitset(expr, env)
                tt_bitset = bitset_to_bool_array(tt_bits, n)
                self.assertTrue(
                    np.array_equal(tt_ref, tt_bitset),
                    msg=f"bitset ordering mismatch at n={n}",
                )

    def test_full_mask_clipping_for_not_imp_eqv(self) -> None:
        n = 16
        env = build_bitset_env([f"x{i}" for i in range(n)])
        n_rows = 1 << n
        overflow_mask = ~((1 << n_rows) - 1)

        exprs = [
            Not(Var(0)),
            Imp(Var(0), Not(Var(1))),
            Eqv(Var(0), Imp(Var(1), Var(2))),
        ]
        for expr in exprs:
            bits = eval_expr_bitset(expr, env)
            self.assertEqual(bits & overflow_mask, 0, msg=f"overflow bits set for {type(expr).__name__}")

    def test_bitset_env_cache_hits(self) -> None:
        clear_bitset_env_cache()
        before = bitset_env_cache_stats()
        self.assertEqual(before["hits"], 0)
        self.assertEqual(before["misses"], 0)

        vars_key = tuple(f"x{i}" for i in range(8))
        env1 = build_bitset_env(vars_key)
        mid = bitset_env_cache_stats()
        self.assertEqual(mid["misses"], 1)
        self.assertEqual(mid["hits"], 0)

        env2 = build_bitset_env(vars_key)
        after = bitset_env_cache_stats()
        self.assertEqual(after["misses"], 1)
        self.assertEqual(after["hits"], 1)
        self.assertEqual(dict(env1), dict(env2))

    def test_cm_node_bitset_eval_matches_truth_table_shape_and_values(self) -> None:
        expr = Or(Xor(Var(0), Var(1)), Not(Var(2)))
        node = compile_expr_to_cm_ir(expr)
        bits = eval_cm_node_bitset(node, ("x0", "x1", "x2"))
        tt_ref = eval_expr_tt(expr, 3).astype(np.uint8).reshape(-1)
        tt_bits = bitset_to_bool_array(bits, 3)
        cube = bitset_to_bool_hypercube(bits, 3)

        self.assertTrue(np.array_equal(tt_ref, tt_bits))
        self.assertEqual(cube.shape, (2, 2, 2))
        self.assertTrue(np.array_equal(tt_ref, cube.reshape(-1).astype(np.uint8)))

    def test_cm_node_bitset_respects_fixed_variables(self) -> None:
        expr = Eqv(Var(0), Imp(Var(1), Var(2)))
        node = compile_expr_to_cm_ir(expr)
        bits = eval_cm_node_bitset(node, ("x1",), fixed={"x0": 1, "x2": 0})
        cube = bitset_to_bool_hypercube(bits, 1)
        expected = np.array([1, 0], dtype=np.uint8)
        self.assertTrue(np.array_equal(expected, cube.reshape(-1).astype(np.uint8)))


if __name__ == "__main__":
    unittest.main()
