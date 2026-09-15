from __future__ import annotations

import numpy as np

from bitset_backend import bitset_to_bool_array
from cm_exprlib import And, Var
from cmbench.expr.partial_contexts import (
    _eval_expr_bitset_fixed,
    _partial_output_vars,
    _partial_reference_array,
)


def test_full_vars_reference_keeps_context_fixed_and_broadcasts_its_axis() -> None:
    expr = And(Var(0), Var(1))
    context = {"x0": 0}
    output_vars = _partial_output_vars(2, context, "full-vars")

    reference = _partial_reference_array(expr, 2, context, output_vars)
    fixed_bits = _eval_expr_bitset_fixed(
        expr,
        {"x0": 0b0011, "x1": 0b0101},
        context,
    )

    assert np.array_equal(reference, np.zeros(4, dtype=np.uint8))
    assert np.array_equal(reference, bitset_to_bool_array(fixed_bits, 2))


def test_full_vars_reference_repeats_conditioned_function_across_fixed_axis() -> None:
    expr = And(Var(0), Var(1))
    context = {"x0": 1}
    output_vars = _partial_output_vars(2, context, "full-vars")

    reference = _partial_reference_array(expr, 2, context, output_vars)
    fixed_bits = _eval_expr_bitset_fixed(
        expr,
        {"x0": 0b1100, "x1": 0b1010},
        context,
    )

    assert np.array_equal(reference, np.array([0, 1, 0, 1], dtype=np.uint8))
    assert np.array_equal(reference, bitset_to_bool_array(fixed_bits, 2))
