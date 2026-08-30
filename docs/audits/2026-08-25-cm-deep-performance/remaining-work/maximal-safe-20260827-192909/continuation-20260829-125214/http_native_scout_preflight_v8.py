"""Read-only V8 preflight including reconciliation of the V7 proxy-404 pod."""

from __future__ import annotations

from pathlib import Path

import http_native_scout_preflight_v7 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
V7_OUTPUT = HERE / "native-procfs-v7-001"
V7_RUN = V7_OUTPUT / "RUN.json"

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def check():
    saved = previous.previous.load(V7_RUN)
    cleanup = saved.get("cleanup", {})
    if (
        saved.get("status") != "failed"
        or saved.get("error") != "proxy HTTP 404"
        or saved.get("pod_id") != "3o7r0za7cm72yn"
        or saved.get("creation_http_status") != 201
        or saved.get("uploaded_source_files") != 0
        or cleanup.get("owned_pod_absent") is not True
        or cleanup.get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("V7 proxy-404 attempt is not reconciled")
    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before V8")
    result["v7_proxy_404_attempt_reconciled"] = True
    result["v7_pod_id"] = saved["pod_id"]
    result["v7_estimated_compute_cost_usd"] = saved.get("estimated_compute_cost_usd")
    result["current_inventories"] = current
    result["authorized_aggregate_campaign_cap_usd"] = 10.0
    result["ready"] = bool(result.get("ready") and result.get("host_ac_connected"))
    return result
