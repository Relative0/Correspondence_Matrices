"""Read-only sequential preflight for bounded W3 development partitions."""

from __future__ import annotations

import json
import os
from pathlib import Path

import http_p7_w3_correctness_preflight_v1 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
CAMPAIGN_CAP_USD = 0.20
PHASE_CAP_USD = 0.10
STORAGE_RATE_RESERVE_USD_PER_HOUR = 0.01
SHARDS = {
    "ir-development-a": {"output": "p7-w3-split-ir-development-a-v4-001", "cells": 68},
    "ir-development-b": {"output": "p7-w3-split-ir-development-b-v4-001", "cells": 68},
    "relation-development-a": {"output": "p7-w3-split-relation-development-a-v4-001", "cells": 85},
    "relation-development-b": {"output": "p7-w3-split-relation-development-b-v4-001", "cells": 85},
}
ORDER = tuple(SHARDS)
SHARD_ID = os.environ.get("CM_W3_SPLIT_ID")
if SHARD_ID not in SHARDS:
    raise RuntimeError("CM_W3_SPLIT_ID must name one frozen W3 development partition")

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
host_ac_connected = previous.host_ac_connected


def _load(name: str) -> dict:
    return json.loads((HERE / name / "RUN.json").read_text(encoding="utf-8"))


def _clean(run: dict) -> bool:
    return (
        run.get("cleanup", {}).get("owned_pod_absent") is True
        and run.get("cleanup", {}).get("inventories") == {"v1": [], "v2": []}
    )


def _require_complete(run: dict, shard_id: str, cells: int) -> None:
    if (
        run.get("status") != "complete"
        or run.get("evidence", {}).get("verified") is not True
        or run.get("evidence", {}).get("p7", {}).get("shard_id") != shard_id
        or run.get("evidence", {}).get("p7", {}).get("cells") != cells
        or not _clean(run)
    ):
        raise RuntimeError("prior W3 partition is not reconciled: " + shard_id)


def check():
    monolith = _load("p7-w3-correctness-v1-001")
    transport = _load("p7-w3-shard-ir-regression-v1-001")
    ir_regression = _load("p7-w3-shard-ir-regression-v2-001")
    ir_development_timeout = _load("p7-w3-shard-ir-development-v2-001")
    relation_regression = _load("p7-w3-shard-relation-regression-v3-001")

    if (
        monolith.get("status") != "failed"
        or monolith.get("pod_id") != "d9z39u7pzvbju8"
        or monolith.get("evidence", {}).get("validation", {}).get("error")
        != "RuntimeError: p7-ir timed out"
        or monolith.get("evidence", {}).get("validation", {}).get("source_unchanged") is not True
        or not _clean(monolith)
    ):
        raise RuntimeError("monolithic W3 timeout is not reconciled")
    if (
        transport.get("status") != "failed"
        or transport.get("pod_id") != "pnpc0c0t6gu358"
        or transport.get("uploaded_source_files") != 0
        or transport.get("error") != "proxy HTTP 400"
        or not _clean(transport)
    ):
        raise RuntimeError("W3 V1 transport refusal is not reconciled")
    _require_complete(ir_regression, "ir-regression", 96)
    if (
        ir_development_timeout.get("status") != "failed"
        or ir_development_timeout.get("pod_id") != "alu08d0mlf02ba"
        or ir_development_timeout.get("uploaded_source_files") != 96
        or ir_development_timeout.get("evidence", {}).get("validation", {}).get("error")
        != "RuntimeError: p7-ir timed out"
        or ir_development_timeout.get("evidence", {}).get("validation", {}).get("source_unchanged") is not True
        or not _clean(ir_development_timeout)
    ):
        raise RuntimeError("W3 ir-development timeout is not reconciled")
    _require_complete(relation_regression, "relation-regression", 120)

    result = previous.check()
    fixed = (monolith, transport, ir_regression, ir_development_timeout, relation_regression)
    prior = result["prior_cost_bound_usd"] + sum(run["estimated_compute_cost_usd"] for run in fixed)
    prior_partitions = []
    for prior_id in ORDER[:ORDER.index(SHARD_ID)]:
        run = _load(SHARDS[prior_id]["output"])
        _require_complete(run, prior_id, SHARDS[prior_id]["cells"])
        prior += run["estimated_compute_cost_usd"]
        prior_partitions.append({
            "shard_id": prior_id,
            "pod_id": run["pod_id"],
            "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        })

    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before W3 development partition")

    offer = result["selected_offer"]
    projected = (offer["rate_usd_per_hour"] + STORAGE_RATE_RESERVE_USD_PER_HOUR) / 3
    result.update({
        "reconciled_fixed_pods": [run["pod_id"] for run in fixed],
        "prior_completed_partitions": prior_partitions,
        "shard_id": SHARD_ID,
        "shard_cells": SHARDS[SHARD_ID]["cells"],
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
