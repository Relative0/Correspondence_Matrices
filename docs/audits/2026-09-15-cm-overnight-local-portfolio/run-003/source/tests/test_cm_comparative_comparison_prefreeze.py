from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from cmbench.comparative import comparison_prefreeze as prefreeze


ROOT = Path(__file__).resolve().parents[1]
FUNCTIONAL = ROOT / "docs/recognition/runs/architecture-refresh-harness-development-20260903-001"


def _load(path: Path):
    payload = path.read_bytes()
    return json.loads(payload), hashlib.sha256(payload).hexdigest()


def _current(new_surface=None):
    native, native_sha = _load(
        ROOT / "docs/recognition/native_portfolio_baseline_closure_results.json"
    )
    c38, c38_sha = _load(
        ROOT
        / "docs/recognition/c38_linux_confirmation/C38_CROSS_MACHINE_ADJUDICATION_20260903.json"
    )
    plan, plan_sha = _load(FUNCTIONAL / "PLAN.json")
    result, result_sha = _load(FUNCTIONAL / "RESULT.json")
    return prefreeze.build_prefreeze(
        source_checkpoint="186a9df88dfa2e7c27046cbcbebbeb51893200b7",
        native_closure=native,
        native_closure_sha256=native_sha,
        c38_adjudication=c38,
        c38_adjudication_sha256=c38_sha,
        functional_plan=plan,
        functional_plan_sha256=plan_sha,
        functional_result=result,
        functional_result_sha256=result_sha,
        new_surface_evidence=new_surface,
    )


def test_current_evidence_allows_only_source_blind_corpus_freeze():
    result = _current()
    assert result["status"] == "ready_for_corpus_freeze"
    assert result["eligibility"]["current_q64_selector_oracle_headroom"] == 1.0
    assert result["eligibility"]["headroom_gate_passed"] is False
    assert result["permissions"]["fresh_corpus_selection"] is True
    assert result["permissions"]["fresh_corpus_inspection"] is True
    assert result["permissions"]["corpus_identity_freeze"] is True
    assert result["permissions"]["prospective_data_consumption"] is False
    assert result["permissions"]["timed_local_campaign"] is False
    assert result["permissions"]["selector_fitting"] is False
    assert result["permissions"]["neural_training"] is False
    assert result["fresh_or_prospective_data_consumed"] is False


def test_blueprint_is_dormant_but_complete_enough_for_future_freeze():
    result = _current()
    blueprint = result["dormant_campaign_blueprint"]
    assert set(blueprint["lanes"]) == {"A", "B", "C", "D"}
    assert blueprint["schedules"]["restriction_query_counts"] == [1, 4, 16, 64]
    assert blueprint["schedules"]["schedule_sha256"] is None
    assert blueprint["cohorts"]["fresh_tree_like"]["dataset_sha256"] is None
    assert blueprint["publication_gates"][
        "new_selector_requires_development_oracle_headroom"
    ] == 1.10


def test_tampered_current_decisions_and_permissions_fail_closed():
    result = _current()
    mutations = []
    changed = copy.deepcopy(result)
    changed["permissions"]["prospective_data_consumption"] = True
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["permissions"]["runpod_execution"] = True
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["dormant_campaign_blueprint"]["schedules"]["schedule_sha256"] = "0" * 64
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["timing_evidence_produced"] = True
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["permissions"]["unreviewed_external_write"] = True
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["eligibility"]["c38_all_performance_gates_passed"] = True
    mutations.append(changed)
    for item in mutations:
        with pytest.raises(ValueError):
            prefreeze.validate_prefreeze(item)


def test_malformed_binding_and_checkpoint_types_fail_closed():
    result = _current()
    mutations = []
    changed = copy.deepcopy(result)
    changed["evidence_bindings"]["native_portfolio_closure_sha256"] = None
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["source_checkpoint"] = None
    mutations.append(changed)
    for item in mutations:
        with pytest.raises(ValueError):
            prefreeze.validate_prefreeze(item)


def test_only_complete_independently_verified_new_surface_evidence_opens_headroom_gate():
    evidence = {
        "schema": prefreeze.HEADROOM_SCHEMA,
        "surface_id": "synthetic-contract-control-only",
        "source_sha256": "1" * 64,
        "results_sha256": "2" * 64,
        "independent_verification_sha256": "3" * 64,
        "exact_artifact_verified": True,
        "optimized_exact_baselines_included": True,
        "development_oracle_headroom": 1.10,
        "prospective_data_consumed": False,
        "training_performed": False,
    }
    result = _current(evidence)
    assert result["status"] == "ready_for_corpus_freeze"
    assert result["eligibility"]["headroom_gate_passed"] is True
    assert result["permissions"]["fresh_corpus_selection"] is True
    assert result["permissions"]["timed_local_campaign"] is False
    assert result["permissions"]["runpod_authorization_request"] is False
    changed = copy.deepcopy(evidence)
    changed["development_oracle_headroom"] = 1.099999
    with pytest.raises(ValueError):
        _current(changed)
