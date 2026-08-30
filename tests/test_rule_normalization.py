from __future__ import annotations

import pytest

from cm_exprlib import And, Var
from cmbench.recognition.normalization import (
    NormalizationRefusal, normalize_to_fixpoint, operator_count,
)
from cmbench.recognition.rule_pack import (
    FACTOR_RULE_ID, OR_RULE_ID, aig_or_expr, compile_rule_pack, prove_rule_pack_v2,
)


def test_fixpoint_exposes_and_applies_factoring_on_second_productive_pass() -> None:
    a, b, c = Var(0), Var(1), Var(2)
    source = aig_or_expr(And(a, b), And(a, c))
    matcher = compile_rule_pack(prove_rule_pack_v2())

    normalized = normalize_to_fixpoint(matcher, source, 3)

    assert normalized.productive_passes == 2
    assert normalized.convergence_passes == 3
    assert normalized.applications_by_rule[OR_RULE_ID] == 1
    assert normalized.applications_by_rule[FACTOR_RULE_ID] == 1
    assert normalized.operator_count_after < normalized.operator_count_before
    assert normalized.termination_reason == "proved_rule_fixpoint"


def test_fixpoint_refuses_declared_overlap_when_requested() -> None:
    a, b = Var(0), Var(1)
    matcher = compile_rule_pack(prove_rule_pack_v2())
    from cmbench.recognition.proved_rules import aig_xor_expr

    with pytest.raises(NormalizationRefusal, match="overlap"):
        normalize_to_fixpoint(matcher, aig_xor_expr(a, b), 2, conflict_policy="refuse")


def test_fixpoint_refuses_insufficient_pass_budget_instead_of_returning_partial() -> None:
    a, b, c = Var(0), Var(1), Var(2)
    source = aig_or_expr(And(a, b), And(a, c))
    matcher = compile_rule_pack(prove_rule_pack_v2())

    with pytest.raises(NormalizationRefusal, match="pass budget"):
        normalize_to_fixpoint(matcher, source, 3, max_passes=1)


def test_operator_count_expands_shared_dag_occurrences_for_ast_measure() -> None:
    shared = And(Var(0), Var(1))
    assert operator_count(And(shared, shared)) == 3
