"""Read-only canonical CUDD BDD persistence retry preflight."""

from __future__ import annotations

from pathlib import Path
import json

import http_native_bdd_persistence_preflight_v1 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
V1_OUTPUT = HERE / "native-bdd-persistence-v1-001"

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def check():
    saved = json.loads((V1_OUTPUT / "RUN.json").read_text(encoding="utf-8"))
    cleanup = saved.get("cleanup", {})
    evidence = saved.get("evidence") or {}
    validation = evidence.get("validation") or {}
    persistence = validation.get("persistence_summary") or {}
    if (
        saved.get("status") != "failed"
        or saved.get("pod_id") != "8fh5st71uqe2pe"
        or saved.get("error") != "remote workload reported failure"
        or evidence.get("verified") is not False
        or evidence.get("sha256")
        != "5db066fef0b6f748fa100245725cf134b36c6c8a2a35bd287ca1cf86f8e82004"
        or validation.get("status") != "complete"
        or validation.get("source_unchanged") is not True
        or validation.get("junit_testcases")
        != {"tests": 22, "failures": 0, "errors": 0, "skipped": 0}
        or persistence.get("status") != "passed"
        or persistence.get("planned_cells") != 4
        or persistence.get("exact_relation_rows") != 8
        or persistence.get("serialized_artifact_deterministic_across_blocks") is not False
        or cleanup.get("owned_pod_absent") is not True
        or cleanup.get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("native BDD persistence V1 result is not reconciled")
    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before canonical native CUDD BDD persistence retry")
    result["native_bdd_persistence_v1_reconciled"] = True
    result["native_bdd_persistence_v1_pod_id"] = saved["pod_id"]
    result["native_bdd_persistence_v1_estimated_compute_cost_usd"] = saved.get("estimated_compute_cost_usd")
    result["native_bdd_persistence_v1_failure_class"] = "raw_CUDD_dump_byte_nondeterminism"
    result["current_inventories"] = current
    result["authorized_aggregate_campaign_cap_usd"] = 10.0
    return result
