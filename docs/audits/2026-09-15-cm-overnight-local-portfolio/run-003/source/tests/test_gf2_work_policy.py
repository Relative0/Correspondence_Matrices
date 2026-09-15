from __future__ import annotations

import copy

import pytest

from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE, SCREENED
from cmbench.recognition.gf2_work_policy import (
    cheap_truth_features, evaluate_tree, fit_cost_tree, fixed_tree, freeze_policy,
    validate_policy)


def test_features_are_bounded_deterministic_integers() -> None:
    first = cheap_truth_features(0x6996, 4)
    assert first == cheap_truth_features(0x6996, 4)
    assert set(first) == {"n_vars", "ones", "transitions", "half_delta", "edge_imbalance"}
    assert all(type(value) is int and value >= 0 for value in first.values())
    with pytest.raises(ValueError):
        cheap_truth_features(1 << 16, 4)


def test_fixed_tree_and_cost_tree_choose_exact_arms() -> None:
    tree = fixed_tree(3)
    assert evaluate_tree(tree, cheap_truth_features(0x96, 3)) == EXHAUSTIVE
    assert evaluate_tree(tree, cheap_truth_features(0x6996, 4)) == SCREENED
    rows = [
        {"features": cheap_truth_features(0x96, 3),
         "costs_ns": {EXHAUSTIVE: 10, SCREENED: 20}},
        {"features": cheap_truth_features(0x6996, 4),
         "costs_ns": {EXHAUSTIVE: 30, SCREENED: 10}},
    ]
    learned, cost = fit_cost_tree(rows, 2)
    assert cost == 20
    assert evaluate_tree(learned, rows[0]["features"]) == EXHAUSTIVE
    assert evaluate_tree(learned, rows[1]["features"]) == SCREENED


def test_frozen_policy_rejects_tamper() -> None:
    policy = freeze_policy(
        selected_candidate="fixed_n3", tree=fixed_tree(3), dataset_sha256="a" * 64,
        calibration_sha256="b" * 64, development_rows=48, validation_rows=24,
        candidate_validation={"fixed_n3": {"aggregate_speedup": 1.2}})
    validate_policy(policy)
    changed = copy.deepcopy(policy)
    changed["tree"]["threshold"] = 4
    with pytest.raises(ValueError):
        validate_policy(changed)
