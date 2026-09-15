from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from cmbench.recognition.gf2_decomposition import analyze_exact_gf2
from cmbench.recognition.gf2_prepared_shadow_boundary import (
    PreparedPolicyShadowBoundary,
    verify_prepared_policy_shadow_result,
)
from cmbench.recognition.gf2_prepared_support_context import (
    prepare_support_policy_context,
)
from cmbench.recognition.gf2_task_dispatcher import canonical_sha256


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset.json"
C27 = ROOT / "docs/recognition/c27_support_aware_policy.json"
C22 = ROOT / "docs/recognition/c22_source_portfolio_policy.json"


def cases():
    return json.loads(DATASET.read_text(encoding="utf-8"))["cases"]


def oracle(case):
    analysis = analyze_exact_gf2(
        int(case["truth_bits_hex"], 16), case["n_vars"], max_partitions=64)
    return analysis.best.to_dict() if analysis.best else None


def prepared():
    return prepare_support_policy_context(C27, C22)


def boundary(context, **kwargs):
    return PreparedPolicyShadowBoundary(
        "test-c32",
        context,
        required_prepared_context_sha256=context.context_sha256,
        max_queries=8,
        **kwargs,
    )


def test_shadow_disabled_serves_exact_baseline_without_candidate_work():
    case = cases()[0]
    required = oracle(case)
    context = prepared()
    called = False

    def should_not_run(_session, _case):
        nonlocal called
        called = True
        raise AssertionError("disabled shadow executed candidate")

    service = boundary(
        context, shadow_enabled=False, candidate_executor=should_not_run)
    result = service.execute(case).to_dict()
    verify_prepared_policy_shadow_result(result, case, required_best=required)
    snapshot = service.close()

    assert not called
    assert result["candidate_status"] == "disabled"
    assert snapshot["requests"] == 1
    assert snapshot["candidate_observations"] == 0
    assert snapshot["served_candidate_results"] == 0
    assert snapshot["production_writes"] == 0


def test_shadow_enabled_observes_exact_candidate_but_still_serves_baseline():
    case = cases()[0]
    required = oracle(case)
    context = prepared()
    service = boundary(context, shadow_enabled=True)

    result = service.execute(case).to_dict()
    verify_prepared_policy_shadow_result(result, case, required_best=required)
    snapshot = service.close()

    assert result["candidate_status"] == "observed"
    assert result["candidate_best_identity_match"] is True
    assert result["served_output_source"] == "exact_screened_baseline"
    assert result["candidate_observed_only"] is True
    assert snapshot["candidate_observations"] == 1
    assert snapshot["served_candidate_results"] == 0


def test_candidate_exception_is_contained_and_baseline_remains_exact():
    case = cases()[0]
    required = oracle(case)
    context = prepared()

    def fail(_session, _case):
        raise RuntimeError("simulated shadow-only failure")

    service = boundary(context, shadow_enabled=True, candidate_executor=fail)
    result = service.execute(case).to_dict()
    verify_prepared_policy_shadow_result(result, case, required_best=required)
    snapshot = service.close()

    assert result["candidate_status"] == "error"
    assert result["candidate_error_type"] == "RuntimeError"
    assert result["shadow_failure_contained"] is True
    assert snapshot["candidate_errors"] == 1


def test_candidate_refusal_is_contained_and_baseline_remains_exact():
    case = cases()[0]
    required = oracle(case)
    context = prepared()

    def refuse(session, selected):
        session.close()
        return session.execute(selected)

    service = boundary(context, shadow_enabled=True, candidate_executor=refuse)
    result = service.execute(case).to_dict()
    verify_prepared_policy_shadow_result(result, case, required_best=required)
    snapshot = service.close()

    assert result["candidate_status"] == "refused"
    assert result["candidate_refusal_reason"].startswith("query_refused:")
    assert result["shadow_failure_contained"] is True
    assert snapshot["candidate_refusals"] == 1


def test_exact_but_nonbest_candidate_divergence_is_detected_and_not_served():
    case = next(case for case in cases() if case["case_id"].endswith("03b09ef790ba581d"))
    required = oracle(case)
    analysis = analyze_exact_gf2(
        int(case["truth_bits_hex"], 16), case["n_vars"], max_partitions=64)
    alternate = next(row.to_dict() for row in analysis.candidates if row.to_dict() != required)
    context = prepared()

    def diverge(session, selected):
        result = session.execute(selected)
        return replace(
            result,
            best_artifact=alternate,
            artifact_sha256=canonical_sha256(alternate),
        )

    service = boundary(context, shadow_enabled=True, candidate_executor=diverge)
    result = service.execute(case).to_dict()
    verify_prepared_policy_shadow_result(result, case, required_best=required)
    snapshot = service.close()

    assert result["served_best_artifact"] == required
    assert result["candidate_best_artifact"] == alternate
    assert result["candidate_best_identity_match"] is False
    assert result["shadow_divergence_detected"] is True
    assert result["shadow_failure_contained"] is True
    assert snapshot["divergences"] == 1
    assert snapshot["served_candidate_results"] == 0


def test_context_binding_and_changed_source_audit_fail_closed(tmp_path):
    c27 = tmp_path / "c27.json"
    c22 = tmp_path / "c22.json"
    c27.write_bytes(C27.read_bytes())
    c22.write_bytes(C22.read_bytes())
    context = prepare_support_policy_context(c27, c22)

    with pytest.raises(ValueError, match="configuration"):
        PreparedPolicyShadowBoundary(
            "test-c32-wrong-bind",
            context,
            required_prepared_context_sha256="0" * 64,
        )

    service = boundary(context, shadow_enabled=False)
    with c27.open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(ValueError, match="source changed"):
        service.audit_sources()
    with pytest.raises(ValueError, match="source changed"):
        service.close()
