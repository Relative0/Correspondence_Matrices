import numpy as np

from cmbench.config import BenchmarkConfig
from cmbench.expr.generators import generate_benchmark_expr, random_expr_for_style


def test_generators_return_expressions_for_all_styles() -> None:
    styles = [
        "ordinary",
        "broad",
        "low-reuse",
        "anti-reduction",
        "balanced_all_vars",
        "xor_heavy",
        "and_or_not",
        "implication_heavy",
        "mixed_no_constants",
        "transform_pairs",
    ]
    rng = np.random.default_rng(1)
    for style in styles:
        assert random_expr_for_style(3, rng, 2, style) is not None


def test_generate_benchmark_expr_can_return_tt_ref() -> None:
    cfg = BenchmarkConfig(sizes=(3,), trials=1, seed=0, max_depth=2)
    expr, diag, tt_ref = generate_benchmark_expr(
        3,
        np.random.default_rng(2),
        2,
        "ordinary",
        True,
        config=cfg,
        return_tt_ref=True,
    )
    assert expr is not None
    assert tt_ref is not None
    assert tt_ref.shape == (8,)
    assert "expr_structural_hash_if_available" in diag
