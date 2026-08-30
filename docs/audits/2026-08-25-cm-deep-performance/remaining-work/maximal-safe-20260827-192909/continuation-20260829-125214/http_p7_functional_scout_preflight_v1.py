"""Read-only P7 isolated-runner functional-scout preflight."""

from __future__ import annotations

from pathlib import Path
import json

import http_native_bdd_persistence_preflight_v2 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
V2_OUTPUT = HERE / "native-bdd-persistence-v2-001"

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def check():
    saved = json.loads((V2_OUTPUT / "RUN.json").read_text(encoding="utf-8"))
    cleanup = saved.get("cleanup", {})
    evidence = saved.get("evidence") or {}
    validation = evidence.get("validation") or {}
    persistence = validation.get("persistence_summary") or {}
    if (
        saved.get("status") != "complete"
        or saved.get("pod_id") != "du48i5xcu9f6rw"
        or evidence.get("verified") is not True
        or evidence.get("sha256")
        != "44823dd37d5c913177ec8182f903d97adaf6e59c575fbe5b6768fdcdbdc6975c"
        or validation.get("status") != "complete"
        or validation.get("source_unchanged") is not True
        or validation.get("junit_testcases")
        != {"tests": 25, "failures": 0, "errors": 0, "skipped": 0}
        or persistence.get("status") != "passed"
        or persistence.get("planned_cells") != 4
        or persistence.get("exact_relation_rows") != 8
        or persistence.get("serialized_artifact_deterministic_across_blocks") is not True
        or cleanup.get("owned_pod_absent") is not True
        or cleanup.get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("canonical native BDD persistence V2 result is not reconciled")
    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before P7 functional scout")
    result["native_bdd_persistence_v2_reconciled"] = True
    result["native_bdd_persistence_v2_pod_id"] = saved["pod_id"]
    result["native_bdd_persistence_v2_estimated_compute_cost_usd"] = saved.get("estimated_compute_cost_usd")
    result["current_inventories"] = current
    result["authorized_aggregate_campaign_cap_usd"] = 10.0
    return result
