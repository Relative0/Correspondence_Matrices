from __future__ import annotations

import copy

import pytest

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cmbench.comparative.gf2_multi_root import expressions_to_multi_root_dag
from cmbench.comparative.gf2_multi_root_python import (
    compile_python_multi_root_arena,
    evaluate_separate_python_roots,
)
from cmbench.expr.eval import eval_expr_assignment


def scalar_residual(expr, n_vars, fixed, remaining):
    bits = 0
    for row in range(1 << len(remaining)):
        assignment = dict(fixed)
        assignment.update(
            {
                variable: (row >> (len(remaining) - position - 1)) & 1
                for position, variable in enumerate(remaining)
            }
        )
        bits |= eval_expr_assignment(expr, assignment) << row
    assert set(assignment) == {f"x{index}" for index in range(n_vars)}
    return bits


def roots():
    shared = Xor(Var(0), Var(1))
    return (
        And(shared, Var(2)),
        Or(shared, Not(Var(3))),
        Eqv(Imp(Var(0), Var(2)), shared),
    )


def test_python_union_and_separate_roots_match_independent_scalar_oracle() -> None:
    expressions = roots()
    union = compile_python_multi_root_arena(
        expressions_to_multi_root_dag(expressions), variable_count=4
    )
    documents = tuple(expr_to_json_dag(expr) for expr in expressions)
    fixed = {"x1": 1, "x3": 0}
    remaining = ("x2", "x0")
    expected = tuple(
        scalar_residual(expr, 4, fixed, remaining) for expr in expressions
    )

    assert union.root_count == 3
    assert union.evaluate(fixed, remaining) == expected
    assert evaluate_separate_python_roots(
        documents,
        variable_count=4,
        fixed=fixed,
        remaining=remaining,
    ) == expected


def test_python_multi_root_validates_dag_and_restriction_partitions() -> None:
    document = expressions_to_multi_root_dag(roots())
    arena = compile_python_multi_root_arena(document, variable_count=4)

    for fixed, remaining in (
        ({"x0": 1}, ("x0", "x1", "x2", "x3")),
        ({"x0": 2}, ("x1", "x2", "x3")),
        ({"x0": 1}, ("x1", "x2")),
        ({}, ("x0", "x0", "x1", "x2", "x3")),
    ):
        with pytest.raises(ValueError):
            arena.evaluate(fixed, remaining)

    invalid_documents = []
    unknown = copy.deepcopy(document)
    unknown["nodes"][-1]["op"] = "nand"
    invalid_documents.append(unknown)
    forward = copy.deepcopy(document)
    forward["nodes"][1] = {"op": "not", "a": 1}
    invalid_documents.append(forward)
    duplicate = copy.deepcopy(document)
    duplicate["roots"][1] = duplicate["roots"][0]
    invalid_documents.append(duplicate)
    both_roots = copy.deepcopy(document)
    both_roots["root"] = both_roots["roots"][0]
    invalid_documents.append(both_roots)

    for invalid in invalid_documents:
        with pytest.raises(ValueError):
            compile_python_multi_root_arena(invalid, variable_count=4)
