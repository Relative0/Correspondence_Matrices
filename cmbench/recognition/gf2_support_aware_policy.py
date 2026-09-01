"""Frozen transparent support policy derived from C26 development evidence."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .gf2_task_dispatcher import EXHAUSTIVE, canonical_sha256
from .gf2_source_portfolio import SOURCE_PACKED_SCREENED

POLICY_SCHEMA = "crse-c27-gf2-support-aware-policy/v1"
TRUTH_SCREENED = "verified_truth_screened"
SHA256 = re.compile(r"[0-9a-f]{64}")


def _body(c26_manifest_sha256: str, c26_result_sha256: str) -> dict[str, Any]:
    return {
        "schema": POLICY_SCHEMA,
        "status": "frozen",
        "objective": "best_exact_gf2_artifact",
        "tiny_support_max_n_vars": 4,
        "tiny_support_arm": TRUTH_SCREENED,
        "large_support_arm": SOURCE_PACKED_SCREENED,
        "advice_off_arm": EXHAUSTIVE,
        "exact_fallback_arm": EXHAUSTIVE,
        "max_partitions": 64,
        "materialize_budget": 4,
        "development_evidence": "C26/F6",
        "c26_manifest_sha256": c26_manifest_sha256,
        "c26_result_sha256": c26_result_sha256,
        "selection_basis": "transparent support threshold; no learned router",
        "training_use": False,
        "fresh_confirmation_required": True,
        "fresh_confirmation_complete": False,
        "production_promotion": False,
    }


def freeze_support_aware_policy(*, c26_manifest_sha256: str,
                                c26_result_sha256: str) -> dict[str, Any]:
    if not all(type(value) is str and SHA256.fullmatch(value) for value in (
            c26_manifest_sha256, c26_result_sha256)):
        raise ValueError("invalid C27 development evidence fingerprint")
    body = _body(c26_manifest_sha256, c26_result_sha256)
    return {**body, "policy_sha256": canonical_sha256(body)}


def validate_support_aware_policy(policy: dict[str, Any]) -> None:
    expected = set(_body("0" * 64, "0" * 64)) | {"policy_sha256"}
    if type(policy) is not dict or set(policy) != expected:
        raise ValueError("invalid C27 policy fields")
    if not all(type(policy.get(field)) is str and SHA256.fullmatch(policy[field]) for field in (
            "c26_manifest_sha256", "c26_result_sha256")):
        raise ValueError("invalid C27 policy evidence fingerprint")
    body = _body(policy["c26_manifest_sha256"], policy["c26_result_sha256"])
    if policy != {**body, "policy_sha256": canonical_sha256(body)}:
        raise ValueError("invalid frozen C27 support-aware policy")


def save_support_aware_policy(policy: dict[str, Any], path: Path) -> None:
    validate_support_aware_policy(policy)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(policy, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def load_support_aware_policy(path: Path, *, max_bytes: int = 64_000) -> dict[str, Any]:
    raw = path.read_bytes()
    if not raw or len(raw) > max_bytes:
        raise ValueError("C27 policy exceeds size bound")

    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate C27 policy key")
            value[key] = item
        return value

    policy = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _value: (
        _ for _ in ()).throw(ValueError("nonfinite C27 policy value")))
    validate_support_aware_policy(policy)
    return policy


def select_support_arm(policy: dict[str, Any], n_vars: int, *, advice_enabled: bool) -> str:
    validate_support_aware_policy(policy)
    if type(n_vars) is not int or not 3 <= n_vars <= 6 or type(advice_enabled) is not bool:
        raise ValueError("invalid C27 support selection")
    if not advice_enabled:
        return policy["advice_off_arm"]
    return (policy["tiny_support_arm"] if n_vars <= policy["tiny_support_max_n_vars"]
            else policy["large_support_arm"])
