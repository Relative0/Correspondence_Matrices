"""Read-only preflight for the exact-96 P7 transport-fix retry."""

from __future__ import annotations

import json
import math
from pathlib import Path

import http_p7_functional_scout_preflight_v2 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.previous.PRIOR_HTTP_RESERVE
V2_OUTPUT = HERE / "p7-functional-scout-v2-001"
V3_OUTPUT = HERE / "p7-functional-scout-v3-001"
V4_OUTPUT = HERE / "p7-functional-scout-v4-freeze-closed-001"
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
    v2 = _load(V2_OUTPUT)
    if (
        v2.get("status") != "failed"
        or v2.get("pod_id") != "r044pqp2vgp7cy"
        or v2.get("creation_http_status") != 201
        or v2.get("error_type") != "AttributeError"
        or v2.get("uploaded_source_files") != 0
        or v2.get("cleanup", {}).get("owned_pod_absent") is not True
        or v2.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
    ):
        raise RuntimeError("exact-96 V2 local transport failure is not reconciled")
    v3 = _load(V3_OUTPUT)
    if (
        v3.get("status") != "failed"
        or v3.get("pod_id") != "2fzt8mu6ji6nmw"
        or v3.get("evidence", {}).get("validation", {}).get("source_unchanged") is not True
        or v3.get("cleanup", {}).get("owned_pod_absent") is not True
        or v3.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
        or not math.isfinite(v3.get("estimated_compute_cost_usd", math.nan))
    ):
        raise RuntimeError("related P7 V3 outcome is not reconciled")
    v4 = _load(V4_OUTPUT)
    if (
        v4.get("status") != "failed"
        or v4.get("creation_attempted") is not False
        or v4.get("pod_created") is not False
        or v4.get("uploaded_source_files") != 0
        or v4.get("error") != "nonempty RunPod inventory before V8"
    ):
        raise RuntimeError("related P7 V4 no-create outcome is not reconciled")

    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before exact-96 retry")

    v2_rate = float(v2["quoted_rate_usd_per_hour"])
    # The V2 RUN file could not calculate cost after its local AttributeError.
    # Bound it by a full minute although the owned pod lived for under six seconds.
    v2_cost_bound = v2_rate / 60
    prior = result["prior_cost_bound_usd"] + v2_cost_bound + v3["estimated_compute_cost_usd"]
    offer = result["selected_offer"]
    projected = (offer["rate_usd_per_hour"] + STORAGE_RATE_RESERVE_USD_PER_HOUR) / 3
    result.update({
        "exact96_v2_reconciled": True,
        "exact96_v2_pod_id": v2["pod_id"],
        "exact96_v2_uploaded_source_files": 0,
        "exact96_v2_cost_bound_usd": v2_cost_bound,
        "related_v3_reconciled": True,
        "related_v3_pod_id": v3["pod_id"],
        "related_v3_estimated_compute_cost_usd": v3["estimated_compute_cost_usd"],
        "related_v4_no_create_reconciled": True,
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
