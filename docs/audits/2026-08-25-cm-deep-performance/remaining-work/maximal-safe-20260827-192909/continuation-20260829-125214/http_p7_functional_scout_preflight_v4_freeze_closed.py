"""Read-only preflight for the all-freeze-source P7 functional retry."""

from __future__ import annotations

import json
from pathlib import Path

import http_p7_functional_scout_preflight_v1 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
FIRST_OUTPUT = HERE / "p7-functional-scout-v1-001"
SECOND_OUTPUT = HERE / "p7-functional-scout-v3-001"
CAMPAIGN_CAP_USD = 1.00

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def _first_failure():
    saved = json.loads((FIRST_OUTPUT / "RUN.json").read_text(encoding="utf-8"))
    cleanup = saved.get("cleanup") or {}
    evidence = saved.get("evidence") or {}
    validation = evidence.get("validation") or {}
    if (
        saved.get("status") != "failed"
        or saved.get("pod_id") != "1xh6csc4oxy067"
        or saved.get("uploaded_source_files") != 152
        or saved.get("estimated_compute_cost_usd") != 0.002207883052031199
        or evidence.get("sha256")
        != "0cd9a0462b719d6c860ca291dc76ab3e9441040453bc967890ce9f6688e4f62b"
        or validation.get("junit_testcases")
        != {"tests": 3, "failures": 0, "errors": 3, "skipped": 0}
        or validation.get("source_unchanged") is not True
        or cleanup.get("owned_pod_absent") is not True
        or cleanup.get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("P7 V1 packaging failure is not reconciled")
    return saved


def _second_failure():
    saved = json.loads((SECOND_OUTPUT / "RUN.json").read_text(encoding="utf-8"))
    cleanup = saved.get("cleanup") or {}
    evidence = saved.get("evidence") or {}
    validation = evidence.get("validation") or {}
    if (
        saved.get("status") != "failed"
        or saved.get("pod_id") != "2fzt8mu6ji6nmw"
        or saved.get("uploaded_source_files") != 156
        or saved.get("estimated_compute_cost_usd") != 0.003181478933493296
        or evidence.get("sha256")
        != "f11e7d60d06e38f16231fd83f3f3d0fe2219433ec052de607fbe12c4ba69decb"
        or validation.get("junit_testcases")
        != {"tests": 32, "failures": 0, "errors": 0, "skipped": 0}
        or validation.get("status") != "failed"
        or validation.get("error") != "RuntimeError: offline-gate-verify failed with exit code 2"
        or validation.get("source_unchanged") is not True
        or cleanup.get("owned_pod_absent") is not True
        or cleanup.get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("P7 V3 offline-gate failure is not reconciled")
    return saved


def check():
    first = _first_failure()
    second = _second_failure()
    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before all-freeze-source retry")
    known_retry_cost = sum(
        float(saved["estimated_compute_cost_usd"]) for saved in (first, second)
    )
    prior = max(0.01, float(result["prior_cost_bound_usd"]) + known_retry_cost)
    offer = result["selected_offer"]
    projected = float(offer["rate_usd_per_hour"]) * (1200 / 3600)
    result.update(
        {
            "p7_failed_attempts_reconciled": True,
            "p7_failed_pod_ids": [first["pod_id"], second["pod_id"]],
            "p7_failed_attempts_estimated_compute_cost_usd": known_retry_cost,
            "prior_cost_bound_usd": prior,
            "projected_20_min_cost_usd": projected,
            "projected_aggregate_cost_usd": prior + projected + 0.01,
            "authorized_aggregate_campaign_cap_usd": CAMPAIGN_CAP_USD,
            "current_inventories": current,
        }
    )
    result["ready"] = bool(
        result.get("ready")
        and projected < 0.10
        and result["projected_aggregate_cost_usd"] < CAMPAIGN_CAP_USD
    )
    return result
