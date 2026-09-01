from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import pytest

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Or, Var, Xor
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2
from cmbench.recognition.gf2_source_portfolio import (
    EXHAUSTIVE,
    SOURCE_PACKED_SCREENED,
    compile_source_portfolio,
    freeze_source_portfolio_policy,
    load_source_portfolio_policy,
    save_source_portfolio_policy,
    verify_source_portfolio_execution,
)
from cmbench.recognition.gf2_task_dispatcher import GF2DecompositionTask
from cmbench.recognition.portfolio import reference_bits


def fixture():
    expression = Xor(And(Var(0), Var(1)), Or(Var(2), Var(3)))
    document = expr_to_json_dag(expression)
    bits = reference_bits(expression, 4)
    expected = analyze_exact_gf2(bits, 4).best
    policy = freeze_source_portfolio_policy(
        c21_manifest_sha256="a" * 64, c21_dataset_sha256="b" * 64)
    task = GF2DecompositionTask(4, (0, 1, 2, 3))
    return document, bits, expected.to_dict() if expected else None, policy, task


def test_selected_advice_off_and_shadow_preserve_exact_best():
    document, bits, expected, policy, task = fixture()
    selected = compile_source_portfolio(policy, task, shadow=True).execute(document)
    assert selected.requested_arm == SOURCE_PACKED_SCREENED
    assert selected.selected_arm == SOURCE_PACKED_SCREENED
    assert selected.best_artifact == expected
    assert selected.shadow_arm == EXHAUSTIVE
    assert selected.shadow_best_identity_match is True
    verify_source_portfolio_execution(
        selected.to_dict(), document, policy_sha256=policy["policy_sha256"])
    disabled = compile_source_portfolio(
        policy, task, advice_enabled=False, shadow=True).execute(document)
    assert disabled.requested_arm == EXHAUSTIVE
    assert disabled.selected_arm == EXHAUSTIVE
    assert disabled.best_artifact == expected
    assert disabled.shadow_arm == SOURCE_PACKED_SCREENED
    verify_source_portfolio_execution(disabled.to_dict(), document)


def test_source_refusal_falls_back_exactly(monkeypatch):
    document, _bits, expected, policy, task = fixture()
    monkeypatch.setattr(
        "cmbench.recognition.gf2_source_portfolio.source_anf_packed",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("refused")))
    result = compile_source_portfolio(policy, task).execute(document)
    assert result.requested_arm == SOURCE_PACKED_SCREENED
    assert result.selected_arm == EXHAUSTIVE
    assert result.fallback_used is True
    assert result.best_artifact == expected


def test_policy_roundtrip_and_tamper_rejection():
    _document, _bits, _expected, policy, _task = fixture()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "policy.json"
        save_source_portfolio_policy(policy, path)
        assert load_source_portfolio_policy(path) == policy
        changed = copy.deepcopy(policy)
        changed["selected_arm"] = EXHAUSTIVE
        path.write_text(json.dumps(changed), encoding="utf-8")
        with pytest.raises(ValueError):
            load_source_portfolio_policy(path)


def test_task_and_result_tamper_are_refused():
    document, _bits, _expected, policy, _task = fixture()
    with pytest.raises(ValueError):
        compile_source_portfolio(policy, GF2DecompositionTask(4, (1, 0, 2, 3)))
    result = compile_source_portfolio(
        policy, GF2DecompositionTask(4, (0, 1, 2, 3))).execute(document).to_dict()
    result["source_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        verify_source_portfolio_execution(result, document)

