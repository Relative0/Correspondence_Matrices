import numpy as np

from cm_exprlib import And, Eqv, Imp, Not, Or, Var, eval_expr_tt
from cmbench.expr.equivalence import generate_equiv_pair, pair_diagnostics


def test_equivalent_pair_styles_are_semantically_equivalent() -> None:
    expr = Eqv(Imp(Var(0), Var(1)), Or(Not(Var(0)), Var(1)))
    rng = np.random.default_rng(3)
    for style in ("identical", "rewritten_equiv", "semantic_equiv"):
        expr_g, expected = generate_equiv_pair(expr, 2, rng, 2, "ordinary", style)
        assert expected is True
        assert np.array_equal(eval_expr_tt(expr, 2), eval_expr_tt(expr_g, 2))


def test_pair_diagnostics_preserves_expected_fields() -> None:
    expr_f = And(Var(0), Var(1))
    expr_g = And(Var(1), Var(0))
    diag = pair_diagnostics(expr_f, expr_g, 2, "rewritten_equiv", True)
    assert diag["equiv_pair_style"] == "rewritten_equiv"
    assert diag["equiv_expected"] is True
    assert diag["expr_pair_unique_var_count"] == 2
