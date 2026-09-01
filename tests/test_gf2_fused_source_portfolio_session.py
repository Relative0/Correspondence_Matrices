from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Or, Var, Xor
from cmbench.recognition import gf2_verified_context as context_module
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2
from cmbench.recognition.gf2_fused_source_portfolio_session import (
    FusedResidentSourcePortfolioSession,
    verify_fused_resident_query_result,
)
from cmbench.recognition.gf2_source_portfolio import freeze_source_portfolio_policy
from cmbench.recognition.gf2_verified_context import build_verified_gf2_context
from cmbench.recognition.portfolio import reference_bits


def fixture(tmp_path: Path):
    expression = Xor(And(Var(0), Var(1)), Or(Var(2), Var(3)))
    document = expr_to_json_dag(expression)
    bits = reference_bits(expression, 4)
    case = {"case_id": "c26-fixture", "n_vars": 4,
            "truth_bits_hex": hex(bits), "expression_v2": document}
    policy = freeze_source_portfolio_policy(
        c21_manifest_sha256="a" * 64, c21_dataset_sha256="b" * 64)
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    best = analyze_exact_gf2(bits, 4).best
    return case, policy, policy_path, best.to_dict() if best else None


def test_fused_session_evaluates_expression_once_and_reuses_plan(tmp_path, monkeypatch):
    case, policy, policy_path, best = fixture(tmp_path)
    calls = 0
    original = context_module.reference_bits

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(context_module, "reference_bits", counted)
    session = FusedResidentSourcePortfolioSession("fused", policy_path, max_queries=2)
    first = session.execute(case).to_dict()
    second = session.execute(case).to_dict()
    assert calls == 2
    assert first["plan_cache_hit"] is False
    assert second["plan_cache_hit"] is True
    context = build_verified_gf2_context(case, require_source_packed=True)
    for result in (first, second):
        verify_fused_resident_query_result(
            result, context, policy_sha256=policy["policy_sha256"], required_best=best)


def test_fused_session_exact_fallback_and_refusals(tmp_path):
    case, policy, policy_path, best = fixture(tmp_path)
    session = FusedResidentSourcePortfolioSession("fused", policy_path, max_queries=2)
    result = session.execute(case, force_source_refusal=True).to_dict()
    context = build_verified_gf2_context(case, require_source_packed=False)
    assert result["selected_arm"] == "explicit_cm_exhaustive"
    assert result["fallback_used"] is True
    verify_fused_resident_query_result(
        result, context, policy_sha256=policy["policy_sha256"], required_best=best)
    mismatch = copy.deepcopy(case)
    mismatch["truth_bits_hex"] = hex(int(case["truth_bits_hex"], 16) ^ 1)
    refused = session.execute(mismatch).to_dict()
    verify_fused_resident_query_result(
        refused, None, policy_sha256=policy["policy_sha256"])
    assert refused["status"] == "refused"
    session.close()
    assert session.execute(case).status == "refused"


def test_fused_session_rejects_tampered_policy(tmp_path):
    _case, policy, policy_path, _best = fixture(tmp_path)
    changed = dict(policy)
    changed["selected_arm"] = "explicit_cm_exhaustive"
    policy_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError):
        FusedResidentSourcePortfolioSession("bad", policy_path)
