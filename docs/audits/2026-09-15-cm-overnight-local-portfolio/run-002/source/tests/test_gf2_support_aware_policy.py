from __future__ import annotations

import json

import pytest

from cmbench.recognition.gf2_support_aware_policy import (
    freeze_support_aware_policy,
    load_support_aware_policy,
    select_support_arm,
)


def test_c27_policy_is_digest_bound_and_transparent(tmp_path):
    policy = freeze_support_aware_policy(
        c26_manifest_sha256="a" * 64, c26_result_sha256="b" * 64)
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy), encoding="utf-8")
    loaded = load_support_aware_policy(path)
    assert select_support_arm(loaded, 3, advice_enabled=True) == "verified_truth_screened"
    assert select_support_arm(loaded, 4, advice_enabled=True) == "verified_truth_screened"
    assert select_support_arm(loaded, 5, advice_enabled=True) == "source_packed_anf_screened"
    assert select_support_arm(loaded, 6, advice_enabled=True) == "source_packed_anf_screened"
    assert select_support_arm(loaded, 6, advice_enabled=False) == "explicit_cm_exhaustive"


def test_c27_policy_tampering_fails_closed(tmp_path):
    policy = freeze_support_aware_policy(
        c26_manifest_sha256="a" * 64, c26_result_sha256="b" * 64)
    policy["tiny_support_max_n_vars"] = 5
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(ValueError):
        load_support_aware_policy(path)
