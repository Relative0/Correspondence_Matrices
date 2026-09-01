"""Cheap truth-vector work features and bounded depth-two exact-arm policy."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .gf2_task_dispatcher import EXHAUSTIVE, SCREENED, canonical_sha256

SCHEMA = "crse-c19-gf2-cheap-work-policy/v1"
FEATURES = ("n_vars", "ones", "transitions", "half_delta", "edge_imbalance")
ARMS = (EXHAUSTIVE, SCREENED)
MAX_DEPTH = 2


def cheap_truth_features(bits: int, n_vars: int) -> dict[str, int]:
    if (type(n_vars) is not int or not 2 <= n_vars <= 10 or type(bits) is not int
            or bits < 0 or bits.bit_length() > (1 << n_vars)):
        raise ValueError("invalid bounded C19 truth vector")
    width = 1 << n_vars
    ones = bits.bit_count()
    transition_mask = (1 << (width - 1)) - 1
    transitions = ((bits ^ (bits >> 1)) & transition_mask).bit_count()
    half = width // 2
    low_mask = (1 << half) - 1
    half_delta = ((bits & low_mask) ^ (bits >> half)).bit_count()
    return {
        "n_vars": n_vars,
        "ones": ones,
        "transitions": transitions,
        "half_delta": half_delta,
        "edge_imbalance": abs(width - 2 * ones),
    }


def _validate_tree(tree: Any, depth: int = 0) -> None:
    if type(tree) is not dict or tree.get("kind") not in {"leaf", "split"}:
        raise ValueError("invalid C19 policy tree")
    if tree["kind"] == "leaf":
        if set(tree) != {"kind", "arm"} or tree["arm"] not in ARMS:
            raise ValueError("invalid C19 policy leaf")
        return
    if (depth >= MAX_DEPTH or set(tree) != {"kind", "feature", "threshold", "le", "gt"}
            or tree["feature"] not in FEATURES or type(tree["threshold"]) is not int):
        raise ValueError("invalid C19 policy split")
    _validate_tree(tree["le"], depth + 1)
    _validate_tree(tree["gt"], depth + 1)


def evaluate_tree(tree: dict[str, Any], features: dict[str, int]) -> str:
    _validate_tree(tree)
    if set(features) != set(FEATURES) or any(type(value) is not int for value in features.values()):
        raise ValueError("invalid C19 feature vector")
    node = tree
    while node["kind"] == "split":
        node = node["le"] if features[node["feature"]] <= node["threshold"] else node["gt"]
    return node["arm"]


def _leaf(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], int]:
    if not rows:
        raise ValueError("cannot fit empty C19 leaf")
    costs = {arm: sum(row["costs_ns"][arm] for row in rows) for arm in ARMS}
    arm = min(ARMS, key=lambda value: (costs[value], value))
    return {"kind": "leaf", "arm": arm}, costs[arm]


def fit_cost_tree(rows: list[dict[str, Any]], max_depth: int) -> tuple[dict[str, Any], int]:
    if type(max_depth) is not int or not 0 <= max_depth <= MAX_DEPTH or not rows:
        raise ValueError("invalid C19 tree fit request")
    if any(set(row["features"]) != set(FEATURES) for row in rows):
        raise ValueError("invalid C19 training features")
    leaf, best_cost = _leaf(rows)
    best_tree, best_key = leaf, (best_cost, json.dumps(leaf, sort_keys=True))
    if max_depth == 0:
        return best_tree, best_cost
    for feature in FEATURES:
        values = sorted({row["features"][feature] for row in rows})
        for threshold in values[:-1]:
            left = [row for row in rows if row["features"][feature] <= threshold]
            right = [row for row in rows if row["features"][feature] > threshold]
            if not left or not right:
                continue
            left_tree, left_cost = fit_cost_tree(left, max_depth - 1)
            right_tree, right_cost = fit_cost_tree(right, max_depth - 1)
            tree = {"kind": "split", "feature": feature, "threshold": threshold,
                    "le": left_tree, "gt": right_tree}
            key = (left_cost + right_cost, json.dumps(tree, sort_keys=True))
            if key < best_key:
                best_tree, best_key = tree, key
    return best_tree, best_key[0]


def fixed_tree(max_exhaustive_n_vars: int) -> dict[str, Any]:
    if type(max_exhaustive_n_vars) is not int or not 2 <= max_exhaustive_n_vars <= 9:
        raise ValueError("invalid C19 fixed threshold")
    return {"kind": "split", "feature": "n_vars", "threshold": max_exhaustive_n_vars,
            "le": {"kind": "leaf", "arm": EXHAUSTIVE},
            "gt": {"kind": "leaf", "arm": SCREENED}}


def validate_policy(policy: dict[str, Any]) -> None:
    keys = {"schema", "status", "selected_candidate", "tree", "training_dataset_sha256",
            "calibration_measurements_sha256", "development_rows", "validation_rows",
            "candidate_validation", "feature_contract", "exact_fallback", "training_use",
            "confirmation_inspected_before_freeze", "production_promotion", "policy_sha256"}
    if type(policy) is not dict or set(policy) != keys:
        raise ValueError("invalid C19 policy fields")
    body = {key: value for key, value in policy.items() if key != "policy_sha256"}
    _validate_tree(policy.get("tree"))
    if (policy.get("schema") != SCHEMA or policy.get("status") != "frozen"
            or policy.get("exact_fallback") != EXHAUSTIVE
            or policy.get("training_use") != "development_fit_validation_select_only"
            or policy.get("confirmation_inspected_before_freeze") is not False
            or policy.get("production_promotion") is not False
            or policy.get("policy_sha256") != canonical_sha256(body)):
        raise ValueError("invalid frozen C19 policy")


def freeze_policy(*, selected_candidate: str, tree: dict[str, Any], dataset_sha256: str,
                  calibration_sha256: str, development_rows: int, validation_rows: int,
                  candidate_validation: dict[str, Any]) -> dict[str, Any]:
    _validate_tree(tree)
    body = {
        "schema": SCHEMA, "status": "frozen", "selected_candidate": selected_candidate,
        "tree": tree, "training_dataset_sha256": dataset_sha256,
        "calibration_measurements_sha256": calibration_sha256,
        "development_rows": development_rows, "validation_rows": validation_rows,
        "candidate_validation": candidate_validation,
        "feature_contract": "n, popcount, adjacent transitions, half-table delta, imbalance/v1",
        "exact_fallback": EXHAUSTIVE,
        "training_use": "development_fit_validation_select_only",
        "confirmation_inspected_before_freeze": False, "production_promotion": False,
    }
    return {**body, "policy_sha256": canonical_sha256(body)}


def save_policy(policy: dict[str, Any], path: Path) -> None:
    validate_policy(policy)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(policy, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def load_policy(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > 256_000:
        raise ValueError("C19 policy exceeds size bound")
    policy = json.loads(raw)
    validate_policy(policy)
    return policy
