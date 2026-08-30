"""Read-only native-persistence V1 preflight preserving and reconciling V20."""

from __future__ import annotations

from pathlib import Path
import json

import http_native_gap_preflight_v20 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
V20_OUTPUT = HERE / "native-gap-v20-001"

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def check():
    saved = json.loads((V20_OUTPUT / "RUN.json").read_text(encoding="utf-8"))
    cleanup = saved.get("cleanup", {})
    evidence = saved.get("evidence", {})
    if (
        saved.get("status") != "complete"
        or saved.get("pod_id") != "rg3zlg5gbdbp5p"
        or evidence.get("verified") is not True
        or evidence.get("sha256") != "3f508be7c11bad4242dfcd64c439dcc4e4b3a8fda455d725a384ff857346b6d2"
        or cleanup.get("owned_pod_absent") is not True
        or cleanup.get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("V20 native readiness result is not reconciled")
    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before native persistence V1")
    result["v20_native_readiness_reconciled"] = True
    result["v20_pod_id"] = saved["pod_id"]
    result["v20_estimated_compute_cost_usd"] = saved.get("estimated_compute_cost_usd")
    result["current_inventories"] = current
    result["authorized_aggregate_campaign_cap_usd"] = 10.0
    return result

