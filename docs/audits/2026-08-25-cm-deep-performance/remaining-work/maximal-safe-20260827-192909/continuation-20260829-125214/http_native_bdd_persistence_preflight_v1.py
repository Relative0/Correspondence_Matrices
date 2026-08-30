"""Read-only native CUDD BDD persistence preflight after successful V7."""

from __future__ import annotations

from pathlib import Path
import json

import http_native_persistence_preflight_v7 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
V7_OUTPUT = HERE / "native-persistence-v7-001"

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def check():
    saved = json.loads((V7_OUTPUT / "RUN.json").read_text(encoding="utf-8"))
    cleanup = saved.get("cleanup", {})
    evidence = saved.get("evidence") or {}
    persistence = evidence.get("persistence") or {}
    if (
        saved.get("status") != "complete"
        or saved.get("pod_id") != "dgfqzk61vl7cbe"
        or evidence.get("verified") is not True
        or evidence.get("sha256")
        != "5755fb58f5a048ef3daf21b3601f511c338175921fa5d1f81536fe2904d4cead"
        or persistence.get("cells") != 16
        or persistence.get("exact_relation_rows") != 32
        or cleanup.get("owned_pod_absent") is not True
        or cleanup.get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("native persistence V7 result is not reconciled")
    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before native CUDD BDD persistence")
    result["native_persistence_v7_reconciled"] = True
    result["native_persistence_v7_pod_id"] = saved["pod_id"]
    result["native_persistence_v7_estimated_compute_cost_usd"] = saved.get("estimated_compute_cost_usd")
    result["current_inventories"] = current
    result["authorized_aggregate_campaign_cap_usd"] = 10.0
    return result

