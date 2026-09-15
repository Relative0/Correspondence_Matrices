from __future__ import annotations

from itertools import product

import numpy as np

from cm_build import compile_expr_to_cm
from cm_build_pair import compile_expr_to_cm_pair, compile_expr_to_cm_pair_token
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, random_expr
from cm_token import (
    TOK,
    cm_align_signed_operands,
    cm_not,
    cm_rot90,
    cm_rot270,
    cm_token_value,
)


ASSIGNMENTS = ((1, 1), (1, 0), (0, 1), (0, 0))
OP_CLASSES = (And, Or, Xor, Imp, Eqv)


def _source_value(
    token: int,
    x: int,
    y: int,
    *,
    swapped: bool,
    negate_first: bool,
    negate_second: bool,
) -> int:
    first, second = (y, x) if swapped else (x, y)
    if negate_first:
        first = 1 - first
    if negate_second:
        second = 1 - second
    return cm_token_value(token, first, second)


def _literal(var: Var, negated: bool):
    return Not(var) if negated else var


def test_signed_token_alignment_is_exhaustive() -> None:
    for token in range(16):
        for swapped, negate_first, negate_second in product((False, True), repeat=3):
            aligned = cm_align_signed_operands(
                token,
                swapped=swapped,
                negate_first=negate_first,
                negate_second=negate_second,
            )
            for x, y in ASSIGNMENTS:
                assert cm_token_value(aligned, x, y) == _source_value(
                    token,
                    x,
                    y,
                    swapped=swapped,
                    negate_first=negate_first,
                    negate_second=negate_second,
                )


def test_pair_compiler_aligns_every_signed_binary_operator() -> None:
    row = Var(0)
    col = Var(1)
    for op_class in OP_CLASSES:
        for swapped, negate_first, negate_second in product((False, True), repeat=3):
            first_var, second_var = (col, row) if swapped else (row, col)
            expr = op_class(
                _literal(first_var, negate_first),
                _literal(second_var, negate_second),
            )
            pair_matrix, metrics = compile_expr_to_cm_pair(
                expr, ["x0"], ["x1"], fixed={}, output_budget=None
            )
            eager_matrix = compile_expr_to_cm(
                expr, ["x0"], ["x1"], fixed={}, output_budget=None
            )
            assert np.array_equal(pair_matrix, eager_matrix)
            assert metrics["primitive_pair_tokens"] == 1
            assert metrics["direct_pair_retabulations"] == 0
            assert metrics["signed_operand_alignments"] == int(
                swapped or negate_first or negate_second
            )


def test_pair_compiler_fuses_aligned_compound_operators() -> None:
    row = Var(0)
    col = Var(1)
    left = Imp(Not(col), row)
    right = Xor(Not(row), col)
    expr = Or(left, right)

    pair_matrix, metrics = compile_expr_to_cm_pair(
        expr, ["x0"], ["x1"], fixed={}, output_budget=None
    )
    eager_matrix = compile_expr_to_cm(
        expr, ["x0"], ["x1"], fixed={}, output_budget=None
    )

    assert np.array_equal(pair_matrix, eager_matrix)
    assert metrics["primitive_pair_tokens"] == 2
    assert metrics["signed_operand_alignments"] == 2
    assert metrics["token_fusions"] == 1
    assert metrics["direct_pair_retabulations"] == 0
    assert 0.0 <= metrics["pairable_ratio"] <= 1.0
    assert metrics["root_outcome"] == "pure_structural"


def test_pair_compiler_retains_four_assignment_fallback() -> None:
    row = Var(0)
    col = Var(1)
    expr = Xor(And(row, col), row)

    pair_matrix, metrics = compile_expr_to_cm_pair(
        expr, ["x0"], ["x1"], fixed={}, output_budget=None
    )
    eager_matrix = compile_expr_to_cm(
        expr, ["x0"], ["x1"], fixed={}, output_budget=None
    )

    assert np.array_equal(pair_matrix, eager_matrix)
    assert metrics["token_fusions"] == 0
    assert metrics["direct_pair_retabulations"] == 1
    assert metrics["root_outcome"] == "full_retabulation"


def test_pair_compiler_reports_hybrid_and_pure_structural_outcomes() -> None:
    row = Var(0)
    col = Var(1)
    structural_child = Imp(row, col)
    retabulated_child = Xor(And(row, col), row)
    expr = Or(structural_child, retabulated_child)

    hybrid, hybrid_metrics = compile_expr_to_cm_pair_token(
        expr, ["x0"], ["x1"], fixed={}, strategy="hybrid"
    )
    pure, pure_metrics = compile_expr_to_cm_pair_token(
        expr, ["x0"], ["x1"], fixed={}, strategy="pure_structural"
    )
    retabulated, retabulated_metrics = compile_expr_to_cm_pair_token(
        expr, ["x0"], ["x1"], fixed={}, strategy="retabulate"
    )

    assert hybrid is not None
    assert retabulated is not None
    assert hybrid.token == retabulated.token
    assert hybrid_metrics["root_outcome"] == "hybrid_pair"
    assert hybrid_metrics["root_hybrid_pair"] == 1
    assert hybrid_metrics["direct_pair_retabulations"] >= 1
    assert pure is None
    assert pure_metrics["root_outcome"] == "ordinary_fallback"
    assert pure_metrics["direct_pair_retabulations"] == 0
    assert retabulated_metrics["root_outcome"] == "full_retabulation"


def test_pair_metrics_separate_occurrences_unique_nodes_and_scans() -> None:
    signed = Not(Not(Not(Var(0))))
    shared = Xor(signed, Var(1))
    expr = Or(shared, shared)

    _compiled, metrics = compile_expr_to_cm_pair_token(
        expr, ["x0"], ["x1"], fixed={}, strategy="pure_structural"
    )

    assert metrics["ast_occurrences"] > metrics["unique_object_nodes"]
    assert metrics["compiler_calls"] > 0
    assert metrics["nodes_total"] == metrics["compiler_calls"]
    assert metrics["pairable_ratio"] == (
        metrics["pair_collapses"] / metrics["compiler_calls"]
    )
    assert metrics["negation_nodes_scanned"] >= 3


def test_known_operator_tokens_remain_true_first() -> None:
    assert TOK["AND"] == 0b1000
    assert TOK["OR"] == 0b1110
    assert TOK["XOR"] == 0b0110


def test_xor_xnor_rotation_and_impax_superposition() -> None:
    assert cm_rot90(TOK["XNOR"]) == TOK["XOR"]
    assert cm_rot270(TOK["XNOR"]) == TOK["XOR"]
    assert cm_not(TOK["XNOR"]) == TOK["XOR"]
    assert TOK["XNOR"] ^ TOK["XOR"] == TOK["TOP"]


def test_pair_compiler_matches_eager_on_random_two_variable_formulas() -> None:
    rng = np.random.default_rng(20260914)
    for _ in range(250):
        expr = random_expr(2, rng, max_depth=6, p_unary=0.3)
        pair_matrix, _ = compile_expr_to_cm_pair(
            expr, ["x0"], ["x1"], fixed={}, output_budget=None
        )
        eager_matrix = compile_expr_to_cm(
            expr, ["x0"], ["x1"], fixed={}, output_budget=None
        )
        assert np.array_equal(pair_matrix, eager_matrix)


def test_pair_compiler_does_not_mutate_caller_inputs() -> None:
    row = Var(0)
    col = Var(1)
    expr = Or(Imp(Not(col), row), Xor(Not(row), col))
    rows = ["x0"]
    columns = ["x1"]
    fixed: dict[str, int] = {}
    rows_before = list(rows)
    columns_before = list(columns)
    fixed_before = dict(fixed)

    _matrix, _metrics = compile_expr_to_cm_pair(
        expr, rows, columns, fixed=fixed, output_budget=None
    )

    assert rows == rows_before
    assert columns == columns_before
    assert fixed == fixed_before


def test_token_only_api_separates_compilation_from_dense_output() -> None:
    row = Var(0)
    col = Var(1)
    expr = Or(Imp(Not(col), row), Xor(Not(row), col))

    compiled, metrics = compile_expr_to_cm_pair_token(
        expr, ["x0"], ["x1"], fixed={}
    )

    assert compiled is not None
    assert compiled.row_variable == "x0"
    assert compiled.column_variable == "x1"
    assert compiled.token == TOK["TOP"]
    assert metrics["token_fusions"] == 1
    assert metrics["direct_pair_retabulations"] == 0


def test_token_only_api_reports_unsupported_multi_pair_expression() -> None:
    expr = Or(And(Var(0), Var(2)), Xor(Var(1), Var(3)))
    compiled, metrics = compile_expr_to_cm_pair_token(
        expr, ["x0", "x1"], ["x2", "x3"], fixed={}
    )

    assert compiled is None
    assert metrics["token_fusions"] == 0


def test_dense_fallback_does_not_mutate_caller_inputs() -> None:
    expr = Or(And(Var(0), Var(2)), Xor(Var(1), Var(3)))
    rows = ["x0", "x1"]
    columns = ["x2", "x3"]
    fixed: dict[str, int] = {}
    rows_before = list(rows)
    columns_before = list(columns)
    fixed_before = dict(fixed)

    pair_matrix, metrics = compile_expr_to_cm_pair(
        expr, rows, columns, fixed=fixed, output_budget=None
    )
    eager_matrix = compile_expr_to_cm(
        expr, rows, columns, fixed=fixed, output_budget=None
    )

    assert np.array_equal(pair_matrix, eager_matrix)
    assert metrics["pair_collapses"] == 2
    assert rows == rows_before
    assert columns == columns_before
    assert fixed == fixed_before


def test_retabulation_ablation_matches_structural_token() -> None:
    row = Var(0)
    col = Var(1)
    expr = Or(Imp(Not(col), row), Xor(Not(row), col))

    structural, structural_metrics = compile_expr_to_cm_pair_token(
        expr, ["x0"], ["x1"], fixed={}, strategy="pure_structural"
    )
    retabulated, retabulated_metrics = compile_expr_to_cm_pair_token(
        expr, ["x0"], ["x1"], fixed={}, strategy="retabulate"
    )

    assert retabulated == structural
    assert structural_metrics["token_fusions"] == 1
    assert structural_metrics["root_outcome"] == "pure_structural"
    assert retabulated_metrics["token_fusions"] == 0
    assert retabulated_metrics["primitive_pair_tokens"] == 0
    assert retabulated_metrics["direct_pair_retabulations"] == 1
    assert retabulated_metrics["retabulation_only_mode"] == 1
    assert retabulated_metrics["root_outcome"] == "full_retabulation"


def test_dense_pair_api_exposes_retabulation_ablation() -> None:
    expr = Eqv(And(Var(0), Var(1)), Or(Not(Var(0)), Var(1)))

    structural, _ = compile_expr_to_cm_pair(
        expr, ["x0"], ["x1"], fixed={}, output_budget=None
    )
    retabulated, metrics = compile_expr_to_cm_pair(
        expr,
        ["x0"],
        ["x1"],
        fixed={},
        output_budget=None,
        pair_strategy="retabulate",
    )

    assert np.array_equal(retabulated, structural)
    assert metrics["retabulation_only_mode"] == 1


def test_token_only_api_rejects_unknown_strategy() -> None:
    with np.testing.assert_raises_regex(ValueError, "strategy must be"):
        compile_expr_to_cm_pair_token(
            And(Var(0), Var(1)),
            ["x0"],
            ["x1"],
            fixed={},
            strategy="unknown",  # type: ignore[arg-type]
        )


def test_legacy_structural_strategy_is_reported_as_hybrid_alias() -> None:
    compiled, metrics = compile_expr_to_cm_pair_token(
        And(Var(0), Var(1)),
        ["x0"],
        ["x1"],
        fixed={},
        strategy="structural",
    )
    assert compiled is not None
    assert metrics["legacy_strategy_alias"] == 1
    assert metrics["root_outcome"] == "pure_structural"


def test_pair_compiler_rejects_overlapping_axis_layouts() -> None:
    with np.testing.assert_raises_regex(ValueError, "disjoint row and column"):
        compile_expr_to_cm_pair_token(
            And(Var(0), Var(0)), ["x0"], ["x0"], fixed={}
        )


def test_pair_compiler_rejects_duplicate_axis_names() -> None:
    with np.testing.assert_raises_regex(ValueError, "row layout R contains duplicate"):
        compile_expr_to_cm_pair_token(
            And(Var(0), Var(1)), ["x0", "x0"], ["x1"], fixed={}
        )
    with np.testing.assert_raises_regex(
        ValueError, "column layout C contains duplicate"
    ):
        compile_expr_to_cm_pair_token(
            And(Var(0), Var(1)), ["x0"], ["x1", "x1"], fixed={}
        )


def test_repeated_variable_is_not_misclassified_as_a_pair() -> None:
    compiled, metrics = compile_expr_to_cm_pair_token(
        Xor(Var(0), Var(0)), ["x0"], ["x1"], fixed={}
    )

    assert compiled is None
    assert metrics["pair_collapses"] == 0
