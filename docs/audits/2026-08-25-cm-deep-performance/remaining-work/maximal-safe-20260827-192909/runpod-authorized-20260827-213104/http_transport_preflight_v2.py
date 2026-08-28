"""Read-only preflight for one approved container-storage-only CPU retry."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from http_transport_preflight import FLAVORS, HERE, V1, V2, get_offer, inventory, session, utc_now

RATE_CAP = 0.25
STORAGE_RESERVE_PER_HOUR = 0.01
PRIOR_HTTP_RESERVE = 0.01
HTTP_CAP = 0.10
CAMPAIGN_CAP = 0.20
PRIOR_POD_ID = "eidn8uu97y3b6q"
PRIOR_RUN = HERE / "http-execute-001b"


def prior_attempt():
    def load(path):
        return json.loads(path.read_text(encoding="utf-8"))
    run = load(PRIOR_RUN / "RUN.json")
    final = load(HERE / "HTTP-FINAL-VERIFICATION-20260828-084114-539259.json")
    frozen = load(PRIOR_RUN / "TRANSPORT-FREEZE.json")
    if (run.get("pod_id") != PRIOR_POD_ID or run.get("creation_http_status") != 201
        or run.get("creation_uncertain") is not False
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or final.get("pod_id") != PRIOR_POD_ID or final.get("owned_pod_absent_verified") is not True
        or final.get("create_requests_this_authorization") != 1
        or final.get("automatic_replacement_queued") is not False
        or any(final["checks"][version]["detail_http_status"] != 404
               or final["checks"][version]["inventory"] for version in ("v1", "v2"))):
        raise RuntimeError("prior HTTP allocation is not reconciled")
    for role in ("http-controller", "http-watchdog"):
        guard = final["guard_releases"][role]
        if guard.get("released") is not True or guard.get("pid_still_running") is not False:
            raise RuntimeError("prior HTTP guard release is not verified")
    for name, field in (("runpod_http_smoke_controller_v2.py", "controller_sha256"),
                        ("http_transport_bootstrap.py", "bootstrap_sha256"),
                        ("http_transport_preflight.py", "preflight_sha256")):
        if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != frozen[field]:
            raise RuntimeError("executed HTTP source has changed")
    return {"pod_id": PRIOR_POD_ID, "cleanup_verified": True,
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
    sanitized = []
    for row in rows:
        if row.get("podId") != PRIOR_POD_ID:
            raise ValueError("billing contains an unattributed pod")
        sanitized.append({"podId": row["podId"], "amount": amount(row["amount"]),
                          "time": row.get("time")})
    if unique != len({row["podId"] for row in sanitized}):
        raise ValueError("billing unique pod count disagrees")
    if not math.isclose(sum(row["amount"] for row in sanitized), totals["totalAmount"],
                        rel_tol=0, abs_tol=1e-9):
        raise ValueError("billing detail and aggregate disagree")
    return {"metadata": {key: metadata.get(key) for key in ("query", "recordCount", "uniquePodCount", "totals")},
            "attributed_rows": sanitized, "observed_previous_cost_usd": totals["totalAmount"],
            "prior_cost_bound_usd": max(PRIOR_HTTP_RESERVE, totals["totalAmount"]),
            "billing_may_lag": True, "unattributed_records": 0}


def billing_check(client):
    params = {"startTime": "2026-08-27T00:00:00Z", "endTime": utc_now(),
              "bucketSize": "day", "grouping": "podId"}
    response = client.get(V2 + "/billing/pods", params=params, timeout=15, allow_redirects=False)
    response.raise_for_status()
    metadata = response.json()["metadata"]
    rows = []
    if metadata.get("recordCount") != 0:
        # The documented v1 grouped records expose podId and amount. Match
        # their sum against v2's aggregate; never ignore an unexplained charge.
        response = client.get(V1 + "/billing/pods", params=params, timeout=15, allow_redirects=False)
        response.raise_for_status()
        rows = response.json()
    return analyze_billing(metadata, rows)


def budget(rate, prior_cost):
    rate, prior_cost = amount(rate), amount(prior_cost)
    projected = (rate + STORAGE_RESERVE_PER_HOUR) / 3
    total = prior_cost + projected
    return {"projected_20_minute_cost_usd": projected, "projected_aggregate_http_cost_usd": total,
            "prior_cost_bound_usd": prior_cost,
            "ready": 0 < rate <= RATE_CAP and prior_cost >= PRIOR_HTTP_RESERVE
                     and total <= HTTP_CAP and total <= CAMPAIGN_CAP}


def check():
    result = {"checked_utc": utc_now(), "resource_writes": 0, "credential_values_recorded": False,
              "prior_attempt": prior_attempt()}
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
    path = HERE / ("HTTP-EPHEMERAL-PREFLIGHT-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(path))
    raise SystemExit(0 if result["ready"] else 1)
