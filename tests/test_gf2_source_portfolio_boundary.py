from __future__ import annotations

import copy
import json
from pathlib import Path

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Or, Var, Xor
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2
from cmbench.recognition.gf2_source_portfolio import freeze_source_portfolio_policy
from cmbench.recognition.gf2_source_portfolio_boundary import (
    execute_source_portfolio_boundary,
    verify_source_portfolio_boundary_result,
)
from cmbench.recognition.portfolio import reference_bits


def fixture(tmp_path: Path):
    expression = Xor(And(Var(0), Var(1)), Or(Var(2), Var(3)))
    document = expr_to_json_dag(expression)
    bits = reference_bits(expression, 4)
    case = {
        "case_id": "c24-fixture",
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


def test_boundary_selected_advice_off_and_shadow(tmp_path):
    case, _policy, policy_path, best = fixture(tmp_path)
    for advice_enabled, shadow in ((True, False), (False, False), (True, True), (False, True)):
        result = execute_source_portfolio_boundary(
            case, policy_path, advice_enabled=advice_enabled, shadow=shadow).to_dict()
        assert result["status"] == "ok"
        assert result["best_artifact"] == best
        assert result["timings_ns"]["task_total_ns"] == sum(
            value for key, value in result["timings_ns"].items() if key != "task_total_ns")
        verify_source_portfolio_boundary_result(result, case, required_best=best)


def test_boundary_forced_source_refusal_uses_exact_fallback(tmp_path):
    case, _policy, policy_path, best = fixture(tmp_path)
    result = execute_source_portfolio_boundary(
        case, policy_path, force_source_refusal=True).to_dict()
    assert result["status"] == "ok"
    assert result["fallback_used"] is True
    assert result["selected_arm"] == "explicit_cm_exhaustive"
    verify_source_portfolio_boundary_result(result, case, required_best=best)


def test_boundary_refuses_ood_malformed_truth_and_policy(tmp_path):
    case, policy, policy_path, _best = fixture(tmp_path)
    ood = copy.deepcopy(case)
    ood["n_vars"] = 7
    assert execute_source_portfolio_boundary(ood, policy_path).status == "refused"
    malformed = copy.deepcopy(case)
    malformed["expression_v2"]["root"] = 999
    assert execute_source_portfolio_boundary(malformed, policy_path).status == "refused"
    mismatch = copy.deepcopy(case)
    mismatch["truth_bits_hex"] = hex(int(case["truth_bits_hex"], 16) ^ 1)
    assert execute_source_portfolio_boundary(mismatch, policy_path).status == "refused"
    changed = dict(policy)
    changed["selected_arm"] = "explicit_cm_exhaustive"
    policy_path.write_text(json.dumps(changed), encoding="utf-8")
    refused = execute_source_portfolio_boundary(case, policy_path).to_dict()
    assert refused["status"] == "refused"
    assert refused["reason"] == "policy_refused:ValueError"
    verify_source_portfolio_boundary_result(refused, case)

