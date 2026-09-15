from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Or, Var, Xor
from cmbench.recognition import gf2_verified_context as context_module
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2
from cmbench.recognition.gf2_source_portfolio import freeze_source_portfolio_policy
from cmbench.recognition.gf2_support_aware_policy import freeze_support_aware_policy
from cmbench.recognition.gf2_support_aware_session import (
    SupportAwareGF2Session, verify_support_aware_query_result,
)
from cmbench.recognition.gf2_verified_context import build_verified_gf2_context
from cmbench.recognition.portfolio import reference_bits


def case(n_vars: int) -> dict:
    expression = Xor(And(Var(0), Var(1)), Or(Var(2), Var(3)))
    if n_vars == 5:
        expression = Xor(expression, Var(4))
    document = expr_to_json_dag(expression)
    bits = reference_bits(expression, n_vars)
    return {
        "case_id": f"c27-fixture-n{n_vars}",
        "n_vars": n_vars,
        "truth_bits_hex": hex(bits),
        "expression_v2": document,
    }


def policies(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    c22 = freeze_source_portfolio_policy(
        c21_manifest_sha256="a" * 64, c21_dataset_sha256="b" * 64)
    c27 = freeze_support_aware_policy(
        c26_manifest_sha256="c" * 64, c26_result_sha256="d" * 64)
    c22_path, c27_path = tmp_path / "c22.json", tmp_path / "c27.json"
    c22_path.write_text(json.dumps(c22), encoding="utf-8")
    c27_path.write_text(json.dumps(c27), encoding="utf-8")
    return c22, c27, c22_path, c27_path


def test_support_aware_session_selects_truth_for_n4_and_packed_for_n5(tmp_path):
    c22, c27, c22_path, c27_path = policies(tmp_path)
    session = SupportAwareGF2Session(
        "support-aware", c27_path, c22_path, max_queries=2)
    tiny, large = case(4), case(5)
    tiny_result = session.execute(tiny).to_dict()
    large_result = session.execute(large).to_dict()
    assert tiny_result["selected_arm"] == "verified_truth_screened"
    assert large_result["selected_arm"] == "source_packed_anf_screened"
    tiny_context = build_verified_gf2_context(tiny, require_source_packed=False)
    large_context = build_verified_gf2_context(large, require_source_packed=True)
    assert tiny_context.source_packed_verified is False
    assert large_context.source_packed_verified is True
    for result, context, item in (
        (tiny_result, tiny_context, tiny), (large_result, large_context, large),
    ):
        best = analyze_exact_gf2(
            context.truth_bits, item["n_vars"]).best
        verify_support_aware_query_result(
            result,
            context,
            c27_policy_sha256=c27["policy_sha256"],
            c22_policy_sha256=c22["policy_sha256"],
            required_best=best.to_dict() if best else None,
        )


def test_support_aware_session_evaluates_once_reuses_plan_and_falls_back(
        tmp_path, monkeypatch):
    c22, c27, c22_path, c27_path = policies(tmp_path)
    item = case(4)
    calls = 0
    original = context_module.reference_bits

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(context_module, "reference_bits", counted)
    session = SupportAwareGF2Session("support-aware", c27_path, c22_path, max_queries=3)
    first = session.execute(item).to_dict()
    second = session.execute(item).to_dict()
    fallback = session.execute(item, force_selected_refusal=True).to_dict()
    assert calls == 3
    assert first["plan_cache_hit"] is False
    assert second["plan_cache_hit"] is True
    assert fallback["selected_arm"] == "explicit_cm_exhaustive"
    assert fallback["requested_arm"] == "verified_truth_screened"
    assert fallback["fallback_used"] is True
    context = build_verified_gf2_context(item, require_source_packed=False)
    best = analyze_exact_gf2(context.truth_bits, 4).best
    verify_support_aware_query_result(
        fallback,
        context,
        c27_policy_sha256=c27["policy_sha256"],
        c22_policy_sha256=c22["policy_sha256"],
        required_best=best.to_dict() if best else None,
    )


def test_support_aware_session_refusals_and_tampered_policies(tmp_path):
    _c22, _c27, c22_path, c27_path = policies(tmp_path)
    item = case(4)
    session = SupportAwareGF2Session("support-aware", c27_path, c22_path, max_queries=1)
    mismatch = copy.deepcopy(item)
    mismatch["truth_bits_hex"] = hex(int(item["truth_bits_hex"], 16) ^ 1)
    assert session.execute(mismatch).status == "refused"
    assert session.execute(item).status == "ok"
    assert session.execute(item).status == "refused"
    session.close()
    assert session.execute(item).status == "refused"

    changed = json.loads(c27_path.read_text(encoding="utf-8"))
    changed["tiny_support_max_n_vars"] = 3
    c27_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError):
        SupportAwareGF2Session("bad-c27", c27_path, c22_path)

    _c22, _c27, c22_path, c27_path = policies(tmp_path / "second")
    changed = json.loads(c22_path.read_text(encoding="utf-8"))
    changed["selected_arm"] = "explicit_cm_exhaustive"
    c22_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError):
        SupportAwareGF2Session("bad-c22", c27_path, c22_path)
