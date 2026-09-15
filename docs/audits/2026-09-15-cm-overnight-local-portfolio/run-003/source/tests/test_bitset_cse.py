"""Tests for the structural-CSE BitSet production baseline (2026-08-02 repair)."""
from __future__ import annotations

import random

import pytest

from bitset_backend import (
    compile_expr_cse,
    compile_expr_flat,
    eval_expr_flat_cse,
    eval_expr_words_bitset,
    eval_expr_words_cse,
    get_expr_cse_program,
    program_metrics,
)
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor


def _support(n):
    return tuple(f"x{i}" for i in range(n))


def _random_expr(rng, n_vars, steps, share=True):
    pool = [Var(i) for i in range(n_vars)]
    for _ in range(steps):
        op = rng.choice([And, Or, Xor, Imp, Eqv, Not])
        if op is Not:
            pool.append(Not(rng.choice(pool)))
        else:
            a = rng.choice(pool)
            b = rng.choice(pool) if share else Var(rng.randrange(n_vars))
            pool.append(op(a, b))
    expr = pool[-1]
    for extra in pool[-4:-1]:
        expr = Xor(expr, extra)
    return expr


@pytest.mark.parametrize("flatten", [False, True])
@pytest.mark.parametrize("seed", range(8))
def test_cse_matches_raw_on_random_shared_expressions(seed, flatten):
    rng = random.Random(seed)
    expr = _random_expr(rng, 8, 20)
    got = eval_expr_words_cse(expr, _support(8), flatten=flatten)
    assert got == eval_expr_words_bitset(expr, _support(8))


@pytest.mark.parametrize("flatten", [False, True])
@pytest.mark.parametrize("n_vars", [3, 8, 12, 16])
def test_cse_bigint_and_words_arms_are_identical(n_vars, flatten):
    rng = random.Random(1000 + n_vars)
    expr = _random_expr(rng, n_vars, 24)
    support = _support(n_vars)
    expected = eval_expr_words_bitset(expr, support)
    assert eval_expr_flat_cse(expr, support, flatten=flatten) == expected
    assert eval_expr_words_cse(expr, support, flatten=flatten) == expected


def test_cse_compiles_each_distinct_subtree_once():
    h = Xor(Xor(Var(0), Var(1)), Var(2))
    expr = And(Or(h, Var(3)), Xor(h, Var(4)))
    cse = compile_expr_cse(expr)
    raw = compile_expr_flat(expr)
    assert len(cse.ops) < len(raw.ops)
    # structurally equal, separately allocated subtrees dedupe identically
    def make_h():
        return Xor(Xor(Var(0), Var(1)), Var(2))
    expr2 = And(Or(make_h(), Var(3)), Xor(make_h(), Var(4)))
    assert len(compile_expr_cse(expr2).ops) == len(cse.ops)


def test_sharing_aware_flatten_never_adds_executed_ops():
    rng = random.Random(99)
    cases = [_random_expr(rng, 8, 25) for _ in range(6)]
    h = Xor(Xor(Var(0), Var(1)), Var(2))
    cases.append(And(Xor(h, Var(3)), Xor(h, Var(4))))
    chain = Var(0)
    for i in range(1, 12):
        chain = Xor(chain, Var(i))
    cases.append(chain)
    for expr in cases:
        plain = program_metrics(compile_expr_cse(expr))
        flat = program_metrics(compile_expr_cse(expr, flatten=True))
        assert flat["executed_word_ops"] == plain["executed_word_ops"]
        assert flat["flat_instructions"] <= plain["flat_instructions"]


def test_fanout1_chains_do_flatten():
    chain = Var(0)
    for i in range(1, 12):
        chain = Xor(chain, Var(i))
    prog = compile_expr_cse(chain, flatten=True)
    assert len(prog.ops) == 1
    assert len(prog.ops[0][2]) == 12


def test_shared_chain_is_not_spliced():
    h = Xor(Xor(Var(0), Var(1)), Var(2))
    expr = Xor(Xor(h, Var(3)), Xor(h, Var(4)))
    m = program_metrics(compile_expr_cse(expr, flatten=True))
    # h computed once (2 combines) + parents (2 + 1 + 1): duplication would give 9+
    assert m["executed_word_ops"] == program_metrics(compile_expr_cse(expr))["executed_word_ops"]


def test_program_cache_is_per_flag():
    expr = And(Var(0), Or(Var(1), Var(2)))
    a = get_expr_cse_program(expr)
    b = get_expr_cse_program(expr, flatten=True)
    assert a is get_expr_cse_program(expr)
    assert b is get_expr_cse_program(expr, flatten=True)
    assert a is not b


def test_bigint_fallback_below_six_vars():
    expr = Imp(And(Var(0), Var(1)), Xor(Var(2), Not(Var(0))))
    assert (eval_expr_words_cse(expr, _support(3))
            == eval_expr_words_bitset(expr, _support(3)))


def test_deep_tree_compiles_without_recursion_error():
    expr = Var(0)
    for i in range(1, 4000):
        expr = Xor(expr, Var(i % 8))
    prog = compile_expr_cse(expr)
    assert len(prog.ops) >= 1
