"""Read-only preflight preserving and reconciling the V9 native failure."""

from __future__ import annotations

from pathlib import Path

import http_native_scout_preflight_v9 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
V9_OUTPUT = HERE / "native-procfs-v9-001"

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def check():
    saved = previous.previous.previous.previous.load(V9_OUTPUT / "RUN.json")
    cleanup = saved.get("cleanup", {})
    if (
        saved.get("status") != "failed"
        or saved.get("error") != "remote workload reported failure"
        or saved.get("pod_id") != "jwyi342sjmjkcj"
        or saved.get("creation_http_status") != 201
        or cleanup.get("owned_pod_absent") is not True
        or cleanup.get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("V9 native failure is not reconciled")
    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before V10")
    result["v9_native_failure_reconciled"] = True
    result["v9_pod_id"] = saved["pod_id"]
    result["v9_estimated_compute_cost_usd"] = saved.get("estimated_compute_cost_usd")
    result["current_inventories"] = current
    result["authorized_aggregate_campaign_cap_usd"] = 10.0
    return result
