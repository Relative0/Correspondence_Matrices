"""Perform a credentialed, read-only RunPod readiness check for the CM campaign."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_runpod_config import load_runpod_config


REST_V1 = "https://rest.runpod.io/v1"
REST_V2 = "https://api.runpod.io/v2"
GRAPHQL = "https://api.runpod.io/graphql"
CAMPAIGN_ID = "cm-mega-prelaunch-20260914-008"
GPU_ID = "NVIDIA GeForce RTX 3090"
VCPU_COUNT = 16
MINIMUM_RAM_GB = 64.0
TOTAL_HOURS = 16.0
TOTAL_CAP_USD = 50.0
STORAGE_ESTIMATE_USD = 30.0 * 0.1 * (TOTAL_HOURS / (30.0 * 24.0))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_text(values: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def _float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def sanitize_inventory(payload: Any) -> dict[str, Any]:
    pods = payload if isinstance(payload, list) else payload.get("pods") if isinstance(payload, dict) else None
    if not isinstance(pods, list):
        raise ValueError("unexpected RunPod pod inventory schema")
    identifiers = [str(row.get("id", "")) for row in pods if isinstance(row, dict) and row.get("id")]
    states: dict[str, int] = {}
    for row in pods:
        if not isinstance(row, dict):
            continue
        state = str(row.get("desiredStatus") or row.get("status") or "unknown")
        states[state] = states.get(state, 0) + 1
    return {
        "pod_count": len(pods),
        "status_counts": dict(sorted(states.items())),
        "pod_id_set_sha256": sha256_text(identifiers),
        "pod_identifiers_recorded": False,
    }


def sanitize_cpu_catalog(payload: Any) -> list[dict[str, Any]]:
    cpus = payload.get("cpus") if isinstance(payload, dict) else None
    if not isinstance(cpus, list):
        raise ValueError("unexpected RunPod CPU catalog schema")
    rows = []
    for cpu in cpus:
        if not isinstance(cpu, dict):
            continue
        vcpu = cpu.get("vcpu") if isinstance(cpu.get("vcpu"), dict) else {}
        minimum, maximum = _float(vcpu.get("min")), _float(vcpu.get("max"))
        ram_per = _float(cpu.get("ramGbPerVcpu"))
        secure_per = _float((cpu.get("price") or {}).get("securePerVcpu"))
        valid_vcpu = minimum is not None and maximum is not None and minimum <= VCPU_COUNT <= maximum
        ram = ram_per * VCPU_COUNT if ram_per is not None else None
        rate = secure_per * VCPU_COUNT if secure_per is not None else None
        availability = str(cpu.get("availability") or "UNKNOWN")
        rows.append({
            "id": cpu.get("id"),
            "name": cpu.get("name"),
            "availability": availability,
            "requested_vcpu": VCPU_COUNT,
            "ram_gb": ram,
            "secure_usd_per_hour": rate,
            "eligible": bool(valid_vcpu and ram is not None and ram >= MINIMUM_RAM_GB and
                             rate is not None and availability in {"LOW", "MEDIUM", "HIGH"}),
            "available_data_centers": sorted(
                str(dc.get("id")) for dc in (cpu.get("dataCenters") or [])
                if isinstance(dc, dict) and dc.get("availability") in {"LOW", "MEDIUM", "HIGH"} and dc.get("id")
            ),
        })
    return sorted(rows, key=lambda row: (not row["eligible"], row["secure_usd_per_hour"] or math.inf, str(row["id"])))


def sanitize_gpu_offer(payload: Any) -> dict[str, Any]:
    price = payload.get("price") if isinstance(payload, dict) and isinstance(payload.get("price"), dict) else {}
    rate = _float(price.get("secure"))
    availability = str(payload.get("availability") or "UNKNOWN") if isinstance(payload, dict) else "UNKNOWN"
    return {
        "id": payload.get("id") if isinstance(payload, dict) else None,
        "name": payload.get("name") if isinstance(payload, dict) else None,
        "availability": availability,
        "secure_usd_per_hour": rate,
        "catalog_eligible": bool(payload.get("id") == GPU_ID and rate is not None and
                                 availability in {"LOW", "MEDIUM", "HIGH"}),
        "resource_envelope_source": "official public rate card; assigned CPU/RAM must be checked after creation",
        "advertised_vcpu": 16,
        "advertised_ram_gb": 125,
    }


def _get_json(session: requests.Session, url: str, *, params: dict[str, Any] | None = None) -> Any:
    response = session.get(url, params=params, timeout=30, allow_redirects=False)
    response.raise_for_status()
    return response.json()


def perform_readiness(api_key: str, *, campaign_id: str = CAMPAIGN_ID) -> dict[str, Any]:
    if not api_key or any(char.isspace() for char in api_key):
        raise ValueError("RUNPOD_API_KEY or RP_TOKEN is missing or malformed")
    client = requests.Session()
    client.trust_env = False
    client.headers["Authorization"] = "Bearer " + api_key
    params = {"include": "AVAILABILITY", "product": "POD", "vcpuCount": VCPU_COUNT}
    inv_v1 = sanitize_inventory(_get_json(client, REST_V1 + "/pods"))
    inv_v2 = sanitize_inventory(_get_json(client, REST_V2 + "/pods"))
    cpus = sanitize_cpu_catalog(_get_json(client, REST_V2 + "/catalog/cpus", params=params))
    gpu = sanitize_gpu_offer(_get_json(
        client,
        REST_V2 + "/catalog/gpus/" + quote(GPU_ID, safe=""),
        params={"include": "AVAILABILITY", "product": "POD", "cloud": "SECURE", "count": 1},
    ))
    account_response = client.post(
        GRAPHQL,
        json={"query": "query { myself { clientBalance currentSpendPerHr spendLimit } }"},
        timeout=30,
        allow_redirects=False,
    )
    account_response.raise_for_status()
    account = account_response.json().get("data", {}).get("myself", {})
    balance, current, limit = (_float(account.get(key)) for key in ("clientBalance", "currentSpendPerHr", "spendLimit"))
    best = next((row for row in cpus if row["eligible"]), None)
    candidate_rate = best["secure_usd_per_hour"] if best else gpu["secure_usd_per_hour"]
    max_compute = candidate_rate * TOTAL_HOURS if candidate_rate is not None else None
    quote_total = max_compute + STORAGE_ESTIMATE_USD if max_compute is not None else None
    credit_ok_cap = balance is not None and balance >= TOTAL_CAP_USD
    credit_ok_quote = balance is not None and quote_total is not None and balance >= quote_total
    spend_ok = limit is not None and current is not None and candidate_rate is not None and limit >= current + candidate_rate
    return {
        "schema": "cm-benchmark-runpod-account-readiness/v1",
        "campaign_id": campaign_id,
        "checked_utc": utc_now(),
        "operation": "credentialed_read_only_preflight",
        "transport": {
            "get_requests": 4,
            "read_only_graphql_queries": 1,
            "resource_writes": 0,
            "create_requests": 0,
            "upload_requests": 0,
            "delete_requests": 0,
        },
        "credential_handling": {
            "credential_values_recorded": False,
            "credential_values_uploaded": False,
            "credential_reference_names": ["RUNPOD_API_KEY", "RP_TOKEN"],
        },
        "inventory": {"v1": inv_v1, "v2": inv_v2, "consistent": inv_v1["pod_id_set_sha256"] == inv_v2["pod_id_set_sha256"]},
        "account": {
            "credit_sufficient_for_selected_quote": credit_ok_quote,
            "credit_sufficient_for_50_usd_emergency_ceiling": credit_ok_cap,
            "spend_limit_sufficient_for_candidate_hourly_rate": spend_ok,
            "financial_values_recorded": False,
        },
        "cpu_offers": cpus,
        "gpu_offer": gpu,
        "selected_proposal": ({
            "compute_type": "CPU",
            "cloud_type": "SECURE",
            **best,
            "compute_hours": TOTAL_HOURS,
            "compute_usd": max_compute,
            "storage_usd_prorated": STORAGE_ESTIMATE_USD,
            "quoted_total_usd": quote_total,
        } if best else None),
        "readiness": {
            "account_checks_pass": bool(credit_ok_quote and spend_ok),
            "qualifying_cpu_offer_present": best is not None,
            "catalog_snapshot_only_not_placement_guarantee": True,
            "paid_launch_authorized": False,
            "upload_authorized": False,
        },
    }


def write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=False)
    with path.open("xb") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--campaign-id", default=CAMPAIGN_ID)
    args = parser.parse_args()
    result = perform_readiness(
        load_runpod_config().api_key, campaign_id=args.campaign_id
    )
    write_new(args.output, result)
    selected = result["selected_proposal"] or {}
    print(json.dumps({
        "status": "pass" if result["readiness"]["account_checks_pass"] and selected else "blocked",
        "output": str(args.output),
        "inventory_pods": result["inventory"]["v2"]["pod_count"],
        "selected_offer": selected.get("id"),
        "hourly_usd": selected.get("secure_usd_per_hour"),
        "ram_gb": selected.get("ram_gb"),
        "quoted_total_usd": selected.get("quoted_total_usd"),
        "resource_writes": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
