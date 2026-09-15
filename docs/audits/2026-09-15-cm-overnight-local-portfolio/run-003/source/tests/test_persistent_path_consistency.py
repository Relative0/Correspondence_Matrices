"""Persistent/normal compile-path consistency tests (2026-08-02 Phase A1).

The persistent path must produce canonical keys and graph shapes identical to
the default builder for every expression and option combination; cache hits
must never cross incompatible flattening options; and no object-id state may
outlive its referents.
"""
from __future__ import annotations

import gc
import json
import random
import unittest

import cm_ir
from bitset_backend import (
    eval_cm_node_words,
    eval_expr_words_bitset,
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json, expr_to_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import (
    clear_cm_ir_persistent_cache,
    compile_expr_to_cm_ir,
    compile_expr_to_cm_ir_persistent,
)


def _support(expr):
    seen, out, stack = set(), set(), [expr]
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if isinstance(cur, Var):
            out.add(int(cur.i))
        elif isinstance(cur, Not):
            stack.append(cur.a)
        else:
            stack.extend((cur.a, cur.b))
    names = {f"x{i}" for i in out} | {f"x{i}" for i in range(6)}
    return tuple(sorted(names, key=lambda s: int(s[1:])))


def _xor_chain(vars_):
    cur = vars_[0]
    for v in vars_[1:]:
        cur = Xor(cur, v)
    return cur


def _shared_cases():
    h_xor = _xor_chain([Var(0), Var(1), Var(2), Var(3)])
    h_and = And(And(Var(0), Var(1)), Var(2))
    h_or = Or(Or(Var(0), Var(1)), Var(2))
    return [
        ("shared_xor", And(Xor(h_xor, Var(4)), Xor(h_xor, Var(5)))),
        ("shared_and", Xor(And(h_and, Var(3)), And(h_and, Var(4)))),
        ("shared_or", Eqv(Or(h_or, Var(3)), Imp(h_or, Var(4)))),
        ("no_sharing_chain", _xor_chain([Var(i) for i in range(10)])),
    ]


def _assert_same_compile(test, expr, **flags):
    clear_cm_ir_persistent_cache()
    normal = compile_expr_to_cm_ir(expr, **flags)
    persistent = compile_expr_to_cm_ir_persistent(expr, **flags)
    test.assertEqual(normal.key, persistent.key)
    pn, pp = get_flat_program(normal), get_flat_program(persistent)
    test.assertEqual(pn.ops, pp.ops)
    test.assertEqual(pn.loads, pp.loads)
    test.assertEqual(program_metrics(pn), program_metrics(pp))
    sup = _support(expr)
    test.assertEqual(eval_cm_node_words(persistent, sup),
                     eval_expr_words_bitset(expr, sup))
    clear_cm_ir_persistent_cache()


class PersistentPathConsistencyTests(unittest.TestCase):
    def test_normal_and_persistent_agree_on_shared_dags(self):
        for name, expr in _shared_cases():
            with self.subTest(name):
                _assert_same_compile(self, expr)
                _assert_same_compile(self, expr, share_aware_flatten=False, build_memo=False)

    def test_persistent_preserves_shared_associative_subchains(self):
        h = _xor_chain([Var(0), Var(1), Var(2), Var(3)])
        expr = And(Xor(h, Var(4)), Xor(h, Var(5)))
        clear_cm_ir_persistent_cache()
        node = compile_expr_to_cm_ir_persistent(expr)
        # shared chain executed once: 3 (h) + 2 parent xors + 1 and
        self.assertEqual(program_metrics(get_flat_program(node))["executed_word_ops"], 6)
        clear_cm_ir_persistent_cache()

    def test_separately_allocated_copies_and_representations_agree(self):
        def make():
            h = _xor_chain([Var(0), Var(1), Var(2), Var(3)])
            return And(Xor(h, Var(4)), Xor(h, Var(5)))

        clear_cm_ir_persistent_cache()
        base_key = compile_expr_to_cm_ir(make()).key
        for variant in (
            make(),                                             # fresh allocation
            expr_from_json(expr_to_json(make())),               # tree-expanded
            expr_from_json(json.loads(json.dumps(expr_to_json_dag(make())))),  # defs/ref
        ):
            self.assertEqual(compile_expr_to_cm_ir_persistent(variant).key, base_key)
        clear_cm_ir_persistent_cache()

    def test_commutative_variant_hits_and_matches_normal_compile(self):
        # a shared-class expression (root-level caching regime): the commuted
        # variant must HIT the digest cache, and the served node must equal
        # the normal compile of the variant itself
        h = _xor_chain([Var(0), Var(1), Var(2)])
        expr = And(Xor(h, Var(3)), Xor(h, Var(4)))
        commuted = And(Xor(Var(4), h), Xor(Var(3), h))
        clear_cm_ir_persistent_cache()
        d1, d2 = {}, {}
        n1 = compile_expr_to_cm_ir_persistent(expr, diagnostics=d1)
        n2 = compile_expr_to_cm_ir_persistent(commuted, diagnostics=d2)
        self.assertGreaterEqual(d2.get("ir_persistent_cache_hits", 0), 1)
        self.assertIs(n1, n2)
        self.assertEqual(n2.key, compile_expr_to_cm_ir(commuted).key)
        clear_cm_ir_persistent_cache()

    def test_cold_miss_then_warm_hit(self):
        expr = _shared_cases()[0][1]
        clear_cm_ir_persistent_cache()
        d_cold, d_warm = {}, {}
        n_cold = compile_expr_to_cm_ir_persistent(expr, diagnostics=d_cold)
        n_warm = compile_expr_to_cm_ir_persistent(expr, diagnostics=d_warm)
        self.assertEqual(d_cold.get("ir_persistent_cache_hits", 0), 0)
        self.assertGreaterEqual(d_cold.get("ir_persistent_cache_misses", 0), 1)
        self.assertGreaterEqual(d_warm.get("ir_persistent_cache_hits", 0), 1)
        self.assertIs(n_cold, n_warm)
        clear_cm_ir_persistent_cache()

    def test_option_change_never_cross_hits(self):
        h = _xor_chain([Var(0), Var(1), Var(2), Var(3)])
        expr = And(Xor(h, Var(4)), Xor(h, Var(5)))
        clear_cm_ir_persistent_cache()
        guarded = compile_expr_to_cm_ir_persistent(expr)
        legacy = compile_expr_to_cm_ir_persistent(
            expr, share_aware_flatten=False, build_memo=False)
        self.assertIsNot(guarded, legacy)
        self.assertNotEqual(
            program_metrics(get_flat_program(guarded))["executed_word_ops"],
            program_metrics(get_flat_program(legacy))["executed_word_ops"])
        self.assertEqual(
            legacy.key,
            compile_expr_to_cm_ir(expr, share_aware_flatten=False, build_memo=False).key)
        clear_cm_ir_persistent_cache()

    def test_build_memo_flag_does_not_change_output_or_fragment_cache(self):
        expr = _shared_cases()[0][1]
        clear_cm_ir_persistent_cache()
        d1, d2 = {}, {}
        n1 = compile_expr_to_cm_ir_persistent(expr, diagnostics=d1, build_memo=True)
        n2 = compile_expr_to_cm_ir_persistent(expr, diagnostics=d2, build_memo=False)
        self.assertIs(n1, n2)  # same cache entry: memo is not part of the key
        self.assertGreaterEqual(d2.get("ir_persistent_cache_hits", 0), 1)
        clear_cm_ir_persistent_cache()

    def test_cache_eviction_keeps_bound_and_recompiles(self):
        old_max = cm_ir._PERSISTENT_IR_CACHE_MAXSIZE
        cm_ir._PERSISTENT_IR_CACHE_MAXSIZE = 4
        try:
            clear_cm_ir_persistent_cache()
            exprs = [_xor_chain([Var(i) for i in range(2 + k)]) for k in range(8)]
            for e in exprs:
                compile_expr_to_cm_ir_persistent(e)
            self.assertLessEqual(len(cm_ir._PERSISTENT_IR_CACHE), 4)
            d = {}
            n = compile_expr_to_cm_ir_persistent(exprs[0], diagnostics=d)  # evicted
            self.assertGreaterEqual(d.get("ir_persistent_cache_misses", 0), 1)
            self.assertEqual(n.key, compile_expr_to_cm_ir(exprs[0]).key)
        finally:
            cm_ir._PERSISTENT_IR_CACHE_MAXSIZE = old_max
            clear_cm_ir_persistent_cache()

    def test_gc_and_id_reuse_pressure(self):
        clear_cm_ir_persistent_cache()
        rng = random.Random(20260802)
        for round_no in range(60):
            pool = [Var(i) for i in range(6)]
            for _ in range(12):
                op = rng.choice([And, Or, Xor])
                pool.append(op(rng.choice(pool), rng.choice(pool)))
            expr = pool[-1]
            for extra in pool[-4:-1]:
                expr = Xor(expr, extra)
            node = compile_expr_to_cm_ir_persistent(expr)
            sup = _support(expr)
            self.assertEqual(eval_cm_node_words(node, sup),
                             eval_expr_words_bitset(expr, sup), round_no)
            del expr, pool, node
            gc.collect()
        clear_cm_ir_persistent_cache()

    # Concurrency: the persistent cache and CMIRBuilder do not claim thread
    # safety (module-level OrderedDict, builder-local state); no concurrent
    # test is added and none is implied by the API.


if __name__ == "__main__":
    unittest.main()
