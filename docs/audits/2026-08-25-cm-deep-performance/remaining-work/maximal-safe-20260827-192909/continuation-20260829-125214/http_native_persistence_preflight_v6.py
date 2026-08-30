"""Read-only native-persistence V6 preflight preserving and reconciling V5."""

from __future__ import annotations

from pathlib import Path
import json

import http_native_persistence_preflight_v5 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
V5_OUTPUT = HERE / "native-persistence-v5-001"

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def check():
    saved = json.loads((V5_OUTPUT / "RUN.json").read_text(encoding="utf-8"))
    cleanup = saved.get("cleanup", {})
    if (
        saved.get("status") != "failed"
        or saved.get("error") != "proxy HTTP 404"
        or saved.get("pod_id") != "hmqvleqhp5n815"
        or saved.get("uploaded_source_files") != 0
        or cleanup.get("owned_pod_absent") is not True
        or cleanup.get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("native persistence V5 result is not reconciled")
    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before native persistence V6")
    result["native_persistence_v5_reconciled"] = True
    result["native_persistence_v5_pod_id"] = saved["pod_id"]
    result["native_persistence_v5_estimated_compute_cost_usd"] = saved.get("estimated_compute_cost_usd")
    result["current_inventories"] = current
    result["authorized_aggregate_campaign_cap_usd"] = 10.0
    return result

