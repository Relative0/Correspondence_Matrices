from __future__ import annotations

import copy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from cmbench.recognition.gf2_async_shadow_boundary import (
    PreparedPolicyAsyncShadowBoundary,
    verify_async_shadow_observation,
    verify_async_shadow_serve_result,
)
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2
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


def prepared(c27=C27, c22=C22):
    return prepare_support_policy_context(c27, c22)


def boundary(context, **kwargs):
    return PreparedPolicyAsyncShadowBoundary(
        "test-c33",
        context,
        required_prepared_context_sha256=context.context_sha256,
        max_queries=16,
        **kwargs,
    )


def release_and_observe(service, result, case, required):
    assert service.observations() == ()
    assert service.acknowledge_delivery(
        result["shadow_envelope_sha256"]) == "acknowledged_for_observation"
    assert service.drain(timeout_seconds=5.0)
    observations = service.observations()
    assert len(observations) == 1
    verify_async_shadow_observation(
        observations[0],
        case,
        required_best=required,
        envelope_sha256=result["shadow_envelope_sha256"],
    )
    return observations[0]


def test_disabled_boundary_serves_exact_baseline_without_shadow_work():
    case = cases()[0]
    required = oracle(case)
    context = prepared()
    service = boundary(context, shadow_enabled=False)

    result = service.execute(case).to_dict()
    verify_async_shadow_serve_result(result, case, required_best=required)
    snapshot = service.close()

    assert result["shadow_disposition"] == "disabled"
    assert result["shadow_envelope_sha256"] is None
    assert snapshot["worker_started"] is False
    assert snapshot["candidate_observations"] == 0
    assert snapshot["served_candidate_results"] == 0


def test_candidate_cannot_start_until_exact_delivery_is_acknowledged():
    case = cases()[0]
    required = oracle(case)
    context = prepared()
    called = False

    def observe(session, selected):
        nonlocal called
        called = True
        return session.execute(selected)

    service = boundary(
        context, shadow_enabled=True, queue_capacity=4, candidate_executor=observe)
    result = service.execute(case).to_dict()
    verify_async_shadow_serve_result(result, case, required_best=required)

    assert result["shadow_disposition"] == "staged_pending_delivery_ack"
    assert called is False
    assert service.observations() == ()
    observation = release_and_observe(service, result, case, required)
    snapshot = service.close()

    assert called is True
    assert observation["candidate_status"] == "observed"
    assert observation["candidate_best_identity_match"] is True
    assert snapshot["candidate_observations"] == 1
    assert snapshot["production_writes"] == 0


def test_staged_request_is_immune_to_post_return_caller_mutation():
    original = copy.deepcopy(cases()[0])
    selected = copy.deepcopy(original)
    required = oracle(original)
    context = prepared()
    service = boundary(context, shadow_enabled=True, queue_capacity=2)

    result = service.execute(selected).to_dict()
    selected["truth_bits_hex"] = "0x0"
    selected["expression_v2"]["root"] = 0
    observation = release_and_observe(service, result, original, required)
    service.close()

    assert observation["candidate_status"] == "observed"
    assert observation["candidate_best_identity_match"] is True


def test_bounded_queue_drops_safely_without_blocking_or_ack_token():
    selected = cases()[:2]
    context = prepared()
    service = boundary(context, shadow_enabled=True, queue_capacity=1)

    first = service.execute(selected[0]).to_dict()
    second = service.execute(selected[1]).to_dict()
    verify_async_shadow_serve_result(first, selected[0], required_best=oracle(selected[0]))
    verify_async_shadow_serve_result(second, selected[1], required_best=oracle(selected[1]))
    snapshot = service.snapshot()

    assert first["shadow_disposition"] == "staged_pending_delivery_ack"
    assert second["shadow_disposition"] == "queue_full"
    assert second["delivery_ack_required_before_candidate"] is False
    assert snapshot["queue_full_drops"] == 1
    assert snapshot["pending_staged"] == 1
    service.close()
    assert len(service.observations()) == 1


def test_deterministic_sampling_releases_only_selected_requests():
    selected = cases()[:4]
    context = prepared()
    service = boundary(
        context, shadow_enabled=True, sample_every=2, queue_capacity=4)

    results = [service.execute(case).to_dict() for case in selected]
    assert [row["sample_eligible"] for row in results] == [True, False, True, False]
    assert [row["shadow_disposition"] for row in results] == [
        "staged_pending_delivery_ack", "sampled_out",
        "staged_pending_delivery_ack", "sampled_out",
    ]
    assert service.acknowledge_all_delivered() == 2
    assert service.drain(timeout_seconds=5.0)
    snapshot = service.close()

    assert snapshot["sampled_in"] == 2
    assert snapshot["sampled_out"] == 2
    assert snapshot["candidate_observations"] == 2


def test_candidate_exception_and_refusal_are_contained_off_path():
    case = cases()[0]
    required = oracle(case)
    context = prepared()

    def fail(_session, _case):
        raise RuntimeError("simulated asynchronous candidate failure")

    failing = boundary(
        context, shadow_enabled=True, queue_capacity=1, candidate_executor=fail)
    failed_result = failing.execute(case).to_dict()
    failed = release_and_observe(failing, failed_result, case, required)
    failing.close()

    def refuse(session, selected):
        session.close()
        return session.execute(selected)

    refusing = boundary(
        context, shadow_enabled=True, queue_capacity=1, candidate_executor=refuse)
    refused_result = refusing.execute(case).to_dict()
    refused = release_and_observe(refusing, refused_result, case, required)
    refusing.close()

    assert failed["candidate_status"] == "error"
    assert failed["candidate_error_type"] == "RuntimeError"
    assert failed["shadow_failure_contained"] is True
    assert refused["candidate_status"] == "refused"
    assert refused["shadow_failure_contained"] is True


def test_exact_but_nonbest_candidate_is_an_observed_divergence_only():
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

    service = boundary(
        context, shadow_enabled=True, queue_capacity=1, candidate_executor=diverge)
    result = service.execute(case).to_dict()
    observation = release_and_observe(service, result, case, required)
    snapshot = service.close()

    assert result["served_best_artifact"] == required
    assert observation["candidate_best_artifact"] == alternate
    assert observation["candidate_best_identity_match"] is False
    assert observation["shadow_divergence_detected"] is True
    assert observation["shadow_failure_contained"] is True
    assert snapshot["divergences"] == 1
    assert snapshot["served_candidate_results"] == 0


def test_wrong_binding_and_changed_source_fail_closed(tmp_path):
    c27 = tmp_path / "c27.json"
    c22 = tmp_path / "c22.json"
    c27.write_bytes(C27.read_bytes())
    c22.write_bytes(C22.read_bytes())
    context = prepared(c27, c22)

    with pytest.raises(ValueError, match="configuration"):
        PreparedPolicyAsyncShadowBoundary(
            "test-c33-wrong-bind",
            context,
            required_prepared_context_sha256="0" * 64,
        )

    case = cases()[0]
    service = boundary(context, shadow_enabled=True, queue_capacity=1)
    result = service.execute(case).to_dict()
    with c27.open("ab") as handle:
        handle.write(b" ")
    observation = release_and_observe(service, result, case, oracle(case))

    assert observation["candidate_status"] == "error"
    assert observation["candidate_error_type"] == "ValueError"
    with pytest.raises(ValueError, match="source changed"):
        service.close()
    assert service.snapshot()["closed"] is True


def test_close_drains_staged_work_and_rejects_late_requests():
    case = cases()[0]
    context = prepared()
    service = boundary(context, shadow_enabled=True, queue_capacity=1)

    service.execute(case)
    snapshot = service.close()

    assert snapshot["closed"] is True
    assert snapshot["pending_staged"] == 0
    assert snapshot["pending_ready"] == 0
    assert snapshot["worker_stopped"] is True
    assert snapshot["candidate_observations"] == 1
    with pytest.raises(ValueError, match="closed"):
        service.execute(case)
