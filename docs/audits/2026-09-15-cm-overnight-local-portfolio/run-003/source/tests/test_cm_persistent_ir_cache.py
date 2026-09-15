import unittest

import numpy as np

from bitset_backend import bitset_to_bool_array
from cm_exprlib import And, Or, Var, Xor, eval_expr_tt
from cm_ir import (
    clear_cm_ir_persistent_cache,
    cm_ir_persistent_cache_stats,
    compile_expr,
    compile_expr_to_cm_ir,
    evaluate_compiled,
    expr_structural_hash,
)


class CMPersistentIRCacheTests(unittest.TestCase):
    def test_structural_hash_is_deterministic_and_commutative(self) -> None:
        a = And(Var(0), Var(1))
        b = And(Var(1), Var(0))
        self.assertEqual(expr_structural_hash(a), expr_structural_hash(b))

    def test_persistent_cache_hits_on_equivalent_expr_objects(self) -> None:
        clear_cm_ir_persistent_cache()
        expr1 = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))
        expr2 = Or(And(Var(1), Var(0)), Xor(Var(3), Var(2)))  # same structure under commutative canon

        d1 = {}
        n1 = compile_expr_to_cm_ir(expr1, diagnostics=d1, persistent_cache=True)
        self.assertEqual(int(d1.get("ir_persistent_cache_hits", 0)), 0)
        self.assertGreaterEqual(int(d1.get("ir_persistent_cache_misses", 0)), 1)
        self.assertGreaterEqual(int(d1.get("ir_persistent_cache_size", 0)), 1)

        d2 = {}
        n2 = compile_expr_to_cm_ir(expr2, diagnostics=d2, persistent_cache=True)
        self.assertGreaterEqual(int(d2.get("ir_persistent_cache_hits", 0)), 1)
        self.assertEqual(int(d2.get("ir_persistent_cache_misses", 0)), 0)
        self.assertIs(n1, n2)

    def test_persistent_cache_stats_and_clear(self) -> None:
        clear_cm_ir_persistent_cache()
        self.assertEqual(cm_ir_persistent_cache_stats()["ir_persistent_cache_size"], 0)

        expr = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))
        diag = {}
        compile_expr_to_cm_ir(expr, diagnostics=diag, persistent_cache=True)
        self.assertGreater(cm_ir_persistent_cache_stats()["ir_persistent_cache_size"], 0)
        self.assertEqual(
            cm_ir_persistent_cache_stats()["ir_persistent_cache_size"],
            int(diag.get("ir_persistent_cache_size", 0)),
        )

        clear_cm_ir_persistent_cache()
        self.assertEqual(cm_ir_persistent_cache_stats()["ir_persistent_cache_size"], 0)

    def test_related_expressions_hit_shared_subtrees(self) -> None:
        clear_cm_ir_persistent_cache()
        shared = And(Var(0), Var(1))
        expr1 = Or(shared, Xor(Var(2), Var(3)))
        expr2 = Xor(shared, Or(Var(2), Var(4)))

        d1 = {}
        compile_expr_to_cm_ir(expr1, diagnostics=d1, persistent_cache=True)
        size_after_first = cm_ir_persistent_cache_stats()["ir_persistent_cache_size"]
        self.assertGreater(size_after_first, 0)

        d2 = {}
        compile_expr_to_cm_ir(expr2, diagnostics=d2, persistent_cache=True)
        self.assertGreaterEqual(int(d2.get("ir_persistent_cache_hits", 0)), 1)
        self.assertGreaterEqual(cm_ir_persistent_cache_stats()["ir_persistent_cache_size"], size_after_first)

    def test_compile_expr_and_evaluate_compiled_hybrid_no_reinflate(self) -> None:
        n = 8
        expr = Or(And(Var(0), Var(1)), Xor(Var(2), Var(3)))
        compiled = compile_expr(expr, use_persistent_cache=True)
        res = evaluate_compiled(compiled, mode="hybrid_no_reinflate", vars_all=[f"x{i}" for i in range(n)])
        if res.bits is not None:
            tt = bitset_to_bool_array(int(res.bits), n)
        else:
            tt = res.tt
        tt_ref = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)
        self.assertTrue(tt is not None and np.array_equal(tt, tt_ref))


if __name__ == "__main__":
    unittest.main()
