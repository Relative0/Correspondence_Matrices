"""Read-only preflight after the reconciled P5/procfs native-scout failure."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import http_native_scout_preflight_v5 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
FLAVORS = previous.FLAVORS
RATE_CAP = previous.RATE_CAP
STORAGE_RESERVE_PER_HOUR = previous.STORAGE_RESERVE_PER_HOUR
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
PHASE_CAP = previous.PHASE_CAP
CAMPAIGN_CAP = previous.CAMPAIGN_CAP
P5_POD_ID = "pow0qre2q39m4t"
P5_RUN = HERE / "http-native-scout-p5-cli-retry-execute-001/RUN.json"
P5_FINAL = HERE / "HTTP-NATIVE-SCOUT-P5-FINAL-VERIFICATION-20260829-123021-741562.json"
P5_CONTROLLER = HERE / "runpod_native_scout_controller_v5.py"
P5_FREEZE = HERE / "http-native-scout-p5-cli-retry-execute-001/TRANSPORT-FREEZE.json"
SCOUT_POD_IDS = {
    "84442bdg4m47x8", "76exgpsv0y39bl", "mljd0t0sb3h1u3", "pes90ta8wgi2g6", P5_POD_ID,
}

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
get_offer = previous.get_offer
amount = previous.amount
budget = previous.budget


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def prior_attempts():
    historical = previous.prior_attempts()
    run = load(P5_RUN)
    final = load(P5_FINAL)
    freeze = load(P5_FREEZE)
    if (
        run.get("status") != "failed"
        or run.get("error_type") != "RuntimeError"
        or run.get("error") != "remote workload reported failure"
        or run.get("pod_id") != P5_POD_ID
        or run.get("creation_http_status") != 201
        or run.get("creation_uncertain") is not False
        or run.get("uploaded_source_files") != 37
        or run.get("remote_progress", {}).get("remote_status") != "failed"
        or run.get("remote_progress", {}).get("stage") != "native-scout"
        or run.get("evidence", {}).get("validation", {}).get("source_unchanged") is not True
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or final.get("attempt_safely_reconciled") is not True
        or final.get("authorization_consumed") is not True
        or final.get("workload_completed") is not False
        or final.get("owned_pods_absent_verified") is not True
        or final.get("create_requests_this_authorization") != 1
        or final.get("automatic_replacement_queued") is not False
        or final.get("evidence", {}).get("primary_failure_confirmed") is not True
        or final.get("evidence", {}).get("source_unchanged") is not True
        or final.get("failure_evidence_preserved") is not True
        or final.get("evidence", {}).get("native_summary", {}).get("error")
            != "sat native worker failed: process_tree_measurement_incomplete"
        or not isinstance(final.get("estimated_attempt_cost_bound_usd"), (int, float))
        or final["estimated_attempt_cost_bound_usd"] < 0
        or hashlib.sha256(P5_CONTROLLER.read_bytes()).hexdigest() != freeze.get("controller_sha256")
    ):
        raise RuntimeError("failed P5/procfs native-scout attempt is not completely reconciled")
    expected_ids = set(historical["pod_ids"]) | {P5_POD_ID}
    for version in ("v1", "v2"):
        check = final.get("checks", {}).get(version, {})
        if check.get("inventory"):
            raise RuntimeError("P5/procfs retry final inventory was not empty")
        statuses = check.get("details_http_status", {})
        if set(statuses) != expected_ids or set(statuses.values()) != {404}:
            raise RuntimeError("P5/procfs retry detail reconciliation changed")
    p5_cost = max(
        float(final["estimated_attempt_cost_bound_usd"]),
        float(final.get("billing", {}).get("current_pod_observed_cost_usd", 0.0)),
    )
    return {
        **historical,
        "pod_ids": sorted(expected_ids),
        "new_comparative_campaign_cost_before_scout_usd": (
            float(historical["new_comparative_campaign_cost_before_scout_usd"]) + p5_cost
        ),
        "failed_p5_procfs_scout_retry_reconciled": True,
    }


def billing_check(client):
    result = previous.billing_check(client)
    result["new_comparative_campaign_observed_cost_usd"] = sum(
        row["amount"] for row in result["historical_account_rows"] if row["podId"] in SCOUT_POD_IDS
    )
    return result


def check():
    prior = prior_attempts()
    result = {
        "checked_utc": utc_now(),
        "resource_writes": 0,
        "credential_values_recorded": False,
        "prior_attempts": prior,
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
        prior["new_comparative_campaign_cost_before_scout_usd"],
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
    path = HERE / (
        "HTTP-NATIVE-SCOUT-PROCFS-RACE-RETRY-PREFLIGHT-"
        + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json"
    )
    with path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(path))
    raise SystemExit(0 if result["ready"] else 1)
