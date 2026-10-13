from __future__ import annotations

import pytest

from cmbench.biology_bnet import evaluate_bnet, parse_bnet, scalar_fixed_point_count
from cmbench.backends.projected_count import (
    ProjectedCNF,
    parse_counting_dimacs,
    pysat_projected_count,
    scalar_projected_count,
)


def test_bnet_parser_preserves_precedence_constants_and_regulators():
    rows = parse_bnet("targets,factors\nout, a | b & !c\nzero, 0\n")
    assert rows[0].regulators == ("a", "b", "c")
    assert evaluate_bnet(rows[0].expression, {"a": 0, "b": 1, "c": 0}) is True
    assert evaluate_bnet(rows[0].expression, {"a": 0, "b": 1, "c": 1}) is False
    assert evaluate_bnet(rows[1].expression, {}) is False


def test_bnet_scalar_fixed_points():
    rows = parse_bnet("targets,factors\na, a\nb, !a\n")
    assert scalar_fixed_point_count(rows) == 2


@pytest.mark.parametrize("bad", ["x, a", "targets,factors\nx, a + b\n", "targets,factors\nx, (a\n"])
def test_bnet_parser_fails_closed(bad):
    with pytest.raises(ValueError):
        parse_bnet(bad)


def test_exact_independent_support_is_not_projection():
    text = "p cnf 3 1\nc ind 1 0\n1 0\n"
    exact = parse_counting_dimacs(text, mode="exact")
    projected = parse_counting_dimacs(text, mode="projected")
    assert scalar_projected_count(exact) == pysat_projected_count(exact) == 4
    assert scalar_projected_count(projected) == pysat_projected_count(projected) == 1


def test_projected_hidden_multiplicity_empty_projection_and_contradiction():
    hidden = parse_counting_dimacs("p cnf 3 1\nc ind 1 0\n2 3 0\n", mode="projected")
    assert scalar_projected_count(hidden) == pysat_projected_count(hidden) == 2
    empty = ProjectedCNF(1, ((1,),), (), "projected")
    assert scalar_projected_count(empty) == pysat_projected_count(empty) == 1
    contradiction = ProjectedCNF(1, ((1,), (-1,)), (), "projected")
    assert scalar_projected_count(contradiction) == pysat_projected_count(contradiction) == 0
