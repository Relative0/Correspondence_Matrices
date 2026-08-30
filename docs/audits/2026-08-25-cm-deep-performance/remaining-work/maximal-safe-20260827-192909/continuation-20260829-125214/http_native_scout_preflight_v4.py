"""Read-only preflight for a dependency-closed scout after three reconciled failures."""

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
SCOUT_POD_ID = "84442bdg4m47x8"
SCOUT_RUN = HERE / "http-native-scout-execute-001/RUN.json"
SCOUT_FINAL = HERE / "HTTP-NATIVE-SCOUT-FINAL-VERIFICATION-20260829-095302-117832.json"
SCOUT_CONTROLLER = HERE / "runpod_native_scout_controller_v1.py"
SCOUT_FREEZE = HERE / "http-native-scout-execute-001/TRANSPORT-FREEZE.json"
RETRY_POD_ID = "76exgpsv0y39bl"
RETRY_RUN = HERE / "http-native-scout-retry-execute-001/RUN.json"
RETRY_FINAL = HERE / "HTTP-NATIVE-SCOUT-RETRY-FINAL-VERIFICATION-20260829-100759-402074.json"
RETRY_CONTROLLER = HERE / "runpod_native_scout_controller_v2.py"
RETRY_FREEZE = HERE / "http-native-scout-retry-execute-001/TRANSPORT-FREEZE.json"
CHUNK_POD_ID = "mljd0t0sb3h1u3"
CHUNK_RUN = HERE / "http-native-scout-chunked-retry-execute-001/RUN.json"
CHUNK_FINAL = HERE / "HTTP-NATIVE-SCOUT-CHUNKED-FINAL-VERIFICATION-20260829-105930-771906.json"
CHUNK_CONTROLLER = HERE / "runpod_native_scout_controller_v3.py"
CHUNK_FREEZE = HERE / "http-native-scout-chunked-retry-execute-001/TRANSPORT-FREEZE.json"


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
    scout_run = load(SCOUT_RUN)
    scout_final = load(SCOUT_FINAL)
    scout_freeze = load(SCOUT_FREEZE)
    if (
        scout_run.get("status") != "failed"
        or scout_run.get("error_type") != "KeyError"
        or scout_run.get("pod_id") != SCOUT_POD_ID
        or scout_run.get("creation_http_status") != 201
        or scout_run.get("creation_uncertain") is not False
        or scout_run.get("uploaded_source_files") != 0
        or scout_run.get("cleanup", {}).get("owned_pod_absent") is not True
        or scout_final.get("attempt_safely_reconciled") is not True
        or scout_final.get("authorization_consumed") is not True
        or scout_final.get("workload_completed") is not False
        or scout_final.get("owned_pods_absent_verified") is not True
        or scout_final.get("create_requests_this_authorization") != 1
        or scout_final.get("automatic_replacement_queued") is not False
        or scout_final.get("failure_diagnosis", {}).get("confirmed") is not True
        or not isinstance(scout_final.get("estimated_attempt_cost_bound_usd"), (int, float))
        or scout_final["estimated_attempt_cost_bound_usd"] < 0
        or hashlib.sha256(SCOUT_CONTROLLER.read_bytes()).hexdigest() != scout_freeze.get("controller_sha256")
    ):
        raise RuntimeError("failed native-scout attempt is not completely reconciled")
    prior_cost = max(
        float(scout_final["estimated_attempt_cost_bound_usd"]),
        float(scout_final.get("billing", {}).get("current_pod_observed_cost_usd", 0.0)),
    )
    retry_run = load(RETRY_RUN)
    retry_final = load(RETRY_FINAL)
    retry_freeze = load(RETRY_FREEZE)
    if (
        retry_run.get("status") != "failed"
        or retry_run.get("error_type") != "ReadTimeout"
        or retry_run.get("pod_id") != RETRY_POD_ID
        or retry_run.get("creation_http_status") != 201
        or retry_run.get("creation_uncertain") is not False
        or retry_run.get("cleanup", {}).get("owned_pod_absent") is not True
        or retry_final.get("attempt_safely_reconciled") is not True
        or retry_final.get("authorization_consumed") is not True
        or retry_final.get("owned_pods_absent_verified") is not True
        or retry_final.get("create_requests_this_authorization") != 1
        or retry_final.get("automatic_replacement_queued") is not False
        or retry_final.get("transfer_and_workload", {}).get("workload_completed") is not False
        or retry_final.get("transfer_and_workload", {}).get("worker_start_request_reached") is not False
        or retry_final.get("failure_diagnosis", {}).get("confirmed") is not True
        or not isinstance(retry_final.get("estimated_retry_cost_bound_usd"), (int, float))
        or retry_final["estimated_retry_cost_bound_usd"] < 0
        or hashlib.sha256(RETRY_CONTROLLER.read_bytes()).hexdigest() != retry_freeze.get("controller_sha256")
    ):
        raise RuntimeError("failed native-scout retry is not completely reconciled")
    for version in ("v1", "v2"):
        check = retry_final.get("checks", {}).get(version, {})
        if check.get("inventory"):
            raise RuntimeError("retry final inventory was not empty")
        if set(check.get("details_http_status", {}).values()) != {404}:
            raise RuntimeError("retry detail reconciliation changed")
    retry_cost = max(
        float(retry_final["estimated_retry_cost_bound_usd"]),
        float(retry_final.get("billing", {}).get("current_pod_observed_cost_usd", 0.0)),
    )
    prior_cost += retry_cost
    chunk_run = load(CHUNK_RUN)
    chunk_final = load(CHUNK_FINAL)
    chunk_freeze = load(CHUNK_FREEZE)
    if (
        chunk_run.get("status") != "failed"
        or chunk_run.get("error_type") != "FileNotFoundError"
        or chunk_run.get("pod_id") != CHUNK_POD_ID
        or chunk_run.get("creation_http_status") != 201
        or chunk_run.get("creation_uncertain") is not False
        or chunk_run.get("uploaded_source_files") != 30
        or chunk_run.get("remote_progress", {}).get("remote_status") != "failed"
        or chunk_run.get("remote_progress", {}).get("stage") != "focused-tests"
        or chunk_run.get("cleanup", {}).get("owned_pod_absent") is not True
        or chunk_final.get("attempt_safely_reconciled") is not True
        or chunk_final.get("authorization_consumed") is not True
        or chunk_final.get("workload_completed") is not False
        or chunk_final.get("owned_pods_absent_verified") is not True
        or chunk_final.get("create_requests_this_authorization") != 1
        or chunk_final.get("automatic_replacement_queued") is not False
        or chunk_final.get("chunked_transport_verified") is not True
        or chunk_final.get("evidence", {}).get("primary_failure_confirmed") is not True
        or chunk_final.get("evidence", {}).get("source_after_recorded") is not False
        or not isinstance(chunk_final.get("estimated_attempt_cost_bound_usd"), (int, float))
        or chunk_final["estimated_attempt_cost_bound_usd"] < 0
        or hashlib.sha256(CHUNK_CONTROLLER.read_bytes()).hexdigest() != chunk_freeze.get("controller_sha256")
    ):
        raise RuntimeError("failed chunked native-scout attempt is not completely reconciled")
    for version in ("v1", "v2"):
        check = chunk_final.get("checks", {}).get(version, {})
        if check.get("inventory"):
            raise RuntimeError("chunked retry final inventory was not empty")
        if set(check.get("details_http_status", {}).values()) != {404}:
            raise RuntimeError("chunked retry detail reconciliation changed")
    chunk_cost = max(
        float(chunk_final["estimated_attempt_cost_bound_usd"]),
        float(chunk_final.get("billing", {}).get("current_pod_observed_cost_usd", 0.0)),
    )
    prior_cost += chunk_cost
    return {
        "cleanup_verified": True,
        "pod_ids": sorted({
            *historical["pod_ids"], "4q816o02xw5lxn", SCOUT_POD_ID, RETRY_POD_ID, CHUNK_POD_ID
        }),
        "new_comparative_campaign_cost_before_scout_usd": prior_cost,
        "historical_campaign_cost_bound_usd": final.get("campaign_cost_bound_usd"),
        "failed_scout_attempt_reconciled": True,
        "failed_scout_retry_reconciled": True,
        "failed_chunked_scout_retry_reconciled": True,
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
            "new_comparative_campaign_observed_cost_usd": sum(
                row["amount"] for row in sanitized
                if row["podId"] in {SCOUT_POD_ID, RETRY_POD_ID, CHUNK_POD_ID}
            ), "billing_may_lag": True}


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
    result["prior_cost_bound_usd"] = max(
        result["prior_attempts"]["new_comparative_campaign_cost_before_scout_usd"],
        result["billing"]["new_comparative_campaign_observed_cost_usd"],
    )
    result["budget"] = budget(
        eligible[0]["rate_usd_per_hour"], result["prior_cost_bound_usd"]
    ) if eligible else {"ready": False}
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
    path = HERE / ("HTTP-NATIVE-SCOUT-CLOSURE-RETRY-PREFLIGHT-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(path))
    raise SystemExit(0 if result["ready"] else 1)
