"""Functional and fail-closed tests for the post-C38 comparison harness."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from cmbench.comparative import architecture_refresh_harness as harness


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json"


@pytest.fixture(scope="module")
def functional_result():
    payload = DATASET.read_bytes()
    native = harness.find_native_library(ROOT)
    plan = harness.build_plan(native_available=native is not None)
    result = harness.run_functional_validation(
        json.loads(payload),
        dataset_sha256=hashlib.sha256(payload).hexdigest(),
        native_library_path=native,
    )
    return plan, result


def test_plan_is_four_lane_and_never_authorizes_timing_or_new_data():
    for native in (False, True):
        plan = harness.build_plan(native_available=native)
        assert set(plan["lanes"]) == {"A", "B", "C", "D"}
        assert plan["lanes"]["B"]["query_counts"] == [1, 4, 16, 64]
        assert plan["timing_permitted"] is False
        assert plan["fresh_corpus_permitted"] is False
        assert plan["prospective_data_permitted"] is False
        assert ("native_fused_slots" in plan["lanes"]["B"]["arms"]) is native


def test_all_four_lanes_match_their_exact_artifacts(functional_result):
    plan, result = functional_result
    harness.validate_functional_result(result, plan)
    assert result["all_exact"] is True
    assert len(result["lanes"]["A"]["arms"]) == 8
    assert set(result["lanes"]["B"]["checkpoints"]) == {"1", "4", "16", "64"}
    assert result["lanes"]["C"]["structure"]["avoided_duplicate_nodes"] > 0
    assert set(result["lanes"]["D"]["sublanes"]) == {
        *harness.tasks.TASKS,
        "structural_reload",
    }
    assert result["timing_evidence_produced"] is False
    assert result["performance_claim_permitted"] is False


def test_result_mutations_fail_closed(functional_result):
    plan, result = functional_result
    mutations = []
    changed = copy.deepcopy(result)
    changed["performance_claim_permitted"] = True
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["lanes"]["A"]["arms"].pop("raw_flat")
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["lanes"]["B"]["checkpoints"]["64"]["arms"][
        "cse_flat_bigint"
    ]["artifact_sha256"] = "0" * 64
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["lanes"]["C"]["all_exact"] = False
    mutations.append(changed)
    changed = copy.deepcopy(result)
    changed["lanes"]["D"]["sublanes"].pop("structural_reload")
    mutations.append(changed)
    for item in mutations:
        with pytest.raises(ValueError):
            harness.validate_functional_result(item, plan)


def test_native_plan_cannot_validate_nonnative_result(functional_result):
    plan, result = functional_result
    if result["native_identity"] is None:
        pytest.skip("retained native library is unavailable")
    changed = copy.deepcopy(result)
    changed["native_identity"] = None
    with pytest.raises(ValueError):
        harness.validate_functional_result(changed, plan)
