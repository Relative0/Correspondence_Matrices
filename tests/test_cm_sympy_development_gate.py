from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.cm_sympy_development_gate import (
    OUTPUT_AUDIT,
    ROOT,
    analyze,
    exact_instance_bootstrap,
)
from cmbench.comparative.sympy_cm_claim_cleanup import sha256_bytes


def test_exact_bootstrap_uses_instances_not_repetitions() -> None:
    result = exact_instance_bootstrap([0.8, 1.0])
    assert result["independent_instances"] == 2
    assert result["bootstrap_replicates"] == 4
    assert result["geometric_mean_candidate_over_incumbent"] == pytest.approx(0.8 ** 0.5)


def test_review_is_no_go_with_no_qualifying_attributed_lane() -> None:
    review = analyze()
    assert review["decision"]["outcome"] == "no_go"
    assert review["decision"]["qualifying_lanes"] == []
    assert review["decision"]["confirmation_corpus_frozen"] is False
    assert review["decision"]["confirmation_run_performed"] is False
    assert all(lane["correctly_attributed_development_gain"] is False for lane in review["lanes"])
    assert {lane["independent_instances"] for lane in review["lanes"] if lane["family"] != "Y05"} == {4}
    assert next(lane for lane in review["lanes"] if lane["family"] == "Y05")["independent_instances"] == 6


def test_review_retains_fairness_limitations() -> None:
    evidence = analyze()["evidence"]
    assert evidence["preparation_and_cache_treatment"]["arm_order_counterbalanced"] is False
    assert evidence["hard_limits"]["hard_memory_limit_present"] is False
    assert evidence["independence"]["repetitions_are_independent_units"] is False
    assert evidence["complete_failure_accounting"] is True


def test_review_audit_manifest_and_source_hashes_verify() -> None:
    manifest = json.loads((OUTPUT_AUDIT / "AUDIT_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["decision"] == "no_go"
    for record in manifest["files"]:
        payload = (OUTPUT_AUDIT / record["path"]).read_bytes()
        assert len(payload) == record["bytes"]
        assert sha256_bytes(payload) == record["sha256"]

    binding = json.loads((OUTPUT_AUDIT / "SOURCE_BINDING.json").read_text(encoding="utf-8"))
    for record in binding["sources"]:
        assert record["verified"] is True
        assert sha256_bytes((ROOT / record["path"]).read_bytes()) == record["sha256"]

    assert not (OUTPUT_AUDIT / "CONFIRMATION_INPUTS.json").exists()
    assert not (OUTPUT_AUDIT / "CONFIRMATION_LEDGER.jsonl").exists()
