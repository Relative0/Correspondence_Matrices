import unittest

import numpy as np

from bitset_backend import (
    bitset_to_bool_hypercube,
    bitset_env_cache_stats,
    bitset_to_bool_array,
    build_bitset_env,
    clear_bitset_env_cache,
    eval_cm_node_bitset,
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_bitset,
    eval_expr_flat_bitset,
    eval_expr_words_bitset,
    get_expr_flat_program,
    get_flat_program,
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
                for free_dead_slots in (False, True):
                    tt_flat = bitset_to_bool_array(
                        eval_expr_flat_bitset(
                            expr,
                            tuple(f"x{i}" for i in range(n)),
                            free_dead_slots=free_dead_slots,
                        ),
                        n,
                    )
                    self.assertTrue(
                        np.array_equal(tt_ref, tt_flat),
                        msg=f"flat bitset ordering mismatch at n={n}, free={free_dead_slots}",
                    )
                # numpy-words twins (covers both the >=6-var word path and the
                # small-n bigint fallback); second call exercises scratch reuse.
                node = compile_expr_to_cm_ir(expr)
                vars_key = tuple(f"x{i}" for i in range(n))
                for _repeat in range(2):
                    tt_words_raw = bitset_to_bool_array(
                        eval_expr_words_bitset(expr, vars_key), n
                    )
                    tt_words_cm = bitset_to_bool_array(
                        eval_cm_node_words(node, vars_key), n
                    )
                    self.assertTrue(
                        np.array_equal(tt_ref, tt_words_raw),
                        msg=f"raw words ordering mismatch at n={n}",
                    )
                    self.assertTrue(
                        np.array_equal(tt_ref, tt_words_cm),
                        msg=f"cm words ordering mismatch at n={n}",
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

        # Latent-fix 3: an unknown opcode must raise in every kernel instead of
        # silently executing as EQV (hand-built program, unreachable from the
        # compilers, which emit exactly the six known opcodes).
        from bitset_backend import FlatProgram, _eval_words

        bad = FlatProgram(2, 1, ((0, "var", "x0"),), ((1, 6, (0, 0)),))
        bad_expr = Not(Var(0))
        object.__setattr__(bad_expr, "_bitset_flat_program", bad)
        with self.assertRaisesRegex(ValueError, "unknown flat opcode"):
            eval_expr_flat_bitset(bad_expr, ("x0",))
        bad_node = compile_expr_to_cm_ir(Not(Var(0)))
        object.__setattr__(bad_node, "_flat_program", bad)
        try:
            with self.assertRaisesRegex(ValueError, "unknown flat opcode"):
                eval_cm_node_flat(bad_node, ("x0",))
        finally:
            object.__setattr__(bad_node, "_flat_program", None)
        with self.assertRaisesRegex(ValueError, "unknown flat opcode"):
            _eval_words(bad, tuple(f"x{i}" for i in range(6)), {})

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
        self.assertEqual(
            bits,
            eval_cm_node_flat(node, ("x1",), fixed={"x0": 1, "x2": 0}, free_dead_slots=False),
        )
        self.assertEqual(
            bits,
            eval_cm_node_flat(node, ("x1",), fixed={"x0": 1, "x2": 0}, free_dead_slots=True),
        )
        self.assertEqual(
            bits,
            eval_expr_flat_bitset(
                expr,
                ("x1",),
                fixed={"x0": 1, "x2": 0},
                free_dead_slots=True,
            ),
        )
        self.assertEqual(
            bits, eval_cm_node_words(node, ("x1",), fixed={"x0": 1, "x2": 0})
        )
        self.assertEqual(
            bits, eval_expr_words_bitset(expr, ("x1",), fixed={"x0": 1, "x2": 0})
        )
        # genuine word path (>= 6 live vars) with a fixed variable
        wide = Imp(Xor(Var(0), Var(3)), Or(Var(5), Eqv(Var(6), Var(1))))
        wide_node = compile_expr_to_cm_ir(wide)
        wide_live = tuple(f"x{i}" for i in range(7) if i != 3)
        wide_ref = eval_cm_node_bitset(wide_node, wide_live, fixed={"x3": 1})
        self.assertEqual(
            wide_ref, eval_cm_node_words(wide_node, wide_live, fixed={"x3": 1})
        )
        self.assertEqual(
            wide_ref, eval_expr_words_bitset(wide, wide_live, fixed={"x3": 1})
        )

        # Exercise the real >=18-variable, >=64-slot release branch in pytest.
        expr = Var(0)
        for index in range(24):
            expr = Imp(
                Xor(expr, Var((index + 1) % 18)),
                Eqv(Var((index + 5) % 18), Or(Var((index + 9) % 18), Var((index + 13) % 18))),
            )
        node = compile_expr_to_cm_ir(expr)
        vars_key = tuple(f"x{i}" for i in range(18))
        self.assertGreaterEqual(get_expr_flat_program(expr).n_slots, 64)
        self.assertGreaterEqual(get_flat_program(node).n_slots, 64)

        raw_retained = eval_expr_flat_bitset(expr, vars_key, free_dead_slots=False)
        raw_released = eval_expr_flat_bitset(expr, vars_key, free_dead_slots=True)
        cm_retained = eval_cm_node_flat(node, vars_key, free_dead_slots=False)
        cm_released = eval_cm_node_flat(node, vars_key, free_dead_slots=True)
        recursive = eval_expr_bitset(expr, build_bitset_env(vars_key))
        self.assertEqual(recursive, raw_retained)
        self.assertEqual(raw_retained, raw_released)
        self.assertEqual(raw_retained, cm_retained)
        self.assertEqual(cm_retained, cm_released)


if __name__ == "__main__":
    unittest.main()
