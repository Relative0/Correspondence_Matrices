"""Tests for the lifetime-safe per-compilation build memo (2026-08-02 repair).

The memo lives only for one outermost CMIRBuilder.build call and holds strong
references to every memoized Expr, so recycled object ids can never alias a
stale entry — the hazard the 2026-08-02 audit found in the id-keyed prototype.
"""
from __future__ import annotations

import gc
import random

from bitset_backend import eval_expr_words_bitset, get_flat_program, _eval_words
from cm_exprlib import And, Not, Or, Var, Xor
from cm_ir import CMIRBuilder, compile_expr_to_cm_ir


def _support(n):
    return tuple(f"x{i}" for i in range(n))


def _ladder(depth):
    cur = Xor(Var(0), Var(1))
    for level in range(depth):
        cur = Or(And(cur, Var(2 + level % 6)), And(cur, Var(3 + level % 5)))
    return cur


def test_memo_hits_on_shared_dag_and_result_matches_raw():
    expr = _ladder(8)
    diag = {}
    node = compile_expr_to_cm_ir(expr, diagnostics=diag)
    assert diag.get("build_memo_hits", 0) > 0
    got = _eval_words(get_flat_program(node), _support(8), {})
    assert got == eval_expr_words_bitset(expr, _support(8))


def test_memo_scope_is_one_build_no_state_left_behind():
    builder = CMIRBuilder()
    builder.build(_ladder(3))
    assert builder._build_state is None
    builder.build(_ladder(4))
    assert builder._build_state is None


def test_id_reuse_across_many_discarded_expressions_stays_correct():
    """Create/discard many expression graphs while reusing ONE builder.

    CPython aggressively recycles object ids, so a memo that outlived its
    expressions would produce stale hits here. Every compile must still match
    the raw evaluator exactly.
    """
    builder = CMIRBuilder()
    rng = random.Random(20260802)
    for round_no in range(60):
        n_vars = 6
        pool = [Var(i) for i in range(n_vars)]
        for _ in range(12):
            op = rng.choice([And, Or, Xor])
            pool.append(op(rng.choice(pool), rng.choice(pool)))
        expr = pool[-1]
        for extra in pool[-4:-1]:
            expr = Xor(expr, extra)
        node = builder.build(expr)
        got = _eval_words(get_flat_program(node), _support(n_vars), {})
        assert got == eval_expr_words_bitset(expr, _support(n_vars)), round_no
        del expr, pool, node
        gc.collect()


def test_repeated_compilation_is_stable():
    expr = _ladder(6)
    keys = {compile_expr_to_cm_ir(expr).key for _ in range(5)}
    assert len(keys) == 1


def test_diagnostics_on_off_produce_identical_nodes():
    expr = _ladder(5)
    with_diag = compile_expr_to_cm_ir(expr, diagnostics={"ir_timing_enabled": 1})
    without = compile_expr_to_cm_ir(expr)
    assert with_diag.key == without.key


def test_structurally_equal_separately_allocated_objects_intern_to_one_node():
    def make():
        return And(Xor(Var(0), Var(1)), Var(2))

    e1, e2 = make(), make()
    builder = CMIRBuilder()
    combined = Or(e1, e2)
    node = builder.build(combined)
    # Or(e, e) with structurally equal args canonicalizes to the single arg
    assert node.key == builder.build(make()).key


def test_memo_off_flag_reproduces_legacy_visit_pattern():
    expr = _ladder(6)
    a = compile_expr_to_cm_ir(expr, build_memo=False)
    b = compile_expr_to_cm_ir(expr)
    assert a.key == b.key
    assert (_eval_words(get_flat_program(a), _support(8), {})
            == _eval_words(get_flat_program(b), _support(8), {}))
