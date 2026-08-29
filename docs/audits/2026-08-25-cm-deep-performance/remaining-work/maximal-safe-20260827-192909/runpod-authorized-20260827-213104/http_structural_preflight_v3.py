"""Read-only preflight for one authorized zero-volume structural CPU study."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math

from http_transport_preflight import FLAVORS, HERE, V1, V2, get_offer, inventory, session, utc_now
import http_transport_preflight_v2 as previous_preflight

RATE_CAP = 0.25
STORAGE_RESERVE_PER_HOUR = 0.01
PRIOR_HTTP_RESERVE = 0.02
PHASE_CAP = 0.10
CAMPAIGN_CAP = 0.20
PRIOR_POD_IDS = {"eidn8uu97y3b6q", "s2dpiij1msutml"}
SUCCESSFUL_RUN = HERE / "http-ephemeral-execute-001"
SUCCESSFUL_FINAL = HERE / "HTTP-EPHEMERAL-FINAL-VERIFICATION-20260828-090555-697553.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def prior_attempts():
    first = previous_preflight.prior_attempt()
    run = load(SUCCESSFUL_RUN / "RUN.json")
    final = load(SUCCESSFUL_FINAL)
    frozen = load(SUCCESSFUL_RUN / "TRANSPORT-FREEZE.json")
    if (first.get("pod_id") != "eidn8uu97y3b6q" or first.get("cleanup_verified") is not True
        or run.get("status") != "complete" or run.get("pod_id") != "s2dpiij1msutml"
        or run.get("creation_http_status") != 201 or run.get("creation_uncertain") is not False
        or run.get("uploaded_source_files") != 65
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or final.get("complete") is not True or final.get("pod_id") != "s2dpiij1msutml"
        or final.get("owned_pods_absent_verified") is not True
        or final.get("create_requests_this_amendment") != 1
        or final.get("automatic_replacement_queued") is not False
        or final.get("approved_source_hashes_match") is not True
        or final.get("frozen_source_preserved") is not True):
        raise RuntimeError("prior HTTP allocations are not reconciled")
    for version in ("v1", "v2"):
        check = final["checks"][version]
        if check.get("inventory") or check.get("details_http_status") != {
                "eidn8uu97y3b6q": 404, "s2dpiij1msutml": 404}:
            raise RuntimeError("prior HTTP inventory/detail reconciliation changed")
    for role in ("http-controller", "http-watchdog"):
        guard = final["guard_releases"][role]
        if guard.get("released") is not True or guard.get("pid_still_running") is not False:
            raise RuntimeError("prior HTTP guard release is not verified")
    for name, field in (("runpod_http_smoke_controller_v3.py", "controller_sha256"),
                        ("http_transport_bootstrap.py", "bootstrap_sha256"),
                        ("http_transport_preflight_v2.py", "preflight_sha256")):
        if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != frozen[field]:
            raise RuntimeError("executed HTTP source has changed")
    return {"pod_ids": sorted(PRIOR_POD_IDS), "cleanup_verified": True,
            "minimum_delayed_billing_reserve_usd": PRIOR_HTTP_RESERVE}


def amount(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("invalid billing amount")
    return float(value)


def analyze_billing(metadata, rows):
    count, unique = metadata["recordCount"], metadata["uniquePodCount"]
    if (type(count) is not int or type(unique) is not int or not 0 <= unique <= count <= 10000
        or not isinstance(rows, list) or len(rows) != count):
        raise ValueError("billing record count is not reconciled")
    totals = {key: amount(metadata["totals"][key])
              for key in ("cpuAmount", "gpuAmount", "diskAmount", "totalAmount")}
    if not math.isclose(sum(totals[key] for key in ("cpuAmount", "gpuAmount", "diskAmount")),
                        totals["totalAmount"], rel_tol=0, abs_tol=1e-9):
        raise ValueError("billing component totals disagree")
    uses_component_rows = bool(rows) and all("totalAmount" in row for row in rows)
    if rows and not (uses_component_rows or all("amount" in row for row in rows)):
        raise ValueError("billing rows use an inconsistent schema")
    sanitized = []
    component_rows = []
    for row in rows:
        pod_id = row.get("podId")
        if not isinstance(pod_id, str) or not pod_id:
            raise ValueError("billing row has no pod attribution")
        if uses_component_rows:
            components = {key: amount(row.get(key))
                          for key in ("cpuAmount", "gpuAmount", "diskAmount", "totalAmount")}
            if not math.isclose(sum(components[key] for key in ("cpuAmount", "gpuAmount", "diskAmount")),
                                components["totalAmount"], rel_tol=0, abs_tol=1e-9):
                raise ValueError("billing row component totals disagree")
            component_rows.append(components)
            sanitized.append({"podId": pod_id, "amount": components["totalAmount"],
                              "startTime": row.get("startTime"), "endTime": row.get("endTime")})
        else:
            sanitized.append({"podId": pod_id, "amount": amount(row.get("amount")), "time": row.get("time")})
    if unique != len({row["podId"] for row in sanitized}):
        raise ValueError("billing unique pod count disagrees")
    if not math.isclose(sum(row["amount"] for row in sanitized), totals["totalAmount"],
                        rel_tol=0, abs_tol=1e-9):
        raise ValueError("billing detail and aggregate disagree")
    if uses_component_rows:
        for key in ("cpuAmount", "gpuAmount", "diskAmount", "totalAmount"):
            if not math.isclose(sum(row[key] for row in component_rows), totals[key], rel_tol=0, abs_tol=1e-9):
                raise ValueError("billing record components and aggregate disagree")
    attributed = [row for row in sanitized if row["podId"] in PRIOR_POD_IDS]
    unrelated = [row for row in sanitized if row["podId"] not in PRIOR_POD_IDS]
    known_cost = sum(row["amount"] for row in attributed)
    return {"metadata": {key: metadata.get(key) for key in ("query", "recordCount", "uniquePodCount", "totals")},
            "attributed_rows": attributed, "unrelated_account_rows": unrelated,
            "observed_previous_cost_usd": known_cost,
            "prior_cost_bound_usd": max(PRIOR_HTTP_RESERVE, known_cost),
            "billing_may_lag": True, "unattributed_records": 0,
            "record_source": "v2_metadata_and_records" if uses_component_rows else "normalized_fixture_or_v1"}


def billing_check(client):
    params = {"startTime": "2026-08-27T00:00:00Z", "endTime": utc_now(),
              "bucketSize": "day", "grouping": "podId"}
    response = client.get(V2 + "/billing/pods", params=params, timeout=15, allow_redirects=False)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("records"), list):
        raise ValueError("v2 billing response has no records array")
    return analyze_billing(body["metadata"], body["records"])


def budget(rate, prior_cost):
    rate, prior_cost = amount(rate), amount(prior_cost)
    projected = (rate + STORAGE_RESERVE_PER_HOUR) / 3
    campaign = prior_cost + projected
    return {"projected_20_minute_cost_usd": projected,
            "projected_phase_cost_usd": projected,
            "projected_campaign_cost_usd": campaign,
            "prior_cost_bound_usd": prior_cost,
            "ready": 0 < rate <= RATE_CAP and prior_cost >= PRIOR_HTTP_RESERVE
                     and projected <= PHASE_CAP and campaign <= CAMPAIGN_CAP}


def check():
    result = {"checked_utc": utc_now(), "resource_writes": 0, "credential_values_recorded": False,
              "prior_attempts": prior_attempts()}
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
        result["observed_previous_cost_usd"] = result["billing"]["observed_previous_cost_usd"]
        result["prior_cost_bound_usd"] = result["billing"]["prior_cost_bound_usd"]
        response = client.post("https://api.runpod.io/graphql",
                               json={"query": "query { myself { clientBalance currentSpendPerHr spendLimit } }"},
                               timeout=15, allow_redirects=False)
        response.raise_for_status()
        body = response.json()
        if body.get("errors"):
            raise RuntimeError("account readiness query failed")
        account = body["data"]["myself"]
        balance = float(account["clientBalance"])
        current = float(account["currentSpendPerHr"])
        limit = float(account["spendLimit"]) if account.get("spendLimit") is not None else float("nan")
        result["credit_sufficient"] = math.isfinite(balance) and balance >= RATE_CAP + STORAGE_RESERVE_PER_HOUR
        result["spend_limit_sufficient"] = (math.isfinite(limit) and math.isfinite(current) and current >= 0
            and limit >= current + RATE_CAP + STORAGE_RESERVE_PER_HOUR)
    eligible = [offer for offer in offers if offer["eligible"]]
    eligible.sort(key=lambda offer: (offer["rate_usd_per_hour"],
        -{"HIGH": 3, "MEDIUM": 2, "LOW": 1}[offer["availability"]], FLAVORS.index(offer["id"])))
    result["selected_offer"] = eligible[0] if eligible else None
    result["budget"] = budget(eligible[0]["rate_usd_per_hour"], result["prior_cost_bound_usd"]) if eligible else {"ready": False}
    result["ready"] = bool(eligible and not any(result["inventories"].values())
        and result["credit_sufficient"] and result["spend_limit_sufficient"] and result["budget"]["ready"])
    return result


if __name__ == "__main__":
    try:
        result = check()
    except Exception as exc:
        result = {"checked_utc": utc_now(), "ready": False, "error_type": type(exc).__name__, "resource_writes": 0}
        if type(exc) in (RuntimeError, ValueError):
            result["error"] = str(exc)
    path = HERE / ("HTTP-STRUCTURAL-PREFLIGHT-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(path))
    raise SystemExit(0 if result["ready"] else 1)
