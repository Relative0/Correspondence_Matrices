from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from bitset_backend import (
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_flat_bitset,
    eval_expr_words_bitset,
)
from cm_exprlib import Eqv, Imp, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir


def _deep_expression(n_vars: int, steps: int):
    expr = Var(0)
    for index in range(steps):
        expr = Imp(
            Xor(expr, Var((index + 1) % n_vars)),
            Eqv(
                Var((index + 5) % n_vars),
                Or(Var((index + 9) % n_vars), Var((index + 13) % n_vars)),
            ),
        )
    return expr


@pytest.mark.parametrize("source", ["cm_node", "raw_expr"])
def test_words_scratch_is_isolated_between_threads(source: str) -> None:
    n_vars = 16
    workers = 8
    expr = _deep_expression(n_vars, steps=64)
    node = compile_expr_to_cm_ir(expr)
    variables = tuple(f"x{i}" for i in range(n_vars))
    if source == "cm_node":
        expected = eval_cm_node_flat(node, variables)
        evaluate = lambda: eval_cm_node_words(node, variables)
    else:
        expected = eval_expr_flat_bitset(expr, variables)
        evaluate = lambda: eval_expr_words_bitset(expr, variables)

    for _round in range(3):
        barrier = Barrier(workers)

        def synchronized_evaluate(_index: int) -> int:
            barrier.wait()
            return evaluate()

        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(synchronized_evaluate, range(workers)))

        assert results == [expected] * workers
