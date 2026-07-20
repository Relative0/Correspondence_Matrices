import numpy as np

from cmbench.expr.families import generate_expression_family, expression_family_diagnostics


def test_expression_family_generation_and_diagnostics() -> None:
    family = generate_expression_family(
        3,
        np.random.default_rng(4),
        2,
        "ordinary",
        family_size=4,
        variant_style="composition_mix",
    )
    assert len(family["variants"]) == 4
    diag = expression_family_diagnostics(
        family,
        3,
        family_id="fam",
        variant_style="composition_mix",
        mutation_rate=0.15,
    )
    assert diag["family_id"] == "fam"
    assert diag["family_size"] == 4
    assert "family_total_subtree_hashes" in diag
    assert "family_unique_subtree_hashes" in diag
