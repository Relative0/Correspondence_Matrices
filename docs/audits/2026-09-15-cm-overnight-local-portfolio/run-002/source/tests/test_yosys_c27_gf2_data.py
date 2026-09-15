from __future__ import annotations

from collections import Counter

from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.yosys_c27_gf2_data import (
    admitted_rows, candidates, scalar_bits, select_rows,
)


def test_c27_source_adapters_have_independent_scalar_oracles():
    rows = candidates()
    assert len(rows) > 100
    for candidate in rows[:120]:
        assert reference_bits(candidate.expression, len(candidate.variable_specs)) == scalar_bits(candidate)


def test_c27_pool_supports_balanced_fresh_selection_without_prior_exclusions():
    admitted, rejected = admitted_rows(set())
    selected = select_rows(admitted)
    assert len(selected) == 48
    assert Counter(row["n_vars"] for row in selected) == {3: 12, 4: 12, 5: 12, 6: 12}
    assert rejected["oracle_mismatch"] == 0
