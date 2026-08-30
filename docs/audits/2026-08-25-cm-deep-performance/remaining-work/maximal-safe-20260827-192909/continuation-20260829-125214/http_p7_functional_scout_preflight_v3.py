"""Read-only preflight for the authorized 156-file P7 functional retry."""

from __future__ import annotations

import json
from pathlib import Path

import http_p7_functional_scout_preflight_v1 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
FAILED_OUTPUT = HERE / "p7-functional-scout-v1-001"
CAMPAIGN_CAP_USD = 1.00

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def check():
    saved = json.loads((FAILED_OUTPUT / "RUN.json").read_text(encoding="utf-8"))
    cleanup = saved.get("cleanup") or {}
    evidence = saved.get("evidence") or {}
    validation = evidence.get("validation") or {}
    if (
        saved.get("status") != "failed"
        or saved.get("pod_id") != "1xh6csc4oxy067"
        or saved.get("creation_http_status") != 201
        or saved.get("uploaded_source_files") != 152
        or saved.get("estimated_compute_cost_usd") != 0.002207883052031199
        or saved.get("error") != "remote workload reported failure"
        or evidence.get("verified") is not False
        or evidence.get("sha256")
        != "0cd9a0462b719d6c860ca291dc76ab3e9441040453bc967890ce9f6688e4f62b"
        or validation.get("status") != "failed"
        or validation.get("source_unchanged") is not True
        or validation.get("junit_testcases")
        != {"tests": 3, "failures": 0, "errors": 3, "skipped": 0}
        or cleanup.get("owned_pod_absent") is not True
        or cleanup.get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("P7 functional-scout V1 packaging failure is not reconciled")
    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before authorized P7 retry")
    failed_cost = float(saved["estimated_compute_cost_usd"])
    prior = max(0.01, float(result["prior_cost_bound_usd"]) + failed_cost)
    offer = result["selected_offer"]
    projected = float(offer["rate_usd_per_hour"]) * (1200 / 3600)
    result.update(
        {
            "p7_functional_scout_v1_reconciled": True,
            "p7_functional_scout_v1_pod_id": saved["pod_id"],
            "p7_functional_scout_v1_estimated_compute_cost_usd": failed_cost,
            "p7_functional_scout_v1_failure_class": "upload_dependency_closure",
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
