import numpy as np

from cm_exprlib import And, Var
from cmbench.expr.partial_contexts import (
    _eval_expr_bitset_fixed,
    _partial_output_vars,
    _partial_reference_array,
    generate_partial_contexts,
    partial_context_diagnostics,
)
from bitset_backend import bitset_to_bool_array, build_bitset_env


def test_partial_context_generation_is_deterministic_with_fixed_rng() -> None:
    a = generate_partial_contexts(4, np.random.default_rng(5), context_count=3, fixed_var_count=2)
    b = generate_partial_contexts(4, np.random.default_rng(5), context_count=3, fixed_var_count=2)
    assert a == b
    diag = partial_context_diagnostics(a, 4, "random_fixed")
    assert diag["partial_context_count"] == 3


def test_partial_reference_array_matches_bitset_fixed() -> None:
    expr = And(Var(0), Var(1))
    context = {"x0": 1}
    out_vars = _partial_output_vars(2, context, "remaining-vars")
    ref = _partial_reference_array(expr, 2, context, out_vars)
    bits = _eval_expr_bitset_fixed(expr, build_bitset_env(out_vars), context)
    assert np.array_equal(ref, bitset_to_bool_array(bits, len(out_vars)))
