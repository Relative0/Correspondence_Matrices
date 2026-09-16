from itertools import product

import pytest

from bitset_backend import build_bitset_env, eval_expr_bitset
from cm_exprlib import And, Imp, Not, Or, Var, Xor
from cmbench.recognition import cut_fusion
from cmbench.recognition.cut_fusion import optimize_cut_fusion, template_document, template_table
from cmbench.recognition.features import IneligibleExpression


def _positive_one():
    a = And(Var(0), Var(1))
    b = Xor(Var(1), Var(2))
    return Xor(And(a, b), Or(a, b))


def _positive_two():
    a = And(Var(0), Var(1))
    b = Xor(Var(1), Var(2))
    return And(Imp(a, b), Imp(b, a))


def test_template_table_covers_and_is_stable():
    table, digest = template_table()
    assert set(table) == set(range(16))
    assert template_document()["payload_sha256"] == digest
    assert len(digest) == 64


@pytest.mark.parametrize("source", [_positive_one(), _positive_two()])
def test_compound_operand_fusion_is_exact_and_accepted(source):
    result = optimize_cut_fusion(source, 3)
    assert result.accepted
    assert result.selected_rewrites == 1
    assert result.proposed_cse_metrics["executed_bigint_ops"] <= (
        result.baseline_cse_metrics["executed_bigint_ops"] - 2)
    assert eval_expr_bitset(source, build_bitset_env(("x0", "x1", "x2"))) == eval_expr_bitset(
        result.result, build_bitset_env(("x0", "x1", "x2")))


def test_alias_complement_and_axis_order_are_exact():
    a = Xor(Var(0), Var(1))
    cases = [
        Xor(And(a, a), Or(a, a)),
        Xor(And(a, Not(a)), Or(a, Not(a))),
        Xor(And(And(Var(0), Var(2)), Xor(Var(1), Var(2))),
            Or(And(Var(0), Var(2)), Xor(Var(1), Var(2)))),
    ]
    env = build_bitset_env(("x2", "x0", "x1"))
    for source in cases:
        result = optimize_cut_fusion(source, 3)
        assert eval_expr_bitset(source, env) == eval_expr_bitset(result.result, env)


def test_shared_interior_is_not_deleted_unsafely():
    a = And(Var(0), Var(1))
    b = Xor(Var(1), Var(2))
    shared = And(a, b)
    shell = Xor(shared, Or(a, b))
    source = Or(shell, shared)
    result = optimize_cut_fusion(source, 3)
    env = build_bitset_env(("x0", "x1", "x2"))
    assert eval_expr_bitset(source, env) == eval_expr_bitset(result.result, env)
    assert all(row["root_postorder"] != 5 for row in result.selected)


def test_invalid_basis_is_refused_without_rewrite():
    with pytest.raises(IneligibleExpression, match="outside declared"):
        optimize_cut_fusion(And(Var(0), Var(2)), 2)


def test_deterministic_diagnostics():
    first = optimize_cut_fusion(_positive_one(), 3).to_document()
    second = optimize_cut_fusion(_positive_one(), 3).to_document()
    assert first == second


def test_structurally_equal_distinct_operands_and_dead_axis_are_exact():
    left = And(Var(0), Var(1))
    right = And(Var(0), Var(1))
    source = Xor(And(left, right), Or(left, right))
    result = optimize_cut_fusion(source, 4)
    env = build_bitset_env(("x0", "x1", "x2", "x3"))
    assert eval_expr_bitset(source, env) == eval_expr_bitset(result.result, env)


def test_token_work_limit_falls_back_without_partial_result(monkeypatch):
    source = _positive_one()
    monkeypatch.setattr(cut_fusion, "MAX_CUT_PAIRS", 0)
    result = optimize_cut_fusion(source, 3)
    assert not result.accepted
    assert result.result is source
    assert result.fallback_reason == "token_combination_limit"


def test_identity_node_limit_is_refused():
    level = [Var(index % 16) for index in range(2049)]
    while len(level) > 1:
        next_level = []
        for index in range(0, len(level), 2):
            next_level.append(level[index] if index + 1 == len(level)
                              else And(level[index], level[index + 1]))
        level = next_level
    with pytest.raises(IneligibleExpression, match="identity-node limit"):
        optimize_cut_fusion(level[0], 16)


def test_unsupported_node_is_refused():
    class Unknown:
        pass
    with pytest.raises(IneligibleExpression, match="unsupported"):
        optimize_cut_fusion(Unknown(), 1)
