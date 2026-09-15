from __future__ import annotations

from dataclasses import FrozenInstanceError
import json

import pytest

from cmbench.recognition.gf2_prepared_support_context import (
    PreparedSupportPolicyContext,
    prepare_support_policy_context,
    verify_prepared_policy_sources,
)
from cmbench.recognition.gf2_support_aware_session import SupportAwareGF2Session
from tests.test_gf2_support_aware_session import case, policies


def test_prepared_context_is_deterministic_immutable_and_exact(tmp_path) -> None:
    c22, c27, c22_path, c27_path = policies(tmp_path)
    prepared = prepare_support_policy_context(c27_path, c22_path)
    verify_prepared_policy_sources(prepared)
    assert prepared.schema == "crse-c30-prepared-support-policy-context/v1"
    assert prepared.c27_policy_sha256 == c27["policy_sha256"]
    assert prepared.c22_policy_sha256 == c22["policy_sha256"]
    assert prepared.identity()["context_sha256"] == prepared.context_sha256
    with pytest.raises(FrozenInstanceError):
        prepared.context_sha256 = "0" * 64

    session = SupportAwareGF2Session.from_prepared_context(
        "prepared", prepared, max_queries=2)
    assert session.execute(case(4)).selected_arm == "verified_truth_screened"
    assert session.execute(case(5)).selected_arm == "source_packed_anf_screened"
    setup = session.snapshot()["setup_timings_ns"]
    assert set(setup) == {
        "prepared_context_bind_ns", "session_initialize_ns", "setup_total_ns"}
    assert setup["setup_total_ns"] == (
        setup["prepared_context_bind_ns"] + setup["session_initialize_ns"])


def test_prepared_context_retains_advice_off_and_exact_fallback(tmp_path) -> None:
    _c22, _c27, c22_path, c27_path = policies(tmp_path)
    prepared = prepare_support_policy_context(c27_path, c22_path)
    off = SupportAwareGF2Session.from_prepared_context(
        "off", prepared, advice_enabled=False, max_queries=1)
    assert off.execute(case(4)).selected_arm == "explicit_cm_exhaustive"
    fallback = SupportAwareGF2Session.from_prepared_context(
        "fallback", prepared, max_queries=1)
    result = fallback.execute(case(4), force_selected_refusal=True)
    assert result.status == "ok"
    assert result.selected_arm == "explicit_cm_exhaustive"
    assert result.fallback_used is True


def test_prepared_context_refuses_source_change_and_wrong_binding(tmp_path) -> None:
    _c22, _c27, c22_path, c27_path = policies(tmp_path)
    prepared = prepare_support_policy_context(c27_path, c22_path)
    c27_path.write_text(c27_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="source changed"):
        verify_prepared_policy_sources(prepared)
    with pytest.raises(ValueError, match="unbound"):
        SupportAwareGF2Session(
            "wrong-binding", None, None, prepared_context=prepared,
            required_prepared_context_sha256="0" * 64)


def test_prepared_context_rejects_direct_unvalidated_construction(tmp_path) -> None:
    _c22, _c27, c22_path, c27_path = policies(tmp_path)
    with pytest.raises(ValueError, match="validated construction"):
        PreparedSupportPolicyContext(
            token=object(), c27_policy=json.loads(c27_path.read_text()),
            c22_policy=json.loads(c22_path.read_text()),
            c27_file_sha256="a" * 64, c22_file_sha256="b" * 64,
            c27_source_path=c27_path, c22_source_path=c22_path, preparation_ns=1)
