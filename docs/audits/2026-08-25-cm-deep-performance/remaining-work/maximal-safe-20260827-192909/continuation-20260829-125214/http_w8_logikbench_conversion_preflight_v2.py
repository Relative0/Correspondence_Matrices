"""Read-only preflight for the corrected W8 LogikBench V3 conversion scout."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path

import http_p7_functional_scout_preflight_v6_exact96_retry as transport
from verify_w8_logikbench_conversion_upload_v3 import verify as verify_upload


HERE = Path(__file__).resolve().parent
V1, V2 = transport.V1, transport.V2
FLAVORS = ("cpu3c", "cpu3m", "cpu5c")
RATE_CAP = 0.25
PHASE_CAP_USD = 0.10
CAMPAIGN_CAP_USD = 5.00
STORAGE_RATE_RESERVE_USD_PER_HOUR = 0.01
MISSING_COST_RESERVE_USD = 0.05
UNATTRIBUTED_OR_LAGGING_RESERVE_USD = 0.25
PRIOR_HTTP_RESERVE = UNATTRIBUTED_OR_LAGGING_RESERVE_USD
CAMPAIGN_START = "2026-08-27T00:00:00Z"
V2_OUTPUT = HERE / "w8-logikbench-conversion-v2-001"

utc_now = transport.utc_now
session = transport.session
inventory = transport.inventory
host_ac_connected = transport.host_ac_connected


def get_offer(flavor: str) -> dict:
    with session() as client:
        response = client.get(
            V2 + "/catalog/cpus/" + flavor,
            params={"include": "AVAILABILITY", "product": "POD", "vcpuCount": 2},
            timeout=15,
            allow_redirects=False,
        )
        response.raise_for_status()
        body = response.json()
    result = {
        field: body.get(field)
        for field in ("id", "availability", "price", "vcpu", "ramGbPerVcpu", "dataCenters")
    }
    result["checked_utc"] = utc_now()
    rate = float(body["price"]["securePerVcpu"]) * 2
    ram = float(body["ramGbPerVcpu"]) * 2
    result.update(rate_usd_per_hour=rate, ram_gb=ram)
    result["eligible"] = bool(
        body.get("id") == flavor
        and body.get("availability") in ("LOW", "MEDIUM", "HIGH")
        and math.isfinite(rate)
        and 0 < rate <= RATE_CAP
        and math.isfinite(ram)
        and ram >= 4
        and body["vcpu"]["min"] <= 2 <= body["vcpu"]["max"]
    )
    return result


def local_campaign_cost_bound() -> dict:
    by_pod = {}
    for path in HERE.rglob("RUN.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        pod_id = record.get("pod_id")
        if not isinstance(pod_id, str) or not record.get("pod_created"):
            continue
        value = record.get("estimated_compute_cost_usd")
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
            previous = by_pod.get(pod_id)
            if previous is None or value > previous:
                by_pod[pod_id] = float(value)
        elif pod_id not in by_pod:
            by_pod[pod_id] = None
    known = sum(value for value in by_pod.values() if value is not None)
    missing = sorted(pod_id for pod_id, value in by_pod.items() if value is None)
    return {
        "unique_created_pods": len(by_pod),
        "known_estimated_compute_cost_usd": known,
        "missing_cost_pod_ids": missing,
        "missing_cost_reserve_each_usd": MISSING_COST_RESERVE_USD,
        "local_bound_before_unattributed_reserve_usd": known + len(missing) * MISSING_COST_RESERVE_USD,
    }


def check() -> dict:
    upload = verify_upload()
    acquisition = json.loads((HERE / "W8-LOGIKBENCH-ACQUISITION.json").read_text(encoding="utf-8"))
    admission = json.loads((HERE / "W8-LOGIKBENCH-STATIC-ADMISSION.json").read_text(encoding="utf-8"))
    w3_audit = json.loads((HERE / "P7-W3-FINAL-INDEPENDENT-AUDIT.json").read_text(encoding="utf-8"))
    w3_postflight = json.loads((HERE / "P7-W3-FINAL-POSTFLIGHT.json").read_text(encoding="utf-8"))
    v2 = json.loads((V2_OUTPUT / "RUN.json").read_text(encoding="utf-8"))
    before = json.loads((V2_OUTPUT / "evidence/run-output/SOURCE-BEFORE.json").read_text(encoding="utf-8"))
    after = json.loads((V2_OUTPUT / "evidence/run-output/SOURCE-AFTER.json").read_text(encoding="utf-8"))
    if (
        acquisition.get("commit") != "891ced851ea4c2f9a46f6ab991eeee199e2fd516"
        or acquisition.get("clean") is not True
        or acquisition.get("repository_code_executed") is not False
        or admission.get("static_admitted_count") != 70
        or admission.get("ready_for_yosys_conversion_scout") is not True
        or admission.get("comparative_timing_inspected") is not False
        or w3_audit.get("verified") is not True
        or w3_postflight.get("all_created_pods_absent") is not True
        or w3_postflight.get("inventories") != {"v1": [], "v2": []}
        or v2.get("status") != "failed"
        or v2.get("pod_id") != "71gv8a3dttwnma"
        or v2.get("creation_http_status") != 201
        or v2.get("uploaded_source_files") != 159
        or v2.get("error") != "remote workload reported failure"
        or v2.get("cleanup", {}).get("owned_pod_absent") is not True
        or v2.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
        or not math.isfinite(v2.get("estimated_compute_cost_usd", math.nan))
        or before != after
    ):
        raise RuntimeError("prior W3/W8 evidence is not ready for conversion")

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(get_offer, flavor) for flavor in FLAVORS]
        offers = []
        for flavor, future in zip(FLAVORS, futures):
            try:
                offers.append(future.result())
            except Exception as exc:
                offers.append({"id": flavor, "eligible": False, "error_type": type(exc).__name__})
    eligible = [offer for offer in offers if offer.get("eligible")]
    priority = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    eligible.sort(key=lambda offer: (
        offer["rate_usd_per_hour"], -priority[offer["availability"]], FLAVORS.index(offer["id"])
    ))

    with session() as client:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
        response = client.get(
            V2 + "/billing/pods",
            params={"startTime": CAMPAIGN_START, "endTime": utc_now()},
            timeout=15,
            allow_redirects=False,
        )
        response.raise_for_status()
        metadata = response.json()["metadata"]
        billing_total = float(metadata["totals"]["totalAmount"])
        response = client.post(
            "https://api.runpod.io/graphql",
            json={"query": "query { myself { clientBalance currentSpendPerHr spendLimit } }"},
            timeout=15,
            allow_redirects=False,
        )
        response.raise_for_status()
        body = response.json()
        if body.get("errors"):
            raise RuntimeError("account readiness query failed")
        account = body["data"]["myself"]

    local = local_campaign_cost_bound()
    attributable_floor = max(local["local_bound_before_unattributed_reserve_usd"], billing_total)
    prior = attributable_floor + UNATTRIBUTED_OR_LAGGING_RESERVE_USD
    selected = eligible[0] if eligible else None
    projected = (
        (selected["rate_usd_per_hour"] + STORAGE_RATE_RESERVE_USD_PER_HOUR) / 3
        if selected else None
    )
    credit_sufficient = bool(
        projected is not None and float(account["clientBalance"]) >= projected
    )
    spend_limit_sufficient = bool(
        selected is not None
        and account.get("spendLimit") is not None
        and float(account["spendLimit"])
        >= float(account["currentSpendPerHr"]) + selected["rate_usd_per_hour"] + STORAGE_RATE_RESERVE_USD_PER_HOUR
    )
    result = {
        "checked_utc": utc_now(),
        "ready": False,
        "resource_writes": 0,
        "credential_values_recorded": False,
        "host_ac_connected": host_ac_connected(),
        "upload_verification": upload,
        "offers": offers,
        "selected_offer": selected,
        "current_inventories": current,
        "billing": {field: metadata.get(field) for field in ("query", "recordCount", "uniquePodCount", "totals")},
        "billing_may_lag": True,
        "observed_campaign_billing_usd": billing_total,
        "local_campaign_accounting": local,
        "attributable_floor_usd": attributable_floor,
        "unattributed_or_lagging_reserve_usd": UNATTRIBUTED_OR_LAGGING_RESERVE_USD,
        "prior_cost_bound_usd": prior,
        "projected_20_min_cost_usd": projected,
        "projected_aggregate_cost_usd": None if projected is None else prior + projected,
        "authorized_phase_cap_usd": PHASE_CAP_USD,
        "authorized_aggregate_campaign_cap_usd": CAMPAIGN_CAP_USD,
        "credit_sufficient": credit_sufficient,
        "spend_limit_sufficient": spend_limit_sufficient,
        "w3_final_audit_verified": True,
        "w3_final_postflight_clean": True,
        "w8_static_candidates": 70,
        "w8_v2_scope_bug_reconciled": True,
        "w8_v2_pod_id": v2["pod_id"],
        "w8_v2_estimated_compute_cost_usd": v2["estimated_compute_cost_usd"],
        "w8_v2_source_unchanged_from_raw_identity": True,
        "performance_measurement": False,
    }
    result["ready"] = bool(
        selected
        and current == {"v1": [], "v2": []}
        and result["host_ac_connected"]
        and math.isfinite(prior)
        and prior >= PRIOR_HTTP_RESERVE
        and projected is not None
        and projected <= PHASE_CAP_USD
        and prior + projected <= CAMPAIGN_CAP_USD
        and credit_sufficient
        and spend_limit_sufficient
    )
    return result


if __name__ == "__main__":
    try:
        value = check()
    except Exception as exc:
        value = {"checked_utc": utc_now(), "ready": False, "error_type": type(exc).__name__, "resource_writes": 0}
    print(json.dumps(value, indent=2, sort_keys=True))
    raise SystemExit(0 if value.get("ready") else 1)
