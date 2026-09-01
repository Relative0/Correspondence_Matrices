from __future__ import annotations

import copy

import pytest

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Or, Var, Xor
from cmbench.recognition.gf2_verified_context import (
    build_verified_gf2_context,
    verify_verified_gf2_context,
)
from cmbench.recognition.portfolio import reference_bits


def case():
    expression = Xor(And(Var(0), Var(1)), Or(Var(2), Var(3)))
    return {
        "case_id": "c26-context",
        "n_vars": 4,
        "truth_bits_hex": hex(reference_bits(expression, 4)),
        "expression_v2": expr_to_json_dag(expression),
    }


def test_verified_context_binds_truth_expression_and_optional_source():
    item = case()
    packed = build_verified_gf2_context(item, require_source_packed=True)
    verify_verified_gf2_context(packed.to_dict(), item, replay_semantics=True)
    assert packed.source_packed_verified is True
    assert packed.packed_polynomial is not None
    truth_only = build_verified_gf2_context(item, require_source_packed=False)
    verify_verified_gf2_context(truth_only.to_dict(), item, replay_semantics=True)
    assert truth_only.source_packed_verified is False


def test_verified_context_tampering_and_truth_mismatch_fail_closed():
    item = case()
    context = build_verified_gf2_context(item, require_source_packed=True).to_dict()
    changed = copy.deepcopy(context)
    changed["truth_bits_hex"] = hex(int(changed["truth_bits_hex"], 16) ^ 1)
    with pytest.raises(ValueError):
        verify_verified_gf2_context(changed, item)
    mismatch = copy.deepcopy(item)
    mismatch["truth_bits_hex"] = hex(int(mismatch["truth_bits_hex"], 16) ^ 1)
    with pytest.raises(ValueError):
        build_verified_gf2_context(mismatch, require_source_packed=True)
