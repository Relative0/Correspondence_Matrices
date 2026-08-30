"""V2 read-only sequential preflight for one frozen P7 W3 correctness shard."""

from __future__ import annotations

import json
import os
from pathlib import Path

import http_p7_w3_correctness_preflight_v1 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
MONOLITH = HERE / "p7-w3-correctness-v1-001"
TRANSPORT_FAILURE = HERE / "p7-w3-shard-ir-regression-v1-001"
SHARDS = {
    "ir-regression": {"output": "p7-w3-shard-ir-regression-v2-001", "cells": 96},
    "ir-development": {"output": "p7-w3-shard-ir-development-v2-001", "cells": 136},
    "relation-regression": {"output": "p7-w3-shard-relation-regression-v2-001", "cells": 120},
    "relation-development": {"output": "p7-w3-shard-relation-development-v2-001", "cells": 170},
}
ORDER = tuple(SHARDS)
SHARD_ID = os.environ.get("CM_W3_SHARD_ID")
if SHARD_ID not in SHARDS:
    raise RuntimeError("CM_W3_SHARD_ID must name one frozen W3 shard")
CAMPAIGN_CAP_USD = 0.20
PHASE_CAP_USD = 0.10
STORAGE_RATE_RESERVE_USD_PER_HOUR = 0.01

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
host_ac_connected = previous.host_ac_connected


def _load(output: Path) -> dict:
    return json.loads((output / "RUN.json").read_text(encoding="utf-8"))


def check():
    monolith = _load(MONOLITH)
    if (
        monolith.get("status") != "failed"
        or monolith.get("pod_id") != "d9z39u7pzvbju8"
        or monolith.get("creation_http_status") != 201
        or monolith.get("uploaded_source_files") != 96
        or monolith.get("evidence", {}).get("validation", {}).get("error") != "RuntimeError: p7-ir timed out"
        or monolith.get("evidence", {}).get("validation", {}).get("source_unchanged") is not True
        or monolith.get("cleanup", {}).get("owned_pod_absent") is not True
        or monolith.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("monolithic W3 timeout outcome is not reconciled")

    transport_failure = _load(TRANSPORT_FAILURE)
    if (
        transport_failure.get("status") != "failed"
        or transport_failure.get("pod_id") != "pnpc0c0t6gu358"
        or transport_failure.get("creation_http_status") != 201
        or transport_failure.get("uploaded_source_files") != 0
        or transport_failure.get("error") != "proxy HTTP 400"
        or transport_failure.get("cleanup", {}).get("owned_pod_absent") is not True
        or transport_failure.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("W3 shard V1 bootstrap refusal is not reconciled")

    result = previous.check()
    prior = (result["prior_cost_bound_usd"] + monolith["estimated_compute_cost_usd"]
             + transport_failure["estimated_compute_cost_usd"])
    prior_shards = []
    for prior_id in ORDER[:ORDER.index(SHARD_ID)]:
        run = _load(HERE / SHARDS[prior_id]["output"])
        if (
            run.get("status") != "complete"
            or run.get("evidence", {}).get("verified") is not True
            or run.get("evidence", {}).get("p7", {}).get("shard_id") != prior_id
            or run.get("evidence", {}).get("p7", {}).get("cells") != SHARDS[prior_id]["cells"]
            or run.get("cleanup", {}).get("owned_pod_absent") is not True
            or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
        ):
            raise RuntimeError("prior W3 shard is not reconciled: " + prior_id)
        prior += run["estimated_compute_cost_usd"]
        prior_shards.append({"shard_id": prior_id, "pod_id": run["pod_id"],
                             "estimated_compute_cost_usd": run["estimated_compute_cost_usd"]})

    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before W3 shard")

    offer = result["selected_offer"]
    projected = (offer["rate_usd_per_hour"] + STORAGE_RATE_RESERVE_USD_PER_HOUR) / 3
    result.update({
        "monolithic_w3_timeout_reconciled": True,
        "monolithic_w3_pod_id": monolith["pod_id"],
        "monolithic_w3_estimated_compute_cost_usd": monolith["estimated_compute_cost_usd"],
        "w3_shard_v1_transport_failure_reconciled": True,
        "w3_shard_v1_transport_failure_pod_id": transport_failure["pod_id"],
        "w3_shard_v1_transport_failure_estimated_compute_cost_usd": transport_failure["estimated_compute_cost_usd"],
        "shard_id": SHARD_ID,
        "shard_cells": SHARDS[SHARD_ID]["cells"],
        "prior_completed_shards": prior_shards,
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
