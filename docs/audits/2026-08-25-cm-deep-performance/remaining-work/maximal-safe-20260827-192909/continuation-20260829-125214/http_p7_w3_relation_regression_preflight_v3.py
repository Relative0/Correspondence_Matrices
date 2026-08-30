"""Read-only preflight for the post-timeout W3 relation-regression shard."""

from __future__ import annotations

import json
from pathlib import Path

import http_p7_w3_correctness_preflight_v1 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
MONOLITH = HERE / "p7-w3-correctness-v1-001"
TRANSPORT_FAILURE = HERE / "p7-w3-shard-ir-regression-v1-001"
IR_REGRESSION = HERE / "p7-w3-shard-ir-regression-v2-001"
IR_DEVELOPMENT_TIMEOUT = HERE / "p7-w3-shard-ir-development-v2-001"
CAMPAIGN_CAP_USD = 0.20
PHASE_CAP_USD = 0.10
STORAGE_RATE_RESERVE_USD_PER_HOUR = 0.01

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
host_ac_connected = previous.host_ac_connected


def _load(output: Path) -> dict:
    return json.loads((output / "RUN.json").read_text(encoding="utf-8"))


def _clean(run: dict) -> bool:
    return (
        run.get("cleanup", {}).get("owned_pod_absent") is True
        and run.get("cleanup", {}).get("inventories") == {"v1": [], "v2": []}
    )


def check():
    monolith = _load(MONOLITH)
    if (
        monolith.get("status") != "failed"
        or monolith.get("pod_id") != "d9z39u7pzvbju8"
        or monolith.get("evidence", {}).get("validation", {}).get("error")
        != "RuntimeError: p7-ir timed out"
        or monolith.get("evidence", {}).get("validation", {}).get("source_unchanged") is not True
        or not _clean(monolith)
    ):
        raise RuntimeError("monolithic W3 timeout outcome is not reconciled")

    transport = _load(TRANSPORT_FAILURE)
    if (
        transport.get("status") != "failed"
        or transport.get("pod_id") != "pnpc0c0t6gu358"
        or transport.get("uploaded_source_files") != 0
        or transport.get("error") != "proxy HTTP 400"
        or not _clean(transport)
    ):
        raise RuntimeError("W3 V1 bootstrap refusal is not reconciled")

    ir_regression = _load(IR_REGRESSION)
    if (
        ir_regression.get("status") != "complete"
        or ir_regression.get("evidence", {}).get("verified") is not True
        or ir_regression.get("evidence", {}).get("p7", {}).get("shard_id") != "ir-regression"
        or ir_regression.get("evidence", {}).get("p7", {}).get("cells") != 96
        or not _clean(ir_regression)
    ):
        raise RuntimeError("W3 ir-regression shard is not reconciled")

    ir_development = _load(IR_DEVELOPMENT_TIMEOUT)
    if (
        ir_development.get("status") != "failed"
        or ir_development.get("pod_id") != "alu08d0mlf02ba"
        or ir_development.get("uploaded_source_files") != 96
        or ir_development.get("evidence", {}).get("validation", {}).get("error")
        != "RuntimeError: p7-ir timed out"
        or ir_development.get("evidence", {}).get("validation", {}).get("source_unchanged") is not True
        or not _clean(ir_development)
    ):
        raise RuntimeError("W3 ir-development timeout is not reconciled")

    result = previous.check()
    prior_runs = (monolith, transport, ir_regression, ir_development)
    prior = result["prior_cost_bound_usd"] + sum(
        run["estimated_compute_cost_usd"] for run in prior_runs
    )

    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before W3 relation-regression shard")

    offer = result["selected_offer"]
    projected = (offer["rate_usd_per_hour"] + STORAGE_RATE_RESERVE_USD_PER_HOUR) / 3
    result.update({
        "reconciled_prior_pods": [run["pod_id"] for run in prior_runs],
        "shard_id": "relation-regression",
        "shard_cells": 120,
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
