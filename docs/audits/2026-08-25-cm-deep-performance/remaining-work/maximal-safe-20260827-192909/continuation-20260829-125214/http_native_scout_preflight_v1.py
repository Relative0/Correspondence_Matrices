"""Read-only account, resource, cleanup, and budget preflight for the native scout."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
TRANSPORT = HERE.parent / "runpod-authorized-20260827-213104"
spec = importlib.util.spec_from_file_location("preserved_corpus_preflight", TRANSPORT / "http_corpus_preflight_v4.py")
previous = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(TRANSPORT))
try:
    spec.loader.exec_module(previous)
finally:
    sys.path.remove(str(TRANSPORT))

V1 = previous.V1
V2 = previous.V2
FLAVORS = previous.FLAVORS
RATE_CAP = 0.25
STORAGE_RESERVE_PER_HOUR = 0.01
PRIOR_HTTP_RESERVE = 0.0
PHASE_CAP = 0.10
CAMPAIGN_CAP = 0.20
CORPUS_RUN = TRANSPORT / "http-corpus-execute-001/RUN.json"
CORPUS_FINAL = TRANSPORT / "HTTP-CORPUS-FINAL-VERIFICATION-20260829-063212-489230.json"
CORPUS_CONTROLLER = TRANSPORT / "runpod_corpus_controller_v5.py"
CORPUS_FREEZE = TRANSPORT / "http-corpus-execute-001/TRANSPORT-FREEZE.json"


utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
get_offer = previous.get_offer


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def prior_attempts():
    historical = previous.prior_attempts()
    run = load(CORPUS_RUN)
    final = load(CORPUS_FINAL)
    freeze = load(CORPUS_FREEZE)
    if (
        historical.get("cleanup_verified") is not True
        or run.get("status") != "complete"
        or run.get("pod_id") != "4q816o02xw5lxn"
        or run.get("creation_http_status") != 201
        or run.get("creation_uncertain") is not False
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or final.get("complete") is not True
        or final.get("pod_id") != run.get("pod_id")
        or final.get("owned_pods_absent_verified") is not True
        or final.get("create_requests_this_authorization") != 1
        or final.get("automatic_replacement_queued") is not False
        or final.get("evidence", {}).get("verified") is not True
        or final.get("evidence", {}).get("source_unchanged") is not True
    ):
        raise RuntimeError("prior Runpod campaign is not completely reconciled")
    for version in ("v1", "v2"):
        if final.get("checks", {}).get(version, {}).get("inventory"):
            raise RuntimeError("prior final inventory was not empty")
        statuses = final.get("checks", {}).get(version, {}).get("details_http_status", {})
        if set(statuses) != {"eidn8uu97y3b6q", "s2dpiij1msutml", "8voqzr4b1a4qti", "4q816o02xw5lxn"} or set(statuses.values()) != {404}:
            raise RuntimeError("prior detail reconciliation changed")
    if hashlib.sha256(CORPUS_CONTROLLER.read_bytes()).hexdigest() != freeze.get("controller_sha256"):
        raise RuntimeError("preserved corpus controller changed")
    return {
        "cleanup_verified": True,
        "pod_ids": sorted({*historical["pod_ids"], "4q816o02xw5lxn"}),
        "new_comparative_campaign_cost_before_scout_usd": 0.0,
        "historical_campaign_cost_bound_usd": final.get("campaign_cost_bound_usd"),
    }


def amount(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("invalid billing amount")
    return float(value)


def billing_check(client):
    params = {"startTime": "2026-08-27T00:00:00Z", "endTime": utc_now(), "bucketSize": "day", "grouping": "podId"}
    response = client.get(V2 + "/billing/pods", params=params, timeout=15, allow_redirects=False)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("records"), list) or not isinstance(body.get("metadata"), dict):
        raise ValueError("v2 billing response shape")
    metadata, rows = body["metadata"], body["records"]
    if type(metadata.get("recordCount")) is not int or metadata["recordCount"] != len(rows):
        raise ValueError("billing count mismatch")
    sanitized = []
    for row in rows:
        pod_id = row.get("podId")
        if not isinstance(pod_id, str) or not pod_id:
            raise ValueError("billing row attribution")
        components = {key: amount(row.get(key)) for key in ("cpuAmount", "gpuAmount", "diskAmount", "totalAmount")}
        if not math.isclose(components["cpuAmount"] + components["gpuAmount"] + components["diskAmount"],
                            components["totalAmount"], rel_tol=0, abs_tol=1e-9):
            raise ValueError("billing row components disagree")
        sanitized.append({"podId": pod_id, "amount": components["totalAmount"],
                          "startTime": row.get("startTime"), "endTime": row.get("endTime")})
    total = amount(metadata.get("totals", {}).get("totalAmount"))
    if not math.isclose(sum(row["amount"] for row in sanitized), total, rel_tol=0, abs_tol=1e-9):
        raise ValueError("billing aggregate disagrees")
    return {"metadata": {key: metadata.get(key) for key in ("query", "recordCount", "uniquePodCount", "totals")},
            "historical_account_rows": sanitized, "historical_total_usd": total,
            "new_comparative_campaign_observed_cost_usd": 0.0, "billing_may_lag": True}


def budget(rate, prior_cost=0.0):
    rate, prior_cost = amount(rate), amount(prior_cost)
    projected = (rate + STORAGE_RESERVE_PER_HOUR) / 3
    campaign = prior_cost + projected
    return {
        "projected_20_minute_cost_usd": projected,
        "projected_phase_cost_usd": projected,
        "projected_comparative_campaign_cost_usd": campaign,
        "comparative_campaign_prior_cost_usd": prior_cost,
        "ready": 0 < rate <= RATE_CAP and projected <= PHASE_CAP and campaign <= CAMPAIGN_CAP,
    }


def check():
    result = {
        "checked_utc": utc_now(),
        "resource_writes": 0,
        "credential_values_recorded": False,
        "prior_attempts": prior_attempts(),
    }
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
        result["billing"] = billing_check(client)
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
        balance = float(account["clientBalance"])
        current = float(account["currentSpendPerHr"])
        limit = float(account["spendLimit"]) if account.get("spendLimit") is not None else float("nan")
        result["credit_sufficient"] = math.isfinite(balance) and balance >= RATE_CAP + STORAGE_RESERVE_PER_HOUR
        result["spend_limit_sufficient"] = (
            math.isfinite(limit) and math.isfinite(current) and current >= 0
            and limit >= current + RATE_CAP + STORAGE_RESERVE_PER_HOUR
        )
    eligible = [offer for offer in offers if offer.get("eligible")]
    eligible.sort(key=lambda offer: (
        offer["rate_usd_per_hour"],
        -{"HIGH": 3, "MEDIUM": 2, "LOW": 1}[offer["availability"]],
        FLAVORS.index(offer["id"]),
    ))
    result["selected_offer"] = eligible[0] if eligible else None
    result["budget"] = budget(eligible[0]["rate_usd_per_hour"]) if eligible else {"ready": False}
    result["ready"] = bool(
        eligible
        and not any(result["inventories"].values())
        and result["credit_sufficient"]
        and result["spend_limit_sufficient"]
        and result["budget"]["ready"]
    )
    return result


if __name__ == "__main__":
    try:
        result = check()
    except Exception as exc:
        result = {"checked_utc": utc_now(), "ready": False, "error_type": type(exc).__name__, "resource_writes": 0}
        if type(exc) in (RuntimeError, ValueError):
            result["error"] = str(exc)
    path = HERE / ("HTTP-NATIVE-SCOUT-PREFLIGHT-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(path))
    raise SystemExit(0 if result["ready"] else 1)
