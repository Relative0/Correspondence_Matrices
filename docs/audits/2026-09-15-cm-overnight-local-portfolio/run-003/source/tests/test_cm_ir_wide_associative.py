from __future__ import annotations

from typing import Any, Callable, Iterable

import numpy as np
import pytest

from bitset_backend import bitset_to_bool_array
from cm_exprlib import And, Not, Or, Var, eval_expr_tt
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate


def _balanced(op: Callable[[Any, Any], Any], leaves: Iterable[Any]) -> Any:
    level = list(leaves)
    while len(level) > 1:
        next_level = []
        iterator = iter(level)
        for left in iterator:
            right = next(iterator, None)
            next_level.append(left if right is None else op(left, right))
        level = next_level
    return level[0]


@pytest.mark.parametrize(("op", "expected_op"), [(And, "AND"), (Or, "OR")])
def test_wide_associative_compile_retains_all_unique_operands(op, expected_op) -> None:
    width = 128
    node = compile_expr_to_cm_ir(_balanced(op, (Var(i) for i in range(width))))

    assert node.kind == "binary"
    assert node.op == expected_op
    assert len(node.args) == width
    assert node.vars == tuple(f"x{i}" for i in range(width))


@pytest.mark.parametrize(("op", "expected"), [(And, 0), (Or, 1)])
@pytest.mark.parametrize("negated_first", [False, True])
def test_wide_associative_complement_pruning_is_order_independent(
    op, expected: int, negated_first: bool
) -> None:
    pivot = Var(63)
    complement_pair = [Not(pivot), pivot] if negated_first else [pivot, Not(pivot)]
    leaves = [Var(i) for i in range(63)] + complement_pair

    diagnostics = {}
    node = compile_expr_to_cm_ir(_balanced(op, leaves), diagnostics=diagnostics)

    assert node.const_value == expected
    assert diagnostics["pruned_branches"] >= 1


@pytest.mark.parametrize("op", [And, Or])
def test_associative_complement_optimization_preserves_truth_table(op) -> None:
    n_vars = 8
    leaves = [Var(i) for i in range(n_vars)] + [Not(Var(3))]
    expr = _balanced(op, leaves)
    node = compile_expr_to_cm_ir(expr)
    result = materialize_hybrid_no_reinflate(
        node,
        [f"x{i}" for i in range(n_vars)],
        hybrid_threshold=n_vars,
        flat_eval=True,
    )

    expected = eval_expr_tt(expr, n_vars).astype(np.uint8, copy=False).reshape(-1)
    assert result.bits is not None
    actual = bitset_to_bool_array(int(result.bits), n_vars).astype(np.uint8, copy=False)
    assert np.array_equal(actual, expected)
