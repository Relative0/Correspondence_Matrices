from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Or, Var, Xor
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2
from cmbench.recognition.gf2_source_portfolio import freeze_source_portfolio_policy
from cmbench.recognition.gf2_source_portfolio_session import (
    ResidentSourcePortfolioSession,
    verify_resident_query_result,
)
from cmbench.recognition.portfolio import reference_bits


def fixture(tmp_path: Path):
    expression = Xor(And(Var(0), Var(1)), Or(Var(2), Var(3)))
    document = expr_to_json_dag(expression)
    bits = reference_bits(expression, 4)
    case = {
        "case_id": "c25-fixture",
        "n_vars": 4,
        "truth_bits_hex": hex(bits),
        "expression_v2": document,
    }
    policy = freeze_source_portfolio_policy(
        c21_manifest_sha256="a" * 64, c21_dataset_sha256="b" * 64)
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    best = analyze_exact_gf2(bits, 4).best
    return case, policy, policy_path, best.to_dict() if best else None


def test_resident_session_reuses_compiled_width_and_enforces_limit(tmp_path):
    case, policy, policy_path, best = fixture(tmp_path)
    session = ResidentSourcePortfolioSession("resident", policy_path, max_queries=2)
    first = session.execute(case).to_dict()
    second = session.execute(case).to_dict()
    refused = session.execute(case).to_dict()
    assert first["compile_cache_hit"] is False
    assert second["compile_cache_hit"] is True
    assert refused["status"] == "refused"
    assert session.successful_queries == 2
    assert session.refused_queries == 1
    for result in (first, second):
        verify_resident_query_result(
            result, case, policy_sha256=policy["policy_sha256"], required_best=best)
    verify_resident_query_result(refused, case, policy_sha256=policy["policy_sha256"])
    closed = session.close()
    assert closed["closed"] is True
    assert closed["compiled_widths"] == []


def test_resident_session_fallback_advice_off_and_query_refusal(tmp_path):
    case, policy, policy_path, best = fixture(tmp_path)
    selected = ResidentSourcePortfolioSession("selected", policy_path, max_queries=3)
    fallback = selected.execute(case, force_source_refusal=True).to_dict()
    assert fallback["fallback_used"] is True
    assert fallback["selected_arm"] == "explicit_cm_exhaustive"
    verify_resident_query_result(
        fallback, case, policy_sha256=policy["policy_sha256"], required_best=best)
    mismatch = copy.deepcopy(case)
    mismatch["truth_bits_hex"] = hex(int(case["truth_bits_hex"], 16) ^ 1)
    refused = selected.execute(mismatch).to_dict()
    assert refused["status"] == "refused"
    verify_resident_query_result(refused, mismatch, policy_sha256=policy["policy_sha256"])

    advice_off = ResidentSourcePortfolioSession(
        "off", policy_path, advice_enabled=False, max_queries=1)
    result = advice_off.execute(case).to_dict()
    assert result["selected_arm"] == "explicit_cm_exhaustive"
    verify_resident_query_result(
        result, case, policy_sha256=policy["policy_sha256"], required_best=best)


def test_resident_session_rejects_tampered_policy(tmp_path):
    _case, policy, policy_path, _best = fixture(tmp_path)
    changed = dict(policy)
    changed["selected_arm"] = "explicit_cm_exhaustive"
    policy_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError):
        ResidentSourcePortfolioSession("bad", policy_path)
