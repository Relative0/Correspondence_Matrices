import pytest

from bitset_backend import build_bitset_env, eval_expr_bitset
from cm_exprlib import Imp, Var
from cm_ir import compile_expr_to_cm_ir
from cmbench.backends.bitset_engine import (
    WORDS_AUTO_MIN_VARS,
    select_cm_node_engine,
    select_raw_ast_engine,
)


@pytest.mark.parametrize("live_k", range(0, WORDS_AUTO_MIN_VARS))
def test_words_request_truthfully_selects_flat_below_auto_crossover(live_k):
    selected = select_raw_ast_engine(
        live_k=live_k, words_requested=True, flat_requested=False
    )
    assert selected.kind == "raw_ast_flat"
    assert selected.requires_bigint_env is False


@pytest.mark.parametrize("live_k", [WORDS_AUTO_MIN_VARS, 17, 20])
def test_words_request_selects_words_at_auto_crossover_and_above(live_k):
    selected = select_raw_ast_engine(
        live_k=live_k, words_requested=True, flat_requested=False
    )
    assert selected.kind == "raw_ast_words"


def test_default_and_explicit_flat_policy():
    recursive = select_raw_ast_engine(
        live_k=8, words_requested=False, flat_requested=False
    )
    flat = select_raw_ast_engine(
        live_k=8, words_requested=False, flat_requested=True
    )
    assert recursive.kind == "raw_ast_recursive"
    assert recursive.requires_bigint_env is True
    assert flat.kind == "raw_ast_flat"
    assert flat.requires_bigint_env is False


def test_selected_evaluators_are_bit_identical():
    expr = Imp(Var(0), Var(1))
    for k in (2, 6, 12, 13, 16):
        names = tuple(f"x{i}" for i in range(k))
        reference = eval_expr_bitset(expr, build_bitset_env(names))
        selection = select_raw_ast_engine(
            live_k=k, words_requested=True, flat_requested=False
        )
        assert selection.evaluate_expr(expr, names) == reference
        node_selection = select_cm_node_engine(
            live_k=k, words_requested=True, flat_requested=False
        )
        assert node_selection.evaluate_node(compile_expr_to_cm_ir(expr), names) == reference
