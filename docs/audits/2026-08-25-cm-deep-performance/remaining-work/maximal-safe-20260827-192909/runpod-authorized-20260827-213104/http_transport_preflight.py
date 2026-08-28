"""Read-only preparation for the authorized two-vCPU HTTP transport retry."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT))
from cm_runpod_config import load_runpod_config

V1 = "https://rest.runpod.io/v1"
V2 = "https://api.runpod.io/v2"
FLAVORS = ("cpu3c", "cpu3m", "cpu5c")
RATE_CAP = 0.25
STORAGE_RESERVE_PER_HOUR = 0.01


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def session():
    config = load_runpod_config()
    if not config.api_key or any(character.isspace() for character in config.api_key):
        raise RuntimeError("missing or malformed Runpod credential")
    client = requests.Session()
    client.trust_env = False
    client.headers["Authorization"] = "Bearer " + config.api_key
    return client


def inventory(client, base):
    response = client.get(base + "/pods", timeout=10, allow_redirects=False)
    response.raise_for_status()
    body = response.json()
    pods = body if isinstance(body, list) else body.get("pods")
    if not isinstance(pods, list):
        raise ValueError("invalid inventory schema")
    return [{field: pod.get(field) for field in ("id", "name", "desiredStatus", "status")}
            for pod in pods]


def get_offer(flavor):
    with session() as client:
        response = client.get(V2 + "/catalog/cpus/" + flavor,
                              params={"include": "AVAILABILITY", "product": "POD", "vcpuCount": 2},
                              timeout=15, allow_redirects=False)
        response.raise_for_status()
        body = response.json()
    # The catalog is public product metadata, not a pod environment response.
    result = {field: body.get(field) for field in ("id", "availability", "price", "vcpu", "ramGbPerVcpu", "dataCenters")}
    result["checked_utc"] = utc_now()
    rate = float(body["price"]["securePerVcpu"]) * 2
    ram = float(body["ramGbPerVcpu"]) * 2
    result["rate_usd_per_hour"] = rate
    result["ram_gb"] = ram
    result["eligible"] = (
        body.get("id") == flavor and body.get("availability") in ("LOW", "MEDIUM", "HIGH")
        and math.isfinite(rate) and 0 < rate <= RATE_CAP
        and math.isfinite(ram) and ram >= 4
        and body["vcpu"]["min"] <= 2 <= body["vcpu"]["max"]
    )
    return result


def check():
    result = {"checked_utc": utc_now(), "resource_writes": 0, "credential_values_recorded": False}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(get_offer, flavor) for flavor in FLAVORS]
        offers = []
        for flavor, future in zip(FLAVORS, futures):
            try:
                offers.append(future.result())
            except Exception as exc:
                offers.append({"id": flavor, "eligible": False, "error_type": type(exc).__name__})
    result["offers"] = offers
    with session() as client:
        result["inventories"] = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
        response = client.get(V2 + "/billing/pods",
                              params={"startTime": "2026-08-27T00:00:00Z", "endTime": utc_now()},
                              timeout=15, allow_redirects=False)
        response.raise_for_status()
        metadata = response.json()["metadata"]
        prior_cost = float(metadata["totals"]["totalAmount"])
        result["billing"] = {field: metadata.get(field) for field in ("query", "recordCount", "uniquePodCount", "totals")}
        result["billing_may_lag"] = True
        result["observed_previous_cost_usd"] = prior_cost
        response = client.post("https://api.runpod.io/graphql",
                               json={"query": "query { myself { clientBalance currentSpendPerHr spendLimit } }"},
                               timeout=15, allow_redirects=False)
        response.raise_for_status()
        body = response.json()
        if body.get("errors"):
            raise RuntimeError("account readiness query failed")
        account = body["data"]["myself"]
        result["credit_sufficient"] = float(account["clientBalance"]) >= RATE_CAP + STORAGE_RESERVE_PER_HOUR
        result["spend_limit_sufficient"] = (account.get("spendLimit") is not None
            and float(account["spendLimit"]) >= float(account["currentSpendPerHr"]) + RATE_CAP + STORAGE_RESERVE_PER_HOUR)
    eligible = [offer for offer in offers if offer["eligible"]]
    eligible.sort(key=lambda offer: (offer["rate_usd_per_hour"], -{"HIGH": 3, "MEDIUM": 2, "LOW": 1}[offer["availability"]], FLAVORS.index(offer["id"])))
    result["selected_offer"] = eligible[0] if eligible else None
    projected = ((eligible[0]["rate_usd_per_hour"] + STORAGE_RESERVE_PER_HOUR) / 3) if eligible else None
    result["projected_20_minute_cost_usd"] = projected
    # No earlier smoke allocation was observed; unexpected charges require attribution.
    result["ready"] = bool(eligible and not any(result["inventories"].values())
        and math.isfinite(prior_cost) and prior_cost == 0 and metadata["recordCount"] == 0
        and result["credit_sufficient"] and result["spend_limit_sufficient"]
        and projected <= 0.10 and projected + prior_cost <= 0.20)
    return result


if __name__ == "__main__":
    try:
        result = check()
    except Exception as exc:
        result = {"checked_utc": utc_now(), "ready": False, "error_type": type(exc).__name__, "resource_writes": 0}
    path = HERE / ("HTTP-TRANSPORT-PREFLIGHT-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(path))
    raise SystemExit(0 if result["ready"] else 1)
