"""Read-only preflight for the full 58-case P7 W3 correctness scout."""

from __future__ import annotations

import json
from pathlib import Path

import http_p7_functional_scout_preflight_v6_exact96_retry as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
SUCCESS = HERE / "p7-functional-scout-v6-exact96-001"
CAMPAIGN_CAP_USD = 0.20
PHASE_CAP_USD = 0.10
STORAGE_RATE_RESERVE_USD_PER_HOUR = 0.01

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
host_ac_connected = previous.host_ac_connected


def check():
    run = json.loads((SUCCESS / "RUN.json").read_text(encoding="utf-8"))
    audit = json.loads((SUCCESS / "INDEPENDENT-RESULT-AUDIT.json").read_text(encoding="utf-8"))
    postflight = json.loads((SUCCESS / "INDEPENDENT-POSTFLIGHT.json").read_text(encoding="utf-8"))
    if (
        run.get("status") != "complete"
        or run.get("pod_id") != "6mlqn19hnco1b0"
        or run.get("uploaded_source_files") != 96
        or run.get("evidence", {}).get("verified") is not True
        or run.get("evidence", {}).get("p7", {}).get("cells") != 36
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
        or audit.get("status") != "passed"
        or audit.get("total_cells") != 36
        or audit.get("unique_worker_pids") != 36
        or audit.get("source_unchanged") is not True
        or postflight.get("inventories") != {"v1": [], "v2": []}
        or postflight.get("owned_pod_absent") is not True
    ):
        raise RuntimeError("exact-96 functional gate is not reconciled")

    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before W3 correctness scout")

    prior = result["prior_cost_bound_usd"] + run["estimated_compute_cost_usd"]
    offer = result["selected_offer"]
    projected = (offer["rate_usd_per_hour"] + STORAGE_RATE_RESERVE_USD_PER_HOUR) / 3
    result.update({
        "exact96_functional_gate_reconciled": True,
        "exact96_functional_gate_pod_id": run["pod_id"],
        "exact96_functional_gate_estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "w3_cases_per_policy": 58,
        "w3_ir_cells": 232,
        "w3_relation_cells": 290,
        "w3_total_cells": 522,
        "prior_cost_bound_usd": prior,
        "projected_20_min_cost_usd": projected,
        "projected_aggregate_cost_usd": prior + projected,
        "authorized_aggregate_campaign_cap_usd": CAMPAIGN_CAP_USD,
        "current_inventories": current,
    })
    result["ready"] = bool(
        result.get("ready")
        and projected < PHASE_CAP_USD
        and prior + projected < CAMPAIGN_CAP_USD
    )
    return result
