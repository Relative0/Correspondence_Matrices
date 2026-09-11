"""Ordering, lifecycle, and independent truth checks for periodic packed masks."""
from concurrent.futures import ThreadPoolExecutor
import unittest

import numpy as np

from bitset_backend import (
    bitset_env_cache_stats, build_bitset_env, clear_bitset_env_cache,
    eval_cm_node_flat, eval_cm_node_words,
)
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir


class PackedMaskConstructionTests(unittest.TestCase):
    def tearDown(self):
        clear_bitset_env_cache()

    def test_every_column_against_assignment_indices(self):
        # Includes the unchanged branch, byte/word boundaries and larger widths.
        for n in (0, 1, 2, 3, 6, 10, 11, 12, 16, 18, 20):
            names = tuple(f"axis-{i}" for i in reversed(range(n)))
            env = build_bitset_env(names)
            self.assertEqual(tuple(env), names)
            rows = np.arange(1 << n, dtype=np.uint32)
            for position, name in enumerate(names):
                expected = ((rows >> (n - 1 - position)) & 1).astype(np.uint8)
                actual = np.unpackbits(np.frombuffer(
                    env[name].to_bytes(max(1, (1 << n) // 8), "little"), dtype=np.uint8), bitorder="little")
                np.testing.assert_array_equal(actual[:1 << n], expected)
                self.assertLess(env[name].bit_length(), (1 << n) + 1)

    def test_cache_identity_order_immutability_and_eviction(self):
        clear_bitset_env_cache()
        names = tuple(f"x{i}" for i in range(11))
        first = build_bitset_env(names)
        self.assertIs(first, build_bitset_env(list(names)))
        with self.assertRaises(TypeError):
            first["x0"] = 0
        reversed_env = build_bitset_env(tuple(reversed(names)))
        self.assertEqual(first["x0"], reversed_env["x10"])
        for key in range(260):
            build_bitset_env(tuple(f"case-{key}-{i}" for i in range(11)))
        self.assertEqual(bitset_env_cache_stats()["size"], 256)
        reloaded = build_bitset_env(names)
        self.assertIsNot(reloaded, first)
        self.assertEqual(reloaded, first)
        clear_bitset_env_cache()
        self.assertEqual(bitset_env_cache_stats()["size"], 0)

    def test_concurrent_readers_have_exact_immutable_masks(self):
        names = tuple(f"x{i}" for i in range(13))
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(build_bitset_env, [names] * 16))
        self.assertTrue(all(result == results[0] for result in results))

    def test_restrictions_and_all_operators_with_permuted_basis(self):
        shared = Xor(Var(0), And(Var(1), Var(2)))
        expr = Eqv(Imp(shared, Or(Var(3), Not(Var(4)))), Xor(shared, Var(5)))
        node = compile_expr_to_cm_ir(expr)
        # Unused declared axes still belong to the explicit-output contract.
        names = tuple(f"x{i}" for i in reversed(range(13)))
        for fixed in ({}, {"x1": 0, "x3": 1}, {"x1": 1, "x3": 0}):
            live = tuple(name for name in names if name not in fixed)
            rows = np.arange(1 << len(live), dtype=np.uint32)
            columns = {name: ((rows >> (len(live) - 1 - p)) & 1).astype(bool)
                       for p, name in enumerate(live)}
            columns.update({name: bool(value) for name, value in fixed.items()})
            common = columns["x0"] ^ (columns["x1"] & columns["x2"])
            expected = ((~common) | (columns["x3"] | ~columns["x4"])) == (common ^ columns["x5"])
            packed = int.from_bytes(np.packbits(expected, bitorder="little").tobytes(), "little")
            self.assertEqual(eval_cm_node_flat(node, live, fixed=fixed), packed)
            self.assertEqual(eval_cm_node_words(node, live, fixed=fixed), packed)


if __name__ == "__main__":
    unittest.main()
