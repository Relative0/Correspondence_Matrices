from __future__ import annotations

import pytest

from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE, SCREENED
from cmbench.recognition.gf2_work_policy import fixed_tree, freeze_policy
from cmbench.recognition.gf2_work_policy_compiler import compile_work_policy


def policy(tree, selected="test"):
    return freeze_policy(
        selected_candidate=selected,
        tree=tree,
        dataset_sha256="a" * 64,
        calibration_sha256="b" * 64,
        development_rows=1,
        validation_rows=1,
        candidate_validation={},
    )


def test_constant_leaf_is_folded_without_features():
    compiled = compile_work_policy(policy({"kind": "leaf", "arm": SCREENED}))
    assert compiled.mode == "constant_leaf"
    assert compiled.requires_features is False
    assert compiled.select(0x6996, 4) == SCREENED


def test_feature_tree_preserves_fixed_threshold_decisions():
    compiled = compile_work_policy(policy(fixed_tree(3)))
    assert compiled.mode == "feature_tree"
    assert compiled.requires_features is True
    assert compiled.select(0x96, 3) == EXHAUSTIVE
    assert compiled.select(0x6996, 4) == SCREENED


@pytest.mark.parametrize("bits,n_vars", [(-1, 4), (1 << 16, 4), (0, 1), (0, 11)])
def test_compiled_policy_rejects_out_of_contract_truth_vectors(bits, n_vars):
    compiled = compile_work_policy(policy({"kind": "leaf", "arm": SCREENED}))
    with pytest.raises(ValueError):
        compiled.select(bits, n_vars)


def test_compile_rejects_tampered_policy():
    value = policy({"kind": "leaf", "arm": SCREENED})
    value["tree"]["arm"] = EXHAUSTIVE
    with pytest.raises(ValueError):
        compile_work_policy(value)

