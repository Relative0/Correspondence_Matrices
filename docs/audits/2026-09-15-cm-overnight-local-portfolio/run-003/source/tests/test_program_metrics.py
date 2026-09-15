"""Tests for program_metrics: executed-operation accounting for FlatProgram.

Guards the 2026-08-02 gap-repair finding that ``len(prog.ops)`` is an
instruction count, not an executed-operation count.
"""
from __future__ import annotations

import pytest

from bitset_backend import (
    _FLAT_OP_AND,
    _FLAT_OP_EQV,
    _FLAT_OP_IMP,
    _FLAT_OP_NOT,
    _FLAT_OP_OR,
    _FLAT_OP_XOR,
    FlatProgram,
    compile_expr_flat,
    get_flat_program,
    program_metrics,
)
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir


def _prog(loads, ops):
    n_slots = len(loads) + len(ops)
    root = ops[-1][0] if ops else loads[-1][0]
    return FlatProgram(n_slots, root, tuple(loads), tuple(ops))


def test_unary_not_counts():
    prog = _prog([(0, "var", "x0")], [(1, _FLAT_OP_NOT, (0,))])
    m = program_metrics(prog)
    assert m["flat_instructions"] == 1
    assert m["loads"] == 1
    assert m["argument_edges"] == 1
    assert m["executed_word_ops"] == 1      # bitwise_not
    assert m["executed_bigint_ops"] == 2    # ~ then & mask


def test_binary_ops_count_one_combine():
    for opcode in (_FLAT_OP_AND, _FLAT_OP_OR, _FLAT_OP_XOR):
        prog = _prog([(0, "var", "x0"), (1, "var", "x1")], [(2, opcode, (0, 1))])
        m = program_metrics(prog)
        assert m["flat_instructions"] == 1
        assert m["executed_word_ops"] == 1
        assert m["executed_bigint_ops"] == 1
        assert m["argument_edges"] == 2


def test_imp_eqv_expand_to_multiple_primitives():
    for opcode, word, bigint in ((_FLAT_OP_IMP, 2, 3), (_FLAT_OP_EQV, 2, 3)):
        prog = _prog([(0, "var", "x0"), (1, "var", "x1")], [(2, opcode, (0, 1))])
        m = program_metrics(prog)
        assert m["flat_instructions"] == 1
        assert m["executed_word_ops"] == word
        assert m["executed_bigint_ops"] == bigint


def test_nary_instruction_counts_arity_minus_one():
    loads = [(i, "var", f"x{i}") for i in range(5)]
    prog = _prog(loads, [(5, _FLAT_OP_XOR, (0, 1, 2, 3, 4))])
    m = program_metrics(prog)
    assert m["flat_instructions"] == 1
    assert m["argument_edges"] == 5
    assert m["executed_word_ops"] == 4
    assert m["executed_bigint_ops"] == 4


def test_one_ary_instruction_is_a_copy_in_words_executor():
    prog = _prog([(0, "var", "x0")], [(1, _FLAT_OP_AND, (0,))])
    m = program_metrics(prog)
    assert m["executed_word_ops"] == 1   # np.copyto
    assert m["executed_bigint_ops"] == 0  # acc aliasing, no combine


def test_xor_chain_cm_vs_raw_executed_ops_agree():
    # The historical trap: CM lowers a 16-leaf XOR chain to ONE n-ary
    # instruction while the raw program has 15 binary instructions — but both
    # execute exactly 15 primitive combines.
    expr = Var(0)
    for i in range(1, 16):
        expr = Xor(expr, Var(i))
    cm_prog = get_flat_program(compile_expr_to_cm_ir(expr))
    raw_prog = compile_expr_flat(expr)
    cm_m = program_metrics(cm_prog)
    raw_m = program_metrics(raw_prog)
    assert raw_m["flat_instructions"] == 15
    assert cm_m["executed_word_ops"] == raw_m["executed_word_ops"] == 15
    assert cm_m["executed_bigint_ops"] == raw_m["executed_bigint_ops"] == 15


def test_mixed_expression_metrics_are_deterministic():
    expr = Imp(Eqv(And(Var(0), Var(1)), Or(Var(2), Not(Var(3)))), Xor(Var(4), Var(5)))
    prog = compile_expr_flat(expr)
    first = program_metrics(prog)
    second = program_metrics(prog)
    assert first == second
    assert first["peak_live_word_buffers"] >= 1


def test_program_metrics_is_observationally_pure():
    """2026-08-02 Phase A3: metric collection must not mutate program state
    or warm evaluation caches."""
    expr = Imp(Eqv(And(Var(0), Var(1)), Or(Var(2), Not(Var(3)))), Xor(Var(4), Var(5)))
    prog = compile_expr_flat(expr)
    assert prog.word_plan is None
    before = (prog.word_plan, dict(prog.bound_cache),
              getattr(prog.word_scratch_local, "by_width", None))
    program_metrics(prog)
    after = (prog.word_plan, dict(prog.bound_cache),
             getattr(prog.word_scratch_local, "by_width", None))
    assert before == after
    assert prog.word_plan is None  # in particular, no plan was cached
