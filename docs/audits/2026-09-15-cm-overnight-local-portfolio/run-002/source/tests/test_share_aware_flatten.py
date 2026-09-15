"""Tests for sharing-aware associative flattening (2026-08-02 gap repair).

Guards the repair of the defect where `_canonicalize_commutative_args`
spliced *shared* associative children into every consumer, re-executing the
shared subchain once per consumer (368 vs 167 executed word ops on the 8x8
multiplier central bit in the 2026-08-02 audit).
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from bitset_backend import (
    bitset_to_bool_array,
    eval_cm_node_words,
    eval_expr_words_bitset,
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json, expr_to_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, eval_expr_tt
from cm_ir import CMIRBuilder, compile_expr_to_cm_ir


def _support(n):
    return tuple(f"x{i}" for i in range(n))


def _assert_matches_raw(expr, n_vars):
    """Packed CM output must equal the raw (no-CSE) reference evaluator."""
    node = compile_expr_to_cm_ir(expr)
    got = eval_cm_node_words(node, _support(n_vars))
    ref = eval_expr_words_bitset(expr, _support(n_vars))
    assert got == ref
    # brute-force truth-table cross-check
    expected = eval_expr_tt(expr, n_vars).astype(np.uint8)
    actual = bitset_to_bool_array(got, n_vars).astype(np.uint8)
    assert np.array_equal(actual, expected)
    return node


def _executed_ops(expr, **flags):
    node = compile_expr_to_cm_ir(expr, **flags)
    return program_metrics(get_flat_program(node))["executed_word_ops"]


def _xor_chain(vars_):
    cur = vars_[0]
    for v in vars_[1:]:
        cur = Xor(cur, v)
    return cur


def test_shared_xor_chain_multiple_parents_not_duplicated():
    h = _xor_chain([Var(0), Var(1), Var(2), Var(3)])
    expr = And(Xor(h, Var(4)), Xor(h, Var(5)))
    _assert_matches_raw(expr, 6)
    new = _executed_ops(expr)
    old = _executed_ops(expr, share_aware_flatten=False, build_memo=False)
    # legacy splicing re-executes h's 3 combines in both parents
    assert old > new
    # shared chain executed once: 3 (h) + 2 parent xors + 1 and = 6
    assert new == 6


@pytest.mark.parametrize("op", [And, Or])
def test_shared_and_or_subchains_not_duplicated(op):
    c = op(op(Var(0), Var(1)), Var(2))
    expr = Xor(op(c, Var(3)), op(c, Var(4)))
    _assert_matches_raw(expr, 5)
    assert _executed_ops(expr) < _executed_ops(expr, share_aware_flatten=False, build_memo=False)


def test_structurally_equal_separately_allocated_subtrees_are_guarded():
    def make_h():
        return _xor_chain([Var(0), Var(1), Var(2), Var(3)])

    shared = And(Xor(make_h(), Var(4)), Xor(make_h(), Var(5)))
    identity = And(Xor(h := make_h(), Var(4)), Xor(h, Var(5)))
    _assert_matches_raw(shared, 6)
    # the fanout prepass merges structural duplicates, so both forms compile
    # to the same canonical node and the same executed-op count
    n_shared = compile_expr_to_cm_ir(shared)
    n_identity = compile_expr_to_cm_ir(identity)
    assert n_shared.key == n_identity.key
    assert _executed_ops(shared) == _executed_ops(identity) == 6


def test_serialized_defs_ref_dag_keeps_guard():
    h = _xor_chain([Var(0), Var(1), Var(2), Var(3)])
    expr = And(Xor(h, Var(4)), Xor(h, Var(5)))
    rt = expr_from_json(json.loads(json.dumps(expr_to_json_dag(expr))))
    _assert_matches_raw(rt, 6)
    assert _executed_ops(rt) == _executed_ops(expr) == 6
    # v1 tree round-trip destroys identity sharing but the structural merge
    # in the prepass restores the guard
    rt_tree = expr_from_json(expr_to_json(expr))
    assert _executed_ops(rt_tree) == 6


def test_xor_duplicate_parity_still_cancels_at_node_level():
    h = _xor_chain([Var(0), Var(1), Var(2)])
    even = Xor(h, h)
    odd = Xor(Xor(h, h), h)
    even_node = compile_expr_to_cm_ir(even)
    assert even_node.const_value == 0
    odd_node = compile_expr_to_cm_ir(odd)
    assert odd_node.key == compile_expr_to_cm_ir(h).key
    _assert_matches_raw(odd, 3)


def test_constants_negation_imp_eqv_around_shared_assoc_nodes():
    h = _xor_chain([Var(0), Var(1), Var(2)])
    cases = [
        (Imp(h, Not(h)), 3),
        (Eqv(h, h), 3),                      # -> const 1
        (And(Or(h, Var(3)), Or(h, Not(Var(3)))), 4),
        (And(h, Xor(Var(4), Var(4))), 5),    # shared node ANDed with const 0
    ]
    for expr, n_vars in cases:
        _assert_matches_raw(expr, n_vars)
    assert compile_expr_to_cm_ir(Eqv(h, h)).const_value == 1
    assert compile_expr_to_cm_ir(And(h, Xor(Var(4), Var(4)))).const_value == 0


def test_deterministic_compilation_across_repeated_runs():
    h = _xor_chain([Var(0), Var(1), Var(2), Var(3)])
    expr = Or(And(Xor(h, Var(4)), Var(5)), Xor(h, Var(6)))
    first = compile_expr_to_cm_ir(expr)
    second = compile_expr_to_cm_ir(expr)
    assert first.key == second.key
    p1, p2 = get_flat_program(first), get_flat_program(second)
    assert p1.ops == p2.ops
    assert p1.loads == p2.loads


def test_no_sharing_behavior_is_unchanged():
    # fanout-1 chains must still flatten exactly as before the repair
    chain = _xor_chain([Var(i) for i in range(16)])
    node_new = compile_expr_to_cm_ir(chain)
    node_old = compile_expr_to_cm_ir(chain, share_aware_flatten=False, build_memo=False)
    assert node_new.key == node_old.key
    assert len(node_new.args) == 16
    wide = And(And(Var(0), Var(1)), And(Var(2), Var(3)))
    assert (compile_expr_to_cm_ir(wide).key
            == compile_expr_to_cm_ir(wide, share_aware_flatten=False, build_memo=False).key)


def test_canonical_key_is_representation_independent():
    """Merge-review regression (2026-08-02): a tree-expanded, dataclass-equal
    copy of a shared DAG must canonicalize to the identical key.

    Without the structural (uid) build memo, no_splice marks accruing
    mid-build made later *rebuilds* of duplicated subtrees canonicalize
    differently than their first build. Seeds 1032/1106/1148/1200/1263
    reproduced the divergence in the original fuzz.
    """
    import random as _random

    from cm_exprlib import Imp, Eqv

    ops = [And, Or, Xor, Imp, Eqv]

    def shared_dag(rng, n_vars, steps):
        pool = [Var(i) for i in range(n_vars)]
        for _ in range(steps):
            choice = rng.choice(["and", "or", "xor", "imp", "eqv", "not"])
            if choice == "not":
                pool.append(Not(rng.choice(pool)))
            else:
                cls = {"and": And, "or": Or, "xor": Xor, "imp": Imp, "eqv": Eqv}[choice]
                pool.append(cls(rng.choice(pool), rng.choice(pool)))
        root = pool[-1]
        for e in pool[-5:-1]:
            root = Xor(root, e)
        return root

    known_bad = [1032, 1106, 1148, 1200, 1263]
    for seed in known_bad + list(range(1000, 1030)):
        rng = _random.Random(seed)
        n_vars = rng.choice([4, 6, 8, 10])
        expr = shared_dag(rng, n_vars, rng.randrange(10, 45))
        copy = expr_from_json(expr_to_json(expr))  # sharing destroyed
        assert copy == expr
        assert compile_expr_to_cm_ir(copy).key == compile_expr_to_cm_ir(expr).key, seed


def test_commutative_equivalent_shared_subtrees_are_guarded():
    """2026-08-02 Phase A4: Xor(a,b) and Xor(b,a) (and AND/OR/EQV analogues)
    are one guard class, so commuted duplicates no longer duplicate work."""
    a, b, c = Var(0), Var(1), Var(2)
    for op in (Xor, And, Or):
        h1 = op(op(a, b), c)
        h2 = op(c, op(b, a))  # commuted, nested permutation
        expr = Eqv(Imp(h1, Var(3)), Imp(h2, Var(4)))
        node = compile_expr_to_cm_ir(expr)
        # identity-shared reference: the same expression with one shared h
        h = op(op(a, b), c)
        ref = compile_expr_to_cm_ir(Eqv(Imp(h, Var(3)), Imp(h, Var(4))))
        assert node.key == ref.key, op.__name__
        assert (program_metrics(get_flat_program(node))["executed_word_ops"]
                == program_metrics(get_flat_program(ref))["executed_word_ops"])
        _assert_matches_raw(expr, 5)
    # EQV analogue (commutative, non-associative)
    e1, e2 = Eqv(a, b), Eqv(b, a)
    expr = And(Xor(e1, c), Xor(e2, Var(3)))
    _assert_matches_raw(expr, 4)


def test_ablation_flag_reproduces_legacy_splice():
    h = _xor_chain([Var(0), Var(1), Var(2), Var(3)])
    expr = And(Xor(h, Var(4)), Xor(h, Var(5)))
    legacy = compile_expr_to_cm_ir(expr, share_aware_flatten=False, build_memo=False)
    # legacy: both parents are 5-ary xors over spliced leaves
    m = program_metrics(get_flat_program(legacy))
    assert m["executed_word_ops"] == 9  # 4 + 4 + 1 (and)
    _assert_matches_raw(expr, 6)
